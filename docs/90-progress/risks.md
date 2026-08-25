# Nợ kỹ thuật và rủi ro đã biết

> **Cập nhật lần cuối**: 2026-08-10
>
> Tách khỏi `status.md` ngày 2026-08-10. Thêm dòng thì kèm ngày và mức.

| Rủi ro | Mức | Ghi chú |
|---|---|---|
| Struct alarm reverse-engineered, chưa có spec chính thức | **Cao** | Q1. ATS đổi format là vỡ |
| Kết luận "không cần SLD" mới đo trên 1 trạm (`DEMO_SAS`) | **Cao** | Q4. Trạm khác có thể lệch quy ước đặt tên |
| Mã thanh cái theo cấp điện áp: 22kV/35kV/500kV là **GIẢ ĐỊNH** | Trung bình | `topology.py: VOLTAGE_BUSBAR_CODE`. Sai thì sinh placeholder + cảnh báo, không im lặng |
| `tools/` chạy bằng python hệ thống, backend chạy trong venv → lệch bản asyncua | Thấp | Đã xử lý `StatusCode` vs `StatusCode_`. Chạy tools qua `uv run` nếu cần chắc |
| Điểm Modbus/DNP không theo quy ước 61850 → không auto-bind được | Trung bình | Trạm pha trộn sẽ có tỷ lệ thủ công cao hơn |
| Endpoint DataServer không bảo mật (None + Anonymous) | **Cao** | Tồn tại độc lập với Black Interface; phải báo team vận hành |
| CPU-only tại trạm → LLM chậm | Trung bình | ADR-0006. Giảm nhẹ: câu trả lời ngắn + structured view |
| SQLite ghi đồng thời (event store + reader) | Thấp | Bật WAL, tách connection đọc/ghi |
| Git chưa có remote — chỉ tồn tại trên máy này | **Cao** *(nâng 2026-08-10)* | Nâng mức vì lô 2026-08-07..10 (ADR-0020/0021/0022, `harness.py`, `digest.py`) đã commit nhưng vẫn chỉ nằm trên một ổ cứng trong OneDrive. Ổ hỏng là mất cả dự án. **Việc U2 của chủ dự án** |
| `.venv` trong OneDrive bị khoá lúc `uv sync` | Thấp | Đã set `link-mode = "copy"`; `check.py` tự retry 1 lần |
| **Đóng gói/triển khai hoãn tới sau demo** *(2026-08-10)* | **Cao** | Inno Setup, Windows Service, embedded CPython, vendor wheel air-gapped, vLLM tại trạm — **0 dòng code, chưa ai sở hữu**. Demo nội bộ chạy từ source nên hoãn được, nhưng ngày có khách thật đây là workstream **3–4 tuần**. Quyết định ở [ADR-0023](../10-architecture/adr/0023-team-delivery-architecture.md) phần phương án đã bác bỏ |
| **Cổng chứng minh của ADR-0015 không chạy được trên trạm không có `IsLive`** *(2026-08-10)* | **Cao** | T220PHOCAO không có `IsLive` ở đâu. Engineer sửa template ở đó thì **không có cách nào bác bỏ template sai** — mở đúng cái cửa ADR-0002/0003 đóng lại. Phải giải **trước khi** code trình soạn (việc B6) |
| **Chủ dự án ôm hai vị trí hub** *(2026-08-10)* | Trung bình | `harness.py` (mọi tool đi qua) + `frontend/` (mọi tính năng hiện ra). Giữ hai hợp đồng `register()` và `openapi.json` sạch thì không thành nút cổ chai; buông một trong hai thì cả hai dev đứng |
| **Trạm demo có thể không có dữ liệu trường** *(2026-08-10)* | Trung bình | Chưa chốt demo chạy trên trạm nào. Không có dữ liệu trường thì sơ đồ toàn xám và `trace` không có gì để nói. **Trả lời trong tuần 1** |

