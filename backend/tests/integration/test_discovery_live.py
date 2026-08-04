"""Live DataServer checks. Skipped unless you ask for them:

    uv run pytest -m live

They exist to catch drift: if OneATS changes its address space, the offline
fixture keeps passing while reality has moved. This is the test that notices.
"""

from __future__ import annotations

import pytest

from blackinterface.domain.models import BayType, Quality, StationGraph
from blackinterface.domain.topology import build_station
from blackinterface.integration.opcua.discovery import discover_station

URL = "opc.tcp://127.0.0.1:48050"

pytestmark = pytest.mark.live


async def _live_graph() -> StationGraph:
    try:
        obs = await discover_station(URL)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"no DataServer at {URL}: {type(exc).__name__}: {exc}")
    return build_station(obs)


async def test_live_discovery_matches_the_committed_fixture(station: StationGraph) -> None:
    """Same station, same graph — whether read live or from the fixture."""
    live = await _live_graph()
    assert {(b.id, b.bay_type) for b in live.bays} == {(b.id, b.bay_type) for b in station.bays}
    assert {d.id for d in live.devices} == {d.id for d in station.devices}
    assert {b.id for b in live.busbars} == {b.id for b in station.busbars}
    assert {(d.id, d.name) for d in live.devices} == {(d.id, d.name) for d in station.devices}


async def test_live_positions_are_bound_and_good() -> None:
    graph = await _live_graph()
    assert graph.model_version
    assert [b.id for b in graph.bays if b.bay_type is BayType.UNKNOWN] == []
    bad = [d.id for d in graph.devices if d.position.quality is not Quality.GOOD]
    assert bad == []
