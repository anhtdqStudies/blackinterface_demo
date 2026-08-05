"""StationStore project lifecycle, across simulated process restarts.

The API tests exercise the endpoints; these exercise the store itself, in
particular the one guarantee endpoints cannot show: a *new* StationStore (a
new process) reopens the last project from its snapshot without touching the
DataServer.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from blackinterface.api.source import StationStore
from blackinterface.config import Settings
from blackinterface.domain.observation import StationObs
from blackinterface.errors import NotFoundError
from blackinterface.integration.dump import load_dump
from blackinterface.store.db import Database
from tests.conftest import SAS_TREE


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.sqlite")
    database.migrate()
    return database


def _store(db: Database, tmp_path: Path) -> StationStore:
    # realtime off: these tests use invented DataServer URLs, and a
    # subscription would be the one thing here actually dialling the network.
    return StationStore(
        Settings(source="fixture", fixture=SAS_TREE, data_dir=tmp_path, realtime=False), db
    )


def _serving_fixture(store: StationStore) -> None:
    async def observe(url: str) -> StationObs:
        return load_dump(SAS_TREE).model_copy(update={"source": url})

    store._observe_opcua = observe  # type: ignore[method-assign]


def _serving_nothing(store: StationStore) -> None:
    async def observe(url: str) -> StationObs:
        raise AssertionError(f"the DataServer must not be contacted (url={url})")

    store._observe_opcua = observe  # type: ignore[method-assign]


async def test_startup_reopens_the_last_project_from_its_snapshot(
    db: Database, tmp_path: Path
) -> None:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")

    first = _store(db, tmp_path)
    _serving_fixture(first)
    row = first.projects.create("Trạm A", "opc.tcp://10.0.0.5:48050")
    await first.refresh_project(row.id)
    assert first.project is not None and first.project.name == "Trạm A"

    # "Restart": a fresh store on the same database, with the server down.
    second = _store(db, tmp_path)
    _serving_nothing(second)
    await second.startup()
    assert second.loaded
    assert second.project is not None and second.project.name == "Trạm A"
    assert second.graph.source.startswith("snapshot:")


async def test_startup_falls_back_to_settings_when_no_project_is_active(
    db: Database, tmp_path: Path
) -> None:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    store = _store(db, tmp_path)
    await store.startup()
    assert store.loaded
    assert store.project is None
    assert store.source_label == "fixture"


async def test_startup_survives_a_deleted_active_project(db: Database, tmp_path: Path) -> None:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    first = _store(db, tmp_path)
    _serving_fixture(first)
    row = first.projects.create("X", "opc.tcp://x:1")
    await first.refresh_project(row.id)
    first.projects.delete(row.id)

    second = _store(db, tmp_path)
    await second.startup()  # must fall back, not crash on the dangling id
    assert second.loaded
    assert second.project is None


async def test_refresh_unknown_project_is_not_found(db: Database, tmp_path: Path) -> None:
    store = _store(db, tmp_path)
    with pytest.raises(NotFoundError):
        await store.refresh_project(99999)
