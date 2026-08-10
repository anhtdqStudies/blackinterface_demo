# ADR-0021 — Harness thật: Pydantic AI, tool ghi sau cổng duyệt, bỏ sàn template

- **Status**: Accepted
- **Date**: 2026-08-07
- **Supersedes**:
  - [ADR-0019](0019-agent-shape.md) **§1** (ba bước `plan → read → phrase`),
    **§4 lớp 2** (mọi capability của tool phải nằm trong `READ_ONLY`), và
    **phương án A** (bác Pydantic AI).
  - [ADR-0020](0020-model-chooses-the-tools.md) **§1** (`MAX_STEPS = 6` cứng),
    **§3** (đường deterministic là sàn), **§4** (`LLMProvider` hai phương thức).
  - [ADR-0011](0011-single-gated-write-path.md) **§3** — «Agent không có tool
    ghi. Vĩnh viễn.» Câu khẩu hiệu *«Agent soạn phiếu, người ký»* **giữ nguyên**;
    đổi cách cưỡng chế nó.
- **Sửa đổi**: invariant **I1**, **I3**, **I4** trong `AGENTS.md` §2; hàng
  *Agent* và *LLM* trong `AGENTS.md` §3.
- **Đã xác minh** (2026-08-07, sau khi ADR chốt): giả định về kích thước payload
  ở **§5** đã **đo thật** — `summary(station)` = 50.345 ký tự ≈ **15.733 token**,
  đúng như ước lượng. Số đo đầy đủ + ba kết luận (evidence chiếm một nửa; facet
  là bắt buộc; `source_ref` phải bị chặn khỏi digest theo I6) nằm ở
  `docs/90-progress/status.md` §*SỰ THẬT ĐÃ ĐO*. Trần 2k/tool-digest **giữ nguyên**.
  Thân ADR không sửa (ADR immutable — `AGENTS.md` §5.3).
- **Giữ nguyên**: [ADR-0005](0005-ai-off-correctness-path.md) — topology,
  energization, chuỗi nhân quả vẫn deterministic. ADR này **không** đụng vào
  phát biểu đó; nó chỉ sửa một hệ quả mà I4 suy ra hơi rộng (xem §3).

## Bối cảnh

ADR-0019 và ADR-0020 được viết cho một agent có **2 tool chỉ-đọc**, nơi mô hình
làm mỗi việc diễn đạt (0019) rồi thêm việc chọn đọc gì (0020). Với phạm vi đó,
mọi quyết định trong hai ADR ấy đều đúng.

Ngày 2026-08-07 người phụ trách sản phẩm mở lại phạm vi, với ba câu:

> «phải là AI first cơ mà?»
> «lý do gì không làm harness như codex hay claude nhỉ?»
> «các tools ấy là các tools nối với ATS, phải là 1 harness mạnh, suy luận, giải
> quyết được vấn đề… tất nhiên không phải cho vạn năng mà kiểm soát các function
> calling, mcp là được mà?»

Kèm một quyết định về sản phẩm: **sau này sẽ có tool ghi.**

Đó là một tiền đề mới, không phải một ý thích. Phạm vi đi từ *2 tool chỉ-đọc +
diễn đạt* sang *8 tool + duyệt ghi + compaction + gọi song song + ngân sách
token*. Quyết định hợp lý cho phạm vi cũ không tự động còn hợp lý cho phạm vi
mới, và ADR này ghi lại việc xét lại đó.

### Triệu chứng quan sát được, 2026-08-07

Người dùng gõ `hello`, nhận về nguyên bảng trạng thái trạm: 80 thiết bị, 4
caveat, 159 điểm đo. Không phải bug — là hệ quả trực tiếp của ADR-0020 §3:
`Outcome.answered` đòi **cả** chữ **lẫn** evidence, nên một câu chào không kèm
tool call bị coi là thất bại và rơi xuống sàn, mà sàn thì vô điều kiện gọi
`resolve` + `summary` trên scope của pane.

