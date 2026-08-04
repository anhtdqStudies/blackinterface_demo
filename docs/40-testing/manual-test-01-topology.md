# Manual test 01 — Bay template + Topology builder

**Ngày viết**: 2026-08-04 · **Module**: #1 trong `docs/90-progress/status.md`
**Đo trên**: `DEMO_SAS` v654, OneATS Data Server 4.2 build 128

> Mục đích của bài test này: **chứng minh mục tiêu M1** — trỏ vào một DataServer
> đã dựng xong thì ra được sơ đồ một sợi chạy được, **không vẽ tay, không map point**.
>
> Không phải test "code có chạy không" (`uv run pytest` lo việc đó).
> Đây là test "sản phẩm có làm đúng việc nó hứa không".

---

## 0. Chuẩn bị (1 lần)

```bash
cd backend  && uv sync
cd frontend && npm install && npm run build
```

**Phải build frontend**, nếu không API chạy nhưng không có giao diện (ADR-0009).

Nếu gặp `os error 396` hoặc `Access is denied` — đó là OneDrive giữ file `.venv`.
Chạy lại lệnh, lần thứ hai luôn được. Xem `AGENTS.md` §7.

---

## 1. Chạy

```bash
cd backend
uv run uvicorn blackinterface.api.app:app --host 127.0.0.1 --port 8080
```

Mở `http://127.0.0.1:8080`

Mặc định app đọc **fixture** (`backend/tests/fixtures/sas_tree.json`) — chạy được
khi không có DataServer. Để nối hệ thật, xem §6.

Khi đang sửa frontend thì dùng `npm run dev` ở cổng 5173 thay vì build lại mỗi lần.

---

## 2. Test case

### TC-01 — Dựng model từ DataServer, không vẽ tay

**Làm**: mở trang, đọc dòng header.

**Phải thấy**:

| Trường | Giá trị đúng |
|---|---|
| Tên trạm | `DEMO_SAS` |
| ModelVersion | `654` |
| Số ngăn | `13` |
| Số thiết bị | `80` |
| Thời gian dựng | **< 0.1 s** (fixture) · **< 3 s** (live) |

**Ý nghĩa**: con số 80 không phải do code này tự đếm — nó khớp với lần đo độc lập
ngày 2026-08-04 (`docs/30-integration/oneats-dataserver.md` §5). Nếu template đặt
thiếu hoặc thừa một dao cách ly nào, con số này lệch ngay.

**So sánh với cách cũ**: trong OneATS Grid Studio, 13 ngăn / 80 thiết bị là
nhiều ngày vẽ và gán point thủ công.

---

### TC-02 — Suy loại ngăn không cần SLD

**Làm**: bấm lần lượt tab `220kV`, `110kV`, `22kV`. Nhìn nhãn dưới mỗi cột và
danh sách ngăn ở panel phải.

**Phải thấy đúng 13 ngăn này**:

| Ngăn | Cấp | Loại | Template |
|---|---|---|---|
| D01 | 220kV | TRANSFORMER | T2 |
| D03 | 220kV | LINE | T1 |
| D04 | 220kV | LINE | T1 |
| D12 | 220kV | BUS_TRANSFER | T4 |
| D17 | 220kV | BUS_COUPLER | T3 |
| DBB | 220kV | BUSBAR_PROTECTION | T6 |
| E01 | 110kV | LINE | T1 |
| E02 | 110kV | LINE | T1 |
| E04 | 110kV | BUS_TRANSFER | T4 |
| E05 | 110kV | BUS_COUPLER | T3 |
| E07 | 110kV | TRANSFORMER | T2 |
| EBB | 110kV | BUSBAR_PROTECTION | T6 |
| J01 | 22kV | FEEDER_MV | T5 |

**Không được có ngăn nào `UNKNOWN`.**

**Ý nghĩa**: loại ngăn suy ra **chỉ từ danh sách logical node** (`XSWI7` → ngăn
đường dây, `XSWI91/92` → ngăn nối thanh cái vòng…). Không đọc SLD, không hỏi ai.

**Đối chiếu**: J01 là ngăn mà bản extract SLD ở `document/SLD_serviceOut/` **bỏ sót
hoàn toàn**. Ở đây nó có mặt. Đó là lý do ADR-0002 loại SLD khỏi MVP.

