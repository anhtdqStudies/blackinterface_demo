"""The write path exists and is shut (AGENTS.md I1, ADR-0011).

Two things are being locked down. First, that the registry is empty — the same
fact `tools/check.py` parses, asserted again here so a `pytest` run alone catches
it. Second, that the guard's default answer is *no*: an unevaluable precondition
must never read as a satisfied one.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from blackinterface.control.audit import AuditEntry, AuditSink, NullAuditSink
from blackinterface.control.guard import (
    GuardVerdict,
    RefusalCode,
    check_preconditions,
    switching_verdict,
)
from blackinterface.control.registry import COMMANDS, get
from blackinterface.domain.models import (
    Device,
    DeviceRole,
    PointSample,
    Quality,
    StationGraph,
    SwitchState,
)
from blackinterface.domain.scope import ScopeRef


def codes(verdict: GuardVerdict) -> set[RefusalCode]:
    return {r.code for r in verdict.refusals}


def graph_with(device: Device) -> StationGraph:
    return StationGraph(name="T", devices=(device,))


def breaker(value: int | None, quality: Quality = Quality.GOOD) -> Device:
    return Device(
        id="D03.XCBR1",
        bay_id="D03",
        ln="XCBR1",
        role=DeviceRole.BREAKER,
        name="271",
        position=PointSample(value=value, quality=quality),
    )


# ------------------------------------------------------------------- registry
def test_no_command_is_open() -> None:
    """Empty by decision. Opening one takes its own ADR (ADR-0011 section 1)."""
    assert COMMANDS == {}
    assert get("switch.open") is None


def test_an_unopened_command_is_refused_before_anything_else_is_looked_at(
    station: StationGraph,
) -> None:
    verdict = check_preconditions(station, "switch.open", ScopeRef.device("D03.XCBR1"))
    assert not verdict.permitted
    assert codes(verdict) == {RefusalCode.UNKNOWN_COMMAND}
    assert verdict.checked == ("registry",)


# ---------------------------------------------------------------------- guard
def test_the_guard_never_permits_while_the_path_is_shut(station: StationGraph) -> None:
    """Whatever the station looks like, C-01 today ends in NOT_EVALUABLE: the
    interlock rules are not modelled, and silence would read as 'clear'."""
    device = station.devices[0]
    verdict = switching_verdict(station, ScopeRef.device(device.id))
    assert not verdict.permitted
    assert RefusalCode.NOT_EVALUABLE in codes(verdict)


def test_bad_quality_refuses_on_its_own_terms() -> None:
    graph = graph_with(breaker(2, Quality.BAD))
    verdict = switching_verdict(graph, ScopeRef.device("D03.XCBR1"))
    assert RefusalCode.POSITION_UNKNOWN in codes(verdict)
    detail = next(r for r in verdict.refusals if r.code is RefusalCode.POSITION_UNKNOWN).detail
    assert detail == Quality.BAD.value


def test_a_mechanism_between_states_is_not_a_position() -> None:
    graph = graph_with(breaker(0))  # Dbpos 0 = INTERMEDIATE
    verdict = switching_verdict(graph, ScopeRef.device("D03.XCBR1"))
    assert RefusalCode.POSITION_INTERMEDIATE in codes(verdict)


def test_asking_for_the_state_it_is_already_in_is_reported() -> None:
    graph = graph_with(breaker(2))  # Dbpos 2 = CLOSED
    verdict = switching_verdict(graph, ScopeRef.device("D03.XCBR1"), to_state=SwitchState.CLOSED)
    assert RefusalCode.ALREADY_IN_STATE in codes(verdict)
    assert "target_state" in verdict.checked


def test_a_device_the_station_does_not_have_is_refused_not_ignored() -> None:
    verdict = switching_verdict(graph_with(breaker(2)), ScopeRef.device("D99.XCBR1"))
    assert codes(verdict) == {RefusalCode.UNKNOWN_TARGET}


@pytest.mark.parametrize("scope", ["station", "bay:D03", "vl:220kV", "point:D03.XCBR1.PosSt"])
def test_only_a_device_can_be_switched(scope: str) -> None:
    verdict = switching_verdict(graph_with(breaker(2)), scope)
    assert codes(verdict) == {RefusalCode.WRONG_SCOPE_KIND}


def test_refusals_are_codes_so_the_ui_and_the_agent_can_both_phrase_them() -> None:
    """No Vietnamese, no English — the frontend is translated (ADR-0014) and the
    agent answers in the operator's language (I3/I4)."""
    verdict = switching_verdict(graph_with(breaker(2, Quality.BAD)), ScopeRef.device("D03.XCBR1"))
    for refusal in verdict.refusals:
        assert refusal.code in set(RefusalCode)
        assert " " not in refusal.detail


# ---------------------------------------------------------------------- audit
def test_the_null_sink_satisfies_the_protocol_and_only_appends() -> None:
    sink = NullAuditSink()
    assert isinstance(sink, AuditSink)
    sink.append(
        AuditEntry(
            at=datetime(2026, 8, 5, tzinfo=UTC),
            actor="operator:quang",
            command_id="switch.open",
            subject=ScopeRef.device("D03.XCBR1").ref,
            verdict=switching_verdict(graph_with(breaker(2)), ScopeRef.device("D03.XCBR1")),
        )
    )
    assert sink.count == 1
    assert sink.recent() == ()
    assert not hasattr(sink, "update")
    assert not hasattr(sink, "delete")
