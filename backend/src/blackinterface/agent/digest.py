"""Payload đầy đủ -> bản gọn cho mô hình. Cái ngăn context window vỡ (ADR-0021 §5).

Mỗi tool trả về hai thứ khác nhau cho hai người đọc khác nhau:

    metadata   payload đầy đủ + EvidenceRecord  ->  giao diện, qua SSE
    content    bản gọn dựng ở đây               ->  mô hình

Tách vật lý bằng `ToolReturn`, không phải tách bằng kỷ luật (I3).

**Số đo ngày 2026-08-07 trên DEMO_SAS (ModelVersion 654)**, lý do module này tồn
tại — xem `docs/90-progress/status.md` §*SỰ THẬT ĐÃ ĐO*:

    summary(station)   50.339 ký tự  20.064 token (tiktoken cl100k_base)
      trong đó evidence  25.532 ký tự  (51%)
      trong đó số đo     26.231 ký tự  (52%)  — 79 dòng x 313 ký tự

    sau module này          1.771 ký tự     715 token   -> giảm 96,4%

Ba thứ bị bỏ, và chỉ một trong ba là vì kích thước:

1. **`evidence` — bỏ sạch.** Nó do tool sinh và giao diện hiện riêng (I3); mô
   hình đã được dặn đừng liệt kê nó. Bỏ đi là giảm một nửa mà không mất gì.
2. **`source_ref` — bỏ vì I6.** Đó là NodeId thô. Không tầng nào ngoài
   `integration/` được thấy nó, và một mô hình ngôn ngữ chắc chắn không phải
   ngoại lệ. Đây là lý do *đúng luật*, không phải lý do tiết kiệm.
3. **`raw_value`, `deadband_*`, `source_timestamp` — bỏ vì thừa.** `raw_value`
   lặp lại `value`; deadband và dấu thời gian là provenance, mà provenance thì
   đã nằm trong evidence rồi.

Còn lại ~50 ký tự mỗi số đo thay vì 313.

**Đơn vị `?` không bao giờ được in như một đơn vị.** DataServer không công bố
`EngineeringUnits` (đo 2026-08-06), nên `Vlin = 221.08` có thể là V hoặc kV.
In "221.08 V" cạnh một thanh cái 220 kV còn tệ hơn không in gì. Bản gọn đánh dấu
`(thang?)` và nói rõ trong chú giải — nếu mô hình vẫn bịa ra "kV" thì đó là lỗi
đọc được, không phải lỗi ta mời nó mắc.
"""

from __future__ import annotations

from blackinterface.api.schemas import ReadingOut, ResolveOut, SummaryOut
from blackinterface.domain.measurement import Unit
from blackinterface.domain.models import Quality

#: Quá số này thì liệt kê từng dòng hết thông tin và bắt đầu đốt ngân sách. Mô
#: hình được báo còn bao nhiêu chưa hiện và được bảo cách thu hẹp — đó là thông
#: tin hành động được, khác với một danh sách bị cắt cụt không lời giải thích.
MAX_READINGS = 40


def for_summary(out: SummaryOut) -> str:
    """`summary` như mô hình đọc nó."""
    lines = [f"{out.scope} ({out.kind}){f' — {out.label}' if out.label else ''}"]

    if out.bays:
        shown = ", ".join(out.bays[:20])
        more = f" (+{len(out.bays) - 20} nữa)" if len(out.bays) > 20 else ""
        lines.append(f"ngăn ({len(out.bays)}): {shown}{more}")

    if out.switch_states:
        lines.append("thiết bị đóng cắt: " + _counts(out.switch_states))
    if out.node_states:
        lines.append("đoạn mạch: " + _counts(out.node_states))

    lines.append(_readings(out.measurements))

    if out.issues:
        lines.append(f"vấn đề ({len(out.issues)}):")
        lines += [
            f"  [{i.severity}] {i.message}" + (f" — {i.subject}" if i.subject else "")
            for i in out.issues[:10]
        ]
        if len(out.issues) > 10:
            lines.append(f"  (+{len(out.issues) - 10} nữa)")

    return "\n".join(lines)


