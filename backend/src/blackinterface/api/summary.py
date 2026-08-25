"""How one scope is doing right now — the first facet that carries evidence.

`GET /api/summary?scope=bay:D03` is the question Module A exists to answer, and
it is also the shape every later facet copies: take a scope ref, resolve it
against the loaded graph, gather only what that scope covers, and hand back the
answer *together with* an `EvidenceRecord` saying how far it can be trusted.

The evidence is assembled here, from the samples actually read (I3). Three
caveats can only be known at this level and are added by hand:

  * `LINK_DOWN` — a subscription is configured and is not currently up, so
    every number below is the last thing we heard, not the present tense.
  * `DEADBAND_APPLIED` — analog readings passed a filter before arriving here
    (ADR-0012 consequence 3: the UI must say so).
  * `UNIT_UNVERIFIED` — the DataServer publishes no engineering units, so a
    scale we did not measure is one we refuse to print. See the module
    docstring of `domain/measurement.py`.

Everything else — missing bindings, bad quality, stale timestamps, snapshot
provenance — the builder derives, so no facet can forget them.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from blackinterface import __version__
from blackinterface.api.mappers import issue_out, reading_out
from blackinterface.api.schemas import SummaryOut
from blackinterface.api.source import StationStore
from blackinterface.domain.energization import solve_energization
from blackinterface.domain.evidence import (
    EvidenceBuilder,
    EvidenceRecord,
    LimitCode,
    Source,
    SourceKind,
)
from blackinterface.domain.measurement import Reading, Unit
from blackinterface.domain.models import Device, StationGraph
from blackinterface.domain.scope import (
    ScopeKind,
    ScopeLike,
    ScopeRef,
    as_scope,
    bays_in,
    exists,
)
from blackinterface.errors import NotFoundError

TOOL = "summary"


def build_summary(store: StationStore, scope: ScopeLike, *, actor: str = "") -> SummaryOut:
    """Answer for one scope. Raises rather than widening an unknown one.

    `actor` goes on the evidence record so an answer can be traced to a person
    later (ADR-0016 section 5). It is a parameter rather than something read
    from the request here because the agent will call this same function under
    the permissions of whoever asked it — and it must not be able to name
    somebody else.
    """
    ref = as_scope(scope)
    graph = store.graph  # raises ModelNotLoadedError when nothing is loaded
    if not exists(graph, ref):
        raise NotFoundError(f"no such scope in this station: {ref.ref}", scope=ref.ref)

    bays = bays_in(graph, ref)
    devices = _devices_in(graph, ref, bays)
    readings = _readings_in(store, graph, ref, bays)
    node_ids = _node_ids(devices, graph, ref)
    solved = solve_energization(graph)

    return SummaryOut(
        scope=ref.ref,
        kind=ref.kind.value,
        label=_label(graph, ref),
        bays=list(bays),
        switch_states=_counts(str(d.state) for d in devices),
        node_states=_counts(str(n.state) for n in solved.nodes if n.node_id in node_ids),
        measurements=[reading_out(r) for r in readings],
        issues=[issue_out(i) for i in graph.all_issues() if _issue_in_scope(i, ref, bays)],
        evidence=_evidence(store, graph, ref, devices, readings, actor),
    )


# ------------------------------------------------------------------- gathering


def _devices_in(graph: StationGraph, ref: ScopeRef, bays: tuple[str, ...]) -> tuple[Device, ...]:
    """A device scope means that one device; anything wider means its bays'."""
    if ref.kind is ScopeKind.DEVICE:
        device = graph.device(ref.id)
        return (device,) if device is not None else ()
    return tuple(d for d in graph.devices if d.bay_id in bays)


def _readings_in(
    store: StationStore, graph: StationGraph, ref: ScopeRef, bays: tuple[str, ...]
) -> tuple[Reading, ...]:
    """Readings whose subject this scope covers.

    Bays come from `bays_in`, which already knows how a busbar or a voltage
    level maps onto them. Busbars and transformers are their own subjects and
    are added only when the scope actually reaches them — a question about one
    bay must not come back carrying the whole station's busbar voltages.
    """
    subjects = {ScopeRef.bay(bay_id) for bay_id in bays}
    match ref.kind:
        case ScopeKind.STATION:
            subjects |= {ScopeRef.busbar(b.id) for b in graph.busbars}
            subjects |= {ScopeRef.transformer(t.id) for t in graph.transformers}
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
    return tuple(r for r in store.measurements.readings if r.subject in subjects)


