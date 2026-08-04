# Trạng thái dự án

> **File này là bộ nhớ xuyên phiên.** Mọi AI agent đọc nó đầu phiên và cập nhật cuối phiên.
> Không cập nhật = phiên sau mất trí nhớ. Đây là chi phí lớn nhất của dự án này.

**Cập nhật lần cuối**: 2026-08-04 · phiên: dựng module #1 (bay template + topology + viewer)

---

## Đang ở đâu

**Giai đoạn: 1 — Module #1 XONG. Có sản phẩm chạy được, nhìn thấy được.**

Trỏ vào DataServer → ra sơ đồ một sợi 13 ngăn / 80 thiết bị, **không vẽ tay,
không map point**. Mục tiêu M1 đã chứng minh được trên `DEMO_SAS`.

Chạy thử:
```bash
cd backend && uv run uvicorn blackinterface.api.app:app --port 8080
```
→ mở `http://127.0.0.1:8080` · kịch bản: `docs/40-testing/manual-test-01-topology.md`

---

## Đã xong

### Khảo sát (2026-08-04) — đo trực tiếp trên `DEMO_SAS` v654
- ✅ DataServer là **OPC UA client-server**, không phải PubSub Part 14
- ✅ Address space browse được: **17.965 node** dưới `/SAS`, NodeId ngữ nghĩa dạng chấm
- ✅ **Auto-bind 100%**: 80/80 thiết bị đóng cắt, 100% quality Good, 100% có timestamp
- ✅ **Suy loại ngăn 12/12 đúng** chỉ từ thành phần LN, không cần SLD
- ✅ Định danh EVN có sẵn trong `Name`/`SName` (`D03.XCBR1.Name = "271"`)
- ✅ Alarm dùng **interface riêng** `OAAlarm.GetActiveAlarm`, đã decode 243/243
- ✅ Subscription datachange hoạt động (200ms)
- ✅ Phát hiện lỗi trong extract SLD: sai số hiệu EVN, sót ngăn J01 22kV
- ✅ Phát hiện rủi ro bảo mật: endpoint None + Anonymous, `PosCtl` gọi được tự do
- 📄 `docs/30-integration/oneats-dataserver.md`

### Quyết định kiến trúc
- ✅ ADR-0001 Neutral Station Model là contract trung tâm
- ✅ ADR-0002 Topology suy từ DataServer, **SLD ra khỏi MVP**
- ✅ ADR-0003 Không làm canvas vẽ; template + view sinh tự động
- ✅ ADR-0004 Evidence là typed object do tool sinh
- ✅ ADR-0005 AI không nằm trên đường đi của tính đúng đắn
- ✅ ADR-0006 Stack triển khai local
- ✅ ADR-0007 Alarm dùng interface riêng

### Workspace
- ✅ `AGENTS.md` + adapter `CLAUDE.md`, `.cursor/rules/`
- ✅ Cấu trúc `docs/` (product / architecture / domain / integration / progress)
- ✅ Scaffold `backend/` theo 6 lớp, `tools/`, `frontend/` placeholder
- ✅ `tools/check.py`, `tools/probe_dataserver.py`, `tools/verify_dataserver.py`
- ✅ `uv sync` chạy được; `tools/check.py` **xanh toàn bộ**
  (layout · ranh giới lớp · read-only · docs dated · ruff · ruff format · mypy strict · pytest 11 passed)
- ✅ `tools/verify_dataserver.py` **xác nhận lại 100% sự thật đã đo** trên hệ live
- ✅ Đã kiểm chứng `check.py` thật sự bắt vi phạm: thêm file gọi `call_method("2:PosCtl")`
  → detect + exit 1; docstring ghi lệnh cấm thì không bị false positive

---

### Module #1 — Bay template + topology builder (2026-08-04) ✅

- ✅ ADR-0008 chốt schema template YAML
- ✅ 6 template: `domain/templates/T1..T6.yaml`
- ✅ `domain/bay_types.py` — suy loại ngăn, **13/13 đúng**
- ✅ `domain/topology.py` — áp template → graph, thuần, không I/O
- ✅ `integration/opcua/discovery.py` — browse live, **~1 s**
- ✅ `integration/dump.py` — đọc fixture, chạy offline
- ✅ `diagram/layout.py` — graph → toạ độ, deterministic
- ✅ `api/app.py` — Domain API, **chỉ có 1 endpoint không-GET là `/api/reload`**
- ✅ `frontend/dev/index.html` — viewer SVG 1 file, không cần Node
- ✅ **96 test offline + 2 test live**, tất cả xanh
- ✅ Fixture `backend/tests/fixtures/sas_tree.json` (617 node, có meta pin ModelVersion)
- 📄 `docs/40-testing/manual-test-01-topology.md`

