"""OneATS alarm snapshot via ``OAAlarm.GetActiveAlarm``.

READ-ONLY (AGENTS.md I1). This module calls ``OAAlarm.GetActiveAlarm`` only.
It never invokes ``Ack*``, ``Enable``, ``Disable``, ``Delete``, or ``Change*Limit``.

**This is the snapshot path, not the realtime one.** Measured 2026-08-13:
OneATS does emit standard OPC UA Alarms & Conditions events — ``OAAlarmType``
(``ns=2;i=1101``) derives from ``AlarmConditionType`` — so live alarm changes
arrive by subscription, not by polling this method. ``GetActiveAlarm`` is what
fills the initial active set and what resynchronises after a dropped link,
because OneATS does not implement ``ConditionRefresh`` (measured: ``BadNoMatch``).

The body layout below is reverse-engineered and **self-checking**: the struct
repeats ``source_point`` as its last field, so a correct walk both reproduces
that echo and consumes the body exactly. Both are asserted on every decode.
That matters — the previous version decoded 243/243 at rest and still had the
field boundaries wrong, because every one of those bodies had an empty ``actor``.

Measured facts: ``docs/30-integration/oneats-dataserver.md`` section 7.
Fixture for the offline tests: ``backend/tests/fixtures/alarm_bodies.json``.
Re-verify with ``python tools/probe_dataserver.py --alarms``.
"""

from __future__ import annotations

import struct
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from asyncua import Client, ua

from blackinterface.integration.opcua.discovery import _find_station_root

#: ExtensionObject TypeId observed on DEMO_SAS v654 (2026-08-04).
ALARM_TYPE_ID_SUFFIX = "5803"

KNOWN_CATEGORIES = frozenset({"Discrete Alarm", "Binary Alarm", "Limit Alarm"})


class AlarmDecodeError(ValueError):
    """The field walk did not land where the struct says it should.

    Raised rather than returned so a bad decode can never be mistaken for a
    valid alarm. `analyze_alarm_batch` catches it and reports it as a decode
    error, which is what surfaces the problem instead of hiding it.
    """


@dataclass(frozen=True, slots=True)
class AlarmRecord:
    """Decoded alarm body (ns=2, TypeId *5803)."""

    event_id: str
    seq: int
    message: str | None
    severity_raw: int
    category: str | None
    source_object: str | None
    source_point: str | None
    #: Who caused it. Empty for alarms the station raised by itself; set to
    #: something like `Administrator@OneATS_DataEditor:anhtdq` when an operator
    #: drove the change. This is the field that separates a fault from somebody
    #: throwing a switch, and the event channel does **not** carry it — measured
    #: 2026-08-13, `ClientUserId` is offered in the select clause and never
    #: populated. It is the reason this snapshot path still exists.
    actor: str | None
    t_active: datetime | None
    t_change: datetime | None
    #: The alarm value, typed as the body declares it: `str` for Discrete
    #: ("2 (CLOSED)"), `bool` for Binary, `float` for Limit. Flattening these to
    #: text would throw away the only machine-readable form of a limit reading.
    value: bool | int | float | str | None
    value_type: str
    body_len: int


@dataclass(frozen=True, slots=True)
class AlarmEnvelope:
    """Raw ExtensionObject metadata before body decode."""

    type_id: str
    encoding: str
    body_len: int
    body_hex_prefix: str


@dataclass(slots=True)
class AlarmStructureReport:
    """Aggregate view of a ``GetActiveAlarm`` batch."""

    scope_node_id: str
    total: int
    decoded: int
    decode_errors: list[str] = field(default_factory=list)
    type_ids: Counter[str] = field(default_factory=Counter)
    body_lengths: Counter[int] = field(default_factory=Counter)
    categories: Counter[str] = field(default_factory=Counter)
    severities: Counter[int] = field(default_factory=Counter)
    envelopes: list[AlarmEnvelope] = field(default_factory=list)
    records: list[AlarmRecord] = field(default_factory=list)

    @property
    def decode_rate(self) -> float:
        if self.total == 0:
            return 1.0
        return self.decoded / self.total


