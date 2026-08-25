# ADR-0026 — Alarm đi qua hai kênh: A&C subscription + snapshot

- **Status**: Accepted
- **Date**: 2026-08-13
- **Supersedes**: [ADR-0007](0007-proprietary-alarm-interface.md)

## Bối cảnh

ADR-0007 (2026-08-04) kết luận: *"OneATS KHÔNG dùng OPC UA Alarms & Conditions,
dùng interface riêng dạng method-call"*, dựa trên phép đo:

```
subscribe_events() trên Server object  →  0 event trong 5 s
/OAEvent                               →  không có children
```

**Đo lại 2026-08-13 — kết luận đó SAI.**

Phép đo cũ hỏng ở phương pháp, không ở kỹ thuật: nó chờ 5 giây trên một trạm
đang đứng yên, không có ai thao tác gì, rồi coi sự im lặng là bằng chứng về cơ
chế. Không có gì xảy ra thì không có event — điều đó đúng với mọi server A&C
trên đời.

Sự thật đo được, mỗi dòng đều lặp lại được:

| Đo được | Bằng chứng |
|---|---|
| OneATS **có** dùng A&C chuẩn | `OAAlarmType [ns=2;i=1101]` kế thừa `AlarmConditionType [i=2915]` |
| Cây kiểu đầy đủ | `OABinaryAlarmType` · `OADiscreteAlarmType` · `OALimitAlarmType` · `OARateOfChangeType`, mỗi loại có `ChangeOfState` và `ReturnToNormal` |
| `OALimitAlarm` tách rất mịn | `HiHi/Hi/Lo/LoLo/HighReasonability/LowReasonability Exceeded` + `ReturnTo*` |
| Subscribe có filter chạy tốt | `subscribe_events(Server, evtypes=[OAAlarmType])` → 46/46 event, 61 field, **29 có giá trị** |
| `Server.EventNotifier = 1` | `Objects` và `OAAlarm` đều `= 0` → chỉ subscribe được trên Server |
| `ClientUserId` và `Quality` **không** được điền | có trong select clause, luôn rỗng |
| Không phát lại lúc subscribe | subscribe rồi ngồi im 75 s → **0 event** |
| `ConditionRefresh` không có | `BadNoMatch` |

`OAEvent` không có children — điều này ADR-0007 đo đúng. Nó chỉ không phải bằng
chứng cho kết luận đã rút ra.

## Quyết định

**Hai kênh, cả hai đều cần, không kênh nào thay được kênh kia.**

```
khởi động / nối lại  ──> OAAlarm.GetActiveAlarm  ──> tập alarm đang active + actor
                                                     (ExtensionObject nhị phân)

liên tục             ──> subscribe_events(Server, evtypes=[OAAlarmType])
                                                  ──> ActiveState · Retain · Value
                                                      ConditionName · Severity · AckedState
```

**Vì sao giữ cả hai** — không phải để dự phòng, mà vì mỗi kênh mang thứ kênh kia
không có:

- Subscription **không** mang `ClientUserId`. Trường "ai gây ra alarm này" chỉ tồn
  tại trong body nhị phân của `GetActiveAlarm`, dưới dạng chuỗi
  `Administrator@OneATS_DataEditor:<user>`. Đây không phải chi tiết vụn: nó là thứ
  phân biệt **sự cố** với **người vận hành vừa thao tác**, và thiếu nó thì hệ sẽ
  báo động mỗi lần có người đóng cắt bình thường.
- OneATS không phát lại condition lúc subscribe và không có `ConditionRefresh`, nên
  subscription **không** cho biết trạng thái ban đầu. Phải có một lần chụp.

Kênh realtime là subscription. **Không có vòng poll định kỳ** — nó thua subscription
về cả độ trễ lẫn chi phí, và không cho thêm gì.

## Hệ quả

**Tích cực**

- Clear được đẩy tường minh qua `ReturnToNormal`, không phải suy ra bằng diff hai lô.
- `OALimitAlarm` phân biệt sẵn HiHi/Hi/Lo/LoLo — ngữ nghĩa cần cho phân tích sự cố
  mà tự suy từ giá trị thì không có.
- `Retain`, `ActiveState`, `AckedState` là field chuẩn, không phải cờ tự chế.
- Phụ thuộc vào struct nhị phân **giảm hẳn**: nó không còn nằm trên đường realtime.

**Tiêu cực / rủi ro**

- Vẫn phải giải mã struct nhị phân cho đường snapshot, và nó vẫn không có spec chính
  thức (**Q1**). Hai byte `tag` chưa rõ nghĩa.
- Hai kênh nghĩa là hai nguồn cho cùng một sự thật → phải hợp nhất. Khoá hợp nhất là
  `EventId`: `EventId` của event khớp `event_id` trong body — đã đối chiếu byte.
- `Quality` không được điền, nên I2 phải lấy quality từ point tương ứng qua
  `monitor.py`, không lấy từ alarm.

## Bài học về phương pháp — quan trọng hơn kết luận kỹ thuật

ADR-0007 sai không phải vì đo cẩu thả mà vì **rút kết luận từ sự im lặng**. Một phép
đo kênh sự kiện chỉ có nghĩa khi nó tự chứng minh được rằng đã có việc gì xảy ra
trong cửa sổ đo.

Trong chính phiên đo lại này, bốn cửa sổ liên tiếp cho "0 event" và suýt dẫn tới
đúng kết luận sai đó lần thứ hai. Thứ cứu được là một phép đo có kênh đối chứng.

**Bổ sung vào `AGENTS.md` §5.4**: với kênh sự kiện, "không quan sát thấy gì" chỉ được
ghi là sự thật đã đo khi kèm bằng chứng độc lập rằng đã có kích thích trong cửa sổ đó.
Không có thì ghi `CHƯA KẾT LUẬN`, không ghi `không tồn tại`.

## Phương án đã bác bỏ

- **Chỉ subscription** — không có ảnh chụp ban đầu, và mất `actor`.
- **Chỉ `GetActiveAlarm` (poll)** — chậm hơn, tốn hơn, mất `ActiveState`/`Retain`, và
  phải tự suy raise/clear bằng diff. Đây là phương án ADR-0007 buộc phải chọn.
- **`ConditionRefresh` cho ảnh chụp** — đã thử, `BadNoMatch`.
- **Subscribe trên `OAAlarm`** — `EventNotifier = 0`, server trả
  `BadMonitoredItemFilterUnsupported`.