**Kết quả đo được (fixture = live, đã đối chiếu):**

| Chỉ số | Giá trị |
|---|---|
| Ngăn dựng được | 13/13, **0 ngăn UNKNOWN** |
| Thiết bị đóng cắt đặt vào graph | **80/80** — khớp lần đo độc lập |
| Thiết bị bị bỏ sót (`slot_unmapped`) | **0** |
| Lỗi (severity ERROR) | **0** |
| Cảnh báo | 1 — thanh cái 22kV không có trong DataServer (đúng, đã báo lên UI) |
| Thời gian dựng model | 0.015 s (fixture) · ~1 s (live) |

**Phát hiện mới trong phiên này** (đã ghi vào `docs/20-domain/bay-templates.md`):
- Thanh cái thật nằm ở `/SAS/Subs/BB11..BB29`, có `IsLive`/`Hz`/`PPV*`.
  `DBB`/`EBB` **không phải** thanh cái mà là bảo vệ so lệch → đính chính bản nháp cũ.
- `IsLive` có sẵn ở **cả cấp thanh cái lẫn cấp ngăn**, cộng `SAS_SIM.CheckLiveState`
  → ảnh hưởng trực tiếp tới module #2 (câu hỏi Q3).
- `BB29.IsLive` và `D12.IsLive` trả `BadWaitingForInitialData` → có sẵn ca thật
  để kiểm chứng invariant I2.

---

## Việc kế tiếp (theo thứ tự)

### 1. Energization solver ← **BẮT ĐẦU TỪ ĐÂY**
Đây là thứ biến sơ đồ hiện tại thành sơ đồ *có nghĩa*: tô màu theo **mang điện**,
không phải theo từng dao.
- [ ] ⚠ **Làm trước tiên**: đối chiếu `Subs.BB*.IsLive`, `<bay>.IsLive` và
      `SAS_SIM.CheckLiveState` — OneATS đã tính sẵn. Đừng tính lại mù (Q3)
- [ ] Lan truyền từ nguồn qua graph + `PosSt`, dùng connectivity node đã có
- [ ] Dbpos 0/3 → `UNDETERMINED` lan truyền ra cả vùng, không đoán
- [ ] Đối chiếu kết quả tự tính vs `IsLive` của OneATS → lệch thì báo, đừng giấu
- [ ] Frontend: tô rail + nhánh theo vùng mang điện

### 2. Realtime (subscription + SSE)
Hiện tại giá trị là **snapshot lúc dựng model**. Cần biến thành sống.
- [ ] Một subscription phía server → fan-out SSE cho N client (bẫy đã biết)
- [ ] Ngưỡng staleness → đánh dấu `STALE` kèm tuổi dữ liệu (I2)
- [ ] Frontend: cập nhật tại chỗ, không vẽ lại toàn bộ

### 3. Event store + SOE
Không có cái này thì mục tiêu M2 không tồn tại.
- [ ] Schema SQLite cho event (dedupe theo `event_id`, retention, ack state)
- [ ] Poll/subscribe `GetActiveAlarm` → ghi store
- [ ] Query SOE theo cửa sổ thời gian, độ phân giải ms

### 4. Evidence + snapshot/release
- [ ] `EvidenceRecord` + `Coverage` + `PointQ` (ADR-0004)
- [ ] Catalog snapshot + release hash + pin `ModelVersion` (I7)
      *(fixture đã có meta `ModelName`/`ModelVersion` — dùng làm nền)*
- [ ] Phát hiện drift: NodeId không resolve được → nổi lên UI, cấm im lặng

### 5. Diagram engine — hoàn thiện
- [ ] Sparse patch layer cho override của engineer
- [ ] Bố cục ngăn nối thanh cái (D17/E05) chưa chuẩn thẩm mỹ SLD
- [ ] Export SVG tĩnh

### 6. BlackCore + Frontend Nuxt
- [ ] Pydantic AI agent, tool registry (**không có write tool**)
- [ ] `LLMProvider` interface (OpenRouter dev → Ollama trạm)
- [ ] Nuxt: chat shell, bay-card review, evidence panel
      *(tham chiếu hành vi: `frontend/dev/index.html`)*

