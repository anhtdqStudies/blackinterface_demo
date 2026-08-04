"""Neutral Station Model — the contract every other layer speaks.

Nothing in this module knows what an OPC UA NodeId is. Provenance travels as an
opaque `source_ref` string (AGENTS.md I6): useful for tracing back to OneATS,
never used as a key.

The graph is node-breaker: switching devices sit between `ConnectivityNode`s.
Bus-branch is a *view* computed later, not stored here.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Quality(StrEnum):
    """Quality of a measured point, collapsed from the OPC UA StatusCode."""

    GOOD = "GOOD"
    UNCERTAIN = "UNCERTAIN"
    BAD = "BAD"
    MISSING = "MISSING"  # point not present / never bound


class SwitchState(StrEnum):
    """Position of a switching device.

    Maps IEC 61850 Dbpos, but with one addition that matters (AGENTS.md I2):
    `UNDETERMINED` is what we report whenever quality is not GOOD. We never
    turn bad data into a position.
    """

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    INTERMEDIATE = "INTERMEDIATE"
    UNDETERMINED = "UNDETERMINED"


#: Dbpos encoding measured on OneATS DataServer 4.2, 2026-08-04.
#: See docs/30-integration/oneats-dataserver.md section 5.
DBPOS: dict[int, SwitchState] = {
    0: SwitchState.INTERMEDIATE,
    1: SwitchState.OPEN,
    2: SwitchState.CLOSED,
    3: SwitchState.UNDETERMINED,  # Dbpos 3 = BAD, which is not a position
}


class DeviceRole(StrEnum):
    """Electrical role of a switching device inside its bay."""

    BREAKER = "breaker"
    BUSBAR_SELECTOR = "busbar_selector"
    TRANSFER_SELECTOR = "transfer_selector"
    LINE_DISCONNECTOR = "line_disconnector"
    TRANSFORMER_DISCONNECTOR = "transformer_disconnector"
    EARTH_SWITCH = "earth_switch"


class BayType(StrEnum):
    LINE = "LINE"
    TRANSFORMER = "TRANSFORMER"
    BUS_COUPLER = "BUS_COUPLER"
    BUS_TRANSFER = "BUS_TRANSFER"
    FEEDER_MV = "FEEDER_MV"
    BUSBAR_PROTECTION = "BUSBAR_PROTECTION"
    UNKNOWN = "UNKNOWN"


class NodeKind(StrEnum):
    INTERNAL = "internal"  # junction inside a bay
    BUSBAR = "busbar"  # the busbar itself
    EARTH = "earth"  # earth reference
    EXTERNAL = "external"  # leaves the station: line, transformer, feeder


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class PointSample(Frozen):
    """One reading of one point, with everything needed to judge it (I2)."""

    value: float | int | bool | str | None = None
    quality: Quality = Quality.MISSING
    source_timestamp: datetime | None = None
    source_ref: str | None = None

    @property
    def usable(self) -> bool:
        return self.quality is Quality.GOOD


class ValidationIssue(Frozen):
    """Something the builder could not resolve. Surfaced, never swallowed (I7)."""

    severity: Severity
    code: str
    message: str
    subject: str | None = None  # bay id / device id this is about


class Terminal(Frozen):
    """One end of a device, attached to exactly one connectivity node."""

    device_id: str
    seq: int  # 0 or 1
    node_id: str


class ConnectivityNode(Frozen):
    id: str
    kind: NodeKind
    label: str = ""
    voltage_level: str = ""


class Device(Frozen):
    id: str  # e.g. "D03.XSWI1" — stable, but NOT a NodeId
    bay_id: str
    ln: str  # logical node instance, e.g. "XSWI1"
    role: DeviceRole
    name: str = ""  # EVN designation, e.g. "271-1"
    short_name: str = ""  # EVN suffix, e.g. "-1"
    position: PointSample = PointSample()
    terminals: tuple[Terminal, ...] = ()
    source_ref: str | None = None

    @property
    def state(self) -> SwitchState:
        """Position, degraded to UNDETERMINED unless quality is GOOD (I2)."""
        if not self.position.usable:
            return SwitchState.UNDETERMINED
        raw = self.position.value
        if isinstance(raw, bool) or not isinstance(raw, int):
            return SwitchState.UNDETERMINED
        return DBPOS.get(raw, SwitchState.UNDETERMINED)


class Busbar(Frozen):
    id: str  # e.g. "BB21"
    name: str
    voltage_level: str
    index: int  # 1, 2 = main busbars; 9 = transfer busbar
    node_id: str  # the connectivity node representing it
    is_live: PointSample = PointSample()
    inferred: bool = False  # True = we invented it, DataServer had no object
    source_ref: str | None = None


class Bay(Frozen):
    id: str  # e.g. "D03"
    name: str
    voltage_level: str
    bay_type: BayType
    template_id: str | None = None
    device_ids: tuple[str, ...] = ()
    logical_nodes: tuple[str, ...] = ()
    is_live: PointSample = PointSample()
    issues: tuple[ValidationIssue, ...] = ()
    source_ref: str | None = None


class StationGraph(Frozen):
    """The whole station as one immutable, deterministic object."""

    name: str
    model_version: str | None = None
    captured_at: datetime | None = None
    source: str = ""  # "opcua://..." or "fixture:<file>"
    voltage_levels: tuple[str, ...] = ()
    busbars: tuple[Busbar, ...] = ()
    bays: tuple[Bay, ...] = ()
    devices: tuple[Device, ...] = ()
    nodes: tuple[ConnectivityNode, ...] = ()
    issues: tuple[ValidationIssue, ...] = Field(default=())

    def device(self, device_id: str) -> Device | None:
        return next((d for d in self.devices if d.id == device_id), None)

    def bay(self, bay_id: str) -> Bay | None:
        return next((b for b in self.bays if b.id == bay_id), None)

    def devices_of(self, bay_id: str) -> tuple[Device, ...]:
        return tuple(d for d in self.devices if d.bay_id == bay_id)

    def all_issues(self) -> tuple[ValidationIssue, ...]:
        return self.issues + tuple(i for b in self.bays for i in b.issues)
