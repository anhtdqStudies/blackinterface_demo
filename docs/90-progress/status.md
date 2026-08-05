# Trạng thái dự án

> **File này là bộ nhớ xuyên phiên.** Mọi AI agent đọc nó đầu phiên và cập nhật cuối phiên.
> Không cập nhật = phiên sau mất trí nhớ. Đây là chi phí lớn nhất của dự án này.

**Cập nhật lần cuối**: 2026-08-05 · phiên: energization solver + realtime (subscription + SSE)

---

## Đang ở đâu

**Giai đoạn: 1 — Module #1 xong. Khung dự án xong. Có git.**

Trỏ vào DataServer → ra sơ đồ một sợi 13 ngăn / 80 thiết bị, **không vẽ tay,
không map point**. Mục tiêu M1 đã chứng minh được trên `DEMO_SAS`.

Chạy thử:
```bash
cd backend  && uv sync
cd frontend && npm install && npm run build
cd backend  && uv run uvicorn blackinterface.api.app:app --port 8080
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
- ✅ `api/app.py` — Domain API, mọi endpoint không-GET chỉ ghi SQLite local,
     không bao giờ ghi OneATS (allowlist khoá trong `test_no_write_endpoint_exists`)
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

### Khung dự án (2026-08-04) ✅

Trước module #1 chỉ có một **lát cắt dọc**: chạy được từ OPC UA tới màn hình,
nhưng chưa có lưu trữ, cấu hình, log, xử lý lỗi, frontend thật, version control.
Phiên này bổ sung đúng những thứ **mọi module còn lại đều đụng vào**.

- ✅ **Git** — khởi tạo, commit đầu tiên gom toàn bộ hiện trạng (84 file)
- ✅ **ADR-0009** — frontend là Vite + Vue 3 + TS, thay phần frontend của ADR-0006
- ✅ `config.py` — mọi setting `BI_*` một chỗ; không nơi nào khác đọc `os.environ`
- ✅ `errors.py` + `api/errors.py` — bộ lỗi đóng, một hình dạng JSON duy nhất
- ✅ `logs.py` — structlog, người đọc được khi dev, JSON ở trạm
- ✅ `store/` — SQLite WAL, migration tiến-một-chiều, repository đầu tiên
- ✅ **Frontend thật** — routing, Pinia, component sơ đồ tách riêng, 3 view
- ✅ **Hợp đồng API cưỡng chế bằng máy**: FastAPI → `openapi.json` →
      `schema.d.ts`. Đổi field mà quên xuất → `check.py` đỏ
- ✅ Xoá `frontend/dev/index.html` (282 dòng) — không để tồn tại hai frontend
- ✅ `tools/check.py` giờ gác 7 mục, gồm cả frontend và hợp đồng API

**Chưa làm, cố ý**: `agent/`, đóng gói Inno Setup, `EvidenceRecord`.
Thiết kế chúng trước khi viết module tương ứng là đoán — đúng cái sai lầm mà
ba phát hiện của phiên trước (`get_children()` trùng, DBB/EBB, vị trí thanh cái)
đã chứng minh.

**Chưa kiểm chứng**: giao diện mới mới verify ở mức build + serve + typecheck,
**chưa xem bằng mắt trên trình duyệt**. Cần chạy `docs/40-testing/manual-test-01-topology.md`.

---

### Project + kết nối DataServer từ UI (2026-08-05) ✅

Luồng mới: mở Black Interface → **Project** → nhập tên + `opc.tcp://…` →
Kết nối → sơ đồ dựng từ nguồn đó. Kết nối thành công lưu **snapshot**
(StationObs JSON trong SQLite): mở lại project là vẽ ngay, offline được;
«Tải lại từ nguồn» mới đọc live. Khởi động lại process tự mở project gần nhất
từ snapshot (`StationStore.startup()`).

- ✅ Migration `002_projects.sql` — `projects` + `project_snapshots` (FK cascade)
- ✅ `store/projects.py` — `ProjectRepository`, store chỉ nói SQL, không biết domain
- ✅ `api/source.py` — `StationStore` theo project: `open_project` (snapshot) /
     `refresh_project` (live + thay snapshot) / fallback `BI_SOURCE` khi không có project
