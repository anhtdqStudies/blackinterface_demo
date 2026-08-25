"""What the station is complaining about right now.

Held apart from `StationStore` on purpose. That store answers *what the station
is* — a graph rebuilt from observations; this one answers *what is wrong with
it*, which arrives on different channels, changes on a different rhythm, and
survives a model reload. Merging them would tie an alarm burst to a graph
rebuild, which ADR-0012 rule 1 exists to prevent.

Two channels feed it (ADR-0026): `load_snapshot` for the `GetActiveAlarm` list
at startup or after a reconnect, `apply_event` for each pushed A&C event.
"""

from __future__ import annotations

from blackinterface.domain.alarm import Alarm, AlarmState


class AlarmStore:
    """Current alarms, keyed by `event_id`.

    `event_id` is the join between the two channels: the `EventId` on a pushed
    event is byte-identical to the `event_id` inside the snapshot body, so the
    same alarm arriving twice is one entry, not two.
    """

    def __init__(self) -> None:
        self._alarms: dict[str, Alarm] = {}
        self._revision = 0
        self._snapshot_taken = False

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def has_snapshot(self) -> bool:
        """False until the initial list has been read.

        Worth exposing: an empty pane means something different before and after
        the first snapshot, and saying "no alarms" when we have not looked yet
        is the sort of quiet falsehood I2 is about.
        """
        return self._snapshot_taken

    @property
    def active(self) -> tuple[Alarm, ...]:
        """Everything not cleared. Narrowing to a scope happens in `api/alarms.py`.

        Deliberately not done here: deciding whether an alarm belongs to a
        voltage level, a busbar or a transformer needs the station graph, and
        this object does not have one. An earlier version filtered with
        `ScopeRef.contains`, whose docstring says plainly that False means "not
        decidable from here" — reading that as "not a member" made every
        voltage-level scope report an empty pane on a station with 82 faults.
        """
        return tuple(
            alarm for alarm in self._alarms.values() if alarm.state is not AlarmState.CLEARED
        )

    def all(self) -> tuple[Alarm, ...]:
        return tuple(self._alarms.values())

    def load_snapshot(self, alarms: list[Alarm]) -> int:
        """Replace everything with a freshly read list.

        Replace rather than merge: after a dropped link we do not know which of
        the alarms we remember have since cleared, and keeping a stale one alive
        is worse than briefly forgetting a real one.
        """
        keep_actors = {a.event_id: a.actor for a in self._alarms.values() if a.actor}
        self._alarms = {}
        for alarm in alarms:
            actor = alarm.actor or keep_actors.get(alarm.event_id)
            self._alarms[alarm.event_id] = (
                alarm if actor == alarm.actor else alarm.model_copy(update={"actor": actor})
            )
        self._snapshot_taken = True
        self._revision += 1
        return len(self._alarms)

    def apply_event(self, alarm: Alarm) -> bool:
        """Fold one pushed event in. Returns whether anything actually changed.

        The pushed event has no `actor` (OneATS never populates `ClientUserId`),
        so an existing one is carried forward rather than blanked — otherwise a
        follow-up event would silently reclassify an operator action as a fault.
        """
        existing = self._alarms.get(alarm.event_id)
        if existing is not None and existing.actor and not alarm.actor:
            alarm = alarm.model_copy(update={"actor": existing.actor, "klass": existing.klass})
        if existing == alarm:
            return False
        if alarm.state is AlarmState.CLEARED:
            self._alarms.pop(alarm.event_id, None)
        else:
            self._alarms[alarm.event_id] = alarm
        self._revision += 1
        return True

    def clear(self) -> None:
        self._alarms = {}
        self._snapshot_taken = False
        self._revision += 1
