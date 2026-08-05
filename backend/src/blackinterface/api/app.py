"""Typed Domain API — deterministic, LLM-free (AGENTS.md I4, I5).

The frontend talks to these endpoints directly. BlackCore, when it exists, will
call the same ones with the same rights: no private path, no elevated access.

Everything here is read-only with respect to OneATS. There is no write endpoint
and no place to add one without also changing the invariants (I1).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from blackinterface.api import errors as error_handlers
from blackinterface.api.source import StationStore
from blackinterface.config import get_settings
from blackinterface.diagram.layout import (
    DiagramView,
    StationView,
    layout_station,
    layout_voltage_level,
)
from blackinterface.domain.energization import (
    CrossCheck,
    Island,
    LiveState,
    solve_energization,
)
from blackinterface.domain.models import (
    Bay,
    Busbar,
    Device,
    Quality,
    StationGraph,
    SwitchState,
    ValidationIssue,
)
from blackinterface.errors import ConflictError, InvalidInputError, NotFoundError
from blackinterface.logs import configure as configure_logging
from blackinterface.logs import get_logger
from blackinterface.store.db import Database
from blackinterface.store.projects import ProjectRow

log = get_logger(__name__)

settings = get_settings()
database = Database(settings.db_path)
store = StationStore(settings, database)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level, settings.log_json)
    log.info(
        "starting",
        source=settings.source,
        db=str(settings.db_path),
        frontend=str(settings.frontend_dir) if settings.frontend_dir else None,
    )
    database.migrate()
    # Reopen the last project from its snapshot, else fall back to BI_SOURCE.
    # A failed load must not take the process down: /api/health has to stay
    # answerable so an operator can see *why* nothing is showing.
    await store.startup()
    yield
    database.close()


app = FastAPI(
    title="Black Interface — Domain API",
    version="0.1.0",
    summary="Read-only station model from OneATS DataServer",
    lifespan=lifespan,
)
error_handlers.install(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ responses
class HealthOut(BaseModel):
    ok: bool
    loaded: bool
    source: str
    load_error: str | None = None
    load_seconds: float | None = None
    project_id: int | None = None
    project_name: str | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    opcua_url: str
    created_at: str
    updated_at: str
    has_snapshot: bool
    model_name: str | None
    model_version: str | None
    captured_at: str | None
    snapshot_saved_at: str | None
    active: bool


class ProjectCreateIn(BaseModel):
    name: str
    opcua_url: str


class ProjectLoadOut(BaseModel):
    """Result of creating/opening/refreshing a project.

    `ok=False` means the project exists but its source could not be read —
    the row is kept so the operator can fix the URL or the network and retry.
    """

    project: ProjectOut
    ok: bool
    error: str | None = None


class StationOut(BaseModel):
    name: str
    model_version: str | None
    captured_at: str | None
    source: str
    voltage_levels: list[str]
    bay_count: int
    device_count: int
    busbar_count: int
    node_count: int
    load_seconds: float | None
    coverage: dict[str, int]
    issues: list[ValidationIssue]


class DeviceOut(BaseModel):
    id: str
    ln: str
    role: str
    name: str
    short_name: str
    state: SwitchState
    quality: Quality
    value: float | int | bool | str | None
    source_timestamp: str | None
    source_ref: str | None
    terminals: list[str]


class BayOut(BaseModel):
    id: str
    name: str
    voltage_level: str
    bay_type: str
    template_id: str | None
    device_count: int
    is_live: bool | None
    is_live_quality: Quality
    logical_nodes: list[str]
    issues: list[ValidationIssue]


class BayDetailOut(BayOut):
    devices: list[DeviceOut]


class BusbarOut(BaseModel):
    id: str
    name: str
    voltage_level: str
    index: int
    is_live: bool | None
    quality: Quality
    inferred: bool


class EnergizationOut(BaseModel):
    """Which conductors are live, why, and whether OneATS agrees.

    `node_state` is keyed by connectivity node so the drawing can be coloured by
    joining on `RailView.node_id` / `EdgeView.node_id` — geometry and
    energisation stay separate, which is what will let the realtime module push
    a new verdict without re-laying-out the station.
    """

    islands: list[Island]
    node_state: dict[str, LiveState]
    checks: list[CrossCheck]
    issues: list[ValidationIssue]
    summary: dict[str, int]


# ------------------------------------------------------------------- mappers
def _device_out(device: Device) -> DeviceOut:
    return DeviceOut(
        id=device.id,
        ln=device.ln,
        role=str(device.role),
        name=device.name,
        short_name=device.short_name,
        state=device.state,
        quality=device.position.quality,
        value=device.position.value,
        source_timestamp=(
            device.position.source_timestamp.isoformat()
            if device.position.source_timestamp
            else None
        ),
        source_ref=device.source_ref,
        terminals=[t.node_id for t in device.terminals],
    )


def _bay_out(bay: Bay, graph: StationGraph) -> BayOut:
    return BayOut(
        id=bay.id,
        name=bay.name,
        voltage_level=bay.voltage_level,
        bay_type=str(bay.bay_type),
        template_id=bay.template_id,
        device_count=len(graph.devices_of(bay.id)),
        is_live=bay.is_live.value if isinstance(bay.is_live.value, bool) else None,
        is_live_quality=bay.is_live.quality,
        logical_nodes=list(bay.logical_nodes),
        issues=list(bay.issues),
    )


def _busbar_out(busbar: Busbar) -> BusbarOut:
    return BusbarOut(
        id=busbar.id,
        name=busbar.name,
        voltage_level=busbar.voltage_level,
        index=busbar.index,
        is_live=busbar.is_live.value if isinstance(busbar.is_live.value, bool) else None,
        quality=busbar.is_live.quality,
        inferred=busbar.inferred,
    )


def _project_out(row: ProjectRow) -> ProjectOut:
    active = store.project is not None and store.project.id == row.id
    return ProjectOut(
        id=row.id,
        name=row.name,
        opcua_url=row.opcua_url,
        created_at=row.created_at,
        updated_at=row.updated_at,
        has_snapshot=row.has_snapshot,
        model_name=row.model_name,
        model_version=row.model_version,
        captured_at=row.captured_at,
        snapshot_saved_at=row.snapshot_saved_at,
        active=active,
    )


# ------------------------------------------------------------------ endpoints
@app.get("/api/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(
        ok=store.loaded,
        loaded=store.loaded,
        source=store.source_label,
        load_error=store.load_error,
        load_seconds=store.load_seconds,
        project_id=store.project.id if store.project else None,
        project_name=store.project.name if store.project else None,
    )


@app.post("/api/reload", response_model=HealthOut)
async def reload_station() -> HealthOut:
    """Re-read the current source: the active project's DataServer (updating
    its snapshot), else BI_SOURCE. Writes nothing to OneATS (I1)."""
    await store.try_reload()
    return await health()


# ------------------------------------------------------------------- projects
# All POST/DELETE endpoints below write only to the local SQLite store.
# Toward OneATS everything remains read-only (AGENTS.md I1) — enforced by
# tools/check.py scanning for write calls, not by trusting this comment.
@app.get("/api/projects", response_model=list[ProjectOut])
async def projects() -> list[ProjectOut]:
    return [_project_out(p) for p in store.projects.list()]


@app.post("/api/projects", response_model=ProjectLoadOut)
async def create_project(body: ProjectCreateIn) -> ProjectLoadOut:
    """Create a project and immediately try to browse its DataServer.

    Success stores a snapshot and makes the project active. Failure keeps the
    project so the URL can be corrected and retried with /refresh.
    """
    name = body.name.strip()
    url = body.opcua_url.strip()
    if not name:
        raise InvalidInputError("project name must not be empty")
    if not url.startswith("opc.tcp://"):
        raise InvalidInputError("the DataServer address must start with opc.tcp://", opcua_url=url)
    if store.projects.get_by_name(name) is not None:
        raise ConflictError(f"a project named {name!r} already exists", name=name)
    row = store.projects.create(name, url)
    return await _load_project(row.id, live=True)


@app.post("/api/projects/{project_id}/open", response_model=ProjectLoadOut)
async def open_project(project_id: int) -> ProjectLoadOut:
    """Make this project current. Renders from its snapshot when one exists;
    only its first-ever open touches the DataServer."""
    return await _load_project(project_id, live=False)


@app.post("/api/projects/{project_id}/refresh", response_model=ProjectLoadOut)
async def refresh_project(project_id: int) -> ProjectLoadOut:
    """Browse the project's DataServer live and replace its snapshot."""
    return await _load_project(project_id, live=True)


