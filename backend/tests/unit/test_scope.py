"""Scope refs — the vocabulary four layers share (ADR-0010, AGENTS.md I8).

The tests worth having here are about *refusal*. A scope parser that quietly
widens a bad input turns a question about one bay into an answer about the
station, and nothing downstream can tell.
"""

from __future__ import annotations

import pytest

from blackinterface.domain.models import StationGraph
from blackinterface.domain.scope import ScopeKind, ScopeRef, as_scope, bays_in, exists
from blackinterface.errors import InvalidInputError


@pytest.mark.parametrize(
    ("text", "kind", "ident"),
    [
        ("station", ScopeKind.STATION, ""),
        ("vl:220kV", ScopeKind.VOLTAGE_LEVEL, "220kV"),
        ("busbar:BB21", ScopeKind.BUSBAR, "BB21"),
        ("bay:D03", ScopeKind.BAY, "D03"),
        ("device:D03.XCBR1", ScopeKind.DEVICE, "D03.XCBR1"),
        ("point:D03.XCBR1.PosSt", ScopeKind.POINT, "D03.XCBR1.PosSt"),
    ],
)
def test_round_trip(text: str, kind: ScopeKind, ident: str) -> None:
    ref = ScopeRef.parse(text)
    assert (ref.kind, ref.id) == (kind, ident)
    assert ref.ref == text
    assert str(ref) == text


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "bay",  # kind that needs an id, given none
        "bay:",
        "station:D03",  # the station takes no id
        "ngan:D03",  # unknown kind
        "bay:D 03",  # whitespace inside an id
        "bay:.D03",  # ids start with a letter or digit
        "device:D03:XCBR1",  # the separator may not reappear
    ],
)
def test_rejects_rather_than_widens(text: str) -> None:
    with pytest.raises(InvalidInputError):
        ScopeRef.parse(text)


def test_value_equality_so_a_scope_can_key_a_pane() -> None:
    assert ScopeRef.bay("D03") == ScopeRef.parse("bay:D03")
    assert len({ScopeRef.bay("D03"), ScopeRef.parse("bay:D03")}) == 1


def test_parent_chain_from_point_to_station() -> None:
    point = ScopeRef.parse("point:D03.XCBR1.PosSt")
    device = point.parent()
    assert device == ScopeRef.device("D03.XCBR1")
    bay = device.parent() if device else None
    assert bay == ScopeRef.bay("D03")
    assert bay is not None and bay.parent() == ScopeRef.station()
    assert ScopeRef.station().parent() is None


def test_containment_is_lexical_and_admits_what_it_cannot_prove() -> None:
    bay = ScopeRef.bay("D03")
    assert bay.contains(ScopeRef.device("D03.XCBR1"))
    assert bay.contains(ScopeRef.parse("point:D03.XCBR1.PosSt"))
    assert not bay.contains(ScopeRef.device("D12.XCBR1"))
    # A prefix that is not a whole segment is not containment.
    assert not ScopeRef.bay("D0").contains(ScopeRef.device("D03.XCBR1"))
    assert ScopeRef.station().contains(ScopeRef.parse("vl:220kV"))
    # Voltage-level membership needs the graph; contains() must not guess it.
    assert not ScopeRef.parse("vl:220kV").contains(ScopeRef.bay("D03"))


def test_as_scope_accepts_both_forms() -> None:
    assert as_scope("bay:D03") == as_scope(ScopeRef.bay("D03"))


# ------------------------------------------------------------- against a graph
def test_exists_matches_the_loaded_station(station: StationGraph) -> None:
    bay = station.bays[0]
    assert exists(station, ScopeRef.station())
    assert exists(station, ScopeRef.bay(bay.id))
    assert exists(station, ScopeRef.voltage_level(bay.voltage_level))
    assert not exists(station, ScopeRef.bay("NOPE"))
    assert not exists(station, ScopeRef.voltage_level("999kV"))


def test_bays_in_narrows_by_voltage_level(station: StationGraph) -> None:
    everything = bays_in(station, ScopeRef.station())
    assert set(everything) == {b.id for b in station.bays}

    level = station.voltage_levels[0]
    subset = bays_in(station, ScopeRef.voltage_level(level))
    assert subset
    assert set(subset) < set(everything)
    assert all(station.bay(b) is not None for b in subset)
    assert {station.bay(b).voltage_level for b in subset if station.bay(b)} == {level}


def test_bays_in_busbar_lists_the_bays_attached_to_it(station: StationGraph) -> None:
    """Attached, not currently fed: a bay whose selector is open is still one of
    the bays that busbar serves. Which of them is live is energization's job."""
    busbar = next(b for b in station.busbars if not b.inferred)
    bays = bays_in(station, ScopeRef.busbar(busbar.id))
    assert bays
    for bay_id in bays:
        bay = station.bay(bay_id)
        assert bay is not None and bay.voltage_level == busbar.voltage_level


def test_bays_in_device_or_point_climbs_to_its_bay(station: StationGraph) -> None:
    device = station.devices[0]
    assert bays_in(station, ScopeRef.device(device.id)) == (device.bay_id,)
    assert bays_in(station, ScopeRef.point(f"{device.id}.PosSt")) == (device.bay_id,)


def test_unknown_scope_yields_no_bays_rather_than_all(station: StationGraph) -> None:
    assert bays_in(station, ScopeRef.bay("NOPE")) == ()
    assert bays_in(station, ScopeRef.busbar("BB99")) == ()
