# Manual test 02 — Số đo và bằng chứng (GĐ 1, Module A)

> Chạy sau `manual-test-01-topology.md`. Kịch bản 01 kiểm sơ đồ và mang điện;
> kịch bản này kiểm **số đo** và **khối bằng chứng** thêm vào ở GĐ 1.
>
> Viết 2026-08-06, đối chiếu với `DEMO_SAS` v654 trên máy dev.

## 0. Khởi động

```bash
cd frontend && npm run build          # chỉ cần khi vừa sửa frontend
cd ../backend && uv run uvicorn blackinterface.api.app:app --port 8080
```

Mở `http://127.0.0.1:8080`.

Cần DataServer đang chạy ở `opc.tcp://127.0.0.1:48050`. Không có nó vẫn xem được
(mở project từ snapshot), nhưng số đo sẽ đứng yên và đó là **đúng** — xem bước 5.

---

## 1. Panel số đo xuất hiện

Vào trang sơ đồ, chọn cấp **220kV**. Panel bên phải, dưới «Độ phủ», phải có
khối **«Số đo»**.

| Kỳ vọng | Nếu sai thì sao |
|---|---|
| Có 6 dòng: Công suất tác dụng · phản kháng · Điện áp dây · Dòng điện lớn nhất · Tần số · Hệ số công suất | Panel trống ở scope `vl:220kV` là **đúng** — số đo gắn vào ngăn, không gắn vào cấp điện áp. Bấm vào một ngăn có `MMXU1` (D01, D03, D04, D12, D17) để thấy |
| Dòng **Tần số** có đơn vị `Hz` | Thiếu `Hz` = lỗi |
| Năm dòng còn lại **KHÔNG có đơn vị nào** | **Có đơn vị (kV, MW, A…) là LỖI** — báo ngay, xem §4 |

## 2. Số đổi theo thời gian thực, mà sơ đồ không nhấp nháy

DEMO_SAS sinh số ngẫu nhiên liên tục, nên số đo phải tự đổi vài giây một lần.

- ✅ Số đo đổi được
- ✅ **Sơ đồ đứng yên** trong lúc số đổi — không vẽ lại, không nhấp nháy, màu
  dây và ký hiệu thiết bị không đổi

Đây là điều quan trọng nhất của kịch bản này (ADR-0012 luật 1). Nếu sơ đồ nháy
theo số đo thì số đo đang đi nhầm đường và phải báo.

Dưới bảng số phải có dòng chữ nhỏ: *«Số đo có áp deadband: thay đổi nhỏ hơn
ngưỡng sẽ không được đẩy lên.»* Đó là yêu cầu của ADR-0012 — người vận hành phải
biết mình đang nhìn số đã lọc.

## 3. Khối bằng chứng

Cuối panel bên phải, khối **«BẰNG CHỨNG»**.

| Kỳ vọng |
|---|
| Có huy hiệu đếm số cảnh báo (hoặc chữ «đầy đủ» nếu không có) |
| Dòng **Độ phủ**: `n / n điểm` — hai số bằng nhau |
| Dòng **Nguồn**: «đọc trực tiếp từ DataServer» hoặc «ảnh chụp đã lưu» + ModelVersion 654 |
| Dòng **Lúc**: giờ hiện tại, đến giây |
| Huy hiệu **không bao giờ đỏ hoặc xanh lá** — đây là màu của phần mềm, không phải của trạm |

Cảnh báo bình thường thấy trên DEMO_SAS:

- *«Số đo đã qua lọc deadband»* — luôn có khi có số đo
- *«Số đúng nhưng thang đo chưa xác minh — không in đơn vị»* — luôn có, đây là Q7
- *«Cấu trúc lấy từ snapshot…»* — khi mở project từ snapshot thay vì tải lại

**Không** được thấy: *«Số liệu cũ»* trong khi DataServer đang chạy bình thường.
Nếu thấy nó khi link đang xanh, đó là lỗi — dao không nhúc nhích cả ngày vẫn là
dữ liệu hiện tại, không phải dữ liệu cũ.

## 4. Bẫy quan trọng nhất — đơn vị

DataServer **không công bố** đơn vị cho bất kỳ số đo nào (đã đo 2026-08-06).
Ta biết `Vlin` là điện áp, **không biết** 221.08 là V hay kV.

Nên: nhìn thấy `221.08` cạnh chữ «Điện áp dây» là **đúng**.
Nhìn thấy `221.08 kV` là **sai** — ai đó đã đoán, và đoán sai một chữ số thập
phân trên màn hình vận hành là chuyện nghiêm trọng.

Ba chỗ **được phép** có đơn vị: `Hz` (tần số), nấc MBA (`step`), hệ số công suất
(không đơn vị). Ba cái đó không thể sai thang.

## 5. Rút dây / tắt DataServer

Tắt DataServer, chờ ~10 giây.

- ✅ Đèn header đổi sang «Mất kết nối», màu **hồng/đỏ nhạt của hệ thống** — không
  phải màu đỏ của máy cắt đóng
- ✅ **Sơ đồ giữ nguyên**, số đo giữ nguyên giá trị cuối
- ✅ Khối bằng chứng mọc thêm *«Mất kết nối — đây là điều biết được lần cuối,
  không phải hiện tại»*
- ❌ Sơ đồ trắng, số đo về 0, hoặc dây chuyển sang «không điện» = **LỖI NGHIÊM
  TRỌNG**. Trạm rỗng trông y hệt trạm cắt hết điện.

Bật lại DataServer → trong ~30 giây phải tự nối lại, không cần F5.

## 6. Đổi ngôn ngữ

Chuyển `VI` ↔ `EN` ở góc phải header. Mọi nhãn trong panel số đo và khối bằng
chứng phải đổi theo — **không được còn chữ tiếng Việt lẫn trong bản EN**, và
không được lòi ra mã máy như `unit_unverified` hay `active_power`.

## 7. Địa chỉ URL

Bấm vào một thiết bị → thanh địa chỉ thành `#/ops/device:D03.XCBR1`.
Copy URL, mở tab mới → phải ra đúng màn hình đó, đúng ngăn đó.

Gõ tay `#/ops/bay:KHONGCO` → phải bị đẩy về trang chủ, **không** được im lặng
hiện cả trạm.

---

## Chỗ đã biết là chưa làm (đừng báo là lỗi)

- Số đo **chưa vẽ lên sơ đồ**, mới ở panel bên phải.
- Giá trị **theo từng pha** (`AphsA/B/C`…) chưa đọc — `MMXU1` có 26 con, ta lấy 6.
- `/api/energization` chưa mang khối bằng chứng; chỉ `/api/summary` có.
- Panel số đo ở scope `station` gộp cả thanh cái và MBA; chưa nhóm theo chủ thể.
