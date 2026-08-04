"""Browse a live OneATS DataServer into a neutral `StationObs`.

READ-ONLY (AGENTS.md I1). This module browses and reads. It never calls a
OneATS write surface, and the client it builds is never handed outward.

Strategy: targeted browse rather than a full dump. We walk
`/SAS/<voltage level>/<bay>/<logical node>` and batch-read only the data
attributes topology needs (`PosSt`, `Name`, `SName`, `IsLive`). On DEMO_SAS
that is ~500 values instead of ~6000 nodes.

Measured shape, 2026-08-04, DEMO_SAS v654 — see
docs/30-integration/oneats-dataserver.md.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from asyncua import Client, ua

from blackinterface.domain.models import PointSample, Quality
from blackinterface.domain.observation import BayObs, BusbarObs, LogicalNodeObs, StationObs

SAS_PATH = ["2:Root", "2:EVN", "2:RLDC", "2:PROJECT", "2:SAS"]
VOLTAGE_LEVEL_RE = re.compile(r"^\d+kV$")
BUSBAR_RE = re.compile(r"^BB\d{2}$")

POSITION_DA = "PosSt"
NAME_DA = "Name"
SHORT_NAME_DA = "SName"
LIVE_DA = "IsLive"

WANTED_BAY_DA = (POSITION_DA, NAME_DA, SHORT_NAME_DA)
WANTED_BUSBAR_DA = (NAME_DA, LIVE_DA)


def _quality(status: Any) -> Quality:
    if status is None:
        return Quality.MISSING
    name = getattr(status, "name", str(status)).lower()
    if name.startswith("good"):
        return Quality.GOOD
    if name.startswith("uncertain"):
        return Quality.UNCERTAIN
    return Quality.BAD


def _sample(value: ua.DataValue | None, source_ref: str | None) -> PointSample:
    if value is None:
        return PointSample(source_ref=source_ref)
    raw = value.Value.Value if value.Value is not None else None
    quality = _quality(value.StatusCode)
    if raw is None and quality is Quality.GOOD:
        quality = Quality.BAD
    return PointSample(
        value=raw if isinstance(raw, bool | int | float | str) else None,
        quality=quality,
        source_timestamp=value.SourceTimestamp,
        source_ref=source_ref,
    )


async def _children(node: Any) -> list[Any]:
    """Browse children, de-duplicated by NodeId.

    OneATS exposes the same child through more than one reference type, so a
    raw `get_children()` returns it several times. Left unchecked that silently
    multiplied every device by four in an early version of this importer.
    """
    seen: dict[str, Any] = {}
    for child in await node.get_children():
        seen.setdefault(child.nodeid.to_string(), child)
    return list(seen.values())


async def _read_batch(client: Client, nodes: list[Any]) -> list[ua.DataValue]:
    """Read many nodes in one service call, with status code and timestamp."""
    if not nodes:
        return []
    values: list[ua.DataValue] = await client.read_attributes(nodes, ua.AttributeIds.Value)
    return values


async def discover_station(
    url: str,
    *,
    username: str | None = None,
    password: str | None = None,
    timeout: float = 30.0,
) -> StationObs:
    """Connect, browse `/SAS`, and return what is there.

    `username`/`password` should be a read-only account (AGENTS.md I1). Passing
    neither connects anonymously, which the DEMO server allows but a real
    station must not.
    """
    client = Client(url=url, timeout=timeout)
    if username:
        client.set_user(username)
        if password:
            client.set_password(password)

    async with client:
        name = await _read_model_attribute(client, "ModelName") or "UNKNOWN"
        model_version = await _read_model_attribute(client, "ModelVersion")
        sas = await client.nodes.objects.get_child(SAS_PATH)
        bays = await _discover_bays(client, sas)
        busbars = await _discover_busbars(client, sas)

    return StationObs(
        name=name,
        model_version=model_version,
        captured_at=datetime.now(UTC),
        source=url,
        bays=tuple(bays),
        busbars=tuple(busbars),
    )


async def _read_model_attribute(client: Client, attribute: str) -> str | None:
    try:
        node = await client.nodes.objects.get_child(["2:OADataModel", f"2:{attribute}"])
        return str(await node.read_value())
    except Exception:
        return None


async def _discover_bays(client: Client, sas: Any) -> list[BayObs]:
    """Two passes: browse the tree, then read every value in one batch."""
    layout: list[tuple[str, str, Any, dict[str, Any]]] = []  # vl, bay, bay node, ln nodes
    read_nodes: list[Any] = []
    read_keys: list[tuple[str, ...]] = []

    for level in await _children(sas):
        level_name = (await level.read_browse_name()).Name
        if not VOLTAGE_LEVEL_RE.match(level_name):
            continue
        for bay in await _children(level):
            bay_name = (await bay.read_browse_name()).Name
            logical_nodes: dict[str, Any] = {}
            for child in await _children(bay):
                child_name = (await child.read_browse_name()).Name
                node_class = await child.read_node_class()
                if node_class == ua.NodeClass.Variable and child_name == LIVE_DA:
                    read_nodes.append(child)
                    read_keys.append((bay_name, LIVE_DA))
                    continue
                if node_class != ua.NodeClass.Object:
                    continue
                logical_nodes[child_name] = child
                for attribute in await _children(child):
                    attribute_name = (await attribute.read_browse_name()).Name
                    if attribute_name in WANTED_BAY_DA:
                        read_nodes.append(attribute)
                        read_keys.append((bay_name, child_name, attribute_name))
            layout.append((level_name, bay_name, bay, logical_nodes))

    values = dict(zip(read_keys, await _read_batch(client, read_nodes), strict=True))

    result = []
    for level_name, bay_name, bay_node, logical_nodes in layout:
        observations = []
        for ln_name, ln_node in sorted(logical_nodes.items()):
            position = values.get((bay_name, ln_name, POSITION_DA))
            name = values.get((bay_name, ln_name, NAME_DA))
            short = values.get((bay_name, ln_name, SHORT_NAME_DA))
            observations.append(
                LogicalNodeObs(
                    ln=ln_name,
                    name=_scalar(name),
                    short_name=_scalar(short),
                    position=_sample(position, ln_node.nodeid.to_string()),
                    source_ref=ln_node.nodeid.to_string(),
                )
            )
        result.append(
            BayObs(
                id=bay_name,
                name=bay_name,
                voltage_level=level_name,
                logical_nodes=tuple(observations),
                is_live=_sample(values.get((bay_name, LIVE_DA)), None),
                source_ref=bay_node.nodeid.to_string(),
            )
        )
    return result


async def _discover_busbars(client: Client, sas: Any) -> list[BusbarObs]:
    try:
        subs = await sas.get_child(["2:Subs"])
    except Exception:
        return []

    layout: list[tuple[str, Any]] = []
    read_nodes: list[Any] = []
    read_keys: list[tuple[str, ...]] = []
    for child in await _children(subs):
        name = (await child.read_browse_name()).Name
        if not BUSBAR_RE.match(name) or await child.read_node_class() != ua.NodeClass.Object:
            continue
        layout.append((name, child))
        for attribute in await _children(child):
            attribute_name = (await attribute.read_browse_name()).Name
            if attribute_name in WANTED_BUSBAR_DA:
                read_nodes.append(attribute)
                read_keys.append((name, attribute_name))

    values = dict(zip(read_keys, await _read_batch(client, read_nodes), strict=True))
    return [
        BusbarObs(
            id=name,
            name=_scalar(values.get((name, NAME_DA))) or name,
            is_live=_sample(values.get((name, LIVE_DA)), node.nodeid.to_string()),
            source_ref=node.nodeid.to_string(),
        )
        for name, node in layout
    ]


def _scalar(value: ua.DataValue | None) -> str:
    if value is None or value.Value is None or value.Value.Value is None:
        return ""
    return str(value.Value.Value)
