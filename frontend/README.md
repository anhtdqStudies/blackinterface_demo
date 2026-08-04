# frontend/ — L1 Black Interface Web

**Chưa khởi tạo.** Sẽ dựng ở giai đoạn 6 (`docs/90-progress/status.md`).

## Đã chốt (ADR-0006)

- **Nuxt build static (SPA)**, KHÔNG phải SSR — bỏ Node runtime khỏi production.
  FastAPI serve file tĩnh → một process duy nhất, installer gọn.
- Gọi **thẳng** Domain API cho thao tác deterministic (view, data, SSE).
  Chỉ gọi BlackCore cho lượt hội thoại ngôn ngữ tự nhiên (AGENTS.md I5).
- Phải dùng được khi LLM chết — mất chat, còn nguyên HMI.

## Ba màn hình MVP

| Màn hình | Vai trò |
|---|---|
| Bay-card review | Engineer duyệt topology auto-derive, chỉ chạm chỗ có cảnh báo |
| Operator workspace | Chat + SLD sinh tự động + overlay live + alarm list |
| Evidence panel | Render từ `EvidenceRecord`; prose LLM nằm cạnh, không nằm trong |

## Lưu ý

Một OPC UA subscription phía server → fan-out SSE cho N client.
Frontend **không** tự tạo kết nối OPC UA.
