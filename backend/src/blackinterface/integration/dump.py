"""Read a dumped OneATS address space into a neutral `StationObs`.

The dump is the flat node list produced by:

    python tools/probe_dataserver.py --dump --depth 4 --out <file>.json

Same output as the live browser in `opcua/discovery.py`, so every layer above
this one runs identically with the DataServer switched off. That is what makes
the topology work testable and demoable on a laptop.

Address-space shape, measured 2026-08-04 on DEMO_SAS v654:

    /SAS/<voltage level>/<bay>/<logical node>/<data attribute>
    /SAS/Subs/<busbar>/<data attribute>

See docs/30-integration/oneats-dataserver.md.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from blackinterface.domain.models import PointSample, Quality
from blackinterface.domain.observation import (
    BayObs,
    BusbarObs,
    LogicalNodeObs,
    StationObs,
    TransformerObs,
)

VOLTAGE_LEVEL_RE = re.compile(r"^\d+kV$")
BUSBAR_RE = re.compile(r"^BB\d{2}$")

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
    children: dict[str, dict[str, dict[str, Any]]] = {}
    for path, record in by_path.items():
        parent, _, name = path.rpartition("/")
        children.setdefault(parent, {})[name] = record

    bays = [
        _build_bay(path, record, children)
        for path, record in sorted(by_path.items())
        if _is_bay(path)
    ]
    busbars = [
        _build_busbar(path, record, children)
        for path, record in sorted(by_path.items())
        if _is_busbar(path)
    ]
    transformers = [
        TransformerObs(
            id=path.rsplit("/", 1)[1],
            name=path.rsplit("/", 1)[1],
            source_ref=record.get("nodeid"),
        )
        for path, record in sorted(by_path.items())
        if _is_transformer(path, children)
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


def _is_bay(path: str) -> bool:
    parts = path.split("/")
    return len(parts) == 4 and parts[1] == "SAS" and bool(VOLTAGE_LEVEL_RE.match(parts[2]))


def _is_busbar(path: str) -> bool:
    parts = path.split("/")
    return len(parts) == 4 and parts[1:3] == ["SAS", "Subs"] and bool(BUSBAR_RE.match(parts[3]))


def _is_transformer(path: str, children: dict[str, dict[str, dict[str, Any]]]) -> bool:
    """A station-level sibling of the voltage levels that carries YPTR/YLTC."""
    parts = path.split("/")
    if len(parts) != 3 or parts[1] != "SAS" or VOLTAGE_LEVEL_RE.match(parts[2]):
        return False
    return any(ln in children.get(path, {}) for ln in TRANSFORMER_LNS)


def _build_bay(
    path: str, record: dict[str, Any], children: dict[str, dict[str, dict[str, Any]]]
) -> BayObs:
    _, _, voltage_level, bay_id = path.split("/")
    logical_nodes = []
    for ln_name, ln_record in sorted(children.get(path, {}).items()):
        if ln_record.get("class") != "Object":
            continue
        das = children.get(f"{path}/{ln_name}", {})
        if POSITION_DA not in das and NAME_DA not in das:
            continue  # not a switching device: MMXU, BCU, protection blocks
        logical_nodes.append(
            LogicalNodeObs(
                ln=ln_name,
                name=_text(das.get(NAME_DA)),
                short_name=_text(das.get(SHORT_NAME_DA)),
                position=_sample(das.get(POSITION_DA)),
                source_ref=ln_record.get("nodeid"),
            )
        )
    # Protection-only objects (DBB/EBB) have no switching LNs but must still be
    # classified, so fall back to the raw child names.
    if not logical_nodes:
        logical_nodes = [
            LogicalNodeObs(ln=name, source_ref=child.get("nodeid"))
            for name, child in sorted(children.get(path, {}).items())
            if child.get("class") == "Object"
        ]
    return BayObs(
        id=bay_id,
        name=bay_id,
        voltage_level=voltage_level,
        logical_nodes=tuple(logical_nodes),
        is_live=_sample(children.get(path, {}).get("IsLive")),
        source_ref=record.get("nodeid"),
    )


def _build_busbar(
    path: str, record: dict[str, Any], children: dict[str, dict[str, dict[str, Any]]]
) -> BusbarObs:
    busbar_id = path.rsplit("/", 1)[1]
    das = children.get(path, {})
    return BusbarObs(
        id=busbar_id,
        name=_text(das.get(NAME_DA)) or busbar_id,
        is_live=_sample(das.get("IsLive")),
        source_ref=record.get("nodeid"),
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
