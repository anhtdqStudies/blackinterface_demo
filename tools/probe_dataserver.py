#!/usr/bin/env python3
"""Probe / dump the OneATS DataServer OPC UA address space.

READ-ONLY. This tool never calls a write method (AGENTS.md I1).

Usage:
    python tools/probe_dataserver.py                     # endpoints + top-level shape
    python tools/probe_dataserver.py --dump              # full /SAS dump -> JSON
    python tools/probe_dataserver.py --dump --out x.json
    python tools/probe_dataserver.py --alarms            # active alarms, decoded
    python tools/probe_dataserver.py --url opc.tcp://host:48050

Output of --dump feeds tests as a fixture, so topology work does not need a
live DataServer. See docs/30-integration/oneats-dataserver.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import struct
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from asyncua import Client, ua

DEFAULT_URL = "opc.tcp://127.0.0.1:48050"
SAS_PATH = ["2:Root", "2:EVN", "2:RLDC", "2:PROJECT", "2:SAS"]
DBPOS = {0: "INTERMEDIATE", 1: "OPEN", 2: "CLOSED", 3: "BAD"}


# --------------------------------------------------------------- alarm decode
def _read_str(b: bytes, o: int) -> tuple[str | None, int]:
    (n,) = struct.unpack_from("<i", b, o)
    o += 4
    if n < 0:
        return None, o
    return b[o : o + n].decode("utf-8", "replace"), o + n


def _read_filetime(b: bytes, o: int) -> tuple[datetime | None, int]:
    (v,) = struct.unpack_from("<q", b, o)
    o += 8
    if v <= 0:
        return None, o
    return datetime(1601, 1, 1, tzinfo=UTC) + timedelta(microseconds=v // 10), o


def decode_alarm(body: bytes) -> dict[str, Any]:
    """Decode a OneATS alarm ExtensionObject body (ns=2, TypeId 5803).

    WARNING - reverse-engineered, not an official spec. Trailing field
    boundaries are approximate; `value_text` may over-read a few bytes.
    Action item Q1 in docs/90-progress/status.md: get the real struct from ATS.
    """
    o = 0
    (idlen,) = struct.unpack_from("<i", body, o)
    o += 4
    event_id = body[o : o + idlen].hex()
    o += idlen
    (seq,) = struct.unpack_from("<i", body, o)
    o += 4
    o += 4  # flags
    message, o = _read_str(body, o)
    severity_raw = int.from_bytes(body[o : o + 2], "little")
    o += 2
    category, o = _read_str(body, o)
    o += 8  # flags
    source_object, o = _read_str(body, o)
    source_point, o = _read_str(body, o)
    o += 4  # pad
    t_active, o = _read_filetime(body, o)
    t_change, o = _read_filetime(body, o)
    value_text, o = _read_str(body, o)
    return {
        "event_id": event_id,
        "seq": seq,
        "message": message,
        "severity_raw": severity_raw,
        "category": category,
        "source_object": source_object,
        "source_point": source_point,
        "t_active": t_active.isoformat() if t_active else None,
        "t_change": t_change.isoformat() if t_change else None,
        "value_text": value_text,
    }


# --------------------------------------------------------------- browse
async def walk(node: Any, depth: int, maxdepth: int, path: str,
               seen: dict[str, dict[str, Any]], read_values: bool) -> None:
    if depth > maxdepth:
        return
    try:
        children = await node.get_children()
    except Exception:
        return
    for nid, child in {c.nodeid.to_string(): c for c in children}.items():
        if nid in seen:
            continue
        try:
            bn = await child.read_browse_name()
            ncls = await child.read_node_class()
        except Exception:
            continue
        rec: dict[str, Any] = {
            "nodeid": nid,
            "name": bn.Name,
            "class": ncls.name,
            "path": f"{path}/{bn.Name}",
            "depth": depth,
        }
        if read_values and ncls.name == "Variable":
            try:
                dv = await child.read_data_value()
                raw = dv.Value.Value
                # Keep JSON-native scalars intact - the dump is a test fixture and
                # `PosSt` must stay an int, not become the string "2".
                rec["value"] = raw if isinstance(raw, bool | int | float | str) else str(raw)[:80]
                rec["vtype"] = str(dv.Value.VariantType)
                # asyncua 1.x calls the field StatusCode_, 2.x calls it StatusCode.
                status = getattr(dv, "StatusCode_", None) or getattr(dv, "StatusCode", None)
                rec["quality"] = status.name if status else None
                rec["src_ts"] = dv.SourceTimestamp.isoformat() if dv.SourceTimestamp else None
            except Exception as exc:
                rec["value"] = f"<err {type(exc).__name__}>"
        seen[nid] = rec
        await walk(child, depth + 1, maxdepth, rec["path"], seen, read_values)


async def show_endpoints(url: str) -> None:
    client = Client(url=url, timeout=10)
    eps = await client.connect_and_get_server_endpoints()
    print(f"endpoints: {len(eps)}")
    for e in eps:
        srv = e.Server
        print(f"  url        {e.EndpointUrl}")
        print(f"  policy     {e.SecurityPolicyUri.rsplit('#', 1)[-1]}  mode={e.SecurityMode}")
        print(f"  transport  {e.TransportProfileUri.rsplit('/', 1)[-1]}")
        print(f"  app        {srv.ApplicationUri}")
        print(f"  tokens     {[t.TokenType.name for t in (e.UserIdentityTokens or [])]}")


async def show_overview(client: Client) -> None:
    ns = await client.get_namespace_array()
    print("\nnamespaces:")
    for i, uri in enumerate(ns):
        print(f"  [{i}] {uri}")

    print("\nmodel:")
    for leaf in ("ModelName", "ModelVersion", "State"):
        try:
            node = await client.nodes.objects.get_child(["2:OADataModel", f"2:{leaf}"])
            print(f"  {leaf:<13} = {await node.read_value()}")
        except Exception as exc:
            print(f"  {leaf:<13} ! {type(exc).__name__}")

    print("\nObjects children:")
    for child in await client.nodes.objects.get_children():
        bn = await child.read_browse_name()
        print(f"  ns={child.nodeid.NamespaceIndex}  {bn.Name}")


# Data attributes the topology importer actually reads. --slim keeps only these
# (plus their parents), which turns a ~2 MB dump into a ~100 KB test fixture.
#
# Two groups, because they behave differently once the fixture is running:
# positions and IsLive are discrete and rebuild the electrical graph; the
# measurands below are analog and only relabel it (ADR-0012). The list mirrors
# domain/measurement.py — a data attribute added there must be added here too,
# or the fixture stops being able to exercise it.
SLIM_DA = {
    # structure and position
    "PosSt",
    "Name",
    "SName",
    "IsLive",
    # measurands: bay MMXU1
    "totW",
    "totVAr",
    "totPF",
    "Vlin",
    "Amax",
    "Hz",
    # measurands: busbar (Subs/BBxx) — note the lowercase m, measured 2026-08-06
    "PPVmax",
    # measurands: transformer tap changer (ATx/YLTC)
    "TapPos",
}


def slim_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep bays, logical nodes, busbars and the four data attributes we read."""
    keep = []
    for rec in records:
        parts = rec["path"].split("/")
        depth = len(parts) - 2  # /SAS/x -> 1
        if depth <= 2:  # voltage levels, bays, Subs/<busbar>
            keep.append(rec)
        elif depth == 3 and (rec["class"] == "Object" or parts[-1] in SLIM_DA):
            keep.append(rec)
        elif depth == 4 and parts[-1] in SLIM_DA:
            keep.append(rec)
    return keep


