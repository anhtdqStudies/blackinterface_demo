"""Turning an OPC UA `DataValue` into a neutral `PointSample`.

Its own module because two readers need exactly the same rule: the browser in
`discovery.py` (one batch read) and the subscription in `monitor.py` (a push
whenever OneATS notices a change). If those two disagreed about what "good"
means, a point would change meaning the moment it started updating live —
which is the one place a discrepancy would be hardest to notice.
"""

from __future__ import annotations

from typing import Any

from asyncua import ua

from blackinterface.domain.models import PointSample, Quality


def to_quality(status: Any) -> Quality:
    if status is None:
        return Quality.MISSING
    name = getattr(status, "name", str(status)).lower()
    if name.startswith("good"):
        return Quality.GOOD
    if name.startswith("uncertain"):
        return Quality.UNCERTAIN
    return Quality.BAD


def to_sample(value: ua.DataValue | None, source_ref: str | None) -> PointSample:
    """One reading, with the judgement about it attached (AGENTS.md I2).

    A `None` value with a GOOD status is downgraded to BAD: the server said the
    read succeeded but handed us nothing, and an absent position must never be
    presented as a readable one.
    """
    if value is None:
        return PointSample(source_ref=source_ref)
    raw = value.Value.Value if value.Value is not None else None
    quality = to_quality(value.StatusCode)
    if raw is None and quality is Quality.GOOD:
        quality = Quality.BAD
    return PointSample(
        value=raw if isinstance(raw, bool | int | float | str) else None,
        quality=quality,
        source_timestamp=value.SourceTimestamp,
        source_ref=source_ref,
    )