- ✅ `api/app.py` — `GET/POST /api/projects`, `/open`, `/refresh`, `DELETE`;
     lỗi kết nối trả trong body (`ok=false`), project giữ lại để sửa URL thử lại
- ✅ **Bỏ hardcode `SAS_PATH`**: `_find_station_root()` trong `discovery.py` —
     thử path DEMO trước (nhanh), không có thì BFS tìm node có con dạng `\d+kV`.
     Trạm mới trong DataServer giờ tìm được bất kể tên project trong cây
- ✅ Frontend: view `ProjectsView` (tạo/nhập URL/kết nối/mở/tải lại/xoá),
     nav «Project», lỗi `model_not_loaded` dẫn thẳng tới trang project
- ✅ 2 lỗi mới trong bộ đóng: `invalid_input` (400), `conflict` (409)
- ✅ 141 test offline (17 test mới: repository, luồng API project, reopen từ
     snapshot qua "restart", auto-dò root trên cây giả), check.py xanh cả 7 mục
- ⚠ Chưa kiểm chứng trên trạm thật thứ 2 (Q4): auto-dò root mới test bằng cây giả;
     `tools/probe_dataserver.py`/`verify_dataserver.py` vẫn hardcode path DEMO
- ⚠ Chưa có manual test cho luồng project (bổ sung vào `docs/40-testing/` khi chạy tay)

---

## Việc kế tiếp (theo thứ tự)

### 0. Xem lại giao diện mới bằng mắt — ✅ **ĐÃ CHẠY TAY 2026-08-05**
Người dùng xác nhận: **energization và realtime chạy đúng trên trình duyệt**,
"về cơ bản khá ổn". Đổi trạng thái ở FEP → màn hình đổi theo, không cần bấm gì.
Còn tồn đọng là **UI/UX**, người dùng sẽ nêu cụ thể ở phiên tiếp → gom vào việc
#5 (diagram engine), đừng tự đoán rồi sửa trước.

Kịch bản `docs/40-testing/manual-test-01-topology.md` vẫn là chuẩn để chạy lại
sau mỗi thay đổi hình học. Trọng tâm TC-03: **hai thanh cái phải tách bạch được
bằng mắt** (làn riêng + chấm nối), và cả trạm nằm trong **một hình**, 220kV lật
ngược ở trên.

**Còn thiếu so với bản Grid Designer** (bảng so sánh):
- [ ] Giá trị đo trên đầu mỗi ngăn (kV/kA/MW/MVar) — nguồn `MMXU1`, chưa vào model
- [ ] Hz/kV cạnh mỗi thanh cái — nguồn `Subs.BB*`, đã browse được, chưa vào model
- [x] ~~Ký hiệu MBA AT1 nối 220↔110~~ — **ĐÍNH CHÍNH 2026-08-05**: bằng chứng
      ghép ngăn CÓ trong DataServer (`BAY/Name` = "AT1 Incoming" ở cả D01 lẫn
      E07 + nhóm `/SAS/AT1` mang `YPTR`/`YLTC`). Đã vẽ, xem phiên 2026-08-05
- [x] ~~Tên ngăn dạng chữ ("Ben Cat", "Hoc Mon")~~ — **ĐÍNH CHÍNH 2026-08-05**:
      DataServer CÓ mang, ở `<bay>/BAY/Name`. Đã vào model và hiển thị

### 1. ~~Energization solver~~ ✅ **XONG 2026-08-05** — xem mục riêng bên dưới

### 2. ~~Realtime (subscription + SSE)~~ ✅ **XONG 2026-08-05** — xem mục riêng bên dưới

### 3. Event store + SOE ← **BẮT ĐẦU TỪ ĐÂY**
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
- [ ] **UI/UX người dùng sẽ nêu ở phiên tới** — chưa ghi được vì chưa nghe.
      Ghi nguyên văn góp ý vào đây khi nhận, đừng diễn giải lại.
- [ ] Sparse patch layer cho override của engineer
- [ ] Bố cục ngăn nối thanh cái (D17/E05) chưa chuẩn thẩm mỹ SLD
- [ ] Export SVG tĩnh

### 6. BlackCore + Frontend Nuxt
- [ ] Pydantic AI agent, tool registry (**không có write tool**)
- [ ] `LLMProvider` interface (OpenRouter dev → Ollama trạm)
- [ ] Nuxt: chat shell, bay-card review, evidence panel
      *(tham chiếu hành vi: `frontend/dev/index.html`)*

