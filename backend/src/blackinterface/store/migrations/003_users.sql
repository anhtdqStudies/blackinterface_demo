-- Accounts, roles and sessions (ADR-0016 section 7, ADR-0017).
--
-- Local because the product installs on one machine at one substation
-- (ADR-0006) and an unattended station may have no directory service to lean
-- on. Remote access is what makes authentication a requirement here rather
-- than a convenience.
--
-- `external_id` is the hinge: when ATS has an account system, each row here
-- points at an identity over there instead of being deleted and rebuilt. Its
-- absence would turn that day into a data migration; its presence makes it
-- filling in a column. `password_hash` is NULL for exactly those rows — the
-- password then lives wherever the identity does.

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL,
    password_hash TEXT,             -- NULL when the identity comes from outside
    external_id   TEXT UNIQUE,      -- hook into an ATS/AD account, later
    created_at    TEXT NOT NULL,
    -- NULL means the seeded password has never been changed. Cheaper and more
    -- honest than re-hashing at startup to find out, and it is what lets the
    -- app say so out loud instead of hoping somebody remembers.
    password_changed_at TEXT,
    -- Disabled rather than deleted: an account named in an old audit record
    -- must stay resolvable, or the record stops meaning anything.
    disabled_at   TEXT
);

-- One person holds SEVERAL roles (ADR-0016 section 1). Effective permission is
-- the union, which is what lets one account run a lightly-manned station
-- without anybody sharing a password.
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role    TEXT NOT NULL,
    PRIMARY KEY (user_id, role)
);

-- Server-side sessions, so signing out and disabling an account take effect at
-- once. A self-contained token could not be withdrawn before it expired, and
-- "revoke this person's access now" is the request that actually arrives.
--
-- Only the SHA-256 of the token is stored. The database is then not a set of
-- usable credentials: whoever reads this table still cannot sign in as anyone.
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
