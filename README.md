# Black Interface

Lớp vận hành **AI-first** thay thế HMI tĩnh của OneATS SCADA. Cài **local** trên server
tại trạm điện, đọc realtime từ OneATS DataServer qua OPC UA.

> 🤖 **AI agent (Claude / Codex / Cursor): đọc [`AGENTS.md`](AGENTS.md) trước.**

---

## Hai mục tiêu

1. **Rút ngắn thời gian dựng project** — trỏ vào DataServer là ra HMI chạy được.
   Không vẽ tay, không map point thủ công.
   *Đã đo:* 100% thiết bị đóng cắt auto-bind, 12/12 loại ngăn suy đúng.
2. **Giám sát realtime + phân tích sự cố** — chỉ ra nguyên nhân cụ thể và hướng xử lý,
   kèm evidence.

## Trạng thái

**Giai đoạn 0** — workspace + khảo sát xong, chưa có code sản phẩm.
Việc kế tiếp: [`docs/90-progress/status.md`](docs/90-progress/status.md)

---

## Bắt đầu

```bash
# backend
cd backend
uv sync

# kiểm tra repo
python tools/check.py

# xác minh sự thật đã đo về DataServer (cần DataServer đang chạy)
python tools/verify_dataserver.py

# thăm dò address space
python tools/probe_dataserver.py
python tools/probe_dataserver.py --dump --out sas_tree.json
python tools/probe_dataserver.py --alarms
```

Yêu cầu: Python 3.12 (không phải 3.13), [uv](https://docs.astral.sh/uv/).

---

## Cấu trúc

```
AGENTS.md          ← nguồn sự thật cho mọi AI agent
CLAUDE.md          ← adapter cho Claude Code
.cursor/rules/     ← adapter cho Cursor

docs/
  00-product/      tầm nhìn, phạm vi
  10-architecture/ kiến trúc 6 lớp + ADR (immutable)
  20-domain/       từ điển thuật ngữ, bay template
  30-integration/  SỰ THẬT ĐÃ ĐO về OneATS
  90-progress/     trạng thái, việc kế tiếp   ← đọc đầu phiên, cập nhật cuối phiên

backend/src/blackinterface/
  domain/          L4 Neutral Station Model (không import lớp nào khác)
  integration/     L5 adapters — lớp DUY NHẤT biết NodeId
  diagram/         L6 graph → layout → SVG
  api/             L3 Typed Domain API (FastAPI + SSE)
  agent/           L2 BlackCore (Pydantic AI)
  store/           SQLite: release, snapshot, event store

frontend/          L1 Nuxt (static SPA, FastAPI serve)
tools/             script vận hành/kiểm chứng
document/          tài liệu gốc ATS — CHỈ ĐỌC
```

## Stack

Python 3.12 · uv · FastAPI + SSE · asyncua · SQLite · Pydantic AI ·
Nuxt static SPA · Ollama (trạm) / OpenRouter (dev) · Inno Setup → Windows Service

Không dùng: MongoDB, Postgres, Docker, Redis, Node runtime ở production.
Muốn thêm → phải có ADR.

## Bảy invariants

1. MVP **read-only**, cưỡng chế bằng cấu trúc
2. Không khẳng định trạng thái khi `quality != GOOD`
3. Evidence là typed object do **tool** sinh
4. LLM không nằm trên đường đi của tính đúng đắn
5. Frontend gọi thẳng Domain API; BlackCore không phải proxy
6. Chỉ `integration/` biết NodeId
7. Release immutable, pin theo snapshot + `ModelVersion`

Chi tiết: [`AGENTS.md`](AGENTS.md) §2

---

© ATS JSC — Confidential
