# ADR-0012 — Tách nhịp `state` / `measurement` / `alarm` trên một stream

- **Status**: Accepted → **Implemented 2026-08-06** (GĐ 1, Module A)
- **Date**: 2026-08-05

## Bối cảnh

Module realtime (2026-08-05) đang chạy như sau: mọi thứ chuyển động nằm trong
**một** tài liệu `LiveOut`, đẩy qua `GET /api/stream` (SSE), sự kiện tên `live`.
Mỗi lô thay đổi → `apply_samples` vá observation → `build_station` dựng lại toàn
bộ graph → `solve_energization`. **Đo được: 0.71 ms + 0.21 ms ≈ 1 ms mỗi lô.**
Sự kiện đầu tiên nặng **12.7 KB**.

Thiết kế đó đúng, và lý do nó đúng được ghi rõ trong bảng bẫy của `AGENTS.md`:
dựng lại toàn bộ **bảo đảm** kết quả giống hệt duyệt mới, thứ mà vá tại chỗ không
hứa được. Trả 1 ms để mua sự bảo đảm đó là món hời.

Nhưng nó đúng **vì dữ liệu hiện tại là rời rạc**. Danh sách theo dõi hiện là 97
điểm, toàn `PosSt` và `IsLive` — một dao cách ly đứng yên hàng giờ.

Module A (Monitoring) sắp đưa vào **số đo tương tự**, và file use case chỉ đích
danh point:

| Nguồn | Point | Use case |
|---|---|---|
| Công suất, dòng, áp mỗi ngăn | `BAYx.MMXU1.totW / totVAr / Vlin / Amax` | A-01, A-02 |
| Nấc máy biến áp | `ATx.YLTC.TapPos` | A-01 |
| Áp và tần số thanh cái | `Subs.BBxx.PPVMax`, `Subs.BBxx.Hz` | A-01 |

Analog **khác bản chất**: nó đổi liên tục. Nếu để chúng đi chung đường với
`PosSt` thì:

1. `build_station` + `solve_energization` chạy lại mỗi khi công suất nhích 0.1 MW
   — **vô nghĩa**, vì số đo không đổi topology và không đổi kết quả mang điện.
2. Tài liệu 12.7 KB (sẽ còn lớn hơn) được đẩy lại mỗi 200 ms cho N client.
3. Frontend phải vẽ lại hoặc so sánh cả tài liệu để biết chỉ một nhãn đổi.

Đây là vấn đề kiến trúc, không phải tối ưu sớm: nó quyết định hình dạng của
`LiveOut`, của store frontend, và của mọi facet sau này.

## Quyết định

**Giữ một EventSource duy nhất. Tách thành nhiều loại sự kiện có kiểu.**

| Sự kiện SSE | Nội dung | Nhịp | Dựng lại graph? | Deadband? |
|---|---|---|---|---|
| `state` | `PosSt`, `IsLive`, energization | hiếm | **có** (~1 ms) | không |
| `measurement` | MMXU, TapPos, PPVMax, Hz | dày | **không** | **có** |
| `alarm` | alarm mới / hết / đổi | thưa | không | không |
| `link` | kết nối, số điểm, drift | thưa | không | không |

### Luật 1 — Chỉ `state` được chạm đồ thị điện

Số đo **không bao giờ** làm thay đổi topology hay kết quả energization. Nó là
nhãn. Đây là ranh giới cứng, có test khoá.

Hệ quả tốt cho an toàn: bão số đo không thể trì hoãn việc xử lý một máy cắt vừa
nhảy.

### Luật 2 — `measurement` có deadband, `state` thì không

- **`state` gộp lô nhưng không lấy mẫu**: mọi thay đổi vị trí đều được áp, chỉ
  hoãn dựng lại 200 ms để một thao tác ngăn vẽ lại **một lần** ở trạng thái nhất
  quán. Giữ nguyên hành vi hiện có.
- **`measurement` có deadband** (theo % hoặc trị tuyệt đối, cấu hình được) và
  throttle. Bỏ qua thay đổi dưới ngưỡng là **đúng** với analog — nó không phải
  mất thông tin, nó là loại bỏ nhiễu.

Áp deadband cho `state` sẽ là lỗi an toàn: một máy cắt nhảy rồi đóng lại trong
150 ms là **đúng thứ phải thấy**, không phải nhiễu.

### Luật 3 — Một kết nối, một chính sách reconnect, một đèn báo

Không mở EventSource thứ hai. Lý do:

- HTTP/1.1 giới hạn ~6 kết nối mỗi origin; mỗi stream thêm vào là một suất bị ăn.
- Hai stream = hai chính sách kết nối lại = hai nguồn sự thật về "ta có đang
  nghe trạm không". Điều đó đâm thẳng vào bẫy đã ghi trong `AGENTS.md`:
  *rớt link là tin về **ta**, không phải về trạm*. Một trạm rỗng trông y hệt một
  trạm cắt hết điện — không được để hai đèn báo mâu thuẫn nhau.

