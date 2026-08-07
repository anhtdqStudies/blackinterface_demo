# OneATS DataServer — Sự thật đã đo

> **Trạng thái: ĐÃ ĐO TRỰC TIẾP trên hệ chạy thật — 2026-08-04, bổ sung §8b 2026-08-06**
> Đo lại bằng: `python tools/verify_dataserver.py`
> Mọi số liệu trong file này đều đến từ hệ live, **không phải từ manual PDF**.
> Manual có chỗ mâu thuẫn với thực tế — xem §9.

Máy đo: máy dev của anhtdq, model `DEMO_SAS` version 654.

---

## 1. Endpoint

```
URL              opc.tcp://127.0.0.1:48050   (advertise: opc.tcp://Anhtdq:48050)
Transport        http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary
SecurityPolicy   None
SecurityMode     1 (None)
UserTokens       Anonymous | UserName (Basic256)
ApplicationUri   urn:Anhtdq:ATSCo:OneATS_DataServer
Product          OneATS Data Server 4.2, build 128, 2025-12-16
```

**→ Client-server cổ điển, KHÔNG phải OPC UA PubSub Part 14.** Đã xác minh bằng
transport profile và bằng việc browse được address space.

### Namespaces
| idx | URI | Nội dung |
|---|---|---|
| 0 | `http://opcfoundation.org/UA/` | chuẩn UA |
| 1 | `urn:Anhtdq:ATSCo:OneATS_DataServer` | server-specific |
| 2 | `OADataServer/MODEL` | **DataModel — vùng làm việc chính** |
| 3 | `OADataServer/FEPSimulate` | kênh FEP mô phỏng (tên IED) |

---

## 2. Cấu trúc address space

Phân cấp CIM đúng như manual mô tả:

```
/Root/EVN/RLDC/PROJECT/SAS/220kV/D03/XCBR1/PosSt
      │   │    │       │   │     │   │     └─ attribute
      │   │    │       │   │     │   └─────── logical node (61850)
      │   │    │       │   │     └─────────── bay
      │   │    │       │   └───────────────── voltage level
      │   │    │       └───────────────────── substation
      └───┴────┴───────────────────────────── region / subregion / project
```

**NodeId là đường dẫn ngữ nghĩa dạng chấm** — đọc được bằng mắt:
```
ns=2;s=D03.XCBR1.PosSt
```
Đây là tài sản lớn: evidence tự giải thích, đối chiếu drift dễ.

### Node roots dưới `Objects` (ns=2)
| Root | Vai trò |
|---|---|
| `Root` | cây CIM (EVN/RLDC/PROJECT/SAS) — **17.965 node dưới `/SAS`** |
| `OAAlarm` | interface alarm riêng (§5) |
| `OAEvent` | rỗng (không có children) |
| `OATagging` | Set/Remove/Query tagging, work order |
| `OADataModel` | ModelName / ModelVersion / State / OnlineUpdate / Restart |
| `OAPSM` | Protection Settings Manager |
| `OAManualWriting`, `OAIntermediate`, `OATrace`, `Local` | phụ trợ |

### Versioning — dùng cho pin release (invariant I7)
```
/OADataModel/ModelName    = "DEMO_SAS"
/OADataModel/ModelVersion = 654          ← móc để phát hiện drift
/OADataModel/State        = 2
```

---

## 3. Thống kê cây `/SAS`

```
tổng node   17.965      (Variable 16.420 | Object 1.283 | Method 262)
voltage lvl  110kV, 220kV, 22kV, AT1, AUX, Subs, SAS_SIM, Tagging
bay thật     13         (12 bay + busbar objects)
```

