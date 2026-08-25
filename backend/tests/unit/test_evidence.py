"""Evidence — the caveats must be derived, not remembered (ADR-0013).

The rule these tests defend: a facet reports facts, the builder produces limits.
If a facet author could forget to mention that half the points were unreadable,
then sooner or later one will, and the answer that looks most confident will be
the one built from the worst data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from blackinterface.domain.evidence import (
    DEFAULT_STALE_AFTER_MS,
    Coverage,
    EvidenceBuilder,
    EvidenceRecord,
    LimitCode,
    Source,
    SourceKind,
)
from blackinterface.domain.models import PointSample, Quality
from blackinterface.domain.scope import ScopeRef

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
LIVE = Source(kind=SourceKind.OPCUA, endpoint="opc.tcp://127.0.0.1:48050")


def good(seconds_ago: float = 0.0) -> PointSample:
    return PointSample(
        value=2,
        quality=Quality.GOOD,
        source_timestamp=NOW - timedelta(seconds=seconds_ago),
        source_ref="ns=2;s=x",
    )


def builder(source: Source = LIVE, **kwargs: object) -> EvidenceBuilder:
    return EvidenceBuilder("state", ScopeRef.bay("D03"), source=source, **kwargs)  # type: ignore[arg-type]


def codes(record: EvidenceRecord) -> set[LimitCode]:
    return {limit.code for limit in record.limits}


def test_a_clean_read_carries_no_caveats() -> None:
    b = builder()
    b.point("D03.XCBR1.PosSt", good(), now=NOW)
    b.point("D03.XSWI1.PosSt", good(1.2), now=NOW)
    record = b.build(now=NOW)

    assert record.subject == "bay:D03"
    assert record.coverage == Coverage(requested=2, resolved=2, missing=())
    assert record.coverage.complete
    assert record.limits == ()
    assert record.trustworthy


def test_missing_points_become_coverage_and_a_limit() -> None:
    b = builder()
    b.point("D03.XCBR1.PosSt", good(), now=NOW)
    b.missing("D03.XSWI36.PosSt", "D03.XSWI9.PosSt")
    record = b.build(now=NOW)

    assert record.coverage.requested == 3
    assert record.coverage.resolved == 1
    assert not record.coverage.complete
    assert LimitCode.POINTS_MISSING in codes(record)
    missing = next(x for x in record.limits if x.code is LimitCode.POINTS_MISSING)
    assert missing.count == 2
    assert set(missing.subjects) == {"D03.XSWI36.PosSt", "D03.XSWI9.PosSt"}


@pytest.mark.parametrize("quality", [Quality.BAD, Quality.UNCERTAIN, Quality.MISSING])
def test_any_quality_short_of_good_is_declared(quality: Quality) -> None:
    """I2 in its most literal form: read it, but do not let it pass as fact."""
    b = builder()
    b.point("D03.XCBR1.PosSt", PointSample(value=2, quality=quality, source_timestamp=NOW), now=NOW)
    record = b.build(now=NOW)
    assert LimitCode.QUALITY_NOT_GOOD in codes(record)


def test_good_but_old_is_still_called_out() -> None:
    """GOOD means the value arrived intact, not that it is current — for a
    reading that is *supposed* to keep arriving."""
    b = builder()
    old = good(seconds_ago=DEFAULT_STALE_AFTER_MS / 1000 + 1)
    b.point("D03.MMXU1.totW", old, expect_refresh=True, now=NOW)
    record = b.build(now=NOW)

    assert record.quality[0].quality is Quality.GOOD
    assert LimitCode.DATA_STALE in codes(record)
    assert record.quality[0].age_ms is not None
    assert record.quality[0].age_ms > DEFAULT_STALE_AFTER_MS


def test_a_value_that_simply_has_not_changed_is_not_stale() -> None:
    """An OPC UA `SourceTimestamp` says when the value was *produced*. A
    disconnector untouched for a day therefore carries a day-old timestamp
    while being perfectly current, and calling it stale would fire the caveat
    on every stationary device — 89 of 159 points on a healthy station when
    this was measured. Age is still reported; it is just not a fault."""
    b = builder()
    b.point("D03.XCBR1.PosSt", good(seconds_ago=86_400), now=NOW)
    record = b.build(now=NOW)

    assert LimitCode.DATA_STALE not in codes(record)
    assert record.quality[0].age_ms is not None


def test_staleness_threshold_is_a_parameter_not_a_clock() -> None:
    b = builder(stale_after_ms=500)
    b.point("D03.MMXU1.totW", good(seconds_ago=1), expect_refresh=True, now=NOW)
    assert LimitCode.DATA_STALE in codes(b.build(now=NOW))


def test_a_snapshot_answer_says_so_without_being_asked() -> None:
    record = builder(Source(kind=SourceKind.SNAPSHOT, endpoint="opc.tcp://x")).build(now=NOW)
    assert LimitCode.FROM_SNAPSHOT in codes(record)


def test_a_facet_may_add_a_caveat_but_the_derived_ones_remain() -> None:
    b = builder()
    b.point("D03.XCBR1.PosSt", PointSample(value=2, quality=Quality.BAD), now=NOW)
    b.note(LimitCode.LINK_DOWN)
    record = b.build(now=NOW)
    assert codes(record) == {LimitCode.QUALITY_NOT_GOOD, LimitCode.LINK_DOWN}


def test_naive_timestamps_are_read_as_utc_not_as_local_time() -> None:
    """OneATS hands back naive UTC. Reading it as local time would invent an
    age of several hours and mark a fresh station stale."""
    b = builder()
    b.point(
        "D03.XCBR1.PosSt",
        PointSample(value=2, quality=Quality.GOOD, source_timestamp=NOW.replace(tzinfo=None)),
        now=NOW,
    )
    record = b.build(now=NOW)
    assert record.quality[0].age_ms == 0
    assert record.limits == ()


def test_a_point_with_no_timestamp_has_no_age_and_no_stale_claim() -> None:
    b = builder()
    b.point("D03.XCBR1.PosSt", PointSample(value=2, quality=Quality.GOOD), now=NOW)
    record = b.build(now=NOW)
    assert record.quality[0].age_ms is None
    assert LimitCode.DATA_STALE not in codes(record)


def test_the_subject_is_a_scope_ref_in_canonical_form() -> None:
    record = EvidenceBuilder("summary", "device:D03.XCBR1", source=LIVE).build(now=NOW)
    assert record.subject == ScopeRef.device("D03.XCBR1").ref


def test_the_record_survives_serialisation_intact() -> None:
    b = builder()
    b.point("D03.XCBR1.PosSt", good(2), now=NOW)
    b.missing("D03.XSWI36.PosSt")
    record = b.build(now=NOW)
    assert EvidenceRecord.model_validate_json(record.model_dump_json()) == record
