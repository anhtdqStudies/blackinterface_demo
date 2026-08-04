# CLAUDE.md

**→ Đọc [`AGENTS.md`](./AGENTS.md) trước. Đó là nguồn sự thật duy nhất cho repo này.**

File này chỉ chứa phần riêng của Claude Code. Mọi quy tắc về kiến trúc, invariants,
tech stack, quy trình xuyên phiên đều nằm trong `AGENTS.md` — không nhân bản ở đây
để tránh hai nguồn lệch nhau.

## Riêng cho Claude Code

- **Bắt đầu phiên**: đọc `AGENTS.md` → `docs/90-progress/status.md`.
- **Kết thúc phiên**: cập nhật `docs/90-progress/status.md`. Bắt buộc.
- Về MCP `code-review-graph` (khai báo ở `~/.claude/CLAUDE.md`): repo này còn rất ít
  code nên graph chưa có giá trị. Dùng Read/Glob/Grep trực tiếp cho tới khi
  `backend/src/` có đủ module thật, rồi mới build graph.
- Script thăm dò OPC UA nằm ở `tools/`, chạy được độc lập — đừng viết lại từ đầu
  trong scratchpad.
- Kết nối DataServer thật: `opc.tcp://127.0.0.1:48050` (đang chạy trên máy dev này).
  **Chỉ đọc.** Xem invariant I1 trong `AGENTS.md`.