Riêng **hội thoại của agent** là ngoại lệ có chủ ý: nó là stream **theo phiên**,
không phải broadcast, vòng đời khác hẳn → dùng đường riêng
(`/api/chat/{session}/stream`). Xem ADR-0014.

### Luật 4 — `structure_revision` vẫn tách khỏi `revision`

Giữ nguyên cơ chế hiện có: đổi hình học thì frontend tải lại bản vẽ; đổi trạng
thái thì chỉ tô lại. Nay áp cho cả ba loại sự kiện.

## Phương án đã bác bỏ

### A. Giữ một tài liệu `LiveOut` gộp tất cả
Ít code nhất, frontend chỉ một đường áp dụng. **Bác bỏ**: buộc dựng lại đồ thị
điện vì một con số đổi, và đẩy lại toàn bộ tài liệu cho mỗi thay đổi analog.

### B. Stream riêng cho số đo (`/api/stream/measurements`)
Tách sạch nhất về khái niệm. **Bác bỏ** vì hai chính sách reconnect và hai đèn
báo kết nối — rủi ro an toàn lớn hơn lợi ích gọn gàng.

### C. Frontend poll số đo theo chu kỳ, chỉ `state` đi SSE
Đơn giản, và với 1 Hz thì chấp nhận được. **Bác bỏ**: đẻ ra đường code thứ hai
cho dữ liệu sống, đúng thứ thiết kế hiện tại đã cố tránh khi cho `/api/live` và
`/api/stream` trả **cùng một tài liệu**.

### D. Vá `StationGraph` tại chỗ để dựng lại rẻ hơn
**Bác bỏ** — đã có trong bảng bẫy `AGENTS.md` với số đo kèm theo. 1 ms đã đủ rẻ;
vá tại chỗ không bảo đảm được kết quả giống duyệt mới. ADR này giải quyết vấn đề
bằng cách **không dựng lại khi không cần**, chứ không phải làm việc dựng lại rẻ đi.

## Hệ quả

**Tích cực**

- Số đo dày bao nhiêu cũng không đụng tới đường đi của tính đúng đắn.
- Băng thông giảm mạnh: một thay đổi analog gửi vài trăm byte thay vì 12.7 KB.
- Frontend tách store theo đúng nhịp dữ liệu → panel số đo cập nhật mà sơ đồ
  không phải vẽ lại.
- Mỗi loại sự kiện test được riêng.

**Tiêu cực**

- `LiveOut` tách thành nhiều schema → `openapi.json` và `schema.d.ts` đổi, phải
  xuất lại và sửa frontend một lượt.
- Frontend có nhiều đường áp dụng hơn một. Giảm nhẹ bằng cách giữ **một** handler
  duy nhất phân nhánh theo `event.type`, không rải khắp nơi.
- Deadband là một tham số **sai được**: đặt quá rộng thì giấu mất biến động thật.
  Phải cấu hình được, có giá trị mặc định bảo thủ, và hiện lên UI rằng số đo có
  áp deadband.

**Việc phải làm để ADR này không mục**

- Test khoá luật 1: sự kiện `measurement` không bao giờ làm đổi
  `structure_revision` hay kết quả `solve_energization`.
- Config mới: `BI_MEASUREMENT_DEADBAND_PCT`, `BI_MEASUREMENT_THROTTLE_MS` —
  khai báo ở `config.py`, không nơi nào khác đọc `os.environ`.

## Khi thực hiện (2026-08-06) — ADR này sai hai chỗ

**1. `PPVMax` thật ra là `PPVmax`** (chữ m thường). Bảng point ở trên chép từ file
use case, chưa đo. Đã sửa ở `domain/measurement.py`; xem
`docs/30-integration/oneats-dataserver.md` §8b.

**2. Một `BI_MEASUREMENT_DEADBAND_PCT` toàn cục là không đủ.** 0,5 % của 50 Hz là
0,25 Hz — một dao động rất lớn, trong khi 0,5 % của phụ tải là nhiễu. Deadband do
đó khai theo **từng đại lượng** trong danh mục, và biến môi trường chỉ còn là
**đặt đè** cho lắp đặt nào đã đo được ngưỡng tốt hơn. Nấc MBA không có deadband:
nó rời rạc như vị trí dao, làm mượt nó là giấu mất thao tác đổi nấc.

Ngoài ra ADR không nói tới việc throttle phải có **sườn xuống**: bỏ hết trong cửa
sổ sẽ khiến số đo *cuối* của một chùm không bao giờ tới nơi, và client đứng lại ở
một số cũ mà không có gì báo là cũ. Xem `api/throttle.py`.

Kiểm chứng trên DataServer thật, 20 s: `state` 1 nhịp, `measurement` 4 nhịp,
`structure_revision` không đổi — đồ thị điện không dựng lại lần nào.
