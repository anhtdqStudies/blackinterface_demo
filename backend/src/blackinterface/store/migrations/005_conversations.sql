-- Conversations with the assistant, and the turns inside them (ADR-0022).
--
-- What is here is **words only**: the question, the prose that came back, and
-- which scope the turn settled on. No evidence, no readings, no summary payload.
-- ADR-0022 section 2 says why: an EvidenceRecord is a statement about one
-- moment, and re-showing it days later under a conversation title invites
-- somebody to read a stale number as a live one. A reopened transcript shows
-- what was said; the numbers come from asking again.
--
-- This is therefore NOT an audit log. Audit is control/audit.py: append-only,
-- for actions. A conversation is something to scroll back through, and to
-- delete.
CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    -- The account that opened it. Every read is filtered by this; a
    -- conversation is never shared between accounts (ADR-0022 section 3).
    actor      TEXT NOT NULL,
    -- First question, truncated. Derived, never typed by anyone.
    title      TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    -- When the last turn landed. What the list is ordered by, and what the
    -- per-account cap prunes on.
    last_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversations_actor
    ON conversations (actor, last_at DESC);

CREATE TABLE IF NOT EXISTS conversation_turns (
    conversation_id TEXT NOT NULL
        REFERENCES conversations (id) ON DELETE CASCADE,
    turn_id         TEXT NOT NULL,
    asked_at        TEXT NOT NULL,
    question        TEXT NOT NULL,
    -- The model's prose. Empty when no model wrote anything, and an empty turn
    -- is skipped when history is handed back to the model: an empty assistant
    -- message teaches it that empty answers are acceptable.
    answer          TEXT NOT NULL DEFAULT '',
    -- The scope the turn settled on, '' when it settled on nothing. Recorded so
    -- a reopened transcript can say what each turn was about.
    scope           TEXT NOT NULL DEFAULT '',
    -- Where the operator's pane was pointing when they asked. Kept alongside
    -- `scope` so "they had not moved" reads differently from "they clicked
    -- something else".
    asked_from      TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (conversation_id, turn_id)
);

CREATE INDEX IF NOT EXISTS idx_conversation_turns_order
    ON conversation_turns (conversation_id, asked_at);
