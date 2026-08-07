# ADR-0011 — Một đường ghi duy nhất qua `control/`; agent không bao giờ có tool ghi

- **Status**: Accepted
- **Date**: 2026-08-05
- **Sửa đổi**: invariant **I1** trong `AGENTS.md` và §Phạm vi MVP trong
  `docs/00-product/vision.md`. Không supersede ADR nào — ADR-0005 (*AI không được
  ghi OPC UA, không được điều khiển*) được **giữ nguyên và tăng cường**.

## Bối cảnh

Invariant I1 hiện nay là: *"MVP là READ-ONLY. Cưỡng chế bằng cấu trúc, không bằng
prompt."* Nó được `tools/check.py` gác cơ học (quét mọi lời gọi tới bề mặt ghi) và
`test_no_write_endpoint_exists` khoá lại. Đã kiểm chứng là bắt được vi phạm thật.

`document/@Station_UseCases 1.xlsx` có **module C — Control**, trong đó hai use
case được đánh dấu MVP:

- `C-09 Control Execution` — *"Điều khiển đóng/mở MC, tăng/giảm nấc MBA"*
- `C-07 Tagging Set` — *"Đặt biển báo cấm thao tác cho MC 271"*

Cả hai là **ghi**. Người dùng đã xác nhận (2026-08-05): **module C nằm trong MVP,
nhưng làm sau cùng** — các module dễ trước.

Đây là tình huống tệ nhất cho kiến trúc nếu xử lý sai:

- Thiết kế như thể chỉ-đọc-mãi-mãi → tới lúc làm C phải đập.
- Mở đường ghi ngay bây giờ → mất bảo vệ cơ học suốt nhiều tháng, trong khi
  chưa một dòng code nào của C được viết.

Ghi chú an toàn có thật, đã đo được: endpoint DataServer hiện dùng
`SecurityPolicy None` + `Anonymous`, và `PosCtl` **gọi được tự do**
(`docs/30-integration/oneats-dataserver.md`, đo 2026-08-04). Bảo vệ duy nhất đang
tồn tại lúc này là kỷ luật của chính repo này.

## Quyết định

### 1. I1 đổi hình, không mất răng

I1 được phát biểu lại thành:

> **Không module nào ngoài `control/` được chạm bề mặt ghi của OneATS.**
> `control/registry.py` **rỗng** cho tới khi có một ADR riêng mở từng lệnh một.

`tools/check.py` đổi luật quét, **không** bỏ luật:

| Trước | Sau |
|---|---|
| cấm lời gọi ghi ở **mọi nơi** | cấm lời gọi ghi ở **mọi nơi trừ `control/`** |
| — | thêm: khẳng định `control/registry.py` rỗng |
| — | thêm: cấm `agent/` import `control/` |

### 2. Lớp `control/` — hình dạng chốt ngay, nội dung để sau

```
backend/src/blackinterface/control/
  registry.py   danh sách lệnh được phép — MVP: RỖNG
  guard.py      tiền điều kiện, chạy TRƯỚC mọi lệnh:
                  interlock · tagging · authority (Local/Remote) · quality
  audit.py      nhật ký thao tác, append-only, không sửa được
```

Không lệnh nào đi vòng qua `guard`. `guard` là deterministic — nó là hiện thực
của C-01 (Interlock Check), thứ **đọc thuần** và làm được ngay từ bây giờ. Nghĩa
là phần khó nhất của module C được xây và kiểm chứng **trước khi** đường ghi mở.

### 3. Agent không có tool ghi. Vĩnh viễn.

Đây là phần quan trọng nhất của ADR này, và nó **chặt hơn** mức I1 cũ yêu cầu.

| Agent **được** | Agent **không được** |
|---|---|
| C-01 kiểm tra interlock | C-07 đặt tagging |
| C-02 đọc quyền điều khiển | C-09 phát lệnh điều khiển |
| C-03 đọc trình tự thao tác | bất kỳ lời gọi nào tới `control/registry` |
| C-04 dựng checklist | |
| C-06 giải thích hậu quả (*"nếu đóng dao tiếp địa thì sao"*) | |
| C-08 đọc trạng thái tagging | |

