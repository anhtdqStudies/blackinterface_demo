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
from blackinterface.diagram.layout import DiagramView, layout_voltage_level
from blackinterface.domain.models import (
    Bay,
    Busbar,
    Device,
    Quality,
    StationGraph,
    SwitchState,
    ValidationIssue,
)
from blackinterface.errors import NotFoundError
from blackinterface.logs import configure as configure_logging
from blackinterface.logs import get_logger
from blackinterface.store.db import Database

log = get_logger(__name__)

settings = get_settings()
store = StationStore(settings)
database = Database(settings.db_path)


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
    # A failed load must not take the process down: /api/health has to stay
    # answerable so an operator can see *why* nothing is showing.
    await store.try_reload()
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


# ------------------------------------------------------------------ endpoints
@app.get("/api/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(
        ok=store.loaded,
        loaded=store.loaded,
        source=store.settings.source,
        load_error=store.load_error,
        load_seconds=store.load_seconds,
    )


@app.post("/api/reload", response_model=HealthOut)
async def reload_station() -> HealthOut:
    """Re-read the source. The only non-GET endpoint, and it writes nothing
    to OneATS."""
    await store.try_reload()
    return await health()


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
