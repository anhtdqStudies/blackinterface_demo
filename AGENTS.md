# AGENTS.md — Black Interface

> **Đây là nguồn sự thật duy nhất cho mọi AI agent làm việc trên repo này**
> (Claude Code, Codex/GPT, Cursor, Copilot…).
> `CLAUDE.md` và `.cursor/rules/` chỉ là adapter mỏng trỏ về file này.
> Đọc hết file này trước khi sửa bất cứ thứ gì. Mất ~3 phút.

---

## 0. Đọc gì trước (theo thứ tự)

| # | File | Khi nào cần |
|---|------|-------------|
| 1 | `AGENTS.md` (file này) | **Luôn luôn** |
| 2 | `docs/90-progress/status.md` | **Luôn luôn** — biết đang ở đâu, việc kế tiếp là gì |
| 3 | `docs/30-integration/oneats-dataserver.md` | Khi động tới OPC UA / DataServer / alarm |
| 4 | `docs/20-domain/glossary.md` | Khi gặp thuật ngữ lạ (61850, CIM, EVN) |
| 5 | `docs/10-architecture/overview.md` | Khi thêm module hoặc đổi ranh giới lớp |
| 6 | `docs/10-architecture/adr/` | Khi định làm khác một quyết định đã chốt |
| 7 | `docs/40-testing/` | Khi muốn tự tay chạy thử một module đã xong |
| 8 | `document/@Station_UseCases 1.xlsx` | Khi làm bất kỳ module use case nào (A–F). Sheet `Use Case` = khung; `A01`/`A02`/`A04` = chi tiết, có **đích danh point** |

Không đọc `document/UserManual/*.pdf` trừ khi thật sự cần — đã chắt lọc vào `docs/`.

⚠ File use case là **ví dụ về loại việc người dùng muốn giải quyết**, không phải
khuôn mẫu để code từng dòng — xem I8. Dùng nó làm **bộ đề kiểm tra độ phủ**.

---

## 1. Sản phẩm này là gì

**Black Interface** = lớp vận hành AI-first thay thế HMI tĩnh của OneATS, cài **local** trên
server tại trạm điện.

Hai mục tiêu, đúng hai cái:

1. **Rút ngắn thời gian dựng project** — trỏ vào OneATS DataServer là ra HMI chạy được,
   không vẽ tay, không map point thủ công.
2. **Giám sát realtime + phân tích sự cố** — khi có vấn đề thì chỉ ra nguyên nhân cụ thể
   và hướng xử lý, kèm bằng chứng.

Chi tiết: `docs/00-product/vision.md`

---

## 2. Tám luật bất biến (INVARIANTS)

Vi phạm bất kỳ luật nào dưới đây = sai, kể cả khi code chạy được.
Nếu bạn nghĩ cần phá luật, **dừng lại và hỏi người dùng**, đừng tự quyết.

### I1. Một đường ghi duy nhất, qua `control/`. Cưỡng chế bằng cấu trúc, không bằng prompt.
*(Phát biểu lại 2026-08-05 theo ADR-0011 — module C nằm trong MVP nhưng làm sau cùng.)*

- **Không module nào ngoài `control/` được chạm bề mặt ghi của OneATS.**
- **`control/registry.py` RỖNG** cho tới khi có ADR riêng mở từng lệnh một.
  Tới lúc này, trên thực tế hệ vẫn read-only — chỉ khác là chỗ để mở đã có sẵn.
- **Agent KHÔNG BAO GIỜ có tool ghi.** Vĩnh viễn, kể cả sau khi module C mở.
  Agent được *chuẩn bị* thao tác (kiểm tra interlock, dựng checklist, đọc trình
  tự, giải thích hậu quả — đều là đọc). Nút bấm ở UI, người bấm, có xác nhận.
  **Agent soạn phiếu, người ký.**
- `agent/` **không được import** `control/`.
- Client OPC UA phải dùng account read-only, không Anonymous.
- Bề mặt ghi: `*.PosCtl`, `SysCommon.Force/Unforce`, `OADataModel.Restart`,
  `OATagging.Set*`, `OAAlarm.Ack*/Enable/Disable`.
  Danh sách đầy đủ: `docs/30-integration/oneats-dataserver.md` §Bề mặt ghi.

