#!/usr/bin/env python3
"""Re-verify the measured facts in docs/30-integration/oneats-dataserver.md.

Run this at the START of any session that touches OPC UA. It tells you which
documented facts still hold and which have drifted, so you never build on a
stale assumption.

READ-ONLY. Never calls a write method (AGENTS.md I1).

    python tools/verify_dataserver.py
    python tools/verify_dataserver.py --url opc.tcp://host:48050

Exit 0 = every fact confirmed. Exit 1 = at least one drifted -> update the doc
(with a new measurement date) before relying on it.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from dataclasses import dataclass
from typing import Any

from asyncua import Client, ua

DEFAULT_URL = "opc.tcp://127.0.0.1:48050"
SAS_PATH = ["2:Root", "2:EVN", "2:RLDC", "2:PROJECT", "2:SAS"]
DOC = "docs/30-integration/oneats-dataserver.md"

# Baseline measured 2026-08-04 on model DEMO_SAS v654.
BASELINE = {
    "transport": "uatcp-uasc-uabinary",
    "model_name": "DEMO_SAS",
    "switching_devices": 80,
    "bay_types": {
        "D01": "TRANSFORMER", "D03": "LINE", "D04": "LINE",
        "D12": "BUS_TRANSFER", "D17": "BUS_COUPLER", "DBB": "BUSBAR",
        "E01": "LINE", "E02": "LINE", "E04": "BUS_TRANSFER",
        "E05": "BUS_COUPLER", "E07": "TRANSFORMER", "EBB": "BUSBAR",
        "J01": "FEEDER_MV",
    },
    "evn_names": {"D03.XCBR1": "271", "D17.XCBR1": "212", "E05.XCBR1": "112"},
}

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
if sys.platform == "win32":
    try:
        import colorama  # type: ignore[import-not-found]

        colorama.just_fix_windows_console()
    except Exception:  # pragma: no cover
        GREEN = RED = YELLOW = DIM = RESET = ""


@dataclass
class Result:
    drift: list[str]

    def ok(self, fact: str, detail: str = "") -> None:
        print(f"  {GREEN}CONFIRMED{RESET}  {fact}" + (f" {DIM}{detail}{RESET}" if detail else ""))

    def bad(self, fact: str, expected: Any, actual: Any) -> None:
        print(f"  {RED}DRIFTED  {RESET}  {fact}")
        print(f"             {DIM}doc says: {expected}{RESET}")
        print(f"             {DIM}actual  : {actual}{RESET}")
        self.drift.append(fact)

    def note(self, fact: str, detail: str) -> None:
        print(f"  {YELLOW}NOTE     {RESET}  {fact} {DIM}{detail}{RESET}")


def infer_bay_type(lns: set[str]) -> str:
    """Bay-type rule from LN composition. docs/20-domain/bay-templates.md."""
    if {"F87B1", "Pos", "PosSt"} & lns:
        return "BUSBAR"
    if not any(ln.startswith("XCBR") for ln in lns):
        return "BUS_TRANSFER_NO_CB"
    if {"XSWI11", "XSWI12", "XSWI21", "XSWI22"} <= lns:
        return "BUS_COUPLER"
    if {"XSWI91", "XSWI92"} <= lns:
        return "BUS_TRANSFER"
    if "XSWI7" in lns:
        return "LINE"
    if "XSWI3" in lns:
        return "TRANSFORMER" if "XSWI1" in lns else "FEEDER_MV"
    return "UNKNOWN"


async def collect_bays(client: Client) -> dict[str, set[str]]:
    sas = await client.nodes.objects.get_child(SAS_PATH)
    bays: dict[str, set[str]] = {}
    for vl_node in await sas.get_children():
        vl_name = (await vl_node.read_browse_name()).Name
        if not re.match(r"^\d+kV$", vl_name):
            continue
        for bay_node in await vl_node.get_children():
            bay = (await bay_node.read_browse_name()).Name
            lns = {(await c.read_browse_name()).Name for c in await bay_node.get_children()}
            bays[bay] = lns
    return bays


async def run(url: str) -> int:
    r = Result(drift=[])
    print(f"Verifying facts in {DOC}\n  against {url}\n")

    # ---- 1. endpoint / transport
    print("1. Endpoint")
    probe = Client(url=url, timeout=10)
    eps = await probe.connect_and_get_server_endpoints()
    transport = eps[0].TransportProfileUri.rsplit("/", 1)[-1]
    if transport == BASELINE["transport"]:
        r.ok("client-server transport (not PubSub Part 14)", transport)
    else:
        r.bad("transport profile", BASELINE["transport"], transport)
    policy = eps[0].SecurityPolicyUri.rsplit("#", 1)[-1]
    tokens = [t.TokenType.name for t in (eps[0].UserIdentityTokens or [])]
    if policy == "None" or "Anonymous" in tokens:
        r.note("endpoint unsecured", f"policy={policy} tokens={tokens} - see {DOC} section 9")

    async with Client(url=url, timeout=30) as client:
        # ---- 2. model identity
        print("\n2. Model")
        name = await (await client.nodes.objects.get_child(["2:OADataModel", "2:ModelName"])).read_value()
        version = await (await client.nodes.objects.get_child(["2:OADataModel", "2:ModelVersion"])).read_value()
        if name == BASELINE["model_name"]:
            r.ok("ModelName", f"{name} v{version}")
        else:
            r.note("different model loaded", f"doc measured {BASELINE['model_name']}, now {name} v{version}")
            print(f"\n  {YELLOW}Baseline counts below apply to {BASELINE['model_name']} only.{RESET}")

        bays = await collect_bays(client)

        # ---- 3. bay-type inference
        print("\n3. Bay-type inference from LN composition")
        mismatches = []
        for bay, expected in BASELINE["bay_types"].items():
            if bay not in bays:
                mismatches.append(f"{bay}: missing from server")
                continue
            got = infer_bay_type(bays[bay])
            if got != expected:
                mismatches.append(f"{bay}: doc={expected} actual={got}")
        if mismatches:
            r.bad("bay types 13/13", "all match", "; ".join(mismatches))
        else:
            r.ok(f"bay types {len(BASELINE['bay_types'])}/{len(BASELINE['bay_types'])} match")

        # ---- 4. auto-bind rate
        print("\n4. Auto-binding (rule-based, no SLD, no LLM)")
        devices = [
            (bay, ln)
            for bay, lns in bays.items()
            for ln in lns
            if re.match(r"^(XCBR|XSWI)\d+$", ln)
        ]
        bound = 0
        quality_good = 0
        has_ts = 0
        for bay, ln in devices:
            node = client.get_node(ua.NodeId(f"{bay}.{ln}.PosSt", 2))
            try:
                dv = await node.read_data_value()
            except Exception:
                continue
            bound += 1
            if dv.StatusCode_ is not None and dv.StatusCode_.is_good():
                quality_good += 1
            if dv.SourceTimestamp:
                has_ts += 1

        total = len(devices)
        if total == BASELINE["switching_devices"]:
            r.ok("switching device count", str(total))
        else:
            r.note("device count changed", f"doc={BASELINE['switching_devices']} actual={total}")

        for label, value in (("PosSt bound", bound), ("quality GOOD", quality_good), ("SourceTimestamp", has_ts)):
            if total and value == total:
                r.ok(f"{label} 100%", f"{value}/{total}")
            else:
                r.bad(f"{label} 100%", f"{total}/{total}", f"{value}/{total}")

        # ---- 5. EVN designations
        print("\n5. EVN designations present in address space")
        for path, expected in BASELINE["evn_names"].items():
            try:
                got = await client.get_node(ua.NodeId(f"{path}.Name", 2)).read_value()
            except Exception as exc:
                r.bad(f"{path}.Name", expected, f"<{type(exc).__name__}>")
                continue
            if str(got) == expected:
                r.ok(f"{path}.Name", str(got))
            else:
                r.bad(f"{path}.Name", expected, got)

        # ---- 6. alarm interface
        print("\n6. Alarm interface (proprietary, not OPC UA A&C)")
        alarm = await client.nodes.objects.get_child(["2:OAAlarm"])
        sas = await client.nodes.objects.get_child(SAS_PATH)
        try:
            res = await alarm.call_method(
                "2:GetActiveAlarm", ua.Variant([sas.nodeid], ua.VariantType.NodeId)
            )
            r.ok("OAAlarm.GetActiveAlarm(NodeId[]) works", f"{len(res)} active")
        except Exception as exc:
            r.bad("OAAlarm.GetActiveAlarm", "returns ExtensionObject[]", f"{type(exc).__name__}: {exc}")

    print()
    if r.drift:
        print(f"{RED}DRIFT DETECTED{RESET} - {len(r.drift)} fact(s) no longer hold:")
        for d in r.drift:
            print(f"  - {d}")
        print(f"\nUpdate {DOC} with a new measurement date before relying on it.")
        return 1
    print(f"{GREEN}ALL DOCUMENTED FACTS CONFIRMED{RESET}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default=DEFAULT_URL)
    args = p.parse_args()
    try:
        return asyncio.run(run(args.url))
    except Exception as exc:
        print(f"{RED}ERROR{RESET} {type(exc).__name__}: {exc}")
        print("Is the DataServer running? Check with: python tools/probe_dataserver.py")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
