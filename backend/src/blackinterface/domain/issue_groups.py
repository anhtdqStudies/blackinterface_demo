"""Which UI surface owns each validation issue (screens.md §2, GĐ 1.5 lô 3).

Group A/B belong on the engineer surface; group C on the operator `anomalies`
pane. The backend is the only place that classifies — the frontend filters on
`group`, never on a hard-coded list of codes.
"""

from __future__ import annotations

from typing import Literal

IssueGroup = Literal["A", "B", "C"]

GROUP_A: frozenset[str] = frozenset(
    {
        "bay_type_unknown",
        "template_missing",
        "slot_missing",
        "slot_unmapped",
    }
)

GROUP_B: frozenset[str] = frozenset(
    {
        "busbar_not_in_source",
        "busbar_unreferenced",
        "unknown_voltage_code",
        "transformer_unpaired",
        "transformer_winding_unresolved",
    }
)

GROUP_C: frozenset[str] = frozenset(
    {
        "earthed_while_live",
        "energization_conflict",
        "energization_mismatch",
    }
)

ALL_KNOWN: frozenset[str] = GROUP_A | GROUP_B | GROUP_C


def issue_group(code: str) -> IssueGroup:
    if code in GROUP_A:
        return "A"
    if code in GROUP_B:
        return "B"
    if code in GROUP_C:
        return "C"
    raise ValueError(f"unknown issue code: {code!r}")
