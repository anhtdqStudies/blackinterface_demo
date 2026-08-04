"""The template library is data; these tests keep it honest."""

from __future__ import annotations

import pytest

from blackinterface.domain.models import BayType, DeviceRole, NodeKind
from blackinterface.domain.templates import BUSBAR_REFS, EARTH_REF, default_registry

EXPECTED = {
    "T1_LINE": BayType.LINE,
    "T2_TRANSFORMER": BayType.TRANSFORMER,
    "T3_BUS_COUPLER": BayType.BUS_COUPLER,
    "T4_BUS_TRANSFER": BayType.BUS_TRANSFER,
    "T5_FEEDER_MV": BayType.FEEDER_MV,
    "T6_BUSBAR_PROTECTION": BayType.BUSBAR_PROTECTION,
}


def test_registry_loads_every_template() -> None:
    registry = default_registry()
    assert {t.id for t in registry.templates} == set(EXPECTED)


@pytest.mark.parametrize(("template_id", "bay_type"), sorted(EXPECTED.items()))
def test_template_declares_its_bay_type(template_id: str, bay_type: BayType) -> None:
    template = default_registry().by_id(template_id)
    assert template is not None
    assert template.bay_type is bay_type


def test_one_template_per_bay_type() -> None:
    """`for_bay_type` must be unambiguous, so no two templates may claim one type."""
    types = [t.bay_type for t in default_registry().templates]
    assert len(types) == len(set(types))


def test_every_endpoint_resolves() -> None:
    for template in default_registry().templates:
        assert template.validate_refs() == []


def test_every_slot_has_two_distinct_endpoints() -> None:
    for template in default_registry().templates:
        for slot in template.slots:
            assert len(slot.endpoints) == 2, f"{template.id}/{slot.ln}"
            assert slot.endpoints[0] != slot.endpoints[1], f"{template.id}/{slot.ln}"


def test_earth_switches_reference_earth() -> None:
    """An earth switch that does not touch EARTH is a modelling mistake."""
    for template in default_registry().templates:
        for slot in template.slots:
            touches_earth = EARTH_REF in slot.endpoints
            is_earth = slot.role is DeviceRole.EARTH_SWITCH
            assert touches_earth == is_earth, f"{template.id}/{slot.ln}"


def test_selectors_reference_a_busbar() -> None:
    selectors = (DeviceRole.BUSBAR_SELECTOR, DeviceRole.TRANSFER_SELECTOR)
    for template in default_registry().templates:
        for slot in template.slots:
            if slot.role in selectors:
                assert any(ref in BUSBAR_REFS for ref in slot.endpoints), (
                    f"{template.id}/{slot.ln} is a selector but touches no busbar"
                )


def test_every_template_has_exactly_one_breaker_except_busbar_protection() -> None:
    for template in default_registry().templates:
        breakers = [s for s in template.slots if s.role is DeviceRole.BREAKER]
        expected = 0 if template.bay_type is BayType.BUSBAR_PROTECTION else 1
        assert len(breakers) == expected, template.id


def test_external_nodes_are_leaves() -> None:
    """An external node is where the bay leaves the station; at most one per bay."""
    for template in default_registry().templates:
        external = [n for n in template.nodes if n.kind is NodeKind.EXTERNAL]
        assert len(external) <= 1, template.id
