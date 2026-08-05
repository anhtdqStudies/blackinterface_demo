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
