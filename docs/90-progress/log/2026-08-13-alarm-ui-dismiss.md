# 2026-08-13 — Alarm UI split + incident dismiss/history

## Đã xong

### Backend
- `store/migrations/006_incident_dismissals.sql` — lưu snapshot sự cố khi operator ấn Done (SQLite, không ack OneATS)
- `store/incident_dismissals.py` — repository
- `GET /api/incidents?status=open|dismissed` — mở vs lịch sử
- `POST /api/incidents/{id}/dismiss` — cần `ALARM_ACK`, ghi local only (I1)
- `api/alarms.py` — lọc dismissed khỏi open; history theo scope
- Tests: `test_alarms_api.py`, allowlist `test_api.py`

### Frontend
- Tab **Alarm** (`alarm-list`) — bảng `/api/alarms`, filter klass/search, toggle status/config
- Tab **Sự cố** (`alarms`) — chỉ incident mở; nút **Done**
- Sub-tab **Đã xử lý** trong Alarm — history từ `status=dismissed`
- Badge tab Sự cố = số incident mở (không đếm dismissed)

## Cách thử lại

```bash
cd frontend && npm run build
cd backend && BI_SOURCE=opcua BI_AUTH=env BI_ROLE=operator \
  uv run uvicorn blackinterface.api.app:app --port 8080
```

1. Tab **Alarm** → bảng alarm, filter, sub-tab **Đã xử lý**
2. Tab **Sự cố** → trống khi bình thường; có thẻ khi có fault
3. Ấn **Done** → biến mất khỏi Sự cố, xuất hiện trong Alarm → Đã xử lý

API:
```bash
curl "http://127.0.0.1:8080/api/incidents?scope=station&status=dismissed"
curl -X POST "http://127.0.0.1:8080/api/incidents/{id}/dismiss?scope=station"
```

## Đo / verify

```bash
python tools/check.py   # xanh 2026-08-13
cd backend && uv run pytest tests/unit/test_alarms_api.py -q
```

## Việc kế tiếp

- ADR-0024 `trace` — block chuẩn đoán nhân quả trên thẻ sự cố
- `store/events.py` — SOE persist (alarm history trên trạm vẫn mất khi tắt app)
