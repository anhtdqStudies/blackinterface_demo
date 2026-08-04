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
def test_station_stacks_every_level_highest_first(station: StationGraph) -> None:
    view = layout_station(station)
    assert [s.voltage_level for s in view.sections] == ["220kV", "110kV", "22kV"]
    tops = [s.top for s in view.sections]
    assert tops == sorted(tops)


def test_top_band_is_mirrored_so_the_busbar_groups_face_each_other(
    station: StationGraph,
) -> None:
    """220 kV busbars at the bottom of their band, 110 kV at the top of theirs."""
    view = layout_station(station)
    hv, mv = view.sections[0], view.sections[1]
    assert hv.flipped and not mv.flipped

    rails = {r.busbar_id: r.y for r in view.rails}
    # Mirrored: the transfer busbar is now above the main pair, and the main
    # pair is the closest thing to the 110 kV band.
    assert rails["BB29"] < rails["BB22"] < rails["BB21"] < hv.bottom
    assert mv.top < rails["BB11"] < rails["BB12"] < rails["BB19"]
    assert rails["BB21"] < rails["BB11"]


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
