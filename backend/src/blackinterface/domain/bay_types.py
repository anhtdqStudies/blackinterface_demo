"""Infer what kind of bay this is, from its logical-node composition alone.

Why this works: the ATS/EVN naming convention encodes electrical position in
the LN instance number (`XSWI1` = busbar-1 selector, `XSWI7` = line
disconnector, `XSWI9x` = earth switches on the transfer busbar, ...). So
identifying a bay is a table lookup, not graph reconstruction.

The *first* digit is the convention; the second only says which of a pair.
That matters because two measured projects number the pairs differently —
DEMO_SAS renumbers them `11/12`, T220PHOCAO keeps the EVN designation `15/14`
— and the rules below deliberately read only the digit both agree on.

Measured 2026-08-04 on DEMO_SAS v654: 12/12 bays classified correctly.
Measured 2026-08-10 on T220PHOCAO v1052: 23/23.
See docs/20-domain/bay-templates.md.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from blackinterface.domain.models import BayType

#: LN instance -> electrical role, and the EVN device suffix it carries. Two
#: spellings per earth switch: DEMO_SAS's, then T220PHOCAO's. Documentation of
#: the convention this whole module rests on; kept next to the rule using it.
LN_POSITION_HINT: dict[str, str] = {
    "XSWI1": "busbar-1 selector (-1)",
    "XSWI2": "busbar-2 selector (-2)",
    "XSWI3": "transformer-side disconnector (-3)",
    "XSWI7": "line disconnector (-7)",
    "XSWI9": "transfer-busbar selector (-9)",
    "XSWI11": "earth switch on busbar-1 side (-15); T220PHOCAO spells it XSWI15",
    "XSWI12": "earth switch on busbar-1 side (-14); T220PHOCAO spells it XSWI14",
    "XSWI21": "earth switch on busbar-2 side (-25); T220PHOCAO spells it XSWI25",
    "XSWI22": "earth switch on busbar-2 side (-24); T220PHOCAO spells it XSWI24",
    "XSWI31": "earth switch, transformer side (-35); T220PHOCAO spells it XSWI35",
    "XSWI32": "earth switch, transformer side (-38); T220PHOCAO spells it XSWI38",
    "XSWI71": "earth switch, line side (-75); T220PHOCAO spells it XSWI75",
    "XSWI72": "earth switch, line side (-76); T220PHOCAO spells it XSWI76",
    "XSWI91": "earth switch, transfer busbar side; T220PHOCAO spells it XSWI95",
    "XSWI92": "earth switch, transfer busbar side; T220PHOCAO spells it XSWI94",
    "XCBR1": "circuit breaker",
}

#: An earth switch is `XSWI<side><which>` — exactly two digits. One digit is a
#: selector or disconnector (`XSWI9`), three is a per-bay isolator image on a
#: busbar protection object (`XSWI103` on DBB), and neither says anything about
#: which side of a bay we are on.
_EARTH_SWITCH_RE = re.compile(r"^XSWI([1-9])\d$")


def _earthed_sides(lns: frozenset[str]) -> frozenset[str]:
    """The leading digits of this bay's earth switches — its wired-up sides.

    `{"1", "2"}` means "earthable on both busbar sides", whether the project
    spelled that `XSWI11`/`XSWI21` or `XSWI15`/`XSWI25`.
    """
    return frozenset(
        match.group(1) for ln in lns if (match := _EARTH_SWITCH_RE.match(ln)) is not None
    )


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

    sides = _earthed_sides(lns)

    # Bus coupler: earth switches on BOTH busbar sides, and no line/transformer side.
    if {"1", "2"} <= sides:
        return BayType.BUS_COUPLER

    # Bus transfer (bus-tie to transfer busbar): earth switches on the transfer side.
    if "9" in sides:
        return BayType.BUS_TRANSFER

    if "XSWI7" in lns:
        return BayType.LINE

    if "XSWI3" in lns:
        # A transformer bay selects a busbar; an MV feeder has no selector.
        return BayType.TRANSFORMER if "XSWI1" in lns else BayType.FEEDER_MV

    return BayType.UNKNOWN
