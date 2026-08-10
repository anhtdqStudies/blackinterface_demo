# ADR-0020 — Mô hình chọn tool; key nằm trong SQLite

- **Status**: Accepted; **§1, §3 và §4 superseded by
  [ADR-0021](0021-agent-harness.md)** (2026-08-07). §1: `MAX_STEPS = 6` cứng đổi
  thành `UsageLimits` + trần cấu hình được. §3: **đường deterministic không còn là
  sàn — nó bị xoá**; cái giữ «UI dùng được khi mô hình chết» là I5, không phải
  template (ADR-0021 §3). §4: `LLMProvider` tự viết nhường chỗ cho Pydantic AI.
  §2 (bốn thứ mô hình không làm được) và §5 (key trong SQLite) **giữ nguyên** —
  §2 điểm 1 nay đọc theo I1 mới: tool ghi tồn tại nhưng dừng ở khung duyệt.
- **Date**: 2026-08-07
- **Supersedes**: [ADR-0019](0019-agent-shape.md) **§2** (mô hình không chọn tool)
  và **§3** (`LLMProvider` một phương thức). Phần còn lại của ADR-0019 giữ nguyên.

## Bối cảnh

ADR-0019 §2 viết sẵn điều kiện xét lại: *"khi danh mục tool đủ lớn để «chọn cái
nào» là một phán đoán thật — quanh module B"*. Người phụ trách sản phẩm gọi điều
kiện đó ra sớm, ngày 2026-08-07, và nêu ba ý:

> «phải dùng AI vào chứ, còn quyết định là do người phụ trách cơ mà?»
> «AI chỉ có thể quyết định ở một số trường hợp nhất định»
> «như hiện tại nó đơn giản toàn là logic, chẳng có tí AI nào cả»

Ý thứ ba là một **phát biểu đúng về sự thật**, không phải một ý kiến: mặc định
`BI_LLM=off`, planner là regex, resolver là so chuỗi bỏ dấu. Không có một dòng
nào của mô hình chạy trong đường trả lời.

Và lập luận «AI không thêm khả năng nào» của ADR-0019 §2 **đã sai ở một chỗ cụ
thể**. Nó đúng với «271 thế nào?». Nó sai với:

| Câu hỏi | `plan.py` | Vòng lặp |
|---|---|---|
| `ngăn Lai Uyên bên 110 có điện không?` | regex không bắt được | hiểu |
| `so sánh 271 với 272` | chỉ gọi được `summary` một lần | gọi hai lần |
| `tại sao E01 mất điện?` | không nối được chuỗi tool | nối được |
| `cái ngăn hồi nãy ấy` | không | có |

`plan.py` chọn **một** scope và đọc **một** lần. Đó là giới hạn của hình dạng,
không phải của số lượng tool — nên «đợi tới module B» là đợi nhầm thứ.

### Đính chính một chỗ hiểu sai về I4

I4 nói LLM không được **khẳng định** một sự thật, và hệ thống phải test được
đầu-cuối không cần mô hình. **Nó không cấm LLM chọn đọc gì.** ADR-0019 §2 chặt
hơn mức invariant đòi, và chặt hơn đó là quyết định của phiên viết nó, không phải
của I4. ADR này nới đúng phần dư ra, giữ nguyên phần I4 thật sự nói.

## Quyết định

### 1. Mô hình chọn tool, trong một vòng lặp có trần — `agent/loop.py`

```
model  ──decide(messages, tools)──>  ToolRequest[]  hoặc  text
  ^                                       │
  └────── kết quả tool (JSON) ────────────┘     tối đa MAX_STEPS = 6 vòng
```

Sáu vòng: hai `resolve` + hai `summary` là bốn, còn chỗ hồi lại sau một lần bị
từ chối. Trần lớn hơn không mua được câu trả lời tốt hơn — nó mua thời gian chờ
và hoá đơn cho một mô hình đã lạc đề.

### 2. Bốn thứ mô hình **vẫn không** làm được, không thứ nào dựa vào prompt

1. **Tool nào cũng chỉ-đọc**, cưỡng chế lúc import + `check.py` mục 3. Không có
   tool ghi để mà chọn (I1). Không đổi so với ADR-0019 §4.
