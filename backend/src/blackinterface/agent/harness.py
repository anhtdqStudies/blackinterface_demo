"""Dựng agent: mô hình nào, tool nào, và ngân sách nào (ADR-0021 §1, §5, §7).

Đây là chỗ *thuê cơ chế, giữ chính sách*. Vòng lặp, sinh JSON Schema từ chữ ký
hàm, validate đối số, retry, đếm token, streaming — Pydantic AI lo. Còn lại là
code của ta và không đi đâu cả:

    lọc tool theo quyền người hỏi      `catalogue(principal)` — ADR-0016 §5
    scope ref phải đã được chứng kiến  `ModelRetry` trong `tools/station.py` — I8
    evidence do tool sinh              `ToolReturn.metadata` — I3
    tool ghi dừng ở cổng duyệt         `requires_approval` — I1

Danh mục tool được **lọc theo quyền trước khi mô hình nhìn thấy**, nên agent
dựng theo từng người hỏi chứ không dựng một lần lúc khởi động. Rẻ: một `Agent`
là vài object Python, còn một danh mục sai là một câu trả lời sai.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from blackinterface.agent.provider import LLMChoice
from blackinterface.agent.session import Conversation
from blackinterface.agent.tools import registry
from blackinterface.agent.tools.registry import ToolContext
from blackinterface.config import Settings
from blackinterface.domain.authz import Principal
from blackinterface.errors import ConfigurationError

#: Thứ mô hình được nói trước tiên. Mọi dòng ở đây **cũng** được cưỡng chế ở chỗ
#: khác — prompt tồn tại để mô hình khỏi tốn lượt đi khám phá luật, không phải để
#: nó là thứ giữ luật. Bất cứ điều gì sẽ thành vấn đề nếu mô hình phớt lờ thì
#: không được phép chỉ sống ở đây.
SYSTEM = """Bạn là trợ lý của hệ thống điều khiển một trạm biến áp.

Bạn trả lời câu hỏi về trạng thái hiện tại của trạm bằng cách gọi tool. Người
hỏi là người trực đang vận hành: họ quyết định làm gì, bạn quyết định đọc gì và
giải thích nó có nghĩa là gì.

Cách làm việc:
- Gọi `resolve` để đổi thứ người trực gọi tên thành scope reference. Không bao
  giờ tự viết scope reference — bạn sẽ bị từ chối.
- Gọi `summary` trên scope reference mà `resolve` đã trả về cho bạn, hoặc trên
  scope mà câu hỏi được đặt từ đó.
- Một cái tên khớp nhiều thứ thì nói ra và hỏi lại cái nào. Đừng chọn hộ.
- Gọi nhiều tool là chuyện bình thường: so sánh hai ngăn nghĩa là resolve và đọc
  cả hai.
- Câu chào hỏi hay câu hỏi về chính bạn thì trả lời thẳng, đừng gọi tool.

Cách trả lời:
- Chỉ nói những gì kết quả tool chứa. Không ước lượng, không "giá trị điển
  hình", không thiết bị nào chưa được trả về cho bạn.
- Chỗ nào vị trí không xác định thì nói là không xác định. Đừng làm tròn thành
  đóng hay mở.
- Số đo ghi `(thang?)` là **chưa biết thang đo**. Đọc lại đúng con số, tuyệt đối
  không tự suy ra kV, MW hay A.
- Trả lời bằng đúng ngôn ngữ câu hỏi, tối đa năm câu.
- Đừng liệt kê bằng chứng; giao diện hiện nó riêng.
- Bạn không thao tác được gì. Nếu bị yêu cầu đóng, cắt, hay reset, hãy nói rằng
  phải có người làm và mô tả việc đó gồm những gì.
