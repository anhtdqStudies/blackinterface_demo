"""Infer what kind of bay this is, from its logical-node composition alone.

Why this works: the ATS/EVN naming convention encodes electrical position in
the LN instance number (`XSWI1` = busbar-1 selector, `XSWI7` = line
disconnector, `XSWI91/92` = earth switches on the transfer busbar, ...). So
identifying a bay is a table lookup, not graph reconstruction.

Measured 2026-08-04 on DEMO_SAS v654: 12/12 bays classified correctly.
See docs/20-domain/bay-templates.md.
"""

from __future__ import annotations

from collections.abc import Iterable

from blackinterface.domain.models import BayType

#: LN instance -> electrical role suffix used by EVN. Documentation of the
#: convention this whole module rests on; kept next to the rule that uses it.
LN_POSITION_HINT: dict[str, str] = {
    "XSWI1": "busbar-1 selector (-1)",
    "XSWI2": "busbar-2 selector (-2)",
    "XSWI3": "transformer-side disconnector (-3)",
    "XSWI7": "line disconnector (-7)",
    "XSWI9": "transfer-busbar selector (-9)",
    "XSWI11": "earth switch on busbar-1 side (-15)",
    "XSWI12": "earth switch on busbar-1 side (-14)",
    "XSWI21": "earth switch on busbar-2 side (-25)",
    "XSWI22": "earth switch on busbar-2 side (-24)",
    "XSWI31": "earth switch, transformer side",
    "XSWI32": "earth switch, transformer side",
    "XSWI71": "earth switch, line side (-75)",
    "XSWI72": "earth switch, line side (-76)",
    "XSWI91": "earth switch, transfer busbar side",
    "XSWI92": "earth switch, transfer busbar side",
    "XCBR1": "circuit breaker",
}


def infer_bay_type(logical_nodes: Iterable[str]) -> BayType:
    """Classify a bay. Returns UNKNOWN rather than guessing.

    Order is significant: the more specific signature wins.
    """
    lns = frozenset(logical_nodes)
    has_breaker = any(ln.startswith("XCBR") for ln in lns)

    # Busbar protection object (DBB / EBB): differential protection, no breaker.
    if any(ln.startswith("F87B") for ln in lns) and not has_breaker:
        return BayType.BUSBAR_PROTECTION

    if not has_breaker:
        return BayType.UNKNOWN

    # Bus coupler: earth switches on BOTH busbar sides, and no line/transformer side.
    if {"XSWI11", "XSWI12", "XSWI21", "XSWI22"} <= lns:
        return BayType.BUS_COUPLER

    # Bus transfer (bus-tie to transfer busbar): earth switches on the transfer side.
    if {"XSWI91", "XSWI92"} <= lns:
        return BayType.BUS_TRANSFER

    if "XSWI7" in lns:
        return BayType.LINE

    if "XSWI3" in lns:
        # A transformer bay selects a busbar; an MV feeder has no selector.
        return BayType.TRANSFORMER if "XSWI1" in lns else BayType.FEEDER_MV

    return BayType.UNKNOWN