### I2. Không khẳng định trạng thái khi quality không GOOD.
Mọi phát biểu về trạng thái thiết bị **bắt buộc** kèm `(value, quality, timestamp/age)`.
- `quality != GOOD` → trả `state = UNDETERMINED`, agent **không được** nói "đang đóng/mở".
- Quá ngưỡng staleness → đánh dấu `STALE` và hiện tuổi dữ liệu.
- Đây là luật an toàn, không phải luật thẩm mỹ.

### I3. Evidence là typed object do tool sinh, không phải văn bản LLM viết.
LLM **không được** tự soạn phần evidence. Tool trả `(payload, EvidenceRecord)`.
Prose của LLM nằm cạnh block evidence và được label rõ là *diễn giải*.

### I4. LLM không nằm trên đường đi của tính đúng đắn.
- Topology, layout, energization, chuỗi nhân quả sự cố → **backend deterministic**.
- LLM chỉ: hiểu ý định, chọn tool, chọn view, diễn đạt kết quả.
- Hệ phải test được end-to-end **không cần LLM**. UI phải dùng được khi LLM chết.

### I5. Frontend gọi thẳng Domain API. BlackCore không phải proxy.
```
Web ──┬──────────────────> Domain API      (deterministic: view, data, SSE)
      └──> BlackCore ────> Domain API      (chỉ cho lượt hội thoại NL)
```
BlackCore dùng **đúng** API mà UI dùng — không có đường riêng, không có quyền cao hơn.

### I6. Không lớp nào chạm raw NodeId ngoài Integration Layer.
UI / AI / Domain API chỉ thấy Neutral Station Model. NodeId, CIM mRID, path 61850
chỉ tồn tại trong `integration/` và trong `source_refs[]` của model.
**NodeId không bao giờ là primary key.**

### I7. Release là immutable và pin theo snapshot.
Point catalog phải freeze thành snapshot có hash, pin vào release, pin kèm
`OADataModel.ModelVersion`. Runtime chỉ lấy *giá trị* live. NodeId không resolve được
= **drift**, phải nổi lên UI như sự cố hệ thống, cấm im lặng fallback.

### I8. Địa chỉ hoá bằng `scope × facet`, không bằng use case. (ADR-0010)
30 use case trong `document/@Station_UseCases 1.xlsx` là **ví dụ về loại việc**,
không phải khuôn mẫu để code từng dòng. A-01/A-02/A-03 là *cùng một hàm*, khác
mỗi phạm vi.

- **Scope** (`station`, `bay:D03`, `device:D03.XCBR1`, `point:…`) là một khái
  niệm dùng chung cho: URL frontend · tham số tool của agent · khoá pane ·
  `subject` của evidence. `domain/scope.py` là **nơi duy nhất** parse/format —
  không nơi nào ghép chuỗi `f"bay:{id}"` bằng tay.
- **LLM không bao giờ tự sinh scope ref.** Người dùng nói "271", resolver
  deterministic đổi thành `device:D03.XCBR1`. Không phân giải được thì báo không
  tìm thấy — **cấm đoán**.
- **Thước đo kiểm tra được**: thêm use case mà phải thêm tool cho agent →
  thiết kế đã sai. Thêm đúng cách là thêm một bộ lọc hoặc một scope.

---

## 3. Tech stack (đã chốt)