2. **`tools.call()` từ chối theo quyền của *người hỏi*.** Agent mượn quyền, không
   có quyền riêng (ADR-0016 §5). Mô hình đòi thứ người trực không được xem thì
   nhận lời từ chối, không nhận dữ liệu. Danh mục tool đưa cho mô hình cũng đã
   lọc theo quyền — đưa thừa chỉ tốn một vòng.
3. **Scope ref phải *đã được trả về cho nó*.** `resolve` sinh ref; mô hình chỉ
   được truyền lại ref đã nhận, hoặc scope mà câu hỏi được đặt từ đó. Gõ
   `bay:E01` từ trí nhớ thì bị từ chối kèm câu «gọi resolve trước».
4. **Mọi con số hiển thị đến từ payload của tool.** Chữ của mô hình nằm ở
   `AnswerOut.text`, nhãn *diễn giải*; câu tính được vẫn ở `key`/`params` bên
   cạnh (I3, ADR-0019 §5 — không đổi).

Điểm (3) là điểm đáng giá nhất và là điểm mới. `bay:E01` **có tồn tại**, nên
không tầng nào phía dưới phản đối — đó chính là chỗ nguy hiểm: một câu trả lời tự
tin về nhầm ngăn nhìn y hệt một câu trả lời đúng. Từ chối được trả về **dưới dạng
một message**, không phải exception, vì nó sửa được và cách sửa chính là hành vi
ta muốn: mô hình gọi `resolve` rồi đi tiếp.

### 3. Đường deterministic là **sàn**, không phải chế độ hỏng

`plan → read → template` chạy khi: không cấu hình mô hình; mô hình không gọi
được; câu trả lời không parse được; **và khi mô hình trả lời mà chưa đọc gì**.

Điều kiện cuối đáng ghi rõ. Chữ không có bằng chứng đằng sau là phỏng đoán, và
phỏng đoán tệ hơn câu tính được. `Outcome.answered` đòi **cả** chữ **lẫn**
evidence.

Hệ quả kiểm tra được, và là hệ quả quan trọng nhất: **53 test trong
`test_agent.py` vẫn chạy không cần mô hình nào.** I4 nguyên vẹn.

### 4. `LLMProvider` thành **hai** phương thức

```python
def stream(self, prompt: Prompt) -> AsyncIterator[str]: ...          # diễn đạt
async def decide(self, messages, tools) -> Decision: ...             # chọn
```

`decide` không stream — một tool call chỉ dùng được khi đã về nguyên vẹn, nửa cái
tên hàm là không có gì. Cái người dùng nhìn thấy chảy trong lúc đó là khung
`tool` và `evidence`, vốn mới là phần đáng nhìn.

**Nợ**: câu trả lời cuối của vòng lặp về nguyên khối, không chảy từng chữ. Sửa
được bằng một lần gọi `stream()` nữa với cùng lịch sử; chưa làm vì tốn thêm một
lượt gọi mô hình để đổi lấy mỹ quan.

### 5. Key và lựa chọn mô hình nằm trong SQLite, không chỉ trong biến môi trường

Bảng riêng `assistant_config`, đúng một dòng. **Không** nhét vào `app_meta`: đó
là k/v cho trạng thái vận hành nhỏ, và một bí mật nằm cạnh `last_model_version`
là một bí mật không ai nhớ nó ở đó.

- Key **mã hoá bằng Fernet**, khoá dẫn xuất từ `BI_SECRET_KEY` (`store/secrets.py`).
- **Thứ tự ưu tiên: DB > env.** Câu trả lời của trạm thắng mặc định của máy.
  `BI_LLM*` ở lại cho CI và máy dev, nơi không có giao diện để điền.
- Quyền mới **`assistant.config`**, gói cho `admin` và `engineer`. **Không** dùng
  `model.*` sẵn có — `model` ở đó nghĩa là *model trạm*, một chữ làm hai việc
  trong tên quyền là lỗi người ta mắc đúng một lần, vào lúc tệ nhất.
