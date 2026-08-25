"""The alarm body decoder, checked against real bodies without a DataServer.

Why this file exists: the previous decoder passed `pytest -m live` on all 243
standing alarms while having the field boundaries wrong. Every one of those
bodies had an empty `actor`, so reading that field as four bytes of padding was
indistinguishable from correct — until an operator moved a breaker and the
timestamps behind it became garbage.

So the assertions here are not "it parsed". They are the two properties that
cannot hold by accident: the struct's trailing echo of `source_point` must come
back identical, and the walk must consume the body exactly.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from blackinterface.integration.opcua.alarms import (
    AlarmDecodeError,
    decode_alarm_body,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "alarm_bodies.json"
REGENERATE = "python tools/probe_dataserver.py --alarms"


def _load() -> list[dict[str, Any]]:
    if not FIXTURE.exists():  # pragma: no cover - fixture ships with the repo
        pytest.skip(f"fixture missing: {FIXTURE} - regenerate with: {REGENERATE}")
    return list(json.loads(FIXTURE.read_text(encoding="utf-8"))["bodies"])


BODIES = _load()


def _ids() -> list[str]:
    return [f"{row['expect']['category']}:{row['expect']['source_point']}" for row in BODIES]


def test_fixture_covers_every_category_and_an_operator_action() -> None:
    """A fixture that lost its interesting rows would make the rest vacuous."""
    categories = {row["expect"]["category"] for row in BODIES}
    assert categories == {"Discrete Alarm", "Binary Alarm", "Limit Alarm"}, categories
    with_actor = [row for row in BODIES if row["expect"]["actor"]]
    assert with_actor, (
        "the regression case is gone: no body carries an actor, so this suite can "
        "no longer catch the bug it was written for"
    )


@pytest.mark.parametrize("row", BODIES, ids=_ids())
def test_decodes_to_the_recorded_values(row: dict[str, Any]) -> None:
    record = decode_alarm_body(bytes.fromhex(row["body_hex"]))
    expect = row["expect"]

    assert record.event_id == expect["event_id"]
    assert record.seq == expect["seq"]
    assert record.message == expect["message"]
    assert record.severity_raw == expect["severity_raw"]
    assert record.category == expect["category"]
    assert record.source_object == expect["source_object"]
    assert record.source_point == expect["source_point"]
    assert record.actor == (expect["actor"] or None)
    assert record.value_type == expect["value_type"]
    assert record.value == expect["value"]
    assert _iso(record.t_active) == expect["t_active"]
    assert _iso(record.t_change) == expect["t_change"]


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment is not None else None


def test_operator_driven_alarm_decodes() -> None:
    """The body that used to raise OverflowError.

    An operator opened CB 431 through OneATS Data Editor, which filled the
    `actor` field the old decoder skipped as padding.
    """
    row = next(r for r in BODIES if r["expect"]["actor"])
    record = decode_alarm_body(bytes.fromhex(row["body_hex"]))
    assert record.actor is not None
    assert "@" in record.actor, record.actor
    assert record.t_active is not None, "timestamps must survive a non-empty actor"
    assert record.t_change is not None


def test_value_is_typed_per_category() -> None:
    """Discrete carries text, Binary a flag, Limit a number — not all strings."""
    by_category: dict[str, set[str]] = {}
    for row in BODIES:
        record = decode_alarm_body(bytes.fromhex(row["body_hex"]))
        by_category.setdefault(record.category or "?", set()).add(record.value_type)
    assert by_category["Discrete Alarm"] == {"String"}
    assert by_category["Binary Alarm"] == {"Boolean"}
    assert by_category["Limit Alarm"] == {"Float"}


def test_truncated_body_raises_rather_than_guessing() -> None:
    """Half a body must fail loudly; a plausible wrong alarm is the danger."""
    body = bytes.fromhex(BODIES[0]["body_hex"])
    with pytest.raises((AlarmDecodeError, IndexError, Exception)):
        decode_alarm_body(body[: len(body) // 2])


def test_shifted_body_is_caught_by_the_echo() -> None:
    """Inject the exact class of bug that shipped: one byte of drift.

    Lengthening the actor string by a byte without moving anything else is what
    a misread field boundary looks like from the inside. The echo check has to
    notice.
    """
    row = next(r for r in BODIES if not r["expect"]["actor"])
    body = bytearray(bytes.fromhex(row["body_hex"]))
    point = (row["expect"]["source_point"] or "").encode()
    at = body.find(point)
    assert at >= 0
    actor_len_at = at + len(point)
    assert body[actor_len_at : actor_len_at + 4] == b"\x00\x00\x00\x00", "expected empty actor"
    body[actor_len_at] = 1  # claim a one-byte actor that is not there

    with pytest.raises(AlarmDecodeError):
        decode_alarm_body(bytes(body))