### Thành phần LN theo bay (đã đo)
| VL | Bay | LN children |
|---|---|---|
| 220kV | D01 | BAY BCU F67 MMXU1 MSQI1 XCBD1 **XCBR1** XSWI1 XSWI11 XSWI2 XSWI3 XSWI31 XSWI32 XSWI9 |
| 220kV | D03 | BAY BCU F21 F87L MMXU1 MSQI1 XCBD1 **XCBR1** XSWI1 XSWI11 XSWI2 XSWI7 XSWI71 XSWI72 XSWI9 |
| 220kV | D04 | (giống D03) |
| 220kV | D12 | BAY BCU F211 F212 MMXU1 MSQI1 XCBD1 XCBR1 XSWI1 XSWI11 XSWI2 XSWI9 XSWI91 XSWI92 |
| 220kV | D17 | BAY BCU F21 MMXU1 MSQI1 XCBD1 XCBR1 XSWI1 XSWI11 XSWI12 XSWI2 XSWI21 XSWI22 |
| 220kV | DBB | BAY F50BF F87B1 F87B2 F87B3 Pos RT |
| 110kV | E01, E02 | …XSWI1 XSWI11 XSWI2 XSWI7 XSWI71 XSWI72 XSWI9 (line) |
| 110kV | E04 | …XSWI9 XSWI91 XSWI92 (bus transfer) |
| 110kV | E05 | …XSWI11 XSWI12 XSWI21 XSWI22 (bus coupler) |
| 110kV | E07 | …XSWI3 XSWI31 XSWI32 (transformer) |
| 110kV | EBB | BAY F50BF F87B1 F87B2 F87B3 PosSt RT |
| 22kV | J01 | BAY BCU MMXU1 MSQI1 XCBD1 XCBR1 XSWI3 XSWI31 XSWI32 |

---

## 4. Auto-binding — 100%

Dò thiết bị đóng cắt **thuần bằng rule** (regex `^/SAS/<VL>/<BAY>/(XCBR|XSWI)\d+$`),
không dùng SLD, không dùng LLM:

| Chỉ số | Kết quả |
|---|---|
| Thiết bị đóng cắt tìm được | **80** |
| Bind được `PosSt` | **80 / 80 = 100%** |
| Quality = Good | **80 / 80** |
| Có SourceTimestamp | **80 / 80** |
| Trạng thái đọc được | 27 CLOSED, 53 OPEN |

Tín hiệu tùy chọn (`Loc`, `Blk`, `PosCmd`) thiếu ở 34 thiết bị — đó là **dao tiếp địa
không có điều khiển**, đúng thực tế, không phải lỗi bind.

### Tên 61850 bị LÀM PHẲNG (khác chuẩn)
ATS không lồng `Pos.stVal` như chuẩn 61850. Thực tế:
```
D03.XCBR1.PosSt        ← vị trí (KHÔNG phải Pos.stVal)
D03.XSWI1.PosSt
D03.MMXU1.AphsA        ← dòng pha A (KHÔNG phải MMXU1.A.phsA.cVal.mag.f)
D03.MMXU1.PhVphsA , .WphsA , .VArphsA , .PFphsA , .PPVphsAB , .Hz , .Vlin
```

### `PosSt` là Dbpos 4 giá trị — KHÔNG phải boolean
```
0 = INTERMEDIATE   (cơ cấu kẹt giữa chừng — tín hiệu chẩn đoán, đừng nuốt)
1 = OPEN
2 = CLOSED
3 = BAD
```

### Nội dung một LN đóng cắt (đo trên `D03.XCBR1`, 28 children)
```
PosSt PosSt1 PosCmd  PosCtl(Method)  Name SName  Loc Mcb Blk
BlkDS BlkES BlkOUT BlkPro BlkF74  Dsch Dscrepancy  F86Lok
F74Coil1A/1B/1C/2A/2B/2C  Tagging …
```
`XSWI` gọn hơn (15 children): `PosSt PosCmd PosCtl Name SName Loc Mcb Blk BlkCB
BlkDS BlkES BlkOUT RemEnaSt ResetCtl Tagging`.

---

## 5. Định danh EVN có sẵn trong address space

Giải quyết luôn bài toán resolve tên do operator gõ:

| Node | `Name` | `SName` |
|---|---|---|
| `D03.XCBR1` | `271` | |
| `D03.XSWI1` | `271-1` | `-1` |
| `D03.XSWI11` | `271-15` | |
| `D03.XSWI2` | `271-2` | `-2` |
| `D03.XSWI7` | `271-7` | |
| `D03.XSWI9` | `271-9` | |
| `D17.XCBR1` | `212` | |
| `E05.XCBR1` | `112` | |

**Quy ước đánh số LN = vị trí điện** (nền tảng cho bay template):

| LN | Hậu tố EVN | Vị trí điện |
|---|---|---|
| `XSWI1` | `-1` | dao cách ly thanh cái 1 |
| `XSWI2` | `-2` | dao cách ly thanh cái 2 |
| `XSWI9` | `-9` | dao cách ly thanh cái vòng |
| `XSWI7` | `-7` | dao cách ly đường dây |
| `XSWI3` | `-3` | dao cách ly phía MBA |
| `XSWI11/12` | `-15/-14` | tiếp địa phía DS1 |
| `XSWI21/22` | `-25/-24` | tiếp địa phía DS2 |
| `XSWI71/72` | `-75/-76` | tiếp địa phía đường dây |
| `XCBR1` | số ngăn | máy cắt |

