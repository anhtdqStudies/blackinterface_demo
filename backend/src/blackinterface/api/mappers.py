"""Domain object -> wire schema. One direction, no I/O, no decisions.

Everything here is a function of its arguments. That is worth protecting: the
moment a mapper starts reading global state or asking the store a question, the
API's shape stops being derivable from the model, and the difference between
"the station says this" and "the server decided this" gets blurry.

The one apparent exception, `project_out`, takes `active` as an argument for
exactly that reason — whether a project is the current one is a fact about the
process, and the caller supplies it rather than the mapper going to look.
"""

from __future__ import annotations

from datetime import UTC, datetime

from blackinterface.api.schemas import (
    BayOut,
    BusbarOut,
    DeviceLiveOut,
    DeviceOut,
    EnergizationOut,
    LinkOut,
    LiveOut,
    MeasurementOut,
    ProjectOut,
    ReadingOut,
    StateOut,
    ValidationIssueOut,
)
from blackinterface.api.source import StationStore
from blackinterface.domain.energization import LiveState, solve_energization
from blackinterface.domain.issue_groups import issue_group
from blackinterface.domain.measurement import Reading
from blackinterface.domain.models import Bay, Busbar, Device, StationGraph, ValidationIssue
from blackinterface.store.projects import ProjectRow


def issue_out(issue: ValidationIssue) -> ValidationIssueOut:
    return ValidationIssueOut(
        severity=issue.severity,
        code=issue.code,
        message=issue.message,
        subject=issue.subject,
        group=issue_group(issue.code),
    )


def device_out(device: Device) -> DeviceOut:
    return DeviceOut(
        id=device.id,
        ln=device.ln,
        role=str(device.role),
        name=device.name,
        short_name=device.short_name,
        state=device.state,
        quality=device.position.quality,
        value=device.position.value,
        source_timestamp=(
            device.position.source_timestamp.isoformat()
            if device.position.source_timestamp
            else None
        ),
        source_ref=device.source_ref,
        terminals=[t.node_id for t in device.terminals],
    )


def bay_out(bay: Bay, graph: StationGraph) -> BayOut:
    return BayOut(
        id=bay.id,
        name=bay.name,
        voltage_level=bay.voltage_level,
        bay_type=str(bay.bay_type),
        template_id=bay.template_id,
        device_count=len(graph.devices_of(bay.id)),
        is_live=bay.is_live.value if isinstance(bay.is_live.value, bool) else None,
        is_live_quality=bay.is_live.quality,
        logical_nodes=list(bay.logical_nodes),
        issues=[issue_out(i) for i in bay.issues],
    )


def busbar_out(busbar: Busbar) -> BusbarOut:
    return BusbarOut(
        id=busbar.id,
        name=busbar.name,
        voltage_level=busbar.voltage_level,
        index=busbar.index,
        is_live=busbar.is_live.value if isinstance(busbar.is_live.value, bool) else None,
        quality=busbar.is_live.quality,
        inferred=busbar.inferred,
    )


def project_out(row: ProjectRow, *, active: bool) -> ProjectOut:
    return ProjectOut(
        id=row.id,
        name=row.name,
        opcua_url=row.opcua_url,
        created_at=row.created_at,
        updated_at=row.updated_at,
        has_snapshot=row.has_snapshot,
        model_name=row.model_name,
        model_version=row.model_version,
        captured_at=row.captured_at,
        snapshot_saved_at=row.snapshot_saved_at,
        active=active,
    )


def energization_out(graph: StationGraph) -> EnergizationOut:
    result = solve_energization(graph)
    states = [island.state for island in result.islands]
    return EnergizationOut(
        islands=list(result.islands),
        node_state={n.node_id: n.state for n in result.nodes},
        checks=list(result.checks),
        issues=[issue_out(i) for i in result.issues],
        summary={
            "islands": len(result.islands),
            **{state.lower(): states.count(state) for state in LiveState},
            "compared": sum(1 for c in result.checks if c.agrees is not None),
            "mismatched": len(result.mismatches),
        },
    )


def link_out(store: StationStore) -> LinkOut:
    status = store.monitor_status
    if status is None:
        # Either realtime is switched off, or this source has no server behind
        # it (a fixture, or a project whose model has no watchable points).
        return LinkOut(revision=store.link_revision, realtime=False, connected=False)
    return LinkOut(
        revision=store.link_revision,
        realtime=True,
        connected=status.connected,
        watching=status.watching,
        rejected=status.rejected,
        error=status.error,
        since=status.since.isoformat() if status.since else None,
    )


def state_out(store: StationStore) -> StateOut:
    """What the station is, right now.

    Never raises when no model is loaded: this is a document a stream is
    holding open, and a client that loses its station should be told so rather
    than have its connection dropped.
    """
    base = StateOut(
        loaded=store.loaded,
        revision=store.state_revision,
        structure_revision=store.structure_revision,
        updated_at=_iso(store.updated_at),
    )
    if not store.loaded:
        return base
    graph = store.graph
    return base.model_copy(
        update={
            "devices": {
                device.id: DeviceLiveOut(
                    state=device.state,
                    quality=device.position.quality,
                    value=device.position.value,
                    source_timestamp=(
                        device.position.source_timestamp.isoformat()
                        if device.position.source_timestamp
                        else None
                    ),
                )
                for device in graph.devices
            },
            # null means "not readable", never "false": a bay whose IsLive
            # cannot be trusted must not be published as de-energised (I2).
            "bay_is_live": {
                bay.id: (
                    bay.is_live.value
                    if bay.is_live.usable and isinstance(bay.is_live.value, bool)
                    else None
                )
                for bay in graph.bays
            },
            "energization": energization_out(graph),
        }
    )


def reading_out(reading: Reading) -> ReadingOut:
    return ReadingOut(
        id=reading.id,
        subject=reading.subject.ref,
        measurand=reading.measurand.key,
        quantity=reading.measurand.quantity,
        unit=reading.measurand.unit,
        value=reading.number,
        raw_value=reading.sample.value,
        quality=reading.sample.quality,
        source_timestamp=(
            reading.sample.source_timestamp.isoformat() if reading.sample.source_timestamp else None
        ),
        source_ref=reading.sample.source_ref,
        deadband_pct=reading.measurand.deadband_pct,
        deadband_abs=reading.measurand.deadband_abs,
    )


def measurement_out(store: StationStore) -> MeasurementOut:
    """Every reading, grouped by the thing it is about."""
    grouped: dict[str, list[ReadingOut]] = {}
    for reading in store.measurements.readings:
        grouped.setdefault(reading.subject.ref, []).append(reading_out(reading))
    return MeasurementOut(
        revision=store.measurement_revision,
        measured_at=_iso(store.measured_at),
        deadband_override_pct=store.settings.measurement_deadband_pct,
        readings=grouped,
    )


def live_out(store: StationStore) -> LiveOut:
    """All three cadences at once — what a client needs on its first load."""
    return LiveOut(
        state=state_out(store),
        measurement=measurement_out(store),
        link=link_out(store),
    )


def _iso(epoch: float | None) -> str | None:
    return datetime.fromtimestamp(epoch, UTC).isoformat() if epoch else None
