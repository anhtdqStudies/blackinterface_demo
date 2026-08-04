"""Where the station model comes from, and the one place it is cached.

Two sources, one downstream code path:

  BI_SOURCE=fixture   read a dumped address space from disk (default)
  BI_SOURCE=opcua     browse a live OneATS DataServer

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
from blackinterface.errors import ModelNotLoadedError, SourceUnavailableError
from blackinterface.logs import get_logger

log = get_logger(__name__)


class StationStore:
    """Holds the current graph. Rebuilt only on explicit reload."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._graph: StationGraph | None = None
        self._loaded_at: float | None = None
        self._load_seconds: float | None = None
        self._load_error: str | None = None

    @property
    def graph(self) -> StationGraph:
        if self._graph is None:
            raise ModelNotLoadedError(
                self._load_error or "station model has not been loaded yet",
                source=self.settings.source,
            )
        return self._graph

    @property
    def loaded(self) -> bool:
        return self._graph is not None

    @property
    def loaded_at(self) -> float | None:
        return self._loaded_at

    @property
    def load_seconds(self) -> float | None:
        return self._load_seconds

    @property
    def load_error(self) -> str | None:
        return self._load_error

    async def reload(self) -> StationGraph:
        started = time.perf_counter()
        obs = await self._observe()
        graph = build_station(obs)
        self._graph = graph
        self._load_seconds = time.perf_counter() - started
        self._loaded_at = time.time()
        self._load_error = None
        log.info(
            "station model built",
            source=self.settings.source,
            model=graph.name,
            model_version=graph.model_version,
            bays=len(graph.bays),
            devices=len(graph.devices),
            issues=len(graph.all_issues()),
            seconds=round(self._load_seconds, 3),
        )
        return graph

    async def try_reload(self) -> str | None:
        """Reload, recording the failure instead of raising. Returns the error."""
        try:
            await self.reload()
        except Exception as exc:
            self._load_error = f"{type(exc).__name__}: {exc}"
            log.error("station model load failed", error=self._load_error)
        return self._load_error

    async def _observe(self) -> StationObs:
        if self.settings.source == "opcua":
            return await self._observe_opcua()
        return self._observe_fixture()

    async def _observe_opcua(self) -> StationObs:
        # Lazy: keeps asyncua out of the api import graph (AGENTS.md I6).
        from blackinterface.integration.opcua.discovery import discover_station

        if self.settings.anonymous_opcua:
            log.warning(
                "connecting to OneATS anonymously - a real station must use a "
                "read-only account (AGENTS.md I1)",
                url=self.settings.opcua_url,
            )
        try:
            return await discover_station(
                self.settings.opcua_url,
                username=self.settings.opcua_user,
                password=self.settings.opcua_password,
                timeout=self.settings.opcua_timeout,
            )
        except Exception as exc:
            raise SourceUnavailableError(
                f"cannot read the OneATS DataServer: {exc}",
                url=self.settings.opcua_url,
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