@app.delete("/api/projects/{project_id}", response_model=list[ProjectOut])
async def delete_project(project_id: int) -> list[ProjectOut]:
    """Remove a project and its snapshot. Returns the remaining projects."""
    was_active = store.project is not None and store.project.id == project_id
    if not store.projects.delete(project_id):
        raise NotFoundError(f"no such project: {project_id}", project_id=project_id)
    if was_active:
        store.unload()
    return await projects()


async def _load_project(project_id: int, *, live: bool) -> ProjectLoadOut:
    row = store.projects.get(project_id)
    if row is None:
        raise NotFoundError(f"no such project: {project_id}", project_id=project_id)
    error: str | None = None
    try:
        if live:
            await store.refresh_project(project_id)
        else:
            await store.open_project(project_id)
    except NotFoundError:
        raise
    except Exception as exc:  # reported in the response body, not raised
        error = f"{type(exc).__name__}: {exc}"
        log.error("project load failed", project=row.name, error=error)
    fresh = store.projects.get(project_id) or row
    return ProjectLoadOut(project=_project_out(fresh), ok=error is None, error=error)


@app.get("/api/station", response_model=StationOut)
async def station() -> StationOut:
    graph = store.graph
    bound = sum(1 for d in graph.devices if d.position.quality is Quality.GOOD)
    determined = sum(1 for d in graph.devices if d.state is not SwitchState.UNDETERMINED)
    return StationOut(
        name=graph.name,
        model_version=graph.model_version,
        captured_at=graph.captured_at.isoformat() if graph.captured_at else None,
        source=graph.source,
        voltage_levels=list(graph.voltage_levels),
        bay_count=len(graph.bays),
        device_count=len(graph.devices),
        busbar_count=len(graph.busbars),
        node_count=len(graph.nodes),
        load_seconds=store.load_seconds,
        coverage={
            "devices": len(graph.devices),
            "position_good": bound,
            "position_determined": determined,
        },
        issues=list(graph.all_issues()),
    )


