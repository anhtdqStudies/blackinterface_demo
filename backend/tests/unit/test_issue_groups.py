"""Issue group classification — locked to the twelve codes in screens.md."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from blackinterface.domain import issue_groups as ig


@pytest.mark.parametrize(
    "code,expected",
    [
        ("bay_type_unknown", "A"),
        ("template_missing", "A"),
        ("slot_missing", "A"),
        ("slot_unmapped", "A"),
        ("busbar_not_in_source", "B"),
        ("busbar_unreferenced", "B"),
        ("unknown_voltage_code", "B"),
        ("transformer_unpaired", "B"),
        ("transformer_winding_unresolved", "B"),
        ("earthed_while_live", "C"),
        ("energization_conflict", "C"),
        ("energization_mismatch", "C"),
    ],
)
def test_known_codes_map_to_groups(code: str, expected: ig.IssueGroup) -> None:
    assert ig.issue_group(code) == expected


def _codes_emitted_in_domain() -> set[str]:
    """Every `code="…"` a `ValidationIssue` is built with, read off the source.

    A regex over the domain package rather than a hand-kept list, because the
    hand-kept list is the failure this test exists to catch. Issues are built in
    one shape throughout — `ValidationIssue(code="…", …)` — so the scan holds;
    if it ever stops holding, the assertion that it found at least twelve codes
    goes red rather than passing on an empty set.
    """
    domain = Path(ig.__file__).parent
    codes: set[str] = set()
    for path in domain.rglob("*.py"):
        codes |= set(re.findall(r'code="([a-z_]+)"', path.read_text(encoding="utf-8")))
    return codes


def test_every_code_emitted_in_domain_is_classified() -> None:
    """The gate, and the proof the gate is looking at something.

    `issue_group()` raises on an unknown code and `/api/issues` calls it for
    every issue — so a thirteenth code added without a group is not a missing
    label, it is a 500 on the page an operator opens to see what is wrong.
    """
    emitted = _codes_emitted_in_domain()
    assert len(emitted) >= 12, f"the scan found only {sorted(emitted)} - it has stopped working"
    assert not emitted - ig.ALL_KNOWN, (
        f"emitted but never classified: {sorted(emitted - ig.ALL_KNOWN)}"
    )
    assert not ig.ALL_KNOWN - emitted, (
        f"classified but never emitted: {sorted(ig.ALL_KNOWN - emitted)}"
    )


def test_unknown_code_raises() -> None:
    with pytest.raises(ValueError, match="unknown issue code"):
        ig.issue_group("made_up")
