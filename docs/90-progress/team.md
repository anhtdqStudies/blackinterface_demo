# Ai sở hữu gì, ai làm gì

> **Cập nhật lần cuối**: 2026-08-10 · **Chỉ chủ dự án sửa file này.**
>
> Luật đằng sau bảng này: [ADR-0023](../10-architecture/adr/0023-team-delivery-architecture.md).
> Ranh giới lớp và invariant: [`AGENTS.md`](../../AGENTS.md).
> Cưỡng chế bằng máy: `CODEOWNERS` + `python tools/check.py`.

## 1. Bảng sở hữu

| | **Chủ dự án** | **Dev A** — tool & use case | **Dev B** — mô hình trạm |
|---|---|---|---|
| **Module** (ADR-0023 §1) | M3 BlackCore · M4 `control/` · M5 vỏ | M2 Domain API | M1 Mô hình trạm |
| **Backend** | `agent/core.py` `harness.py` `digest.py` `session.py` `provider.py` `config.py` | `agent/tools/**` · `api/routers/**` · `api/summary.py` + facet mới · `store/events.py` | `integration/**` · `domain/**` (trừ `scope.py`) · `diagram/**` · `store/projects.py` `releases.py` |
| **Frontend** | **toàn bộ `frontend/`** | không đụng | không đụng |
| **Chỉ chủ dự án** | `AGENTS.md` · `adr/**` · `tools/check.py` · `domain/scope.py` · `control/**` · `docs/90-progress/{status,team,questions,risks}.md` | | |
| **Thước đo** | một lượt hội thoại thật, đo bằng `tiktoken`; eval suite xanh | **độ phủ 30 use case** trong `document/@Station_UseCases 1.xlsx` | **số trạm dựng đúng N/N ngăn** |

**Số migration cấp trước** — Dev A: `006`, `008`, `010`… · Dev B: `007`, `009`, `011`…

**Ba file giao nhau, ba luật:**
- `backend/openapi.json` — conflict thì `git checkout --theirs` rồi chạy lại
  `uv run python ../tools/export_openapi.py`. **Không bao giờ merge tay.**
- `api/schemas.py`, `api/app.py` — **chỉ thêm vào cuối**, mỗi người một khối có
  comment tên luồng.

---

## 2. Hai bắt tay — đọc kỹ, đây là chỗ hay chặn nhau nhất

**Dev B → Dev A: fixture là hợp đồng.**
B nộp `backend/tests/fixtures/*.json` **trước** khi viết reader live. A viết
facet và tool trên `integration/dump.py` — không cần DataServer, không chờ B.

**Dev A → chủ dự án: schema trước, ruột sau.**
```
Dev A:  PR#1 "schema + endpoint trả DỮ LIỆU THẬT"  → merge
          ↓
Chủ dự án: git pull → npm run api:types → dựng pane   ┐ song song
Dev A:  PR#2..N hoàn thiện bên dưới, KHÔNG đổi schema  ┘
```
Endpoint trong PR#1 **không được mock**. Dựng giao diện trên hình dạng tưởng
tượng là dựng hai lần.

**Dev A → chủ dự án (lần hai): `register()`.**
A thêm tool bằng `agent/tools/registry.register()`, **không đụng `harness.py`**.
`register()` từ chối ngay lúc import nếu tool khai capability ghi mà thiếu
`requires_approval=True` — A không thể phá I1 kể cả khi muốn.

---

## 3. Việc cụ thể

### Chủ dự án

