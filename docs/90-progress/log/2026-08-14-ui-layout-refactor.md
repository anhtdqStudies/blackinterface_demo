# 2026-08-14 — UI layout refactor (DSH-inspired)

## Đã xong

- **Chrome phẳng**: `PaneHost` bỏ padding/gap dư; splitter mảnh; `PaneFrame` không bọc Card khi `chrome: minimal`; `Header`/`ChatPane`/`ScopeHeader` bỏ blur và nền lồng.
- **Nav dọc**: `WorkspaceNav.vue` + `workspace-nav.ts` — icon rail thay tab ngang; thu gọn còn 48px; badge alarm/anomaly giữ nguyên.
- **Details rail**: `WorkspaceDetails.vue` — cột trạng thái nhanh khi tab SLD + scope bay/device; kéo splitter; nút ẩn + link mở lại.
- **Tỷ lệ chat**: `OPERATOR_LAYOUT` 30/70 (trước 42/58).
- **Pane polish**: `MeasurementPane`, `EnergizationPane`, `EvidencePane`, `AnomaliesPane` — scope banner + Card, bỏ `Panel`/`text-dim` cũ.
- **i18n**: khối `workspace.*` + `scopeLine` cho measurement/energization/evidence/anomalies (vi + en).
- **Fix check**: `SldPane` fullscreen dùng `var(--background)` thay hex.

File chính: `frontend/src/app/layout/{WorkspaceNav,WorkspaceDetails,WorkspaceTabs,PaneHost,PaneFrame}.vue`, `presets.ts`, `stores/workspace.ts`.

## Cách xem lại

```bash
cd frontend && npm run build
cd ../backend && uv run uvicorn blackinterface.api.app:app --port 8080
```

Mở `#/ops/station?tab=sld`, chọn một ngăn trên sơ đồ → details rail bên phải.

## Việc kế tiếp (tuỳ chọn)

- Command palette (`Cmd+K`) chuyển pane nhanh khi nav dọc dài thêm module B/D.
- ADR ngắn ghi nhận nav dọc (lệch wireframe ADR-0018 tab ngang — cùng mục tiêu, khác presentation).
- Group tab (Giám sát / Sự cố) nếu 8 mục vẫn cảm thấy dài trên màn hình nhỏ.

## Đo lại

```bash
python tools/check.py   # xanh 2026-08-14
cd frontend && npm run check && npm run build
```
