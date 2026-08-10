"""How a OneATS project spells the things the importers look for.

Two stations have been browsed and they disagree on spelling, not on structure.
Keeping the differences in one place means `dump.py` and `opcua/discovery.py`
each stay a single browse strategy instead of growing a second one.

    DEMO_SAS v654 (measured 2026-08-04)  T220PHOCAO v1052 (measured 2026-08-10)
    /SAS/220kV/D03/XCBR1                 /T220PCA/S220kV/D03_DBT/D03/XCBR1
    /SAS/220kV/D03/BCU                   /T220PCA/S220kV/D03_DBT/D03BCU
    /SAS/AT1/YPTR                        /T220PCA/AT1/DT1/YPTR

Three differences, one function each:

1. the voltage level may carry a letter prefix — `S220kV`, not `220kV`
2. a bay may be wrapped in a group named `<bay>_<label>`, which holds the bay
   beside its IEDs instead of below them
3. inside such a group the IEDs carry the bay id as a prefix — `D03BCU`, not
   `BCU`

Re-measure with `python tools/probe_dataserver.py`.
"""

from __future__ import annotations

import re

#: `220kV`, and also `S220kV` — T220PHOCAO prefixes every voltage level with a
#: letter. The prefix carries no information the model uses, so it is dropped:
#: `domain/topology.py` keys its EVN busbar codes on the bare `220kV`.
_VOLTAGE_LEVEL_RE = re.compile(r"^[A-Za-z]*(\d+(?:\.\d+)?)kV$")

#: LN prefixes that make a node a switching device, and therefore make its
#: parent a bay rather than a grouping node. Same list as
#: `domain/topology.SWITCHING_PREFIXES`, restated here because integration/
#: must not depend on how the domain later uses it.
SWITCHING_PREFIXES = ("XCBR", "XSWI")


def voltage_level(browse_name: str) -> str | None:
    """Canonical voltage level of a browse name, or `None` if it is not one.

    `"220kV"` and `"S220kV"` both give `"220kV"`. Everything downstream — the
    busbar codes, the diagram ordering, `vl:220kV` scope refs — sees one
    spelling regardless of which project is loaded.
    """
    match = _VOLTAGE_LEVEL_RE.match(browse_name)
    return f"{match.group(1)}kV" if match else None


def bay_within(group_name: str, children: frozenset[str]) -> str | None:
    """Name of the bay inside a bay *group*, or `None` when there is no group.

    T220PHOCAO wraps each bay in `<bay>_<label>` (`D03_DBT`, `EBB_Busbar`) and
    puts the bay's IEDs beside the bay, not below it. DEMO_SAS has no such
    wrapper, so this returns `None` there and the caller treats the node it
    already has as the bay.

    Deliberately not "the child that has switching logical nodes": DEMO's `DBB`
    has none (it is busbar *protection*, not a bay — AGENTS.md §7) and would be
    descended into by such a rule. Matching the name before `_` is narrower and
    both measured stations satisfy it.
    """
    head, sep, _ = group_name.partition("_")
    return head if sep and head in children else None


def strip_bay_prefix(bay_id: str, name: str) -> str:
    """`("DBB", "DBBF87B1")` -> `"F87B1"`. Unprefixed names pass through.

    The IEDs beside a bay are what `domain/bay_types.py` classifies a busbar
    protection object by, and it knows them under DEMO_SAS's bare spelling.
    Stripping here keeps that rule reading one vocabulary.
    """
    stripped = name.removeprefix(bay_id)
    return stripped if stripped and not stripped[0].isdigit() else name


def is_switching(ln_name: str) -> bool:
    return ln_name.startswith(SWITCHING_PREFIXES)


__all__ = [
    "SWITCHING_PREFIXES",
    "bay_within",
    "is_switching",
    "strip_bay_prefix",
    "voltage_level",
]
