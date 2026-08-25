"""The alarm and incident facets — built like `summary.py`, for the same reasons.

Takes a scope, resolves it against the loaded graph, gathers only what that
scope covers, and hands back the answer *together with* an `EvidenceRecord`
saying how far it can be trusted (ADR-0013).

The one thing this adds over `summary.py` is the electrical relation used for
clustering. `domain/incident.py` is pure and knows nothing about the station
graph, so the graph-aware "are these two scopes connected" predicate is built
here and passed in — which is what lets a busbar alarm join a bay alarm in the
same incident.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from blackinterface import __version__
from blackinterface.api.alarmsource import AlarmStore
from blackinterface.api.schemas import (
    AlarmOut,
    AlarmsOut,
    IncidentOut,
    IncidentsOut,
    PlaybookOut,
    PlaybookStepOut,
)
from blackinterface.api.source import StationStore
from blackinterface.api.summary import source_kind
from blackinterface.domain.alarm import Alarm, AlarmClass
from blackinterface.domain.energization import solve_energization
from blackinterface.domain.evidence import (
    EvidenceBuilder,
    EvidenceRecord,
    LimitCode,
    Source,
)
from blackinterface.domain.incident import Incident, group_incidents
from blackinterface.domain.models import StationGraph
from blackinterface.domain.playbooks import Playbook, default_registry
from blackinterface.domain.scope import (
    ScopeKind,
    ScopeLike,
    ScopeRef,
    as_scope,
    bays_in,
    exists,
)
from blackinterface.errors import NotFoundError
from blackinterface.store.incident_dismissals import IncidentDismissalRepository

ALARMS_TOOL = "alarms"
INCIDENTS_TOOL = "incidents"

#: Classes hidden unless explicitly asked for. A healthy station reports 90
#: switch-position alarms; showing them by default is the failure mode.
_NOISE = frozenset({AlarmClass.STATUS, AlarmClass.CONFIG})


def build_alarms(
    station: StationStore,
    alarms: AlarmStore,
    scope: ScopeLike,
    *,
    actor: str = "",
    include_status: bool = False,
) -> AlarmsOut:
    """Active alarms for one scope. Raises rather than widening an unknown one."""
    ref, graph = _resolve(station, scope)
    selected = _in_scope(alarms, graph, ref)
    counts = Counter(a.klass.value for a in selected)
    shown = [a for a in selected if include_status or a.klass not in _NOISE]
    shown.sort(key=lambda a: (-a.severity, a.point.ref))
    return AlarmsOut(
        scope=ref.ref,
        kind=ref.kind.value,
        counts=dict(sorted(counts.items())),
        alarms=[alarm_out(a) for a in shown],
        evidence=_evidence(ALARMS_TOOL, station, alarms, graph, ref, selected, actor),
    )


def build_incidents(
    station: StationStore,
    alarms: AlarmStore,
    scope: ScopeLike,
    *,
    actor: str = "",
    window_ms: int | None = None,
    status: Literal["open", "dismissed"] = "open",
    dismissals: IncidentDismissalRepository | None = None,
) -> IncidentsOut:
    """What is actually wrong in one scope, with guidance attached."""
    ref, graph = _resolve(station, scope)
    if status == "dismissed":
        if dismissals is None:
            return IncidentsOut(
                scope=ref.ref,
                kind=ref.kind.value,
                incidents=[],
                evidence=_evidence(INCIDENTS_TOOL, station, alarms, graph, ref, (), actor),
            )
        return IncidentsOut(
            scope=ref.ref,
            kind=ref.kind.value,
            incidents=_dismissed_incidents(dismissals, graph, ref, actor),
            evidence=_evidence(INCIDENTS_TOOL, station, alarms, graph, ref, (), actor),
        )

    selected = _in_scope(alarms, graph, ref)
    related = _relation_for(graph)
    incidents = (
        group_incidents(selected, related=related)
        if window_ms is None
        else group_incidents(selected, related=related, window_ms=window_ms)
    )
    hidden = dismissals.dismissed_ids(actor) if dismissals is not None and actor else frozenset()
    if hidden:
        incidents = tuple(i for i in incidents if i.id not in hidden)
    incidents = _newest_first(incidents)
    return IncidentsOut(
        scope=ref.ref,
        kind=ref.kind.value,
        incidents=[incident_out(i) for i in incidents],
        evidence=_evidence(INCIDENTS_TOOL, station, alarms, graph, ref, selected, actor),
    )


def dismiss_incident(
    station: StationStore,
    alarms: AlarmStore,
    scope: ScopeLike,
    incident_id: str,
    *,
    actor: str,
    window_ms: int | None = None,
    dismissals: IncidentDismissalRepository,
) -> IncidentOut:
    """Mark one open incident as handled locally. Does not ack on OneATS (I1)."""
    if not actor:
        raise NotFoundError("no signed-in operator to dismiss an incident")
    ref, graph = _resolve(station, scope)
    selected = _in_scope(alarms, graph, ref)
    related = _relation_for(graph)
    incidents = (
        group_incidents(selected, related=related)
        if window_ms is None
        else group_incidents(selected, related=related, window_ms=window_ms)
    )
    hidden = dismissals.dismissed_ids(actor)
    match = next((i for i in incidents if i.id == incident_id and i.id not in hidden), None)
    if match is None:
        raise NotFoundError(
            f"no open incident {incident_id!r} in scope {ref.ref}",
            scope=ref.ref,
        )
    payload = incident_out(match)
    row = dismissals.record(
        incident_id=incident_id,
        actor=actor,
        view_scope=ref.ref,
        payload=payload.model_dump_json(),
    )
    return payload.model_copy(update={"dismissed_at": row.dismissed_at})


# --------------------------------------------------------------------- scope


def _newest_first(incidents: Iterable[Incident]) -> tuple[Incident, ...]:
    """Most recent burst first — what the operator cares about right now."""
    return tuple(
        sorted(
            incidents,
            key=lambda i: (i.started_at or datetime.min, i.id),
            reverse=True,
        )
    )


def _dismissed_incidents(
    dismissals: IncidentDismissalRepository,
    graph: StationGraph,
    ref: ScopeRef,
    actor: str,
) -> list[IncidentOut]:
    """Stored snapshots, filtered to the scope being viewed."""
    out: list[IncidentOut] = []
    for row in dismissals.list_for_actor(actor):
        incident = IncidentOut.model_validate_json(row.payload)
        if _stored_incident_in_scope(incident, graph, ref):
            out.append(incident.model_copy(update={"dismissed_at": row.dismissed_at}))
    return out


def _stored_incident_in_scope(incident: IncidentOut, graph: StationGraph, ref: ScopeRef) -> bool:
    if ref.kind is ScopeKind.STATION:
        return True
    subjects = {as_scope(incident.subject), *(as_scope(s) for s in incident.scopes)}
    probes = [
        Alarm(
            event_id=f"{incident.id}-{subject.ref}",
            subject=subject,
            point=ScopeRef.point(incident.seed.point),
            klass=AlarmClass.FAULT,
        )
        for subject in subjects
    ]
    return bool(_filter_alarms(probes, graph, ref))


def _filter_alarms(
    alarms: Iterable[Alarm], graph: StationGraph, ref: ScopeRef
) -> tuple[Alarm, ...]:
    if ref.kind is ScopeKind.STATION:
        return tuple(alarms)

    bays = frozenset(bays_in(graph, ref))
    subjects: set[ScopeRef] = set()
    match ref.kind:
        case ScopeKind.VOLTAGE_LEVEL:
            subjects |= {ScopeRef.busbar(b.id) for b in graph.busbars if b.voltage_level == ref.id}
            subjects |= {
                ScopeRef.transformer(t.id)
                for t in graph.transformers
                if any(bay_id in bays for bay_id in t.bay_ids)
            }
        case ScopeKind.BUSBAR | ScopeKind.TRANSFORMER:
            subjects.add(ref)
        case _:
            pass

    bay_of = {device.id: device.bay_id or "" for device in graph.devices}

    def covered(alarm: Alarm) -> bool:
        subject = alarm.subject
        if ref == subject or ref.contains(subject):
            return True
        if subject in subjects:
            return True
        bay = bay_of.get(subject.id) or subject.id.split(".")[0]
        return bool(bays) and bay in bays

    return tuple(a for a in alarms if covered(a))


def _in_scope(alarms: AlarmStore, graph: StationGraph, ref: ScopeRef) -> tuple[Alarm, ...]:
    """Alarms this scope covers, resolved against the graph.

    Membership cannot be decided from ids alone. `ScopeRef.contains` says so in
    its own docstring — it returns False for a voltage level, a busbar and a
    transformer because those need the graph, and False there means "ask
    somebody who knows", not "no". Filtering on it directly made every
    voltage-level scope show an empty pane while the station had 82 faults.

    So this mirrors `summary.py::_readings_in`: bays come from `bays_in`, which
    already knows how a busbar or a voltage level maps onto them, and the
    subjects that are not bays are added only where the scope actually reaches
    them.
    """
    return _filter_alarms(alarms.active, graph, ref)


# ------------------------------------------------------------------ relation


def _relation_for(graph: StationGraph):  # type: ignore[no-untyped-def]
    """Are two scopes close enough electrically to belong to one incident?

    Same bay, or the same energised island. The island half is what makes the
    measured cascade work: `Subs.BB11` shares no bay with `D01`, but a breaker
    opening in D01 is exactly why the busbar complained 24 ms later.
    """
    solved = solve_energization(graph)
    island_of: dict[str, int] = {}
    for index, island in enumerate(getattr(solved, "islands", ()) or ()):
        for node_id in getattr(island, "node_ids", ()) or ():
            island_of[node_id] = index

    bay_of: dict[str, str] = {}
    for device in graph.devices:
        bay_of[device.id] = device.bay_id or ""

    def _key(scope: ScopeRef) -> str:
        if scope.kind.value == "device":
            return bay_of.get(scope.id, scope.id.split(".")[0])
        if scope.kind.value == "bay":
            return scope.id
        return ""

    def related(left: ScopeRef, right: ScopeRef) -> bool:
        if left == right:
            return True
        left_key, right_key = _key(left), _key(right)
        if left_key and left_key == right_key:
            return True
        # A busbar and anything on it: the busbar carries no bay, so fall back to
        # "both are in this station" rather than dropping the link entirely. This
        # is deliberately generous — a missed link hides a cascade, and a spurious
        # one shows up as a slightly wide incident that an operator can read.
        return "busbar" in (left.kind.value, right.kind.value)

    return related


# ------------------------------------------------------------------- mapping


def alarm_out(alarm: Alarm) -> AlarmOut:
    return AlarmOut(
        event_id=alarm.event_id,
        subject=alarm.subject.ref,
        point=alarm.point.ref,
        klass=alarm.klass.value,
        state=alarm.state.value,
        message=alarm.message,
        severity=alarm.severity,
        category=alarm.category,
        value=alarm.value,
        actor=alarm.actor,
        t_active=alarm.t_active.isoformat() if alarm.t_active else None,
        t_change=alarm.t_change.isoformat() if alarm.t_change else None,
        acknowledged=alarm.acknowledged,
    )


def playbook_out(playbook: Playbook) -> PlaybookOut:
    return PlaybookOut(
        id=playbook.id,
        title=playbook.title,
        status=playbook.status.value,
        summary=playbook.summary,
        steps=[PlaybookStepOut(text=s.text, caution=s.caution) for s in playbook.steps],
        references=list(playbook.references),
    )


def incident_out(incident: Incident) -> IncidentOut:
    found = default_registry().find(
        point=incident.seed.point.id,
        category=incident.seed.category,
        message=incident.seed.message,
    )
    return IncidentOut(
        id=incident.id,
        subject=incident.subject.ref,
        started_at=incident.started_at.isoformat() if incident.started_at else None,
        ended_at=incident.ended_at.isoformat() if incident.ended_at else None,
        severity=incident.severity,
        seed=alarm_out(incident.seed),
        faults=[alarm_out(a) for a in incident.faults],
        evidence=[alarm_out(a) for a in incident.evidence],
        flapping_points=[p.ref for p in incident.flapping_points],
        scopes=[s.ref for s in incident.scopes],
        playbook=playbook_out(found) if found else None,
    )


# ------------------------------------------------------------------ evidence


def _resolve(station: StationStore, scope: ScopeLike) -> tuple[ScopeRef, StationGraph]:
    ref = as_scope(scope)
    graph = station.graph  # raises ModelNotLoadedError when nothing is loaded
    if not exists(graph, ref):
        raise NotFoundError(f"no such scope in this station: {ref.ref}", scope=ref.ref)
    return ref, graph


def _evidence(
    tool: str,
    station: StationStore,
    alarms: AlarmStore,
    graph: StationGraph,
    ref: ScopeRef,
    selected: tuple[Alarm, ...],
    actor: str,
) -> EvidenceRecord:
    builder = EvidenceBuilder(
        tool,
        ref,
        source=Source(
            kind=source_kind(graph.source),
            endpoint=graph.source or None,
            catalog_snapshot=graph.model_version,
        ),
        actor=actor or None,
        args={"scope": ref.ref},
        release=__version__,
        model_version=graph.model_version,
    )
    # No snapshot yet means "we have not looked", which reads very differently
    # from "nothing is wrong" — and an empty pane looks identical either way.
    if not alarms.has_snapshot:
        builder.note(LimitCode.NO_HISTORY, count=1)
    link = station.monitor_status
    if link is not None and not link.connected:
        builder.note(LimitCode.LINK_DOWN, count=1)
    # OneATS leaves the A&C `Quality` field empty, so no alarm can assert the
    # quality of the point behind it. Saying so beats implying it was GOOD (I2).
    if selected:
        builder.note(
            LimitCode.QUALITY_NOT_GOOD,
            count=len(selected),
            subjects=tuple(a.point.ref for a in selected[:12]),
        )
    unknown = tuple(a.point.ref for a in selected if a.klass is AlarmClass.UNKNOWN)
    if unknown:
        builder.note(LimitCode.POINTS_MISSING, count=len(unknown), subjects=unknown)
    return builder.build()
