# ADR-0013 — Evidence envelope trên mọi facet, ngay từ facet đầu tiên

- **Status**: Accepted
- **Date**: 2026-08-05
- **Chi tiết hoá**: ADR-0004 (*Evidence là typed object do tool sinh*).
  ADR-0004 nói evidence **là gì**; ADR này nói nó **nằm ở đâu** và **khi nào phải có**.

## Bối cảnh

ADR-0004 đã chốt hình dạng `EvidenceRecord` từ 2026-08-04, nhưng chưa được hiện
thực — `status.md` ghi rõ là *"chưa làm, cố ý"*, vì lúc đó thiết kế nó trước khi
có module tương ứng là đoán.

Bối cảnh nay đã khác. ADR-0010 chốt trục `scope × facet`, và giai đoạn tới sẽ
sinh ra một loạt facet mang khẳng định về trạm: `measurement`, `alarm`, `tagging`,
`authority`, `interlock`, `history`. Mỗi facet là một chỗ để nói sai.

Câu hỏi thời điểm rất cụ thể:

| Làm evidence lúc | Số endpoint phải sửa | Số người dùng đang phụ thuộc |
|---|---|---|
| **bây giờ** (2 facet) | 2 | 0 |
| sau module A + B + E | ~15 | có, kể cả agent |

Và có một chi phí ẩn nghiêm trọng hơn số endpoint: evidence trích dẫn
`release` + `catalog_snapshot` + `model_version`. Không gắn evidence từ đầu thì
những câu trả lời đã phát ra **không truy ngược được** — đúng vấn đề mà
`docs/10-architecture/overview.md` gọi là *"nói dối hồi tố"* khi ai đó sửa project
OneATS.

## Quyết định

### 1. Mọi payload của facet mang một field `evidence`

```python
class FacetOut(BaseModel):
    evidence: EvidenceRecord
```

Không dùng generic wrapper `Envelope[T]`. Dùng **mixin/base class** để mỗi facet
vẫn có schema riêng có tên rõ ràng trong `openapi.json` — quan trọng, vì
`schema.d.ts` sinh từ đó và ADR-0009 xem type an toàn xuyên biên giới là lý do
kỹ thuật quan trọng nhất của frontend.

### 2. `EvidenceRecord` mang `subject` là một scope ref

Nối trực tiếp với ADR-0010:

```python
EvidenceRecord(
    tool="summary", subject="bay:D03", args={...}, called_at=...,
    source=Source(kind="opcua", endpoint="…:48050",
                  node_ids=[...], catalog_snapshot="sha256:a3f…"),
    release="sha256:91c…", model_version=654,
    coverage=Coverage(requested=7, resolved=5, missing=["ES36", "DS9"]),
    quality=[PointQ(point="D03.XCBR1.PosSt", value="CLOSED",
                    quality="GOOD", ts_source=..., age_ms=1200)],
    limits=["2 điểm không resolve trong snapshot hiện tại"],
)
```

`subject` là scope ref chứ không phải chuỗi tự do → evidence, URL, pane và tool
cùng một hệ danh từ.

### 3. Ranh giới: cái gì phải có evidence, cái gì không

| Phải có | Không cần |
|---|---|
| mọi facet (`state`, `measurement`, `alarm`, …) | `/api/health` |
| `/api/summary` | `/api/projects` (cấu hình cục bộ, không phải khẳng định về trạm) |
| `/api/energization` | `/api/diagram` (hình học, không phải khẳng định về trạm) |
| mọi tool của agent | |

Quy tắc một câu: **cái gì phát biểu về trạng thái trạm thì phải nói được nó biết
từ đâu.** Hình học và cấu hình thì không.

### 4. `limits` là bắt buộc, không phải trang trí

Trường hợp bắt buộc phải điền `limits`:

