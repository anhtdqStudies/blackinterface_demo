"""Agent được phép làm gì, và cái cổng mọi lần dùng phải đi qua.

Một registry, và hai luật cưỡng chế bằng cấu trúc chứ không bằng lời hứa
(I1, ADR-0011 §3 như [ADR-0021](../../../../docs/10-architecture/adr/0021-agent-harness.md) §2 phát biểu lại):

  * `agent/` **không import được** `control/` lẫn `integration/` — `tools/check.py`
    mục 2 làm đỏ build nếu có. Một tool ở đây không có gì để ghi *bằng*.
  * Tool khai capability nằm trong `READ_ONLY` thì chạy thẳng. Tool khai bất kỳ
    capability nào khác — thứ **thay đổi** một cái gì đó — **bắt buộc**
    `requires_approval=True`, và `register()` từ chối ngay lúc import nếu thiếu.

Luật thứ hai là chỗ I1 đã đổi hình ngày 2026-08-07 và **chặt thêm chứ không nới**.
Phát biểu cũ là *«tool ghi không tồn tại»* — một khẳng định về **danh mục**, và
nó sẽ phải nới ra vào đúng ngày module C mở, vì lúc đó `control.draft` trở thành
quyền hợp pháp của một số tài khoản mà agent thì mượn quyền của người hỏi
(ADR-0016 §5). Phát biểu mới là khẳng định về **đường thi hành**: tool ghi được
phép có tên trong danh mục, nhưng không tự chạy được. Đường thi hành thì test
được; danh mục thì chỉ đếm được.

`control.sign` không bao giờ nằm trong tập quyền agent mượn được. Agent soạn
phiếu, người ký.

Mọi tool trả `ToolReturn`, và đó là chỗ I3 đứng: `content` là bản gọn cho mô
hình, `metadata` mang payload đầy đủ + `EvidenceRecord` và **mô hình không nhìn
thấy nó**. Hai đường tách vật lý, không tách bằng kỷ luật — xem `agent/digest.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import ToolReturn

from blackinterface.api.schemas import ResolveOut, SummaryOut
from blackinterface.api.source import StationStore
from blackinterface.domain.authz import Capability, Principal
from blackinterface.domain.evidence import EvidenceRecord
from blackinterface.errors import ForbiddenError
from blackinterface.logs import get_logger

log = get_logger(__name__)

#: Capability một tool được khai mà **không** cần duyệt. Mọi cái ở đây là một
#: lần *đọc*.
#:
#: Chú ý cái vắng mặt, vì chỗ vắng mặt mới là luật: `alarm.ack`, `control.draft`,
#: `control.sign`, `knowledge.write`, `model.edit`, `model.connect`,
#: `model.publish`, `account.manage` đều thay đổi một cái gì đó.
#: `report.export` thì *đọc*, nhưng gửi kết quả ra khỏi máy — một tác động lên
#: thế giới y như ghi. Agent soạn báo cáo, người gửi.
READ_ONLY: frozenset[Capability] = frozenset(
    {
        Capability.STATION_READ,
        Capability.ALARM_READ,
        Capability.EVENT_READ,
        Capability.TREND_READ,
        Capability.REPORT_READ,
        Capability.KNOWLEDGE_READ,
        Capability.PROTECTION_READ,
        Capability.BINDING_READ,
        Capability.AUDIT_READ,
    }
)


@dataclass
class ToolContext:
    """Mọi thứ một tool được chạm, và trạng thái của đúng một lượt hỏi.

    Đây cũng là `deps` của Pydantic AI: tool nhận nó qua `RunContext[ToolContext]`.
    Không có gì toàn cục, nên một test dựng được một cái.

    `principal` là **người hỏi**, không bao giờ là agent. Agent không có danh
    tính và không có quyền riêng — nó chạy dưới quyền của người đang gõ
    (ADR-0016 §5). Vì thế cùng một câu hỏi cho ra câu trả lời khác nhau với người
    trực và với quản trị viên.

    Không `frozen`: `seen` và `evidence` lớn dần trong lượt, và chúng là *trạng
    thái của lượt* chứ không phải cấu hình. Giữ chúng ở đây thay vì ở một biến
    toàn cục là lý do hai lượt chạy song song không giẫm lên nhau.
    """

    store: StationStore
    principal: Principal
    #: Scope ref lượt này **đã được trả về cho mô hình** (I8). Mồi bằng scope mà
    #: câu hỏi được đặt từ đó — người trực đang nhìn nó, nên mô hình không bịa ra.
    seen: set[str] = field(default_factory=set)
    #: Evidence theo đúng thứ tự tool chạy. Bản kê đầy đủ của lượt (ADR-0013).
    evidence: list[EvidenceRecord] = field(default_factory=list)
    #: *Cái cuối* của mỗi loại — thứ giao diện hiện cạnh câu trả lời. Với một câu
    #: hỏi so sánh thì lần đọc cuối là cái câu kết nói về.
    resolution: ResolveOut | None = None
    summary: SummaryOut | None = None


#: Hàm một tool thật sự là. Tham số đầu là `RunContext[ToolContext]`; phần còn
#: lại là đối số có kiểu, và **Pydantic AI sinh JSON Schema từ chính chữ ký +
#: docstring**. Không còn schema viết tay để lệch khỏi hàm nữa.
ToolFunc = Callable[..., Any]


@dataclass(frozen=True)
class Tool:
    """Một việc agent làm được, kèm điều kiện được phép làm."""

    name: str
    #: Mô hình được kể tool này để làm gì. Nằm cạnh code chứ không nằm trong một
    #: file prompt, để nó không trôi khỏi thứ đang chạy.
    description: str
    requires: Capability
    run: ToolFunc
    #: Bắt buộc `True` cho mọi capability ngoài `READ_ONLY`. Tool dừng ở khung
    #: duyệt và chỉ chạy tiếp sau chữ ký của người (I1).
    requires_approval: bool = False


#: Tên -> tool. `register()` đổ đầy lúc import `agent.tools`.
TOOLS: dict[str, Tool] = {}


class WriteToolError(RuntimeError):
    """Ai đó đăng ký một tool đổi được thứ gì đó mà không qua cổng duyệt (I1).

    `RuntimeError` trần và ném lúc **import**, không phải lúc gọi: một tool tự
    thực thi không được phép tồn tại đủ lâu để có thể với tới, và một tiến trình
    khởi động xong rồi mới từ chối một request thì đã trót ship nó rồi.
    """


def register(tool: Tool) -> Tool:
    if tool.requires not in READ_ONLY and not tool.requires_approval:
        raise WriteToolError(
            f"tool {tool.name!r} đòi {tool.requires.value!r} — không phải một lần đọc — "
            f"mà không khai requires_approval=True. Agent không bao giờ có tool TỰ "
            f"THỰC THI (AGENTS.md I1, ADR-0021 §2)."
        )
    if tool.name in TOOLS:
        raise RuntimeError(f"trùng tên tool: {tool.name!r}")
    TOOLS[tool.name] = tool
    return tool


def authorize(ctx: ToolContext, tool_name: str) -> None:
    """Từ chối nếu người hỏi không được dùng tool này. Gọi trong thân tool.

    Thừa so với `catalogue()` — mô hình chỉ được kể những tool nó gọi được. Giữ
    lại vì đúng lý do ADR-0019 §4 giữ ba lớp: nới danh mục không được phép nới
    luôn cái cổng gác chính nó. Một 403 ở đây, không phải một câu trả lời im
    lặng hẹp hơn: bỏ bớt phần người ta không được xem tạo ra một câu trả lời
    *đọc như thể đã đầy đủ*, tệ hơn là bị nói không.
    """
    tool = TOOLS.get(tool_name)
    if tool is None:  # pragma: no cover - chỉ xảy ra khi lập trình sai
        raise RuntimeError(f"không có tool nào tên {tool_name!r}")
    if not ctx.principal.can(tool.requires):
        log.warning(
            "tool denied", tool=tool.name, user=ctx.principal.user, missing=tool.requires.value
        )
        raise ForbiddenError(
            "tài khoản này không được dùng phần đó của trợ lý",
            tool=tool.name,
            missing=[tool.requires.value],
        )


def catalogue(principal: Principal) -> tuple[Tool, ...]:
    """Những tool người hỏi thật sự dùng được, theo thứ tự ổn định.

    Lọc theo quyền **trước khi** đưa cho mô hình: kể ra một tool rồi từ chối nó
    chỉ tốn một vòng lặp và một dòng bối rối trong câu trả lời.
    """
    return tuple(t for _, t in sorted(TOOLS.items()) if principal.can(t.requires))


def result(*, content: str, payload: Any, evidence: EvidenceRecord) -> ToolReturn:
    """Một kết quả tool, hai người đọc, tách vật lý (I3).

    Dựng ở một chỗ để không tool nào lỡ đưa payload đầy đủ cho mô hình — đó là
    cách 20.064 token đi vào một context window 40k và làm hỏng lượt hỏi.
    """
    return ToolReturn(
        return_value=content,
        metadata={"payload": payload, "evidence": evidence},
    )