Không có đường nào để agent trả lời một câu không cần đọc gì. Đó là cái giá của
sàn, và nó hiện ra ở màn hình đầu tiên người dùng nhìn.

### Đính chính: điều tra về Pydantic AI, 2026-08-07

ADR-0019 phương án A bác Pydantic AI với hai lý do: (a) nó giải bài toán vòng lặp
mà §2 nói chưa nên có, (b) gánh nặng dependency ở trạm air-gapped. Lý do (a) đã
mất hiệu lực từ ADR-0020. Trong phiên này, lập luận «framework không cho ta thứ
gì đặc thù của bài toán» được **kiểm tra lại bằng tài liệu** và **sai**:

| Thứ tưởng phải tự viết | Pydantic AI có sẵn |
|---|---|
| Tách *cái model thấy* khỏi *cái ứng dụng nhận* | `ToolReturn(return_value=…, content=…, metadata=…)` |
| Dừng loop chờ người ký, rồi chạy tiếp | `requires_approval=True`, `ApprovalRequired`, `ctx.tool_call_approved`, `DeferredToolRequests` / `DeferredToolResults`, `ToolDenied` |
| Ngân sách token, chặn khi vượt | `UsageLimits`, `RunUsage`, `UsageLimitExceeded` |
| Từ chối *dưới dạng message* để mô hình sửa | `ModelRetry` |
| Khung `tool` / `evidence` ra SSE | `agent.run_stream_events()` |
| Tiêm `ToolContext` (principal, store) | `deps_type` + `RunContext[T]` |
| Compaction | capability có sẵn |
| Chèn authz vào tool MCP của bên thứ ba | `MCPToolset(process_tool_call=…)` |
| Test không cần mô hình | `TestModel` / `FunctionModel` |

Tám trên chín. Lập luận (a) sụp hoàn toàn; lập luận (b) — air-gapped — vẫn thật
và được xử ở §8 chứ không bị bỏ qua.

Đáng chú ý nhất là `raise ApprovalRequired` **có điều kiện**: kiểm tra interlock
chạy trong thân tool, đạt thì đi tiếp, không đạt thì bật thành yêu cầu chữ ký.
Đó là *«Agent soạn phiếu, người ký»* viết bằng một câu lệnh — không phải một
ngoại lệ của I1 mà là một hiện thực trung thực hơn của chính nó.

## Quyết định

### 1. Nhận Pydantic AI làm cơ chế; giữ chính sách trong `agent/`

**Thuê cơ chế, giữ chính sách.** Vòng lặp, sinh schema từ type hint, validate
args, retry, usage, streaming, approval — thuê. Còn lại là code của ta và không
đi đâu cả:

| Chính sách | Ở đâu sau khi đổi |
|---|---|
| Tool gọi đúng facet mà UI gọi (I5) | thân tool, gọi `build_summary` như cũ |
| Capability gating theo *người hỏi* (ADR-0016 §5) | thân tool, đọc `ctx.deps.principal` |
| Scope ref phải đã được chứng kiến (I8) | `ModelRetry`, logic không đổi |
| `EvidenceRecord` do tool sinh (I3) | `ToolReturn.metadata` |
| `agent/` không import `control/` | không đổi, `check.py` mục 2 giữ nguyên |

`provider.py` (431 dòng) và `loop.py` (316 dòng) phần lớn **bị xoá**, không phải
sửa. `OpenAIProvider` biến mất; OpenRouter là một `base_url` OpenAI-compatible
mà Pydantic AI đã hỗ trợ.

### 2. I1 phát biểu lại: không có tool **tự thực thi**

> **Agent không bao giờ có tool tự thực thi.** Tool ghi được phép tồn tại trong
> danh mục, nhưng mọi tool chạm bề mặt ghi **bắt buộc** dừng ở khung duyệt và
> chỉ chạy tiếp sau một chữ ký của người. Quyền `control.sign` **không bao giờ**
> nằm trong tập quyền agent mượn được.

