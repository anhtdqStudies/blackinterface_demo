"""Read a dumped OneATS address space into a neutral `StationObs`.

The dump is the flat node list produced by:

    python tools/probe_dataserver.py --dump --depth 4 --out <file>.json

Same output as the live browser in `opcua/discovery.py`, so every layer above
this one runs identically with the DataServer switched off. That is what makes
the topology work testable and demoable on a laptop. The two importers share
`integration/naming.py`, which is where the shapes below are reconciled.

Address-space shapes measured so far:

    DEMO_SAS v654, 2026-08-04
        /SAS/<voltage level>/<bay>/<logical node>/<data attribute>
        /SAS/Subs/<busbar>/<data attribute>

    T220PHOCAO v1052, 2026-08-10
        /T220PCA/<voltage level>/<bay group>/<bay>/<logical node>/<...>
        /T220PCA/Subs/<busbar>/<data attribute>

See docs/30-integration/oneats-dataserver.md.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from blackinterface.domain.measurement import (
    BAY_MEASURANDS,
    BUSBAR_MEASURANDS,
    TRANSFORMER_MEASURANDS,
    wanted_das,
)
from blackinterface.domain.models import PointSample, Quality
from blackinterface.domain.observation import (
    BayObs,
    BusbarObs,
    LogicalNodeObs,
    MeasurandObs,
    StationObs,
    TransformerObs,
)
from blackinterface.integration.naming import bay_within, strip_bay_prefix, voltage_level

BUSBAR_RE = re.compile(r"^BB\d{2}$")

#: `{parent path: {child name: record}}` — the shape every walker below reads.
Children = dict[str, dict[str, dict[str, Any]]]

#: A station-level group is a power transformer when it carries one of these
#: logical nodes. Measured on DEMO_SAS (2026-08-05): /SAS/AT1/YPTR, .../YLTC.
TRANSFORMER_LNS = ("YPTR", "YLTC")

#: Data attributes we lift out of a logical node.
POSITION_DA = "PosSt"
NAME_DA = "Name"
SHORT_NAME_DA = "SName"


def _quality(raw: str | None) -> Quality:
    if not raw:
        return Quality.MISSING
    lowered = raw.lower()
    if lowered.startswith("good"):
        return Quality.GOOD
    if lowered.startswith("uncertain"):
        return Quality.UNCERTAIN
    return Quality.BAD


def _timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _coerce(value: Any) -> float | int | bool | str | None:
    """Older dumps stringified everything; recover ints so Dbpos still works."""
    if isinstance(value, bool | int | float) or value is None:
        return value
    text = str(value)
    if text.startswith("<err"):
        return None
    try:
        return int(text)
    except ValueError:
        return text


def _sample(record: dict[str, Any] | None) -> PointSample:
    if record is None:
        return PointSample()
    value = _coerce(record.get("value"))
    quality = _quality(record.get("quality"))
    # A read that errored has no usable value whatever the status code says.
    if value is None and quality is Quality.GOOD:
        quality = Quality.BAD
    return PointSample(
        value=value,
        quality=quality,
        source_timestamp=_timestamp(record.get("src_ts")),
        source_ref=record.get("nodeid"),
    )


def _text(record: dict[str, Any] | None) -> str:
    if record is None:
        return ""
    value = record.get("value")
    return "" if value is None or str(value).startswith("<err") else str(value)


def parse_dump(
    records: Iterable[dict[str, Any]],
    source: str = "",
    meta: dict[str, Any] | None = None,
) -> StationObs:
    """Turn the flat node list into an observation. Pure; no I/O."""
    meta = meta or {}
    by_path: dict[str, dict[str, Any]] = {}
    for record in records:
        path = record.get("path")
        if isinstance(path, str):
            by_path[path] = record

    # Group data attributes by their parent path.
    children: Children = {}
    for path, record in by_path.items():
        parent, _, name = path.rpartition("/")
        children.setdefault(parent, {})[name] = record

    levels = _voltage_levels(children)
    root = _station_root(levels)
    bays = [
        _build_bay(voltage, path, bay_id, beside, children)
        for voltage, path, bay_id, beside in _find_bays(levels, children)
    ]
    busbars = [
        _build_busbar(f"{root}/Subs/{name}", record, children)
        for name, record in sorted(children.get(f"{root}/Subs", {}).items())
        if BUSBAR_RE.match(name) and record.get("class") == "Object"
    ]
    transformers = [
        _build_transformer(path, by_path[path], lns, children)
        for path, lns in _find_transformers(root, children)
    ]
    return StationObs(
        name=str(meta.get("ModelName") or ""),
        model_version=str(meta["ModelVersion"]) if meta.get("ModelVersion") else None,
        captured_at=_timestamp(meta.get("captured_at")),
        source=source,
        bays=tuple(bays),
        busbars=tuple(busbars),
        transformers=tuple(transformers),
    )


def _voltage_levels(children: Children) -> dict[str, str]:
    """`{path of the voltage level: its canonical name}`.

    Found by shape rather than by looking the node up: a dump may have been
    trimmed (`--slim`) and need not contain a record for the level itself, but
    every path below it still spells the level out.
    """
    levels: dict[str, str] = {}
    for parent in children:
        parts = parent.split("/")
        for i, part in enumerate(parts):
            level = voltage_level(part)
            if level:
                levels["/".join(parts[: i + 1])] = level
                break
    return levels


def _station_root(levels: dict[str, str]) -> str:
    """Where the dump was rooted — `/SAS` on DEMO_SAS, `/T220PCA` on T220PHOCAO.

    The probe tool walks from the station node, so the root carries the
    project's name, not one we may assume. It is whatever sits above the
    voltage levels.
    """
    return min(levels, default="").rsplit("/", 1)[0]


def _objects(children: Children, path: str) -> dict[str, dict[str, Any]]:
    return {
        name: record
        for name, record in children.get(path, {}).items()
        if record.get("class") == "Object"
    }


#: `(voltage level, bay path, bay id, names of IEDs standing beside the bay)`.
FoundBay = tuple[str, str, str, tuple[str, ...]]


def _find_bays(levels: dict[str, str], children: Children) -> list[FoundBay]:
    """Every bay in the dump, however this project nests them.

    Mirrors `discovery._bays_under`: a bay is either a voltage level's child or,
    where the project wraps it, that child's namesake one level down.
    """
    found: list[FoundBay] = []
    for level_path, level in sorted(levels.items()):
        for group_name in sorted(_objects(children, level_path)):
            group_path = f"{level_path}/{group_name}"
            names = frozenset(_objects(children, group_path))
            inner = bay_within(group_name, names)
            if inner is None:
                found.append((level, group_path, group_name, ()))
                continue
            beside = tuple(sorted(strip_bay_prefix(inner, name) for name in names if name != inner))
            found.append((level, f"{group_path}/{inner}", inner, beside))
    return found


def _find_transformers(root: str, children: Children) -> list[tuple[str, dict[str, Any]]]:
    """`(path of the transformer group, its logical-node records)`.

    Mirrors `discovery._transformer_lns`: the `YPTR`/`YLTC` pair identifies a
    transformer, and it may sit one level below the group that names it.
    """
    found = []
    for name in sorted(children.get(root, {})):
        if voltage_level(name) or name == "Subs":
            continue
        path = f"{root}/{name}"
        lns = _objects(children, path)
        if any(ln in lns for ln in TRANSFORMER_LNS):
            found.append((path, lns))
            continue
        for inner in sorted(lns):
            deeper = _objects(children, f"{path}/{inner}")
            if any(ln in deeper for ln in TRANSFORMER_LNS):
                found.append((path, deeper))
                break
    return found


def _build_bay(
    voltage_level: str,
    path: str,
    bay_id: str,
    beside: tuple[str, ...],
    children: Children,
) -> BayObs:
    record = children[path.rsplit("/", 1)[0]][bay_id]
    logical_nodes = []
    for ln_name, ln_record in sorted(_objects(children, path).items()):
        das = children.get(f"{path}/{ln_name}", {})
        measurands = _measurands(das, wanted_das(BAY_MEASURANDS, ln_name))
        if POSITION_DA not in das and NAME_DA not in das and not measurands:
            continue  # neither a switching device nor a measuring one
        logical_nodes.append(
            LogicalNodeObs(
                ln=ln_name,
                name=_text(das.get(NAME_DA)),
                short_name=_text(das.get(SHORT_NAME_DA)),
                position=_sample(das.get(POSITION_DA)),
                measurands=measurands,
                source_ref=ln_record.get("nodeid"),
            )
        )
    # Protection-only objects (DBB/EBB) have no switching LNs but must still be
    # classified, so fall back to the raw child names.
    if not logical_nodes:
        logical_nodes = [
            LogicalNodeObs(ln=name, source_ref=child.get("nodeid"))
            for name, child in sorted(_objects(children, path).items())
        ]
    named = {ln.ln for ln in logical_nodes}
    logical_nodes += [LogicalNodeObs(ln=name) for name in beside if name not in named]
    return BayObs(
        id=bay_id,
        name=bay_id,
        voltage_level=voltage_level,
        logical_nodes=tuple(sorted(logical_nodes, key=lambda ln: ln.ln)),
        is_live=_sample(children.get(path, {}).get("IsLive")),
        source_ref=record.get("nodeid"),
    )


def _build_busbar(path: str, record: dict[str, Any], children: Children) -> BusbarObs:
    busbar_id = path.rsplit("/", 1)[1]
    das = children.get(path, {})
    return BusbarObs(
        id=busbar_id,
        name=_text(das.get(NAME_DA)) or busbar_id,
        is_live=_sample(das.get("IsLive")),
        measurands=_measurands(das, wanted_das(BUSBAR_MEASURANDS)),
        source_ref=record.get("nodeid"),
    )


def _build_transformer(
    path: str, record: dict[str, Any], lns: dict[str, dict[str, Any]], children: Children
) -> TransformerObs:
    """A transformer group. Only its measuring logical nodes are kept — it has
    no switching devices of its own, and its bays are found by name pairing.

    `lns` is passed in rather than looked up because it may have come from one
    level below `path` — see `_find_transformers`.
    """
    transformer_id = path.rsplit("/", 1)[1]
    logical_nodes = []
    for ln_name, ln_record in sorted(lns.items()):
        measurands = _measurands(
            children.get(str(ln_record.get("path", "")), {}),
            wanted_das(TRANSFORMER_MEASURANDS, ln_name),
        )
        if measurands:
            logical_nodes.append(
                LogicalNodeObs(
                    ln=ln_name, measurands=measurands, source_ref=ln_record.get("nodeid")
                )
            )
    return TransformerObs(
        id=transformer_id,
        name=transformer_id,
        logical_nodes=tuple(logical_nodes),
        source_ref=record.get("nodeid"),
    )


def _measurands(das: dict[str, dict[str, Any]], wanted: frozenset[str]) -> tuple[MeasurandObs, ...]:
    """The analog attributes the catalog asked for, in a stable order.

    A wanted attribute the dump does not contain is simply absent here. That is
    a fact about coverage, and `domain/evidence.py` is where it gets reported —
    inventing an empty reading would turn "we never read it" into "it read
    nothing", which are different things (I2, I7).
    """
    return tuple(
        MeasurandObs(da=name, sample=_sample(das[name])) for name in sorted(wanted) if name in das
    )


def load_dump(path: Path, station_name: str | None = None) -> StationObs:
    """Read a dump file from disk.

    Accepts both shapes the probe tool has produced: a bare list of nodes, and
    the current `{"meta": ..., "nodes": [...]}` envelope that pins the dump to a
    ModelName/ModelVersion (I7).
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        records, meta = payload.get("nodes", []), payload.get("meta", {})
    else:
        records, meta = payload, {}
    obs = parse_dump(records, source=f"fixture:{path.name}", meta=meta)
    if station_name or not obs.name:
        obs = obs.model_copy(update={"name": station_name or path.stem})
    return obs