---

### Diagram v2 theo góp ý người dùng (2026-08-05) ✅

Người dùng đối chiếu với bản vẽ OneATS (`document/DEMO_SLD.pdf`) và nêu 3 điểm.

1. **MBA nối 220↔110 — đã vẽ, có bằng chứng.** Phát hiện mới đo được
   (2026-08-05, fixture + cấu trúc live):
   - `/SAS/220kV/D01/BAY/Name` = `/SAS/110kV/E07/BAY/Name` = `"AT1 Incoming"`
   - `/SAS/AT1` là nhóm ngang cấp điện áp, mang `YPTR` (MBA) + `YLTC` (OLTC)
   → luật ghép: nhóm MBA + id xuất hiện trong tên ngăn ở ≥2 cấp điện áp.
   Không đủ bằng chứng → `transformer_unpaired` warning, vẽ cuộn dây rời như cũ.
   - `domain`: `Transformer` + `pair_transformers()`; importers đọc nhóm AT*
   - `diagram`: ký hiệu 2 vòng tròn trong khe giữa 2 band, link chạy làn riêng
     cạnh ngăn, cắt ngang thanh cái **không chấm** = không nối (I3 giữ nguyên)
2. **Tên ngăn dạng chữ** — `BAY/Name` vào `Bay.name`: "Ben Cat", "Hoc Mon",
   "Lai Uyen" hiện dưới mã ngăn, đúng như bản vẽ Grid Designer.
3. **DS vs ES + giãn khoảng** — ES: thoi nhỏ hơn (6px vs 10px), gạch tiếp địa
   to và xa thân hơn; `SIDE_OFFSET` 54→68; bỏ chữ loại ngăn thừa ở caption.
4. **Thu phóng** — SVG thành camera: lăn chuột zoom quanh con trỏ, kéo để pan,
   nút «Vừa màn hình» (phím `f`), tab cấp điện áp = focus camera vào band.
   Toạ độ vẫn 100% từ backend; frontend chỉ đổi viewBox.

147 test offline (6 test mới khoá pairing + hình học link), check.py xanh cả 7 mục.
**Chưa xem bằng mắt trên trình duyệt** — việc #0 vẫn đứng.

### Diagram v2.1 — cuộn thứ ba 22kV của AT1 (2026-08-05) ✅

Người dùng hỏi: "còn 22kV thì sao, BB41 (suy ra) theo SLD phải nối vào AT1".
Đo lại fixture → tìm được **nguồn bằng chứng thứ hai** (BAY/Name của J01 rỗng
nên luật cũ không bắt được):

- **Số hiệu máy cắt theo quy ước EVN (TT 44/2014/TT-BCT)**: ngăn MBA có số
  `<mã cấp điện áp>3<số thứ tự MBA>` → AT1 sở hữu **231** (220kV), **131**
  (110kV), **431** (22kV). Trong fixture chỉ đúng 3 ngăn này khớp `^\d31$`;
  đường dây là x71/x72, liên lạc 112/212 — không đụng.
- `pair_transformers()`: match theo `BAY/Name` **hoặc** số máy cắt; id MBA
  không có đúng 1 chữ số cuối → không sinh luật số (thà không ghép còn hơn
  ghép sai). AT1 giờ ghép `(D01, E07, J01)` — 3 cấp điện áp.
- `layout` — qua 3 vòng góp ý cùng ngày, chốt ở **band 22kV nằm giữa**:
  `_band_order()`: cấp điện áp mà *mọi* ngăn vẽ được đều là cuộn ≥3 của MBA
  thì được nhấc lên ngay dưới band cao áp của MBA đó và **lật ngược**
  (terminal chĩa lên MBA, BB41 suy ra chìm xuống đáy band) — đúng bố cục dải
  giữa của tờ Grid Designer. Cấp 22kV có xuất tuyến thật thì giữ nguyên vị trí
  → khi đó link dùng tuyến dự phòng `_free_lane` (đường dọc nửa-bước-cột,
  giữa 2 cột luôn trống vì fitting rộng nhất vươn ±96 < ±105). Link ngắn:
  terminal → làn cạnh ngăn → hành lang `TX_DROP=52` → đáy vòng tròn 3
  (`TX_TAP=30`). Cắt ngang không chấm (I3).