| Lớp | Công nghệ | Ghi chú |
|---|---|---|
| Backend | **Python 3.12** (không phải 3.13) | ecosystem wheel còn lệch trên 3.13 |
| Dependency | **uv** | lockfile + quản lý bản Python + export offline wheels |
| API | **FastAPI** + SSE | |
| OPC UA | **asyncua** | client-server, KHÔNG phải PubSub |
| Store | **SQLite** | config, release, topology, event store. **Không dùng MongoDB** |
| Agent | **`LLMProvider` tự viết** (ADR-0019) | một phương thức, không SDK mô hình. Pydantic AI đã bác — xem ADR-0019 phương án A, kèm đường lui |
| LLM | OpenRouter (dev) → Ollama (trạm) | cùng một hiện thực: endpoint OpenAI-compatible qua `httpx`. **Mặc định `BI_LLM=off`** — không mô hình, câu trả lời vẫn đúng và vẫn có bằng chứng (I4) |
| Frontend | **Vite + Vue 3 + TypeScript** (ADR-0009) | build tĩnh → FastAPI serve → 1 process, không cần Node runtime |
| UI kit | **shadcn-vue** + Tailwind v4 + reka-ui (ADR-0014) | cài theo đường **Vite**, KHÔNG dùng Nuxt. MCP: `npx shadcn-vue@latest mcp init --client claude` |
| i18n | **vue-i18n** — `vi` mặc định + `en` | ngôn ngữ UI ≠ ngôn ngữ câu trả lời của LLM |
| Type API | **sinh từ OpenAPI** (`openapi-typescript`) | backend đổi field → frontend lỗi biên dịch |
| Đóng gói | embedded CPython + Inno Setup → Windows Service | |

**Không được thêm** vào stack mà không có ADR: MongoDB, Postgres, Docker, Redis,
Node runtime ở production, message broker, **Nuxt** (ADR-0009 đã bác, ADR-0014 xác nhận lại).

---

## 4. Cấu trúc thư mục

