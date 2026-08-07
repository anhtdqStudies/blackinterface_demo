# ADR-0010 — Scope + facet là trục địa chỉ hoá của toàn hệ

- **Status**: Accepted
- **Date**: 2026-08-05

## Bối cảnh

`document/@Station_UseCases 1.xlsx` liệt kê **30 use case** trên 6 module
(A Monitoring · B Alarm/Event · C Control · D Trend · E Report · F Knowledge).
Người viết file đã xác nhận: đây là **ví dụ về loại việc người dùng muốn giải
quyết**, không phải khuôn mẫu cố định để code theo từng dòng.

Cách làm ngây thơ là mỗi use case một endpoint, một panel, một tool cho agent.
Đọc kỹ bảng thì thấy ngay vì sao cách đó sai:

| Use case | Prompt | Khác nhau ở đâu |
|---|---|---|
| A-01 Station Summary | *"Tóm tắt tình trạng trạm"* | phạm vi = trạm |
| A-02 Bay Overview | *"Tình trạng ngăn lộ 271"* | phạm vi = ngăn |
| A-03 Equipment Status | *"MBA AT1 thế nào?"* | phạm vi = thiết bị |

Ba use case, **một hàm**. Tương tự A-04 / B-01 / B-02 / B-03 đều là *liệt kê
alarm*, chỉ khác bộ lọc và phạm vi.

Làm theo use case → 30 endpoint + 30 panel + 30 tool, và use case thứ 31 phải
sửa ba chỗ. Đó chính là kiểu phình mà dự án này muốn tránh.

## Quyết định

Mọi thứ trong hệ được địa chỉ hoá bằng **hai trục vuông góc**: `scope` và `facet`.

### Scope — danh từ

Một chuỗi ổn định, có kiểu, sinh và phân giải trong `domain/scope.py`:

```
station              vl:220kV             busbar:BB21
bay:D03              device:D03.XCBR1     point:D03.XCBR1.PosSt
```

Chuỗi này là **một khái niệm dùng ở bốn nơi**, không phải bốn khái niệm giống nhau:

| Dùng ở | Ví dụ |
|---|---|
| URL frontend | `#/ops/bay:D03?facet=alarm` |
| Tham số tool của agent | `summary(scope="bay:D03")` |
| Khoá của pane trong workspace | `{kind:'measurements', scope:'bay:D03'}` |
| Chủ thể của `EvidenceRecord` | `subject="bay:D03"` |

**Luật kèm theo — LLM không bao giờ tự sinh scope ref.** Người dùng nói theo số
hiệu EVN (*"271"*, *"MC 231"*, *"thanh cái C21"*); một resolver **deterministic**
(`agent/resolve.py`) đổi tên đó thành scope ref. Không phân giải được thì báo
không tìm thấy — **cấm đoán**. Đây là hệ quả trực tiếp của ADR-0005.

### Facet — họ dữ liệu

Mỗi facet là một module cùng một hình dạng:

```python
def read(scope: ScopeRef, window: TimeWindow | None) -> tuple[Payload, EvidenceRecord]
```

| Facet | Nguồn | Trạng thái |
|---|---|---|
| `state` | `XCBR/XSWI.PosSt` | có |
| `energization` | `domain/energization.py` | có |
| `measurement` | `MMXU1`, `YLTC.TapPos`, `Subs.BB*.PPVMax/Hz` | chưa |
| `alarm` | `OAAlarm.GetActiveAlarm` + event store | chưa |
| `tagging` | `*.Tagging` | chưa |
| `authority` | Local/Remote | chưa |
| `history` | historian (nguồn chưa chốt) | chưa |
| `comms` | Gateway / LAN / IED | chưa |
| `document` | manual, quy trình thao tác | chưa |

### Hệ quả trên API: ~7 endpoint cho 30 use case

```
GET /api/summary?scope=…                       gộp mọi facet có cho scope đó
GET /api/alarms?scope=…&from=&to=&severity=&category=&limit=
GET /api/history?scope=point:…&from=&to=
GET /api/interlock?scope=device:…
GET /api/comms?scope=…
GET /api/knowledge?q=…
GET /api/report?kind=&from=&to=
```

Các endpoint đang có — `/api/station`, `/api/bays`, `/api/diagram`, `/api/live`,
`/api/energization` — **giữ nguyên**. Chúng là *bản đồ và hình học*, nằm trên
trục khác với facet. Không đập thứ đang chạy.

### Hệ quả trên agent: 7 tool, không hơn

Tool registry của BlackCore là lớp bọc mỏng có kiểu trên đúng các endpoint trên
(invariant I5 — agent dùng cùng API với UI, không có đường riêng).

> **Thước đo có thể kiểm tra**: thêm use case mà phải thêm tool → thiết kế đã sai
> ở đâu đó. Thêm use case đúng cách là thêm một bộ lọc hoặc một scope.

## Phương án đã bác bỏ

### A. Mỗi use case một endpoint (`/api/station-summary`, `/api/bay-overview`, …)
Ánh xạ 1-1 với file use case nên đọc rất thuận. **Bác bỏ**: 30 endpoint cho ~7
hành vi thật, logic trùng lặp giữa A-01 và A-02, và mỗi use case mới chạm 3 lớp.

### B. Một endpoint tổng `/api/query` nhận câu hỏi tự do
Gọn nhất về số lượng. **Bác bỏ** vì phá hợp đồng OpenAPI → `schema.d.ts` mất kiểu
→ mất đúng thứ mà ADR-0009 gọi là "lý do kỹ thuật quan trọng nhất". Payload trở
thành `unknown`, frontend hết được máy cưỡng chế.

### C. Để LLM tự lắp ghép từ point thô
Linh hoạt nhất. **Bác bỏ** — đặt LLM lên đường đi của tính đúng đắn, trái ADR-0005,
và không test được nếu không có LLM.

### D. Dùng NodeId làm scope ref
Có sẵn, unique. **Bác bỏ** — vi phạm I6 (chỉ `integration/` được biết NodeId) và
I7 (NodeId đổi khi project OneATS recompile, không bao giờ là primary key).

## Hệ quả

**Tích cực**

- Thêm use case thường là thêm **tham số lọc**, không phải thêm lớp.
- Thêm facet = 1 module + 1 endpoint + 1 component, cả ba đều độc lập nhau.
- URL, tool, pane, evidence dùng chung một hệ danh từ → chat, click sơ đồ và
  danh sách alarm cùng một cơ chế chọn, không phải ba cơ chế song song.
- Test được từng facet riêng, không cần LLM.

**Tiêu cực**

- Trừu tượng thêm một lớp so với "mỗi màn hình một endpoint" — người mới đọc
  code phải nắm khái niệm scope trước.
- `/api/summary` trả một tài liệu ghép nhiều facet → schema rộng hơn, phải cẩn
  thận để không thành cái túi đựng tạp nham. Ràng buộc: **mỗi field của summary
  phải thuộc về đúng một facet đã khai báo**, không có field mồ côi.
- Resolver tên EVN → scope là một điểm hỏng mới, phải có test riêng cho nó.

**Việc phải làm để ADR này không mục**

- `domain/scope.py` là **nơi duy nhất** parse/format scope ref. Không nơi nào
  ghép chuỗi `f"bay:{id}"` bằng tay.
- 30 dòng của file use case trở thành **bộ đề kiểm tra độ phủ**: nếu bộ tool trả
  lời được cả 30 thì bộ tool đủ. Ghi lại thành checklist trong `docs/40-testing/`.
