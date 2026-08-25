# 2026-08-13 — Module B: alarm đầu-cuối, và một ADR bị lật

## Việc lớn nhất: ADR-0007 sai, đã đo lại

ADR-0007 kết luận *"OneATS KHÔNG dùng OPC UA A&C, dùng interface riêng"*.
**Sai.** `OAAlarmType [ns=2;i=1101]` kế thừa thẳng `AlarmConditionType [i=2915]`.

Nguyên nhân sai không phải kỹ thuật mà là **phương pháp**: phép đo cũ subscribe
5 giây bằng filter `BaseEventType` trên một trạm đang đứng yên, thấy 0 event, rồi
kết luận cơ chế không tồn tại. Im lặng không phải bằng chứng.

Trong chính phiên này tôi suýt lặp lại đúng lỗi đó — **bốn cửa sổ đo liên tiếp
cho 0 event** và tôi đã bắt đầu viết kết luận "chỉ có poll". Thứ chặn lại là
người dùng phản đối, rồi một phép đo có kênh đối chứng.

→ [ADR-0026](../../10-architecture/adr/0026-alarm-channels.md) `Supersedes: 0007`.
Đề nghị bổ sung `AGENTS.md` §5.4: với kênh sự kiện, "không quan sát thấy gì" chỉ
được ghi là sự thật đã đo khi có bằng chứng độc lập rằng đã có kích thích.

## Đo được (2026-08-13, DEMO_SAS qua `opc.tcp://127.0.0.1:48050`)

| Chỉ số | Giá trị |
|---|---|
| Cây kiểu | `OABinaryAlarmType` · `OADiscreteAlarmType` · `OALimitAlarmType` · `OARateOfChangeType`, mỗi loại có `ChangeOfState` + `ReturnToNormal` |
| `subscribe_events(Server, evtypes=[OAAlarmType])` | 46/46 event · 61 field · **29 có giá trị** |
| Filter mặc định `BaseEventType` | 13 field |
| `Server.EventNotifier` | `1` · `Objects` và `OAAlarm` đều `0` → chỉ subscribe được trên Server |
| `ClientUserId`, `Quality` | có trong select clause, **không bao giờ được điền** |
| Phát lại lúc subscribe | **không** — subscribe rồi ngồi im 75 s → 0 event |
| `ConditionRefresh` | `BadNoMatch` — không hiện thực |
| `GetActiveAlarm` | 243 alarm, 14 ms/lần |
| Chuỗi lan truyền thật | 1 máy cắt mở → 7 alarm điện áp, 4 ngăn + 3 thanh cái, **87 ms** |

Cách đo lại: script trong scratchpad phiên này; cốt lõi là subscribe với
`evtypes=[client.get_node("ns=2;i=1101")]` rồi **thao tác thật** trên simulator.

## Struct nhị phân: giải xong, và nó từng sai

`decode_alarm_body` cũ decode "sạch 243/243" mà **vẫn sai**. Trường sau
`source_point` là một **string mang tên người thao tác**
(`Administrator@OneATS_DataEditor:<user>`), không phải 4 byte pad. Với 243 alarm
nền nó luôn rỗng nên đọc nhầm thành pad vẫn ra đúng — cho tới khi có người mở
một máy cắt, trường thành 38 byte, và mọi field sau lệch → `OverflowError`.

Phần đuôi là một **OPC UA variant**: `0x0c`=String (Discrete), `0x01`=Boolean
(Binary), `0x0a`=Float (Limit).

Bản mới **tự kiểm**: struct lặp lại `source_point` ở cuối, nên walk đúng thì
echo phải khớp *và* tiêu thụ hết body. Kiểm chứng **90/90** trên body thật.

## Đã xong

**Backend**
- `integration/opcua/alarms.py` — decode viết lại, `AlarmDecodeError`, hai bất biến tự kiểm
- `integration/opcua/alarm_events.py` — `AlarmMonitor`: A&C subscription + snapshot, tự nối lại
- `integration/alarm_map.py` — dotted path → `ScopeRef`, cả hai kênh (I6)
- `domain/alarm.py` · `alarm_rules.py` + `alarm_rules/default.yaml` — phân loại tra bảng
- `domain/incident.py` — gom cụm 3 chiều + chống rung, hàm thuần
- `domain/playbooks.py` + 4 YAML — hướng dẫn xử lý, **toàn bộ `status: draft`**
- `api/alarmsource.py` · `alarms.py` · `alarmwatch.py` · `routers/alarms.py`
- `Cadence.ALARM` ngay sau `STATE`, **không** qua throttle
- `/api/alarms` · `/api/incidents`, có `EvidenceRecord`

**Frontend**
- `features/monitoring/AlarmPane.vue` + `IncidentCard.vue`, tab **Sự cố**
- `stores/alarms.ts`, nhánh `alarm` trong `stream.ts` (vẫn một EventSource)
- i18n vi + en

**Test** — 122 test mới, chạy không cần DataServer:
`test_alarm_decode.py` (95) · `test_alarm_rules.py` (18) · `test_incident.py` (9) ·
`test_alarms_api.py` (8). Fixture: `alarm_bodies.json` (90 body thật, có ca hồi
quy `actor`), `alarm_cascade.json` (chuỗi 87 ms).

`python tools/check.py` **xanh cả 9 mục**.

Thử tay: [`docs/40-testing/module-b-alarm.md`](../../40-testing/module-b-alarm.md).

## Quyết định đáng chú ý

- **Severity không dùng để phân loại.** `team.md` B3 đề xuất `>= 800`; đo thật
  thì chỉ 1 alarm đạt, trong khi `ABNORMAL VOLTAGE` (650) và 41 `TimeFail` (360)
  đều là bất thường. Khoá phân loại là `(category, point suffix, actor)`.
- **`actor` khác rỗng → không bao giờ là sự cố.** Thiếu luật này thì lúc demo,
  mở một máy cắt để diễn là hệ báo động kèm hướng dẫn xử lý.
- **Cửa sổ gom cụm 200 ms**, không phải 2000 ms như dự kiến ban đầu.
- **Playbook là dữ liệu tra theo khoá**, không nhét vào system prompt — module F
  sau này chỉ thay *nguồn* của cùng một field.

## Việc kế tiếp

- **`store/events.py` + migration 006** — SOE. Hiện chỉ có hiện tại, đóng app là mất.
- **Tool `alarms` cho agent** + nhánh `digest.py`, trần 2k token.
- **Q1 với ATS, hỏi khác trước**: xin struct chính thức (kèm dãy byte + hai byte
  `tag` chưa rõ), và **vì sao `ClientUserId`/`Quality` không được điền** — bật
  được thì đường nhị phân bớt quan trọng hẳn và I2 có `Quality` thật.
- **Nội dung playbook cần người có thẩm quyền vận hành duyệt.** Trạm chưa có tài
  liệu xử lý sự cố (xác nhận 2026-08-13), nên 4 playbook hiện tại do agent soạn.
- Đo thêm vài chuỗi lan truyền nữa để xác nhận cửa sổ 200 ms — hiện suy từ **một**
  lần đo.
