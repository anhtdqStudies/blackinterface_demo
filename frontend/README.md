# frontend/ — L1 Black Interface Web

**Vite + Vue 3 + TypeScript + Tailwind CSS v4 + shadcn-vue.** ADR-0009 (Vite), ADR-0014 (UI).

## UI — BẮT BUỘC (đọc trước khi sửa giao diện)

**Tailwind và shadcn đã cài sẵn.** Không thêm CSS framework khác, không tự viết component
chrome từ đầu.

| Việc cần | Làm gì | Cấm |
|---|---|---|
| Nút, input, form | `npx shadcn-vue@latest add …` rồi `import { Button } from '@/ui/button'` | `<button class="…">` tự style, global `button {}` |
| Khung pane, card | `Card`, `CardHeader`, `CardContent` từ `@/ui/card` | `<div class="border … bg-panel">` copy-paste |
| Bảng | `Table` + wrapper `DataTable.vue` | `<table>` + CSS scoped riêng |
| Tab / preset | `Tabs`, `TabsList`, `TabsTrigger` | Segmented control tự viết |
| Màu chrome | Token Tailwind: `bg-background`, `text-muted-foreground`, `border-border` | Hex `#…`, `bg-[#010102]` trong `features/` |
| Màu trạm (SLD) | `st-*` qua `components/diagram/state.ts` | Dùng `st-*` cho link/lỗi phần mềm |
| Màu phần mềm | `sys-*` (`text-sys-down`, …) | Đỏ/xanh lá cho online/offline |
| Theme / spacing | [`DESIGN.md`](DESIGN.md) → [`docs/20-ui/tokens.md`](../docs/20-ui/tokens.md) → `src/styles.css` | Màu/spacing “cho nhanh” trong từng pane |
| Ghép class | `cn()` từ `@/lib/utils` | Chuỗi class template dài, không merge conflict |

**Thứ tự khi thiếu component:** (1) tìm trong `@/ui/*` đã add — (2) `shadcn-vue add`
— (3) wrapper mỏng trong `ui/*.vue` (domain only: `ValueCell`, `EvidenceBlock`, …) —
**(4) không** tạo `<div>` styled trong `features/`.

Chi tiết: [`docs/20-ui/frontend-architecture.md`](../docs/20-ui/frontend-architecture.md) §10,
[`docs/20-ui/tokens.md`](../docs/20-ui/tokens.md).

### Thêm component shadcn

```bash
cd frontend
npx shadcn-vue@latest add dialog sheet   # ví dụ
```

Cấu hình: [`components.json`](components.json) — alias `"ui": "@/ui"`.

### Tailwind v4 (đã cài)

- Plugin: `@tailwindcss/vite` trong [`vite.config.ts`](vite.config.ts)
- Token: `@theme` + shadcn vars trong [`src/styles.css`](src/styles.css)
- **Không** thêm `tailwind.config.js` — cấu hình bằng CSS (ADR-0014)

```bash
cd frontend && npm install   # tailwindcss, @tailwindcss/vite đã trong package.json
```

## Chạy

```bash
npm install
npm run dev            # http://localhost:5173 — proxy /api → :8080
npm run build          # -> dist/ — FastAPI serve khi production
```

Chưa build → không có giao diện (cố ý, ADR-0009).

`BI_API_URL=http://127.0.0.1:8081 npm run dev`

## Type API — sinh tự động

`src/api/schema.d.ts` **không sửa tay**:

```bash
cd backend && uv run python ../tools/export_openapi.py
cd frontend && npm run api:types
```

`python tools/check.py` gác openapi.json; `npm run build` gọi `api:types`.

## Kiểm tra

```bash
npm run check     # api:types + typecheck + lint + format:check
```

## Cấu trúc (2026-08-10)

```
src/
  app/layout/       Shell, Header, PaneHost, presets
  features/         pane theo bề mặt — CHỈ compose ui/, không tự style chrome
  ui/               shadcn CLI (button/, card/, …) + domain wrappers
  components/diagram/   SLD — bảng màu st-*
  api/              client.ts, schema.d.ts (generated)
  stores/           Pinia theo vòng đời
  styles.css        Tailwind @theme + shadcn CSS variables
```

## Quy tắc domain (không đổi)

- Frontend **không suy luận điện** — backend deterministic (I4).
- `UNDETERMINED` ≠ xanh lá “hết điện” (I2).
- Gọi thẳng Domain API; BlackCore chỉ cho hội thoại (I5).
