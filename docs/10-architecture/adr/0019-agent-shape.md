# ADR-0019 — Hình dạng của agent: quyết định trước, hỏi mô hình sau

- **Status**: Accepted; **§2 và §3 superseded by
  [ADR-0020](0020-model-chooses-the-tools.md)** (2026-08-07). §2 nói mô hình chưa
  chọn tool và ghi sẵn điều kiện xét lại; điều kiện đó được gọi ra sớm. §3 nói
  `LLMProvider` một phương thức; nay là hai.
  **§1, §4 lớp 2 và phương án A superseded by
  [ADR-0021](0021-agent-harness.md)** (2026-08-07): ba bước `plan → read → phrase`
  bỏ cùng cái sàn; `READ_ONLY` thành `REQUIRES_APPROVAL`; và **phương án A đảo
  chiều — Pydantic AI được nhận**, vì tiền đề của nó (§2 nói chưa nên có vòng lặp)
  đã mất hiệu lực từ ADR-0020, còn lập luận «framework không cho ta thứ đặc thù»
  thì tra tài liệu ra là sai. §5, §6, §7, §8 giữ nguyên.
- **Date**: 2026-08-07
- **Supersedes**: không ADR nào. Nhưng **thay dòng «Agent = Pydantic AI»** trong
  `AGENTS.md` §3 — dòng đó viết 2026-08-04, trước khi có một dòng agent nào chạy,
  và chưa từng có ADR đỡ.

## Bối cảnh

GĐ 2 dựng lát cắt dọc mỏng nhất của BlackCore: hỏi bằng tiếng Việt → trả lời kèm
bằng chứng. Kế hoạch chốt 2026-08-05 nói rõ **chỉ 2 tool** (`resolve` + `summary`),
và lý do nằm ở chỗ khác chứ không phải tiết kiệm công: *"dựng mỏng lúc mới có 2
tool thì sai còn sửa được; phát hiện sai sau khi có 7 tool là đập lại tất cả"*.

Ràng buộc đã có từ trước, không thương lượng:

| | Nguồn |
|---|---|
| LLM không nằm trên đường đi của tính đúng đắn | I4, ADR-0005 |
| Evidence là typed object do tool sinh, không do LLM viết | I3, ADR-0004 |
| LLM không bao giờ tự sinh scope ref | I8, ADR-0010 |
| Agent không bao giờ có tool ghi — **vĩnh viễn** | I1, ADR-0011 §3 |
| Agent mượn quyền của người hỏi, không có quyền riêng | ADR-0016 §5 |
| Agent dùng đúng API mà UI dùng | I5 |

Cả sáu đều là phát biểu về **kiến trúc**, không phải về prompt. ADR này ghi lại
hình dạng làm cho chúng đứng được bằng cấu trúc.

## Quyết định

### 1. Ba bước, đúng thứ tự: **lập kế hoạch → đọc → diễn đạt**

```
plan     deterministic, không mô hình     -> đọc scope nào
read     đúng facet mà UI gọi (I5)        -> payload + EvidenceRecord
phrase   mô hình ngôn ngữ, hoặc template  -> chữ
```

Tới lúc mô hình được hỏi bất cứ điều gì, **mọi con số trong câu trả lời đã cố
định và mọi caveat đã ghi xong**. Mô hình nhận chữ, trả chữ, không chạm gì khác.

Hệ quả kiểm tra được, và là hệ quả quan trọng nhất: `backend/tests/unit/test_agent.py`
chạy **toàn bộ 45 test không có mô hình nào**. Một bộ test cần API key mới kiểm
được một dao cách ly đang mở hay đóng chính là bằng chứng rằng I4 đã hỏng.

### 2. Mô hình **không** chọn tool — chưa

Với 2 tool và một resolver deterministic, để mô hình chọn chỉ thêm một kiểu hỏng
mà không thêm khả năng nào. Kế hoạch nằm ở `agent/plan.py`, 4 nhánh, đọc được hết
trong một màn hình.