- `coverage.missing` không rỗng
- có `PointQ` nào `quality != GOOD`
- có điểm quá ngưỡng staleness
- facet trả dữ liệu từ **snapshot** chứ không phải live
- số đo có áp deadband (ADR-0012) — người đọc phải biết con số đã được lọc

Đây là hiện thực của I2: *không khẳng định trạng thái khi quality không GOOD*.

### 5. Frontend có đúng một component hiển thị evidence

`ui/EvidenceBlock.vue`, nhận `EvidenceRecord`, render giống nhau ở mọi nơi: panel,
tooltip của sơ đồ, tin nhắn của agent. Prose của LLM nằm **cạnh** khối này và
được nhãn là *diễn giải* (ADR-0004 §2) — không bao giờ nằm trong.

Mặc định thu gọn thành một dòng (*"7/7 điểm · quality GOOD · 1.2 s trước"*), bung
ra khi bấm. Evidence phải **có mặt** mà không **lấn át** — hệ quả tiêu cực mà
ADR-0004 đã lường trước.

## Phương án đã bác bỏ

### A. Làm evidence sau, khi module B (alarm) cần tới
Rẻ hôm nay. **Bác bỏ** — retrofit ~15 endpoint đã có người dùng, và những câu trả
lời phát ra trong thời gian đó vĩnh viễn không truy ngược được.

### B. Endpoint evidence riêng: `/api/evidence?for=<request-id>`
Payload gọn. **Bác bỏ**: hai lượt gọi cho một câu trả lời, và evidence trở thành
thứ **tuỳ chọn** — cái gì tuỳ chọn thì sẽ bị bỏ qua đúng lúc nó quan trọng nhất.
Evidence phải đi cùng dữ liệu trong cùng một tài liệu.

### C. Generic `Envelope[T]` cho mọi response
Đẹp về kiểu. **Bác bỏ** — Pydantic generic sinh tên schema xấu và lồng nhau trong
`openapi.json`, làm `schema.d.ts` khó dùng ở frontend.

### D. Chỉ gắn evidence cho tool của agent, không gắn cho endpoint UI
Hợp lý nếu tin rằng chỉ AI mới cần chứng minh. **Bác bỏ**: I5 nói agent dùng
**đúng** API mà UI dùng. Hai mức chi tiết khác nhau tức là hai đường khác nhau,
đó chính là thứ I5 cấm. Và người vận hành cũng cần biết con số trên màn hình cũ
bao nhiêu giây.

## Hệ quả

**Tích cực**

- Mọi khẳng định truy ngược được về `release` + `catalog_snapshot` + `model_version`.
- Phát hiện drift (I7) có chỗ tự nhiên để nổi lên: `coverage.missing`.
- Agent không thể bịa evidence vì nó không sinh evidence — nó chuyển tiếp.
- Test được không cần LLM.

**Tiêu cực**

- Mỗi facet phải thu thập coverage/quality → không facet nào được viết ẩu.
  ADR-0004 đã ghi nhận và chấp nhận điều này.
- Payload lớn hơn. Với `/api/summary` phạm vi trạm thì `quality[]` có thể dài;
  cần cho phép rút gọn (`quality_summary` + chi tiết theo yêu cầu) — **chưa
  quyết**, để tới lúc đo được kích thước thật, không đoán trước.
- Một `EvidenceRecord` cho mỗi lô sự kiện SSE là quá nặng. **Quyết định**: sự
  kiện `measurement`/`state` mang *tham chiếu* tới evidence (release + revision +
  quality theo điểm đã có sẵn trong payload), không mang bản ghi đầy đủ. Bản đầy
  đủ lấy khi người dùng bấm mở.

**Việc phải làm để ADR này không mục**

- `domain/evidence.py` là nơi duy nhất định nghĩa `EvidenceRecord`/`Coverage`/`PointQ`.
- Test kiến trúc: mọi response model nằm trong danh sách "phải có" mà thiếu field
  `evidence` → đỏ. Cùng kiểu cưỡng chế bằng máy mà `tools/check.py` đang áp.