def for_resolve(out: ResolveOut) -> str:
    """`resolve` như mô hình đọc nó.

    Khi nhập nhằng thì **không** chọn hộ: liệt kê đủ để mô hình hỏi lại người
    trực. "Lai Uyen" là tên của cả E01 lẫn E02 trên DEMO_SAS, và đoán một trong
    hai là cách trả lời tự tin về nhầm ngăn.
    """
    if out.ambiguous or (out.scope is None and out.candidates):
        lines = [f"{out.query!r} khớp {len(out.candidates)} thứ — hỏi người trực chọn:"]
        lines += [
            f"  {c.scope} — {c.label or c.kind} (khớp {c.tier}: {c.matched!r})"
            for c in out.candidates[:12]
        ]
        if len(out.candidates) > 12:
            lines.append(f"  (+{len(out.candidates) - 12} nữa)")
        return "\n".join(lines)

    if out.scope is None:
        return (
            f"{out.query!r} không khớp thứ gì trong trạm này. Đừng đoán sang thứ khác — "
            f"nói với người trực là không tìm thấy."
        )

    return f"{out.query!r} -> {out.scope}" + (f" — {out.label}" if out.label else "")


def _counts(counts: dict[str, int]) -> str:
    """`{'CLOSED': 27, 'OPEN': 53}` -> `CLOSED 27, OPEN 53`, bỏ số không."""
    return ", ".join(f"{name} {n}" for name, n in sorted(counts.items()) if n)


def _readings(readings: list[ReadingOut]) -> str:
    if not readings:
        return "số đo: không có"

    head = f"số đo ({len(readings)}) — dòng: <đối tượng> <đại lượng> <giá trị> <đơn vị>"
    unverified = any(r.unit is Unit.UNKNOWN for r in readings)
    if unverified:
        head += "; `(thang?)` = biết đại lượng, CHƯA biết thang đo — cấm tự suy ra kV/MW"

    lines = [head]
    lines += [f"  {_reading(r)}" for r in readings[:MAX_READINGS]]
    if len(readings) > MAX_READINGS:
        left = len(readings) - MAX_READINGS
        lines.append(
            f"  (+{left} số đo chưa hiện — gọi lại `summary` trên một ngăn cụ thể để xem hết)"
        )
    return "\n".join(lines)


def _reading(r: ReadingOut) -> str:
    """Một số đo, ~50 ký tự thay vì 313.

    `value` là None khi quality khác GOOD — đó là I2 đã được `build_summary`
    cưỡng chế từ trước, và ở đây nó in ra thành chữ *không xác định* chứ không
    thành một con số trông có vẻ dùng được.
    """
    where = r.subject.split(":", 1)[-1]
    if r.value is None:
        return f"{where} {r.quantity} không xác định ({r.quality})"

    value = _number(r.value)
    if r.unit is Unit.UNKNOWN:
        return f"{where} {r.quantity} {value} (thang?)"
    unit = f" {r.unit}" if r.unit is not Unit.NONE else ""
    stale = "" if r.quality is Quality.GOOD else f" ({r.quality})"
    return f"{where} {r.quantity} {value}{unit}{stale}"


def _number(value: float) -> str:
    """Ba chữ số có nghĩa là đủ để nói về một trạm, và cắt 2/3 độ dài.

    `10.700414657592773` không mang nhiều thông tin hơn `10.7` với người đọc,
    nhưng tốn gấp bốn lần ngân sách. Số đầy đủ vẫn nằm nguyên trong payload đi
    ra giao diện.
    """
    if value == 0:
        return "0"
    rounded = round(value, 3)
    if rounded == int(rounded) and abs(rounded) < 1e6:
        return str(int(rounded))
    return f"{rounded:g}"
