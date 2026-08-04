-- Migration bookkeeping and a small key/value table for application state.
--
-- Deliberately minimal. The event store (module #3) and the release/snapshot
-- pin (module #4) get their own migrations when those modules are written --
-- designing their schema before writing them would be guesswork.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version    INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_meta (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
