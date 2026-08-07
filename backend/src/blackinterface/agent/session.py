"""Conversation memory — what "còn số đo thì sao?" is allowed to mean.

A follow-up question is the normal way people talk about a substation, and it is
the only reason this module exists: the second question usually names nothing,
and the thing it is about is whatever the first one settled on.

Two rules, and both are about who may read what.

**A conversation belongs to the person who opened it.** Asking to continue
someone else's id does not fail and does not warn — it quietly starts a new
conversation. Failing would confirm the id exists, which is a small leak of who
asked what and when, and there is no legitimate case for one account resuming
another's thread.

**Nothing here is persisted yet.** Held in this process, capped, gone on
restart. That is a deliberate limit of the thin slice, not an oversight — the
shape that matters is the `Conversations` protocol, and a SQLite repository
behind it is a later, mechanical step (`store/`). It is worth doing when the
transcript becomes something to audit rather than something to scroll back
through, which is Module B's problem.

`agent/` may not import `store/` (`tools/check.py` section 2), so persistence
will arrive as an implementation injected by `api/` — the same shape as the
station store. That boundary is why the protocol is here and the database is not.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

#: Turns kept per conversation. Beyond this the oldest are forgotten; a
#: substation shift asks a lot of questions and the twentieth answer is not
#: context for the twenty-first.
MAX_TURNS = 40

#: Conversations kept in the process, least recently used dropped first.
MAX_CONVERSATIONS = 200

#: How many earlier turns are shown to the model. Small on purpose: the answer
#: comes from the tools, not from the transcript, and a long history is mostly
#: an invitation to answer from memory instead of from this minute's readings.
HISTORY_TURNS = 4


@dataclass(frozen=True)
class Turn:
    """One question and what was said back."""

    id: str
    asked_at: datetime
    question: str
    #: The prose. Empty when the answer was computed rather than written, which
    #: is why `history()` skips those: an empty assistant message teaches a model
    #: that empty answers are acceptable.
    answer: str = ""
    #: The scope this turn settled on. What a follow-up inherits.
    scope: str = ""
    #: The scope the operator's pane was showing when they asked. Recorded
    #: alongside `scope` so a later turn can tell "they have not moved" from
    #: "they clicked something else" — see `plan.py`.
    asked_from: str = ""


@dataclass
class Conversation:
    id: str
    actor: str
    started_at: datetime
    turns: list[Turn] = field(default_factory=list)

    @property
    def scope(self) -> str | None:
        """What the last turn was about, or None for a fresh conversation."""
        for turn in reversed(self.turns):
            if turn.scope:
                return turn.scope
        return None

    def history(self, limit: int = HISTORY_TURNS) -> tuple[tuple[str, str], ...]:
        """Recent (question, answer) pairs, oldest first, prose only."""
        spoken = [(t.question, t.answer) for t in self.turns if t.answer]
        return tuple(spoken[-limit:])


class Conversations(Protocol):
    """Where conversations live. One implementation today, one seam."""

    def resume(self, conversation_id: str | None, actor: str) -> Conversation:
        """The named conversation if it is this actor's, otherwise a new one."""

    def append(self, conversation: Conversation, turn: Turn) -> None:
        """Record a turn. Must be safe to call on a conversation this store
        handed out and has since evicted."""


class InMemoryConversations:
    """Process-local, bounded, and not shared between accounts."""

    def __init__(
        self, max_conversations: int = MAX_CONVERSATIONS, max_turns: int = MAX_TURNS
    ) -> None:
        self._by_id: OrderedDict[str, Conversation] = OrderedDict()
        self._max_conversations = max_conversations
        self._max_turns = max_turns

    def resume(self, conversation_id: str | None, actor: str) -> Conversation:
        if conversation_id:
            found = self._by_id.get(conversation_id)
            if found is not None and found.actor == actor:
                self._by_id.move_to_end(conversation_id)
                return found
        return self._open(actor)

    def append(self, conversation: Conversation, turn: Turn) -> None:
        conversation.turns.append(turn)
        del conversation.turns[: -self._max_turns]
        self._by_id[conversation.id] = conversation
        self._by_id.move_to_end(conversation.id)
        while len(self._by_id) > self._max_conversations:
            self._by_id.popitem(last=False)

    def _open(self, actor: str) -> Conversation:
        conversation = Conversation(id=uuid.uuid4().hex, actor=actor, started_at=datetime.now(UTC))
        self._by_id[conversation.id] = conversation
        while len(self._by_id) > self._max_conversations:
            self._by_id.popitem(last=False)
        return conversation


def new_turn_id() -> str:
    return uuid.uuid4().hex