```
backend/src/blackinterface/
  config.py      # MỌI setting BI_* ở đây. Không nơi nào khác đọc os.environ
  errors.py      # bộ lỗi đóng; mọi lỗi API là một trong số này
  logs.py        # structlog; gọi configure() một lần lúc khởi động
  domain/        # L4 Neutral Station Model — contract hợp nhất, immutable
    models.py        Bay/Device/Busbar/ConnectivityNode/PointSample/ValidationIssue
    observation.py   StationObs — đầu vào trung tính cho mọi importer; nền của
                     realtime, TÁCH LÀM HAI HỌ: state_points/apply_state_samples
                     (rời rạc, dựng lại graph) và measurement_points/
                     apply_measurement_samples (tương tự, chỉ dán nhãn). Hai
                     danh sách rời nhau — ADR-0012 luật 1 (thuần)
    bay_types.py     suy loại ngăn từ thành phần LN
    templates.py     loader + registry cho templates/*.yaml
    templates/       6 bay template (ADR-0008)
    topology.py      observation + template -> StationGraph  (thuần, không I/O)
    energization.py  StationGraph -> vùng mang điện; gieo mầm từ thanh cái,
                     đối chiếu với <bay>.IsLive của OneATS (thuần, không I/O)
    scope.py         ScopeRef — NƠI DUY NHẤT parse/format scope ref (I8)
    measurement.py   danh mục measurand + Reading + deadband theo TỪNG đại lượng.
                     Không in đơn vị nào chưa đo được thang (thuần)
    evidence.py      EvidenceRecord/Coverage/PointQ/Limit + EvidenceBuilder;
                     builder tự suy ra `limits`, facet chỉ khai báo sự kiện
  integration/   # L5 importers + adapters — CHỈ ĐÂY được biết NodeId
    dump.py          đọc dump JSON -> StationObs (offline, dùng cho test/demo)
    opcua/discovery.py  browse DataServer live -> StationObs (hiếm: cấu trúc)
    opcua/monitor.py    subscription có giám sát -> lô PointSample (liên tục)
    opcua/values.py     DataValue -> PointSample, dùng chung cho cả hai trên
  diagram/       # L6 graph → layout → ViewModel → SVG
    layout.py        StationGraph -> DiagramView (toạ độ, deterministic)
  api/           # L3 Typed Domain API (FastAPI, HTTP/SSE)
    app.py           CHỈ lắp ráp: lifespan, middleware, include_router, static.
                     Thứ tự include_router = thứ tự path trong openapi.json
    deps.py          state của process (settings/db/store); router lấy qua
                     get_store() — test đổi bằng deps.use()
    schemas.py       MỌI response model. Tên = tên schema trong openapi.json
    mappers.py       domain -> schema, hàm thuần, không đọc state toàn cục
    routers/         health · projects · station · live · summary · diagram · agent
    summary.py       facet `summary`: một scope -> câu trả lời + EvidenceRecord.
                     Khuôn mẫu cho mọi facet sau
    source.py        StationStore: model nào đang hiện hành và đổi lúc nào
    reader.py        SourceReader: đọc nguồn -> StationObs (import lazy asyncua)
    watch.py         MonitorSupervisor: vòng đời subscription, sync() idempotent
    broadcast.py     Cadence(state|measurement|link) + revision mỗi nhịp +
                     Listener giữ MỘT chỗ CHO MỖI nhịp (ADR-0012)
    throttle.py      giảm nhịp `measurement`, có sườn xuống nên số đo cuối của
                     một chùm không bao giờ mất
    errors.py        exception -> JSON {"error": {code, message, detail}}
  agent/         # L2 BlackCore (ADR-0019) — lập kế hoạch → đọc → diễn đạt
    core.py          một lượt hội thoại; MỘT generator phục vụ cả hai endpoint
    plan.py          chọn scope nào để đọc. DETERMINISTIC — đây là chỗ I4 đứng
    resolve.py       "271" -> device:D03.XCBR1; nhiều kết quả thì HỎI LẠI, cấm đoán
    brief.py         cái tool tìm được, nói hai lần: `facts` cho mô hình, khoá
                     i18n + tham số cho người (backend không viết câu)
    provider.py      LLMProvider: `off` (mặc định) | endpoint OpenAI-compatible
    session.py       lịch sử hội thoại; protocol + bản trong-tiến-trình. agent/
                     KHÔNG import được store/, bản SQLite sẽ do api/ tiêm vào
    tools/           registry CHỈ ĐỌC, mỗi tool trả (payload, EvidenceRecord).
                     Capability của mọi tool phải nằm trong READ_ONLY — check.py
                     mục 3 đọc bằng ast, không tin `register()` lúc chạy
  control/       # đường ghi DUY NHẤT (I1, ADR-0011) — hình dạng đã có, cửa đóng
    registry.py      lệnh được phép — `COMMANDS = {}`, check.py parse bằng ast
    guard.py         tiền điều kiện; đồng thời là hiện thực C-01 (đọc thuần).
                     Mặc định LÀ TỪ CHỐI: không đánh giá được ≠ đã thông qua
    audit.py         AuditEntry + AuditSink (chỉ append, không sửa/xoá)
  store/         # SQLite (ADR-0006)
    db.py            connection, WAL, migration tiến-một-chiều
    meta.py          repository app_meta — mẫu cho các repository sau
    projects.py      repository projects + snapshot (StationObs JSON, opaque)
    migrations/      NNN_name.sql, đánh số liên tục từ 001
backend/openapi.json  # HỢP ĐỒNG API. Sinh ra, được check.py gác
frontend/        # L1 — Vite + Vue 3 + TS (ADR-0009) + shadcn-vue (ADR-0014)
  components.json      # cấu hình shadcn-vue CLI (`npx shadcn-vue@latest add …`)
  src/styles.css       # Tailwind v4 cấu hình BẰNG CSS (@theme) — không có file JS
  src/api/schema.d.ts  # SINH từ openapi.json. ĐỪNG SỬA TAY
  src/scope.ts         # parse/format ScopeRef, khớp domain/scope.py (I8).
                       # check.py so hai bộ ScopeKind, lệch là đỏ
  src/router.ts        # `/ops/:scope` là địa chỉ chính; scope sai -> redirect
  src/i18n/            # vi (mặc định) + en. Nhãn của MỌI code từ backend ở đây
  src/lib/utils.ts     # cn() cho shadcn-vue
  src/ui/              # design system; hai bảng màu tách bạch (ADR-0014 §2)
  src/stores/          # tách theo VÒNG ĐỜI: structure · live · measurements ·
                       # workspace · summary · projects.
                       # stream.ts giữ EventSource DUY NHẤT và phân nhánh theo
                       # event.type — store giữ dữ liệu, không giữ socket
tools/           # script vận hành/kiểm chứng — chạy được độc lập
docs/            # xem §0
document/        # tài liệu gốc ATS (manual PDF, output service SLD) — CHỈ ĐỌC
```

### 4.1 Hợp đồng giữa backend và frontend là máy giữ, không phải người nhớ