---

### TC-03 — Sơ đồ một sợi khớp thực tế

**Làm**: ở tab `220kV`, nhìn cột `D03`.

**Phải thấy** (trạng thái đo lúc 2026-08-04, nếu chạy live thì có thể khác):

```
BB29 ────────────────  (thanh cái vòng, xám nét đứt — xem TC-05)
        │
      -9  MỞ (xanh)
BB21 ────┼────────────  (đỏ = có điện)
        │
      -1  ĐÓNG (đỏ)
BB22 ────┼────────────
        │
      -2  MỞ (xanh)
        │
  -15 ⏚  MỞ
        │
      271  ĐÓNG (máy cắt, ô vuông đặc đỏ)
        │
      -7  ĐÓNG
        │
  -75 ⏚   ⏚ -76   (cả hai MỞ)
        │
      ○ Line
```

**Kiểm tra 3 điều**:

1. **Đúng điện**: `-1` đóng và `-2` mở → ngăn đang bám **thanh cái 1**, không phải
   thanh cái 2. Đây là trạng thái **runtime**, không phải hình vẽ cố định.
2. **Đúng tên**: nhãn phải là số hiệu EVN thật (`271`, `-1`, `-75`), không phải
   `XCBR1`, `XSWI1`.
3. **Đúng cấu trúc**: 3 dao chọn thanh cái ở trên máy cắt, dao đường dây `-7` ở
   dưới, 2 tiếp địa `-75/-76` ở phía đường dây, 1 tiếp địa `-15` phía thanh cái.

**Đối chiếu ngoài hệ thống**: mở OneATS Grid Viewer (hoặc HMI hiện có) cùng lúc,
so từng vị trí dao của D03. Phải khớp 100%. **Đây là phép kiểm quan trọng nhất
của bài test.**

---

### TC-04 — Truy vết được về DataServer

**Làm**: bấm vào ký hiệu máy cắt `271` của D03.

**Panel phải hiện**:

| Trường | Giá trị |
|---|---|
| Tên EVN | `271` |
| Logical node | `XCBR1` |
| Trạng thái | `CLOSED` |
| Dbpos thô | `2` |
| Quality | `GOOD` |
| Timestamp | có, dạng ISO |
| source_ref | `ns=2;s=D03.XCBR1` |

**Ý nghĩa**: mọi trạng thái hiển thị đều kèm `(giá trị, quality, timestamp, nguồn)`.
Không có con số nào "từ trên trời" — invariant **I2** và **I3**.

**Lưu ý về I6**: `source_ref` chỉ là *dấu vết*. NodeId không phải khoá chính —
khoá là `D03.XCBR1`, do domain đặt.

---

### TC-05 — Dữ liệu xấu KHÔNG được thành trạng thái

Đây là test an toàn. **Quan trọng hơn mọi test đẹp mắt ở trên.**

**Làm**: ở tab `220kV`, nhìn thanh cái **BB29** (thanh cái vòng, trên cùng).

**Phải thấy**: **màu xám, nét đứt** — không phải xanh, không phải đỏ.

**Lý do**: `Subs.BB29.IsLive` trên DataServer đang trả `BadWaitingForInitialData`.
Quality không GOOD → hệ thống **không được phép** nói thanh cái có điện hay không.

**Sai nếu**: BB29 hiện màu xanh (suy ra "không có điện" từ việc đọc lỗi). Đó là
lỗi an toàn nghiêm trọng — vào hiện trường, "không có điện" là câu khiến người ta
chạm tay vào.

Tương tự, ngăn `D12` có `IsLive` lỗi. Kiểm tra panel của D12 hiển thị đúng như vậy.

---

### TC-06 — Thiếu dữ liệu thì phải nói ra

**Làm**: mở panel phải, kéo xuống mục **"Cảnh báo dựng model"** (hoặc tab
**Cảnh báo** trên thanh trên cùng để xem đầy đủ, tách theo mức độ).

**Phải thấy đúng 1 cảnh báo**:

```
Bay J01 connects to busbar BB41, but the DataServer has no such object.
Added as inferred; it carries no live data.
busbar_not_in_source · J01
```

**Và ở tab `22kV`**: thanh cái hiện nhãn `BB41 (suy ra)`, màu xám.

