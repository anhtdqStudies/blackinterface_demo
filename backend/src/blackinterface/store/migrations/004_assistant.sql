-- Which language model this installation uses, and its key.
--
-- A table of its own rather than a few rows in `app_meta`. `meta.py` says why:
-- that table is a key/value store for small operational state, and a secret
-- sitting next to `last_model_version` is a secret nobody remembers is there.
-- One row, enforced by the CHECK — there is one assistant, not a list of them.
--
-- `api_key_enc` is a Fernet token, not the key. See `store/secrets.py` for what
-- that does and does not protect against; the short version is that reading
-- this file is not enough, you also need BI_SECRET_KEY.
CREATE TABLE IF NOT EXISTS assistant_config (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    provider    TEXT    NOT NULL DEFAULT 'off',
    base_url    TEXT    NOT NULL DEFAULT '',
    model       TEXT    NOT NULL DEFAULT '',
    api_key_enc BLOB,
    timeout     REAL    NOT NULL DEFAULT 120.0,
    -- Cleared whenever the key is replaced, so "it worked when we set it up" is
    -- never mistaken for "it works now".
    verified_at TEXT,
    updated_at  TEXT    NOT NULL,
    updated_by  TEXT    NOT NULL
);