**Điều kiện xét lại, ghi rõ để phiên sau không phải đoán**: khi danh mục tool đủ
lớn để "chọn cái nào" là một phán đoán thật — quanh module B (alarm + SOE) — thì
việc chọn chuyển sang mô hình, **đi qua đúng lớp kiểm tra hiện có**, và kế hoạch
deterministic vẫn là thứ chạy khi câu trả lời của mô hình không parse được.

### 3. `LLMProvider` là **interface của chúng ta**, một phương thức, không SDK

```python
class LLMProvider(Protocol):
    name: str
    generated: bool
    def stream(self, prompt: Prompt) -> AsyncIterator[str]: ...
```

Hai hiện thực: `OfflineProvider` (không mô hình) và `OpenAIProvider` (bất kỳ
endpoint nào nói OpenAI chat-completions — OpenRouter khi phát triển, Ollama tại
trạm). Gọi bằng `httpx`, một POST và một stream theo dòng.

**Mặc định là `off`.** Cài mới, máy dev, CI — tất cả chạy không cần key. Đây là
cách duy nhất để câu "sản phẩm dùng được khi mô hình chết" được *thử* mỗi ngày
thay vì được *tuyên bố* trong một ADR.

### 4. Registry tool chỉ-đọc, cưỡng chế bằng ba lớp

1. `agent/` không import được `control/` lẫn `integration/` — `check.py` mục 2.
   Một tool ghi ở đây **không có gì để ghi bằng**.
2. Mỗi tool khai một capability, và capability đó phải nằm trong `READ_ONLY`.
   `register()` ném `WriteToolError` ngay lúc import.
3. `check.py` mục 3 đọc `agent/tools/*.py` bằng `ast`: mọi `Tool(...)` phải khai
   `requires=`, và không được khai một capability ghi. Danh sách cấm viết **hai
   lần, ở hai file** — cố ý: nới `READ_ONLY` không được phép nới luôn cái cổng
   gác chính nó.

Lớp 2 và 3 thừa so với lớp 1 **hôm nay**. Ngày module C mở, `control.draft` trở
thành quyền hợp pháp của một số tài khoản, và agent thì mượn quyền của người hỏi
(ADR-0016 §5) — không có hai lớp kia, đúng ngày đó mô hình phân quyền chạy đúng
như thiết kế sẽ lặng lẽ trao cho agent một tool ghi.

`report.export` **không** nằm trong `READ_ONLY`: nó đọc, rồi gửi kết quả ra khỏi
máy. Agent soạn báo cáo, người gửi.

### 5. Câu trả lời tính được là **khoá i18n + tham số**, không phải câu

Backend không biết người đọc muốn tiếng Việt hay tiếng Anh, nên nó không viết
câu. Cùng một lập luận với `LimitCode` trong `domain/evidence.py` và `reason`
trong `domain/energization.py`. `check.py` mục 5 so danh sách khoá `agent/brief.py`
sinh ra với `i18n/vi.ts` + `en.ts` — thiếu một khoá là chữ máy hiện trên màn hình
đúng lúc người trực cần được giải thích.

Prose của mô hình nằm ở `AnswerOut.text` và được nhãn là *diễn giải*; số liệu
nằm ở `summary` / `resolution` / `evidence` (I3). Hai trường khác nhau, không
phải hai đoạn trong một chuỗi.

### 6. Mô hình chết thì mất chữ, không mất câu trả lời

Nếu mô hình hỏng **giữa chừng**, phần chữ đã gửi bị **bỏ**, không giữ lại. Nửa
câu về việc dao nào đang mở tệ hơn không có câu nào. `AnswerOut.llm_error` nói rõ
đã xảy ra, `key`/`params` mang câu tính được. Không có hạ cấp âm thầm.

### 7. Hai cửa, một đường code

`POST /api/ask` trả nguyên khối; `POST /api/ask/stream` gửi từng khung. Cùng một
generator, đúng cặp `/api/live` + `/api/stream` (ADR-0012) và cùng lý do: client
không giữ được stream vẫn dùng được tính năng.

POST cho cả hai, kể cả cái stream. Câu hỏi là văn bản tự do; nó thuộc về body,
không thuộc về một URL đi vào access log và lịch sử trình duyệt. Giá phải trả là
mất `EventSource` — frontend đọc bằng `fetch`, thứ nó phải làm để gửi body.

