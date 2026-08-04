"""Topology pinned to OneATS's own energisation logic.

`document/DEMO_SAS-MODELExplorer.xlsx` exports the `SAS_SIM.CheckLiveState`
Lua program, which OneATS uses to compute IsLive. That script is independent
evidence of how the station is actually wired, and it is the only such evidence
we have — the DataServer carries no connectivity, and the SLD extract is known
to be wrong.

Each test below quotes the line of Lua it encodes. If ATS changes the station,
these fail and someone has to look at the model export again.

Found 2026-08-04. It corrected a real defect: v1 of T1/T2 attached XSWI9 to the
busbar side, which would have reported a line fed from the transfer busbar as
dead.
"""

from __future__ import annotations

from blackinterface.domain.models import DeviceRole, StationGraph


def _nodes(graph: StationGraph, bay: str, ln: str) -> set[str]:
    device = graph.device(f"{bay}.{ln}")
    assert device is not None, f"{bay}.{ln} missing"
    return {t.node_id for t in device.terminals}


def test_line_transfer_selector_bypasses_the_breaker(station: StationGraph) -> None:
    """E01L = ... or (C19L and 171-9C)

    One term, no breaker in it: the transfer busbar reaches the line through
    -9 alone. So -9 and -7 must share the line-side node.
    """
    for bay in ("D03", "D04", "E01", "E02"):
        line_side = _nodes(station, bay, "XSWI9") & _nodes(station, bay, "XSWI7")
        assert line_side, f"{bay}: XSWI9 does not touch the line side of XSWI7"
        assert f"{bay}.n_line" in line_side


def test_line_transfer_selector_is_not_on_the_busbar_side(station: StationGraph) -> None:
    """The defect this file exists to prevent."""
    for bay in ("D03", "D04", "E01", "E02"):
        assert f"{bay}.n_bb" not in _nodes(station, bay, "XSWI9")


def test_transformer_transfer_selector_feeds_the_transformer_side(
    station: StationGraph,
) -> None:
    """AT1L = ... or (C29L and 231-9C)"""
    for bay in ("D01", "E07"):
        assert f"{bay}.n_tr" in _nodes(station, bay, "XSWI9")


def test_busbar_selectors_sit_between_busbar_and_breaker(station: StationGraph) -> None:
    """E01L = (((C11L and 171-1C) or (C12L and 171-2C)) and 171C and 171-7C) ...

    -1 and -2 are in series with the breaker, in parallel with each other.
    """
    for bay in ("D03", "D01", "E01", "E07"):
        breaker_side = _nodes(station, bay, "XCBR1")
        for ln in ("XSWI1", "XSWI2"):
            shared = _nodes(station, bay, ln) & breaker_side
            assert shared == {f"{bay}.n_bb"}, f"{bay}.{ln}"


def test_bus_transfer_selector_is_beyond_the_breaker(station: StationGraph) -> None:
    """C29L = ((C21L and 200-1C) or (C22L and 200-2C)) and 200C and 200-9C

    Here -9 IS in series with the breaker, unlike a line bay. Same LN number,
    different electrical position — which is why bay type has to be inferred
    before the template is applied.
    """
    for bay, transfer_busbar in (("D12", "NODE.BB29"), ("E04", "NODE.BB19")):
        transfer = _nodes(station, bay, "XSWI9")
        assert transfer_busbar in transfer
        assert transfer & _nodes(station, bay, "XCBR1") == {f"{bay}.n_b"}


def test_bus_coupler_ties_the_two_main_busbars(station: StationGraph) -> None:
    """D17L = (C21L or C22L) and 212-1C and 212-2C and 212C"""
    for bay, bb1, bb2 in (("D17", "NODE.BB21", "NODE.BB22"), ("E05", "NODE.BB11", "NODE.BB12")):
        assert bb1 in _nodes(station, bay, "XSWI1")
        assert bb2 in _nodes(station, bay, "XSWI2")
        breaker = _nodes(station, bay, "XCBR1")
        assert breaker == {f"{bay}.n_a", f"{bay}.n_b"}


def test_mv_feeder_disconnector_is_upstream_of_the_breaker(station: StationGraph) -> None:
    """J01L = AT1L and 431C and 431-3C, drawn AT1 -> -3 -> 431 -> feeder.

    v1 had the breaker first, putting -3 on the feeder side of it.
    """
    disconnector = station.device("J01.XSWI3")
    breaker = station.device("J01.XCBR1")
    assert disconnector is not None and breaker is not None
    assert disconnector.role is DeviceRole.TRANSFORMER_DISCONNECTOR
    assert "NODE.BB41" in {t.node_id for t in disconnector.terminals}
    assert {t.node_id for t in breaker.terminals} == {"J01.n_a", "J01.n_feed"}
