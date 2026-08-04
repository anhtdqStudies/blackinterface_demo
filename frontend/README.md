# frontend/ — L1 Black Interface Web

**Vite + Vue 3 + TypeScript.** Xem `docs/10-architecture/adr/0009-frontend-vite-vue.md`
để biết vì sao không dùng Nuxt (ADR-0009 thay phần frontend của ADR-0006).

## Chạy

```bash
npm install

# Phát triển: Vite serve, proxy /api sang backend cổng 8080
npm run dev            # http://localhost:5173

# Đóng gói: FastAPI serve dist/, không cần Node lúc chạy
npm run build          # -> dist/
```

Backend đọc `frontend/dist/`. **Chưa build thì không có giao diện** — cố ý,
xem ADR-0009: một frontend cũ còn sót lại nguy hiểm hơn là không có gì.

Đổi cổng backend khi dev: `BI_API_URL=http://127.0.0.1:8081 npm run dev`

## Type của API là SINH TỰ ĐỘNG

`src/api/schema.d.ts` **không được sửa tay**. Nó sinh từ OpenAPI của backend:

```bash
# 1. backend xuất schema (chạy lại mỗi khi đổi endpoint)
cd backend && uv run python ../tools/export_openapi.py

# 2. frontend sinh type
cd frontend && npm run api:types
```

Bước 1 được `python tools/check.py` kiểm tra: đổi API mà quên xuất thì repo check đỏ.
Bước 2 nằm trong `npm run build`.

Nhờ vậy backend đổi tên field → frontend **lỗi biên dịch**, không phải `undefined`
lúc 2 giờ sáng trong trạm.

## Kiểm tra

```bash
npm run check     # api:types + typecheck + lint + format:check
```

## Cấu trúc

```
src/
  api/
    schema.d.ts     SINH TỰ ĐỘNG - đừng sửa
    client.ts       nơi duy nhất gọi HTTP
  stores/           Pinia - state dùng chung
  components/
    diagram/        SldCanvas, DeviceSymbol, state.ts (bảng màu)
    panels/         CoveragePanel, DevicePanel, IssueList
  views/            StationView, BayView, IssuesView
  router.ts         hash history (lý do ghi trong file)
  styles.css        design token
```

## Quy tắc

**Frontend không suy luận về hệ thống điện.** Mang điện hay không, bám thanh cái
nào, liên động có cho phép không — tất cả tính ở backend (AGENTS.md I4).
Frontend chỉ vẽ. Thấy mình viết logic điện trong `.vue` là đặt sai chỗ.

**Xám không bao giờ được nhầm với xanh lá.** `UNDETERMINED` nghĩa là quality không
GOOD và ta từ chối đoán (I2). Tô nó thành xanh lá là nói "không có điện" — câu
khiến người ta chạm tay vào thiết bị.

**Gọi thẳng Domain API** cho mọi thao tác deterministic. Chỉ gọi BlackCore cho
lượt hội thoại ngôn ngữ tự nhiên (I5). Phải dùng được khi LLM chết.

## Còn thiếu (theo `docs/90-progress/status.md`)

| Màn hình | Trạng thái |
|---|---|
| Sơ đồ trạm + panel thiết bị | ✅ |
| Bay detail, danh sách cảnh báo | ✅ |
| Realtime overlay (SSE) | chưa — module #2 |
| Timeline SOE | chưa — module #3 |
| Evidence panel | chưa — module #4 |
| Chat shell | chưa — module #6 |

Một OPC UA subscription phía server → fan-out SSE cho N client.
Frontend **không** tự tạo kết nối OPC UA.
