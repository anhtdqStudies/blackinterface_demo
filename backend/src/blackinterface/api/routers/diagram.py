"""Geometry. Coordinates only — nothing here claims anything about the station.

That is why these two endpoints carry no evidence record (ADR-0013 section 3):
a drawing is not an assertion about plant. The colours are joined on by the
client from `/api/live`, which does carry one.
"""

from __future__ import annotations

from fastapi import APIRouter

from blackinterface.api.authz import requires
from blackinterface.api.deps import get_store
from blackinterface.diagram.layout import (
    DiagramView,
    StationView,
    layout_station,
    layout_voltage_level,
)
from blackinterface.domain.authz import Capability
from blackinterface.errors import NotFoundError

router = APIRouter()


# Geometry carries no evidence, but it still reveals the shape of the station,
# so it is gated the same as everything else that describes it.
@router.get(
    "/api/diagram",
    response_model=StationView,
    dependencies=[requires(Capability.STATION_READ)],
)
async def station_diagram() -> StationView:
    """The whole station in one drawing — every voltage level, stacked."""
    return layout_station(get_store().graph)


@router.get(
    "/api/diagram/{voltage_level}",
    response_model=DiagramView,
    dependencies=[requires(Capability.STATION_READ)],
)
async def diagram(voltage_level: str) -> DiagramView:
    graph = get_store().graph
    if voltage_level not in graph.voltage_levels:
        raise NotFoundError(
            f"no such voltage level: {voltage_level}",
            voltage_level=voltage_level,
            available=list(graph.voltage_levels),
        )
    return layout_voltage_level(graph, voltage_level)