### 8. Bộ nhớ hội thoại: trong tiến trình, sau protocol

`Conversations` là protocol; hiện thực hôm nay là `InMemoryConversations`, có
chặn số lượng, mất khi khởi động lại. **Hội thoại thuộc về người mở nó** — hỏi
tiếp id của người khác thì im lặng mở hội thoại mới, không báo lỗi (báo lỗi là
xác nhận id đó có tồn tại).

`agent/` không import được `store/`, nên bản SQLite sẽ do `api/` tiêm vào, đúng
hình dạng của station store. Đó là lý do protocol nằm ở đây còn database thì không.

## Phương án đã bác bỏ

**A. Pydantic AI** (thứ `AGENTS.md` §3 đã ghi từ 2026-08-04). Nó giải bài toán
*vòng lặp gọi tool do mô hình điều khiển* — chính là bài toán §2 nói chưa nên có.
Thứ còn lại sau khi bỏ vòng lặp đó là một POST và một stream theo dòng, và
`pydantic-ai-slim[openai]` kéo về cả `openai` SDK để làm việc đó. Tại một trạm
điện air-gapped, một dependency phải cập nhật để vá lỗi của lớp bọc quanh một
POST là gánh nặng, không phải tiện lợi. **Đường lui còn nguyên**: `LLMProvider`
là một phương thức — bọc Pydantic AI thành một hiện thực nữa là chuyện một file,
và đó chính là việc phải làm khi §2 tới điều kiện xét lại.

**B. Để mô hình chọn tool ngay từ đầu.** Xem §2. Bác vì thêm kiểu hỏng mà không
thêm khả năng, **không** vì nguyên tắc — điều kiện xét lại đã ghi ở §2.

**C. Backend viết luôn câu tiếng Việt cho phương án dự phòng.** Đơn giản hơn một
file. Bác vì sản phẩm có hai ngôn ngữ UI (ADR-0014) và câu nướng cứng sẽ sai ở
một trong hai. Lập luận này đã dùng hai lần trước đó và không có lý do để lần này
khác.

**D. Lưu hội thoại xuống SQLite ngay.** Một migration và một repository, không
khó. Bác vì cái đáng chốt là **hình dạng** (protocol), còn transcript trở thành
thứ để *soát lại* chứ không phải để *cuộn lên xem* là bài toán của module B —
làm cùng nó, với đúng yêu cầu audit của nó.

**E. `GET` + `EventSource` cho stream.** Rẻ hơn ở frontend. Bác vì câu hỏi vào
URL: mọi câu người trực gõ sẽ nằm trong access log của proxy và trong lịch sử
trình duyệt của máy tính đặt ở phòng điều khiển.

## Hệ quả

- `AGENTS.md` §3 dòng «Agent — Pydantic AI» đổi thành «Agent — `LLMProvider` tự
  viết (ADR-0019)»; `pyproject.toml` bỏ extra `agent`, thêm `httpx` vào deps chính.
- Bốn `BI_LLM*` mới trong `config.py`. Mặc định `BI_LLM=off`.
- `check.py` mục 3 thêm máy dò tool ghi; mục 5 thêm máy dò khoá câu trả lời.
  Cả hai đã bẻ thử và xác nhận đỏ (2026-08-07).
- `api/deps.py` giữ thêm provider (dựng lười) và conversations.
- **Còn nợ, cố ý**: hội thoại không bền qua khởi động lại (§8); mô hình không
  chọn tool (§2); chưa có endpoint liệt kê hội thoại — client giữ id.
- Bước kế tiếp là `ChatPane` thật, rồi mới dựng vỏ theo
  [ADR-0018](0018-conversation-first-workspace.md).

## Nguồn

- `document/@Station_UseCases 1.xlsx` — 30 use case, tất cả là *hỏi → trả lời*
- Tên thiết bị đo trên `DEMO_SAS` 2026-08-06: `271` là `D03.XCBR1`; `Lai Uyen`
  là tên của **cả E01 lẫn E02** — nguồn của luật "nhập nhằng thì hỏi lại"
- `backend/tests/unit/test_agent.py` — 45 test, không mô hình nào