Không nới cái gì cả — nó chặt hơn phát biểu cũ ở một điểm. Phát biểu cũ nói *tool
ghi không tồn tại*, và đó là một khẳng định về **danh mục**. Ngày module C mở,
`control.draft` thành quyền hợp pháp của một số tài khoản, agent mượn quyền của
người hỏi, và khẳng định về danh mục sẽ phải nới ra bằng cách nào đó — ADR-0019
§4 đã dự đoán đúng chỗ nguy hiểm này. Phát biểu mới là khẳng định về **đường thi
hành**, và đường thi hành thì kiểm tra được bằng test.

Ba lớp cưỡng chế của ADR-0019 §4 giữ nguyên hình, đổi nội dung lớp 2:

1. `agent/` không import `control/` — **không đổi**.
2. `READ_ONLY` → **`REQUIRES_APPROVAL`**. Tool khai capability ngoài `READ_ONLY`
   thì `register()` **bắt buộc** `requires_approval=True`; thiếu là lỗi lúc
   import, y như `WriteToolError` hôm nay.
3. `check.py` mục 3 đọc `ast`: giữ nguyên luật cũ, thêm luật mới — capability
   ghi mà không kèm `requires_approval=True` là **đỏ**. Danh sách vẫn nằm hai
   nơi, hai file, đúng lý do cũ.

`control/registry.py` **vẫn rỗng**. ADR này không mở lệnh nào; nó chỉ định nghĩa
cái cổng mà lệnh đầu tiên sẽ phải đi qua.

### 3. I4 thu hẹp đúng phần suy rộng, giữ nguyên phần lõi

I4 gồm hai mệnh đề. Mệnh đề lõi — *topology, layout, energization, chuỗi nhân
quả là deterministic; LLM không khẳng định sự thật* — **giữ nguyên tuyệt đối**.
Đó là ADR-0005 và ADR này không đụng tới.

Mệnh đề hệ quả — *hệ phải test được đầu-cuối không cần LLM; UI phải dùng được khi
LLM chết* — được phát biểu lại:

> Domain API, facet, sơ đồ, SSE, và toàn bộ giao diện giám sát **phải chạy đúng
> khi không có mô hình nào**. Riêng **lượt hội thoại** thì cần mô hình: không
> cấu hình mô hình thì tab hội thoại báo chưa cấu hình, chứ không trả lời bằng
> template.

Cái giữ cho «UI dùng được khi LLM chết» đứng vững **không phải** sàn template —
là **I5**: frontend gọi thẳng Domain API, BlackCore không phải proxy. Mô hình
chết thì panel, sơ đồ, số đo, SSE không hề biết. Sàn template chưa bao giờ là
thứ giữ lời hứa đó; nó chỉ làm cho tab hội thoại trả về *một cái gì đó*, và
ADR-0020 §3 đã phải thừa nhận «một cái gì đó» ấy có thể là bảng trạng thái trạm
đáp lại câu «hello».

`agent/plan.py`, `agent/brief.py` và nhánh sàn trong `agent/core.py` bị **xoá**
(~380 dòng). Phương án C của ADR-0020 («bỏ hẳn `plan.py`») từng bị bác với lý do
*«hệ thống sẽ chỉ trả lời được khi có key»* — nay đó chính là điều được chấp
nhận, có ý thức, cho riêng tab hội thoại.

### 4. I3 siết chặt thêm

> Evidence là typed object do tool sinh (không đổi). **Và**: mọi con số xuất hiện
> trong prose của mô hình phải truy được về `metadata` của một `ToolReturn` trong
> chính lượt đó.