- **Bug sửa kèm**: band không có thanh cái vòng (22kV không BB49) đặt terminal
  sai phía — `terminal_y` chỉ lấy `max(rail_y)` = thanh cái chính trên cùng,
  terminal chui lên sát busbar thay vì nằm quá dãy thiết bị. Giờ
  `max(spine_bottom, max(rail_y))`.
- Frontend: MBA có ≥3 ngăn → thêm vòng tròn thứ ba (tâm `y+14`, r16 — phải
  khớp `TX_TAP` backend), nhãn hạ xuống `y+52`.
- BB41 vẫn «(suy ra)» — đo được `/SAS/Subs` chỉ có BB11/12/19, BB21/22/29;
  nhãn phản ánh đúng nguồn, không sửa.

148 test (1 test mới khoá hình học link cuộn 3), check.py xanh cả 7 mục,
dist đã build lại. **Vẫn chưa xem bằng mắt trên trình duyệt** — việc #0.

---

### Energization solver (2026-08-05) ✅ — việc #1, và **câu trả lời cho Q3**

Hướng đã chốt với người dùng: **tự giải từ topology, rồi đối chiếu với `IsLive`
của OneATS** — không đọc lại kết quả của OneATS rồi gọi là của mình.

**Cách làm** (`domain/energization.py`, thuần, không I/O):

1. **Chia đảo (island)**: union-find, chỉ thiết bị `CLOSED` mới nối 2 node.
   `UNDETERMINED`/`INTERMEDIATE` **không** nối. Node `EARTH` bị loại khỏi phân
   hoạch — hai đoạn cùng tiếp địa không phải một dây dẫn.
2. **Gieo mầm CHỈ từ thanh cái** (`Subs.BB*.IsLive`, quality GOOD). **Cố ý
   không** dùng `<bay>.IsLive` làm mầm: OneATS suy ngăn *từ* thanh cái, dùng nó
   thì kết quả của ta chỉ là chép lại của họ, mất luôn giá trị đối chiếu.
3. **Lan truyền**: qua MBA thì mang *nguyên trạng thái* (đóng điện một cuộn là
   đóng điện cả máy — không có dao ở giữa); qua thiết bị không đọc được vị trí
   thì **chỉ mang nghi ngờ** → `UNKNOWN`, không bao giờ `LIVE`, càng không `DEAD`.
4. **Còn lại**: `DEAD` (mọi đường tới nguồn đều mở) — trừ khi đảo có thanh cái mà
   `IsLive` hỏng thì `UNKNOWN`. **Không bao giờ suy ra "hết điện"** từ thiếu dữ liệu.

Trạng thái: `LIVE` / `DEAD` / `EARTHED` / `UNKNOWN`, kèm `reason` (mã, không phải
câu chữ — UI tự dịch) và `via` (MBA/thiết bị nào mang phán quyết vào).

**Kết quả đối chiếu trên DEMO_SAS: 7/7 ngăn khớp `IsLive` của OneATS.**
Đây là bằng chứng mạnh nhất tới giờ rằng bộ template ngăn của ta đúng — hai
đường tính hoàn toàn độc lập ra cùng đáp số. Ca đắt nhất: **E02** mọi dao đều mở
trừ `-9`, nên đường dây có điện *vòng qua* ngăn từ thanh cái vòng BB19, trong khi
chính ngăn thì chết — đúng vế 2 của Lua `(C19L and 171-9C)`, và là lý do
`T1_LINE` v2 chuyển `XSWI9` sang phía đường dây.

Các ca khác đo được:
- **BB29** (`BadWaitingForInitialData`) → `UNKNOWN`, xám nét đứt. Đúng yêu cầu
  an toàn ở manual-test-01 ca 6.
- **D12** mọi dao mở → 2 đoạn `DEAD` riêng biệt, lý do `isolated`.
- **22kV** không có điểm đo nào → `LIVE` qua AT1 (`via=AT1`), và OneATS cũng nói
  `J01.IsLive=True` → khớp. Node cuộn hạ áp lấy theo luật template: đầu của dao
  `TRANSFORMER_DISCONNECTOR` không phải node nội bộ — với T2 là `n_tr`, với T5 là
  `BB41`. Tức **BB41 "suy ra" chính là cuộn 22kV của AT1**, không phải thanh cái ma.

