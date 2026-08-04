# ADR-0006 — Stack triển khai local trên server tại trạm

- **Status**: Accepted
- **Date**: 2026-08-04

## Bối cảnh

Sản phẩm **không phải SaaS**. Cài trên **một server vận hành tại trạm điện**,
nhiều người truy cập. Cần đóng gói thành bản cài. OS: Windows
(manual OneATS: Windows Server 2012+ / Windows 10+).

Ràng buộc quyết định nhất: **LLM chạy ở đâu.** Trạm thường air-gapped hoặc chặn
outbound. Giai đoạn test có GPU và tạm dùng OpenRouter; giai đoạn triển khai phải
chạy local được.

## Quyết định

| Thành phần | Chọn | Lý do |
|---|---|---|
| Backend | **Python 3.12** (không 3.13) | ecosystem wheel còn lệch trên 3.13; phải build sạch để đóng installer |
| Dependency | **uv** | lockfile chặt, quản lý cả bản Python, `uv export` → vendor wheels cho cài offline |
| API | **FastAPI** + SSE | |
| OPC UA | **asyncua** | thuần Python, async, đủ nhanh ở quy mô trạm (~18k node, ~vài nghìn point) |
| Frontend | **Nuxt build static (SPA)**, FastAPI serve | bỏ Node khỏi runtime → **một process**, installer gọn |
| Store | **SQLite** cho tất cả | config, release, snapshot, event store. 1 file, zero admin, transactional |
| LLM runtime | **Ollama** đóng gói kèm; OpenRouter cho dev | API OpenAI-compatible → đổi bằng config qua interface `LLMProvider` |
| Model | Qwen2.5 7B/14B Instruct | tool-calling tốt, tiếng Việt khá; đủ vì AI không load-bearing (ADR-0005) |
| Đóng gói | embedded CPython → **Inno Setup** → **Windows Service** | đồng nhất với cách OneATS cài (OAFEP/OADataServer/OAHISServer đều là service) |

### Ràng buộc runtime

- **Một** OPC UA subscription phía server → fan-out SSE cho N client.
  Không tạo subscription theo từng browser.
- Client OPC UA dùng account **read-only** qua `UserName`, **không Anonymous**
  (invariant I1; xem cảnh báo bảo mật `docs/30-integration/oneats-dataserver.md` §9).
- Bind localhost hoặc interface hạn chế, có auth. Không mở port không xác thực
  lên mạng trạm (manual nhắc NERC-CIP / IEC 62351).

## Phương án đã bác bỏ

- **MongoDB** (vì OneATS dùng) — nhân đôi footprint installer, thêm service phải quản,
  trong khi SQLite thừa sức cho quy mô một trạm.
- **PostgreSQL / TimescaleDB** cho time series — cài Postgres trong installer là gánh nặng
  không tương xứng. Nếu sau này volume trend đòi hỏi, cân nhắc DuckDB trước.
- **Docker** — chính sách IT tại trạm, licensing Docker Desktop, và độ tin cậy trên
  Windows Server đều là rủi ro không đáng.
- **Nuxt SSR** — kéo Node runtime vào production mà không đổi lại lợi ích gì
  (không SEO, không đa tenant).
- **Tauri / Electron desktop shell** — server phục vụ nhiều workstation, nên HTTP
  linh hoạt hơn hẳn. Chỉ cân nhắc nếu sau này xác định một máy một người.
- **Python 3.13** — free-threading chưa cần, ecosystem còn lag.

## Hệ quả

**Tích cực**
- Một process, một file DB, một installer. Vận hành tại trạm đơn giản.
- Đổi LLM provider bằng config, không đổi code.
- Chạy được air-gapped.

**Tiêu cực / cần chú ý**
- **CPU-only là rủi ro thật**: 7B q4 trên CPU ~5–15 tok/s — chấp nhận được cho câu
  trả lời ngắn, khó chịu cho câu dài. Hoặc dự trù GPU, hoặc thiết kế câu trả lời ngắn
  và đẩy phần lớn nội dung sang structured view thay vì prose.
- SQLite ghi đồng thời có giới hạn. Với event store ghi liên tục + nhiều reader,
  phải bật WAL mode và tách connection đọc/ghi.
- Đóng gói embedded Python + Ollama làm installer khá nặng. Cần đo và cân nhắc
  tách model ra bản cài riêng.
