# Tài liệu Black Interface

## Bản đồ

| Thư mục | Nội dung | Đọc khi nào |
|---|---|---|
| `00-product/` | Tầm nhìn, phạm vi, vai trò người dùng | Hiểu *vì sao* làm sản phẩm này |
| `10-architecture/` | Kiến trúc 6 lớp, ranh giới, luồng dữ liệu | Thêm module, đổi ranh giới lớp |
| `10-architecture/adr/` | Decision records — **immutable** | Trước khi làm khác một quyết định đã chốt |
| `20-domain/` | Từ điển thuật ngữ, bay template | Gặp thuật ngữ lạ (61850/CIM/EVN) |
| `30-integration/` | **Sự thật đã đo** về OneATS | Động tới OPC UA / DataServer / alarm |
| `90-progress/` | Trạng thái, việc kế tiếp, câu hỏi mở | **Đầu và cuối mỗi phiên** |

## Quy tắc viết tài liệu

### 1. Phân biệt SỰ THẬT ĐÃ ĐO và GIẢ ĐỊNH
Đây là quy tắc quan trọng nhất của dự án này.

- Số liệu về OneATS phải ghi kèm **ngày đo** + **cách đo lại**.
- Chưa đo thì ghi rõ `> ⚠ GIẢ ĐỊNH — chưa xác minh`.
- **Cấm** trích số liệu từ trí nhớ hoặc từ manual PDF như thể đã đo.

Manual có chỗ sai so với hệ chạy thật — đã gặp ba lần
(alarm A&C, tên 61850 lồng nhau, port HIS). Xem `30-integration/oneats-dataserver.md` §10.

### 2. Tiếng Việt, thuật ngữ kỹ thuật giữ tiếng Anh
Không dịch `busbar`, `circuit breaker`, `evidence`, `snapshot`, `logical node`.

### 3. Bảng hơn đoạn văn
Tài liệu này để tra cứu, không để đọc tuần tự.

### 4. ADR là immutable
Đổi ý → ADR mới với `Supersedes: NNNN`. Không sửa ADR cũ.
Luôn ghi **phương án đã bác bỏ + lý do** — phần giá trị nhất, nó ngăn phiên sau
đề xuất lại thứ đã cân nhắc và loại.

## Tài liệu gốc

`document/` (ngoài `docs/`) là tài liệu gốc của ATS — **chỉ đọc, không sửa**:

| Đường dẫn | Nội dung |
|---|---|
| `document/UserManual/*.pdf` | Manual OneATS 8 chương (A Overview → H OneMasterTool) |
| `document/SLD_serviceOut/` | Output service extract SLD bằng computer vision. ⚠ **Có lỗi đã xác nhận** — xem ADR-0002 |
| `document/*.xlsx`, `CMA_SL_v2_2.pdf` | Use case, model explorer |

Đã chắt lọc phần cần thiết vào `docs/`. **Không đọc PDF trừ khi thật sự cần** —
tốn context mà phần lớn không liên quan.