| # | Việc | Ghi chú |
|---|---|---|
| U1 | ✅ Commit lô 92 file · tách `status.md` · ADR-0023 · onboarding | xong 2026-08-10 |
| U2 | Remote nội bộ ATS + quy ước branch/PR | chưa có remote — rủi ro mất dữ liệu |
| U3 | **ADR-0024 hợp đồng tool `trace`** | **chặn A3** — viết trước khi A bắt đầu |
| U4 | `harness.py` · `digest.py` cho payload alarm | trần 2k token/tool, đo bằng `tiktoken` |
| U5 | Eval suite gọi 27B thật, opt-in env, **ngoài** `check.py` | |
| U6 | Frontend: `AlarmPane` · `TracePane` · banner drift · i18n | chờ schema của A2/B5 |
| U7 | **ADR-0025 khung duyệt** — mở lệnh đầu tiên trong `COMMANDS`, `draft_operation`, ai được `control.sign` | |
| U8 | Q7 (thang đo) · Q1 (struct alarm) · Q4b (quy ước LN) với ATS | [`questions.md`](questions.md) — không ai làm thay được |

### Dev A — tool & use case

Luật quan trọng nhất giao cho A, **I8**: *thêm một use case mà phải thêm một
tool cho agent → thiết kế đã sai.* Cách đúng là thêm một **bộ lọc** hoặc một
**scope**. Sau 6 tuần mà có 12 tool thì đó là tín hiệu đỏ, không phải thành tích.

| # | Việc | Xong là khi |
|---|---|---|
| A0 | **Tuần 1** — đọc `document/@Station_UseCases 1.xlsx` + `api/summary.py`; nộp bảng *use case nào đã phủ, use case nào thiếu gì*; dump simulator riêng → **trạm thứ 3** | onboarding có sản phẩm, không phải đọc suông |
| A1 | `store/events.py` + `migrations/006_events.sql` — SOE **chỉ append**. A định nghĩa `record()`, **B gọi** từ đường reader (một dòng, một PR chung) | test: ghi rồi không sửa/xoá được |
| A2 | **Facet `/api/alarms`** theo khuôn `api/summary.py` + `routers/summary.py` ⟵ *PR schema merge sớm nhất* | **bắt buộc mang `EvidenceRecord`** (ADR-0013); scope sai → 400/404, **không** âm thầm rơi về toàn trạm |
| A3 | **Tool `trace`** — món quan trọng nhất còn thiếu | theo ADR-0024. `metadata` mang evidence (**mô hình không thấy**), `content` là bản gọn |
| A4 | Facet + bộ lọc cho A-02/A-04 (tagging, alarm theo ngăn) | |

**A phải thuộc trước khi gõ**: I2 (quality khác GOOD → `UNDETERMINED`, cấm khẳng
định) · I3 (evidence do tool sinh, không phải LLM viết) · I6 (NodeId chỉ sống
trong `integration/`) · I8 (ở trên).

### Dev B — mô hình trạm

| # | Việc | Xong là khi |
|---|---|---|
| B0 | **Tuần 1** — `probe_dataserver.py --dump` lên simulator riêng → **trạm thứ 4**, chạy `build_station()`, nộp fixture + báo cáo lệch dialect | có con số *"N/N ngăn phân loại đúng"*. Đây là bằng chứng cho rủi ro **Cao** Q4 |
| B1 | **CI chạy `check.py` chặn merge** — hiện **không có `.github/`** | một ngày công, làm tuần 1, trước mọi thứ khác |
| B2 | Đọc alarm: `integration/opcua/alarms.py` — port decode từ `tools/probe_dataserver.py` (đã decode sạch 243/243) | **toàn bộ parse ExtensionObject nằm trong đúng một file** — Q1 chưa có spec chính thức, ATS đổi format thì sửa một chỗ |
| B3 | `domain/alarm.py` — model trung tính, severity ≥ 800, 5 category, `source_point` → `ScopeRef` | **NodeId không rò ra ngoài `integration/`** (I6) |
| B4 | Nhịp `alarm` trên SSE: thêm `Cadence.ALARM` vào `api/broadcast.py`, đặt **ngay sau `STATE`** trong `CADENCE_ORDER` | **không** áp `api/throttle.py` — mất một alarm khác hẳn mất một số đo |
| B5 | **Release pinning (I7)**: `migrations/007_releases.sql` + `store/releases.py` — snapshot có hash, pin `ModelVersion` + phiên bản template | NodeId không resolve = **drift, nổi lên như sự cố, cấm im lặng fallback** |
| B6 | **Template động (ADR-0015)**: template vào store, chọn theo **chữ ký** thay `infer_bay_type()`, trình soạn **đồ thị** (ADR-0003 đã bác canvas vẽ), cổng chứng minh | xem cảnh báo dưới |

