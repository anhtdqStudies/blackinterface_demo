"""Browse a live OneATS DataServer into a neutral `StationObs`.

READ-ONLY (AGENTS.md I1). This module browses and reads. It never calls a
OneATS write surface, and the client it builds is never handed outward.

Strategy: targeted browse rather than a full dump. We walk
`<station>/<voltage level>/<bay>/<logical node>` and batch-read only the data
attributes topology needs (`PosSt`, `Name`, `SName`, `IsLive`). On DEMO_SAS
that is ~500 values instead of ~6000 nodes.

How each of those four levels may be spelled differs between projects and lives
in `integration/naming.py` — measured on DEMO_SAS v654 (2026-08-04) and
T220PHOCAO v1052 (2026-08-10). See docs/30-integration/oneats-dataserver.md.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from asyncua import Client, ua

from blackinterface.domain.measurement import (
    BAY_MEASURANDS,
    BUSBAR_MEASURANDS,
    TRANSFORMER_MEASURANDS,
    wanted_das,
)
from blackinterface.domain.observation import (
    BayObs,
    BusbarObs,
    LogicalNodeObs,
    MeasurandObs,
    StationObs,
    TransformerObs,
)
from blackinterface.integration.naming import bay_within, strip_bay_prefix, voltage_level
from blackinterface.integration.opcua.values import to_sample

#: The DEMO_SAS station root. The path embeds the project name ("PROJECT"),
#: so it is only a fast path — other projects are found by `_find_station_root`.
KNOWN_SAS_PATH = ["2:Root", "2:EVN", "2:RLDC", "2:PROJECT", "2:SAS"]
#: Objects(0) -> Root -> EVN -> <region> -> <project> -> <station>(5). One spare.
#: T220PHOCAO's station sits at 4 (`Root/EVN/NPT_PTC1/T220PCA`, no `SAS` level).
MAX_ROOT_SEARCH_DEPTH = 6
BUSBAR_RE = re.compile(r"^BB\d{2}$")

POSITION_DA = "PosSt"
NAME_DA = "Name"
SHORT_NAME_DA = "SName"
LIVE_DA = "IsLive"

#: A station-level group is a power transformer when it carries one of these
#: logical nodes. Measured on DEMO_SAS (2026-08-05): /SAS/AT1/YPTR, .../YLTC.
TRANSFORMER_LNS = ("YPTR", "YLTC")

WANTED_BAY_DA = frozenset({POSITION_DA, NAME_DA, SHORT_NAME_DA})
WANTED_BUSBAR_DA = frozenset({NAME_DA, LIVE_DA}) | wanted_das(BUSBAR_MEASURANDS)


def _wanted_under(ln_name: str) -> frozenset[str]:
    """Data attributes to read under one logical node of a bay.

    Structure first, then whatever the measurement catalog asks for under this
    particular LN — so `MMXU1` yields six analog values and `XSWI1` yields
    none, from one loop that knows neither name.
    """
    return WANTED_BAY_DA | wanted_das(BAY_MEASURANDS, ln_name)


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


Key = tuple[str, ...]


async def _read_batch(
    client: Client, nodes: list[Any], keys: list[Key]
) -> tuple[dict[Key, ua.DataValue], dict[Key, str]]:
    """Read many nodes in one service call, keeping each one's NodeId.

    The NodeId travels on into `PointSample.source_ref`, and it must be the
    NodeId of the *variable* that produced the value — not of its parent
    logical node. That is what makes the sample traceable, and it is also the
    address the realtime subscription later monitors (see opcua/monitor.py).
    """
    if not nodes:
        return {}, {}
    values: list[ua.DataValue] = await client.read_attributes(nodes, ua.AttributeIds.Value)
    return (
        dict(zip(keys, values, strict=True)),
        {key: node.nodeid.to_string() for key, node in zip(keys, nodes, strict=True)},
    )


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
        sas = await _find_station_root(client)
        bays = await _discover_bays(client, sas)
        busbars = await _discover_busbars(client, sas)
        transformers = await _discover_transformers(client, sas)

    return StationObs(
        name=name,
        model_version=model_version,
        captured_at=datetime.now(UTC),
        source=url,
        bays=tuple(bays),
        busbars=tuple(busbars),
        transformers=tuple(transformers),
    )


async def _find_station_root(client: Client) -> Any:
    """Locate the node whose children are voltage levels (`220kV`, `S110kV`…).

    On DEMO_SAS that is `Objects/Root/EVN/RLDC/PROJECT/SAS`; on T220PHOCAO it is
    `Objects/Root/EVN/NPT_PTC1/T220PCA`, one level shallower and with no `SAS`
    node at all. The path embeds the project, so it changes with every project
    loaded into the DataServer. Try the known path first (fast), then
    breadth-first search the ns=2 object tree. The tree above the station is
    narrow — a handful of grouping nodes — so the search touches few nodes
    before it either finds a voltage level or exhausts the depth budget.
    """
    try:
        return await client.nodes.objects.get_child(KNOWN_SAS_PATH)
    except Exception:
        pass

    queue: list[tuple[Any, int]] = [(client.nodes.objects, 0)]
    while queue:
        node, depth = queue.pop(0)
        object_children = []
        for child in await _children(node):
            browse_name = await child.read_browse_name()
            if browse_name.NamespaceIndex == 0:
                continue  # Server, Types… — the standard namespace, never ours
            if voltage_level(browse_name.Name):
                return node
            if await child.read_node_class() == ua.NodeClass.Object:
                object_children.append(child)
        if depth < MAX_ROOT_SEARCH_DEPTH:
            queue.extend((child, depth + 1) for child in object_children)

    raise LookupError(
        "no station root found: no node within depth "
        f"{MAX_ROOT_SEARCH_DEPTH} of Objects has a voltage-level child "
        "(a name like '220kV' or 'S220kV'). Is a project loaded in this DataServer?"
    )


async def _read_model_attribute(client: Client, attribute: str) -> str | None:
    try:
        node = await client.nodes.objects.get_child(["2:OADataModel", f"2:{attribute}"])
        return str(await node.read_value())
    except Exception:
        return None


async def _bays_under(level: Any) -> list[tuple[str, Any, tuple[str, ...]]]:
    """Every bay under one voltage level, however this project nests them.

    Yields the bay's id, the node whose children are its logical nodes, and the
    names of the IEDs standing *beside* it rather than below. Only the nested
    shape has those, and `domain/bay_types.py` needs them: a busbar protection
    object is recognised by its `F87B*` relays, which T220PHOCAO keeps as
    siblings (`DBB` + `DBBF87B1`) where DEMO_SAS keeps them as children.
    """
    result: list[tuple[str, Any, tuple[str, ...]]] = []
    for group in await _children(level):
        if await group.read_node_class() != ua.NodeClass.Object:
            continue
        group_name = (await group.read_browse_name()).Name
        objects: dict[str, Any] = {}
        for child in await _children(group):
            if await child.read_node_class() == ua.NodeClass.Object:
                objects[(await child.read_browse_name()).Name] = child

        inner = bay_within(group_name, frozenset(objects))
        if inner is None:
            result.append((group_name, group, ()))
            continue
        beside = tuple(sorted(strip_bay_prefix(inner, name) for name in objects if name != inner))
        result.append((inner, objects[inner], beside))
    return result


async def _discover_bays(client: Client, sas: Any) -> list[BayObs]:
    """Two passes: browse the tree, then read every value in one batch."""
    layout: list[tuple[str, str, Any, dict[str, Any], tuple[str, ...]]] = []
    read_nodes: list[Any] = []
    read_keys: list[Key] = []

    for level in await _children(sas):
        level_name = voltage_level((await level.read_browse_name()).Name)
        if level_name is None:
            continue
        for bay_name, bay, beside in await _bays_under(level):
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
                wanted = _wanted_under(child_name)
                for attribute in await _children(child):
                    attribute_name = (await attribute.read_browse_name()).Name
                    if attribute_name in wanted:
                        read_nodes.append(attribute)
                        read_keys.append((bay_name, child_name, attribute_name))
            layout.append((level_name, bay_name, bay, logical_nodes, beside))

    values, refs = await _read_batch(client, read_nodes, read_keys)

    result = []
    for level_name, bay_name, bay_node, logical_nodes, beside in layout:
        observations = [LogicalNodeObs(ln=name) for name in beside if name not in logical_nodes]
        for ln_name, ln_node in sorted(logical_nodes.items()):
            position_key = (bay_name, ln_name, POSITION_DA)
            observations.append(
                LogicalNodeObs(
                    ln=ln_name,
                    name=_scalar(values.get((bay_name, ln_name, NAME_DA))),
                    short_name=_scalar(values.get((bay_name, ln_name, SHORT_NAME_DA))),
                    position=to_sample(values.get(position_key), refs.get(position_key)),
                    measurands=_measurands(
                        values, refs, (bay_name, ln_name), wanted_das(BAY_MEASURANDS, ln_name)
                    ),
                    source_ref=ln_node.nodeid.to_string(),
                )
            )
        result.append(
            BayObs(
                id=bay_name,
                name=bay_name,
                voltage_level=level_name,
                logical_nodes=tuple(sorted(observations, key=lambda ln: ln.ln)),
                is_live=to_sample(values.get((bay_name, LIVE_DA)), refs.get((bay_name, LIVE_DA))),
                source_ref=bay_node.nodeid.to_string(),
            )
        )
    return result


async def _transformer_lns(group: Any) -> dict[str, Any] | None:
    """The logical nodes of a power transformer, or `None` if this is not one.

    DEMO_SAS hangs `YPTR`/`YLTC` directly off `/SAS/AT1`. T220PHOCAO puts a
    device between them (`/T220PCA/AT1/DT1/YPTR`) and stands the transformer's
    relays beside it, so one level of descent is tried before giving up. The
    test is the logical nodes themselves, not the name — `ACQUY`, `COMM` and
    `Program` are station-level groups too, and only this rejects them.
    """
    children = {(await c.read_browse_name()).Name: c for c in await _children(group)}
    if any(ln in children for ln in TRANSFORMER_LNS):
        return children
    for child in children.values():
        if await child.read_node_class() != ua.NodeClass.Object:
            continue
        inner = {(await c.read_browse_name()).Name: c for c in await _children(child)}
        if any(ln in inner for ln in TRANSFORMER_LNS):
            return inner
    return None


async def _discover_transformers(client: Client, sas: Any) -> list[TransformerObs]:
    """Station-level siblings of the voltage levels that carry YPTR/YLTC.

    `YLTC` also holds the tap changer's write surfaces (`TapChg`, `MasCtl`,
    `EmerCtl`, `ParCtl` are Methods — browsed 2026-08-06). We read `TapPos` and
    nothing else; invoking any of those methods is forbidden outside `control/`
    and `tools/check.py` enforces it (AGENTS.md I1).
    """
    layout: list[tuple[str, Any, dict[str, Any]]] = []  # id, node, measuring LNs
    read_nodes: list[Any] = []
    read_keys: list[Key] = []

    for child in await _children(sas):
        name = (await child.read_browse_name()).Name
        if voltage_level(name) or name == "Subs":
            continue
        if await child.read_node_class() != ua.NodeClass.Object:
            continue
        grandchildren = await _transformer_lns(child)
        if grandchildren is None:
            continue
        measuring: dict[str, Any] = {}
        for ln_name, ln_node in sorted(grandchildren.items()):
            wanted = wanted_das(TRANSFORMER_MEASURANDS, ln_name)
            if not wanted:
                continue
            measuring[ln_name] = ln_node
            for attribute in await _children(ln_node):
                attribute_name = (await attribute.read_browse_name()).Name
                if attribute_name in wanted:
                    read_nodes.append(attribute)
                    read_keys.append((name, ln_name, attribute_name))
        layout.append((name, child, measuring))

    values, refs = await _read_batch(client, read_nodes, read_keys)
    return [
        TransformerObs(
            id=name,
            name=name,
            logical_nodes=tuple(
                LogicalNodeObs(
                    ln=ln_name,
                    measurands=_measurands(
                        values, refs, (name, ln_name), wanted_das(TRANSFORMER_MEASURANDS, ln_name)
                    ),
                    source_ref=ln_node.nodeid.to_string(),
                )
                for ln_name, ln_node in sorted(measuring.items())
            ),
            source_ref=node.nodeid.to_string(),
        )
        for name, node, measuring in layout
    ]


def _measurands(
    values: dict[Key, ua.DataValue],
    refs: dict[Key, str],
    owner: Key,
    wanted: frozenset[str],
) -> tuple[MeasurandObs, ...]:
    """The analog attributes the catalog asked for, in a stable order.

    An attribute the server did not return is left out rather than recorded as
    an empty reading: "never read" and "read nothing" are different facts, and
    the first belongs in `Coverage.missing` (I2, I7).
    """
    found = []
    for name in sorted(wanted):
        key = (*owner, name)
        if key in values:
            found.append(MeasurandObs(da=name, sample=to_sample(values[key], refs.get(key))))
    return tuple(found)


async def _discover_busbars(client: Client, sas: Any) -> list[BusbarObs]:
    try:
        subs = await sas.get_child(["2:Subs"])
    except Exception:
        return []

    layout: list[tuple[str, Any]] = []
    read_nodes: list[Any] = []
    read_keys: list[Key] = []
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

    values, refs = await _read_batch(client, read_nodes, read_keys)
    return [
        BusbarObs(
            id=name,
            name=_scalar(values.get((name, NAME_DA))) or name,
            is_live=to_sample(values.get((name, LIVE_DA)), refs.get((name, LIVE_DA))),
            measurands=_measurands(values, refs, (name,), wanted_das(BUSBAR_MEASURANDS)),
            source_ref=node.nodeid.to_string(),
        )
        for name, node in layout
    ]


def _scalar(value: ua.DataValue | None) -> str:
    if value is None or value.Value is None or value.Value.Value is None:
        return ""
    return str(value.Value.Value)
