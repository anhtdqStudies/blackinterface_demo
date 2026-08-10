# ADR-0022 — Trí nhớ hội thoại: mô hình thấy lời, không thấy số

- **Status**: Accepted
- **Date**: 2026-08-10
- **Supersedes**: [ADR-0019](0019-agent-shape.md) **§8** ở đúng một câu — *«hội
  thoại mất khi khởi động lại; bản SQLite làm cùng module B»*. Hình dạng
  (`Conversations` protocol + hiện thực do `api/` tiêm vào) **giữ nguyên**, chỉ
  đổi thời điểm và bổ sung ba thứ ADR-0019 chưa nói tới: mô hình có được đọc
  lịch sử không, transcript sống ở đâu, và một người có bao nhiêu hội thoại.
- **Không đụng tới**: [ADR-0021](0021-agent-harness.md) — vòng lặp, ngân sách,
  digest, cổng duyệt không đổi một dòng.

## Bối cảnh

Ngày 2026-08-10, sau khi người phụ trách sản phẩm chạy được agent với model
thật, câu hỏi đầu tiên là:

> «thế hoàn thành phần memory cho hệ thống, hiện tại cũng chưa làm theo
> conversation, thấy tất cả chỉ là 1 session thì phải?»

Đúng, và đúng cả ba tầng — đây là ba lỗ khác nhau bị gộp thành một triệu chứng:

| Tầng | Hiện trạng trước ADR này |
|---|---|
| Mô hình có nhớ câu trước? | **Không.** `core.py` truyền `message_history=None`. `Conversation.history()` viết từ 2026-08-07 và **chưa ai gọi một lần nào** |
| Có nhiều hội thoại? | **Không.** Frontend giữ đúng một `conversationId`; không danh sách, không mở lại được cái cũ |
| Sống qua restart? | **Không.** `InMemoryConversations` là một `OrderedDict` trong process |

Lỗ thứ nhất là lỗ đắt nhất và rẻ nhất cùng lúc: nó làm hỏng đúng thứ mà cả
`session.py` sinh ra để phục vụ — câu hỏi nối tiếp. *«Còn số đo thì sao?»* hiện
chạy được, nhưng **không phải nhờ trí nhớ**: nó chạy nhờ gợi ý scope của pane
bơm vào prompt. Bỏ gợi ý đó đi thì không còn gì. Và *«so với cái vừa rồi thì
sao?»* trượt hoàn toàn.

## Quyết định

### 1. Mô hình đọc **lời**, không đọc **số**

`message_history` chỉ mang các cặp `(câu hỏi, văn xuôi đã trả lời)`. **Không**
mang lại tool call, tool result, digest, evidence hay bất cứ con số nào của lượt
trước.

Đây là quyết định trọng tâm của ADR này, và lý do là an toàn chứ không phải ngân
sách. Một trạm biến áp **đổi trạng thái trong lúc người ta đang nói chuyện về
nó**. Nếu lượt 5 còn nhìn thấy `271 CLOSED` mà tool trả về ở lượt 1, thì con
đường ngắn nhất để trả lời lượt 5 là đọc lại trí nhớ thay vì gọi tool — và mô
hình sẽ đi con đường ngắn nhất. Kết quả là một câu khẳng định về vị trí máy cắt,
trôi chảy, đúng-lúc-mười-phút-trước, và **không có gì trên màn hình nói rằng nó
cũ**. Đó là I2 bị phá từ một hướng mà I2 không nhìn thấy: quality của điểm vẫn
GOOD, timestamp vẫn mới, chỉ có điều con số không đến từ lần đọc này.

Hệ quả cưỡng chế được, và đây là chỗ quyết định này tự bảo vệ mình:
**`ctx.seen` không thừa kế từ lịch sử.** Mỗi lượt bắt đầu với đúng một ref —
scope của pane. Mô hình nhớ *«lượt trước ta đang nói về ngăn Bến Cát»* thì vẫn
phải gọi `resolve` lần nữa trước khi `summary` chịu chạy (`ModelRetry` trong
`tools/station.py`). Trí nhớ giúp nó **hiểu câu hỏi**; nó không bao giờ được
dùng để **trả lời**.

Trần: **4 lượt gần nhất có văn xuôi** (`llm_history_turns`, mặc định 4). Lượt
không có văn xuôi bị bỏ — một message assistant rỗng dạy mô hình rằng trả lời
rỗng là chấp nhận được.

### 2. Transcript nằm trong SQLite, và chỉ có lời

Bảng `conversations` + `conversation_turns` (migration `005`). Một lượt lưu:
`question`, `answer` (văn xuôi), `scope` đã chốt, `asked_from`, `asked_at`.

