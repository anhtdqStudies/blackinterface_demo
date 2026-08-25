# Trạng thái dự án

> **Cập nhật lần cuối**: 2026-08-10 — chuyển sang chế độ nhiều người (3 người).
>
> **File này chỉ nói hiện tại.** Nó ngắn có chủ đích và **chỉ chủ dự án sửa**,
> mỗi tuần một lần. Lịch sử nằm ở `log/`, câu hỏi ở `questions.md`, rủi ro ở
> `risks.md`. Ai làm gì và luật chống va chạm nằm ở
> [`team.md`](team.md) + [ADR-0023](../10-architecture/adr/0023-team-delivery-architecture.md).

| Muốn biết | Đọc |
|---|---|
| Hiện đang ở đâu, việc kế tiếp | file này |
| Ai sở hữu thư mục nào, làm gì tuần này | [`team.md`](team.md) |
| Mỗi phiên/PR đã làm gì | [`log/`](log/) — mỗi lần một file mới |
| Câu hỏi đang chờ ATS trả lời | [`questions.md`](questions.md) |
| Rủi ro và nợ kỹ thuật | [`risks.md`](risks.md) |
| Toàn bộ tiến độ 04–10/08 | [`log/2026-08-04_10-archive.md`](log/2026-08-04_10-archive.md) |
| Người mới vào dự án | [`docs/00-onboarding.md`](../00-onboarding.md) |

---

## Đang ở đâu

**GĐ 0 · 1 · 1.5 · 2 xong.** `tools/check.py` xanh cả 9 mục (đo 2026-08-10):
418 test backend, mypy strict, hợp đồng OpenAPI khớp, 239 khoá i18n khớp vi/en.

| Mục tiêu | Trạng thái |
|---|---|
| **M1** — trỏ endpoint là ra HMI, không vẽ tay, không map point | ✅ **2 trạm**: DEMO_SAS 13 ngăn/80 thiết bị · T220PHOCAO 23 ngăn/6 thanh cái/2 MBA, phân loại 23/23 |
| **M2** — giám sát realtime + phân tích sự cố có bằng chứng | ⬅ **nửa đầu xong** (module A). Alarm/event, `trace`, khung duyệt: **chưa có dòng nào** |

Đã chạy thật, không phải chỉ build được: energization tự giải đối chiếu `IsLive`
7/7 khớp · subscription 176 monitored item, rejected=0 · agent gọi model thật
qua OpenRouter (2026-08-10) · digest đo bằng `tiktoken` 20.064 → 715 token.

### Trạm thứ hai T220PHOCAO — một cảnh báo phải nhớ

Trạm này **không có dữ liệu trường**: mọi `PosSt` và mọi measurand trả
`BadWaitingForInitialData`, và **không có `IsLive` ở đâu cả**. Sơ đồ dựng đúng
hình nhưng toàn `UNDETERMINED` (xám) — đúng theo I2, không phải lỗi.

Hệ quả, cả hai đều nghiêm trọng:
- Đối chiếu energization **không dùng được** trên trạm này.
- **Cổng chứng minh của ADR-0015 không chạy được ở đây.** Engineer sửa template
  ở một trạm không có dữ liệu trường thì ta không có cách nào bác bỏ template
  sai. Phải giải trước khi code trình soạn template.

---

## ⬅ Việc kế tiếp

Phân công chi tiết ở [`team.md`](team.md). Tóm tắt:

| # | Việc | Ai |
|---|---|---|
| 1 | Remote + CI chặn merge | Dev B |
| 2 | ADR-0024 hợp đồng tool `trace` — **viết trước khi ai code** | Chủ dự án |
| 3 | Trạm thứ 3 + thứ 4 từ simulator riêng của hai dev | Dev A, Dev B |
| 4 | Đọc alarm (`OAAlarm.GetActiveAlarm`) → `domain/alarm.py` → nhịp SSE | Dev B |
| 5 | Event store + facet `/api/alarms` + tool `trace` | Dev A |
| 6 | `AlarmPane` · `TracePane` · banner drift | Chủ dự án |
| 7 | Release pinning (I7) rồi template động (ADR-0015) | Dev B |
| 8 | Eval suite gọi 27B thật, opt-in env, ngoài `check.py` | Chủ dự án |

