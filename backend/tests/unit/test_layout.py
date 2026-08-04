"""Diagram layout: deterministic geometry, nothing invented (AGENTS.md I4)."""

from __future__ import annotations

import math

import pytest

from blackinterface.diagram.layout import layout_voltage_level
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
