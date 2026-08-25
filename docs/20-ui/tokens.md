# Design tokens — chrome, station, system

> **Nguồn theme:** [frontend/DESIGN.md](../../frontend/DESIGN.md) (Linear-dark, dense ops).
> **Hiện thực:** [frontend/src/styles.css](../../frontend/src/styles.css).
> **Component UI:** shadcn-vue — chỉ map token, không copy layout marketing.

---

## Luật UI — shadcn + Tailwind (bắt buộc)

**Đã cài:** Tailwind CSS v4 (`@tailwindcss/vite`) + shadcn-vue (`frontend/components.json`).

Mọi thay đổi giao diện sau 2026-08-10:

1. **Chrome** (header, pane, form, bảng, chat) → component **shadcn** trong `src/ui/`:
   `Button`, `Input`, `Card`, `Tabs`, `Table`, `Alert`, …
2. **Styling** → utility **Tailwind** từ token theme (`bg-card`, `text-muted-foreground`, …).
3. **Cấm** trong `features/`: hex màu, `<button>`/`<input>` styled tay, scoped CSS màu mới,
   copy layout marketing từ `DESIGN.md`.
4. **Thiếu component** → `npx shadcn-vue@latest add <name>` trước khi viết HTML mới.
5. **Wrapper domain** (`ValueCell`, `EvidenceBlock`, `SysBadge`, `PaneSkeleton`) — chỉ khi
   shadcn không có API phù hợp hoặc luật an toàn (I2, I3, ADR-0014 §2).

`tools/check.py` mục 5 gác: hex thô trong `features/`, `ui/` không import store.

---
## Ba lớp màu (ADR-0014 §2)

| Lớp | Prefix | Dùng cho | shadcn? |
|---|---|---|---|
| Chrome | `--background`, `--primary`, … | Header, pane, form, bảng | Có |
| Station | `--color-st-*` | SLD, PosSt, mang điện | Không |
| System | `--color-sys-*` | Link, warn, down, idle | Không |

**Luật:** `sys-*` cấm đỏ/xanh lá thiết bị. Chrome không dùng `st-*`.

---

## Chrome — DESIGN.md → shadcn → Tailwind

| DESIGN token | shadcn `:root` | Tailwind utility | Legacy (@deprecated) |
|---|---|---|---|
| canvas `#010102` | `--background` | `bg-background` | `--color-bg`, `bg-bg` |
| surface-1 `#0f1011` | `--card` | `bg-card` | `--color-panel`, `bg-panel` |
| surface-2 `#141516` | `--muted` | `bg-muted` | `--color-panel-2`, `bg-panel-2` |
| ink `#f7f8f8` | `--foreground` | `text-foreground` | `--color-fg`, `text-fg` |
| ink-subtle `#8a8f98` | `--muted-foreground` | `text-muted-foreground` | `--color-dim`, `text-dim` |
| primary `#5e6ad2` | `--primary` | `bg-primary` | `--color-accent`, `bg-accent` |
| on-primary `#ffffff` | `--primary-foreground` | `text-primary-foreground` | — |
| primary-hover `#828fff` | — (hover in Button) | — | — |
| hairline `#23252a` | `--border` | `border-border` | `--color-line`, `border-line` |
| rounded.md `8px` | `--radius` | `rounded-md` | `--radius` |

---

## Station palette (OneATS — không đổi)

| Token | Value | Meaning |
|---|---|---|
| `--color-st-closed` | `#e5484d` | Device CLOSED |
| `--color-st-open` | `#24c07a` | Device OPEN |
| `--color-st-intermediate` | `#f5a524` | INTERMEDIATE |
| `--color-st-undetermined` | `#8b8d98` | quality ≠ GOOD |
| `--color-st-live` | `#4aa3ff` | Conductor energised |
| `--color-st-dead` | `#24c07a` | De-energised |
| `--color-st-earthed` | `#b48ce8` | Earth bond |

Tailwind: `text-st-closed`, `bg-st-live`, …

---

## System palette

| Token | Value | Use |
|---|---|---|
| `--color-sys-ok` | `#8b93a3` | Online (neutral) |
| `--color-sys-warn` | `#f0b429` | Degraded |
| `--color-sys-down` | `#ff5c8a` | Offline / error |
| `--color-sys-idle` | `#5c6474` | Snapshot mode |

Tailwind: `text-sys-down`, `bg-sys-warn`, …

---

## Typography — dense ops

| Token | Size | Use |
|---|---|---|
| `--text-base` | 14px | Body default |
| `--text-sm` | 13px | Pane meta, buttons |
| `--text-xs` | 12px | Caption, table header |
| `--text-lg` | 15px | Section title |
| `--text-xl` | 18px | Page title |

Font: **Inter** 400/500/600 (`@fontsource/inter`). Mono: system stack.

---

## Spacing

4 · 8 · 12 · 16 · 24 · 32 px — Tailwind `p-1` … `p-8` only. No arbitrary values in features.

---

## Elevation (DESIGN)

| Level | Treatment |
|---|---|
| 0 | Flat on canvas |
| 1 | `bg-card` + `border-border` |
| 2 | `bg-muted` + stronger border |
| Focus | `ring-ring` 2px primary-focus |

Pane chrome uses level 1 (`Card`).
