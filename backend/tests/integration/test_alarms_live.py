"""Live DataServer alarm / event structure probe.

Run only when a OneATS DataServer is reachable:

    cd backend && uv run pytest -m live tests/integration/test_alarms_live.py -s

READ-ONLY — calls ``OAAlarm.GetActiveAlarm`` and browses ``OAEvent`` only.
Never invokes ``Ack*``, ``Enable``, ``Disable``, or standard OPC UA A&C subscribe.

The test prints a structure summary (``-s``) and asserts invariants measured on
DEMO_SAS v654 (2026-08-04). Update ``docs/30-integration/oneats-dataserver.md``
if a re-run shows drift.
"""

from __future__ import annotations

import re

import pytest
from asyncua import Client

from blackinterface.integration.opcua.alarms import (
    ALARM_TYPE_ID_SUFFIX,
    KNOWN_CATEGORIES,
    analyze_alarm_batch,
    fetch_alarm_structure,
    get_active_alarms,
    probe_oa_event,
)
from blackinterface.integration.opcua.discovery import _find_station_root

URL = "opc.tcp://127.0.0.1:48050"
SOURCE_POINT_RE = re.compile(r"^[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)+$")

pytestmark = pytest.mark.live


def _print_structure_report(title: str, report: object) -> None:
    """Human-readable dump for ``pytest -s`` sessions."""
    from blackinterface.integration.opcua.alarms import AlarmStructureReport

    assert isinstance(report, AlarmStructureReport)
    print(f"\n=== {title} ===")
    print(f"scope          : {report.scope_node_id}")
    print(f"total          : {report.total}")
    print(f"decoded        : {report.decoded} ({report.decode_rate:.0%})")
    print(f"type_ids       : {dict(report.type_ids)}")
    print(f"body_lengths   : {dict(report.body_lengths)}")
    print(f"categories     : {dict(report.categories)}")
    print(f"severities(top): {report.severities.most_common(5)}")
    if report.decode_errors:
        print(f"decode_errors  : {report.decode_errors[:5]}")
    if report.records:
        sample = report.records[0]
        print(
            "sample record  : "
            f"category={sample.category!r} message={sample.message!r} "
            f"source_point={sample.source_point!r} "
            f"value={sample.value!r} ({sample.value_type}) actor={sample.actor!r}"
        )
    if report.envelopes:
        env = report.envelopes[0]
        print(
            "sample envelope: "
            f"type_id={env.type_id} encoding={env.encoding} "
            f"body_len={env.body_len} prefix={env.body_hex_prefix}"
        )


async def _client() -> Client:
    client = Client(url=URL, timeout=30)
    try:
        await client.connect()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"no DataServer at {URL}: {type(exc).__name__}: {exc}")
    return client


@pytest.fixture
async def live_client() -> Client:
    client = await _client()
    yield client
    await client.disconnect()


async def test_dataserver_connection_and_oaevent_shape(live_client: Client) -> None:
    """OneATS does not expose OPC UA A&C under ``OAEvent`` (ADR-0007)."""
    probe = await probe_oa_event(live_client)
    print(
        f"\nOAEvent exists={probe.node_exists} children={probe.child_count} names={probe.child_names}"
    )
    assert probe.node_exists
    assert probe.child_count == 0


async def test_get_active_alarm_station_scope_structure(live_client: Client) -> None:
    """``GetActiveAlarm(/SAS)`` returns decodable ExtensionObject batch."""
    report = await fetch_alarm_structure(live_client)
    _print_structure_report("station scope", report)

    assert report.total > 0, "expected at least one active alarm on loaded project"
    assert report.decode_rate == 1.0, report.decode_errors
    assert all(ALARM_TYPE_ID_SUFFIX in tid for tid in report.type_ids), dict(report.type_ids)
    assert report.categories.keys() <= KNOWN_CATEGORIES or report.categories, (
        "unexpected alarm categories — update KNOWN_CATEGORIES or docs"
    )

    for record in report.records:
        assert record.event_id, "event_id must be present"
        assert record.message, "message must be present"
        assert record.source_point, "source_point links alarm to diagram device"
        assert SOURCE_POINT_RE.match(record.source_point), record.source_point
        assert record.t_active is not None, "t_active FILETIME must parse"
        assert record.t_change is not None, "t_change FILETIME must parse"


async def test_get_active_alarm_bay_scope_is_subset(live_client: Client) -> None:
    """Scoped call with a bay NodeId returns fewer alarms than the whole station."""
    station = await _find_station_root(live_client)
    station_report = await fetch_alarm_structure(live_client, station)
    if station_report.total == 0:
        pytest.skip("no active alarms on station")

    bay_ids = {
        (record.source_object or record.source_point or "").split(".")[0]
        for record in station_report.records
        if record.source_object or record.source_point
    }
    bay_ids.discard("")
    if not bay_ids:
        pytest.skip("alarms have no source_object/source_point to derive bay id")

    bay_name = sorted(bay_ids)[0]
    bay_node = None
    for child in await station.get_children():
        if (await child.read_browse_name()).Name == bay_name:
            bay_node = child
            break
    if bay_node is None:
        for vl in await station.get_children():
            for child in await vl.get_children():
                if (await child.read_browse_name()).Name == bay_name:
                    bay_node = child
                    break
            if bay_node is not None:
                break
    if bay_node is None:
        pytest.skip(f"could not locate bay node {bay_name!r} in address space")

    bay_batch = await get_active_alarms(live_client, bay_node)
    bay_report = analyze_alarm_batch(bay_node.nodeid.to_string(), bay_batch)
    _print_structure_report(f"bay scope ({bay_name})", bay_report)

    assert bay_report.total <= station_report.total
    assert bay_report.total > 0, f"expected alarms scoped to {bay_name}"
    assert bay_report.decode_rate == 1.0, bay_report.decode_errors
    for record in bay_report.records:
        prefix = (record.source_object or record.source_point or "").split(".")[0]
        assert prefix == bay_name, (
            f"bay-scoped alarm should belong to {bay_name}, got {record.source_object!r}"
        )


async def test_alarm_extension_object_field_layout_is_stable(live_client: Client) -> None:
    """Body length varies with message length — bounds catch a broken struct."""
    report = await fetch_alarm_structure(live_client)
    _print_structure_report("layout stability", report)

    assert report.total > 0
    assert report.decode_rate == 1.0, report.decode_errors
    lengths = list(report.body_lengths.keys())
    assert min(lengths) >= 100, f"body unexpectedly short: {dict(report.body_lengths)}"
    assert max(lengths) <= 300, f"body unexpectedly long: {dict(report.body_lengths)}"
    dominant_count = report.body_lengths.most_common(1)[0][1]
    assert dominant_count / report.total >= 0.1, (
        f"expected a dominant body-length cluster, got {dict(report.body_lengths)}"
    )