- **API không bao giờ trả key.** `AssistantConfigOut` chỉ có `has_key`. Test kiểm
  bằng cách tìm chuỗi key trong *toàn bộ* body, không kiểm từng field — một
  field thêm sau này mà lỡ mang key sẽ qua được kiểu kiểm thứ hai.
- **Lưu ≠ chạy được.** Chỉ `POST /api/assistant/test` gọi thật mới đặt
  `verified_at`, và mọi lần lưu đều xoá nó.

`store/secrets.py` nói rõ cái này **không** chống được gì: người có shell trên
máy đang chạy. Tiến trình phải giải mã được key để dùng, nên `BI_SECRET_KEY` nằm
trong môi trường của nó. Nếu biến đó được đặt trong một file ngay cạnh database
thì đây là **dời chỗ** bí mật, không phải xoá nó. Nói thẳng còn hơn để chữ «đã mã
hoá» làm việc mà nó không làm được.

## Phương án đã bác bỏ

**A. Chỉ cho LLM hiểu câu hỏi + diễn đạt, không có vòng lặp.** Mô hình dịch câu
hỏi thành một kế hoạch có cấu trúc, backend gọi tool theo kế hoạch đó. Ít kiểu
hỏng hơn. Bác vì nó không làm được câu nhiều bước — mà nhiều bước chính là thứ
`plan.py` thiếu, tức là bác vì nó không giải bài toán đang mở.

**B. Mỗi tool phải xin người trực duyệt.** An toàn nhất trên giấy. Bác vì mọi
tool đều chỉ-đọc: đây là bắt người ta duyệt một việc không thể gây hại, và thói
quen bấm bừa hình thành trong tuần đầu — rồi cái nút đó vô dụng đúng ngày module
C cho nó ý nghĩa.

**C. Bỏ hẳn `plan.py` sau khi có vòng lặp.** Bớt được một đường code. Bác vì đó
đúng là thứ I4 cấm: hệ thống sẽ chỉ trả lời được khi có key.

**D. Lưu key plaintext, chỉ chặn ở tầng API.** Đơn giản, không mất gì khi quên
`BI_SECRET_KEY`. Bác vì bản sao file SQLite — một bản backup, một support bundle,
một laptop mang ra khỏi trạm — là đường rò key phổ biến và đóng được.

**E. Không lưu key, mỗi lần khởi động nhập lại.** An toàn nhất. Bác vì trạm không
người trực: restart là mất trợ lý cho tới khi có người tới nhập.

## Hệ quả

- `agent/loop.py` mới. `agent/plan.py`, `agent/brief.py` **không đổi** — chúng là
  cái sàn, và sàn không đổi khi thêm tầng.
- `Tool` thêm `parameters` (JSON Schema). `check.py` mục 3 nay đòi **cả**
  `requires=` **lẫn** `parameters=`: một tool không khai schema là tool mô hình
  được kể tên nhưng không gọi nổi.
- Migration `004_assistant.sql`; `cryptography` thành dependency **trực tiếp**
  (đã có sẵn qua asyncua — dựa vào dependency bắc cầu cho một biện pháp bảo mật
  là cách biện pháp đó biến mất trong một lần nâng cấp không liên quan).
- `BI_SECRET_KEY` mới trong `config.py`.
- Quyền thứ 20: `assistant.config`.
- 8 test mới cho vòng lặp, **tất cả không có mô hình thật** — `PlanningProvider`
  là một danh sách quyết định, vì điều đang kiểm là vòng lặp làm gì với một quyết
  định, không phải mô hình quyết định thế nào.
- **Còn nợ, cố ý**: câu trả lời cuối không chảy từng chữ (§4); `OpenAIProvider`
  vẫn **chưa gọi mạng lần nào** — món nợ này có từ ADR-0019 và nay đã có nút
  «Thử kết nối» để trả nó.

## Nguồn

- Người phụ trách sản phẩm, 2026-08-07 — ba câu trích ở phần Bối cảnh
- [ADR-0019 §2](0019-agent-shape.md) — điều kiện xét lại, viết 2026-08-07
- `backend/tests/unit/test_agent.py` — 53 test, không mô hình nào
- `backend/tests/unit/test_assistant_config.py` — key không rời khỏi API
