"""Diagram layout: deterministic geometry, nothing invented (AGENTS.md I4)."""

from __future__ import annotations

import math

import pytest

from blackinterface.diagram.layout import Point, layout_station, layout_voltage_level
from blackinterface.domain.models import BayType, StationGraph

LEVELS = ("220kV", "110kV", "22kV")


@pytest.mark.parametrize("level", LEVELS)
def test_layout_produces_finite_geometry(station: StationGraph, level: str) -> None:
    view = layout_voltage_level(station, level)
    for symbol in view.symbols:
        assert math.isfinite(symbol.x) and math.isfinite(symbol.y), symbol.device_id
    for edge in view.edges:
        assert all(math.isfinite(p.x) and math.isfinite(p.y) for p in edge.points), edge.id


@pytest.mark.parametrize("level", LEVELS)
def test_every_device_is_drawn_exactly_once(station: StationGraph, level: str) -> None:
    view = layout_voltage_level(station, level)
    drawn = [s.device_id for s in view.symbols]
    expected = [
        d.id for b in station.bays if b.voltage_level == level for d in station.devices_of(b.id)
    ]
    assert sorted(drawn) == sorted(expected)
    assert len(drawn) == len(set(drawn))


def test_all_devices_appear_across_all_levels(station: StationGraph) -> None:
    drawn = {s.device_id for level in LEVELS for s in layout_voltage_level(station, level).symbols}
    assert drawn == {d.id for d in station.devices}


def test_rails_exist_for_every_busbar_at_the_level(station: StationGraph) -> None:
    view = layout_voltage_level(station, "220kV")
    assert {r.busbar_id for r in view.rails} == {"BB21", "BB22", "BB29"}


def test_transfer_busbar_is_drawn_on_the_terminal_side(station: StationGraph) -> None:
    """Main busbars above the bay, transfer busbar below it, terminal below that.

    Not a style choice: `-9` connects the transfer busbar to the LINE-side node,
    so drawing it beside the main busbars would imply a connection that does not
    exist. Matches OneATS Grid Designer.
    """
    view = layout_voltage_level(station, "220kV")
    rails = {r.busbar_id: r.y for r in view.rails}
    assert rails["BB21"] < rails["BB22"] < rails["BB29"]

    d03 = {s.ln: s.y for s in view.symbols if s.bay_id == "D03"}
    assert rails["BB22"] < d03["XCBR1"] < d03["XSWI7"] < rails["BB29"]

    terminal = next(t for t in view.terminals if t.node_id == "D03.n_line")
    assert terminal.y > rails["BB29"]


def test_transfer_selector_sits_between_its_node_and_its_rail(station: StationGraph) -> None:
    view = layout_voltage_level(station, "220kV")
    rail = next(r.y for r in view.rails if r.busbar_id == "BB29")
    d03 = {s.ln: s.y for s in view.symbols if s.bay_id == "D03"}
    assert d03["XSWI7"] < d03["XSWI9"] < rail


def test_columns_do_not_overlap(station: StationGraph) -> None:
    xs = [c.x for c in layout_voltage_level(station, "220kV").columns]
    assert xs == sorted(xs)
    assert len(xs) == len(set(xs))


def test_busbar_protection_gets_no_column(station: StationGraph) -> None:
    """DBB/EBB have no switching devices; drawing an empty column would mislead."""
    columns = {c.bay_id for c in layout_voltage_level(station, "220kV").columns}
    assert "DBB" not in columns
    assert columns == {
        b.id
        for b in station.bays
        if b.voltage_level == "220kV" and b.bay_type is not BayType.BUSBAR_PROTECTION
    }


def test_line_bay_has_an_external_terminal(station: StationGraph) -> None:
    view = layout_voltage_level(station, "220kV")
    assert any(t.node_id.startswith("D03.") for t in view.terminals)


def test_edges_connect_to_the_symbol_they_belong_to(station: StationGraph) -> None:
    view = layout_voltage_level(station, "220kV")
    position = {s.device_id: (s.x, s.y) for s in view.symbols}
    for edge in view.edges:
        if edge.device_id is None:
            continue
        start = edge.points[0]
        assert (start.x, start.y) == position[edge.device_id], edge.id


def test_layout_is_deterministic(station: StationGraph) -> None:
    assert layout_voltage_level(station, "220kV") == layout_voltage_level(station, "220kV")