---

## 6. Suy loại ngăn từ DataServer — 12/12 đúng

Rule chỉ dựa vào thành phần LN, không cần SLD:

```
có F87B*/Pos/PosSt          → BUSBAR
không có XCBR*              → BUS_TRANSFER (no CB)
có XSWI11+XSWI12+XSWI21+22  → BUS_COUPLER
có XSWI91+XSWI92            → BUS_TRANSFER
có XSWI7                    → LINE
có XSWI3 + XSWI1            → TRANSFORMER
có XSWI3, không XSWI1       → FEEDER_MV
```

Đối chiếu với `bay_type` từ extract SLD: **12/12 khớp**.
Ngoài ra rule tìm thấy **J01 (22kV)** mà bản extract SLD bỏ sót hoàn toàn.

---

## 7. Alarm — interface RIÊNG, không phải OPC UA A&C

> ⚠ **Đây là chỗ dễ làm sai nhất.** Manual gợi ý A&C; thực tế KHÔNG dùng.

Đã đo: subscribe event chuẩn trên Server object → **0 event** trong 5s.
`OAEvent` không có children.

### Interface thật
```
OAAlarm.GetActiveAlarm(objectID: NodeId[])  →  ExtensionObject[]  (ns=2, TypeId 5803)
```
- Truyền NodeId gốc `/SAS` → **243 alarm active**
- Truyền NodeId ngăn `D03` → chỉ alarm của D03 (**scope được theo node** → ánh xạ thẳng sang AOR)
- Mảng rỗng → toàn bộ

### Method khác trên `OAAlarm`
```
AckAll  AcknowledgeByEventId  AcknowledgeByNodeId  AcknowledgeByObjectId
Enable  Disable  Delete  GetDisabledAlarm
ChangeHiHiLimit ChangeHiLimit ChangeHiRsnLimit ChangeLoLimit ChangeLoLoLimit ChangeLoRsnLimit
```
**Tất cả đều là ghi — cấm dùng ở MVP (invariant I1).**

### Struct ExtensionObject (reverse-engineered, decode 243/243 sạch)
Thứ tự field, little-endian, string = Int32 length prefix + UTF-8:
```
int32 len + bytes   event_id (GUID-ish, 20 byte)
int32               seq
4 byte              flags
string              message          "CB 231 STATUS"
2 byte              severity_raw
string              category         "Discrete Alarm" | "Binary Alarm" | "Limit Alarm"
8 byte              flags
string              source_object    "D01.XCBR1"
string              source_point     "D01.XCBR1.PosSt"   ← nối thẳng về thiết bị
4 byte              pad
int64               t_active         FILETIME (100ns từ 1601-01-01 UTC)
int64               t_change         FILETIME
string              value_text       "2 (CLOSED)"
```
> ⚠ **GIẢ ĐỊNH — chưa xác minh**: ranh giới field cuối còn lệch vài byte
> (`value_text` đọc lố). **Việc cần làm: xin ATS định nghĩa struct chính thức**
> thay vì tiếp tục reverse-engineer. Xem `docs/90-progress/status.md`.

### Phân bố alarm đo được
```
243 alarm active | Discrete 159, Binary 82, Limit 2 | 133 source object riêng biệt
timestamp parse được 243/243 | mới nhất 2026-08-03T04:53:39Z
```

---

## 8. Subscription (cho realtime overlay)

Đã đo: hoạt động bình thường.
```
publishing interval  200 ms (server revise: 200.0)
lifetime / keepalive 3000 / 1000
10 monitored item → 12 datachange notification trong 5 s (có initial values)
```
**Một subscription phía server → fan-out SSE cho N client.** Đừng tạo subscription
theo từng browser.

Đo lại 2026-08-06 khi thêm Module A: **176 monitored item** (97 vị trí/IsLive + 79
số đo), server nhận hết, `rejected=0`. Trong 20 s quan sát: 1 nhịp `link`, 1 nhịp
`state`, 4 nhịp `measurement` — đồ thị điện **không** dựng lại lần nào dù DEMO_SAS
sinh số đo ngẫu nhiên liên tục. Đó là ADR-0012 luật 1 chạy trên dữ liệu thật.

---

## 8b. Số đo tương tự — đo 2026-08-06 (DEMO_SAS v654)

Đọc trực tiếp bằng `tools/probe_dataserver.py`; danh mục ở
`backend/src/blackinterface/domain/measurement.py`.