"""


def limits(settings: Settings) -> UsageLimits:
    """Ngân sách một lượt, đặt theo hồ sơ **trạm** chứ không theo máy dev.

    `tool_calls_limit` thay `MAX_STEPS = 6` cứng của ADR-0020 §1. Ba trần đọc từ
    `Settings` vì cùng một binary chạy trên một laptop dư sức và trên một máy
    trạm 32GB VRAM — và cái phải vừa là máy trạm.

    `count_tokens_before_request` chặn **trước khi** gửi, nhưng mặc định tắt:
    không phải model nào cũng đếm trước được, và bật nó lên khi chưa thử với
    endpoint thật là đổi một tối ưu lấy nguy cơ mọi câu hỏi đều hỏng. Xem
    `Settings.llm_count_tokens_before_request`. `total_tokens_limit` vẫn chặn sau
    khi gửi, và đó mới là cái thật sự giữ ngân sách.
    """
    return UsageLimits(
        request_limit=settings.llm_max_requests,
        tool_calls_limit=settings.llm_max_tool_calls,
        total_tokens_limit=settings.llm_max_turn_tokens,
        count_tokens_before_request=settings.llm_count_tokens_before_request,
    )


def history(conversation: Conversation, settings: Settings) -> list[ModelMessage]:
    """Earlier turns, as messages the model reads before this question.

    **Prose only, and that is the whole design** (ADR-0022 §1). Pydantic AI would
    happily take back the full `ModelMessage` list it produced last turn — tool
    calls, tool results, digests and all — and every chat harness does exactly
    that. Here it would be wrong, for a reason specific to a substation: the
    station *changes while people are talking about it*. A model that can still
    see `271 CLOSED` from four turns ago has a cheaper way to answer the fifth
    question than calling a tool, and it will take it. The sentence that comes
    out is fluent, is about a breaker, is ten minutes stale, and nothing on the
    screen says so. Quality was GOOD and the timestamp was fresh — I2 does not
    catch this, because the number never went near a point this turn.

    So: what was asked, what was said. Nothing that was *read*.

    `ctx.seen` is not seeded from here either. Remembering that the last turn was
    about Bến Cát helps the model understand *"còn ngăn kia thì sao?"*; it does
    not let it skip `resolve` (`ModelRetry` in `tools/station.py`). Memory is for
    understanding the question, never for answering it.
    """
    messages: list[ModelMessage] = []
    for question, answer in conversation.history(settings.llm_history_turns):
        messages.append(ModelRequest(parts=[UserPromptPart(content=question)]))
        messages.append(ModelResponse(parts=[TextPart(content=answer)]))
    return messages


def build(principal: Principal, model: Model | None) -> Agent[ToolContext, str]:
    """Agent cho đúng một người hỏi.

    `model=None` là hợp lệ và có nghĩa là "chưa cấu hình": `core.py` bắt trường
    hợp đó trước khi chạy, và tab hội thoại nói *chưa cấu hình mô hình* thay vì
    trả lời bằng một template (I4 như ADR-0021 §3 phát biểu lại).
    """
    agent: Agent[ToolContext, str] = Agent(
        model,
        deps_type=ToolContext,
        instructions=SYSTEM,
        output_type=str,
    )
    for tool in registry.catalogue(principal):
        agent.tool(
            name=tool.name,
            description=tool.description,
            requires_approval=tool.requires_approval,
        )(tool.run)
    return agent


def model_for(settings: Settings, choice: LLMChoice) -> Model | None:
    """Mô hình cho một lựa chọn, hoặc `None` khi trợ lý đang tắt.

    Cấu hình sai thì hỏng **ở đây, ầm ĩ**. Một endpoint đã được yêu cầu mà không
    dựng nổi thì tuyệt đối không được lặng lẽ thành "tắt": câu trả lời sẽ vẫn
    tới, trông bình thường, và không bao giờ là thứ người ta đã trả tiền để có.
    """
    if choice.provider == "off":
        return None
    if not choice.model:
        raise ConfigurationError(
            "phải có tên model khi trợ lý được bật",
            setting="BI_LLM_MODEL",
        )
    return OpenAIChatModel(
        choice.model,
        provider=OpenAIProvider(base_url=choice.base_url, api_key=choice.api_key),
        settings=_settings_for(settings, choice),
    )


def _settings_for(settings: Settings, choice: LLMChoice) -> OpenAIChatModelSettings:
    """Tham số gửi kèm mỗi lần gọi, kể cả phần riêng của OpenRouter.

    **Pin nhà cung cấp là bắt buộc, không phải tuỳ chọn.** OpenRouter route cùng
    một model id sang nhiều nhà cung cấp, mỗi nơi một sampling mặc định, một
    tool-call parser, đôi khi một template khác. Không pin thì eval suite hôm nay
    xanh, mai đỏ, mà không ai đổi một dòng code — và ta sẽ đi tìm lỗi trong code
    của mình (ADR-0021 §7).
    """
    extra: dict[str, object] = {}
    if choice.provider_order:
        extra["provider"] = {
            "order": list(choice.provider_order),
            "allow_fallbacks": False,
        }
    return OpenAIChatModelSettings(
        timeout=choice.timeout,
        max_tokens=settings.llm_max_output_tokens,
        **({"extra_body": extra} if extra else {}),
    )
