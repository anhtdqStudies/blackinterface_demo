# Từ điển thuật ngữ

Đọc file này khi gặp thuật ngữ lạ. Sắp theo nhóm, không theo alphabet.

---

## Hệ thống điện

| Thuật ngữ | Nghĩa |
|---|---|
| **SLD** | Single Line Diagram — sơ đồ một sợi, biểu diễn trạm bằng một đường cho cả 3 pha |
| **Bay / Ngăn** | Một "cột" chức năng trong trạm: tập thiết bị nối một đường dây/MBA vào thanh cái |
| **Busbar / Thanh cái** | Thanh dẫn chung, nối nhiều thiết bị cùng cấp điện áp |
| **CB — Circuit Breaker** | Máy cắt. Cắt được dòng sự cố. LN `XCBR` |
| **DS — Disconnector** | Dao cách ly. **Chỉ đóng/cắt khi không tải.** LN `XSWI` |
| **ES — Earthing Switch** | Dao tiếp địa. Nối đất khi bảo dưỡng. LN `XSWI` |
| **CT / VT** | Biến dòng / biến áp đo lường |
| **Transformer / MBA** | Máy biến áp. 2 hoặc 3 cuộn → 2 hoặc 3 terminal |
| **Feeder / Lộ** | Đường dây xuất tuyến |
| **Bus coupler** | Ngăn liên lạc, nối hai thanh cái với nhau qua một máy cắt |
| **Bus transfer** | Ngăn chuyển thanh cái (thanh cái vòng), không có máy cắt riêng |
| **Energization / Coloring** | Suy trạng thái mang điện của từng phần tử, lan truyền từ Source |
| **SOE** | Sequence of Events — chuỗi sự kiện theo thời gian, độ phân giải ms |
| **Tagging / LOTO** | Treo thẻ khoá thiết bị khi bảo dưỡng (lockout-tagout) |
| **AOR** | Area of Responsibility — phạm vi thiết bị một người được xem/thao tác |

---

## Mô hình topology

| Thuật ngữ | Nghĩa |
|---|---|
| **Connectivity Node** | Điểm đấu nối điện — busbar, điểm nối giữa các thiết bị |
| **Connection Point / Terminal** | Chân của thiết bị. CB & DS = 2 terminal; ES = 1; MBA = 2–3 |
| **Node-breaker model** | Mô hình chi tiết: giữ nguyên từng dao/máy cắt. Đây là mô hình ta dùng |
| **Bus-branch model** | Mô hình rút gọn cho tính toán trào lưu công suất. Chỉ derive khi cần |

Nguyên tắc (manual OneATS A.5.2): **Terminal luôn mang cùng trạng thái điện với
Connectivity Node nó nối vào.** Đây là nền của thuật toán coloring.

---

## IEC 61850 — Logical Nodes

Chuẩn đặt tên thiết bị/tín hiệu trong trạm số.

| LN | Nghĩa |
|---|---|
| `XCBR` | Circuit breaker — máy cắt |
| `XSWI` | Switch — dao cách ly / dao tiếp địa |
| `XCBD` | Chẩn đoán máy cắt (breaker diagnostics) |
| `CSWI` | Switch controller — điều khiển đóng cắt |
| `CILO` | Interlocking — liên động |
| `MMXU` | Measurement — đo lường (U, I, P, Q, f, PF) |
| `MSQI` | Sequence & imbalance — thành phần thứ tự, mất cân bằng |
| `PTOC` `PTUV` `PTOV` `PDIS` `PDIF` | Bảo vệ: quá dòng, kém áp, quá áp, khoảng cách, so lệch |
| `RREC` | Autorecloser — tự đóng lại |
| `RBRF` | Breaker failure — bảo vệ máy cắt từ chối |
| `GGIO` | Generic I/O — tín hiệu chung, không phân loại |

> ⚠ **OneATS làm phẳng tên 61850.** Thực tế là `D03.XCBR1.PosSt`,
> **không** phải `D03CTRL/XCBR1.Pos.stVal`. Xem `docs/30-integration/oneats-dataserver.md`.

