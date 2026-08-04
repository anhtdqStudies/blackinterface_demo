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

Không đọc `document/UserManual/*.pdf` trừ khi thật sự cần — đã chắt lọc vào `docs/`.

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

## 2. Bảy luật bất biến (INVARIANTS)

Vi phạm bất kỳ luật nào dưới đây = sai, kể cả khi code chạy được.
Nếu bạn nghĩ cần phá luật, **dừng lại và hỏi người dùng**, đừng tự quyết.

### I1. MVP là READ-ONLY. Cưỡng chế bằng cấu trúc, không bằng prompt.
- Tool registry **không được chứa** bất kỳ tool ghi nào.
- Client OPC UA phải dùng account read-only, không Anonymous.
- Không bao giờ gọi `*.PosCtl`, `SysCommon.Force/Unforce`, `OADataModel.Restart`,
  `OATagging.Set*`, `OAAlarm.Ack*/Enable/Disable`.
- Danh sách đầy đủ bề mặt ghi: `docs/30-integration/oneats-dataserver.md` §Bề mặt ghi.

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

---

## 3. Tech stack (đã chốt)

| Lớp | Công nghệ | Ghi chú |
|---|---|---|
| Backend | **Python 3.12** (không phải 3.13) | ecosystem wheel còn lệch trên 3.13 |
| Dependency | **uv** | lockfile + quản lý bản Python + export offline wheels |
| API | **FastAPI** + SSE | |
| OPC UA | **asyncua** | client-server, KHÔNG phải PubSub |
| Store | **SQLite** | config, release, topology, event store. **Không dùng MongoDB** |
| Agent | **Pydantic AI** | |
| LLM | OpenRouter (dev) → Ollama (trạm) | qua interface `LLMProvider`, đổi bằng config |
| Frontend | **Nuxt build static (SPA)** | FastAPI serve tĩnh → 1 process, không cần Node runtime |
| Đóng gói | embedded CPython + Inno Setup → Windows Service | |

**Không được thêm** vào stack mà không có ADR: MongoDB, Postgres, Docker, Redis,
Node runtime ở production, message broker.

---

## 4. Cấu trúc thư mục

```
backend/src/blackinterface/
  domain/        # L4 Neutral Station Model — contract hợp nhất, immutable
    models.py        Bay/Device/Busbar/ConnectivityNode/PointSample/ValidationIssue
    observation.py   StationObs — đầu vào trung tính cho mọi importer
    bay_types.py     suy loại ngăn từ thành phần LN
    templates.py     loader + registry cho templates/*.yaml
    templates/       6 bay template (ADR-0008)
    topology.py      observation + template -> StationGraph  (thuần, không I/O)
  integration/   # L5 importers + adapters — CHỈ ĐÂY được biết NodeId
    dump.py          đọc dump JSON -> StationObs (offline, dùng cho test/demo)
    opcua/discovery.py  browse DataServer live -> StationObs
  diagram/       # L6 graph → layout → ViewModel → SVG
    layout.py        StationGraph -> DiagramView (toạ độ, deterministic)
  api/           # L3 Typed Domain API (FastAPI, HTTP/SSE)
    source.py        StationStore: fixture | opcua, cấu hình qua BI_*
    app.py           endpoint + serve frontend/dev
  agent/         # L2 BlackCore (Pydantic AI: intent, tools, planner, evidence)
  store/         # SQLite: release, snapshot, event store
frontend/
  dev/index.html # viewer 1 file, không cần Node — xem §4.1
tools/           # script vận hành/kiểm chứng — chạy được độc lập
docs/            # xem §0
document/        # tài liệu gốc ATS (manual PDF, output service SLD) — CHỈ ĐỌC
```

### 4.1 Frontend hiện tại là bản dev, không phải bản chốt

`frontend/dev/index.html` là **một file HTML tĩnh**, FastAPI serve trực tiếp,
không build, không Node. Nó tồn tại để **nhìn thấy kết quả ngay** trong lúc dựng
từng module.

Bản chính thức vẫn là **Nuxt static SPA** như §3. Khi dựng Nuxt, đây là bản tham
chiếu về mặt hành vi — đừng xoá cho tới lúc đó, và đừng để nó phình thành
ứng dụng thật.

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

### 5.5 Không tin dữ liệu extract SLD
`document/SLD_serviceOut/` là output computer-vision, **có lỗi đã xác nhận**:
số hiệu EVN sai (D03 ghi 179, thực tế 271), sót nguyên ngăn J01 22kV,
20–26% thiếu tên, 36–40% thiếu connections.
DataServer là chân lý. SLD chỉ dùng để đối chiếu.

---

## 6. Công cụ kiểm tra

```bash
cd backend
uv sync                      # cài môi trường
uv run ruff check .          # lint
uv run ruff format --check . # format
uv run mypy src              # type check
uv run pytest                # test (không cần DataServer)
uv run pytest -m live        # test cần DataServer đang chạy

# chạy thử có giao diện:
uv run uvicorn blackinterface.api.app:app --port 8080   # rồi mở http://127.0.0.1:8080

# từ gốc repo:
python tools/check.py             # chạy tất cả ở trên + kiểm tra cấu trúc docs
python tools/verify_dataserver.py # xác minh lại "sự thật đã đo" trên DataServer live
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
| `uv sync` báo `os error 396` / `Access is denied` | OneDrive giữ file trong `.venv`. Đã set `link-mode = "copy"`; nếu vẫn lỗi thì **chạy lại lần 2**. `tools/check.py` tự retry 1 lần. |

---

## 8. Ngôn ngữ

- **Trao đổi với người dùng: tiếng Việt.**
- Code, tên biến, docstring, commit message: **tiếng Anh**.
- Tài liệu trong `docs/`: tiếng Việt, thuật ngữ kỹ thuật giữ nguyên tiếng Anh.

---

## 9. Trạng thái repo

- **Chưa init git** (repo nằm trong OneDrive — xem `docs/90-progress/status.md`).
  Đừng tự chạy `git init` nếu người dùng chưa yêu cầu.
- `document/` là tài liệu gốc, **chỉ đọc**, không sửa không xoá.