**Hoãn có chủ ý tới sau demo nội bộ**: đóng gói Inno Setup, Windows Service,
vendor wheel air-gapped, vLLM trên máy trạm. Chạy từ source là đủ cho demo.
Ghi ở `risks.md` để nó không âm thầm biến mất — ngày có khách thật đó là một
workstream 3–4 tuần chưa ai chạm.

---

## Lộ trình giai đoạn (chốt 2026-08-05, còn hiệu lực)

| GĐ | Nội dung | |
|---|---|---|
| 0 | Nền: `scope.py` · `evidence.py` · tách `api/` · shadcn-vue · `control/` rỗng | ✅ |
| 1 | Module A — Monitoring: measurand, nhịp SSE, `/api/summary` + evidence | ✅ |
| 1.5 | Nền UI/UX: workspace nhiều pane, phân quyền, bề mặt engineer | ✅ |
| 2 | Agent lát cắt dọc + ADR-0020/0021/0022 | ✅ |
| **3** | **Module B — Alarm/Event + `trace`** ⟵ *đang ở đây* | ⬅ |
| 2.5 | Trình soạn template + chốt bản (ADR-0015) | song song |
| 4 | Module E (Report) · Module F (Knowledge/RAG) | |
| 5 | Module D (Trend — chờ HIS) · Module C (Control — mở `control/registry.py`) | |

Bản đầy đủ kèm lý do thứ tự: [`log/2026-08-04_10-archive.md`](log/2026-08-04_10-archive.md)
mục *KẾ HOẠCH ĐÃ CHỐT*.

---

## Chạy thử

```bash
cd backend  && uv sync
cd frontend && npm install && npm run build
cd backend  && uv run uvicorn blackinterface.api.app:app --port 8080
# -> http://127.0.0.1:8080
```

Chưa `npm run build` thì API chạy nhưng không có giao diện — cố ý.

**Bật mô hình thật**: sinh `BI_SECRET_KEY` một lần
(`python -c "import secrets; print(secrets.token_urlsafe(32))"`), khởi động với
nó, đăng nhập `engineer` → `#/eng` → khối **Mô hình ngôn ngữ** → endpoint kiểu
OpenAI, model `qwen/qwen3.6-27b`, dán key OpenRouter → **Lưu** → **Thử kết nối**.
Rồi về `#/ops/station?l=chat` hỏi `so sánh 271 với Ben Cat`.
Mất `BI_SECRET_KEY` = mất key đã lưu, phải nhập lại.

**Bỏ qua đăng nhập khi dev**: `BI_AUTH=env BI_ROLE=engineer`.
**Không dùng ở trạm** — nó cấp cùng bộ quyền cho bất kỳ ai chạm tới cổng mạng.

**Tài khoản** (lần chạy đầu tự tạo, mật khẩu `blackinterface`):
`operator` · `supervisor` · `maintenance` · `protection` · `admin` · `engineer` ·
`truc` (operator+supervisor+maintenance, cho trạm ít người).

Kịch bản chạy tay: [`docs/40-testing/`](../40-testing/).

---

## Còn chưa xác minh

- **`llm_count_tokens_before_request` vẫn mặc định TẮT.** Giờ đã có endpoint
  thật để thử — món rẻ nhất còn lại.
- **Lịch sử hội thoại tốn bao nhiêu token: CHƯA ĐO.** Đo bằng `tiktoken` như đã
  làm với `digest`, đừng dùng lại con số ước.
- **Chưa có máy trạm (RTX 5090)** để đo tok/s một lượt — ADR-0021 §7 là GIẢ ĐỊNH.
- **Trạm demo có dữ liệu trường không?** Chưa chốt. Quyết định `trace` được kiểm
  chứng trên dữ liệu nào — phải trả lời trong tuần 1.