Cưỡng chế bằng `ToolReturn`: `metadata` mang `EvidenceRecord` + payload đầy đủ và
**mô hình không nhìn thấy nó**; `content` mang bản gọn cho mô hình. Hai đường
tách vật lý, không phải tách bằng kỷ luật.

### 5. Ngân sách token là ràng buộc hạng nhất, đặt theo **trạm** chứ không theo máy dev

Đây là ràng buộc kỹ thuật nặng nhất của ADR này và nó đến từ số học, không từ sở
thích.

- Mỗi tool result **phải** có bản `digest` cho mô hình. Payload đầy đủ đi thẳng
  ra UI qua SSE, không qua context window.
- Trần cấu hình được: `max_tool_digest_tokens`, `max_turn_tokens`, `max_steps` —
  đặt theo hồ sơ **trạm**, không theo hồ sơ máy dev, kể cả khi máy dev thừa sức.
- Cưỡng chế bằng test: digest vượt trần là **đỏ**, không phải phát hiện lúc chạy.
- `usage` trả về từ endpoint được **giữ lại** để đo thật, thay cho ước lượng.

`MAX_STEPS = 6` cứng của ADR-0020 §1 bỏ. Thay bằng `UsageLimits` + trần bước cấu
hình được, và khi hết ngân sách thì **nói rõ đã đọc tới đâu** thay vì im lặng rơi
xuống một đường khác.

> **GIẢ ĐỊNH — chưa xác minh (2026-08-07).** Một `summary(station)` ước lượng
> ~15.000 token, suy từ schema `ReadingOut` (12 field × 159 điểm) chứ **chưa đo**.
> Cách đo lại: chạy backend ở cổng 8080, `GET /api/summary?scope=station`, đếm
> byte rồi chia ~3,2 ký tự/token. Trần ở §5 phải đặt lại sau khi có số thật.

### 6. Danh mục tool mở rộng theo trục **facet**, không theo use case

Hai tool là quá ít để «suy luận» có nghĩa. Thêm: `search`, `summary` có tham số
facet, **`trace`** (topology: cái gì cấp cho cái gì, mất điện lan từ đâu),
**`history`** (trend/SOE), `alarms`, `interlock` (đọc thuần, C-01).

`trace` và `history` **không** vi phạm I8. Chúng là **facet mới trên trục scope
đã có**, không phải tool-cho-một-use-case: `trace(scope)` và `history(scope,
window)` nhận đúng thứ `summary(scope)` nhận. Luật của I8 — *thêm use case thì
thêm scope và facet, không thêm tool* — vẫn đứng; điều bị bỏ là con số «đúng hai
tool» của ADR-0019, vốn là một phỏng đoán về độ đủ chứ không phải một invariant.

`trace` là món thiếu quan trọng nhất: không có nó thì *«tại sao E01 mất điện»*
chỉ là đoán từ một cái summary.

### 7. Mô hình và cách phục vụ

- **Dev**: `qwen/qwen3.6-27b` qua OpenRouter — **đúng con sẽ deploy**, không phải
  một con lớn hơn. Model lớn hơn giữ lại làm nút *kiểm tra trần*: hỏng ở 27B mà
  chạy ở model lớn thì đó là giới hạn mô hình; hỏng cả hai thì là lỗi harness.
- **Trạm**: **vLLM** thay Ollama. Lý do là ba thứ harness agentic cần mà Ollama
  không cho: automatic prefix caching (messages của loop là append-only nên gần
  như 100% cache hit), guided decoding cho tool arguments, và tool-call parser
  đúng cho họ Qwen.
- **Pin provider trên OpenRouter** (`provider.order`, `allow_fallbacks: false`).
  Cùng một model id có thể được route sang nhiều nhà cung cấp với sampling default
  và template khác nhau — không pin thì test hôm nay xanh, mai đỏ, code không đổi
  một dòng.