Toàn bộ cột trái là **đọc**. Nút bấm nằm ở UI, người bấm, có xác nhận tường minh.

> **Agent soạn phiếu, người ký.**

Nhờ đó lập luận bảo mật của I5 còn nguyên **kể cả sau khi module C mở**: về mặt
cấu trúc, AI không làm được gì mà người dùng không tự làm được qua UI. Không phải
tin vào prompt, không phải tin vào guardrail của mô hình.

### 4. Thứ tự thi công không đổi

Module C vẫn ở giai đoạn cuối. ADR này **không mở** đường ghi — nó chỉ khoan sẵn
lỗ, để lúc mở không phải đập tường.

## Phương án đã bác bỏ

### A. Giữ nguyên I1 "MVP read-only", tính sau
Đơn giản nhất hôm nay. **Bác bỏ**: người dùng đã chốt C thuộc MVP. Thiết kế
`api/`, `agent/` và store trong 4 giai đoạn tới mà giả định không bao giờ có ghi
sẽ tạo ra những chỗ phải đập — đúng thứ phiên này được lập ra để tránh.

### B. Mở đường ghi ngay, chỉ dựa vào review con người
**Bác bỏ.** Mất bảo vệ cơ học nhiều tháng để đổi lấy con số không lợi ích —
không dòng code C nào được viết trong thời gian đó. Repo này đã chứng minh giá
trị của cưỡng chế bằng máy; bỏ nó đi là đi lùi.

### C. Cho agent tool ghi, chặn bằng permission trong prompt/policy
Hấp dẫn: *"đóng máy cắt 271 giúp tôi"* chạy được ngay. **Bác bỏ dứt khoát.**
Đặt LLM lên đường đi của một thao tác không đảo ngược được trên thiết bị cao áp.
Prompt injection, hiểu sai scope, hoặc chỉ đơn giản là mô hình phân giải nhầm
"271" sang thiết bị khác — bất kỳ cái nào cũng đủ gây tai nạn. Trái ADR-0005.

### D. Đặt logic ghi rải trong `api/routers/`, cạnh endpoint đọc
Ít file hơn. **Bác bỏ** — mất khả năng quét cơ học. Sức mạnh của I1 nằm đúng ở
chỗ *có một biên giới quét được*.

## Hệ quả

**Tích cực**

- Module C mở được bằng cách **thêm** vào registry, không phải sửa kiến trúc.
- `guard.py` phục vụ hai mục đích: tiền điều kiện cho C-09 **và** hiện thực của
  C-01 — làm được ngay, kiểm chứng được sớm, dùng lại sau.
- Lập luận bảo mật của I5 sống sót qua việc mở đường ghi.
- Biên giới ghi vẫn quét được bằng máy, chỉ đổi vị trí.

**Tiêu cực**

- Thêm một lớp `control/` rỗng suốt nhiều tháng — có vẻ thừa, và người mới đọc
  code sẽ hỏi vì sao. Câu trả lời nằm trong ADR này.
- Luật của `check.py` phức tạp hơn (trừ một thư mục) → chính `check.py` phải có
  test cho luật mới, giống lần trước đã làm với luật cũ.
- Khi mở C sẽ cần thêm: xác thực người thao tác, và quyết định về xác nhận hai
  người. **Cố ý chưa quyết** ở ADR này — chưa đủ thông tin, và quyết sớm là đoán.

**Việc phải làm để ADR này không mục**

- `AGENTS.md` I1 phải viết lại theo phát biểu mới, kèm trỏ về ADR này.
- `vision.md` §Phạm vi MVP: chuyển *"Mọi thao tác điều khiển/ghi"* từ **ngoài
  phạm vi** sang **trong phạm vi, giai đoạn cuối**.
- Mỗi lệnh thêm vào `control/registry.py` phải có ADR riêng nêu rõ: lệnh gì,
  tiền điều kiện nào, ai được bấm, ghi audit ra sao.
