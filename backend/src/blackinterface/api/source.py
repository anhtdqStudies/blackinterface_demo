"""Where the station model comes from, and the one place it is cached.

Three ways a model gets loaded, one downstream code path:

  * a **project** opened from its stored snapshot — instant, works offline
  * a **project** refreshed live from its DataServer URL (snapshot updated)
  * the BI_SOURCE fallback (`fixture` | `opcua`) when no project is active —
    what tests and headless dev use

The OPC UA importer is imported lazily inside the function that needs it. That
is deliberate: `api` must not pull `asyncua` into its import graph, and the
architecture test in tests/unit/test_architecture.py checks exactly that.
"""

from __future__ import annotations

import time

from blackinterface.config import Settings, get_settings
from blackinterface.domain.models import StationGraph
from blackinterface.domain.observation import StationObs
from blackinterface.domain.topology import build_station
from blackinterface.errors import (
    ConfigurationError,
    ModelNotLoadedError,
    NotFoundError,
    SourceUnavailableError,
)
from blackinterface.logs import get_logger
from blackinterface.store.db import Database
from blackinterface.store.meta import ACTIVE_PROJECT_ID, MetaRepository
from blackinterface.store.projects import ProjectRepository, ProjectRow

log = get_logger(__name__)


class StationStore:
    """Holds the current graph. Rebuilt only on explicit reload/open/refresh."""

    def __init__(self, settings: Settings | None = None, database: Database | None = None) -> None:
        self.settings = settings or get_settings()
        self._database = database
        self._graph: StationGraph | None = None
        self._project: ProjectRow | None = None
        self._loaded_at: float | None = None
        self._load_seconds: float | None = None
        self._load_error: str | None = None

    # ----------------------------------------------------------- repositories
    @property
    def projects(self) -> ProjectRepository:
        if self._database is None:
            raise ConfigurationError("this StationStore was built without a database")
        return ProjectRepository(self._database)

    @property
    def _meta(self) -> MetaRepository:
        if self._database is None:
            raise ConfigurationError("this StationStore was built without a database")
        return MetaRepository(self._database)

    # ------------------------------------------------------------------ state
    @property
    def graph(self) -> StationGraph:
        if self._graph is None:
            raise ModelNotLoadedError(
                self._load_error or "station model has not been loaded yet",
                source=self.source_label,
            )
        return self._graph

    @property
    def loaded(self) -> bool:
        return self._graph is not None

    @property
    def project(self) -> ProjectRow | None:
        """The project the current graph came from, if any."""
        return self._project

    @property
    def source_label(self) -> str:
        if self._project is not None:
            return f"project:{self._project.name}"
        return self.settings.source

    @property
    def loaded_at(self) -> float | None:
        return self._loaded_at

    @property
    def load_seconds(self) -> float | None:
        return self._load_seconds

    @property
    def load_error(self) -> str | None:
        return self._load_error

    # ---------------------------------------------------------------- loading
    async def startup(self) -> None:
        """Reopen the last active project from its snapshot; else BI_SOURCE.

        Never raises: a failed load must not take the process down, so
        /api/health can report *why* nothing is showing.
        """
        project = self._startup_project()
        if project is not None:
            try:
                await self.open_project(project.id)
            except Exception as exc:  # recorded, surfaced via /api/health
                self._load_error = f"{type(exc).__name__}: {exc}"
                log.error(
                    "could not reopen last project",
                    project=project.name,
                    error=self._load_error,
                )
            return
        await self.try_reload()

    def _startup_project(self) -> ProjectRow | None:
        if self._database is None:
            return None
        raw = self._meta.get(ACTIVE_PROJECT_ID)
        if not raw:  # never set, or cleared to "" by unload()
            return None
        project = self.projects.get(int(raw))
        if project is None:
            # Deleted since. Clean up so we do not chase it every boot.
            self._meta.set(ACTIVE_PROJECT_ID, "")
            return None
        return project

    async def open_project(self, project_id: int) -> StationGraph:
        """Make a project current, rendering from its snapshot when one exists.

        No snapshot yet (its first connection failed) -> read live, which also
        creates the snapshot.
        """
        project = self._require_project(project_id)
        obs_json = self.projects.load_snapshot(project.id)
        if obs_json is None:
            return await self.refresh_project(project_id)
        obs = StationObs.model_validate_json(obs_json)
        obs = obs.model_copy(update={"source": f"snapshot:{obs.source or project.opcua_url}"})
        return self._install(obs, project)

    async def refresh_project(self, project_id: int) -> StationGraph:
        """Browse the project's DataServer live and replace its snapshot."""
        project = self._require_project(project_id)
        obs = await self._observe_opcua(project.opcua_url)
        self.projects.save_snapshot(
            project.id,
            obs.model_dump_json(),
            model_name=obs.name,
            model_version=obs.model_version,
            captured_at=obs.captured_at.isoformat() if obs.captured_at else None,
        )
        return self._install(obs, self.projects.get(project.id))

    async def reload(self) -> StationGraph:
        """Re-read the current source: active project live, else BI_SOURCE."""
        if self._project is not None:
            return await self.refresh_project(self._project.id)
        obs = await self._observe_settings()
        return self._install(obs, None)

    async def try_reload(self) -> str | None:
        """Reload, recording the failure instead of raising. Returns the error."""
        try:
            await self.reload()
        except Exception as exc:  # recorded, surfaced via /api/health
            self._load_error = f"{type(exc).__name__}: {exc}"
            log.error("station model load failed", error=self._load_error)
        return self._load_error

    def unload(self) -> None:
        """Forget the current graph and project (used when the project is deleted)."""
        self._graph = None
        self._project = None
        self._load_error = None
        if self._database is not None:
            self._meta.set(ACTIVE_PROJECT_ID, "")

    # ----------------------------------------------------------------- humble
    def _require_project(self, project_id: int) -> ProjectRow:
        project = self.projects.get(project_id)
        if project is None:
            raise NotFoundError(f"no such project: {project_id}", project_id=project_id)
        return project

    def _install(self, obs: StationObs, project: ProjectRow | None) -> StationGraph:
        started = time.perf_counter()
        graph = build_station(obs)
        self._graph = graph
        self._project = project
        self._load_seconds = time.perf_counter() - started
        self._loaded_at = time.time()
        self._load_error = None
        if project is not None and self._database is not None:
            self._meta.set(ACTIVE_PROJECT_ID, str(project.id))
        log.info(
            "station model built",
            source=self.source_label,
            model=graph.name,
            model_version=graph.model_version,
            bays=len(graph.bays),
            devices=len(graph.devices),
            issues=len(graph.all_issues()),
            seconds=round(self._load_seconds, 3),
        )
        return graph

    # ------------------------------------------------------------- observers
    async def _observe_settings(self) -> StationObs:
        if self.settings.source == "opcua":
            return await self._observe_opcua(self.settings.opcua_url)
        return self._observe_fixture()

    async def _observe_opcua(self, url: str) -> StationObs:
        # Lazy: keeps asyncua out of the api import graph (AGENTS.md I6).
        from blackinterface.integration.opcua.discovery import discover_station

        if not self.settings.opcua_user:
            log.warning(
                "connecting to OneATS anonymously - a real station must use a "
                "read-only account (AGENTS.md I1)",
                url=url,
            )
        try:
            return await discover_station(
                url,
                username=self.settings.opcua_user,
                password=self.settings.opcua_password,
                timeout=self.settings.opcua_timeout,
            )
        except Exception as exc:
            raise SourceUnavailableError(
                f"cannot read the OneATS DataServer: {exc}",
                url=url,
            ) from exc

    def _observe_fixture(self) -> StationObs:
        from blackinterface.integration.dump import load_dump

        path = self.settings.fixture
        if not path.exists():
            raise SourceUnavailableError(
                f"fixture not found: {path}. Generate it with: "
                "python tools/probe_dataserver.py --dump --slim --depth 4 "
                "--out backend/tests/fixtures/sas_tree.json",
                path=str(path),
            )
        return load_dump(path)