> ⚠ **Cổng chứng minh của ADR-0015 không chạy được trên T220PHOCAO** — trạm đó
> không có `IsLive` ở đâu. Engineer sửa template ở một trạm không có dữ liệu
> trường thì ta **không có cách nào bác bỏ template sai**. B phải trả lời câu
> này **trước khi** code trình soạn: cổng chứng minh thay thế là gì?

---

## 4. Lịch 6 tuần tới demo nội bộ

| Tuần | Chủ dự án | Dev A | Dev B |
|---|---|---|---|
| **0** | U1 ✅ · U2 remote | — | — |
| **1** | U3 ADR-0024 | A0 use case + trạm #3 | **B1 CI** + B0 trạm #4 |
| **2** | U5 eval suite | A1 event store | B2 + B3 alarm |
| **3** | U8 Q7/Q1 với ATS · U6 `AlarmPane` | **A2 PR schema → merge** | B4 nhịp SSE · **B5 PR schema → merge** |
| **4** | U7 ADR-0025 · U6 banner drift | A3 `trace` | B5 xong · B6 bắt đầu |
| **5** | U6 `TracePane` · `ApprovalPane` | A3 xong · A4 | B6 |
| **6** | **tập demo** | vá lỗi demo | vá lỗi demo |

**Ba mốc cứng** — trượt cái nào thì báo ngay, đừng bù giờ:

1. **Cuối tuần 1**: hai fixture trạm mới + CI xanh. Trượt cái này là quy trình
   sai, không phải kỹ thuật.
2. **Cuối tuần 3**: `/api/alarms` và schema release đã merge → frontend hết bị chặn.
3. **Cuối tuần 5**: `trace` chạy đầu-cuối, có evidence, **trên trạm có dữ liệu
   trường thật**.

**Kịch bản demo** — viết ra từ bây giờ để mọi việc kéo về nó:

1. Nhập `opc.tcp://…` của một trạm chưa từng thấy → sơ đồ một sợi hiện ra, không vẽ tay.
2. Hỏi tiếng Việt `271 đang thế nào?` → trả lời kèm evidence có quality + tuổi dữ liệu.
3. Giả một sự cố → pane Bất thường + agent chỉ ra chuỗi nhân quả, mỗi con số truy
   được về một tool.
4. Xin thao tác → agent **soạn phiếu, dừng lại chờ người ký**.

Bước 4 chứng minh I1 bằng hình ảnh. Với người quyết định, nó nặng hơn cả ba
bước trên cộng lại.

---

## 5. Ba rủi ro của chính kế hoạch này

1. **Tuần 3 chủ dự án bị dồn ba việc** (Q7 với ATS + `AlarmPane` + review hai
   luồng). Tuần dễ vỡ nhất. Căng thì đẩy banner drift sang tuần 5 — nó không nằm
   trong kịch bản demo.
2. **`trace` chưa ai biết hình dạng đúng.** ADR-0024 gần như chắc chắn phải viết
   lại sau lần thử đầu. Chốt **một lượt chạy đầu-cuối xấu xí giữa tuần 4**, rồi
   mới đẹp — đừng để A code hai tuần rồi mới xem.
3. **Trạm demo có dữ liệu trường không?** Chưa chốt. T220PHOCAO hiện mọi `PosSt`
   trả `BadWaitingForInitialData` → sơ đồ đúng hình nhưng toàn xám, alarm và
   `trace` không có gì để nói. **Trả lời trong tuần 1.**
