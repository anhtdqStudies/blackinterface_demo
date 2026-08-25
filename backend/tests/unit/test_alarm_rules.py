"""The classification table, and the guidance lookup beside it.

The assertions worth having here are the ones that encode a decision somebody
could plausibly reverse by accident: that a closed breaker is not a fault, that
an operator action outranks everything, and that an unmatched alarm surfaces
rather than vanishing.
"""

from __future__ import annotations

import pytest

from blackinterface.domain.alarm import AlarmClass
from blackinterface.domain.alarm_rules import default_rule_set
from blackinterface.domain.playbooks import PlaybookStatus, default_registry


@pytest.fixture(scope="module")
def rules():  # type: ignore[no-untyped-def]
    return default_rule_set()


@pytest.mark.parametrize(
    ("point", "category", "message", "expected"),
    [
        ("D03.XCBR1.PosSt", "Discrete Alarm", "CB 271 STATUS", AlarmClass.STATUS),
        ("D03.XSWI1.PosSt", "Discrete Alarm", "DS 271 - 1 STATUS", AlarmClass.STATUS),
        ("J01.XCBR1.PosSt1", "Discrete Alarm", "CB 431 STATUS", AlarmClass.STATUS),
        ("D03.F21.ANN.ST.SG1", "Binary Alarm", "RELAY IN GROUP 1", AlarmClass.CONFIG),
        ("D03.BCU.ANN.ST.TimeFail", "Binary Alarm", "RELAY TIME SYNC FAIL", AlarmClass.FAULT),
        ("AT1.YPTR.OilTmpTr", "Binary Alarm", "OIL TEMP TRIP", AlarmClass.FAULT),
        ("D12.MMXU1.Vlin", "Limit Alarm", "ABNORMAL VOLTAGE", AlarmClass.FAULT),
        ("Subs.BB29.PPVmax", "Limit Alarm", "ABNORMAL VOLATGE", AlarmClass.FAULT),
        ("AT1.YPTR.FanSt", "Binary Alarm", "FAN GROUP 1 RUNNING", AlarmClass.STATUS),
    ],
)
def test_classifies_measured_alarms(rules, point, category, message, expected) -> None:  # type: ignore[no-untyped-def]
    assert rules.classify(point=point, category=category, message=message) is expected


def test_a_closed_breaker_is_not_a_fault(rules) -> None:  # type: ignore[no-untyped-def]
    """90 of 243 alarms on a healthy station are this. If they seed incidents,
    the pane becomes the wall of noise the product exists to replace."""
    klass = rules.classify(
        point="D03.XCBR1.PosSt", category="Discrete Alarm", message="CB 271 STATUS"
    )
    assert klass is AlarmClass.STATUS


def test_operator_action_outranks_every_other_rule(rules) -> None:  # type: ignore[no-untyped-def]
    """Whatever the table says, a named actor means a person did it.

    Without this the demo alarms 'fault' the moment somebody throws a switch on
    purpose — which is exactly what happens during a demo.
    """
    klass = rules.classify(
        point="AT1.YPTR.OilTmpTr",  # would otherwise be FAULT
        category="Binary Alarm",
        message="OIL TEMP TRIP",
        actor="Administrator@OneATS_DataEditor:anhtdq",
    )
    assert klass is AlarmClass.ACTION


def test_unmatched_alarm_becomes_unknown_not_dropped(rules) -> None:  # type: ignore[no-untyped-def]
    klass = rules.classify(
        point="X99.WEIRD.NeverSeenBefore", category="Mystery Alarm", message="???"
    )
    assert klass is AlarmClass.UNKNOWN


# ------------------------------------------------------------------- playbooks


def test_every_bundled_playbook_declares_draft_status() -> None:
    """Nothing here has been through operational review (2026-08-13).

    If a playbook ever claims `approved`, a human with authority over this
    substation must have signed it off — this test is the reminder.
    """
    registry = default_registry()
    assert registry.playbooks, "no playbooks bundled"
    for playbook in registry.playbooks:
        assert playbook.status is PlaybookStatus.DRAFT, playbook.id


@pytest.mark.parametrize(
    ("point", "category", "message", "expected_id"),
    [
        ("AT1.YPTR.OilTmpTr", "Binary Alarm", "OIL TEMP  TRIP", "oil-temperature-trip"),
        ("D12.MMXU1.Vlin", "Limit Alarm", "ABNORMAL VOLTAGE", "abnormal-voltage"),
        ("Subs.BB29.PPVmax", "Limit Alarm", "ABNORMAL VOLATGE", "abnormal-voltage"),
        ("D03.BCU.ANN.ST.TimeFail", "Binary Alarm", "RELAY TIME SYNC", "relay-time-sync-fail"),
    ],
)
def test_playbook_lookup(point, category, message, expected_id) -> None:  # type: ignore[no-untyped-def]
    found = default_registry().find(point=point, category=category, message=message)
    assert found is not None, f"no playbook for {point}"
    assert found.id == expected_id
    assert found.steps, "a playbook with no steps is not guidance"


def test_no_playbook_returns_none_rather_than_inventing_one() -> None:
    """The gap must stay visible. An invented switching procedure reads exactly
    as confidently as a real one, which is what makes it dangerous."""
    assert default_registry().find(point="X99.WEIRD.Nothing", category="?", message="?") is None
