# 2026-08-13 — Live test alarm / event structure

## Đã xong

- `backend/src/blackinterface/integration/opcua/alarms.py` — decode body ExtensionObject (TypeId 5803), inspect envelope, `GetActiveAlarm`, probe `OAEvent`.
- `backend/tests/integration/test_alarms_live.py` — 4 test live (`pytest -m live`):
  - kết nối DataServer, xác nhận `OAEvent` không có children (không phải OPC UA A&C);
  - gọi `OAAlarm.GetActiveAlarm(/SAS)`, decode 243/243, in cấu trúc;
  - scope theo ngăn (subset ≤ toàn trạm);
  - kiểm tra biên độ body length.

## Đo được (2026-08-13, DEMO_SAS qua `opc.tcp://127.0.0.1:48050`)

```bash
cd backend && uv run pytest -m live tests/integration/test_alarms_live.py -s
```

| Chỉ số | Giá trị |
|---|---|
| Active alarms (SAS) | 243 |
| Decode rate | 243/243 (100%) |
| TypeId | `ns=2;i=5803` (243/243) |
| Categories | Discrete 159, Binary 82, Limit 2 |
| Severity top | 360×150, 200×90, 650×2, 850×1 |
| Body length | 23 giá trị khác nhau, 152–213 byte; cụm 167 byte ×64 |
| OAEvent children | 0 |

`value_text` vẫn có byte thừa ở cuối (reverse-engineered) — khớp doc §7.

## Việc kế tiếp

- Dev B: dùng `alarms.py` cho reader live + facet `/api/alarms` (Dev A).
- Q1 với ATS: struct chính thức thay decode tay.
