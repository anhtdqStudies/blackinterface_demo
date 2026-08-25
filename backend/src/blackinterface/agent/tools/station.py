"""Hai tool của lát cắt mỏng: gọi tên một thứ, rồi đọc nó.

Hai không phải là một con số tạm. Chúng là hai nửa của mọi câu hỏi trong
`document/@Station_UseCases 1.xlsx`: *phần nào của trạm* và *nó đang thế nào*.
Thêm use case thì thêm **scope và facet**, không thêm tool — nếu một use case
mới đòi một tool mới thì mô hình địa chỉ hoá sai (I8). ADR-0021 §6 mở rộng danh
mục dọc theo trục facet (`trace`, `history`, `summary(scope, facet)`), đúng trục
đó, chứ không mở theo trục use case.

Không tool nào tự tính gì. `summary` gọi đúng hàm nằm sau `GET /api/summary`,
dưới quyền của người hỏi (I5): agent dùng đúng API mà giao diện dùng, không có
đường riêng và không có quyền rộng hơn.

**Chỗ đáng giá nhất của file này là `_witnessed()`.** `bay:E01` *có tồn tại*, nên
không tầng nào phía dưới phản đối nếu mô hình gõ nó ra từ trí nhớ — và đó chính
là chỗ nguy hiểm: một câu trả lời tự tin về **nhầm ngăn** trông y hệt một câu trả
lời đúng. Từ chối được ném bằng `ModelRetry`, tức là nó quay lại với mô hình dưới
dạng một câu nhắc chứ không phải một exception làm hỏng lượt — vì lỗi này sửa
được, và cách sửa (gọi `resolve` trước) chính là hành vi ta muốn.
"""

from __future__ import annotations

from pydantic_ai import ModelRetry, RunContext, ToolReturn

from blackinterface import __version__
from blackinterface.agent import digest
from blackinterface.agent import resolve as resolver
from blackinterface.agent.tools.registry import (
    Tool,
    ToolContext,
    authorize,
    register,
    result,
)
from blackinterface.api.schemas import ResolveOut, ScopeCandidateOut
from blackinterface.api.summary import build_summary, source_kind
from blackinterface.domain.authz import Capability
from blackinterface.domain.evidence import EvidenceBuilder, EvidenceRecord, Source
from blackinterface.domain.models import StationGraph
from blackinterface.domain.scope import ScopeRef

RESOLVE = "resolve"
SUMMARY = "summary"


def run_resolve(ctx: RunContext[ToolContext], query: str) -> ToolReturn:
    """Đổi thứ người trực gọi tên thành một scope reference.

    Args:
        query: Nguyên văn thứ người trực gọi — số hiệu EVN như `271`, tên ngăn,
            hay một id. Đừng sửa lời họ trước khi tra.
    """
    deps = ctx.deps
    authorize(deps, RESOLVE)

    graph = deps.store.graph
    match = resolver.resolve(graph, query)
    if not match.found:
        match = resolver.find_in_text(graph, query)

    chosen = match.scope
    payload = ResolveOut(
        query=query,
        scope=chosen.ref if chosen is not None else None,
        label=chosen.label if chosen is not None else "",
        ambiguous=match.ambiguous,
        candidates=[
            ScopeCandidateOut(
                scope=c.ref,
                kind=c.kind.value,
                label=c.label,
                tier=c.tier.name.lower(),
                matched=c.matched,
            )
            for c in match.candidates
        ],
    )

    # Mọi ref lần này trao cho mô hình đều thành hợp lệ để nó truyền lại.
    deps.seen |= _witnessed(payload)
    deps.resolution = payload

    subject = chosen if chosen is not None else ScopeRef.station()
    evidence = _evidence(RESOLVE, subject, graph, deps, query)
    deps.evidence.append(evidence)
    return result(content=digest.for_resolve(payload), payload=payload, evidence=evidence)


def run_summary(ctx: RunContext[ToolContext], scope: str) -> ToolReturn:
    """Đọc trạng thái hiện tại của một scope: vị trí đóng cắt, đoạn nào có điện,
    số đo tương tự, và các vấn đề đang mở.

    Args:
        scope: Một scope reference **do `resolve` trả về**, ví dụ `bay:D03` hay
            `device:D03.XCBR1`. Đừng bao giờ tự gõ từ trí nhớ — gọi `resolve` trước.
    """
    deps = ctx.deps
    authorize(deps, SUMMARY)

    if scope not in deps.seen:
        raise ModelRetry(
            f"từ chối: {scope!r} không phải thứ `resolve` đã trả về. Gọi `resolve` với "
            f"đúng lời người trực nói, rồi dùng scope reference trong kết quả của nó."
        )

    out = build_summary(deps.store, scope, actor=deps.principal.user)
    deps.summary = out
    deps.evidence.append(out.evidence)
    return result(content=digest.for_summary(out), payload=out, evidence=out.evidence)


def _witnessed(payload: ResolveOut) -> set[str]:
    """Mọi scope reference kết quả `resolve` này đã trao cho mô hình."""
    found = {candidate.scope for candidate in payload.candidates}
    if payload.scope:
        found.add(payload.scope)
    return found


def _evidence(
    tool: str, subject: ScopeRef, graph: StationGraph, ctx: ToolContext, query: str
) -> EvidenceRecord:
    """`resolve` mang evidence dù không đọc điểm nào, và đó không phải nghi thức:
    những cái tên nó khớp đến từ **một** phiên bản model của **một** trạm, và
    "271 là máy cắt của D03" hết đúng ngay khi ai đó nạp một trạm khác. Xuất xứ
    là toàn bộ nội dung của câu trả lời này."""
    builder = EvidenceBuilder(
        tool,
        subject,
        source=Source(
            kind=source_kind(graph.source),
            endpoint=graph.source or None,
            catalog_snapshot=graph.model_version,
        ),
        actor=ctx.principal.user or None,
        args={"query": query},
        release=__version__,
        model_version=graph.model_version,
    )
    return builder.build()


register(
    Tool(
        name=RESOLVE,
        description=(
            "Đổi thứ người trực gọi tên — số hiệu EVN như 271, tên ngăn, một id — "
            "thành scope reference. Trả về mọi thứ khớp; nhiều kết quả nghĩa là "
            "phải hỏi lại xem cái nào."
        ),
        requires=Capability.STATION_READ,
        run=run_resolve,
    )
)

register(
    Tool(
        name=SUMMARY,
        description=(
            "Đọc trạng thái hiện tại của một scope: vị trí đóng cắt, đoạn nào có "
            "điện, số đo tương tự, và các vấn đề đang mở."
        ),
        requires=Capability.STATION_READ,
        run=run_summary,
    )
)