> **GIẢ ĐỊNH — chưa xác minh (2026-08-07).** Card trạm dự kiến RTX 5090 (32GB).
> Tính toán sơ bộ: 27B Q4_K_M ≈ 17GB trọng số, còn ~12GB cho KV cache ≈ 40–60k
> token dùng được. RTX 5080 (16GB) **không đủ** cho 27B Q4. Khoảng cách chất
> lượng giữa Q4 (trạm) và FP16/FP8 (API lúc dev) **không đo được từ xa** — chống
> bằng cách để trần ngân sách chừa biên. Cách đo lại: có máy thật thì chạy một
> lượt 6 bước và ghi tok/s + thời gian tường.

### 8. Air-gapped: trả lời lý do (b) của ADR-0019, không né nó

Lý do bác Pydantic AI năm ADR-0019 vẫn còn giá trị một nửa: một dependency phải
cập nhật để vá lỗi, tại một trạm không có internet, là gánh nặng thật.

Cách xử, ghi thành yêu cầu chứ không thành thiện chí:

- **Pin cứng** phiên bản Pydantic AI trong `uv.lock`, và xác định rằng bản cài
  ở trạm **có thể không bao giờ nâng**. Chấp nhận được với một thư viện; sẽ không
  chấp nhận được với một dịch vụ.
- **Vendor wheel** cho lần cài offline — `uv` đã nằm trong stack đúng vì việc này
  (`AGENTS.md` §3: *«export offline wheels»*).
- Bản cài trạm phải dựng được **không cần mạng**, và đó là một mục trong quy
  trình đóng gói, không phải một ghi chú.

### 9. MCP: chỉ cho hệ ngoài

Tool ATS giữ **in-process**. Authz, evidence và audit đang nằm một chỗ trong
`tools.call()`; đẩy ra sau MCP là thêm một hop mà phải dựng lại toàn bộ ba thứ đó
ở đầu kia.

MCP dùng cho hệ **bên ngoài**: CMMS, kho tài liệu, historian. Và vì tool MCP theo
định nghĩa là tool **do người khác định nghĩa**, không thể tin nó chỉ-đọc — nó đi
qua đúng cổng duyệt của §2, không có ngoại lệ.

### 10. Test: hai tầng

- **Tầng 1** — `TestModel` / `FunctionModel` của Pydantic AI thay `PlanningProvider`
  tự viết. Deterministic, không cần key, chạy trong `check.py` như hôm nay. I4
  mệnh đề lõi vẫn kiểm được bằng máy.
- **Tầng 2** — **eval suite gọi 27B thật**, opt-in qua biến môi trường, **ngoài**
  `check.py`. Assert vào thứ đo được: gọi đúng tool nào, hết mấy bước, tốn bao
  nhiêu token, có bịa scope ref không.

Tầng 2 là thứ duy nhất bắt được trôi dạt giữa máy dev và trạm. Không có nó thì
harness chạy ngon suốt kỳ phát triển rồi lạc ở bước 4 vào đúng ngày nghiệm thu.

## Phương án đã bác bỏ

**A. Giữ harness tự viết, chỉ thêm tính năng.** Đây là phương án được đề xuất
đầu phiên và bị chính người phụ trách sản phẩm bác bằng một câu đúng: *«nếu tự
xây thì ngồi xây tất các phần của Pydantic AI hiện có có vẻ rất mất thời gian và
không cần thiết»*. Kiểm tra tài liệu xác nhận: 8/9 hạng mục đã có sẵn. Giữ tự
viết là trả giá xây lại chúng để đổi lấy một lợi ích — kiểm soát — mà §1 cho thấy
vẫn giữ được qua hook.

**B. LangChain / LangGraph.** Bác. Kéo về một cây dependency lớn hơn nhiều cho
một hệ air-gapped, và repo này đã Pydantic-heavy nên `ToolReturn` + `RunContext`
khớp với `pydantic.BaseModel` sẵn có mà không cần lớp dịch.

