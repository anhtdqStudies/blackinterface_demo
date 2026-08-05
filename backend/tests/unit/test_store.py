"""SQLite layer: migrations run once, WAL is on, the repository round-trips."""

from __future__ import annotations

from pathlib import Path

import pytest

from blackinterface.errors import ConfigurationError
from blackinterface.store import db as db_module
from blackinterface.store.db import Database
from blackinterface.store.meta import LAST_MODEL_VERSION, MetaRepository
from blackinterface.store.projects import ProjectRepository


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.sqlite")
    database.migrate()
    return database


def test_migrate_creates_the_file_and_records_the_version(tmp_path: Path) -> None:
    database = Database(tmp_path / "nested" / "test.sqlite")
    all_versions = [v for v, _, _ in Database._migration_files()]
    assert database.migrate() == all_versions
    assert database.path.exists()
    assert database.applied_versions() == set(all_versions)


def test_migrate_is_idempotent(db: Database) -> None:
    assert db.migrate() == []


def test_wal_is_enabled(db: Database) -> None:
    """Without WAL a reader blocks the writer, which matters once events stream in."""
    mode = db.connection.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_foreign_keys_are_on(db: Database) -> None:
    """SQLite defaults this to OFF per connection - a classic silent data bug."""
    assert db.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_meta_round_trip(db: Database) -> None:
    meta = MetaRepository(db)
    assert meta.get(LAST_MODEL_VERSION) is None
    meta.set(LAST_MODEL_VERSION, "654")
    assert meta.get(LAST_MODEL_VERSION) == "654"
    meta.set(LAST_MODEL_VERSION, "655")
    assert meta.get(LAST_MODEL_VERSION) == "655"
    assert meta.all() == {LAST_MODEL_VERSION: "655"}


def test_transaction_rolls_back(db: Database) -> None:
    meta = MetaRepository(db)
    meta.set("k", "before")
    with pytest.raises(RuntimeError), db.transaction() as conn:
        conn.execute("INSERT INTO app_meta (key, value, updated_at) VALUES ('k2', 'x', '')")
        raise RuntimeError("boom")
    assert meta.get("k2") is None
    assert meta.get("k") == "before"


def test_projects_round_trip(db: Database) -> None:
    projects = ProjectRepository(db)
    assert projects.list() == []

    row = projects.create("Trạm A", "opc.tcp://10.0.0.5:48050")
    assert row.id > 0
    assert row.has_snapshot is False
    assert projects.get(row.id) == row
    assert projects.get_by_name("Trạm A") == row
    assert projects.get_by_name("nope") is None
    assert [p.name for p in projects.list()] == ["Trạm A"]

    projects.save_snapshot(
        row.id, '{"name": "A"}', model_name="A", model_version="654", captured_at="2026-08-05"
    )
    stamped = projects.get(row.id)
    assert stamped is not None
    assert stamped.has_snapshot is True
    assert stamped.model_version == "654"
    assert stamped.updated_at >= row.updated_at
    assert projects.load_snapshot(row.id) == '{"name": "A"}'

    # Saving again replaces, not duplicates.
    projects.save_snapshot(row.id, '{"name": "B"}')
    assert projects.load_snapshot(row.id) == '{"name": "B"}'


def test_deleting_a_project_cascades_to_its_snapshot(db: Database) -> None:
    projects = ProjectRepository(db)
    row = projects.create("X", "opc.tcp://x:1")
    projects.save_snapshot(row.id, "{}")
    assert projects.delete(row.id) is True
    assert projects.delete(row.id) is False
    assert projects.load_snapshot(row.id) is None
    count = db.connection.execute("SELECT COUNT(*) FROM project_snapshots").fetchone()[0]
    assert count == 0


def _migration_dir(tmp_path: Path, *names: str) -> Path:
    directory = tmp_path / "migrations"
    directory.mkdir()
    for name in names:
        (directory / name).write_text("SELECT 1;", encoding="utf-8")
    return directory


def test_migration_versions_must_be_consecutive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A gap means an applied migration was deleted or renamed. Fail loudly."""
    monkeypatch.setattr(
        db_module, "MIGRATIONS_DIR", _migration_dir(tmp_path, "001_a.sql", "003_c.sql")
    )
    with pytest.raises(ConfigurationError, match="consecutive"):
        Database(tmp_path / "x.sqlite").migrate()


def test_migration_filename_must_start_with_a_number(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(db_module, "MIGRATIONS_DIR", _migration_dir(tmp_path, "init.sql"))
    with pytest.raises(ConfigurationError, match="start with a number"):
        Database(tmp_path / "x.sqlite").migrate()


def test_real_migrations_are_well_formed() -> None:
    versions = [v for v, _, _ in Database._migration_files()]
    assert versions == list(range(1, len(versions) + 1))
