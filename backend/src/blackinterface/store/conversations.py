"""Conversations on disk. Words, not readings (ADR-0022 §2).

Follows the repository shape of `projects.py`: takes a `Database`, speaks SQL,
returns plain rows. It does not import `agent/` and knows nothing about turns
being fed to a model — `api/conversations.py` is what joins the two, because
`agent/` may not import `store/` (`tools/check.py` §2).

**What this file does and does not protect.** The transcript is plain text in
the SQLite file. Anyone who can read that file reads every question asked and
every sentence the assistant wrote. What they do *not* get is station data:
no readings, no evidence, no switch positions are stored here, because none of
them are written in the first place. That is a property of the schema, not of
this class being careful.
"""

from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Row

from blackinterface.store.db import Database

#: Turns kept per conversation; the oldest fall off. A shift asks a lot of
#: questions and the fortieth answer is not context for the forty-first.
MAX_TURNS = 40

#: Conversations kept **per account**, least recently used pruned first. Per
#: account rather than globally so a busy operator cannot evict the engineer's
#: thread from under them.
MAX_CONVERSATIONS = 50

#: Title length. A title is a handle for finding a thread again, not a summary.
TITLE_CHARS = 80


@dataclass(frozen=True)
class ConversationRow:
    id: str
    actor: str
    title: str
    started_at: str
    last_at: str
    turns: int


@dataclass(frozen=True)
class TurnRow:
    turn_id: str
    asked_at: str
    question: str
    answer: str
    scope: str
    asked_from: str


_LIST_SQL = """
SELECT c.id, c.actor, c.title, c.started_at, c.last_at,
       (SELECT COUNT(*) FROM conversation_turns t
         WHERE t.conversation_id = c.id) AS turns
FROM conversations c
"""


def _conversation(row: Row) -> ConversationRow:
    return ConversationRow(
        id=str(row["id"]),
        actor=str(row["actor"]),
        title=str(row["title"]),
        started_at=str(row["started_at"]),
        last_at=str(row["last_at"]),
        turns=int(row["turns"]),
    )


def _turn(row: Row) -> TurnRow:
    return TurnRow(
        turn_id=str(row["turn_id"]),
        asked_at=str(row["asked_at"]),
        question=str(row["question"]),
        answer=str(row["answer"]),
        scope=str(row["scope"]),
        asked_from=str(row["asked_from"]),
    )


class ConversationRepository:
    def __init__(
        self,
        db: Database,
        *,
        max_turns: int = MAX_TURNS,
        max_conversations: int = MAX_CONVERSATIONS,
    ) -> None:
        self.db = db
        self._max_turns = max_turns
        self._max_conversations = max_conversations

    # ----------------------------------------------------------------- writing
    def open(self, conversation_id: str, actor: str, started_at: str) -> None:
        """Record a new conversation. Idempotent — reopening is not an error."""
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO conversations (id, actor, title, started_at, last_at) "
                "VALUES (?, ?, '', ?, ?) ON CONFLICT(id) DO NOTHING",
                (conversation_id, actor, started_at, started_at),
            )
        self._prune_conversations(actor)

    def append(
        self,
        conversation_id: str,
        actor: str,
        turn: TurnRow,
    ) -> None:
        """Add one turn, set the title if there is not one yet, trim the tail.

        Takes `actor` so a turn can never be appended to a row this account does
        not own, even if a caller hands over an id it found somewhere. The
        `WHERE actor = ?` on the parent update is that guarantee; the foreign
        key alone would happily attach it.
        """
        with self.db.transaction() as conn:
            owned = conn.execute(
                "SELECT 1 FROM conversations WHERE id = ? AND actor = ?",
                (conversation_id, actor),
            ).fetchone()
            if owned is None:
                return
            conn.execute(
                "INSERT INTO conversation_turns "
                "(conversation_id, turn_id, asked_at, question, answer, scope, asked_from) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(conversation_id, turn_id) DO UPDATE SET "
                "answer = excluded.answer, scope = excluded.scope",
                (
                    conversation_id,
                    turn.turn_id,
                    turn.asked_at,
                    turn.question,
                    turn.answer,
                    turn.scope,
                    turn.asked_from,
                ),
            )
            conn.execute(
                "UPDATE conversations SET last_at = ?, "
                "title = CASE WHEN title = '' THEN ? ELSE title END "
                "WHERE id = ?",
                (turn.asked_at, turn.question[:TITLE_CHARS], conversation_id),
            )
            # Oldest turns fall off. `rowid` breaks ties within the same
            # timestamp, which two questions asked in the same second will have.
            conn.execute(
                "DELETE FROM conversation_turns WHERE conversation_id = ? AND rowid NOT IN "
                "(SELECT rowid FROM conversation_turns WHERE conversation_id = ? "
                " ORDER BY asked_at DESC, rowid DESC LIMIT ?)",
                (conversation_id, conversation_id, self._max_turns),
            )

    # ----------------------------------------------------------------- reading
    def get(self, conversation_id: str, actor: str) -> ConversationRow | None:
        """The conversation, or None when it is missing **or somebody else's**.

        One return value for both cases on purpose (ADR-0022 §3): telling the
        caller apart confirms that an id exists, which is a small leak of who
        asked what and when.
        """
        row = self.db.connection.execute(
            _LIST_SQL + " WHERE c.id = ? AND c.actor = ?", (conversation_id, actor)
        ).fetchone()
        return _conversation(row) if row else None

    def turns(self, conversation_id: str, actor: str) -> list[TurnRow]:
        """Every stored turn, oldest first. Empty for a conversation not theirs."""
        if self.get(conversation_id, actor) is None:
            return []
        rows = self.db.connection.execute(
            "SELECT turn_id, asked_at, question, answer, scope, asked_from "
            "FROM conversation_turns WHERE conversation_id = ? "
            "ORDER BY asked_at, rowid",
            (conversation_id,),
        ).fetchall()
        return [_turn(r) for r in rows]

    # Defined after `turns()` on purpose: a method named `list` shadows the
    # builtin for every annotation that follows it in the class body, so
    # `-> list[TurnRow]` above would stop being a type. Ordering is the fix that
    # costs nothing; renaming the method would make this repository read
    # differently from `projects.py`.
    def list(self, actor: str, limit: int = MAX_CONVERSATIONS) -> list[ConversationRow]:
        rows = self.db.connection.execute(
            _LIST_SQL + " WHERE c.actor = ? ORDER BY c.last_at DESC LIMIT ?",
            (actor, limit),
        ).fetchall()
        return [_conversation(r) for r in rows]

    # ---------------------------------------------------------------- deleting
    def delete(self, conversation_id: str, actor: str) -> bool:
        """Delete it and (by FK cascade) its turns. False when not theirs."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM conversations WHERE id = ? AND actor = ?",
                (conversation_id, actor),
            )
        return cursor.rowcount > 0

    def _prune_conversations(self, actor: str) -> None:
        """Keep this account's newest `max_conversations`, drop the rest."""
        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM conversations WHERE actor = ? AND id NOT IN "
                "(SELECT id FROM conversations WHERE actor = ? "
                " ORDER BY last_at DESC LIMIT ?)",
                (actor, actor, self._max_conversations),
            )
