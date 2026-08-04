# ADR-0007 — Alarm dùng interface riêng của OneATS

- **Status**: Accepted
- **Date**: 2026-08-04

## Bối cảnh

Manual OneATS (A.3) mô tả hệ dùng OPC UA với DA / **AC (Alarm & Conditions)** / HA / Prog.
Giả định ban đầu (và tư vấn ban đầu): lấy alarm qua OPC UA Alarms & Conditions chuẩn,
subscribe event thay vì poll giá trị.

**Đã đo trực tiếp 2026-08-04 — giả định này SAI.**

```
subscribe_events() trên Server object  →  0 event trong 5 s
/OAEvent                               →  không có children
```

Thực tế OneATS dùng interface riêng dạng method-call.

## Quyết định

Dùng interface riêng của OneATS:

```
OAAlarm.GetActiveAlarm(objectID: NodeId[])  →  ExtensionObject[]  (ns=2, TypeId 5803)
```

Đã đo: NodeId gốc `/SAS` → 243 alarm active; NodeId ngăn `D03` → chỉ alarm D03.
**Scope được theo node** → ánh xạ thẳng sang AOR và sang `get_active_alarms(scope)`.

Struct (reverse-engineered, decode 243/243 sạch) — chi tiết field:
`docs/30-integration/oneats-dataserver.md` §7.

Điểm khai thác quan trọng: `source_point` trong alarm là NodeId dạng chấm
(`D01.XCBR1.PosSt`) → **nối thẳng alarm về thiết bị trên sơ đồ**, không cần bảng
mapping trung gian.

Hệ quả bắt buộc: **`GetActiveAlarm` chỉ cho trạng thái hiện tại.** Muốn phân tích
nhân quả (mục tiêu M2) thì phải **tự buffer event vào store cục bộ** (SQLite) để
dựng SOE. Không có event store thì M2 không tồn tại.

Các method còn lại trên `OAAlarm` (`Ack*`, `Enable`, `Disable`, `Delete`, `Change*Limit`)
**đều là ghi → cấm dùng ở MVP** (invariant I1).

## Phương án đã bác bỏ

- **OPC UA Alarms & Conditions chuẩn** — đã đo, không hoạt động trên OneATS.
- **Poll giá trị point rồi tự suy ra alarm** — bỏ mất phân loại/ngưỡng/severity mà
  DataServer đã tính, và tự chế lại logic alarm là nguồn sai lệch với HMI hiện hữu.
- **Chờ SmartHIS cho lịch sử event** — SmartHIS ngoài phạm vi MVP, và trên máy dev
  còn chưa chạy. Tự buffer rẻ hơn và gỡ SmartHIS khỏi critical path.

## Hệ quả

**Tích cực**
- Alarm scope theo node khớp sẵn với mô hình AOR.
- `source_point` nối thẳng về thiết bị → không cần mapping layer.
- Event store cục bộ cho ta SOE ngay, không phụ thuộc SmartHIS.

**Tiêu cực / rủi ro**
- **Phụ thuộc struct nhị phân không có tài liệu.** Bản decode hiện tại chạy 243/243
  nhưng ranh giới field cuối còn lệch vài byte (`value_text` đọc lố).
  → **Việc phải làm: xin ATS định nghĩa struct chính thức.** Đây là cuộc trò chuyện
  10 phút với team DataServer, tiết kiệm nhiều ngày dò dẫm và tránh vỡ khi ATS
  đổi format. Xem `docs/90-progress/status.md`.
- Interface riêng ⇒ khoá vào OneATS. Chấp nhận: sản phẩm vốn là lớp phủ trên OneATS.
- Phải tự quản vòng đời event (dedupe theo `event_id`, retention, ack state).
