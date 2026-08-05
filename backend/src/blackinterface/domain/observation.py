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


class LogicalNodeObs(Frozen):
    """One logical node instance found under a bay, e.g. `XSWI1`."""

    ln: str
    name: str = ""  # value of the `Name` data attribute, e.g. "271-1"
    short_name: str = ""  # value of `SName`, e.g. "-1"
    position: PointSample = PointSample()  # `PosSt`, if the LN has one
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
# An observation is a still photograph. These two functions are what turn a
# sequence of them into a film: `watch_points` says which points can move, and
# `apply_samples` puts new readings of those points back where they came from.
#
# Both are pure and key off `source_ref`, which stays an opaque string here
# (AGENTS.md I6) — only integration/ knows it happens to be an OPC UA NodeId.


def watch_points(obs: StationObs) -> tuple[str, ...]:
    """Every point whose value can change while the station keeps its shape.

    Switch positions and the `IsLive` flags — not names, not the tree. Sorted,
    so two runs over the same observation subscribe in the same order.
    """
    refs: set[str] = set()
    for bay in obs.bays:
        if bay.is_live.source_ref:
            refs.add(bay.is_live.source_ref)
        for ln in bay.logical_nodes:
            if ln.position.source_ref:
                refs.add(ln.position.source_ref)
    for busbar in obs.busbars:
        if busbar.is_live.source_ref:
            refs.add(busbar.is_live.source_ref)
    return tuple(sorted(refs))


def apply_samples(obs: StationObs, samples: Mapping[str, PointSample]) -> StationObs:
    """Replace every point whose `source_ref` appears in `samples`.

    Returns `obs` itself when nothing matched, so a caller can skip the rebuild
    on a batch that turned out to be about points this station does not carry
    (a stale NodeId after the model changed, say).

    Note what is *not* updated: `captured_at`. That records when the structure
    was browsed, and the structure has not been re-browsed. When each point was
    read is already on the point, in `source_timestamp`.
    """
    if not samples:
        return obs

    changed = False

    def replace(point: PointSample) -> PointSample:
        nonlocal changed
        fresh = samples.get(point.source_ref) if point.source_ref else None
        if fresh is None:
            return point
        changed = True
        # The subscription reports a value, not an address: keep ours, so a
        # patched point stays traceable to the same node it was browsed from.
        return fresh.model_copy(update={"source_ref": point.source_ref})

    bays = tuple(
        bay.model_copy(
            update={
                "is_live": replace(bay.is_live),
                "logical_nodes": tuple(
                    ln.model_copy(update={"position": replace(ln.position)})
                    for ln in bay.logical_nodes
                ),
            }
        )
        for bay in obs.bays
    )
    busbars = tuple(
        busbar.model_copy(update={"is_live": replace(busbar.is_live)}) for busbar in obs.busbars
    )
    if not changed:
        return obs
    return obs.model_copy(update={"bays": bays, "busbars": busbars})