# --------------------------------------------------------------- busbar lanes
# The drawing has to distinguish "on busbar 1" from "on busbar 2". These tests
# pin the geometry that makes that readable; without them a refactor can quietly
# put both isolators back on one vertical, which shows a path through both
# busbars regardless of what the isolators are actually doing.


def _on_segment(point: tuple[float, float], a: Point, b: Point) -> bool:
    """Segments here are axis-aligned, so this stays exact — no float slop."""
    x, y = point
    if a.x == b.x == x:
        return min(a.y, b.y) <= y <= max(a.y, b.y)
    if a.y == b.y == y:
        return min(a.x, b.x) <= x <= max(a.x, b.x)
    return False


@pytest.mark.parametrize("level", ("220kV", "110kV"))
def test_no_conductor_runs_through_another_devices_busbar_connection(
    station: StationGraph, level: str
) -> None:
    """The bug this pins: -1 and -2 drawn on one vertical.

    The busbar-1 drop then passed straight through the point where busbar 2 is
    joined, so the picture showed a continuous path across both busbars whatever
    the isolators were doing. A conductor may cross a busbar; it may not cross
    somebody else's junction dot.
    """
    view = layout_voltage_level(station, level)
    assert view.junctions, "expected busbar connections at this level"

    for junction in view.junctions:
        owner = junction.id.rsplit(".", 1)[0]  # "D03.XSWI1.0" -> "D03.XSWI1"
        bay = owner.split(".")[0]
        for edge in view.edges:
            if not edge.id.startswith(f"{bay}.") or edge.id.startswith(f"{owner}."):
                continue
            for a, b in zip(edge.points, edge.points[1:], strict=False):
                assert not _on_segment((junction.x, junction.y), a, b), (
                    f"{edge.id} runs through {owner}'s busbar connection"
                )


def test_every_busbar_connection_is_marked_and_nothing_else_is(
    station: StationGraph,
) -> None:
    """A dot means connected. The bay spine crosses rails it is not on."""
    view = layout_voltage_level(station, "220kV")
    rail_y = {r.y for r in view.rails}
    dots = {(j.x, j.y) for j in view.junctions}

    d03 = {s.ln: s for s in view.symbols if s.bay_id == "D03"}
    for ln, busbar in (("XSWI1", "BB21"), ("XSWI2", "BB22"), ("XSWI9", "BB29")):
        y = next(r.y for r in view.rails if r.busbar_id == busbar)
        assert (d03[ln].x, y) in dots, f"{ln} should be dotted onto {busbar}"

    # The line tail runs down the column and passes BB29 without joining it.
    column_x = next(c.x for c in view.columns if c.bay_id == "D03")
    for y in rail_y:
        assert (column_x, y) not in dots


def test_transfer_isolator_does_not_share_the_column_with_the_line_tail(
    station: StationGraph,
) -> None:
    """Otherwise the tail's crossing of BB29 lands on -9's connection point."""
    view = layout_voltage_level(station, "220kV")
    column_x = next(c.x for c in view.columns if c.bay_id == "D03")
    xswi9 = next(s for s in view.symbols if s.bay_id == "D03" and s.ln == "XSWI9")
    assert xswi9.x != column_x


# ------------------------------------------------------------- whole station
def test_station_stacks_levels_with_the_tertiary_band_in_the_middle(
    station: StationGraph,
) -> None:
    """Voltage order would give 220/110/22, but the 22kV level holds nothing
    except AT1's tertiary bay, so it tucks into the middle strip right under
    the transformer — the way the Grid Designer sheet draws it."""
    view = layout_station(station)
    assert [s.voltage_level for s in view.sections] == ["220kV", "22kV", "110kV"]
    tops = [s.top for s in view.sections]
    assert tops == sorted(tops)


def test_top_band_is_mirrored_so_the_busbar_groups_face_each_other(
    station: StationGraph,
) -> None:
    """220 kV busbars at the bottom of their band, 110 kV at the top of theirs.
    The tertiary band is mirrored too: its terminal points up at AT1 and its
    inferred busbar sinks to the bottom of the band."""
    view = layout_station(station)
    hv = next(s for s in view.sections if s.voltage_level == "220kV")
    mv = next(s for s in view.sections if s.voltage_level == "110kV")
    tv = next(s for s in view.sections if s.voltage_level == "22kV")
    assert hv.flipped and tv.flipped and not mv.flipped

    rails = {r.busbar_id: r.y for r in view.rails}
    # Mirrored: the transfer busbar is now above the main pair, and the main
    # pair is the closest thing to the next band down.
    assert rails["BB29"] < rails["BB22"] < rails["BB21"] < hv.bottom
    assert mv.top < rails["BB11"] < rails["BB12"] < rails["BB19"]
    assert rails["BB21"] < rails["BB41"] < rails["BB11"]

    j01_terminal = next(t for t in view.terminals if t.node_id.startswith("J01"))
    j01_symbols = [s.y for s in view.symbols if s.bay_id == "J01"]
    assert j01_terminal.y < min(j01_symbols) < rails["BB41"]


