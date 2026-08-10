"""The `Conversations` seam, wired to SQLite (ADR-0022 §2).

`agent/` may not import `store/` (`tools/check.py` §2), so this module is where
the protocol declared in `agent/session.py` meets the repository in
`store/conversations.py`. It is the same shape as `StationStore`: the layer that
knows about both is the one above them.

Everything here is words. Nothing writes a reading, an evidence record or a
switch position to disk, because none of them are in `Turn` — see the migration
for why that is a schema property and not a habit.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from blackinterface.agent.session import Conversation, ConversationInfo, Turn, title_for
from blackinterface.store.conversations import ConversationRepository, ConversationRow, TurnRow


def _parse(stamp: str) -> datetime:
    """An ISO stamp from the database, always timezone-aware.

    Rows written by an older build could lack an offset; treating those as UTC
    keeps `last_at` comparable instead of raising when a naive and an aware
    datetime meet during a sort.
    """
    parsed = datetime.fromisoformat(stamp)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _info(row: ConversationRow) -> ConversationInfo:
    return ConversationInfo(
        id=row.id,
        title=row.title,
        started_at=_parse(row.started_at),
        last_at=_parse(row.last_at),
        turns=row.turns,
    )


def _turn(row: TurnRow) -> Turn:
    return Turn(
        id=row.turn_id,
        asked_at=_parse(row.asked_at),
        question=row.question,
        answer=row.answer,
        scope=row.scope,
        asked_from=row.asked_from,
    )


class StoredConversations:
    """Conversations that outlive the process.

    Reads go to the database every time rather than through a cache. A cache
    here would have to be invalidated by `delete`, by the per-account cap, and
    by a second worker — and the whole object is a handful of rows per question.
    """

    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    # ------------------------------------------------------------------ asking
    def resume(self, conversation_id: str | None, actor: str) -> Conversation:
        """Continue a thread of theirs, **with its turns**, or open a new one.

        Loading the turns is the whole point: `core.py` reads `history()` off
        this object, so returning an empty shell would switch the memory off
        without failing anything — the kind of bug that looks like the model
        being forgetful.
        """
        if conversation_id:
            found = self.load(conversation_id, actor)
            if found is not None:
                return found
        return self._open(actor)

    def append(self, conversation: Conversation, turn: Turn) -> None:
        conversation.turns.append(turn)
        if not conversation.title:
            conversation.title = title_for(turn.question)
        self._repository.append(
            conversation.id,
            conversation.actor,
            TurnRow(
                turn_id=turn.id,
                asked_at=turn.asked_at.isoformat(),
                question=turn.question,
                answer=turn.answer,
                scope=turn.scope,
                asked_from=turn.asked_from,
            ),
        )

    # ----------------------------------------------------------------- reading
    def list(self, actor: str) -> tuple[ConversationInfo, ...]:
        """Their conversations, newest first. No transcript is read.

        The count comes off the row, so opening the picker costs one query
        whether a thread has two turns or forty.
        """
        return tuple(_info(row) for row in self._repository.list(actor))

    def load(self, conversation_id: str, actor: str) -> Conversation | None:
        row = self._repository.get(conversation_id, actor)
        if row is None:
            return None
        return Conversation(
            id=row.id,
            actor=row.actor,
            started_at=_parse(row.started_at),
            title=row.title,
            turns=[_turn(t) for t in self._repository.turns(conversation_id, actor)],
        )

    def delete(self, conversation_id: str, actor: str) -> bool:
        return self._repository.delete(conversation_id, actor)

    # ------------------------------------------------------------------ making
    def _open(self, actor: str) -> Conversation:
        conversation = Conversation(id=uuid.uuid4().hex, actor=actor, started_at=datetime.now(UTC))
        self._repository.open(conversation.id, actor, conversation.started_at.isoformat())
        return conversation