def _node_ids(devices: tuple[Device, ...], graph: StationGraph, ref: ScopeRef) -> frozenset[str]:
    """Connectivity nodes this scope touches, so energisation can be counted."""
    if ref.kind is ScopeKind.STATION:
        return frozenset(n.id for n in graph.nodes)
    ids = {t.node_id for d in devices for t in d.terminals}
    if ref.kind is ScopeKind.BUSBAR:
        busbar = next((b for b in graph.busbars if b.id == ref.id), None)
        if busbar is not None:
            ids.add(busbar.node_id)
    return frozenset(ids)


def _label(graph: StationGraph, ref: ScopeRef) -> str:
    match ref.kind:
        case ScopeKind.STATION:
            return graph.name
        case ScopeKind.VOLTAGE_LEVEL:
            return ref.id
        case ScopeKind.TRANSFORMER:
            found = next((t for t in graph.transformers if t.id == ref.id), None)
            return found.name if found else ""
        case ScopeKind.BUSBAR:
            busbar = next((b for b in graph.busbars if b.id == ref.id), None)
            return busbar.name if busbar else ""
        case ScopeKind.BAY:
            bay = graph.bay(ref.id)
            return bay.name if bay else ""
        case ScopeKind.DEVICE:
            device = graph.device(ref.id)
            return device.name if device else ""
        case ScopeKind.POINT:
            return ref.id


def _issue_in_scope(issue: object, ref: ScopeRef, bays: tuple[str, ...]) -> bool:
    subject = getattr(issue, "subject", None)
    if ref.kind is ScopeKind.STATION:
        return True
    if not subject:
        return False  # a station-wide issue is not evidence about one bay
    return subject in bays or subject == ref.id or subject.startswith(f"{ref.id}.")


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


# -------------------------------------------------------------------- evidence


def _evidence(
    store: StationStore,
    graph: StationGraph,
    ref: ScopeRef,
    devices: tuple[Device, ...],
    readings: tuple[Reading, ...],
    actor: str,
) -> EvidenceRecord:
    builder = EvidenceBuilder(
        TOOL,
        ref,
        source=Source(
            kind=source_kind(graph.source),
            endpoint=graph.source or None,
            node_ids=tuple(
                sorted(
                    {d.position.source_ref for d in devices if d.position.source_ref}
                    | {r.sample.source_ref for r in readings if r.sample.source_ref}
                )
            ),
            catalog_snapshot=graph.model_version,
        ),
        actor=actor or None,
        args={"scope": ref.ref},
        release=__version__,
        model_version=graph.model_version,
    )

    # A position is event-driven: its timestamp says when it last *moved*, so a
    # disconnector untouched for a day is current, not stale. A measurement is
    # supposed to keep arriving, so its age does mean something.
    for device in devices:
        point = ScopeRef.point(f"{device.id}.PosSt").ref
        if device.position.source_ref is None:
            builder.missing(point)  # never bound: absent, not unreadable (I7)
        else:
            builder.point(point, device.position)
    for reading in readings:
        builder.point(reading.point.ref, reading.sample, expect_refresh=True)

    link = store.monitor_status
    if link is not None and not link.connected:
        builder.note(LimitCode.LINK_DOWN, count=1)
    if readings:
        builder.note(LimitCode.DEADBAND_APPLIED, count=len(readings))
    unverified = tuple(r.point.ref for r in readings if r.measurand.unit is Unit.UNKNOWN)
    if unverified:
        builder.note(LimitCode.UNIT_UNVERIFIED, count=len(unverified), subjects=unverified)
    return builder.build()


def source_kind(source: str) -> SourceKind:
    """Read provenance off the label the loader already stamped on the graph.

    Public because every facet needs it and there is only one right answer:
    an agent tool that decided provenance for itself could report a snapshot as
    live, which is the one caveat an operator most needs to see (ADR-0013).
    """
    if source.startswith("snapshot:"):
        return SourceKind.SNAPSHOT
    if source.startswith("fixture:"):
        return SourceKind.FIXTURE
    if source.startswith("opc."):
        return SourceKind.OPCUA
    return SourceKind.DERIVED
