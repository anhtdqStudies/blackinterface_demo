"""Chọn mô hình nào, và chứng minh nó gọi được. Không còn gì khác.

Trước ADR-0021 file này là cả một client HTTP tự viết: hai phương thức, một
stream theo dòng, một parser tool-call. Pydantic AI làm hết phần đó, nên chỗ này
còn lại đúng hai việc mà **không** framework nào làm hộ được:

  `LLMChoice`   lựa chọn đến từ đâu, và cái nào thắng
  `probe()`     nút «Thử kết nối» — đã lưu ≠ chạy được

Endpoint vẫn là *bất kỳ endpoint nào nói OpenAI chat-completions*: OpenRouter
khi phát triển, vLLM tại trạm (ADR-0021 §7). Khác biệt giữa hai cái là một
base_url, nên vẫn chỉ một hiện thực — thứ đã đúng từ ADR-0019 và không có lý do
gì để đổi.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai.exceptions import UserError
from pydantic_ai.models import Model

from blackinterface.config import Settings
from blackinterface.errors import BlackInterfaceError


class LLMUnavailableError(BlackInterfaceError):
    """Không gọi được mô hình của trợ lý, hoặc nó từ chối.

    Cố ý **không** phải `SourceUnavailableError`. Người trực phải phân biệt được
    "ta đã ngừng nghe thấy trạm" với "dịch vụ diễn đạt đang hỏng" — cái thứ nhất
    là một sự kiện ở trạm biến áp, cái thứ hai là một phiền toái, và các con số
    trên màn hình đáng tin trong trường hợp này mà không đáng tin trong trường
    hợp kia.
    """

    code = "llm_unavailable"
    http_status = 503


@dataclass(frozen=True)
class LLMChoice:
    """Dùng mô hình nào, dưới dạng giá trị thuần.

    Một kiểu riêng, tách khỏi `Settings` lẫn `AssistantConfig` của store, vì hai
    cái đó là *hai nơi một lựa chọn có thể đến từ* và `agent/` không được biết
    cái nào: nó không import được `store/`, còn nhận thẳng `Settings` sẽ biến
    biến môi trường thành nguồn duy nhất có thể. `api/` phân xử thứ tự ưu tiên
    rồi đưa kết quả xuống.
    """

    provider: str = "off"
    base_url: str = ""
    model: str = ""
    api_key: str | None = None
    timeout: float = 120.0
    #: Nhà cung cấp OpenRouter được phép phục vụ model này, theo thứ tự ưu tiên.
    #: Rỗng nghĩa là để OpenRouter tự chọn — chấp nhận được ở máy dev, **không**
    #: chấp nhận được khi chạy eval suite (ADR-0021 §7).
    provider_order: tuple[str, ...] = ()


def choice_from_settings(settings: Settings) -> LLMChoice:
    """Lựa chọn dự phòng: `BI_LLM*`. Thứ CI và máy dev dùng."""
    return LLMChoice(
        provider=settings.llm,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout,
        provider_order=tuple(p for p in settings.llm_provider_order.split(",") if p.strip()),
    )


#: Câu nút «Thử kết nối» gửi đi. Tầm thường một cách cố ý: câu hỏi cần trả lời là
#: *endpoint, tên model và key có ăn khớp với nhau không*, và một câu hỏi thật về
#: trạm sẽ trộn lẫn một lỗi mạng với một câu trả lời tồi.
PROBE = "Trả lời đúng một từ: ok"


async def probe(model: Model) -> str:
    """Gọi mô hình thật và trả về thứ nó nói.

    Ném `LLMUnavailableError` khi không với tới được — đó là toàn bộ mục đích của
    cái nút. Cấu hình chưa bao giờ được chứng minh với một endpoint sống là cấu
    hình không ai nên tin, và `verified_at` trong store ghi lại đúng khác biệt đó.

    Không tool, không deps: đây là phép thử đường truyền, không phải một lượt hỏi.
    """
    agent: Agent[None, str] = Agent(model, output_type=str)
    try:
        run = await agent.run(PROBE)
    except UserError as exc:  # cấu hình sai, không phải mạng hỏng
        raise LLMUnavailableError(f"cấu hình mô hình không dùng được: {exc}") from exc
    except Exception as exc:
        raise LLMUnavailableError(f"không gọi được endpoint mô hình: {exc}") from exc
    return run.output.strip()
