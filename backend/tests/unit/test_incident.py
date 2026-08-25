"""Clustering, checked against a cascade that actually happened.

The fixture is not invented. On 2026-08-13 an operator opened CB 231 on the
simulator while a filtered A&C subscription was recording, and seven voltage
alarms followed across four bays and three busbars within 87 ms. Collapsing that
into one incident instead of eight rows is the whole job of this module.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from blackinterface.domain.alarm import Alarm, AlarmClass, AlarmState
from blackinterface.domain.alarm_rules import default_rule_set
from blackinterface.domain.incident import group_incidents
from blackinterface.domain.scope import ScopeRef

CASCADE = Path(__file__).parent.parent / "fixtures" / "alarm_cascade.json"


def _alarms() -> list[Alarm]:
    from blackinterface.integration.alarm_map import from_event

    raw = json.loads(CASCADE.read_text(encoding="utf-8"))["events"]
    out: list[Alarm] = []
    for index, row in enumerate(raw):
        out.append(
            from_event(
                {
                    "EventId": f"evt{index:02d}".encode(),
                    "InputKeyName": row["source_name"],
                    "ConditionName": row["condition_name"],
                    "Message": row["message"],
                    "Severity": row["severity"],
                    "Value": row["value"],
                    "ActiveState": row["active_state"],
                    "Time": datetime.fromisoformat(row["time"]),
                    "ReceiveTime": datetime.fromisoformat(row["time"]),
                },
                rules=default_rule_set(),
            )
        )
    return out


@pytest.fixture(scope="module")
def cascade() -> list[Alarm]:
    return _alarms()


def test_the_cascade_classifies_as_one_breaker_and_seven_faults(cascade) -> None:  # type: ignore[no-untyped-def]
    """Sanity on the input before asserting anything about the grouping."""
    assert len(cascade) == 8
    statuses = [a for a in cascade if a.klass is AlarmClass.STATUS]
    faults = [a for a in cascade if a.klass is AlarmClass.FAULT]
    assert len(statuses) == 1, "the breaker position is the only status row"
    assert statuses[0].point.id == "D01.XCBR1.PosSt"
    assert len(faults) == 7, "seven voltage alarms"


def test_whole_cascade_spans_under_a_hundred_milliseconds(cascade) -> None:
    """The measurement the 200 ms default window is derived from."""
    stamps = [a.t_active for a in cascade if a.t_active]
    assert max(stamps) - min(stamps) < timedelta(milliseconds=100)


def test_breaker_position_never_seeds_an_incident(cascade) -> None:
    """A switch that moved is evidence. If it could raise incidents, every
    normal operation on the station would open one."""
    breaker = next(a for a in cascade if a.point.id == "D01.XCBR1.PosSt")
    assert not breaker.can_seed_incident


def test_station_wide_cascade_collapses_when_scopes_are_related(cascade) -> None:
    """With an electrical view that knows these scopes are connected, eight
    alarms become one incident — the outcome the pane is built around."""
    incidents = group_incidents(cascade, related=lambda a, b: True)
    assert len(incidents) == 1
    incident = incidents[0]
    assert len(incident.faults) == 7
    assert incident.severity == 650
    assert incident.seed.klass is AlarmClass.FAULT
    breaker_points = [a.point.id for a in incident.evidence]
    assert "D01.XCBR1.PosSt" in breaker_points, "the breaker must ride along as evidence"


def test_unrelated_scopes_stay_separate(cascade) -> None:
    """The opposite guard: without a relation, clustering must not merge things
    merely because they arrived close together."""
    incidents = group_incidents(cascade, related=lambda a, b: a == b)
    assert len(incidents) == 7, "one per distinct faulted point"


def test_far_apart_in_time_are_separate_incidents(cascade) -> None:
    later = [
        a.model_copy(
            update={
                "event_id": f"late-{a.event_id}",
                "t_active": a.t_active + timedelta(seconds=30),
            }
        )
        for a in cascade
        if a.t_active
    ]
    incidents = group_incidents([*cascade, *later], related=lambda a, b: True)
    assert len(incidents) == 2


def test_flapping_point_collapses_to_one_entry() -> None:
    """`E01.MMXU1.Vlin` alternated exceeded/normal repeatedly inside one burst.
    That is one misbehaving measurement, not N faults."""
    base = datetime.fromisoformat("2026-08-13T05:04:16.700000+00:00")
    point = ScopeRef.point("E01.MMXU1.Vlin")
    flapping = [
        Alarm(
            event_id=f"flap{i}",
            subject=ScopeRef.device("E01.MMXU1"),
            point=point,
            klass=AlarmClass.FAULT,
            state=AlarmState.ACTIVE if i % 2 == 0 else AlarmState.CLEARED,
            message="ABNORMAL VOLTAGE",
            severity=650 if i % 2 == 0 else 0,
            category="Limit Alarm",
            t_active=base + timedelta(milliseconds=10 * i),
        )
        for i in range(6)
    ]
    incidents = group_incidents(flapping, related=lambda a, b: True)
    assert len(incidents) == 1
    assert incidents[0].flapping_points == (point,)
    assert incidents[0].seed.state is AlarmState.FLAPPING


def test_no_faults_means_no_incidents() -> None:
    """243 standing status alarms on a healthy station must produce nothing."""
    quiet = [
        Alarm(
            event_id=f"pos{i}",
            subject=ScopeRef.device(f"D{i:02d}.XCBR1"),
            point=ScopeRef.point(f"D{i:02d}.XCBR1.PosSt"),
            klass=AlarmClass.STATUS,
            message="CB STATUS",
            severity=200,
            category="Discrete Alarm",
            t_active=datetime.fromisoformat("2026-08-13T05:00:00+00:00"),
        )
        for i in range(1, 20)
    ]
    assert group_incidents(quiet, related=lambda a, b: True) == ()


def test_operator_action_does_not_raise_an_incident() -> None:
    """The demo-safety case: throwing a switch on purpose is not a fault."""
    alarm = Alarm(
        event_id="act1",
        subject=ScopeRef.device("D01.XCBR1"),
        point=ScopeRef.point("D01.XCBR1.PosSt"),
        klass=AlarmClass.ACTION,
        message="CB 231 STATUS",
        severity=200,
        category="Discrete Alarm",
        actor="Administrator@OneATS_DataEditor:anhtdq",
        t_active=datetime.fromisoformat("2026-08-13T05:04:16+00:00"),
    )
    assert group_incidents([alarm], related=lambda a, b: True) == ()
