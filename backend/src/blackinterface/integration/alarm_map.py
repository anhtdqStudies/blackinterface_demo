"""Turning OneATS alarm rows into neutral `Alarm` objects.

This is where the dotted OneATS path stops (I6). `D01.XCBR1.PosSt` is a naming
convention of one vendor's data model; everything above this layer sees a
`ScopeRef`, the same vocabulary used by URLs, panes and tool arguments.

Both channels of ADR-0026 land here: `from_record` takes a decoded
`GetActiveAlarm` body (and is the only path that carries `actor`), `from_event`
takes a field dict off the A&C subscription.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from blackinterface.domain.alarm import Alarm, AlarmClass, AlarmState
from blackinterface.domain.alarm_rules import AlarmRuleSet, default_rule_set
from blackinterface.domain.scope import ScopeRef
from blackinterface.integration.opcua.alarms import AlarmRecord

#: OneATS keeps busbars under a `Subs.` prefix (`Subs.BB11.PPVmax`), which is the
#: one path shape that does not describe a device inside a bay.
_BUSBAR_PREFIX = "Subs."


def subject_for(point_path: str) -> ScopeRef:
    """Best-effort scope for a dotted point path.

    Best-effort on purpose: this layer knows the naming convention, not the
    station. `api/` refines the result against the loaded graph, where a name
    can actually be checked against the bays and busbars that exist.
    """
    if point_path.startswith(_BUSBAR_PREFIX):
        parts = point_path.split(".")
        if len(parts) >= 2:
            return ScopeRef.busbar(parts[1])
    segments = point_path.rsplit(".", 1)
    if len(segments) == 2 and segments[0]:
        return ScopeRef.device(segments[0])
    return ScopeRef.station()


def _classify(
    rules: AlarmRuleSet, point: str, category: str, message: str, actor: str | None
) -> AlarmClass:
    return rules.classify(point=point, category=category, message=message, actor=actor)


def from_record(record: AlarmRecord, *, rules: AlarmRuleSet | None = None) -> Alarm:
    """Snapshot channel. The only source of `actor`."""
    table = rules or default_rule_set()
    path = record.source_point or record.source_object or ""
    category = record.category or ""
    message = record.message or ""
    return Alarm(
        event_id=record.event_id,
        subject=subject_for(path),
        point=ScopeRef.point(path) if path else ScopeRef.station(),
        klass=_classify(table, path, category, message, record.actor),
        state=AlarmState.ACTIVE,
        message=message,
        severity=record.severity_raw,
        category=category,
        value=record.value,
        actor=record.actor,
        t_active=record.t_active,
        t_change=record.t_change,
    )


def from_event(fields: dict[str, Any], *, rules: AlarmRuleSet | None = None) -> Alarm:
    """Subscription channel (A&C).

    `ClientUserId` is read even though OneATS leaves it empty (measured
    2026-08-13). If ATS ever populates it, this picks it up with no other change
    — and until then `actor` simply stays `None` on this path.
    """
    table = rules or default_rule_set()
    path = _text(fields.get("InputKeyName")) or _text(fields.get("SourceName")) or ""
    category = _text(fields.get("ConditionName")) or ""
    message = _text(fields.get("Message")) or ""
    actor = _text(fields.get("ClientUserId")) or None
    active = _text(fields.get("ActiveState"))
    return Alarm(
        event_id=_event_id(fields.get("EventId")),
        subject=subject_for(path),
        point=ScopeRef.point(path) if path else ScopeRef.station(),
        klass=_classify(table, path, category, message, actor),
        state=AlarmState.ACTIVE if active != "Inactive" else AlarmState.CLEARED,
        message=message,
        severity=_int(fields.get("Severity")),
        category=category,
        value=fields.get("Value"),
        actor=actor,
        t_active=_time(fields.get("Time")),
        t_change=_time(fields.get("ReceiveTime")),
        acknowledged=_text(fields.get("AckedState")) == "Acknowledged",
    )


def _text(value: Any) -> str:
    """Flatten a `LocalizedText`, a plain string, or nothing at all."""
    if value is None:
        return ""
    inner = getattr(value, "Text", None)
    return str(inner if inner is not None else value)


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _time(value: Any) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _event_id(value: Any) -> str:
    if isinstance(value, bytes | bytearray):
        return bytes(value).hex()
    return str(value or "")
