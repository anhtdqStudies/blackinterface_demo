"""End-to-end topology build, offline, from the committed DEMO_SAS fixture.

These numbers are the acceptance criteria for milestone M1 ("point at a
DataServer, get a working model"). They came from an independent measurement
run, not from this code: 80 switching devices, 100 % position bound, 13 bays.
"""

from __future__ import annotations

import pytest

from blackinterface.domain.models import (
    BayType,
    NodeKind,
    PointSample,
    Quality,
    Severity,
    StationGraph,
    SwitchState,
)
from blackinterface.domain.observation import BayObs, LogicalNodeObs, StationObs
from blackinterface.domain.topology import build_station

MEASURED_DEVICE_COUNT = 80  # docs/30-integration/oneats-dataserver.md, 2026-08-04
MEASURED_BAY_COUNT = 13


def test_every_bay_is_classified(station: StationGraph) -> None:
    unknown = [b.id for b in station.bays if b.bay_type is BayType.UNKNOWN]
    assert unknown == []


def test_every_bay_gets_a_template(station: StationGraph) -> None:
    assert [b.id for b in station.bays if b.template_id is None] == []


def test_bay_count_matches_measurement(station: StationGraph) -> None:
    assert len(station.bays) == MEASURED_BAY_COUNT


def test_device_count_matches_independent_measurement(station: StationGraph) -> None:
    """The templates must place every switching device - no more, no fewer."""
    assert len(station.devices) == MEASURED_DEVICE_COUNT


def test_no_switching_device_is_left_out_of_the_graph(station: StationGraph) -> None:
    """`slot_unmapped` means a real disconnector exists but has no place in the graph."""
    unmapped = [i for i in station.all_issues() if i.code == "slot_unmapped"]
    assert unmapped == []


def test_no_errors_only_the_known_22kv_busbar_warning(station: StationGraph) -> None:
    errors = [i for i in station.all_issues() if i.severity is Severity.ERROR]
    assert errors == []
    warnings = {i.code for i in station.all_issues() if i.severity is Severity.WARNING}
    assert warnings <= {"busbar_not_in_source"}


def test_every_terminal_points_at_a_real_node(station: StationGraph) -> None:
    known = {n.id for n in station.nodes}
    dangling = [
        f"{d.id}[{t.seq}] -> {t.node_id}"
        for d in station.devices
        for t in d.terminals
        if t.node_id not in known
    ]
    assert dangling == []


def test_every_device_has_exactly_two_terminals(station: StationGraph) -> None:
    assert [d.id for d in station.devices if len(d.terminals) != 2] == []


def test_busbars_carry_their_voltage_level(station: StationGraph) -> None:
    assert {b.id: b.voltage_level for b in station.busbars if not b.inferred} == {
        "BB11": "110kV",
        "BB12": "110kV",
        "BB19": "110kV",
        "BB21": "220kV",
        "BB22": "220kV",
        "BB29": "220kV",
    }


def test_missing_busbar_is_flagged_not_hidden(station: StationGraph) -> None:
    """22 kV has no busbar object in DEMO_SAS. The model must say so out loud."""
    inferred = [b for b in station.busbars if b.inferred]
    assert [b.voltage_level for b in inferred] == ["22kV"]
    assert any(i.code == "busbar_not_in_source" for i in station.all_issues())


def test_position_is_bound_for_every_device(station: StationGraph) -> None:
    """Measured 2026-08-04: 80/80 positions readable with quality GOOD."""
    unbound = [d.id for d in station.devices if d.position.quality is not Quality.GOOD]
    assert unbound == []


def test_every_position_carries_a_source_timestamp(station: StationGraph) -> None:
    assert [d.id for d in station.devices if d.position.source_timestamp is None] == []


def test_line_bay_matches_the_measured_switching_state(station: StationGraph) -> None:
    """D03 as read on 2026-08-04: on busbar 1, connected to the line, in service."""
    states = {d.ln: d.state for d in station.devices_of("D03")}
    assert states["XSWI1"] is SwitchState.CLOSED
    assert states["XSWI2"] is SwitchState.OPEN
    assert states["XSWI9"] is SwitchState.OPEN
    assert states["XSWI7"] is SwitchState.CLOSED
    assert states["XCBR1"] is SwitchState.CLOSED


def test_evn_designations_survive_the_import(station: StationGraph) -> None:
    names = {d.ln: d.name for d in station.devices_of("D03")}
    assert names["XCBR1"] == "271"
    assert names["XSWI1"] == "271-1"
    assert names["XSWI71"] == "271-75"


def test_busbar_protection_produces_no_devices(station: StationGraph) -> None:
    for bay_id in ("DBB", "EBB"):
        assert station.devices_of(bay_id) == ()