def test_station_terminals_point_away_from_the_busbars(station: StationGraph) -> None:
    view = layout_station(station)
    hv_rail = max(r.y for r in view.rails if r.busbar_id.startswith("BB2"))
    for terminal in view.terminals:
        if terminal.node_id.startswith(("D0", "D1")):
            assert terminal.flipped
            assert terminal.y < hv_rail


def test_station_draws_every_device_once(station: StationGraph) -> None:
    view = layout_station(station)
    drawn = [s.device_id for s in view.symbols]
    assert sorted(drawn) == sorted(d.id for d in station.devices)


def test_station_layout_is_deterministic(station: StationGraph) -> None:
    assert layout_station(station) == layout_station(station)


# --------------------------------------------------------------- transformers
def test_paired_transformer_is_drawn_between_its_two_bands(station: StationGraph) -> None:
    """AT1 couples D01 (220kV), E07 (110kV) and the tertiary J01 (22kV)."""
    view = layout_station(station)
    assert [t.id for t in view.transformers] == ["AT1"]
    at1 = view.transformers[0]
    assert at1.bay_ids == ("D01", "E07", "J01")

    hv = next(s for s in view.sections if s.voltage_level == "220kV")
    mv = next(s for s in view.sections if s.voltage_level == "110kV")
    assert hv.bottom < at1.y < mv.top, "the transformer sits in the gap between its bands"


def test_transformer_link_edges_run_from_both_winding_terminals(
    station: StationGraph,
) -> None:
    view = layout_station(station)
    terminals = {t.node_id.split(".")[0]: t for t in view.terminals}
    at1 = view.transformers[0]
    for side, bay_id in zip(("hv", "lv"), at1.bay_ids[:2], strict=True):
        edge = next(e for e in view.edges if e.id == f"link.AT1.{side}")
        start, end = edge.points[0], edge.points[-1]
        terminal = terminals[bay_id]
        assert (start.x, start.y) == (terminal.x, terminal.y)
        assert end.y == at1.y
        assert abs(end.x - at1.x) < 30, "the link ends at the transformer symbol"


def test_linked_terminals_are_marked_and_others_are_not(station: StationGraph) -> None:
    view = layout_station(station)
    linked = {t.node_id.split(".")[0] for t in view.terminals if t.linked}
    assert linked == {"D01", "E07", "J01"}


def test_tertiary_link_stays_in_the_middle_strip_next_to_the_symbol(
    station: StationGraph,
) -> None:
    """With the 22kV band tucked under AT1, the tertiary link is short: from
    J01's upward terminal, up its own lane, into the corridor below the
    symbol, ending at the bottom circle. The whole route stays between the
    220kV and 22kV bands' contents — no trip to the canvas edge."""
    view = layout_station(station)
    at1 = view.transformers[0]
    edge = next(e for e in view.edges if e.id == "link.AT1.w3")

    terminal = next(t for t in view.terminals if t.node_id.startswith("J01"))
    start, end = edge.points[0], edge.points[-1]
    assert (start.x, start.y) == (terminal.x, terminal.y)
    assert (end.x, end.y) == (at1.x, at1.y + 30.0), "meets the tertiary circle"

    hv = next(s for s in view.sections if s.voltage_level == "220kV")
    tv = next(s for s in view.sections if s.voltage_level == "22kV")
    for p in edge.points:
        assert hv.bottom < p.y < tv.bottom, "the route never leaves the middle strip"


def test_transformer_link_never_crosses_a_junction_dot(station: StationGraph) -> None:
    """The link lane crosses rails; a dot there would claim a busbar connection."""
    view = layout_station(station)
    dots = {(j.x, j.y) for j in view.junctions}
    for edge in view.edges:
        if not edge.id.startswith("link."):
            continue
        for p in edge.points:
            assert (p.x, p.y) not in dots