**API/Frontend**: `GET /api/energization` trả `node_state` theo connectivity node;
`RailView`/`EdgeView`/`JunctionView` giờ mang `node_id` để frontend **ghép** màu.
Hình học và trạng thái điện tách rời — chính là thứ cho phép module realtime sau
này đẩy phán quyết mới mà không cần layout lại. Panel bên phải hiện số đảo theo
trạng thái + dòng "Khớp OneATS 7/7".

**Sửa kèm**: bỏ cạnh stub tiếp địa trong layout — nó trùng với ký hiệu tự vẽ và
luôn đi xuống, nên ở band 220kV lật ngược nó chĩa ngược hướng bãi tiếp địa.

168 test (20 test mới), check.py xanh cả 7 mục.

---

### Realtime — subscription + SSE (2026-08-05) ✅ — việc #2

Trước đó model là **ảnh chụp lúc dựng**: đổi dao ở FEP thì màn hình không đổi cho
tới khi bấm «Tải lại từ nguồn». Giờ màn hình bám theo trạm.

**Chia hai pha, đúng như bản chất bài toán:**

| Pha | Làm gì | Tần suất |
|---|---|---|
| Khám phá — `discovery.py` | duyệt cây → cấu trúc, template, graph, hình học | hiếm (mở/tải lại project) |
| Theo dõi — `monitor.py` | subscribe đúng các điểm đã biết địa chỉ | server **đẩy** khi có đổi |

**Danh sách theo dõi tự sinh từ chính observation** — `watch_points(obs)` gom mọi
`PointSample.source_ref` của `PosSt` và `IsLive` (DEMO_SAS: **97 điểm**). Không có
registry song song nào phải giữ đồng bộ; thêm một ngăn vào trạm là tự động được
theo dõi. Để làm được thế phải sửa `discovery.py`: trước đây nó ghi NodeId của
*logical node* vào `source_ref` thay vì của **biến** sinh ra giá trị (dump đã đúng
sẵn) — vừa là lỗi truy vết, vừa là thứ chặn subscription.

**Vá rồi dựng lại, không sửa tại chỗ.** `apply_samples` (thuần) thay đúng những
điểm có `source_ref` trong lô, rồi `build_station` chạy lại toàn bộ. Đo được:
`build_station` 0.71 ms + `solve_energization` 0.21 ms → ~1 ms mỗi lô. Trả 1 ms để
đổi lấy bảo đảm graph sau khi cập nhật **giống hệt** graph dựng mới — thứ mà sửa
tại chỗ không hứa được.

**Hai hành vi an toàn, có test:**
- **Mất kết nối ≠ tin tức về trạm.** Rớt link → `connected=false`, giá trị cũ giữ
  nguyên, header hiện chấm đỏ «Mất kết nối». Không bịa vị trí, cũng không xoá
  trắng sơ đồ (trạm rỗng trông như trạm cắt hết điện).
- **Gộp lô, không lấy mẫu.** Mọi thay đổi đều được áp; chỉ hoãn dựng lại 200 ms để
  một thao tác ngăn (máy cắt + vài dao trong vài trăm ms) vẽ lại **một lần**, ở
  trạng thái nhất quán, thay vì 5 lần qua các tổ hợp chưa từng tồn tại.
- Điểm server từ chối (snapshot cũ hơn model đang chạy) → đếm vào `rejected`, hiện
  «Trực tuyến (thiếu điểm)» màu vàng. Tươi chỗ này đứng chỗ kia còn tệ hơn cũ đều.

**API**: `GET /api/live` (poll) và `GET /api/stream` (SSE) trả **cùng một tài liệu
`LiveOut`** → frontend chỉ có một đường code áp dụng, không có nhánh riêng cho lần
đầu. `structure_revision` tách khỏi `revision`: đổi hình học mới phải tải lại bản
vẽ, đổi trạng thái thì chỉ tô lại.