```
FastAPI app  ──export_openapi.py──>  backend/openapi.json
                                          │ openapi-typescript
                                          ▼
                                  frontend/src/api/schema.d.ts
```

Đổi endpoint mà quên xuất lại → `tools/check.py` đỏ.
Frontend dùng sai tên field → lỗi biên dịch, không phải `undefined` lúc chạy.

Không có frontend dự phòng: chưa `npm run build` thì API chạy nhưng không có
giao diện. Cố ý — một frontend cũ còn sót lại nguy hiểm hơn là không có gì.

Chiều phụ thuộc **một chiều**: `api → domain ← integration`, `agent → api`,
`diagram → domain`. `domain` không import bất cứ lớp nào khác.

---

## 5. Quy tắc làm việc xuyên phiên

### 5.1 Mở đầu mỗi phiên
1. Đọc `docs/90-progress/status.md`
2. Chạy `python tools/check.py` — biết repo có đang sạch không
3. Nếu định động tới OPC UA: chạy `python tools/verify_dataserver.py`
   để xác nhận các "sự thật đã đo" còn đúng

### 5.2 Kết thúc mỗi phiên (BẮT BUỘC)
Cập nhật `docs/90-progress/status.md`:
- việc đã xong (kèm đường dẫn file)
- việc đang dở + đang vướng ở đâu
- việc kế tiếp
Không cập nhật = phiên sau mất trí nhớ. Đây là chi phí lớn nhất của dự án này.

### 5.3 Khi ra quyết định kiến trúc
Viết ADR mới trong `docs/10-architecture/adr/NNNN-<slug>.md` theo mẫu có sẵn.
ADR là **immutable** — muốn đổi thì viết ADR mới với `Supersedes: NNNN`, đừng sửa cái cũ.

### 5.4 Phân biệt SỰ THẬT ĐÃ ĐO và GIẢ ĐỊNH
Đây là quy tắc riêng và quan trọng của dự án này.

- Số liệu về OneATS phải ghi kèm **ngày đo** + **cách đo lại**.
- Chưa đo thì viết rõ `GIẢ ĐỊNH — chưa xác minh`.
- **Cấm** trích số liệu từ trí nhớ hoặc từ manual PDF như thể đã đo.
  Manual có chỗ sai/lệch so với hệ chạy thật (đã gặp: manual mô tả alarm theo
  OPC UA A&C, thực tế OneATS dùng interface riêng).

### 5.5 Nguồn sự thật về TOPOLOGY: script Lua trong model export

`document/DEMO_SAS-MODELExplorer.xlsx` → dòng `CheckLiveState`, cột `R` chứa
**mã Lua tính IsLive của chính OneATS**. Đây là bằng chứng độc lập duy nhất về
đấu nối thật — DataServer không có connectivity, extract SLD thì sai.

```lua
-- E01L = (((C11L and 171-1C) or (C12L and 171-2C)) and 171C and 171-7C)
--        or (C19L and 171-9C)
```

Vế thứ hai không có máy cắt: **`-9` cấp điện thẳng cho đường dây, bỏ qua cả máy
cắt lẫn `-7`.** Đây là thứ đã bắt được lỗi thật trong template v1.

Đọc lại bằng:
```bash
python -c "import zipfile,xml.etree.ElementTree as ET; ..."   # xem git log commit template v2
```
Test khoá lại: `backend/tests/unit/test_topology_ground_truth.py`.

**Lua KHÔNG nói gì về dao tiếp địa** (tiếp địa đóng khi có điện là sự cố, sim
không mô hình hoá). Vị trí tiếp địa hiện đọc từ bản vẽ Grid Designer → câu hỏi Q6.

### 5.6 Không tin dữ liệu extract SLD
`document/SLD_serviceOut/` là output computer-vision, **có lỗi đã xác nhận**:
số hiệu EVN sai (D03 ghi 179, thực tế 271), sót nguyên ngăn J01 22kV,
20–26% thiếu tên, 36–40% thiếu connections.
DataServer là chân lý. SLD chỉ dùng để đối chiếu.

---

## 6. Công cụ kiểm tra