@dataclass(frozen=True, slots=True)
class OaEventProbe:
    """What exists under ``Objects/OAEvent`` — not OPC UA A&C."""

    node_exists: bool
    child_count: int
    child_names: tuple[str, ...]


def _read_str(body: bytes, offset: int) -> tuple[str | None, int]:
    (length,) = struct.unpack_from("<i", body, offset)
    offset += 4
    if length < 0:
        return None, offset
    return body[offset : offset + length].decode("utf-8", "replace"), offset + length


def _read_filetime(body: bytes, offset: int) -> tuple[datetime | None, int]:
    (value,) = struct.unpack_from("<q", body, offset)
    offset += 8
    if value <= 0:
        return None, offset
    return datetime(1601, 1, 1, tzinfo=UTC) + timedelta(microseconds=value // 10), offset


#: OPC UA built-in type ids, as they appear in the value variant. Only the
#: three seen on DEMO_SAS are exercised; the rest are here so an unexpected
#: measurand fails with a readable width instead of a silent misparse.
_VARIANT_WIDTHS: dict[int, int] = {
    1: 1,  # Boolean
    2: 1,  # SByte
    3: 1,  # Byte
    4: 2,  # Int16
    5: 2,  # UInt16
    6: 4,  # Int32
    7: 4,  # UInt32
    8: 8,  # Int64
    9: 8,  # UInt64
    10: 4,  # Float
    11: 8,  # Double
}
_VARIANT_NAMES: dict[int, str] = {
    1: "Boolean", 2: "SByte", 3: "Byte", 4: "Int16", 5: "UInt16", 6: "Int32",
    7: "UInt32", 8: "Int64", 9: "UInt64", 10: "Float", 11: "Double", 12: "String",
}  # fmt: skip
_VARIANT_STRING = 12


def _read_variant(body: bytes, offset: int) -> tuple[str, bool | int | float | str | None, int]:
    """Read a type-tagged value: one type-id byte, then the payload."""
    type_id = body[offset]
    offset += 1
    name = _VARIANT_NAMES.get(type_id, f"Unknown({type_id})")
    if type_id == _VARIANT_STRING:
        text, offset = _read_str(body, offset)
        return name, text, offset
    width = _VARIANT_WIDTHS.get(type_id)
    if width is None:
        raise AlarmDecodeError(f"unknown value type id {type_id} at offset {offset - 1}")
    raw = body[offset : offset + width]
    offset += width
    if type_id == 1:
        return name, raw[0] != 0, offset
    if type_id == 10:
        return name, struct.unpack("<f", raw)[0], offset
    if type_id == 11:
        return name, struct.unpack("<d", raw)[0], offset
    return name, int.from_bytes(raw, "little", signed=True), offset


def decode_alarm_body(body: bytes) -> AlarmRecord:
    """Decode a OneATS alarm ExtensionObject body.

    Reverse-engineered — not an official ATS spec (question Q1) — but
    **self-checking**: the struct ends by repeating `source_point`, so a correct
    walk reproduces that echo *and* lands exactly on the end of the body. Both
    are asserted here, and a failure raises rather than returning a plausible
    wrong answer.

    That check is not decoration. The previous version read the `actor` field as
    four bytes of padding, which is indistinguishable from correct as long as
    nobody is logged in — it decoded 243/243 standing alarms and then raised
    `OverflowError` the first time an operator moved a breaker.
    """
    offset = 0
    (id_len,) = struct.unpack_from("<i", body, offset)
    offset += 4
    event_id = body[offset : offset + id_len].hex()
    offset += id_len
    (seq,) = struct.unpack_from("<i", body, offset)
    offset += 4
    offset += 4  # flags
    message, offset = _read_str(body, offset)
    severity_raw = int.from_bytes(body[offset : offset + 2], "little")
    offset += 2
    category, offset = _read_str(body, offset)
    offset += 8  # flags
    source_object, offset = _read_str(body, offset)
    source_point, offset = _read_str(body, offset)
    actor, offset = _read_str(body, offset)
    t_active, offset = _read_filetime(body, offset)
    t_change, offset = _read_filetime(body, offset)
    value_type, value, offset = _read_variant(body, offset)
    offset += 1  # tag; 0x04 on 85 of 89 sampled bodies, meaning unknown (Q1)
    echo, offset = _read_str(body, offset)

    if echo != source_point:
        raise AlarmDecodeError(
            f"trailing echo {echo!r} does not match source_point {source_point!r} — "
            "the field walk drifted"
        )
    if offset != len(body):
        raise AlarmDecodeError(f"consumed {offset} of {len(body)} bytes — the field walk drifted")

    return AlarmRecord(
        event_id=event_id,
        seq=seq,
        message=message,
        severity_raw=severity_raw,
        category=category,
        source_object=source_object,
        source_point=source_point,
        actor=actor or None,
        t_active=t_active,
        t_change=t_change,
        value=value,
        value_type=value_type,
        body_len=len(body),
    )


def _encoding_label(encoding: Any) -> str:
    if encoding is None:
        return "<missing>"
    name = getattr(encoding, "name", None)
    return str(name if name is not None else encoding)


def inspect_extension_object(ext: Any) -> AlarmEnvelope:
    """Extract envelope metadata from an asyncua ExtensionObject."""
    type_id = ext.TypeId.to_string() if ext.TypeId is not None else "<missing>"
    encoding = _encoding_label(ext.Encoding)
    body = getattr(ext, "Body", None) or b""
    prefix = body[:32].hex()
    return AlarmEnvelope(
        type_id=type_id,
        encoding=encoding,
        body_len=len(body),
        body_hex_prefix=prefix,
    )


def analyze_alarm_batch(scope_node_id: str, extension_objects: list[Any]) -> AlarmStructureReport:
    """Decode a ``GetActiveAlarm`` result and summarize its shape."""
    report = AlarmStructureReport(
        scope_node_id=scope_node_id, total=len(extension_objects), decoded=0
    )
    for index, ext in enumerate(extension_objects):
        envelope = inspect_extension_object(ext)
        report.envelopes.append(envelope)
        report.type_ids[envelope.type_id] += 1
        report.body_lengths[envelope.body_len] += 1

        body = getattr(ext, "Body", None)
        if body is None:
            report.decode_errors.append(f"[{index}] missing Body")
            continue
        try:
            record = decode_alarm_body(body)
        except Exception as exc:
            report.decode_errors.append(f"[{index}] {type(exc).__name__}: {exc}")
            continue

        report.decoded += 1
        report.records.append(record)
        if record.category:
            report.categories[record.category] += 1
        report.severities[record.severity_raw] += 1
    return report


async def probe_oa_event(client: Client) -> OaEventProbe:
    """Report whether ``OAEvent`` exposes any browsable children."""
    try:
        node = await client.nodes.objects.get_child(["2:OAEvent"])
    except Exception:
        return OaEventProbe(node_exists=False, child_count=0, child_names=())

    children = await node.get_children()
    names: list[str] = []
    for child in children:
        browse_name = await child.read_browse_name()
        names.append(browse_name.Name)
    return OaEventProbe(node_exists=True, child_count=len(children), child_names=tuple(names))


async def get_active_alarms(client: Client, scope_node: Any) -> list[Any]:
    """Call ``OAAlarm.GetActiveAlarm`` for one scope node. READ-ONLY."""
    alarm = await client.nodes.objects.get_child(["2:OAAlarm"])
    result = await alarm.call_method(
        "2:GetActiveAlarm",
        ua.Variant([scope_node.nodeid], ua.VariantType.NodeId),
    )
    return list(result)


async def fetch_alarm_structure(
    client: Client,
    scope_node: Any | None = None,
) -> AlarmStructureReport:
    """Connect path is external; this assumes an open ``Client``."""
    node = scope_node if scope_node is not None else await _find_station_root(client)
    scope_id = node.nodeid.to_string()
    batch = await get_active_alarms(client, node)
    return analyze_alarm_batch(scope_id, batch)
