# ADR-0004 — Evidence là typed object do tool sinh

- **Status**: Accepted
- **Date**: 2026-08-04

## Bối cảnh

Trụ cột "evidence-first": mọi câu trả lời phải có nguồn — tool nào gọi, scope nào,
quality/timestamp, hạn chế gì.

Rủi ro: nếu LLM tự soạn phần evidence thì nó có thể **bịa evidence**. Khi đó ta không
có evidence, ta có *thẩm mỹ evidence* — tệ hơn không có, vì nó tạo niềm tin sai.

Bối cảnh vận hành làm rủi ro này nghiêm trọng: mọi point trong OneATS là bộ ba
value/quality/timestamp. Nếu AI nói *"máy cắt 271 đang đóng"* mà không nói quality=BAD
hoặc timestamp cũ 3 tiếng, đó là thứ nguy hiểm cho người vận hành.

## Quyết định

1. **Mỗi tool trả `(payload, EvidenceRecord)`. EvidenceRecord do *tool* sinh,
   không do model sinh.** UI render evidence từ record.
2. Prose của LLM nằm **cạnh** block evidence, được label rõ là *diễn giải*,
   **không bao giờ nằm trong** block evidence.
3. **Quality & staleness cưỡng chế ở Domain API**, không ở prompt:
   - Mọi khẳng định về trạng thái thiết bị **bắt buộc** kèm `(value, quality, age)`.
   - `quality != GOOD` → API trả `state = UNDETERMINED`; agent **không được** khẳng định,
     phải nói "không xác định được, quality = BAD lúc …".
   - Quá ngưỡng staleness → `STALE`, hiện tuổi dữ liệu ngay trên sơ đồ.
4. Kế thừa ngữ nghĩa sẵn có của OneATS thay vì tự định nghĩa lại — manual A.5.1.5:
   earth switch quality xấu → *"grounding status cannot be determined"*.

```python
EvidenceRecord(
    tool="get_bay_snapshot", args={"bay": "D03"}, called_at=...,
    source=Source(kind="opcua", endpoint="…:48050",
                  node_ids=[...], catalog_snapshot="sha256:a3f…"),
    release="sha256:91c…", model_version=654,
    coverage=Coverage(requested=7, resolved=5, missing=["ES36", "DS9"]),
    quality=[PointQ(point="D03.XCBR1.PosSt", value="CLOSED",
                    quality="GOOD", ts_source=..., age_ms=1200)],
    limits=["2 điểm không resolve trong snapshot hiện tại",
            "chưa có dữ liệu lịch sử"],
)
```

## Phương án đã bác bỏ

- **LLM soạn evidence dạng text theo template prompt** — không kiểm chứng được,
  và mô hình có thể bỏ sót đúng cái quan trọng nhất (quality xấu) vì nó "không hợp
  với câu trả lời hay".
- **Chỉ hiện quality khi người dùng hỏi** — sai hướng. Quality xấu là thông tin
  cần đẩy chủ động, không phải thông tin cần kéo.
- **Coi `PosSt` là boolean** — mất `0` (INTERMEDIATE, cơ cấu kẹt) và `3` (BAD),
  đúng hai giá trị mang tính chẩn đoán cao nhất.

## Hệ quả

**Tích cực**
- Evidence kiểm chứng được và test được không cần LLM.
- Người vận hành thấy được giới hạn của câu trả lời → tin đúng mức.

**Tiêu cực**
- Mỗi tool phải làm thêm việc thu thập coverage/quality → không tool nào được viết ẩu.
- UI phức tạp hơn: phải có chỗ hiển thị evidence mà không lấn át câu trả lời.
- Câu trả lời dài hơn, nhiều điều kiện hơn. Chấp nhận — đây là hệ vận hành,
  không phải chatbot.
