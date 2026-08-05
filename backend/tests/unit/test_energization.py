"""Energisation: solved from topology, cross-checked against OneATS.

The fixture is DEMO_SAS v654 in a real, non-trivial state — 172 and 112 open,
E02 fed through the transfer busbar, BB29's measurement broken — so most of
these tests are about behaviour the station itself exhibits, not scenarios
invented to make the code look good.
"""

from __future__ import annotations

import pytest

from blackinterface.domain.energization import LiveState, Reason, solve_energization
from blackinterface.domain.models import (
    NodeKind,
    PointSample,
    Quality,
    Severity,
    StationGraph,
)


def with_position(
    station: StationGraph,
    device_id: str,
    *,
    value: int | None,
    quality: Quality = Quality.GOOD,
) -> StationGraph:
    """A copy of the station with one device's measured position replaced."""
    devices = tuple(
        d.model_copy(update={"position": PointSample(value=value, quality=quality)})
        if d.id == device_id
        else d
        for d in station.devices
    )
    return station.model_copy(update={"devices": devices})


def with_busbar_live(
    station: StationGraph,
    busbar_id: str,
    *,
    value: bool | None,
    quality: Quality = Quality.GOOD,
) -> StationGraph:
    busbars = tuple(
        b.model_copy(update={"is_live": PointSample(value=value, quality=quality)})
        if b.id == busbar_id
        else b
        for b in station.busbars
    )
    return station.model_copy(update={"busbars": busbars})


CLOSED, OPEN = 2, 1


# ------------------------------------------------------------ the real station
def test_every_cross_check_agrees_with_oneats(station: StationGraph) -> None:
    """The whole point of seeding from busbars only.

    OneATS derives each bay's `IsLive` from the busbars through its own
    CheckLiveState logic; we derive it from the busbars through our templates
    and the measured switch positions. Two independent paths, same answers —
    that is what makes our topology believable. A failure here means a bay
    template is wrong, and is worth far more than a green test.
    """
    result = solve_energization(station)
    assert result.mismatches == ()
    compared = [c for c in result.checks if c.agrees is not None]
    assert len(compared) >= 7, "the fixture should give us real comparisons, not blanks"
    assert all(c.agrees for c in compared)


def test_transfer_busbar_bypass_energises_the_line_but_not_the_bay(
    station: StationGraph,
) -> None:
    """E02 in the fixture: every switch open except `-9`.

    So the line is live *around* the bay — fed from the transfer busbar BB19,
    bypassing both the breaker and `-7` — while the bay's own busbar side and
    breaker/line section sit dead between open switches. This is the second
    clause of the CheckLiveState Lua (`(C19L and 171-9C)`) and the reason
    T1_LINE v2 moved `XSWI9` to the line side. Getting this wrong would paint a
    live line green.
    """
    result = solve_energization(station)
    assert result.state_of("E02.n_line") is LiveState.LIVE
    assert result.state_of("E02.n_bb") is LiveState.DEAD
    assert result.state_of("E02.n_mid") is LiveState.DEAD


def test_isolated_section_is_dead_with_a_stated_reason(station: StationGraph) -> None:
    """D12 has every switch open, so both its nodes are cut off from everything."""
    result = solve_energization(station)
    islands = {i.id: i for i in result.islands}
    for node_id in ("D12.n_a", "D12.n_b"):
        island = islands[f"ISL.{node_id}"]
        assert island.state is LiveState.DEAD
        assert island.reason is Reason.ISOLATED


def test_unreadable_busbar_measurement_is_unknown_never_dead(
    station: StationGraph,
) -> None:
    """`Subs.BB29.IsLive` returns BadWaitingForInitialData in the fixture.

    A measurement point that exists and cannot be read tells us nothing. The
    one answer that must never come out of that is "dead" (AGENTS.md I2) — see
    docs/40-testing/manual-test-01-topology.md, case 6.
    """
    result = solve_energization(station)
    island = next(i for i in result.islands if "BB29" in i.busbar_ids)
    assert island.state is LiveState.UNKNOWN
    assert island.reason is Reason.NO_MEASUREMENT


def test_transformer_carries_energisation_to_the_22kv_side(station: StationGraph) -> None:
    """Nothing measures the 22 kV side, but AT1's HV winding is live.

    The 22 kV section is energised through the transformer, and the verdict says
    so — `via` names AT1 rather than leaving an unexplained LIVE.
    """
    result = solve_energization(station)
    island = next(i for i in result.islands if "J01" in i.bay_ids)
    assert island.state is LiveState.LIVE
    assert island.reason is Reason.THROUGH_TRANSFORMER
    assert island.via == "AT1"
    # And OneATS agrees, which is the real proof.
    check = next(c for c in result.checks if c.bay_id == "J01")
    assert check.reported is True and check.agrees is True


def test_every_node_gets_a_verdict(station: StationGraph) -> None:
    """No conductor may be left uncoloured — silence is not a state."""
    result = solve_energization(station)
    covered = {n.node_id for n in result.nodes}
    expected = {n.id for n in station.nodes if n.kind is not NodeKind.EARTH}
    assert covered == expected


def test_solver_is_deterministic(station: StationGraph) -> None:
    assert solve_energization(station) == solve_energization(station)