**Đo thật trên DataServer (2026-08-05, DEMO_SAS v654):**
- duyệt cây 0.70 s → 97 điểm → subscribe **97/97 nhận, 0 từ chối**
- `/api/live`: `connected=true`, 8 đảo, **0 sai lệch** với OneATS (như bản fixture)
- SSE qua HTTP thật: `text/event-stream`, sự kiện đầu 12.7 KB, đủ trạng thái

Vòng thông báo được chứng minh bằng `tests/integration/test_monitor_roundtrip.py`:
dựng **server OPC UA cục bộ**, tự ghi giá trị, khẳng định lô về tới callback. Dùng
server riêng chính vì test này **ghi** — OneATS chỉ đọc (I1), không được chọc.

Cấu hình mới: `BI_REALTIME` (mặc định bật), `BI_OPCUA_PUBLISH_MS` (mặc định 500).

**197 test** (29 test mới), check.py xanh cả 7 mục.

---

## Nhật ký phiên gần nhất

### 2026-08-05 — Làm rõ nguồn dữ liệu + chốt thiết kế project/connect
- Người dùng đổi project trong DataServer nhưng sơ đồ không đổi → nguyên nhân:
  `BI_SOURCE=fixture` là mặc định, backend vẽ từ `sas_tree.json`, không đụng
  DataServer. Model chỉ dựng lại lúc khởi động hoặc `POST /api/reload`.
- Chốt thiết kế "tạo project → nhập URL DataServer → tải và vẽ":
  có lưu snapshot. Người dùng sau đó đổi thứ tự: **làm trước** energization.
- Điểm gãy đã nhận diện cho trạm mới: `SAS_PATH` hardcode trong `discovery.py`.

### 2026-08-05 — Hiện thực project + connect (xem mục Đã xong cùng tên)
- Toàn bộ luồng tạo/mở/tải lại/xoá project chạy được, offline test bằng cách
  patch `_observe_opcua` trả fixture — không cần DataServer.
- `.env` của người dùng (`BI_SOURCE=opcua`) giờ chỉ còn là fallback khi
  **chưa có** project nào active; có thể xoá sau khi tạo project đầu tiên.
- **Chưa xem giao diện mới bằng mắt** — cả trang Project lẫn sơ đồ (việc #0
  vẫn đứng nguyên). Người dùng nói sơ đồ "chưa ưng ý" → khi chạy tay, ghi cụ
  thể chỗ chưa ưng vào status để sửa trong việc #5 (diagram engine).

---

## Câu hỏi mở / chờ người khác

| # | Câu hỏi | Hỏi ai | Chặn việc gì |
|---|---|---|---|
| Q1 | **Định nghĩa struct chính thức của alarm ExtensionObject** (ns=2, TypeId 5803) | Team DataServer, ATS | Việc #3 — hiện đang reverse-engineer, field cuối còn lệch |
| Q2 | ATS đã có thư viện bay template chuẩn EVN chưa? | Nội bộ ATS | ~~Việc #1~~ — đã tự dựng 6 template. Vẫn hữu ích để đối chiếu ở trạm khác |
| Q3 | `IsLive` (thanh cái + ngăn) và `SAS_SIM.CheckLiveState`: OneATS tính thế nào? Vì sao `BB29`/`D12` trả `BadWaitingForInitialData`? | Team DataServer | **Đã tự trả lời phần chính (2026-08-05)**: OneATS suy `<bay>.IsLive` **từ** `Subs.BB*.IsLive` qua Lua `CheckLiveState`. Ta gieo mầm từ thanh cái, tự giải, đối chiếu → **7/7 khớp**. Còn hỏi: vì sao 2 điểm kia hỏng, và mầm của chính thanh cái từ đâu ra |
| Q4 | Có trạm thật thứ 2–3 để verify ADR-0002 + ADR-0008 không? | Nội bộ ATS | **Cao** — mã thanh cái theo cấp điện áp và quy ước LN mới đo trên 1 trạm |
| Q5 | Account read-only trên DataServer: xin ở đâu? | Team vận hành | Invariant I1 khi triển khai thật |
| Q6 | **Dao tiếp địa nối vào node nào?** `-75/-76` quanh `-7`, `-35/-38` quanh `-3`, `-94/-95` quanh `-9` | Team thiết kế / bản vẽ Grid Designer | Đang đọc từ ảnh chụp SLD, **chưa chứng minh**. Không ảnh hưởng energization, nhưng ảnh hưởng câu hỏi an toàn ("đoạn này đã tiếp địa chưa") ở module #2+ |

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
| Git chưa có remote — chỉ tồn tại trên máy này | Trung bình | Ổ cứng hỏng là mất. Đẩy lên GitHub/GitLab nội bộ ATS khi được phép |
| `.venv` trong OneDrive bị khoá lúc `uv sync` | Thấp | Đã set `link-mode = "copy"`; `check.py` tự retry 1 lần |

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

