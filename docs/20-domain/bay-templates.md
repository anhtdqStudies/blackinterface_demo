# Bay Template — Đặc tả

> **Bay template KHÔNG phải bản vẽ.** Nó là bảng ánh xạ
> `số hiệu LN → vị trí điện trong graph`, cộng thứ tự slot.
> Topology sinh ra từ template là **correct-by-construction**.

Cơ sở dữ liệu: `docs/30-integration/oneats-dataserver.md` §5, §6 (đã đo 2026-08-04).

---

## Vì sao template hoạt động

Cấu trúc đấu nối của một ngăn **do loại ngăn quyết định**, không do trạm quyết định.
Ngăn đường dây 220kV hai thanh cái ở Bến Cát và Hóc Môn có cùng một sơ đồ một sợi.

Và quan trọng hơn: **quy ước đánh số LN của ATS/EVN đã mã hoá sẵn vị trí điện.**

| LN | Hậu tố EVN | Vị trí |
|---|---|---|
| `XSWI1` | `-1` | dao cách ly thanh cái 1 |
| `XSWI2` | `-2` | dao cách ly thanh cái 2 |
| `XSWI9` | `-9` | dao cách ly thanh cái vòng |
| `XSWI7` | `-7` | dao cách ly đường dây |
| `XSWI3` | `-3` | dao cách ly phía MBA |
| `XSWI11` `XSWI12` | `-15` `-14` | tiếp địa phía DS1 |
| `XSWI21` `XSWI22` | `-25` `-24` | tiếp địa phía DS2 |
| `XSWI71` `XSWI72` | `-75` `-76` | tiếp địa phía đường dây |
| `XSWI31` `XSWI32` | | tiếp địa phía MBA |
| `XSWI91` `XSWI92` | | tiếp địa phía thanh cái vòng |
| `XCBR1` | số ngăn | máy cắt |

Nên bài toán *tái dựng đồ thị từ chuỗi mơ hồ* (không giải được) trở thành bài toán
*tra bảng* (giải được, verify được).

---

## Suy loại ngăn từ DataServer

Rule chỉ dựa vào thành phần LN. **Đã đo: 12/12 đúng.**

```python
def infer_bay_type(lns: set[str]) -> BayType:
    if {"F87B1", "Pos", "PosSt"} & lns:            return BUSBAR
    if not any(l.startswith("XCBR") for l in lns): return BUS_TRANSFER_NO_CB
    if {"XSWI11","XSWI12","XSWI21","XSWI22"} <= lns: return BUS_COUPLER
    if {"XSWI91","XSWI92"} <= lns:                 return BUS_TRANSFER
    if "XSWI7" in lns:                             return LINE
    if "XSWI3" in lns:
        return TRANSFORMER if "XSWI1" in lns else FEEDER_MV
    return UNKNOWN
```

---

## Sáu template phủ hết DEMO_SAS

Ký hiệu: `BB1`/`BB2` = thanh cái 1/2, `BB9` = thanh cái vòng, `T` = terminal ngoài.

### T1 — LINE (`DLL`, `ELL`)
Bay: D03, D04, E01, E02
```
BB1 ──[XSWI1]──┬───────────────┐
               │              [XSWI11] ⏚
BB2 ──[XSWI2]──┤
               │
BB9 ──[XSWI9]──┤
               │
            [XCBR1]
               │
            [XSWI7]──┬──[XSWI71] ⏚
               │      └──[XSWI72] ⏚
               T (đường dây)
```
Slot: `bb_sel_1, bb_sel_2, bb_sel_9, es_bb, breaker, line_ds, es_line_a, es_line_b`

### T2 — TRANSFORMER (`DTI`, `ETI`)
Bay: D01, E07
```
BB1 ──[XSWI1]──┬──[XSWI11] ⏚
BB2 ──[XSWI2]──┤
BB9 ──[XSWI9]──┤
            [XCBR1]
               │
            [XSWI3]──┬──[XSWI31] ⏚
               │      └──[XSWI32] ⏚
               T (MBA)
```

### T3 — BUS_COUPLER (`DBC`, `EBC`)
Bay: D17, E05 — đối xứng hai phía
```
BB1 ──[XSWI1]──┬──[XSWI11] ⏚
               │  [XSWI12] ⏚
            [XCBR1]
               │
BB2 ──[XSWI2]──┴──[XSWI21] ⏚
                  [XSWI22] ⏚
```

### T4 — BUS_TRANSFER (`DBT`, `EBT`)
Bay: D12, E04 — nối thanh cái chính sang thanh cái vòng
```
BB1 ──[XSWI1]──┬──[XSWI11] ⏚
BB2 ──[XSWI2]──┤
            [XCBR1]
               │
BB9 ──[XSWI9]──┴──[XSWI91] ⏚
                  [XSWI92] ⏚
```

### T5 — FEEDER_MV (22kV)
Bay: J01 — không có dao chọn thanh cái
```
BB ────────[XCBR1]──[XSWI3]──┬──[XSWI31] ⏚
                              └──[XSWI32] ⏚
                              T
```

### T6 — BUSBAR_PROTECTION
Bay: DBB, EBB — **không phải thanh cái**, là đối tượng *bảo vệ so lệch thanh cái*
```
LN: F87B1..3 (so lệch thanh cái), F50BF (chống hỏng máy cắt), RT,
    Pos/PosSt/Map (ảnh vị trí dao từng ngăn cho sơ đồ bảo vệ)
Topology: không sinh thiết bị đóng cắt nào
```