**C. Giữ sàn template làm lưới an toàn.** Bác. Nó không giữ lời hứa mà người ta
tưởng nó giữ (I5 mới giữ — §3), nó tạo ra lỗi «hello ra bảng trạm», và nó buộc
mọi tính năng mới phải hiện thực **hai lần**, một lần cho mô hình một lần cho
template. Món thứ ba là món đắt nhất và nó chỉ đắt dần lên.

**D. Bắt duyệt mọi tool call, kể cả tool đọc.** Bác — **giữ nguyên lý do của
ADR-0020 phương án B**: bắt người ta duyệt một việc không thể gây hại thì thói
quen bấm bừa hình thành trong tuần đầu, và cái nút đó vô dụng đúng ngày module C
cho nó ý nghĩa. Duyệt chỉ áp cho tool chạm bề mặt ghi.

**E. Đưa tool ATS ra sau MCP cho «đồng nhất».** Bác — xem §9.

**F. Dev trên một mô hình lớn hơn cho nhanh, đổi sang 27B lúc nghiệm thu.** Bác.
Đó chính là cái bẫy §10 tầng 2 sinh ra để bắt; dev thẳng trên con sẽ deploy thì
không cần bắt.

## Hệ quả

- **Xoá**: `agent/plan.py`, `agent/brief.py`, nhánh sàn trong `agent/core.py`,
  phần lớn `agent/provider.py` và `agent/loop.py`. Tổng ~1.100 dòng.
- **`AGENTS.md` §2**: I1, I3, I4 phát biểu lại. **§3**: hàng *Agent* thành
  «Pydantic AI (ADR-0021)»; hàng *LLM* thành «OpenRouter `qwen/qwen3.6-27b` (dev)
  → vLLM (trạm)». Pydantic AI ra khỏi danh sách *không được thêm*.
- **`check.py`**: mục 2 không đổi. Mục 3 thêm luật `requires_approval`. Mục 5
  (khoá i18n từ `brief.py`) **bỏ** cùng `brief.py` — câu tính được biến mất thì
  máy dò khoá cũng hết việc.
- **`pyproject.toml`**: thêm `pydantic-ai-slim[openai]`, pin cứng. `httpx` ở lại
  (còn dùng ngoài `agent/`).
- `config.py`: `llm_model` mặc định `qwen/qwen3.6-27b`; thêm ba trần ở §5.
- Quyền `control.sign` được **định nghĩa** ở đây nhưng chưa gói cho vai nào —
  lệnh đầu tiên và người ký đầu tiên vẫn cần ADR riêng của nó (ADR-0011 §4 không
  đổi: module C ở giai đoạn cuối).
- **Nợ có ý thức**: chưa đo `summary(station)` thật (§5); chưa có máy trạm để đo
  tok/s (§7); compaction và gọi tool song song hoãn tới sau khi §1–§6 chạy.
- Thứ tự thi công: đo payload → dựng lại `agent/` trên Pydantic AI → ngân sách →
  bỏ sàn → tool mới → eval suite → khung duyệt.

## Nguồn

- Người phụ trách sản phẩm, 2026-08-07 — bốn câu trích ở Bối cảnh và phương án A
- Tài liệu Pydantic AI tra ngày 2026-08-07 (`/pydantic/pydantic-ai`, v2.0.0):
  `docs/deferred-tools.md`, `docs/tools-advanced.md`, `docs/agent.md`,
  `docs/mcp/client.md`, `docs/ui/ag-ui.md`
- <https://openrouter.ai/qwen/qwen3.6-27b> — mô hình chốt cho cả dev lẫn trạm
- Ảnh chụp màn hình 2026-08-07: `hello` → bảng trạng thái 80 thiết bị, nguồn của
  §Bối cảnh/Triệu chứng
- [ADR-0019 §4](0019-agent-shape.md) — dự đoán đúng chỗ nguy hiểm mà §2 ở đây trả lời
