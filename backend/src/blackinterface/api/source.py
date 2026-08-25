"""Which station model is current, and how it stays current.

Three ways a model gets loaded, one downstream code path:

  * a **project** opened from its stored snapshot — instant, works offline
  * a **project** refreshed live from its DataServer URL (snapshot updated)
  * the BI_SOURCE fallback (`fixture` | `opcua`) when no project is active —
    what tests and headless dev use

Once loaded, the model is kept current by a subscription rather than by browsing
again: `integration/opcua/monitor.py` pushes new readings of the points the
observation already named, `apply_samples` puts them back, and the graph is
rebuilt. Rebuilding the whole thing per batch sounds wasteful and is not —
measured 2026-08-05 on DEMO_SAS, build_station is 0.7 ms and solve_energization
0.2 ms. Paying a millisecond buys the guarantee that a live-updated graph is
bit-for-bit what a fresh browse would have produced, which mutating one in place
could not promise.

One batch of readings, two destinations. The subscription does not distinguish
a breaker position from a load reading, so this module does: refs in the state
set rebuild the graph, refs in the measurement set only relabel it, and the two
sets are disjoint by construction (ADR-0012 rule 1). That routing is the reason
a storm of analog values cannot delay the handling of a breaker that tripped.

What this module is *not*: it does not read sources (`reader.py`), it does not
run the subscription (`watch.py`), and it does not track who is streaming
(`broadcast.py`). It decides which model is current and when that changed.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING

from blackinterface.api.alarmsource import AlarmStore
from blackinterface.api.alarmwatch import AlarmSupervisor
from blackinterface.api.broadcast import Cadence, Listener, RevisionBroadcaster
from blackinterface.api.reader import SourceReader
from blackinterface.api.throttle import Throttle
from blackinterface.api.watch import MonitorSupervisor
from blackinterface.config import Settings, get_settings
from blackinterface.domain.measurement import MeasurementSet, filter_deadband, read_measurements
from blackinterface.domain.models import PointSample, StationGraph
from blackinterface.domain.observation import (
    StationObs,
    apply_measurement_samples,
    apply_state_samples,
    measurement_points,
    state_points,
    watch_points,
)
from blackinterface.domain.topology import build_station
from blackinterface.errors import ConfigurationError, ModelNotLoadedError, NotFoundError
from blackinterface.logs import get_logger
from blackinterface.store.db import Database
from blackinterface.store.meta import ACTIVE_PROJECT_ID, MetaRepository
from blackinterface.store.projects import ProjectRepository, ProjectRow

if TYPE_CHECKING:
    from blackinterface.integration.opcua.monitor import MonitorStatus

log = get_logger(__name__)


class StationStore:
    """Holds the current graph, and keeps it current.

    Four clocks run here, and keeping them apart is what lets a client do the
    least work that is still correct:

      * `structure_revision` — the station was browsed again. Redraw.
      * `state_revision` — a position or `IsLive` moved. Recolour.
      * `measurement_revision` — an analog value moved. Relabel.
      * `link_revision` — the subscription came up or went down. Re-badge.
    """

    def __init__(self, settings: Settings | None = None, database: Database | None = None) -> None:
        self.settings = settings or get_settings()
        self._database = database
        self._reader = SourceReader(self.settings)
        self._broadcast = RevisionBroadcaster()
        self._watch = MonitorSupervisor(
            self.settings, on_batch=self.apply_live, on_status=self._on_monitor_status
        )
        # Alarms ride their own channel (ADR-0026) and their own supervisor: an
        # alarm subscription that has dropped must not stop the diagram being
        # drawn, and a lost point subscription must not silence alarms.
        self.alarms = AlarmStore()
        self._alarm_watch = AlarmSupervisor(self.settings, self.alarms, self._broadcast)
        self._measurement_pulse = Throttle(
            self.settings.measurement_throttle_ms / 1000.0, self._announce_measurement
        )

        self._obs: StationObs | None = None
        self._graph: StationGraph | None = None
        self._measurements = MeasurementSet()
        self._project: ProjectRow | None = None
        self._loaded_at: float | None = None
        self._load_seconds: float | None = None
        self._load_error: str | None = None
        self._structure_revision = 0
        self._updated_at: float | None = None
        self._measured_at: float | None = None
        #: Which refs belong to which cadence. Recomputed on every install, so
        #: a point can never end up in both — the routing below trusts that.
        self._state_refs: frozenset[str] = frozenset()
        self._measurement_refs: frozenset[str] = frozenset()

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

    @property
    def measurements(self) -> MeasurementSet:
        """The analog readings behind the current observation. Never empty of
        meaning: a station with no instrument transformers simply has none."""
        return self._measurements

    @property
    def state_revision(self) -> int:
        """Bumped by every change to a position or `IsLive`, and every reload."""
        return self._broadcast.revision(Cadence.STATE)

    @property
    def measurement_revision(self) -> int:
        """Bumped when an analog reading moved further than its deadband."""
        return self._broadcast.revision(Cadence.MEASUREMENT)

    @property
    def link_revision(self) -> int:
        """Bumped when the subscription's own status changed."""
        return self._broadcast.revision(Cadence.LINK)

    @property
    def structure_revision(self) -> int:
        """Bumped only when the station was browsed again. Geometry key."""
        return self._structure_revision

    @property
    def updated_at(self) -> float | None:
        return self._updated_at

    @property
    def measured_at(self) -> float | None:
        """When the readings last changed. Separate from `updated_at`, because a
        station whose load moves while nothing switches is still current."""
        return self._measured_at

    @property
    def monitor_status(self) -> MonitorStatus | None:
        """None when no subscription is configured for the current source."""
        return self._watch.status

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
        return await self._install(obs, project)

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
        return await self._install(obs, self.projects.get(project.id))

    async def reload(self) -> StationGraph:
        """Re-read the current source: active project live, else BI_SOURCE."""
        if self._project is not None:
            return await self.refresh_project(self._project.id)
        obs = await self._reader.from_settings()
        return await self._install(obs, None)

    async def try_reload(self) -> str | None:
        """Reload, recording the failure instead of raising. Returns the error."""
        try:
            await self.reload()
        except Exception as exc:  # recorded, surfaced via /api/health
            self._load_error = f"{type(exc).__name__}: {exc}"
            log.error("station model load failed", error=self._load_error)
        return self._load_error

    async def unload(self) -> None:
        """Forget the current graph and project (used when the project is deleted)."""
        await self._watch.stop()
        await self._alarm_watch.stop()
        self.alarms.clear()
        self._measurement_pulse.cancel()
        self._obs = None
        self._graph = None
        self._measurements = MeasurementSet()
        self._state_refs = frozenset()
        self._measurement_refs = frozenset()
        self._project = None
        self._load_error = None
        self._structure_revision += 1
        self._broadcast.bump(Cadence.STATE)
        if self._database is not None:
            self._meta.set(ACTIVE_PROJECT_ID, "")

    async def shutdown(self) -> None:
        """Release the subscriptions. Called from the app's lifespan."""
        await self._watch.stop()
        await self._alarm_watch.stop()
        self._measurement_pulse.cancel()

    # ----------------------------------------------------------------- humble
    def _require_project(self, project_id: int) -> ProjectRow:
        project = self.projects.get(project_id)
        if project is None:
            raise NotFoundError(f"no such project: {project_id}", project_id=project_id)
        return project

    async def _observe_opcua(self, url: str) -> StationObs:
        """Seam kept on the store itself: the offline project tests replace this
        one method to serve the committed fixture in place of a DataServer."""
        return await self._reader.from_opcua(url)

    async def _install(self, obs: StationObs, project: ProjectRow | None) -> StationGraph:
        started = time.perf_counter()
        graph = build_station(obs)
        self._obs = obs
        self._graph = graph
        self._measurements = read_measurements(obs)
        self._state_refs = frozenset(state_points(obs))
        self._measurement_refs = frozenset(measurement_points(obs))
        self._project = project
        self._load_seconds = time.perf_counter() - started
        self._loaded_at = time.time()
        self._updated_at = self._loaded_at
        self._measured_at = self._loaded_at
        self._load_error = None
        self._structure_revision += 1
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
        await self._watch.sync(self._monitor_url(), watch_points(obs))
        await self._alarm_watch.sync(self._monitor_url())
        self._broadcast.bump(Cadence.STATE)
        return graph

    # --------------------------------------------------------------- realtime
    def listen(self) -> AbstractAsyncContextManager[Listener]:
        """Subscribe to cadence pulses for as long as the block runs."""
        return self._broadcast.listen()

    async def apply_live(self, samples: Mapping[str, PointSample]) -> None:
        """Fold a batch of fresh readings into the model. Called by the monitor.

        The batch arrives undifferentiated — one subscription, one link — so
        this is where it is split. Anything the current observation does not
        claim is ignored: a stale NodeId from a snapshot that predates the
        running model is not a reason to touch either half.
        """
        if self._obs is None:
            return
        state = {ref: s for ref, s in samples.items() if ref in self._state_refs}
        measured = {ref: s for ref, s in samples.items() if ref in self._measurement_refs}
        if state:
            self._apply_state(state)
        if measured:
            self._apply_measurements(measured)

    def _apply_state(self, samples: Mapping[str, PointSample]) -> None:
        """A position moved: rebuild the graph and re-solve energisation.

        Rebuilds rather than mutates (see the module docstring). Never
        throttled, never deadbanded — a breaker that trips and recloses inside
        a window is exactly what has to be seen.
        """
        patched = apply_state_samples(self._obs, samples) if self._obs else None
        if patched is None or patched is self._obs:
            return
        self._obs = patched
        self._graph = build_station(patched)
        self._updated_at = time.time()
        self._broadcast.bump(Cadence.STATE)

    def _apply_measurements(self, samples: Mapping[str, PointSample]) -> None:
        """An analog value moved: relabel, and touch nothing electrical.

        `self._graph` is deliberately not reassigned here. That is the ADR-0012
        rule 1 boundary, and `tests/unit/test_measurement.py` holds it: a
        measurement batch must leave `structure_revision`, the graph and the
        energisation verdict bit-for-bit as they were.
        """
        if self._obs is None:
            return
        kept = filter_deadband(
            self._obs, samples, pct_override=self.settings.measurement_deadband_pct
        )
        patched = apply_measurement_samples(self._obs, kept)
        if patched is self._obs:
            return
        self._obs = patched
        self._measurements = read_measurements(patched)
        self._measured_at = time.time()
        self._measurement_pulse.offer()

    def _announce_measurement(self) -> None:
        self._broadcast.bump(Cadence.MEASUREMENT)

    def _monitor_url(self) -> str | None:
        """Which DataServer to watch, or None if this source cannot be watched.

        A project is watched at its own URL even when it was opened from a
        snapshot: the snapshot supplies the structure instantly, and the
        subscription then corrects every reading in it. BI_SOURCE=fixture has
        no server behind it and is never watched.
        """
        if not self.settings.realtime:
            return None
        if self._project is not None:
            return self._project.opcua_url
        if self.settings.source == "opcua":
            return self.settings.opcua_url
        return None

    def _on_monitor_status(self, status: MonitorStatus) -> None:
        """The link coming up or going down is its own cadence: it changes what
        the screen may claim, without changing anything about the station."""
        self._broadcast.bump(Cadence.LINK)