@app.get("/api/bays", response_model=list[BayOut])
async def bays() -> list[BayOut]:
    graph = store.graph
    return [_bay_out(b, graph) for b in graph.bays]


@app.get("/api/bays/{bay_id}", response_model=BayDetailOut)
async def bay_detail(bay_id: str) -> BayDetailOut:
    graph = store.graph
    bay = graph.bay(bay_id)
    if bay is None:
        raise NotFoundError(f"no such bay: {bay_id}", bay_id=bay_id)
    return BayDetailOut(
        **_bay_out(bay, graph).model_dump(),
        devices=[_device_out(d) for d in graph.devices_of(bay_id)],
    )


@app.get("/api/busbars", response_model=list[BusbarOut])
async def busbars() -> list[BusbarOut]:
    return [_busbar_out(b) for b in store.graph.busbars]


@app.get("/api/energization", response_model=EnergizationOut)
async def energization() -> EnergizationOut:
    """Solve which sections are live from the switch positions we can read.

    Seeded from the busbars the station measures, spread across closed devices
    and through paired transformers, then compared against the bay-level
    `IsLive` OneATS publishes. Disagreements are returned, not hidden (I7).
    """
    result = solve_energization(store.graph)
    states = [island.state for island in result.islands]
    return EnergizationOut(
        islands=list(result.islands),
        node_state={n.node_id: n.state for n in result.nodes},
        checks=list(result.checks),
        issues=list(result.issues),
        summary={
            "islands": len(result.islands),
            **{state.lower(): states.count(state) for state in LiveState},
            "compared": sum(1 for c in result.checks if c.agrees is not None),
            "mismatched": len(result.mismatches),
        },
    )


@app.get("/api/diagram", response_model=StationView)
async def station_diagram() -> StationView:
    """The whole station in one drawing — every voltage level, stacked."""
    return layout_station(store.graph)


@app.get("/api/diagram/{voltage_level}", response_model=DiagramView)
async def diagram(voltage_level: str) -> DiagramView:
    graph = store.graph
    if voltage_level not in graph.voltage_levels:
        raise NotFoundError(
            f"no such voltage level: {voltage_level}",
            voltage_level=voltage_level,
            available=list(graph.voltage_levels),
        )
    return layout_voltage_level(graph, voltage_level)


# ------------------------------------------------------------------- frontend
# Serves frontend/dist when the SPA has been built, otherwise the single-file
# dev viewer. See ADR-0009.
_frontend = settings.frontend_dir
if _frontend is not None:
    if (_frontend / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_frontend / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        assert _frontend is not None
        return FileResponse(_frontend / "index.html")
