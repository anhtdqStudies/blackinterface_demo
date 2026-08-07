"""Asking a question in words. Two deliveries of one answer.

`POST /api/ask` returns the whole thing; `POST /api/ask/stream` sends the same
thing in frames as it is produced. The pairing is deliberate and mirrors
`/api/live` and `/api/stream`: a client that cannot keep a stream open — a proxy
that buffers, a test, a script — is not thereby cut off from the feature.

POST rather than GET for both, including the streaming one. A question is
arbitrary text and belongs in a body, not in a URL that ends up in access logs
and browser history. That does cost the browser's `EventSource`, which only
issues GETs; the frontend reads the stream with `fetch` instead, which it has to
do anyway to send the body.

`agent.ask` is what this endpoint demands. It is not what the *answers* demand:
each tool declares its own capability and is refused separately, so an account
that may talk to the assistant but may not read the station gets a sentence
saying which permission is missing, rather than a station summary it should
never have seen (ADR-0016 section 5).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from blackinterface.agent import core
from blackinterface.agent.tools import ToolContext
from blackinterface.api.authz import CALLER, requires
from blackinterface.api.deps import get_conversations, get_provider, get_store
from blackinterface.api.schemas import AnswerOut, AskIn
from blackinterface.domain.authz import Capability, Principal

router = APIRouter()


@router.post(
    "/api/ask",
    response_model=AnswerOut,
    dependencies=[requires(Capability.AGENT_ASK)],
)
async def ask(body: AskIn, principal: Principal = CALLER) -> AnswerOut:
    """Answer one question, whole."""
    return await core.answer(
        body.question,
        body.scope,
        body.conversation_id,
        ctx=ToolContext(store=get_store(), principal=principal),
        provider=get_provider(),
        conversations=get_conversations(),
    )


@router.post(
    "/api/ask/stream",
    responses={200: {"content": {"text/event-stream": {}}, "description": "Answer frames"}},
    response_class=StreamingResponse,
    dependencies=[requires(Capability.AGENT_ASK)],
)
async def ask_stream(body: AskIn, principal: Principal = CALLER) -> StreamingResponse:
    """The same answer, as it is produced (Server-Sent Events).

    Frame types are `turn`, `tool`, `evidence`, `token` and `answer`; the last
    carries the complete `AnswerOut` and supersedes anything accumulated from
    `token`. See `agent/core.py` for why that replacement matters.
    """
    return StreamingResponse(
        _frames(body, principal),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # nginx would otherwise sit on each frame
            "Connection": "keep-alive",
        },
    )


async def _frames(body: AskIn, principal: Principal) -> AsyncIterator[str]:
    """The SSE body. Separate from the endpoint so a test can drive it directly."""
    async for event in core.run(
        body.question,
        body.scope,
        body.conversation_id,
        ctx=ToolContext(store=get_store(), principal=principal),
        provider=get_provider(),
        conversations=get_conversations(),
    ):
        yield f"event: {event.name}\ndata: {event.data.model_dump_json()}\n\n"
