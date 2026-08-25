"""Một lượt hội thoại. Một generator, hai cửa.

Sau ADR-0021 chỉ còn **một** đường: mô hình chọn đọc gì, trong ngân sách của
`harness.limits()`. Đường thứ hai — `plan → read → template` — đã bị xoá cùng
`plan.py` và `brief.py`, và lý do đáng ghi lại vì nó ngược với trực giác:

  Cái giữ cho *"giao diện dùng được khi mô hình chết"* **không phải** câu trả lời
  template. Là **I5** — frontend gọi thẳng Domain API, BlackCore không phải
  proxy. Mô hình chết thì sơ đồ, panel, số đo, SSE không hề biết. Sàn template
  chưa bao giờ giữ lời hứa mà người ta tưởng nó giữ; nó chỉ làm cho tab hội
  thoại trả về *một cái gì đó*, và cái gì đó ấy có lần là nguyên bảng trạng thái
  80 thiết bị đáp lại câu «hello» (ADR-0021 §Bối cảnh).

Không cấu hình mô hình thì tab hội thoại nói *chưa cấu hình*. Đó là I4 sau khi
ADR-0021 §3 thu hẹp nó về đúng phần lõi.

Khung, theo thứ tự:

    turn        định danh và mô hình sắp dùng
    tool        một khung mỗi tool, **trước** khi nó chạy
    evidence    một khung mỗi tool, **sau** khi nó chạy
    resolution  payload `resolve`, ngay sau evidence của nó
    summary     payload `summary`, ngay sau evidence của nó — câu tính được
                hiện trước khi mô hình viết xong
    token       văn xuôi, từng mẩu
    answer      toàn bộ, và là bản chính thức của mọi trường

Client áp `answer` lên trên thứ nó đã gom từ `token`. Không phải thắt lưng kèm
dây đeo quần: nếu mô hình hỏng giữa chừng thì đám token đã gửi là một câu **dở
dang** về một trạm biến áp, và khung cuối là chỗ chúng bị thay bằng thứ hoàn
chỉnh.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel
from pydantic_ai import UsageLimitExceeded
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
)
from pydantic_ai.models import Model

from blackinterface.agent import harness
from blackinterface.agent.provider import LLMUnavailableError
from blackinterface.agent.session import Conversation, Conversations, Turn, new_turn_id
from blackinterface.agent.tools.registry import ToolContext
from blackinterface.api.schemas import (
    AnswerOut,
    TokenOut,
    ToolCallOut,
    TurnStartOut,
)
from blackinterface.config import Settings
from blackinterface.domain.evidence import EvidenceRecord
from blackinterface.domain.scope import ScopeLike, ScopeRef, as_scope
from blackinterface.errors import ForbiddenError
from blackinterface.logs import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Event:
    """Một khung. `name` thành kiểu event của SSE."""

    name: str
    data: BaseModel


async def run(
    question: str,
    asked_from: ScopeLike,
    conversation_id: str | None,
    *,
    ctx: ToolContext,
    model: Model | None,
    model_name: str,
    settings: Settings,
    conversations: Conversations,
) -> AsyncIterator[Event]:
    """Trả lời một câu hỏi, báo tiến trình dọc đường."""
    pane = as_scope(asked_from)
    conversation = conversations.resume(conversation_id, ctx.principal.user)
    turn_id = new_turn_id()

    # Người trực đang nhìn scope này, nên mô hình không bịa ra nó (I8).
    ctx.seen.add(pane.ref)

    yield Event(
        "turn",
        TurnStartOut(
            conversation_id=conversation.id,
            turn_id=turn_id,
            provider=model_name,
            generated=model is not None,
        ),
    )

    if model is None:
        answer = _assemble(
            question=question,
            conversation_id=conversation.id,
            turn_id=turn_id,
            scope=pane,
            model_name=model_name,
            ctx=ctx,
            text="",
            llm_error=None,
            unconfigured=True,
        )
        yield Event("answer", answer)
        return

    agent = harness.build(ctx.principal, model)
    text, llm_error = "", None
    pending_tool: str | None = None

    try:
        async with agent.run_stream_events(
            _prompt(question, pane),
            deps=ctx,
            # Prose of earlier turns, and nothing they read (ADR-0022 §1).
            # `harness.history()` is where that line is drawn and defended.
            message_history=harness.history(conversation, settings),
            usage_limits=harness.limits(settings),
        ) as events:
            async for event in events:
                tool_for_result = (
                    pending_tool if isinstance(event, FunctionToolResultEvent) else None
                )
                for frame in _frames(event, ctx, tool_for_result):
                    yield frame
                if isinstance(event, FunctionToolCallEvent):
                    pending_tool = event.part.tool_name
                elif isinstance(event, FunctionToolResultEvent):
                    pending_tool = None
                text += _prose(event)
    except UsageLimitExceeded as exc:
        # Hết ngân sách là một kết cục, không phải một sự cố. Giữ lại những gì đã
        # đọc và nói thẳng là đã dừng ở đâu — im lặng rơi sang một đường khác là
        # đúng thứ ADR-0021 §5 bỏ đi.
        log.warning("agent hit its budget", error=str(exc), user=ctx.principal.user)
        llm_error = f"đã dừng khi hết ngân sách một lượt: {exc}"
    except ForbiddenError as exc:
        # Người hỏi không được đọc thứ này. Trả trong luồng, không phải bằng lỗi
        # HTTP: họ có quyền *hỏi*, và một stream chết nói với họ ít hơn một câu
        # cho biết đang thiếu quyền nào.
        missing = exc.detail.get("missing") or [""]
        llm_error = f"thiếu quyền: {missing[0]}"
    except Exception as exc:
        # Bỏ những gì đã tới. Nửa câu về việc dao nào đang mở tệ hơn không có câu
        # nào — và evidence thì vẫn còn nguyên, nên người trực vẫn đọc được số.
        log.warning("the model failed mid-answer", error=str(exc), provider=model_name)
        text, llm_error = "", str(LLMUnavailableError(f"không gọi được mô hình: {exc}").message)

    answer = _assemble(
        question=question,
        conversation_id=conversation.id,
        turn_id=turn_id,
        scope=_answered_about(ctx, pane),
        model_name=model_name,
        ctx=ctx,
        text=text.strip(),
        llm_error=llm_error,
        unconfigured=False,
    )
    _remember(conversations, conversation, answer, pane, turn_id)
    yield Event("answer", answer)


async def answer(
    question: str,
    asked_from: ScopeLike,
    conversation_id: str | None,
    *,
    ctx: ToolContext,
    model: Model | None,
    model_name: str,
    settings: Settings,
    conversations: Conversations,
) -> AnswerOut:
    """Cùng một lượt, giao nguyên khối. Thứ `POST /api/ask` trả về."""
    final: AnswerOut | None = None
    async for event in run(
        question,
        asked_from,
        conversation_id,
        ctx=ctx,
        model=model,
        model_name=model_name,
        settings=settings,
        conversations=conversations,
    ):
        if isinstance(event.data, AnswerOut):
            final = event.data
    assert final is not None, "run() luôn phải kết thúc bằng một khung answer"
    return final


def _prompt(question: str, asked_from: ScopeRef) -> str:
    """Câu hỏi, kèm thứ người trực đang nhìn.

    Nói ra chứ không để mô hình đoán: *"còn số đo thì sao?"* chỉ có nghĩa khi
    biết màn hình đang ở đâu, và scope của pane là bằng chứng cứng về điều đó.
    """
    return (
        f"{question}\n\n"
        f"(Người trực đang xem {asked_from.ref}. Nếu câu hỏi không gọi tên thứ gì "
        f"thì nó nói về chỗ đó.)"
    )


def _frames(event: object, ctx: ToolContext, tool_for_result: str | None) -> list[Event]:
    """Event của Pydantic AI -> khung của ta.

    `agent/` mô tả chuyện gì xảy ra; `api/` quyết định đưa nó lên dây thế nào.
    Dịch ở đây để một lần Pydantic AI đổi tên event không lan tới frontend.
    """
    if isinstance(event, FunctionToolCallEvent):
        args = event.part.args_as_dict()
        return [Event("tool", ToolCallOut(tool=event.part.tool_name, args=_flat(args)))]
    if isinstance(event, FunctionToolResultEvent):
        out: list[Event] = []
        evidence = _evidence_of(event)
        if evidence is not None:
            out.append(Event("evidence", evidence))
        if tool_for_result == "resolve" and ctx.resolution is not None:
            out.append(Event("resolution", ctx.resolution))
        elif tool_for_result == "summary" and ctx.summary is not None:
            out.append(Event("summary", ctx.summary))
        return out
    piece = _prose(event)
    return [Event("token", TokenOut(text=piece))] if piece else []


def _prose(event: object) -> str:
    """Chữ mới trong một event, hoặc "" nếu event này không mang chữ.

    **Mẩu đầu tiên đến trong `PartStartEvent`, không phải `PartDeltaEvent`.**
    Bỏ sót nó thì câu trả lời mất chữ đầu — và trên màn hình nó hiện thành một
    câu cụt đầu chạy ra, thứ trông y như mô hình bị cắt ngang. Một test bắt được
    đúng lỗi này, nên hai nhánh nằm chung một hàm để không nhánh nào bị quên.
    """
    if isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
        return event.part.content
    if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
        return event.delta.content_delta
    return ""


def _evidence_of(event: FunctionToolResultEvent) -> EvidenceRecord | None:
    """Evidence của một tool vừa xong.

    Lấy từ `metadata` — thứ mô hình **không** nhìn thấy — chứ không parse ra từ
    `content`. Đó là I3 nói bằng cấu trúc: bằng chứng do tool sinh, không phải
    thứ đọc ngược lại từ chữ.

    `None` khi tool bị `ModelRetry` từ chối hoặc ném lỗi: không có gì được đọc,
    nên không có bằng chứng nào để kể.
    """
    metadata = getattr(event.part, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    evidence = metadata.get("evidence")
    return evidence if isinstance(evidence, EvidenceRecord) else None


def _flat(args: dict[str, object]) -> dict[str, str | int | float | bool | None]:
    """Đối số phẳng để ghi log và đưa lên dây.

    Thứ lồng nhau bị **bỏ** chứ không bị ép thành chuỗi: một đối số tool không
    log được, không replay được, không đưa vào evidence được thì không phải thứ
    hệ này nhận — và lặng lẽ ép `{'a': 1}` thành `"{'a': 1}"` là cách tuồn một
    cái như thế vào.
    """
    return {k: v for k, v in args.items() if isinstance(v, str | int | float | bool) or v is None}


def _answered_about(ctx: ToolContext, pane: ScopeRef) -> ScopeRef:
    """Scope câu trả lời thật sự nói về: cái đọc cuối, nếu có đọc gì."""
    if ctx.summary is not None:
        return ScopeRef.parse(ctx.summary.scope)
    return pane


def _assemble(
    *,
    question: str,
    conversation_id: str,
    turn_id: str,
    scope: ScopeRef,
    model_name: str,
    ctx: ToolContext,
    text: str,
    llm_error: str | None,
    unconfigured: bool,
) -> AnswerOut:
    """Một chỗ duy nhất dựng câu trả lời, để hai cửa không thể trôi khỏi nhau."""
    return AnswerOut(
        conversation_id=conversation_id,
        turn_id=turn_id,
        question=question,
        scope=scope.ref,
        provider=model_name,
        generated=bool(text) and not unconfigured,
        text=text,
        resolution=ctx.resolution,
        summary=ctx.summary,
        evidence=list(ctx.evidence),
        llm_error=llm_error,
        unconfigured=unconfigured,
    )


def _remember(
    conversations: Conversations,
    conversation: Conversation,
    answer: AnswerOut,
    pane: ScopeRef,
    turn_id: str,
) -> None:
    """Ghi lại lượt. `scope` chỉ khi thật sự đã đọc gì đó — một câu hỏi không trả
    lời được không được phép thành chủ đề mà câu sau thừa kế."""
    conversations.append(
        conversation,
        Turn(
            id=turn_id,
            asked_at=datetime.now(UTC),
            question=answer.question,
            answer=answer.text,
            scope=answer.scope if answer.summary is not None else "",
            asked_from=pane.ref,
        ),
    )