# ----------------------------------------------------- states we have to force
def test_unreadable_switch_spreads_doubt_not_deadness(station: StationGraph) -> None:
    """D12's `-1` sits between the live 220 kV busbar and a dead section.

    Open, it isolates: the section is dead. Unreadable, it *might* be closed —
    so the section might be live, and the only honest answer is UNKNOWN. This
    is the branch that keeps a bad point from turning into a green conductor.
    """
    assert solve_energization(station).state_of("D12.n_a") is LiveState.DEAD

    blinded = with_position(station, "D12.XSWI1", value=None, quality=Quality.BAD)
    result = solve_energization(blinded)
    island = next(i for i in result.islands if "D12.n_a" in i.node_ids)
    assert island.state is LiveState.UNKNOWN
    assert island.reason is Reason.POSSIBLE_VIA_UNCERTAIN
    assert island.via == "D12.XSWI1"


def test_doubt_travels_as_far_as_the_uncertainty_reaches(station: StationGraph) -> None:
    """Two unreadable switches in series: the doubt must not stop at the first.

    D12's `-1` and its breaker both unreadable means the far side of the bay
    could be energised through both. Reporting `n_b` dead because the doubt
    "already stopped" at `n_a` would be exactly the wrong kind of tidy.
    """
    blinded = with_position(station, "D12.XSWI1", value=None, quality=Quality.BAD)
    blinded = with_position(blinded, "D12.XCBR1", value=None, quality=Quality.BAD)
    result = solve_energization(blinded)
    assert result.state_of("D12.n_a") is LiveState.UNKNOWN
    assert result.state_of("D12.n_b") is LiveState.UNKNOWN


def test_intermediate_position_counts_as_unreadable(station: StationGraph) -> None:
    """Dbpos 0 is a device mid-travel, not a device that is open."""
    moving = with_position(station, "D12.XSWI1", value=0)
    assert solve_energization(moving).state_of("D12.n_a") is LiveState.UNKNOWN


def test_closed_earth_switch_marks_its_section_earthed(station: StationGraph) -> None:
    """E02's breaker/line section is dead; earthing it says something stronger."""
    earthed = with_position(station, "E02.XSWI71", value=CLOSED)
    result = solve_energization(earthed)
    island = next(i for i in result.islands if "E02.n_mid" in i.node_ids)
    assert island.state is LiveState.EARTHED
    assert island.earthed_by == ("E02.XSWI71",)


def test_earthing_does_not_bond_two_separate_sections(station: StationGraph) -> None:
    """Both sections earthed still means two conductors, not one.

    Earth switches closed in different bays share the earth grid, but a verdict
    must never travel from one bay to another along it.
    """
    earthed = with_position(station, "E02.XSWI71", value=CLOSED)
    earthed = with_position(earthed, "D12.XSWI11", value=CLOSED)
    result = solve_energization(earthed)
    islands = {n.node_id: n.island_id for n in result.nodes}
    assert islands["E02.n_mid"] != islands["D12.n_a"]


def test_earthing_a_live_section_is_reported_as_a_fault(station: StationGraph) -> None:
    """A closed earth switch on an energised busbar is a fault or bad data.

    Either way it is the operator's business, not something to average away.
    """
    faulted = with_position(station, "D03.XSWI11", value=CLOSED)
    result = solve_energization(faulted)
    codes = [i.code for i in result.issues if i.severity is Severity.ERROR]
    assert "earthed_while_live" in codes
    # Still reported live: the section measures live, and "live" is the safe
    # word to be wrong with.
    assert result.state_of("D03.n_bb") is LiveState.LIVE


def test_busbars_bonded_together_may_not_disagree(station: StationGraph) -> None:
    """BB21 and BB22 are tied into one conductor in the fixture.

    If their measurements then disagree, our topology or a switch position is
    wrong. Reporting the contradiction is the whole value of computing this
    independently; picking a winner quietly would hide it.
    """
    split = with_busbar_live(station, "BB22", value=False)
    result = solve_energization(split)
    conflict = next(i for i in result.issues if i.code == "energization_conflict")
    assert conflict.severity is Severity.ERROR
    assert result.state_of("NODE.BB22") is LiveState.LIVE


def test_a_disagreement_with_oneats_is_reported(station: StationGraph) -> None:
    """Force our answer away from OneATS's and check we say so out loud.

    Opening E02's `-9` cuts its line off from the transfer busbar, so we
    compute DEAD while the fixture's `E02.IsLive` still says True.
    """
    cut = with_position(station, "E02.XSWI9", value=OPEN)
    result = solve_energization(cut)
    check = next(c for c in result.checks if c.bay_id == "E02")
    assert check.computed is LiveState.DEAD
    assert check.reported is True
    assert check.agrees is False
    assert result.mismatches == (check,)
    assert [i.code for i in result.issues if i.subject == "E02"] == ["energization_mismatch"]


def test_unknown_is_never_counted_as_agreement(station: StationGraph) -> None:
    """An UNKNOWN verdict cannot confirm or contradict anything."""
    blinded = with_position(station, "E02.XSWI9", value=None, quality=Quality.BAD)
    result = solve_energization(blinded)
    check = next(c for c in result.checks if c.bay_id == "E02")
    assert check.computed is LiveState.UNKNOWN
    assert check.agrees is None
    assert check not in result.mismatches


@pytest.mark.parametrize("busbar_id", ["BB21", "BB22"])
def test_losing_a_busbar_measurement_does_not_kill_the_bays(
    station: StationGraph, busbar_id: str
) -> None:
    """BB21 and BB22 are bonded; one broken point leaves the other speaking."""
    result = solve_energization(
        with_busbar_live(station, busbar_id, value=None, quality=Quality.BAD)
    )
    assert result.state_of("D03.n_bb") is LiveState.LIVE