### 2026-08-04 — Sửa topology theo ground truth + layout kiểu Grid Designer
- **Phát hiện nguồn sự thật mới**: `document/DEMO_SAS-MODELExplorer.xlsx` chứa
  mã Lua `CheckLiveState` — chính công thức OneATS dùng để tính `IsLive`.
  Xem `AGENTS.md` §5.5.
- **Sửa lỗi thật trong template v1**: `XSWI9` (`-9`) ở ngăn đường dây và MBA
  nối vào **phía đường dây**, bỏ qua máy cắt — không phải phía thanh cái.
  Template cũ sẽ báo "đường dây mất điện" khi thực tế đang được cấp qua
  thanh cái vòng. T1, T2 → v2.
- Sửa T5 (22kV): `-3` nằm **trước** máy cắt, không phải sau.
- Xác nhận T3 (nối thanh cái) và T4 (nối vòng) đã đúng.

### 2026-08-04 — Sơ đồ đọc được: làn thanh cái + gộp cả trạm một hình
Người dùng đối chiếu với ảnh chụp HMI OneATS và chỉ ra hai chỗ sai.

- **Lỗi đọc hình, đã sửa**: `-1` và `-2` vẽ chung một đường thẳng đứng, nên
  đường đó chạm cả BB21 lẫn BB22 tại cùng một điểm — hình luôn trông như có
  đường dẫn xuyên qua cả hai thanh cái, **bất kể dao đang ở đâu**. Cũng vậy
  với đuôi đường dây cắt ngang BB29 đúng chỗ `-9` nối vào.
  Sửa: mỗi dao nối thanh cái có **làn x riêng** (`_assign_lanes`), mỗi chỗ nối
  thật có **chấm** (`JunctionView`), cắt ngang không chấm = không nối.
  Khoá bằng `test_no_conductor_runs_through_another_devices_busbar_connection`
  — test này duyệt mọi đoạn dây và mọi chấm nối trong cùng ngăn.
- **Gộp cả trạm vào một hình**: `layout_station()` + `GET /api/diagram`.
  220kV lật ngược (thanh cái chính xuống dưới, đường dây đi lên), 110kV và 22kV
  bình thường → hai nhóm thanh cái quay vào nhau, đúng cách bản vẽ Grid
  Designer của trạm đang trình bày. Tab cấp điện áp giờ chỉ để nhảy tới dải.
- Ngăn MBA kết thúc bằng ký hiệu cuộn dây; **cố ý không vẽ** đường nối D01↔E07
  vì DataServer không có bằng chứng ghép ngăn (I3).
- 124 test offline xanh; `tools/check.py` xanh cả 7 mục.
- `tests/unit/test_topology_ground_truth.py` — mỗi test trích đúng dòng Lua nó khoá
- Layout theo Grid Designer: 2 thanh cái chính ở trên, ngăn ở giữa,
  **thanh cái vòng ở phía đầu ra**, terminal dưới cùng
- Ký hiệu theo Grid Designer: máy cắt = ô vuông đặc, dao = hình thoi đặc
- **Đính chính bảng màu**: dây dẫn xanh dương = có điện (không phải đỏ).
  Thiết bị vẫn đỏ = đóng.

### 2026-08-04 — Khung dự án
- Init git, commit toàn bộ hiện trạng; branch `skeleton/project-structure`
- ADR-0009: bỏ Nuxt, dùng Vite + Vue 3 + TS
- Thêm `config.py` / `errors.py` / `logs.py` / `store/` (SQLite WAL + migration)
- Dựng frontend thật, xoá viewer tạm 282 dòng
- Nối hợp đồng API bằng máy: `openapi.json` → `schema.d.ts`, `check.py` gác
- `tools/check.py`: 7 mục, xanh toàn bộ. Backend 107 test + 2 live
