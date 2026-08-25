# Câu hỏi mở — chờ câu trả lời từ ngoài

> **Cập nhật lần cuối**: 2026-08-10
>
> Tách khỏi `status.md` ngày 2026-08-10. **Chỉ chủ dự án sửa file này** —
> mỗi câu hỏi ở đây chặn một việc cụ thể và cần một người ở ATS trả lời,
> không phải một dòng code.

| # | Câu hỏi | Hỏi ai | Chặn việc gì |
|---|---|---|---|
| Q1 | **Định nghĩa struct chính thức của alarm ExtensionObject** (ns=2, TypeId 5803) | Team DataServer, ATS | Việc #3 — hiện đang reverse-engineer, field cuối còn lệch |
| Q2 | ATS đã có thư viện bay template chuẩn EVN chưa? | Nội bộ ATS | ~~Việc #1~~ — đã tự dựng 6 template. Vẫn hữu ích để đối chiếu ở trạm khác |
| Q3 | `IsLive` (thanh cái + ngăn) và `SAS_SIM.CheckLiveState`: OneATS tính thế nào? Vì sao `BB29`/`D12` trả `BadWaitingForInitialData`? | Team DataServer | **Đã tự trả lời phần chính (2026-08-05)**: OneATS suy `<bay>.IsLive` **từ** `Subs.BB*.IsLive` qua Lua `CheckLiveState`. Ta gieo mầm từ thanh cái, tự giải, đối chiếu → **7/7 khớp**. Còn hỏi: vì sao 2 điểm kia hỏng, và mầm của chính thanh cái từ đâu ra |
| Q4 | Có trạm thật thứ 2–3 để verify ADR-0002 + ADR-0008 không? | Nội bộ ATS | **CHẶN** (nâng từ Cao, 2026-08-06) — mã thanh cái theo cấp điện áp và quy ước LN mới đo trên **1 trạm**; cả 6/6 template đều `observed_on: DEMO_SAS v654`. ADR-0015 đứng hay đổ tuỳ câu này: trạm thứ hai ra 12/12 thì trình soạn template là chuyện quy mô, ra một nửa `UNKNOWN` thì là việc gấp. **Phép thử rẻ nhất và quyết định nhất của cả dự án** — chỉ cần một dump, `tools/probe_dataserver.py --dump` đã có sẵn |
| Q4b | Quy ước đánh số LN (`XSWI1`=dao thanh cái 1, `XSWI7`=dao đường dây…) là **chuẩn cố định** của OneATS cho mọi project, hay **cấu hình được** lúc dựng bằng Grid Designer? | Team DataServer / Grid Designer, ATS | **CHẶN** cùng Q4. Nếu đặt tự do thì `infer_bay_type()` sập ở trạm sau và toàn bộ M1 phải nghĩ lại. Có thể `document/UserManual/OneATS_UserManual_Chapter-F_OneATS-GridStudio.pdf` đã trả lời — **chưa đọc** |
| Q5 | Account read-only trên DataServer: xin ở đâu? | Team vận hành | Invariant I1 khi triển khai thật |
| Q8 | **ATS đã có hệ thống tài khoản người dùng để liên thông chưa?** (2026-08-06) | Nội bộ ATS | ADR-0016 chốt lưu tài khoản ở SQLite cục bộ + `external_id` để móc sang nguồn ngoài. Trả lời sớm thì `external_id` trỏ đúng chỗ ngay lần đầu; trả lời muộn thì có giai đoạn **hai nơi cấp quyền**, người nghỉ việc phải xoá hai chỗ |
| Q6 | **Dao tiếp địa nối vào node nào?** `-75/-76` quanh `-7`, `-35/-38` quanh `-3`, `-94/-95` quanh `-9` | Team thiết kế / bản vẽ Grid Designer | Đang đọc từ ảnh chụp SLD, **chưa chứng minh**. Không ảnh hưởng energization, nhưng ảnh hưởng câu hỏi an toàn ("đoạn này đã tiếp địa chưa") ở module #2+ |
| Q7 | **Thang đo của số đo là gì?** DataServer không công bố `EngineeringUnits`/`EURange` trên bất kỳ measurand nào (đã kiểm từng biến, 2026-08-06). `Vlin` = 221.08 — V hay kV? `totW` = 87.43 — W hay MW? | Team DataServer, ATS | Hiện **không in đơn vị** cho áp/dòng/công suất, chỉ in số + tên đại lượng, và gắn `LimitCode.UNIT_UNVERIFIED`. Chặn việc hiện đơn vị đúng trên UI và mọi câu agent nói về độ lớn |