**Ý nghĩa**: trạm 22kV trong `DEMO_SAS` không có object thanh cái ở `/SAS/Subs/`.
Hệ thống **không im lặng bịa ra** một thanh cái bình thường — nó dựng placeholder,
đánh dấu `inferred`, và báo lên UI. Invariant **I7**.

**Sai nếu**: thanh cái 22kV hiện như thanh cái bình thường, hoặc ngăn J01 mất
thanh cái mà không có cảnh báo nào.

---

### TC-07 — Không có đường ghi nào

**Làm**: mở `http://127.0.0.1:8080/docs` (OpenAPI).

**Phải thấy**: chỉ đúng **một** endpoint không phải GET, là `POST /api/reload`.
Không có endpoint nào điều khiển thiết bị.

**Ý nghĩa**: invariant **I1** được cưỡng chế bằng cấu trúc chứ không bằng lời hứa.
Test `test_no_write_endpoint_exists` sẽ fail nếu ai đó thêm vào.

---

## 3. Kiểm chứng tự động (chạy kèm)

```bash
cd backend
uv run pytest          # 107 test, không cần DataServer
uv run pytest -m live  # 2 test, cần DataServer đang chạy
```

Test `live` so **model dựng từ hệ thật** với **model dựng từ fixture** — cùng ngăn,
cùng thiết bị, cùng tên EVN. Đây là cái bắt **drift**: nếu ATS đổi address space,
fixture vẫn xanh nhưng test này đỏ.

Và từ gốc repo:

```bash
python tools/check.py
```

---

## 4. Sai số / giới hạn đã biết của bài test này

| Điều | Trạng thái |
|---|---|
| Mới verify trên **1 trạm** (`DEMO_SAS`) | ⚠ Câu hỏi mở Q4. Trạm khác có thể lệch quy ước đặt tên |
| Giá trị là **snapshot lúc dựng model**, chưa realtime | Đúng thiết kế ở bước này. Subscription là module #3 |
| Chưa có lan truyền mang điện (energization) | Module #2. Hiện chỉ tô theo `PosSt` từng thiết bị |
| Mã thanh cái 22kV/35kV/500kV | ⚠ GIẢ ĐỊNH — chưa xác minh. Xem `topology.py: VOLTAGE_BUSBAR_CODE` |
| Bố cục ngăn nối thanh cái (D17/E05) | Hai dao chọn nằm ở hai rail khác nhau, máy cắt vẽ bên dưới cả hai. Đọc được, nhưng chưa đúng thẩm mỹ SLD chuẩn |

---

## 5. Nếu hỏng thì xem ở đâu

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| Mở `/` ra 404 | Chưa `npm run build`. Không có frontend dự phòng (ADR-0009) |
| Trang trắng, header báo "Không tải được model" | Fixture chưa có → xem §6 để tạo lại |
| `bay_type = UNKNOWN` | Trạm dùng quy ước LN khác. Xem `domain/bay_types.py`, cần template mới |
| Cảnh báo `slot_unmapped` | Ngăn có dao cách ly mà template không đặt → **graph thiếu thiết bị**, phải sửa template |
| Số thiết bị gấp 4 lần | Browse OPC UA bị trùng. `_children()` trong `discovery.py` phải dedupe theo NodeId |
| Tất cả trạng thái `UNDETERMINED` | Quality không GOOD — kiểm tra DataServer, không phải kiểm tra code |

---

## 6. Chạy trên DataServer thật

```bash
cd backend
BI_SOURCE=opcua BI_OPCUA_URL=opc.tcp://127.0.0.1:48050 \
  uv run uvicorn blackinterface.api.app:app --port 8080
```

PowerShell:
```powershell
$env:BI_SOURCE="opcua"; $env:BI_OPCUA_URL="opc.tcp://127.0.0.1:48050"
uv run uvicorn blackinterface.api.app:app --port 8080
```

> ⚠ **Invariant I1**: khi triển khai thật phải dùng account read-only
> (`BI_OPCUA_USER` / `BI_OPCUA_PASSWORD`), **không Anonymous**.
> Endpoint DEMO cho Anonymous, trạm thật thì không được. Câu hỏi mở Q5.

Tạo lại fixture từ hệ thật:

```bash
python tools/probe_dataserver.py --dump --slim --depth 4 \
  --out backend/tests/fixtures/sas_tree.json
```
