"""Turning a burst of alarms into the small number of things actually wrong.

Pure, no I/O, rebuilt from scratch every batch — same reasoning as
`build_station` (`AGENTS.md` section 7): recomputing is cheap and *guarantees*
the result equals a fresh calculation, which patching in place cannot promise.

The window is 200 ms, and that number is measured rather than guessed. A real
cascade recorded on 2026-08-13:

    05:04:16.727  D01.XCBR1.PosSt    CB 231 STATUS     1 (OPENED)
    05:04:16.736  E01.MMXU1.Vlin     ABNORMAL VOLTAGE
    ...
    05:04:16.814  E04.MMXU1.Vlin     ABNORMAL VOLTAGE

One breaker opening produced seven voltage alarms across four bays and three
busbars in **87 ms**. Seconds-wide windows would swallow unrelated events.

What this module does *not* do is decide causality. It says "these belong
together"; it never says the first one caused the rest. That is `trace`
(ADR-0024) and it needs the electrical graph, not a clock.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timedelta

from blackinterface.domain.alarm import Alarm, AlarmClass, AlarmState
from blackinterface.domain.models import Frozen
from blackinterface.domain.scope import ScopeKind, ScopeRef

#: Measured 2026-08-13: a real cascade spans 87 ms. Doubled for headroom, and
#: overridable per deployment because one measurement is one measurement.
DEFAULT_WINDOW_MS = 200

#: A point that goes in and out this many times inside one window is flapping,
#: not producing that many faults. Seen on `E01.MMXU1.Vlin`, which alternated
#: LoLimitExceeded / ReturnToNormal repeatedly inside a single burst.
DEFAULT_FLAP_THRESHOLD = 3

#: Which alarms may be pulled into an incident as supporting evidence. A breaker
#: that opened is the most important fact about a fault — and is never the alarm
#: that should have raised it.
_EVIDENCE_CLASSES = frozenset({AlarmClass.STATUS, AlarmClass.CONFIG, AlarmClass.UNKNOWN})

Related = Callable[[ScopeRef, ScopeRef], bool]


class Incident(Frozen):
    """A cluster of alarms that belong together in time and in the network."""

    id: str
    subject: ScopeRef
    started_at: datetime | None = None
    ended_at: datetime | None = None
    #: The highest-severity fault in the cluster, and the one the playbook keys
    #: on. Deliberately *not* called "cause" — see the module docstring.
    seed: Alarm
    faults: tuple[Alarm, ...] = ()
    evidence: tuple[Alarm, ...] = ()
    flapping_points: tuple[ScopeRef, ...] = ()

    @property
    def severity(self) -> int:
        return max((a.severity for a in self.faults), default=self.seed.severity)

    @property
    def alarm_count(self) -> int:
        return len(self.faults) + len(self.evidence)

    @property
    def scopes(self) -> tuple[ScopeRef, ...]:
        seen = {a.subject for a in self.faults} | {a.subject for a in self.evidence}
        return tuple(sorted(seen, key=lambda s: s.ref))


def same_bay(left: ScopeRef, right: ScopeRef) -> bool:
    """Default adjacency: the same subject, or two devices in the same bay.

    Deliberately narrow. The caller that owns the electrical graph passes a
    better `related` — one that also joins scopes energised from the same island,
    which is what links `Subs.BB11` to `D01` in the cascade above.
    """
    if left == right:
        return True
    return _bay_of(left) == _bay_of(right) != ""


def _bay_of(scope: ScopeRef) -> str:
    if scope.kind is ScopeKind.BAY:
        return scope.id
    parent = scope.parent()
    while parent is not None and not parent.is_station:
        if parent.kind is ScopeKind.BAY:
            return parent.id
        parent = parent.parent()
    return ""


def group_incidents(
    alarms: Iterable[Alarm],
    *,
    window_ms: int = DEFAULT_WINDOW_MS,
    flap_threshold: int = DEFAULT_FLAP_THRESHOLD,
    related: Related | None = None,
) -> tuple[Incident, ...]:
    """Cluster alarms into incidents. Deterministic: same input, same output."""
    joins = related or same_bay
    window = timedelta(milliseconds=window_ms)

    collapsed, flapping = _collapse_flapping(list(alarms), window, flap_threshold)
    seeds = sorted(
        (a for a in collapsed if a.can_seed_incident),
        key=lambda a: (a.t_active or datetime.min, a.event_id),
    )
    if not seeds:
        return ()

    clusters: list[list[Alarm]] = []
    for alarm in seeds:
        target = _cluster_for(alarm, clusters, window, joins)
        if target is None:
            clusters.append([alarm])
        else:
            target.append(alarm)

    supporting = [a for a in collapsed if a.klass in _EVIDENCE_CLASSES]
    return tuple(_build(cluster, supporting, window, joins, flapping) for cluster in clusters)


def _cluster_for(
    alarm: Alarm,
    clusters: list[list[Alarm]],
    window: timedelta,
    joins: Related,
) -> list[Alarm] | None:
    for cluster in clusters:
        if not _within(alarm, cluster, window):
            continue
        if any(joins(alarm.subject, other.subject) for other in cluster):
            return cluster
    return None


def _within(alarm: Alarm, cluster: Sequence[Alarm], window: timedelta) -> bool:
    if alarm.t_active is None:
        return False
    stamps = [a.t_active for a in cluster if a.t_active is not None]
    if not stamps:
        return False
    return min(abs(alarm.t_active - stamp) for stamp in stamps) <= window


def _collapse_flapping(
    alarms: list[Alarm], window: timedelta, threshold: int
) -> tuple[list[Alarm], set[ScopeRef]]:
    """One entry per flapping point, marked as such, instead of N entries."""
    by_point: dict[ScopeRef, list[Alarm]] = {}
    for alarm in alarms:
        by_point.setdefault(alarm.point, []).append(alarm)

    kept: list[Alarm] = []
    flapping: set[ScopeRef] = set()
    for point, group in by_point.items():
        stamps = [a.t_active for a in group if a.t_active is not None]
        spans_window = bool(stamps) and (max(stamps) - min(stamps)) <= window
        if len(group) >= threshold and spans_window:
            flapping.add(point)
            newest = max(group, key=lambda a: (a.t_active or datetime.min, a.event_id))
            kept.append(newest.model_copy(update={"state": AlarmState.FLAPPING}))
        else:
            kept.extend(group)
    return kept, flapping


def _build(
    cluster: list[Alarm],
    supporting: list[Alarm],
    window: timedelta,
    joins: Related,
    flapping: set[ScopeRef],
) -> Incident:
    seed = max(cluster, key=lambda a: (a.severity, a.t_active or datetime.min))
    evidence = tuple(
        a
        for a in supporting
        if _within(a, cluster, window) and any(joins(a.subject, other.subject) for other in cluster)
    )
    stamps = [a.t_active for a in (*cluster, *evidence) if a.t_active is not None]
    touched = {a.point for a in (*cluster, *evidence)} & flapping
    return Incident(
        id=seed.event_id,
        subject=seed.subject,
        started_at=min(stamps) if stamps else None,
        ended_at=max(stamps) if stamps else None,
        seed=seed,
        faults=tuple(sorted(cluster, key=lambda a: (-a.severity, a.event_id))),
        evidence=evidence,
        flapping_points=tuple(sorted(touched, key=lambda s: s.ref)),
    )
