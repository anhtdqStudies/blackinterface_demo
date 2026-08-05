-- Projects: a named connection to one OneATS DataServer, plus the last
-- successful browse frozen as a snapshot.
--
-- The snapshot is the serialized StationObs (the unit of a snapshot, see
-- domain/observation.py). Opening a project renders from the snapshot without
-- the DataServer running; an explicit refresh re-reads live and replaces it.
-- One snapshot per project: history/releases belong to module #5 (I7), not here.

CREATE TABLE IF NOT EXISTS projects (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    opcua_url  TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_snapshots (
    project_id    INTEGER PRIMARY KEY
                  REFERENCES projects(id) ON DELETE CASCADE,
    obs_json      TEXT NOT NULL,   -- StationObs.model_dump_json()
    model_name    TEXT NOT NULL DEFAULT '',
    model_version TEXT,
    captured_at   TEXT,            -- when the source was browsed
    saved_at      TEXT NOT NULL    -- when this row was written
);