---

## Câu hỏi mở / chờ người khác

| # | Câu hỏi | Hỏi ai | Chặn việc gì |
|---|---|---|---|
| Q1 | **Định nghĩa struct chính thức của alarm ExtensionObject** (ns=2, TypeId 5803) | Team DataServer, ATS | Việc #3 — hiện đang reverse-engineer, field cuối còn lệch |
| Q2 | ATS đã có thư viện bay template chuẩn EVN chưa? | Nội bộ ATS | ~~Việc #1~~ — đã tự dựng 6 template. Vẫn hữu ích để đối chiếu ở trạm khác |
| Q3 | `IsLive` (thanh cái + ngăn) và `SAS_SIM.CheckLiveState`: OneATS tính thế nào? Vì sao `BB29`/`D12` trả `BadWaitingForInitialData`? | Team DataServer | **Việc kế tiếp #1** |
| Q4 | Có trạm thật thứ 2–3 để verify ADR-0002 + ADR-0008 không? | Nội bộ ATS | **Cao** — mã thanh cái theo cấp điện áp và quy ước LN mới đo trên 1 trạm |
| Q5 | Account read-only trên DataServer: xin ở đâu? | Team vận hành | Invariant I1 khi triển khai thật |

---

## Nợ kỹ thuật / rủi ro đã biết

| Rủi ro | Mức | Ghi chú |
|---|---|---|
| Struct alarm reverse-engineered, chưa có spec chính thức | **Cao** | Q1. ATS đổi format là vỡ |
| Kết luận "không cần SLD" mới đo trên 1 trạm (`DEMO_SAS`) | **Cao** | Q4. Trạm khác có thể lệch quy ước đặt tên |
| Mã thanh cái theo cấp điện áp: 22kV/35kV/500kV là **GIẢ ĐỊNH** | Trung bình | `topology.py: VOLTAGE_BUSBAR_CODE`. Sai thì sinh placeholder + cảnh báo, không im lặng |
| `tools/` chạy bằng python hệ thống, backend chạy trong venv → lệch bản asyncua | Thấp | Đã xử lý `StatusCode` vs `StatusCode_`. Chạy tools qua `uv run` nếu cần chắc |
| Điểm Modbus/DNP không theo quy ước 61850 → không auto-bind được | Trung bình | Trạm pha trộn sẽ có tỷ lệ thủ công cao hơn |
| Endpoint DataServer không bảo mật (None + Anonymous) | **Cao** | Tồn tại độc lập với Black Interface; phải báo team vận hành |
| CPU-only tại trạm → LLM chậm | Trung bình | ADR-0006. Giảm nhẹ: câu trả lời ngắn + structured view |
| SQLite ghi đồng thời (event store + reader) | Thấp | Bật WAL, tách connection đọc/ghi |
| Repo trong OneDrive, **chưa init git** | Trung bình | Người dùng chọn chưa init. Chưa có version control = mất việc là mất thật |

---

## Nhật ký phiên

### 2026-08-04 — Khảo sát OneATS + dựng workspace
- Đọc manual OneATS (8 chương), phân tích `document/SLD_serviceOut/`
- Kết nối DataServer live, dump address space, đo auto-bind + bay-type inference
- Decode struct alarm
- Chốt 7 ADR, dựng workspace + tài liệu + công cụ kiểm tra
- **Chuyển hướng lớn**: SLD ra khỏi MVP (ADR-0002); không làm canvas vẽ (ADR-0003);
  alarm không dùng OPC UA A&C (ADR-0007)

### 2026-08-04 — Module #1: bay template + topology + viewer
- Chốt ADR-0008 (schema template YAML), hiện thực 6 template
- Dựng chuỗi: dump/live → `StationObs` → template → `StationGraph` → `DiagramView` → SVG
- Viewer 1 file HTML để nhìn kết quả ngay, không cần Node
- 96 test offline + 2 test live; `tools/check.py` xanh toàn bộ
- Đính chính: `DBB`/`EBB` là bảo vệ so lệch, không phải thanh cái
- Bắt được 1 lỗi thật lúc test live: `get_children()` của OneATS trả trùng
  → 320 thiết bị thay vì 80. Đã dedupe theo NodeId + ghi vào bảng bẫy
