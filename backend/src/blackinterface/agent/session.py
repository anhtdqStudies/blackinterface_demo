"""Conversation memory — what "còn số đo thì sao?" is allowed to mean.

A follow-up question is the normal way people talk about a substation, and it is
the only reason this module exists: the second question usually names nothing,
and the thing it is about is whatever the first one settled on.

Three rules, and all three are about what may be remembered and by whom.

**A conversation belongs to the person who opened it.** Asking to continue
someone else's id does not fail and does not warn — it quietly starts a new
conversation. Failing would confirm the id exists, which is a small leak of who
asked what and when, and there is no legitimate case for one account resuming
another's thread.

**A turn remembers words, never readings** (ADR-0022 §1). `history()` hands the
model question/answer prose and nothing else. Not the tool calls, not the
digests, not the evidence. A substation changes while people are talking about
it, and a model that can still see `271 CLOSED` from four turns ago will answer
from that instead of reading again — fluently, and with nothing on screen
saying the number is ten minutes old. `ctx.seen` is not inherited either, so a
follow-up still costs one `resolve` before any `summary` will run.

**Where they live is somebody else's problem.** `Conversations` is a protocol.
`InMemoryConversations` is the process-local one, used by tests and by an
installation with no database; `api/conversations.py` is the SQLite one that
survives a restart. `agent/` may not import `store/` (`tools/check.py` §2), so
persistence arrives as an implementation injected by `api/` — the same seam as
the station store.
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

#: Conversations `InMemoryConversations` keeps, least recently used dropped
#: first. The SQLite implementation caps **per account** instead and at a lower
#: number — see `store/conversations.py`. The difference is deliberate: this one
#: is a process-wide dictionary and cannot tell whose memory it is spending.
MAX_CONVERSATIONS = 200

#: How many earlier turns are shown to the model by default. Small on purpose:
#: the answer comes from the tools, not from the transcript, and a long history
#: is mostly an invitation to answer from memory instead of from this minute's
#: readings. Overridden per installation by `Settings.llm_history_turns`.
HISTORY_TURNS = 4

#: A title is a handle for finding a thread again, not a summary of it.
TITLE_CHARS = 80


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
    #: "they clicked something else".
    asked_from: str = ""


@dataclass
class Conversation:
    id: str
    actor: str
    started_at: datetime
    turns: list[Turn] = field(default_factory=list)
    #: Derived from the first question, never typed by anyone. Asking somebody to
    #: name a thread before they know where it goes is a field nobody fills in.
    title: str = ""

    @property
    def scope(self) -> str | None:
        """What the last turn was about, or None for a fresh conversation."""
        for turn in reversed(self.turns):
            if turn.scope:
                return turn.scope
        return None

    @property
    def last_at(self) -> datetime:
        return self.turns[-1].asked_at if self.turns else self.started_at

    def history(self, limit: int = HISTORY_TURNS) -> tuple[tuple[str, str], ...]:
        """Recent (question, answer) pairs, oldest first, **prose only**.

        This is the whole of what a model is told about the past (ADR-0022 §1).
        Turns with no prose are dropped rather than sent as an empty reply.
        """
        if limit <= 0:
            return ()
        spoken = [(t.question, t.answer) for t in self.turns if t.answer]
        return tuple(spoken[-limit:])


@dataclass(frozen=True)
class ConversationInfo:
    """A conversation as it appears in a list: enough to pick one, no transcript.

    A separate type rather than a `Conversation` with its turns left empty. The
    two are easy to confuse and confusing them is expensive in exactly one
    direction: handing a half-loaded `Conversation` to `history()` produces a
    model with no memory and no error, which is the hardest kind of bug to see.
    """

    id: str
    title: str
    started_at: datetime
    last_at: datetime
    turns: int


def title_for(question: str) -> str:
    """The handle a conversation is listed under."""
    return " ".join(question.split())[:TITLE_CHARS]


class Conversations(Protocol):
    """Where conversations live. Two implementations, one seam."""

    def resume(self, conversation_id: str | None, actor: str) -> Conversation:
        """The named conversation if it is this actor's, otherwise a new one.

        Must come back with its earlier turns loaded — `history()` is read off
        the object this returns, so an implementation that hands out an empty
        shell silently switches the memory off.
        """

    def append(self, conversation: Conversation, turn: Turn) -> None:
        """Record a turn. Must be safe to call on a conversation this store
        handed out and has since evicted."""

    def list(self, actor: str) -> tuple[ConversationInfo, ...]:
        """This actor's conversations, most recently used first."""

    def load(self, conversation_id: str, actor: str) -> Conversation | None:
        """One conversation with its turns, or None when it is missing **or
        somebody else's**. One answer for both cases — see the module docstring."""

    def delete(self, conversation_id: str, actor: str) -> bool:
        """Forget it. False when there was nothing of theirs to forget."""


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
        if not conversation.title:
            conversation.title = title_for(turn.question)
        self._by_id[conversation.id] = conversation
        self._by_id.move_to_end(conversation.id)
        self._evict()

    def list(self, actor: str) -> tuple[ConversationInfo, ...]:
        mine = [c for c in self._by_id.values() if c.actor == actor and c.turns]
        mine.sort(key=lambda c: c.last_at, reverse=True)
        return tuple(
            ConversationInfo(
                id=c.id,
                title=c.title,
                started_at=c.started_at,
                last_at=c.last_at,
                turns=len(c.turns),
            )
            for c in mine
        )

    def load(self, conversation_id: str, actor: str) -> Conversation | None:
        found = self._by_id.get(conversation_id)
        return found if found is not None and found.actor == actor else None

    def delete(self, conversation_id: str, actor: str) -> bool:
        if self.load(conversation_id, actor) is None:
            return False
        del self._by_id[conversation_id]
        return True

    def _open(self, actor: str) -> Conversation:
        conversation = Conversation(id=uuid.uuid4().hex, actor=actor, started_at=datetime.now(UTC))
        self._by_id[conversation.id] = conversation
        self._evict()
        return conversation

    def _evict(self) -> None:
        while len(self._by_id) > self._max_conversations:
            self._by_id.popitem(last=False)


def new_turn_id() -> str:
    return uuid.uuid4().hex
