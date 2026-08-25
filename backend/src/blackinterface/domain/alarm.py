"""Alarm as the rest of the system sees it — no NodeId, no binary struct (I6).

Two channels feed this (ADR-0026): a `GetActiveAlarm` snapshot at startup, and an
OPC UA A&C subscription for changes. Both land here, in one shape, keyed by
`event_id` so a snapshot row and a pushed event about the same alarm are the same
alarm rather than two.

The classification is the point of this module. Measured on DEMO_SAS: a perfectly
healthy station reports **243 active alarms**, of which 90 are switch positions
saying a breaker is closed. Passing that list through untouched would rebuild the
HMI this product exists to replace, so a raw alarm is not what any facet returns —
a *classified* alarm is (ADR-0027).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from blackinterface.domain.models import Frozen, Quality
from blackinterface.domain.scope import ScopeRef


class AlarmClass(StrEnum):
    """What kind of thing this alarm is, which decides whether it can raise a fault."""

    FAULT = "fault"  # a real abnormality
    STATUS = "status"  # a switch position; evidence, never a reason to alert
    CONFIG = "config"  # setting group, configuration state
    ACTION = "action"  # an operator did this; never a fault (ADR-0027 section 1)
    UNKNOWN = "unknown"  # no rule matched — shown, never silently dropped (I7)


class AlarmState(StrEnum):
    """Where the alarm is in its life. `ActiveState` on the event channel."""

    ACTIVE = "active"
    CLEARED = "cleared"
    #: Seen going in and out repeatedly inside one clustering window. Collapsed to
    #: one entry rather than N, because a flapping limit is one problem.
    FLAPPING = "flapping"


class Alarm(Frozen):
    """One alarm, addressed the way everything else in the system is addressed.

    `subject` is the scope it belongs to and `point` the specific point, both
    `ScopeRef` (ADR-0010) — so an alarm, a URL, a pane and a tool argument all
    speak the same vocabulary. The dotted OneATS path (`D03.XCBR1.PosSt`) never
    leaves `integration/`.
    """

    event_id: str
    subject: ScopeRef
    point: ScopeRef
    klass: AlarmClass
    state: AlarmState = AlarmState.ACTIVE
    message: str = ""
    severity: int = 0
    category: str = ""
    #: Typed as the source declares it: text for Discrete, a flag for Binary, a
    #: number for Limit. Flattening to string would throw away the only
    #: machine-readable form of a limit reading.
    value: bool | int | float | str | None = None
    #: Who caused it, when a person did. Present only on the snapshot channel —
    #: the subscription never populates `ClientUserId` (measured 2026-08-13).
    actor: str | None = None
    t_active: datetime | None = None
    t_change: datetime | None = None
    #: Quality of the *alarm*, not of the point behind it. OneATS leaves the A&C
    #: `Quality` field empty, so this stays `MISSING` unless a caller fills it
    #: from the monitored point. I2 forbids reading absence as good news.
    quality: Quality = Quality.MISSING
    acknowledged: bool = False

    @property
    def is_operator_action(self) -> bool:
        return self.klass is AlarmClass.ACTION

    @property
    def can_seed_incident(self) -> bool:
        """Only a real fault starts one. Everything else can join as evidence."""
        return self.klass is AlarmClass.FAULT and self.state is not AlarmState.CLEARED


class AlarmDelta(Frozen):
    """What changed between two views of the alarm set."""

    raised: tuple[Alarm, ...] = ()
    cleared: tuple[Alarm, ...] = ()
    changed: tuple[Alarm, ...] = ()

    @property
    def empty(self) -> bool:
        return not (self.raised or self.cleared or self.changed)


def diff(previous: dict[str, Alarm], current: dict[str, Alarm]) -> AlarmDelta:
    """Compare two snapshots keyed by `event_id`.

    Only needed on the snapshot path — the subscription reports raise and clear
    directly, through dedicated `ChangeOfState` / `ReturnToNormal` event types
    (ADR-0026). This is what reconciles the two after a reconnect.
    """
    raised = tuple(a for key, a in current.items() if key not in previous)
    cleared = tuple(a for key, a in previous.items() if key not in current)
    changed = tuple(
        current[key]
        for key in current.keys() & previous.keys()
        if _moved(previous[key], current[key])
    )
    return AlarmDelta(raised=raised, cleared=cleared, changed=changed)


def _moved(before: Alarm, after: Alarm) -> bool:
    return (
        before.value != after.value
        or before.state is not after.state
        or before.severity != after.severity
        or before.t_change != after.t_change
        or before.acknowledged != after.acknowledged
    )