### Mã chức năng bảo vệ (ANSI, dùng trong tên IED của ATS)
| Mã | Chức năng |
|---|---|
| `F21` | Distance — bảo vệ khoảng cách |
| `F50` / `F51` | Overcurrent tức thời / có thời gian |
| `F50BF` | Breaker failure |
| `F67` | Directional overcurrent — quá dòng có hướng |
| `F87L` / `F87B` / `F87T` | So lệch đường dây / thanh cái / máy biến áp |
| `F85` | Teleprotection / truyền cắt |
| `F86` | Lockout relay — rơ le khoá |
| `F74` | Trip circuit supervision — giám sát mạch cắt |

---

## Dbpos — kiểu vị trí (QUAN TRỌNG)

`PosSt` **không phải boolean**. Là double point:

| Giá trị | Nghĩa |
|---|---|
| `0` | INTERMEDIATE — đang chuyển, cơ cấu kẹt giữa chừng |
| `1` | OPEN — mở |
| `2` | CLOSED — đóng |
| `3` | BAD — không xác định |

`0` và `3` là **tín hiệu chẩn đoán quan trọng**, cấm nuốt thành "unknown".

---

## Mã ngăn EVN

Ký tự đầu = cấp điện áp, hai ký tự sau = loại ngăn.

| Mã | Nghĩa | Cấp |
|---|---|---|
| `D..` | ngăn 220kV | 220kV |
| `E..` | ngăn 110kV | 110kV |
| `J..` | ngăn 22kV | 22kV |
| `.LL` | Line — ngăn đường dây |  |
| `.TI` | Transformer Incoming — ngăn máy biến áp |  |
| `.BC` | Bus Coupler — ngăn liên lạc |  |
| `.BT` | Bus Transfer — ngăn vòng |  |

Ví dụ: `DLL` = ngăn đường dây 220kV, `EBC` = ngăn liên lạc 110kV.

### Số hiệu thiết bị EVN
`271` = máy cắt ngăn 71 cấp 220kV. Hậu tố sau dấu `-` là vị trí:

| Hậu tố | Vị trí |
|---|---|
| `-1` `-2` | dao cách ly thanh cái 1 / 2 |
| `-7` | dao cách ly đường dây |
| `-9` | dao cách ly thanh cái vòng |
| `-3` | dao cách ly phía MBA |
| `-14` `-15` | tiếp địa phía DS1 |
| `-24` `-25` | tiếp địa phía DS2 |
| `-75` `-76` | tiếp địa phía đường dây |

---

## OneATS

| Thuật ngữ | Nghĩa |
|---|---|
| **FEP** | Front End Processing — thu thập dữ liệu từ IED qua protocol công nghiệp |
| **DataServer** | Xử lý realtime: data server, alarm server, tagging server. Cổng 48050 |
| **SmartHIS** | Historical Information System — lưu lịch sử + alarm/event. Cổng 48010 |
| **Grid Studio** | HMI: Grid Designer (thiết kế) + Grid Viewer (vận hành) |
| **DataEditor** | Công cụ cấu hình FEP + DataServer, quản lý project/version/AOR/user |
| **DataModel** | Tập dữ liệu có cấu trúc theo CIM, mô tả hệ thống điện |
| **IED** | Intelligent Electronic Device — rơ le bảo vệ, BCU… |
| **BCU** | Bay Control Unit — thiết bị điều khiển ngăn |

---

## Black Interface

| Thuật ngữ | Nghĩa |
|---|---|
| **Neutral Station Model** | Domain model chuẩn hoá, contract giữa các lớp. Không lộ NodeId |
| **BlackCore** | Agent LLM: intent, tool registry, planner, evidence, policy |
| **EvidenceRecord** | Object có kiểu do *tool* sinh, chứa nguồn/quality/coverage/limits |
| **Catalog snapshot** | Bản đóng băng point catalog có hash, pin vào release |
| **Release** | Bản publish immutable, định danh bằng hash nội dung |
| **Drift** | NodeId trong snapshot không còn resolve được trên DataServer live |
| **Bay template** | Bảng ánh xạ số hiệu LN → vị trí điện. **Không phải bản vẽ** |
| **Bay card** | UI xác nhận một ngăn; engineer chỉ chạm chỗ có cảnh báo |
