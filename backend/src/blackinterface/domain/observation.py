"""What an importer hands to the topology builder.

This is deliberately dumb: a flat description of what was found in the source
system, with no electrical meaning attached yet. Meaning is added by
`topology.build_station`, which is pure and therefore testable offline.

Two importers produce this today:
  * integration/opcua/discovery.py   — live DataServer browse
  * integration/dump.py              — a JSON address-space dump (fixture)

Both produce identical objects, so every test below the importer runs without
a DataServer.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from blackinterface.domain.models import PointSample


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class MeasurandObs(Frozen):
    """One analog data attribute as the importer found it.

    Deliberately uninterpreted: the importer records `da="totW"` and the raw
    sample, and `domain/measurement.py` decides what that means, what unit it
    may be printed with and how far it must move to be worth reporting. Keeping
    the meaning out of here is what lets one importer serve a catalog that
    grows.
    """

    da: str  # data attribute name, exactly as OneATS spells it
    sample: PointSample = PointSample()


class LogicalNodeObs(Frozen):
    """One logical node instance found under a bay, e.g. `XSWI1` or `MMXU1`."""

    ln: str
    name: str = ""  # value of the `Name` data attribute, e.g. "271-1"
    short_name: str = ""  # value of `SName`, e.g. "-1"
    position: PointSample = PointSample()  # `PosSt`, if the LN has one
    measurands: tuple[MeasurandObs, ...] = ()  # analog values, if any
    source_ref: str | None = None


class BayObs(Frozen):
    id: str
    name: str = ""
    voltage_level: str = ""
    logical_nodes: tuple[LogicalNodeObs, ...] = ()
    is_live: PointSample = PointSample()
    source_ref: str | None = None

    @property
    def ln_names(self) -> frozenset[str]:
        return frozenset(ln.ln for ln in self.logical_nodes)


class BusbarObs(Frozen):
    id: str  # e.g. "BB21"
    name: str = ""
    is_live: PointSample = PointSample()
    #: A busbar carries its measurands directly, with no logical node between
    #: (measured: `/SAS/Subs/BB21/Hz`, `/SAS/Subs/BB21/PPVmax`).
    measurands: tuple[MeasurandObs, ...] = ()
    source_ref: str | None = None


class TransformerObs(Frozen):
    """A power transformer the source exposes as its own station-level group.

    Measured on DEMO_SAS (2026-08-05): `/SAS/AT1` sits beside the voltage
    levels and carries `YPTR` (power transformer) and `YLTC` (tap changer).
    Its id ("AT1") is what transformer bays reference in their `BAY/Name`
    ("AT1 Incoming") — the pairing evidence for coupling voltage levels.
    """

    id: str  # e.g. "AT1"
    name: str = ""
    #: Same shape as a bay's, so `YLTC.TapPos` is found by the same code path
    #: that finds `MMXU1.totW`. A transformer has no switching devices, so
    #: these logical nodes carry measurands and nothing else.
    logical_nodes: tuple[LogicalNodeObs, ...] = ()
    source_ref: str | None = None


class StationObs(Frozen):
    """Everything one importer run saw. The unit of a snapshot."""

    name: str
    model_version: str | None = None
    captured_at: datetime | None = None
    source: str = ""
    bays: tuple[BayObs, ...] = ()
    busbars: tuple[BusbarObs, ...] = ()
    transformers: tuple[TransformerObs, ...] = ()


# --------------------------------------------------------------------- realtime
# An observation is a still photograph. The functions below turn a sequence of
# them into a film. All are pure and key off `source_ref`, which stays an opaque
# string here (AGENTS.md I6) — only integration/ knows it is an OPC UA NodeId.
#
# They come in two families, and the split is the load-bearing part (ADR-0012):
#
#   state_points / apply_state_samples              discrete, rebuilds the graph
#   measurement_points / apply_measurement_samples  analog, only relabels it
#
# A caller that routed an analog point into the state family would silently
# reintroduce the thing the ADR forbids: rebuilding the electrical graph because
# a load moved 0.1 MW. Keeping the two lists disjoint is what makes that
# mistake visible instead of merely slow.


def state_points(obs: StationObs) -> tuple[str, ...]:
    """Points that change what the station *is*: positions and `IsLive`.

    Sorted, so two runs over the same observation subscribe in the same order.
    """
    refs: set[str] = set()
    for bay in obs.bays:
        _add(refs, bay.is_live)
        for ln in bay.logical_nodes:
            _add(refs, ln.position)
    for busbar in obs.busbars:
        _add(refs, busbar.is_live)
    return tuple(sorted(refs))


def measurement_points(obs: StationObs) -> tuple[str, ...]:
    """Points that change what the station is *reading*: every analog value."""
    refs: set[str] = set()
    owners: tuple[BayObs | TransformerObs, ...] = (*obs.bays, *obs.transformers)
    for owner in owners:
        for ln in owner.logical_nodes:
            for measurand in ln.measurands:
                _add(refs, measurand.sample)
    for busbar in obs.busbars:
        for measurand in busbar.measurands:
            _add(refs, measurand.sample)
    return tuple(sorted(refs))


def watch_points(obs: StationObs) -> tuple[str, ...]:
    """Everything worth a subscription — one list, because there is one link.

    The subscription does not care which cadence a point belongs to; the
    routing happens when its batches come back. See ADR-0012 rule 3 for why
    there is deliberately only one connection to a substation.
    """
    return tuple(sorted({*state_points(obs), *measurement_points(obs)}))


def _add(refs: set[str], sample: PointSample) -> None:
    if sample.source_ref:
        refs.add(sample.source_ref)


def apply_state_samples(obs: StationObs, samples: Mapping[str, PointSample]) -> StationObs:
    """Replace every position / `IsLive` whose `source_ref` appears in `samples`.

    Returns `obs` itself when nothing matched, so a caller can skip the rebuild
    on a batch that turned out to be about points this station does not carry
    (a stale NodeId after the model changed, say).

    Note what is *not* updated: `captured_at`. That records when the structure
    was browsed, and the structure has not been re-browsed. When each point was
    read is already on the point, in `source_timestamp`.
    """
    if not samples:
        return obs

    patch = _Patch(samples)
    bays = tuple(
        bay.model_copy(
            update={
                "is_live": patch(bay.is_live),
                "logical_nodes": tuple(
                    ln.model_copy(update={"position": patch(ln.position)})
                    for ln in bay.logical_nodes
                ),
            }
        )
        for bay in obs.bays
    )
    busbars = tuple(
        busbar.model_copy(update={"is_live": patch(busbar.is_live)}) for busbar in obs.busbars
    )
    if not patch.changed:
        return obs
    return obs.model_copy(update={"bays": bays, "busbars": busbars})


def apply_measurement_samples(obs: StationObs, samples: Mapping[str, PointSample]) -> StationObs:
    """Replace every analog reading whose `source_ref` appears in `samples`.

    Same contract as its state counterpart, and deliberately the same shape —
    but it touches only `measurands`, so no caller of this function can move a
    switch. Returns `obs` unchanged when nothing matched.
    """
    if not samples:
        return obs

    patch = _Patch(samples)

    def patch_lns(lns: tuple[LogicalNodeObs, ...]) -> tuple[LogicalNodeObs, ...]:
        return tuple(
            ln.model_copy(
                update={
                    "measurands": tuple(
                        m.model_copy(update={"sample": patch(m.sample)}) for m in ln.measurands
                    )
                }
            )
            for ln in lns
        )

    bays = tuple(
        bay.model_copy(update={"logical_nodes": patch_lns(bay.logical_nodes)}) for bay in obs.bays
    )
    transformers = tuple(
        t.model_copy(update={"logical_nodes": patch_lns(t.logical_nodes)}) for t in obs.transformers
    )
    busbars = tuple(
        busbar.model_copy(
            update={
                "measurands": tuple(
                    m.model_copy(update={"sample": patch(m.sample)}) for m in busbar.measurands
                )
            }
        )
        for busbar in obs.busbars
    )
    if not patch.changed:
        return obs
    return obs.model_copy(update={"bays": bays, "busbars": busbars, "transformers": transformers})


class _Patch:
    """Swap in fresh readings, remembering whether anything actually moved."""

    def __init__(self, samples: Mapping[str, PointSample]) -> None:
        self._samples = samples
        self.changed = False

    def __call__(self, point: PointSample) -> PointSample:
        fresh = self._samples.get(point.source_ref) if point.source_ref else None
        if fresh is None:
            return point
        self.changed = True
        # The subscription reports a value, not an address: keep ours, so a
        # patched point stays traceable to the same node it was browsed from.
        return fresh.model_copy(update={"source_ref": point.source_ref})