**Không lưu evidence, không lưu payload `summary`.** Một `EvidenceRecord` là
phát biểu về **một khoảnh khắc**; đọc lại nó ba ngày sau, cạnh một câu hỏi, dưới
một tiêu đề hội thoại, là mời người ta đọc số cũ như số đang sống. Transcript mở
lại vì thế hiện **câu hỏi + văn xuôi + dấu thời gian**, và nói thẳng đó là lịch
sử. Muốn số hiện tại thì hỏi lại — rẻ, và luôn đúng.

Đây cũng là lý do transcript **không phải** audit log. Audit là `control/audit.py`,
chỉ-append, cho hành động. Hội thoại là thứ để cuộn lại, và xoá được.

`agent/` không import được `store/` (`check.py` mục 2), nên hiện thực SQLite nằm
ở `api/conversations.py` và được tiêm vào qua `deps.py` — đúng đường nối mà
ADR-0019 §8 đã chừa sẵn, nay được dùng.

### 3. Hội thoại thuộc về người mở nó

Giữ nguyên luật của `session.py`: hỏi tiếp id của người khác **không lỗi và
không cảnh báo**, nó âm thầm mở một hội thoại mới. Báo lỗi là xác nhận id đó tồn
tại.

Áp thêm cho ba endpoint mới: `GET /api/conversations` chỉ liệt kê của chính
người gọi; `GET /api/conversations/{id}` và `DELETE` của người khác trả **404,
không phải 403** — cùng một lý do.

Trần: **50 hội thoại mỗi người**, cũ nhất rơi trước; **40 lượt mỗi hội thoại**.

### 4. Tiêu đề suy ra, không hỏi

Tiêu đề là câu hỏi đầu tiên, cắt ở 80 ký tự. Bắt người trực đặt tên cho một
luồng trước khi biết nó sẽ đi tới đâu là một ô nhập không ai điền.

## Phương án đã bác bỏ

**A. Truyền cả `ModelMessage` đầy đủ của Pydantic AI, gồm tool call và tool
result.** Đây là cách dùng mặc định của thư viện và là thứ mọi harness chat làm.
Bác vì §1: nó đặt số đo của mười phút trước vào context như thể là số của bây
giờ, và không tầng nào phía dưới phân biệt được. Nó cũng đốt ngân sách đúng vào
chỗ `digest.py` vừa dọn — bốn lượt × 715 token là 2.860 token tool result **đã
hết hạn**, cho một lượt có trần 24k.

**B. Không có trí nhớ, chỉ mở rộng gợi ý scope trong prompt.** Rẻ hơn, và giữ
nguyên tính chất «mỗi lượt độc lập» vốn dễ suy luận. Bác vì nó không giải được
lớp câu hỏi mà con người thật sự hỏi: *«so với lúc nãy?»*, *«thế còn cái kia?»*,
*«tại sao anh nói vậy?»*. Đó không phải tiện nghi — trạm ít người là nơi người
ta hỏi dồn.

**C. Tóm tắt hội thoại bằng chính mô hình (compaction) khi vượt trần.** Đúng
hướng và sẽ cần khi danh mục tool lớn lên. Bác **bây giờ** vì với 4 lượt văn xuôi
thì chưa có gì để nén, và một bản tóm tắt do mô hình viết là đúng thứ I3 nói
không được tin. Xét lại khi `llm_history_turns` phải vượt quá ~10.

**D. Lưu transcript kèm evidence để «xem lại được đầy đủ».** Bác vì §2. Nếu sau
này cần xem lại một lượt kèm bằng chứng thì thứ phải làm là **pin evidence theo
`turn_id` vào một store riêng có nhãn thời gian rõ ràng**, không phải làm cho
transcript trông giống màn hình đang sống.

## Hệ quả

- `agent/core.py` truyền `message_history` — đường duy nhất mô hình biết quá khứ.
- `ctx.seen` **cố ý không** thừa kế. Câu nối tiếp vẫn tốn một lần `resolve`, và
  đó là cái giá của việc mọi con số đều đến từ lần đọc này.
- Transcript trên đĩa ở trạm. Ai đọc được file SQLite thì đọc được câu hỏi và câu
  trả lời — **không** đọc được số đo, vì số đo không nằm đó. Ghi vào
  `store/secrets.py`-style docstring của repository.
- Mở lại hội thoại cũ hiện lịch sử **không có khối bằng chứng**. Giao diện phải
  nói rõ điều đó, nếu không nó trông như bằng chứng bị mất.
- `llm_history_turns` vào `config.py` — cùng nhóm với năm trần của ADR-0021 §5.
- Thước đo xét lại ADR này: ngày ai đó muốn agent trả lời một câu **chỉ bằng**
  lịch sử mà không gọi tool nào. Nếu điều đó thành mong muốn hợp lý thì §1 phải
  được viết lại, không phải bị lách.
