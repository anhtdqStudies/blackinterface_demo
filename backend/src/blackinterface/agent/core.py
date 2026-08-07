"""One turn of conversation: plan, read, phrase. In that order, always.

    plan    deterministic, this process, no model      -> which scope
    read    the same facets the interface calls (I5)   -> payload + evidence
    phrase  a language model, or a template            -> words

The order is the architecture. By the time a model is asked for anything, every
number in the answer is fixed and every caveat is recorded; the model is handed
text and returns text and touches nothing else (I4, ADR-0005). If it is
misconfigured, slow, hallucinating or dead, the answer is still computed, still
carries its evidence, and still arrives — only the wording changes.

A model does not choose which tool to call. With two tools and a deterministic
resolver, letting it choose would add a failure mode and no capability. That is
a decision with a trigger, recorded in ADR-0019: when the catalogue reaches a
size where selection is a real judgement — around Module B's alarm and event
tools — the choice moves here, *behind* the same validation, and the plan stays
the thing that runs when the model's answer does not parse.

One generator serves both endpoints. `POST /api/ask` drains it and returns the
last frame; `POST /api/ask/stream` writes each frame to the wire. Two deliveries
of one code path, so a bug cannot exist in only one of them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel

from blackinterface.agent import brief as briefing
from blackinterface.agent import tools
from blackinterface.agent.plan import plan
from blackinterface.agent.provider import LLMProvider, LLMUnavailableError, Prompt
from blackinterface.agent.session import Conversations, Turn, new_turn_id
from blackinterface.agent.tools.station import RESOLVE, SUMMARY
from blackinterface.api.schemas import (
    AnswerOut,
    ResolveOut,
    SummaryOut,
    TokenOut,
    ToolCallOut,
    TurnStartOut,
)
from blackinterface.domain.evidence import EvidenceRecord
from blackinterface.domain.scope import ScopeLike, ScopeRef, as_scope
from blackinterface.errors import ForbiddenError
from blackinterface.logs import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Event:
    """One frame. `name` becomes the SSE event type."""

    name: str
    data: BaseModel


async def run(
    question: str,
    asked_from: ScopeLike,
    conversation_id: str | None,
    *,
    ctx: tools.ToolContext,
    provider: LLMProvider,
    conversations: Conversations,
) -> AsyncIterator[Event]:
    """Answer one question, reporting progress as it goes.

    Frames, in order:

        turn      identifiers and which model is about to be used
        tool      one per tool, before it runs
        evidence  one per tool, after it runs
        token     prose, in pieces; absent when nothing generates prose
        answer    the whole thing, and the authoritative copy of every field

    A client applies `answer` over whatever it accumulated from `token`. That is
    not belt-and-braces: if the model fails halfway, the tokens already sent are
    a truncated sentence about a substation, and the final frame is where they
    get replaced by something complete.
    """
    pane = as_scope(asked_from)
    conversation = conversations.resume(conversation_id, ctx.principal.user)
    intent = plan(question, pane, conversation)
    turn_id = new_turn_id()

    yield Event(
        "turn",
        TurnStartOut(
            conversation_id=conversation.id,
            turn_id=turn_id,
            provider=provider.name,
            generated=provider.generated,
        ),
    )

    evidence: list[EvidenceRecord] = []
    resolution: ResolveOut | None = None
    summary: SummaryOut | None = None
    scope: ScopeRef = pane
    digest: briefing.Brief

    try:
        yield Event("tool", ToolCallOut(tool=RESOLVE, args={"query": question}))
        found = tools.call(RESOLVE, {"query": intent.query}, ctx)
        resolution = _as_resolution(found.payload)
        evidence.append(found.evidence)
        yield Event("evidence", found.evidence)

        scope, notes = _target(resolution, intent.fallback, intent.names)
        if notes is not None:
            digest = notes
        else:
            yield Event("tool", ToolCallOut(tool=SUMMARY, args={"scope": scope.ref}))
            read = tools.call(SUMMARY, {"scope": scope.ref}, ctx)
            summary = _as_summary(read.payload)
            evidence.append(read.evidence)
            yield Event("evidence", read.evidence)
            digest = briefing.for_summary(summary, resolution)
    except ForbiddenError as exc:
        # In band, not as an HTTP error: the caller is entitled to *ask*, and a
        # dead stream tells them less than a sentence saying which permission
        # they are missing. Nothing was read, so there is no evidence to carry.
        missing = exc.detail.get("missing") or [""]
        digest = briefing.for_denied(str(missing[0]))

    text, llm_error = "", None
    if provider.generated:
        prompt = Prompt(question=question, brief=digest.facts, history=conversation.history())
        try:
            async for piece in provider.stream(prompt):
                text += piece
                yield Event("token", TokenOut(text=piece))
        except LLMUnavailableError as exc:
            # Drop what arrived. Half a statement about which disconnectors are
            # open is worse than none, and the computed answer below is complete.
            log.warning("the model failed mid-answer", error=exc.message, provider=provider.name)
            text, llm_error = "", exc.message

    answer = AnswerOut(
        conversation_id=conversation.id,
        turn_id=turn_id,
        question=question,
        scope=scope.ref,
        provider=provider.name,
        generated=provider.generated and not llm_error,
        text=text,
        key=digest.key,
        params=digest.params,
        resolution=resolution,
        summary=summary,
        evidence=evidence,
        llm_error=llm_error,
    )
    conversations.append(
        conversation,
        Turn(
            id=turn_id,
            asked_at=datetime.now(UTC),
            question=question,
            answer=text,
            scope=scope.ref if summary is not None else "",
            asked_from=pane.ref,
        ),
    )
    yield Event("answer", answer)


async def answer(
    question: str,
    asked_from: ScopeLike,
    conversation_id: str | None,
    *,
    ctx: tools.ToolContext,
    provider: LLMProvider,
    conversations: Conversations,
) -> AnswerOut:
    """The same turn, delivered whole. What `POST /api/ask` returns."""
    final: AnswerOut | None = None
    async for event in run(
        question,
        asked_from,
        conversation_id,
        ctx=ctx,
        provider=provider,
        conversations=conversations,
    ):
        if isinstance(event.data, AnswerOut):
            final = event.data
    assert final is not None, "run() must always end with an answer frame"
    return final


def _target(
    resolution: ResolveOut, fallback: ScopeRef, names: tuple[str, ...]
) -> tuple[ScopeRef, briefing.Brief | None]:
    """Which scope to read, or the reason there is nothing to read.

    Four outcomes, and the third is the one that matters: a question that names
    something this station does not have is answered with "no such thing", never
    by quietly answering about somewhere else (`plan.py`).
    """
    if resolution.ambiguous:
        return fallback, briefing.for_ambiguity(resolution)
    if resolution.scope:
        return as_scope(resolution.scope), None
    if names:
        return fallback, briefing.for_unknown(", ".join(names))
    return fallback, None


def _as_resolution(payload: BaseModel) -> ResolveOut:
    assert isinstance(payload, ResolveOut)
    return payload


def _as_summary(payload: BaseModel) -> SummaryOut:
    assert isinstance(payload, SummaryOut)
    return payload
