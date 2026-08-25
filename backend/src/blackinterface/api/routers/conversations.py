"""Threads with the assistant: list them, reopen one, throw one away (ADR-0022).

All three are behind `agent.ask`. That is the same permission asking a question
needs, and deliberately so: a separate `conversation.read` would suggest one
account might read another's, and none ever does.

**A conversation that is not yours is 404, never 403.** A 403 says *"this exists
and you may not have it"*, which confirms an id somebody guessed or found in a
log. Missing and not-yours are one answer here for the same reason `resume()`
quietly starts a new thread rather than refusing.
"""

from __future__ import annotations

from fastapi import APIRouter

from blackinterface.agent.session import Conversation, ConversationInfo
from blackinterface.api.authz import CALLER, requires
from blackinterface.api.deps import get_conversations
from blackinterface.api.schemas import (
    ConversationDetailOut,
    ConversationOut,
    ConversationTurnOut,
)
from blackinterface.domain.authz import Capability, Principal
from blackinterface.errors import NotFoundError

router = APIRouter()


def _summary(info: ConversationInfo) -> ConversationOut:
    return ConversationOut(
        id=info.id,
        title=info.title,
        started_at=info.started_at.isoformat(),
        last_at=info.last_at.isoformat(),
        turns=info.turns,
    )


def _detail(conversation: Conversation) -> ConversationDetailOut:
    return ConversationDetailOut(
        id=conversation.id,
        title=conversation.title,
        started_at=conversation.started_at.isoformat(),
        last_at=conversation.last_at.isoformat(),
        turns=len(conversation.turns),
        transcript=[
            ConversationTurnOut(
                turn_id=turn.id,
                asked_at=turn.asked_at.isoformat(),
                question=turn.question,
                answer=turn.answer,
                scope=turn.scope,
                asked_from=turn.asked_from,
            )
            for turn in conversation.turns
        ],
    )


@router.get(
    "/api/conversations",
    response_model=list[ConversationOut],
    dependencies=[requires(Capability.AGENT_ASK)],
)
def list_conversations(principal: Principal = CALLER) -> list[ConversationOut]:
    """The caller's own threads, most recent first."""
    return [_summary(info) for info in get_conversations().list(principal.user)]


@router.get(
    "/api/conversations/{conversation_id}",
    response_model=ConversationDetailOut,
    dependencies=[requires(Capability.AGENT_ASK)],
)
def read_conversation(conversation_id: str, principal: Principal = CALLER) -> ConversationDetailOut:
    """One thread and what was said in it. No evidence — see the schema."""
    found = get_conversations().load(conversation_id, principal.user)
    if found is None:
        raise NotFoundError("không có hội thoại nào như vậy", conversation_id=conversation_id)
    return _detail(found)


@router.delete(
    "/api/conversations/{conversation_id}",
    response_model=list[ConversationOut],
    dependencies=[requires(Capability.AGENT_ASK)],
)
def delete_conversation(
    conversation_id: str, principal: Principal = CALLER
) -> list[ConversationOut]:
    """Forget a thread. Returns what is left, so the picker needs no second call."""
    if not get_conversations().delete(conversation_id, principal.user):
        raise NotFoundError("không có hội thoại nào như vậy", conversation_id=conversation_id)
    return [_summary(info) for info in get_conversations().list(principal.user)]