async def read_meta(client: Client) -> dict[str, Any]:
    """Model identity, so a dump can be pinned to the release it came from (I7)."""
    meta: dict[str, Any] = {"captured_at": datetime.now(UTC).isoformat(), "endpoint": None}
    for leaf in ("ModelName", "ModelVersion"):
        try:
            node = await client.nodes.objects.get_child(["2:OADataModel", f"2:{leaf}"])
            meta[leaf] = str(await node.read_value())
        except Exception:
            meta[leaf] = None
    return meta


async def dump(client: Client, out: Path, maxdepth: int, slim: bool, url: str) -> None:
    sas = await client.nodes.objects.get_child(SAS_PATH)
    seen: dict[str, dict[str, Any]] = {}
    print(f"walking /SAS (maxdepth={maxdepth}) - this takes a few minutes ...")
    await walk(sas, 0, maxdepth, "/SAS", seen, read_values=True)
    records = list(seen.values())
    total = len(records)
    if slim:
        records = slim_records(records)
    meta = await read_meta(client)
    meta["endpoint"] = url
    payload = {"meta": meta, "nodes": records}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(records)}/{total} nodes -> {out}  ({meta['ModelName']} v{meta['ModelVersion']})")


async def show_alarms(client: Client, limit: int) -> None:
    alarm = await client.nodes.objects.get_child(["2:OAAlarm"])
    sas = await client.nodes.objects.get_child(SAS_PATH)
    res = await alarm.call_method(
        "2:GetActiveAlarm", ua.Variant([sas.nodeid], ua.VariantType.NodeId)
    )
    print(f"active alarms: {len(res)}")
    rows = []
    for eo in res:
        body = getattr(eo, "Body", None)
        if body is None:
            continue
        try:
            rows.append(decode_alarm(body))
        except Exception as exc:
            rows.append({"decode_error": f"{type(exc).__name__}: {exc}"})
    good = [r for r in rows if "message" in r]
    print(f"decoded: {len(good)}/{len(rows)}\n")
    print(f"{'MESSAGE':<44} {'CATEGORY':<16} {'SOURCE POINT':<26} VALUE")
    print("-" * 110)
    for r in good[:limit]:
        print(
            f"{(r['message'] or '')[:43]:<44} {(r['category'] or '')[:15]:<16} "
            f"{(r['source_point'] or '')[:25]:<26} {(r['value_text'] or '')[:16]}"
        )


async def main_async(args: argparse.Namespace) -> None:
    await show_endpoints(args.url)
    async with Client(url=args.url, timeout=30) as client:
        await show_overview(client)
        if args.dump:
            await dump(client, Path(args.out), args.depth, args.slim, args.url)
        if args.alarms:
            await show_alarms(client, args.limit)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--dump", action="store_true", help="dump the /SAS subtree to JSON")
    p.add_argument("--out", default="sas_tree.json")
    p.add_argument("--depth", type=int, default=8)
    p.add_argument("--slim", action="store_true", help="keep only what the importer reads")
    p.add_argument("--alarms", action="store_true", help="list active alarms")
    p.add_argument("--limit", type=int, default=20)
    args = p.parse_args()
    try:
        asyncio.run(main_async(args))
    except Exception as exc:
        print(f"ERROR {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