```bash
# --- một lệnh gác tất cả (chạy từ gốc repo) ---
python tools/check.py

# --- backend ---
cd backend
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run pytest                # 288 test, không cần DataServer
uv run pytest -m live        # cần DataServer đang chạy
uv run python ../tools/export_openapi.py   # sau MỌI thay đổi endpoint

# --- frontend ---
cd frontend
npm install
npm run check                # api:types + typecheck + lint + format
npm run build                # -> dist/, FastAPI sẽ serve
npm run dev                  # http://localhost:5173, proxy /api sang :8080

# --- chạy thử có giao diện ---
cd backend && uv run uvicorn blackinterface.api.app:app --port 8080
# rồi mở http://127.0.0.1:8080   (phải npm run build trước)

# --- công cụ OneATS ---
python tools/verify_dataserver.py    # xác minh lại "sự thật đã đo" trên hệ live
python tools/probe_dataserver.py --dump --slim --depth 4 \
  --out backend/tests/fixtures/sas_tree.json   # tạo lại fixture
```

Hướng dẫn test thủ công từng module: `docs/40-testing/`.

**Không được báo "xong" khi `tools/check.py` chưa xanh.**
Test fail thì nói rõ là fail, kèm output. Không giấu, không hedging.

---

## 7. Bẫy đã biết