def test_earth_node_is_shared(station: StationGraph) -> None:
    earth = [n for n in station.nodes if n.kind is NodeKind.EARTH]
    assert len(earth) == 1


def test_build_is_deterministic(observation: StationObs) -> None:
    assert build_station(observation) == build_station(observation)


# ------------------------------------------------------ quality gate (I2)
def _one_bay(position_value: object, quality: Quality) -> StationGraph:
    return build_station(
        StationObs(
            name="T",
            bays=(
                BayObs(
                    id="X01",
                    voltage_level="220kV",
                    logical_nodes=tuple(
                        LogicalNodeObs(
                            ln=ln,
                            position=PointSample(value=position_value, quality=quality),
                        )
                        for ln in ("XCBR1", "XSWI1", "XSWI2", "XSWI7", "XSWI71")
                    ),
                ),
            ),
        )
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0, SwitchState.INTERMEDIATE),
        (1, SwitchState.OPEN),
        (2, SwitchState.CLOSED),
        (3, SwitchState.UNDETERMINED),  # Dbpos BAD is not a position
        (None, SwitchState.UNDETERMINED),
        ("2", SwitchState.UNDETERMINED),  # a string is not a Dbpos
    ],
)
def test_dbpos_mapping(raw: object, expected: SwitchState) -> None:
    graph = _one_bay(raw, Quality.GOOD)
    assert graph.devices_of("X01")[0].state is expected


@pytest.mark.parametrize("quality", [Quality.BAD, Quality.UNCERTAIN, Quality.MISSING])
def test_bad_quality_never_becomes_a_position(quality: Quality) -> None:
    """AGENTS.md I2: a CLOSED value with bad quality must not read as CLOSED."""
    graph = _one_bay(2, quality)
    assert all(d.state is SwitchState.UNDETERMINED for d in graph.devices_of("X01"))


def test_unknown_bay_type_is_reported_not_guessed() -> None:
    graph = build_station(
        StationObs(
            name="T",
            bays=(
                BayObs(
                    id="Z99",
                    voltage_level="220kV",
                    logical_nodes=(LogicalNodeObs(ln="MMXU1"),),
                ),
            ),
        )
    )
    bay = graph.bay("Z99")
    assert bay is not None
    assert bay.bay_type is BayType.UNKNOWN
    assert bay.template_id is None
    assert [i.code for i in bay.issues] == ["bay_type_unknown"]


def test_missing_required_slot_is_an_error() -> None:
    """A line bay without its breaker must fail loudly, not build a half graph."""
    graph = build_station(
        StationObs(
            name="T",
            bays=(
                BayObs(
                    id="Y01",
                    voltage_level="220kV",
                    logical_nodes=tuple(
                        LogicalNodeObs(ln=ln) for ln in ("XCBR1", "XSWI1", "XSWI7")
                    ),
                ),
            ),
        )
    )
    bay = graph.bay("Y01")
    assert bay is not None
    graph_no_breaker = build_station(
        StationObs(
            name="T",
            bays=(
                BayObs(
                    id="Y02",
                    voltage_level="220kV",
                    logical_nodes=(
                        LogicalNodeObs(ln="XCBR1"),
                        LogicalNodeObs(ln="XSWI7"),
                        LogicalNodeObs(ln="XSWI71"),
                    ),
                ),
            ),
        )
    )
    bay2 = graph_no_breaker.bay("Y02")
    assert bay2 is not None
    assert bay2.bay_type is BayType.LINE
    assert [i.code for i in bay2.issues] == ["slot_missing"]  # XSWI1 is required


# --------------------------------------------------------------- transformers
def test_transformer_pairing_is_evidence_backed(station: StationGraph) -> None:
    """Two evidence sources, measured 2026-08-05 on the DEMO_SAS fixture:
    'AT1' in the BAY/Name of D01 and E07, and EVN breaker numbering for the
    tertiary — J01's breaker is 431 (`<voltage 4=22kV>3<AT #1>`) while its
    BAY/Name is empty. HV first; couplers (212) and lines (271) must not join.
    """
    assert [(t.id, t.bay_ids) for t in station.transformers] == [("AT1", ("D01", "E07", "J01"))]


def test_bay_display_names_come_from_the_bay_logical_node(station: StationGraph) -> None:
    names = {b.id: b.name for b in station.bays}
    assert names["D01"] == "AT1 Incoming"
    assert names["D03"] == "Ben Cat"
    assert names["E07"] == "AT1 Incoming"
    # A bay without a BAY/Name keeps its id — never an empty caption.
    assert names["J01"] == "J01"
