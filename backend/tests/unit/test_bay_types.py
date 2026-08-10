"""Bay-type inference, pinned to what the live DataServer actually contains.

The LN sets below were read from DEMO_SAS v654 on 2026-08-04 with
`python tools/probe_dataserver.py --dump --slim --depth 4`. If ATS changes the
naming convention, these are the tests that should fail first.
"""

from __future__ import annotations

import pytest

from blackinterface.domain.bay_types import infer_bay_type
from blackinterface.domain.models import BayType

MEASURED: dict[str, tuple[BayType, set[str]]] = {
    "D01": (
        BayType.TRANSFORMER,
        {"XCBR1", "XSWI1", "XSWI11", "XSWI2", "XSWI3", "XSWI31", "XSWI32", "XSWI9"},
    ),
    "D03": (
        BayType.LINE,
        {"XCBR1", "XSWI1", "XSWI11", "XSWI2", "XSWI7", "XSWI71", "XSWI72", "XSWI9"},
    ),
    "D04": (
        BayType.LINE,
        {"XCBR1", "XSWI1", "XSWI11", "XSWI2", "XSWI7", "XSWI71", "XSWI72", "XSWI9"},
    ),
    "D12": (
        BayType.BUS_TRANSFER,
        {"XCBR1", "XSWI1", "XSWI11", "XSWI2", "XSWI9", "XSWI91", "XSWI92"},
    ),
    "D17": (
        BayType.BUS_COUPLER,
        {"XCBR1", "XSWI1", "XSWI11", "XSWI12", "XSWI2", "XSWI21", "XSWI22"},
    ),
    "DBB": (BayType.BUSBAR_PROTECTION, {"F50BF", "F87B1", "F87B2", "F87B3", "Pos", "RT"}),
    "E01": (
        BayType.LINE,
        {"XCBR1", "XSWI1", "XSWI11", "XSWI2", "XSWI7", "XSWI71", "XSWI72", "XSWI9"},
    ),
    "E02": (
        BayType.LINE,
        {"XCBR1", "XSWI1", "XSWI11", "XSWI2", "XSWI7", "XSWI71", "XSWI72", "XSWI9"},
    ),
    "E04": (
        BayType.BUS_TRANSFER,
        {"XCBR1", "XSWI1", "XSWI11", "XSWI2", "XSWI9", "XSWI91", "XSWI92"},
    ),
    "E05": (
        BayType.BUS_COUPLER,
        {"XCBR1", "XSWI1", "XSWI11", "XSWI12", "XSWI2", "XSWI21", "XSWI22"},
    ),
    "E07": (
        BayType.TRANSFORMER,
        {"XCBR1", "XSWI1", "XSWI11", "XSWI2", "XSWI3", "XSWI31", "XSWI32", "XSWI9"},
    ),
    "EBB": (BayType.BUSBAR_PROTECTION, {"F50BF", "F87B1", "F87B2", "F87B3", "PosSt", "RT"}),
    "J01": (BayType.FEEDER_MV, {"XCBR1", "XSWI3", "XSWI31", "XSWI32"}),
}


@pytest.mark.parametrize(
    ("bay_id", "expected", "lns"), [(k, v[0], v[1]) for k, v in sorted(MEASURED.items())]
)
def test_measured_bays_classify_correctly(bay_id: str, expected: BayType, lns: set[str]) -> None:
    assert infer_bay_type(lns) is expected, bay_id


def test_empty_bay_is_unknown() -> None:
    assert infer_bay_type(set()) is BayType.UNKNOWN


def test_breaker_alone_is_unknown_not_guessed() -> None:
    """A breaker with no disconnector matches nothing. We must not pick a type."""
    assert infer_bay_type({"XCBR1"}) is BayType.UNKNOWN


def test_measurement_only_bay_is_unknown() -> None:
    assert infer_bay_type({"MMXU1", "MSQI1", "BCU"}) is BayType.UNKNOWN


def test_bus_coupler_wins_over_line() -> None:
    """A coupler carrying a spurious XSWI7 must still classify as a coupler."""
    lns = {"XCBR1", "XSWI1", "XSWI11", "XSWI12", "XSWI2", "XSWI21", "XSWI22", "XSWI7"}
    assert infer_bay_type(lns) is BayType.BUS_COUPLER


#: The same station read on T220PHOCAO v1052, 2026-08-10. Every earth switch is
#: named after its EVN designation instead of being renumbered, so these sets
#: differ from MEASURED above in the second digit only.
MEASURED_T220PHOCAO: dict[str, tuple[BayType, set[str]]] = {
    "D03": (
        BayType.BUS_TRANSFER,
        {"XCBR1", "XSWI1", "XSWI15", "XSWI2", "XSWI9", "XSWI94", "XSWI95"},
    ),
    "D04": (
        BayType.TRANSFORMER,
        {"XCBR1", "XSWI1", "XSWI15", "XSWI2", "XSWI3", "XSWI35", "XSWI38", "XSWI9"},
    ),
    "D05": (
        BayType.LINE,
        {"XCBR1", "XSWI1", "XSWI15", "XSWI2", "XSWI7", "XSWI75", "XSWI76", "XSWI9"},
    ),
    "D07": (
        BayType.BUS_COUPLER,
        {"XCBR1", "XSWI1", "XSWI14", "XSWI15", "XSWI2", "XSWI24", "XSWI25"},
    ),
    "E18": (
        BayType.BUS_TRANSFER,
        {"XCBR1", "XSWI1", "XSWI15", "XSWI2", "XSWI9", "XSWI94", "XSWI95"},
    ),
    "J01": (BayType.FEEDER_MV, {"XCBR1", "XSWI3", "XSWI35", "XSWI38"}),
}


@pytest.mark.parametrize(
    ("bay_id", "expected", "lns"),
    [(k, v[0], v[1]) for k, v in sorted(MEASURED_T220PHOCAO.items())],
)
def test_the_evn_designation_dialect_classifies_too(
    bay_id: str, expected: BayType, lns: set[str]
) -> None:
    assert infer_bay_type(lns) is expected, bay_id


def test_a_busbar_protection_isolator_image_is_not_an_earth_switch() -> None:
    """`XSWI103` on T220PHOCAO's DBB is bay D03's -1 seen from busbar 1.

    Three digits, not two. Reading it as an earth switch would put a phantom
    side on the object and classify busbar protection as a bay.
    """
    lns = {"F87B1", "F87B2", "F87B3", "XSWI103", "XSWI110", "XSWI203", "XSWI210"}
    assert infer_bay_type(lns) is BayType.BUSBAR_PROTECTION


def test_a_transfer_selector_alone_does_not_make_a_transfer_bay() -> None:
    """Every line bay has `XSWI9`; only a bus-tie has an earth switch on it."""
    assert infer_bay_type({"XCBR1", "XSWI1", "XSWI2", "XSWI7", "XSWI9"}) is BayType.LINE