| Bẫy | Thực tế |
|---|---|
| "Dùng OPC UA A&C cho alarm" | **Sai.** OneATS dùng `OAAlarm.GetActiveAlarm(NodeId[])`, trả ExtensionObject riêng. Subscribe event chuẩn → 0 event. |
| "PubSub Part 14" | **Sai.** DataServer là client-server (`uatcp-uasc-uabinary`). |
| "`Pos.stVal` lồng nhau theo 61850" | **Sai.** ATS làm phẳng: `D03.XCBR1.PosSt`, `MMXU1.AphsA`. |
| "PosSt là boolean" | **Sai.** Dbpos: `0`=INTERMEDIATE `1`=OPEN `2`=CLOSED `3`=BAD. Phải map cả 4. |
| "Mỗi browser một subscription" | **Sai.** Một subscription phía server → fan-out SSE cho N client. |
| "48010 là OneATS HIS" | Trên máy dev này 48010 là `sunshine`. HIS chưa chạy. |
| Tên thiết bị là unique id | **Không.** `DS9` xuất hiện 4 lần trên C29. Dùng path/NodeId làm khoá. |
| `node.get_children()` trả danh sách sạch | **Không.** OneATS lộ cùng một con qua nhiều reference type → trùng lặp. Phải dedupe theo NodeId (`_children()` trong `discovery.py`). Không dedupe → số thiết bị gấp 4. |
| `DataValue.StatusCode_` | Chỉ đúng với asyncua 1.x. Trong venv là asyncua **2.0.1**, field tên `StatusCode`. `tools/` chạy bằng python hệ thống nên có thể lệch version — chạy tools qua `uv run` nếu cần chắc. |
| `DBB`/`EBB` là thanh cái | **Sai.** Đó là **bảo vệ so lệch thanh cái**. Thanh cái thật ở `/SAS/Subs/BB11..BB29`. |
| `-9` (XSWI9) là dao chọn thanh cái như `-1`/`-2` | **Sai ở ngăn đường dây/MBA.** `-9` nối thanh cái vòng thẳng vào phía **đường dây**, bỏ qua máy cắt. Ở ngăn nối vòng (D12/E04) thì `-9` lại nằm sau máy cắt. Cùng số hiệu LN, khác vị trí điện — xem §5.5. |
| Màu: đỏ = có điện | **Sai.** OneATS: **thiết bị** đỏ=đóng/xanh lá=mở; **dây dẫn** xanh dương=có điện/xanh lá=không điện. |
| Dùng màu của sơ đồ để báo trạng thái phần mềm (mất kết nối, đang tải) | **Sai và đã từng gây lỗi thật.** Header cũ tô "mất kết nối" bằng `--closed` (đỏ) và "trực tuyến" bằng `--open` (xanh lá) — đúng hai màu đang có nghĩa "máy cắt đóng" và "dao mở" trên sơ đồ bên cạnh. **Hai bảng màu tách bạch** (ADR-0014 §2, `styles.css`): `st-*` cho trạm, `sys-*` cho phần mềm, và `sys-*` **không bao giờ dùng đỏ hoặc xanh lá**. "Trực tuyến" là màu trung tính. |
| Vẽ `-1` và `-2` trên cùng một đường thẳng đứng | **Sai và nguy hiểm.** Đường đó chạm cả hai thanh cái tại cùng một điểm → hình luôn trông như có đường dẫn xuyên qua cả hai, bất kể dao ở đâu. Mỗi dao nối thanh cái phải có **làn x riêng** + **chấm nối**; cắt ngang không chấm = không nối. `test_no_conductor_runs_through_another_devices_busbar_connection` khoá điều này. |
| Mỗi cấp điện áp một hình riêng | SLD thật vẽ **cả trạm trong một hình**, cấp cao nhất trên cùng và **lật ngược** để hai nhóm thanh cái quay vào nhau. `layout_station()`; `/api/diagram`. |
| `uv sync` báo `os error 396` / `Access is denied` | OneDrive giữ file trong `.venv`. Đã set `link-mode = "copy"`; nếu vẫn lỗi thì **chạy lại lần 2**. `tools/check.py` tự retry 1 lần. |
| Path `Objects/Root/EVN/RLDC/PROJECT/SAS` là cố định | **Sai.** Path chứa **tên project** — đổi project trong DataServer là path đổi. `discovery.py` auto-dò root theo *nội dung* (node có con dạng `\d+kV`), nhưng `tools/probe_dataserver.py` và `verify_dataserver.py` vẫn hardcode path DEMO. |
| "DataServer không có bằng chứng ghép ngăn MBA / tên ngăn chữ" | **Sai** (đính chính 2026-08-05). `<bay>/BAY/Name` mang tên hiển thị ("Ben Cat", "AT1 Incoming"), và `/SAS/AT1` (ngang cấp điện áp, có `YPTR`/`YLTC`) là chính MBA. Ghép ngăn 220↔110: id nhóm MBA xuất hiện trong `BAY/Name` của cả hai ngăn. Cuộn 3 (22kV, J01) có `BAY/Name` rỗng nhưng ghép được qua số máy cắt EVN (TT 44/2014/TT-BCT): `<mã cấp áp>3<số MBA>` → 231/131/431 đều là AT1. Xem `topology.pair_transformers()`. |
| Dùng `<bay>.IsLive` làm nguồn để tô màu mang điện | **Đừng.** OneATS **suy** nó ra *từ* `Subs.BB*.IsLive` bằng Lua `CheckLiveState`. Lấy nó làm mầm thì kết quả của ta chỉ là chép lại của họ và mất luôn khả năng phát hiện template sai. Gieo mầm **chỉ từ thanh cái**, tự giải, rồi dùng `<bay>.IsLive` để **đối chiếu** (`domain/energization.py`). Hiện 7/7 khớp trên DEMO_SAS. |
| Không đọc được vị trí dao → coi như mở | **Sai và nguy hiểm.** `UNDETERMINED`/`INTERMEDIATE` không nối đảo, nhưng phải **lan nghi ngờ**: đoạn bên kia thành `UNKNOWN` (xám), không bao giờ `DEAD`. Thiếu dữ liệu không bao giờ được suy ra "hết điện" — đó là câu khiến người ta chạm tay vào. |
| Node `EARTH` gộp vào phân hoạch đảo được | **Không.** Mọi đoạn đang tiếp địa sẽ dính thành một đảo khổng lồ và phán quyết nhảy từ ngăn này sang ngăn khác. Earth đứng ngoài union-find; dao tiếp địa đóng chỉ *đánh dấu* đảo là `EARTHED`. |
| Muốn cập nhật liên tục thì duyệt lại cây | **Không.** Duyệt ~6000 node để biết một dao vừa mở là vô lý. Cấu trúc gần như đứng yên lúc vận hành, chỉ *vị trí* chạy → `discovery` duyệt một lần, `monitor` subscribe đúng các điểm đã có địa chỉ (DEMO_SAS: 97). Danh sách theo dõi **sinh từ chính observation** (`watch_points`), không có registry song song. |
| `PointSample.source_ref` là NodeId của logical node | **Sai** (đã sửa 2026-08-05). Phải là NodeId của **biến** sinh ra giá trị (`...XCBR1.PosSt`), không phải của LN cha. `dump.py` vốn đã đúng; `discovery.py` thì không — vừa hỏng truy vết, vừa khiến subscribe sai node. |
| Mất kết nối thì xoá sơ đồ / coi là mất điện | **Sai và nguy hiểm.** Rớt link là tin về *ta*, không phải về trạm. Giữ nguyên giá trị cuối, đặt `connected=false`, nói rõ trên header. Trạm rỗng trông y hệt trạm cắt hết điện. |
| Vá `StationGraph` tại chỗ cho nhanh | Không cần. Đo 2026-08-05: `build_station` 0.71 ms + `solve_energization` 0.21 ms. Dựng lại toàn bộ mỗi lô ~1 ms và **bảo đảm** kết quả giống hệt duyệt mới — sửa tại chỗ không hứa được điều đó. |
| Cho số đo đi chung đường với vị trí đóng cắt | **Sai.** Số đo tương tự đổi liên tục và **không** đổi topology. Chung đường thì `build_station` + `solve_energization` chạy lại mỗi khi phụ tải nhích 0,1 MW, và một bão số đo có thể hoãn việc xử lý một máy cắt vừa nhảy. Hai họ hàm rời nhau trong `observation.py`, `StationStore` định tuyến theo `source_ref`, `test_realtime.py` khoá lại việc hai danh sách không giao nhau (ADR-0012 luật 1). |
| In đơn vị theo suy đoán (kV, MW) cho số đo | **Sai.** DataServer **không** công bố `EngineeringUnits` trên bất kỳ measurand nào (đo 2026-08-06). Biết đại lượng, **không** biết thang: `Vlin` = 221.08 có thể là V hoặc kV. In "221.08 V" cạnh thanh cái 220 kV còn tệ hơn không in gì. Chỉ `Hz`, hệ số công suất, nấc MBA là miễn. Số nào chưa xác minh thang → `Unit.UNKNOWN` + `LimitCode.UNIT_UNVERIFIED` trong bằng chứng. Câu hỏi mở Q7. |
| Một ngưỡng deadband toàn cục cho mọi số đo | **Sai.** 0,5 % của 50 Hz là 0,25 Hz — dao động rất lớn; 0,5 % của phụ tải là nhiễu. Deadband khai theo **từng đại lượng** trong `domain/measurement.py`; `BI_MEASUREMENT_DEADBAND_PCT` chỉ là đặt đè. Nấc MBA **không** deadband: nó rời rạc như vị trí dao. |
| Throttle chỉ cần chặn sườn lên | **Sai.** Bỏ hết trong cửa sổ thì số đo *cuối* của một chùm không bao giờ tới, client đứng ở một số cũ mà không có gì báo là cũ. `api/throttle.py` có sườn xuống. |
| Số của DEMO_SAS dùng để kiểm chứng công thức điện được | **Không.** Simulator sinh ngẫu nhiên từng điểm: đo cùng lúc `D03.MMXU1.Hz = 51.33` và `BB21.Hz = 49.71` — bất khả thi trong một trạm đồng bộ. Dùng nó để kiểm chứng **đường dẫn dữ liệu**, không phải vật lý. |

---

## 8. Ngôn ngữ

- **Trao đổi với người dùng: tiếng Việt.**
- Code, tên biến, docstring, commit message: **tiếng Anh**.
- Tài liệu trong `docs/`: tiếng Việt, thuật ngữ kỹ thuật giữ nguyên tiếng Anh.

---

## 9. Trạng thái repo

- **Có git** (khởi tạo 2026-08-04, chưa có remote). Branch mặc định `master`.
  Làm việc trên branch riêng, đừng commit thẳng lên `master` nếu không được yêu cầu.
- `document/` là tài liệu gốc, **chỉ đọc**, không sửa không xoá.
- Repo nằm trong OneDrive → xem bẫy về `.venv` ở §7.
