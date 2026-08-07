"""The station as it is structured: bays, devices, busbars, what is energised.

These change when the station is browsed again, not from moment to moment —
what moves is in `routers/live.py`, and what it looks like is in
`routers/diagram.py`.
"""

from __future__ import annotations

from fastapi import APIRouter

from blackinterface.api.authz import requires
from blackinterface.api.deps import get_store
from blackinterface.api.mappers import bay_out, busbar_out, device_out, energization_out, issue_out
from blackinterface.api.schemas import (
    BayDetailOut,
    BayOut,
    BusbarOut,
    EnergizationOut,
    StationOut,
)
from blackinterface.domain.authz import Capability
from blackinterface.domain.models import Quality, SwitchState
from blackinterface.errors import NotFoundError

router = APIRouter()

# Everything here describes the station itself, so it all sits behind one
# capability. Spelled out per route rather than once on the router: a permission
# a whole file shares by accident is exactly what ADR-0016 asks to be able to
# read off each facet, and `tools/check.py` reads these decorators literally.


@router.get(
    "/api/station",
    response_model=StationOut,
    dependencies=[requires(Capability.STATION_READ)],
)
async def station() -> StationOut:
    store = get_store()
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
        issues=[issue_out(i) for i in graph.all_issues()],
    )


@router.get(
    "/api/bays",
    response_model=list[BayOut],
    dependencies=[requires(Capability.STATION_READ)],
)
async def bays() -> list[BayOut]:
    graph = get_store().graph
    return [bay_out(b, graph) for b in graph.bays]


@router.get(
    "/api/bays/{bay_id}",
    response_model=BayDetailOut,
    dependencies=[requires(Capability.STATION_READ)],
)
async def bay_detail(bay_id: str) -> BayDetailOut:
    graph = get_store().graph
    bay = graph.bay(bay_id)
    if bay is None:
        raise NotFoundError(f"no such bay: {bay_id}", bay_id=bay_id)
    return BayDetailOut(
        **bay_out(bay, graph).model_dump(),
        devices=[device_out(d) for d in graph.devices_of(bay_id)],
    )


@router.get(
    "/api/busbars",
    response_model=list[BusbarOut],
    dependencies=[requires(Capability.STATION_READ)],
)
async def busbars() -> list[BusbarOut]:
    return [busbar_out(b) for b in get_store().graph.busbars]


@router.get(
    "/api/energization",
    response_model=EnergizationOut,
    dependencies=[requires(Capability.STATION_READ)],
)
async def energization() -> EnergizationOut:
    """Solve which sections are live from the switch positions we can read.

    Seeded from the busbars the station measures, spread across closed devices
    and through paired transformers, then compared against the bay-level
    `IsLive` OneATS publishes. Disagreements are returned, not hidden (I7).
    """
    return energization_out(get_store().graph)