> **Đính chính (đo 2026-08-04).** Bản nháp đầu của tài liệu này coi `DBB`/`EBB`
> là thanh cái. Sai. Xem mục dưới.

---

## Thanh cái nằm ở đâu (ĐÃ ĐO 2026-08-04)

Thanh cái thật là object riêng dưới `/SAS/Subs/`:

| Object | Cấp | Vai trò | Data attribute |
|---|---|---|---|
| `BB11` `BB12` `BB19` | 110kV | TC1 · TC2 · TC vòng | `IsLive`, `Hz`, `PPVphsAB/BC/CA`, `PPVmax`, `GndSwSt`, `Name` |
| `BB21` `BB22` `BB29` | 220kV | TC1 · TC2 · TC vòng | như trên |

Quy ước tên: **`BB<mã cấp điện áp><chỉ số>`** — `1`=110kV, `2`=220kV;
chỉ số `1`/`2` = thanh cái chính, `9` = thanh cái vòng.

Ngoài ra có các biến dẫn xuất OneATS đã tính sẵn:
`Subs.BB220_BusCoupled`, `Subs.BB29_CBPosSt`, `Subs.BB19_DS9PosStEx`.

**Chưa xác minh**: mã cấp cho 22kV / 35kV / 500kV. `DEMO_SAS` không có object
thanh cái 22kV nào — ngăn J01 vì thế sinh placeholder `BB41` kèm cảnh báo
`busbar_not_in_source`. Xem `domain/topology.py: VOLTAGE_BUSBAR_CODE`.

**Đáng chú ý cho module #2 (energization)**: `IsLive` đã có sẵn cả ở cấp **thanh cái**
(`Subs.BB21.IsLive`) lẫn cấp **ngăn** (`/SAS/220kV/D03/IsLive`), và có `SAS_SIM.CheckLiveState`.
Trước khi tự viết solver, **đối chiếu với cái OneATS đã tính** — câu hỏi mở Q3.
Lưu ý `BB29.IsLive` và `D12.IsLive` đang trả `BadWaitingForInitialData`, tức là
không phải lúc nào cũng dùng được → vẫn cần solver riêng, nhưng để đối chiếu.

---

## Bám thanh cái là TRẠNG THÁI RUNTIME

Trong sơ đồ hai thanh cái, ngăn bám BB1 hay BB2 **không cố định** — nó do
`XSWI1.PosSt` / `XSWI2.PosSt` quyết định tại thời điểm chạy.

- Template cho **các khả năng** (ngăn này *có thể* bám BB1, BB2, BB9)
- Runtime chọn **thực tế** (dao nào đang đóng)

Đây là lý do SLD tĩnh không đủ, và là lý do coloring phải chạy trên topology + PosSt.

Ví dụ đo được lúc 2026-08-04 tại D03:
```
XSWI1 (271-1) = CLOSED  → đang bám thanh cái C22
XSWI2 (271-2) = OPEN
XSWI9 (271-9) = OPEN
XSWI7 (271-7) = CLOSED  → nối ra đường dây
XCBR1 (271)   = CLOSED  → ngăn đang mang tải
```

---

## Định dạng lưu template

**ĐÃ CHỐT — xem ADR-0008.** YAML trong
`backend/src/blackinterface/domain/templates/`, một file một template.
Schema thực tế đang chạy:

```yaml
id: T1_LINE
version: 1
title: "Line bay — double busbar + transfer busbar"
bay_type: LINE
observed_on: [D03, D04, E01, E02]

nodes:
  - {id: n_bb,   kind: internal, label: "busbar side"}
  - {id: n_mid,  kind: internal, label: "breaker/line"}
  - {id: n_line, kind: external, label: "Line"}

slots:
  - {ln: XSWI1,  role: busbar_selector,   endpoints: [BB1, n_bb],     order: 0}
  - {ln: XSWI2,  role: busbar_selector,   endpoints: [BB2, n_bb],     order: 0, required: false}
  - {ln: XSWI9,  role: transfer_selector, endpoints: [BB9, n_bb],     order: 0, required: false}
  - {ln: XSWI11, role: earth_switch,      endpoints: [n_bb, EARTH],   order: 1, side: left,
     required: false}
  - {ln: XCBR1,  role: breaker,           endpoints: [n_bb, n_mid],   order: 2}
  - {ln: XSWI7,  role: line_disconnector, endpoints: [n_mid, n_line], order: 3}
  - {ln: XSWI71, role: earth_switch,      endpoints: [n_line, EARTH], order: 4, side: left,
     required: false}
  - {ln: XSWI72, role: earth_switch,      endpoints: [n_line, EARTH], order: 4, side: right,
     required: false}
```

Ba loại tham chiếu trong `endpoints`: node nội bộ (`n_*`), thanh cái của cấp điện
áp (`BB1` `BB2` `BB9` `BB`), và `EARTH`. Terminal ngoài không phải slot — nó là
`node` có `kind: external`, `diagram/` tự vẽ đuôi ra.

---

## Xử lý ngoại lệ

Ngăn không khớp template nào → `UNKNOWN` → đẩy vào bay-card cho engineer.
**Không đoán.** Ghi validation issue với severity, hiện lý do cụ thể
(thiếu LN nào, thừa LN nào so với template gần nhất).

Ba nguồn đồng thuận (template + DataServer + [SLD nếu có]) → auto-pass, không hỏi.
