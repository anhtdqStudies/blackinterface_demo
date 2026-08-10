"""How two real projects spell the same station, and why the importers care.

Every fact here was browsed off a live DataServer: DEMO_SAS v654 (2026-08-04)
and T220PHOCAO v1052 (2026-08-10). Re-measure with tools/probe_dataserver.py.
"""

from __future__ import annotations

import pytest

from blackinterface.integration.naming import bay_within, strip_bay_prefix, voltage_level


@pytest.mark.parametrize(
    ("browse_name", "expected"),
    [
        ("220kV", "220kV"),  # DEMO_SAS
        ("S220kV", "220kV"),  # T220PHOCAO prefixes every level with a letter
        ("S110kV", "110kV"),
        ("S22kV", "22kV"),
        ("6.6kV", "6.6kV"),
        ("Subs", None),
        ("AT1", None),
        ("220", None),
        ("kV", None),
    ],
)
def test_voltage_level_is_read_off_the_name(browse_name: str, expected: str | None) -> None:
    assert voltage_level(browse_name) == expected


def test_the_prefix_is_dropped_so_one_spelling_reaches_the_domain() -> None:
    """`domain/topology.py` keys its EVN busbar codes on the bare form.

    `S220kV` reaching it would resolve no busbar code and every bay in the
    station would report `unknown_voltage_code`.
    """
    assert voltage_level("S220kV") == voltage_level("220kV")


def test_a_bay_group_is_recognised_by_its_namesake_child() -> None:
    """T220PHOCAO: /S220kV/D03_DBT holds the bay D03 beside its three IEDs."""
    assert bay_within("D03_DBT", frozenset({"D03", "D03BCU", "D03F211", "D03F212"})) == "D03"
    assert bay_within("EBB_Busbar", frozenset({"EBB", "EBBF87B1"})) == "EBB"


def test_a_plain_bay_is_not_descended_into() -> None:
    """DEMO_SAS: /220kV/DBB *is* the bay, and its children are logical nodes.

    A rule like "descend to the child carrying switching logical nodes" would
    get this wrong — DBB is busbar protection and carries none (AGENTS.md §7).
    """
    assert bay_within("DBB", frozenset({"BAY", "F87B1", "F87B2", "F50BF"})) is None
    assert bay_within("D03", frozenset({"XCBR1", "XSWI1", "BCU"})) is None


def test_an_underscore_without_a_namesake_child_is_not_a_group() -> None:
    assert bay_within("D03_DBT", frozenset({"BCU", "XCBR1"})) is None


@pytest.mark.parametrize(
    ("bay_id", "name", "expected"),
    [
        ("DBB", "DBBF87B1", "F87B1"),  # what bay_types.py classifies a busbar object by
        ("D03", "D03BCU", "BCU"),
        ("E08", "E08F87L", "F87L"),
        ("D03", "BCU", "BCU"),  # DEMO_SAS spelling passes through untouched
        ("D03", "D03", "D03"),
    ],
)
def test_ieds_are_stripped_back_to_the_shared_vocabulary(
    bay_id: str, name: str, expected: str
) -> None:
    assert strip_bay_prefix(bay_id, name) == expected