| Chủ thể | Đường dẫn | Data attribute dùng |
|---|---|---|
| Ngăn | `/SAS/<VL>/<BAY>/MMXU1` | `totW` `totVAr` `totPF` `Vlin` `Amax` `Hz` |
| Thanh cái | `/SAS/Subs/BBxx` | `PPVmax` `Hz` |
| MBA | `/SAS/AT1/YLTC` | `TapPos` |

`MMXU1` có 26 con (thêm `AphsA/B/C`, `PhVphsA/B/C`, `WphsA/B/C`, `VArphsA/B/C`,
`PFphsA/B/C`, `PPVphsAB/BC/CA`, `Aneut`, `Tagging`). Ta chỉ lấy tổng và cực đại;
giá trị theo pha chưa có use case nên chưa đọc. 11/12 ngăn có `MMXU1`.

### Ba phát hiện quan trọng

**1. `PPVmax` viết thường chữ m**, không phải `PPVMax` như ghi trong ADR-0012 và
tài liệu use case. Case sai thì không bind được.

**2. KHÔNG có `EngineeringUnits` / `EURange` / `Unit` trên bất kỳ measurand nào.**
Đã kiểm tra từng biến. Vậy **đơn vị không lấy được từ nguồn**: `Vlin` đọc ra
221.08 và không có gì nói đó là V hay kV. Black Interface do đó **không in đơn vị**
cho công suất/áp/dòng, chỉ in số kèm tên đại lượng, và gắn
`LimitCode.UNIT_UNVERIFIED` vào bằng chứng. `Hz`, hệ số công suất và nấc MBA được
miễn vì không thể sai thang. → **Câu hỏi mở Q7**: xin ATS thang đo thật.

**3. DEMO_SAS sinh số đo ngẫu nhiên, không nhất quán vật lý.** Cùng lúc đo được
`D03.MMXU1.Hz = 51.33` và `Subs/BB21.Hz = 49.71` — bất khả thi trong một trạm đồng
bộ. Đừng dùng số của DEMO để kiểm chứng công thức điện; nó chỉ dùng để kiểm chứng
đường dẫn dữ liệu.

---

## 9. Bề mặt GHI — cấm chạm, và là rủi ro bảo mật

Address space có sẵn bề mặt ghi, hiện **không được bảo vệ**:
```
<bay>.XCBR1.PosCtl / <bay>.XSWI*.PosCtl    Method điều khiển đóng cắt
ATx.YLTC.TapChg / MasCtl / EmerCtl / ParCtl / ResetCtl   ← đo 2026-08-06
SysCommon.Force / Unforce / UnforceAllData
SysCommon.EnableAlarm / DisableAlarm
OATagging.SetTagging / RemoveTagging / ChangeTagging
OAAlarm.Ack* / Enable / Disable / Delete / Change*Limit
OADataModel.Restart / OnlineUpdate          ← restart data server
```

Nhóm `YLTC` đáng chú ý: ta **đọc** `TapPos` ngay cạnh 5 Method điều khiển bộ đổi
nấc. Đã thêm cả 5 vào `FORBIDDEN_CALLS` của `tools/check.py` — đọc một node nằm
sát một lệnh chính là lúc phải viết ranh giới ra, không phải lúc mặc định nó có.

**Endpoint đang là SecurityPolicy None + Anonymous cho phép** → bất kỳ ai tới được
cổng 48050 đều gọi được `PosCtl`. Trên máy demo thì không sao; **trước khi triển khai
trạm thật đây là lỗ hổng nghiêm trọng**, tồn tại độc lập với Black Interface.

Black Interface phải: dùng account riêng **read-only** qua `UserName` (không Anonymous),
và tool registry không chứa write tool. Hai lớp độc lập.

---

## 10. Chỗ manual sai so với thực tế

| Manual nói | Thực tế đo được |
|---|---|
| Alarm qua OPC UA Alarm & Conditions (A.3) | Interface riêng `OAAlarm.GetActiveAlarm` |
| Tên theo chuẩn 61850 | Bị làm phẳng (`XCBR1.PosSt`, không `Pos.stVal`) |
| HIS ở port 48010 | Trên máy dev 48010 là tiến trình `sunshine`; HIS chưa chạy |

---

## 11. Cách đo lại

```bash
python tools/verify_dataserver.py          # kiểm tra toàn bộ số liệu file này
python tools/probe_dataserver.py --dump    # dump lại cây đầy đủ ra JSON
```
Script sẽ báo rõ mục nào còn đúng, mục nào đã lệch.
