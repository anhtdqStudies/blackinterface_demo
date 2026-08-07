# ADR-0015 — Template do engineer soạn, có phiên bản, phải chứng minh trước khi dùng

- **Status**: Accepted
- **Date**: 2026-08-06
- **Bổ sung** ADR-0008 (schema template YAML). **Không supersede** — schema giữ
  nguyên. Nhưng **thay thế hai điểm** của ADR-0008, ghi rõ ở §6.
- **Liên quan**: ADR-0002 (topology từ DataServer) · ADR-0003 (không canvas vẽ) ·
  ADR-0005 (AI ngoài đường tính đúng đắn) · ADR-0011 (agent soạn phiếu, người ký)

---

## Bối cảnh

### ADR-0008 đã định cho engineer sửa template — nhưng chưa bao giờ mở đường

Đọc lại lý do ADR-0008 **bác bỏ** phương án viết template bằng Python:

> *"thêm loại ngăn thành sửa code → phải review, phải test, phải release. **Kỹ sư
> trạm không sửa được.** Bác bỏ: template là dữ liệu cấu hình của một trạm cụ
> thể, không phải logic sản phẩm."*

Chọn YAML **chính là để** kỹ sư sửa được. Nhưng đường đi đó chưa bao giờ dựng:
template nằm trong `domain/templates/` **bên trong package Python**, nên sửa
template = sửa repo = ra bản dựng mới. Đúng cái ADR-0008 muốn tránh.

### Sáu template, một trạm

| Bằng chứng | Nguồn |
|---|---|
| `observed_on: [...] # DEMO_SAS v654` trên **6/6** file | `domain/templates/*.yaml` |
| Quy ước đánh số LN mới xác nhận trên một trạm | ADR-0008 §Hệ quả, câu hỏi mở **Q4** |
| Chỉ có `BB1 BB2 BB9 BB EARTH` trong từ vựng endpoint | `templates.py: BUSBAR_REFS` |
| `for_bay_type()` trả `next(...)` → **một loại ngăn một template** | `templates.py` |

Sơ đồ **1½ máy cắt** (thường gặp ở 500kV) và sơ đồ **tứ giác** không dựng được
bằng sáu template này. Nếu mỗi lần gặp sơ đồ mới phải chờ ATS ra bản dựng mới thì
**sản phẩm không nhân bản được** — đó là chặn về kinh doanh, không phải chi tiết
kỹ thuật.

### Rủi ro đã xảy ra thật, một lần

`T1_LINE.yaml` v1 đặt `XSWI9` (dao thanh cái vòng) ở **phía thanh cái** thay vì
phía đường dây. Hậu quả: **một đường dây đang mang điện hiện ra là mất điện.**

Sơ đồ vẫn vẽ ra bình thường, đủ thiết bị, không cảnh báo gì. Bắt được là nhờ đọc
script `CheckLiveState` trong `document/DEMO_SAS-MODELExplorer.xlsx` rồi đối
chiếu từng vế logic. Ghi nguyên văn trong comment đầu file.

**Đây là lý do phải có cổng chứng minh, không phải lý do cấm soạn template.** Một
sai sót im lặng cần cơ chế làm cho nó kêu lên, không cần một điều cấm.

### ADR-0003 không chặn quyết định này

Thoạt nhìn "engineer soạn template qua UI" nghe như đi ngược *"engineer không
vẽ"*. Kinh tế của hai việc ngược hẳn nhau:

| | Grid Designer (cái đang thay thế) | Soạn template |
|---|---|---|
| Đối tượng | **cả một trạm** | **một loại ngăn** (~8 slot) |
| Tần suất | **mỗi trạm một lần** | **một lần, dùng cho mọi trạm** |
| Quy mô | 13 trạm = 13 lần vẽ tay | cả EVN ước ~15–20 template |

ADR-0003 bác bỏ canvas vì công việc **lặp vô tận theo số trạm**. Template thì
ngược lại — nó chính là **đòn bẩy** làm cho M1 (dựng project nhanh) có giá trị.

---

## Quyết định

### 1. Template là tài sản của **bản cài**, không phải của package

Sáu file YAML hiện có trở thành **seed**: lần khởi động đầu tiên chúng được nạp
vào store cục bộ, và từ đó store là nguồn sự thật. `domain/templates/*.yaml` giữ
lại làm bản gốc để cài mới và để so sánh.

Hệ quả: template đi cùng dữ liệu của trạm — phải backup, phải migrate, phải có
phiên bản. Xem §Hệ quả.

### 2. Soạn qua UI, nhưng soạn **đấu nối** — không soạn **hình vẽ**

Trình soạn là **trình soạn đồ thị**: đặt nút, rồi khai *"`XSWI7` nằm giữa nút này
và nút kia"*. Kéo thả được, trực quan được, nhưng thứ **lưu xuống** là đấu nối —
đúng schema ADR-0008, không thêm trường nào.

**Cấm** suy đấu nối từ vị trí hình học. Đó chính là thứ mong manh mà ADR-0002 đã
chứng minh không làm được; dựng lại nó trong trình soạn template là đi vòng qua
cửa sau. Toạ độ vẫn sinh tự động từ `order` + `side` như ADR-0008 §D đã chốt.

Nói gọn: UI là **cách nhập dễ hơn cho đúng cái YAML hiện tại**, không phải một mô
hình khác.

### 3. Sửa được **template**, không sửa được **bộ sinh**

| Thứ | Bản chất | Sửa ở đâu |
|---|---|---|
| Template (nút, slot, endpoint, role) | **dữ liệu** | UI ✅ |
| `topology.py`, `energization.py`, `diagram/` | **mã an toàn, có test, dùng chung mọi trạm** | git ❌ |

Cho sửa bộ sinh tại trạm thì mỗi bản cài thành một nhánh riêng: không test được
cái nào, và lỗi sửa cho trạm A không bao giờ tới trạm B.

Nếu một sơ đồ không diễn đạt được bằng schema hiện tại, đó là **thiếu sót của bộ
từ vựng template** (ví dụ hiện không có `BB3`), và cách xử lý là **mở rộng từ
vựng qua ADR**, không phải mở mã cho sửa tại chỗ.

### 4. Chọn template bằng **chữ ký**, không phải bằng `bay_type` một-đối-một

Hiện có **hai nguồn sự thật** về "ngăn này loại gì", và không gì kiểm tra chúng
khớp nhau:

- chuỗi `if` trong `domain/bay_types.py` (Python)
- trường `bay_type:` mà mỗi template tự khai (YAML)

Gộp làm một. Template tự khai chữ ký của nó:

```yaml
id: T1_LINE
version: 3
matches:
  requires: [XCBR1, XSWI7]        # phải có mặt
  excludes: [XSWI91, XSWI92]      # có thì không phải loại này
```

Chọn template = khớp chữ ký, **cụ thể nhất thắng** (nhiều `requires` hơn thì cụ
thể hơn); hoà thì báo lỗi chứ không chọn bừa. `infer_bay_type()` biến mất.

Ba cái được:

1. Một nguồn sự thật thay vì hai.
2. Thêm loại ngăn **thật sự** chỉ còn là thêm một template — đúng như ADR-0008
   §Hệ quả 1 đã hứa mà chưa đạt (hiện phải sửa thêm `BayType` enum và
   `infer_bay_type()`, cả hai là Python).
3. **Hai biến thể cùng tồn tại được**: `T1_LINE` và `T1_LINE_NO_TRANSFER`. Đây là
   điều kiện cần để phục vụ trạm thứ hai.

`BayType` giữ lại làm **nhãn phân loại để hiển thị và lọc**, không còn là khoá
tra template.

### 5. Cổng chứng minh: template phải khớp dữ liệu thật trước khi vào vận hành

Đây là điều kiện làm cho §1–§4 an toàn, và cơ chế **đã có sẵn trong code**:
`energization_mismatch` — ta tính mang điện từ vị trí dao, OneATS tự báo `IsLive`,
lệch thì kêu.

```
engineer sửa/tạo template
        ↓
áp lên trạm đang chạy → tính lại mang điện toàn trạm
        ↓
so với IsLive của OneATS trên MỌI ngăn và MỌI thanh cái
        ↓
  ┌──────────────────────┬──────────────────────────────────┐
  │ 0 lệch, 0 ERROR      │ có lệch                          │
  │ → cho phép Chốt bản  │ → CHẶN chốt, chỉ đích danh ngăn  │
  └──────────────────────┴──────────────────────────────────┘
```

Template sai **không thể lặng lẽ đi vào vận hành**: nó phải qua được dữ liệu thật
của trạm thật. Mạnh hơn hẳn review bằng mắt — người duyệt nhìn `T1_LINE` v1 cũng
sẽ thấy nó hợp lý.

Cổng này **chặn việc chốt bản**, không chặn việc soạn. Engineer vẫn thử nghiệm
thoải mái trên bản nháp.

### 6. Chốt bản pin **cả hai**: `ModelVersion` và bộ phiên bản template

Từ giờ mô hình sai được theo **hai** đường: DataServer đổi, hoặc người sửa
template. Nên bản chốt phải ghi cả hai:

```
release = hash( ModelVersion của DataServer + {template_id: version} + kết quả cổng chứng minh )
```

**Sửa template không tự động đổi trạm đang chạy.** Trạm chạy theo bản đã chốt;
muốn đổi phải chốt lại, có chủ ý, qua cổng. Cùng nguyên tắc ADR-0011: *soạn
phiếu, người ký*.

Điều này **làm sống lại khái niệm "chốt bản"** mà phiên 2026-08-06 đã kết luận là
vô nghĩa. Kết luận đó đúng khi template là hằng số — hai project cùng DataServer
cho ra topology giống hệt nhau nên không có gì để chọn. Khi template thành thứ
con người soạn thì lại có thật một thứ để duyệt và để đóng băng.

### Hai điểm của ADR-0008 bị thay thế

| ADR-0008 nói | ADR-0015 thay bằng |
|---|---|
| *"`bay_type` — **duy nhất một template cho một loại**"* | chọn theo chữ ký, biến thể cùng tồn tại (§4) |
| Template là file trong `domain/templates/`, nạp lúc import | file là **seed**; store của bản cài là nguồn sự thật (§1) |

Mọi phần còn lại của ADR-0008 giữ nguyên: schema `nodes`/`slots`/`endpoints`, ba
loại tham chiếu, `order`/`side` là dữ liệu chứ không phải toạ độ, thiếu slot bắt
buộc là ERROR có tên.

---

## Phương án đã bác bỏ

### A. Giữ nguyên ADR-0008 — template chỉ sửa được trong repo
Rẻ nhất, an toàn nhất, và là điều tôi đề xuất đầu phiên. **Bác bỏ**: mỗi sơ đồ
mới phải chờ một bản dựng từ ATS. Sản phẩm không nhân bản được sang trạm không
dùng sơ đồ thanh cái kép — mà ta **chưa hề đo** trạm nào như vậy (Q4).

### B. Canvas vẽ SLD tự do, suy đấu nối từ hình học
Quen thuộc với người đã dùng Grid Designer. **Bác bỏ** — ADR-0002 đã chứng minh
suy đấu nối từ dữ liệu mơ hồ không giải được, và ADR-0003 đã bác canvas. Kéo thả
để **khai đồ thị** thì được; kéo thả để **vẽ hình rồi đoán ra đồ thị** thì không.

### C. Cho engineer sửa cả bộ sinh (`topology.py`, solver)
Linh hoạt tối đa. **Bác bỏ** — mỗi bản cài thành một nhánh không test được, và
đây là mã quyết định câu *"đoạn này đã cắt điện và tiếp địa chưa"*. Không có mã
nào trong dự án này đáng được bảo vệ hơn.

### D. Cho soạn template, nhưng không có cổng chứng minh
Nhanh hơn, ít việc hơn. **Bác bỏ** — `T1_LINE` v1 là bằng chứng đã xảy ra: một
template sai làm đường dây mang điện hiện ra mất điện, và **không gì báo**. Mở
đường soạn mà không mở đường kiểm là nhân bản đúng cái lỗi đó ra mọi trạm.

### E. Chỉ cho chọn trong thư viện biến thể dựng sẵn, không cho tạo mới
An toàn, và phủ được kha khá trường hợp. **Bác bỏ** — không giải quyết đúng cái
đang chặn: sơ đồ **chưa từng gặp**. Rốt cuộc vẫn phải chờ ATS.

### F. Để LLM sinh template từ mô tả bằng lời
**Bác bỏ thẳng** — ADR-0005: AI không nằm trên đường đi của tính đúng đắn.
Template quyết định câu trả lời về mang điện và tiếp địa. Agent có thể *giúp đọc*
một template, không được *sinh* ra nó.

---

## Hệ quả

### Tích cực

- Sản phẩm nhân bản được sang trạm dùng sơ đồ khác, **không cần bản dựng mới**.
- Một nguồn sự thật cho việc phân loại ngăn, thay vì hai chỗ phải tự khớp nhau.
- Biến thể cùng tồn tại → trạm thứ hai không phải tranh template với trạm thứ nhất.
- "Chốt bản" có nghĩa trở lại, và pin đủ hai chiều rủi ro.
- Template sai bị **chặn bằng dữ liệu thật**, không bằng review bằng mắt.

### Phải chấp nhận

- **Cổng chứng minh chỉ mạnh bằng các trạng thái mà trạm tình cờ đang ở.** Một
  dao chưa bao giờ mở trong lúc kiểm thì nhánh logic qua nó không được kiểm. Với
  `T1_LINE` v1, nếu không có ngăn nào đang ăn điện từ thanh cái vòng thì lỗi vẫn
  lọt. **Đây là hạn chế thật, không được quảng cáo cổng này là chứng minh đầy đủ.**
  Giảm nhẹ: ghi lại độ phủ trạng thái đã kiểm vào bản chốt, và nói rõ nhánh nào
  chưa từng được kiểm.
- **Cổng lấy `IsLive` của OneATS làm chuẩn.** OneATS sai thì ta khớp với cái sai.
  Chấp nhận được: sản phẩm này thay HMI của họ, khớp ngữ nghĩa của họ là mức nền.
- Template thành dữ liệu của bản cài → sinh ra nghĩa vụ **backup, migrate, phiên
  bản hoá** chưa từng có. Store thêm bảng, `releases` phải dựng (hiện chưa tồn tại).
- Trình soạn đồ thị là **việc lớn**, không nhét vừa một giai đoạn đang chạy.
- `infer_bay_type()` bỏ đi là **refactor có thể âm thầm làm sai**. Bắt buộc phải
  có test khoá trước khi động vào: *bộ template hiện tại vẫn phải cho ra đúng
  12/12 phân loại và 80/80 thiết bị như hôm nay*.

### Việc phải làm để ADR này không mục

- [ ] Test khoá 12/12 + 80/80 **trước** khi bỏ `infer_bay_type()`.
- [ ] `tools/check.py` gác: không có đường ghi nào vào `domain/templates/*.yaml`
      lúc chạy — seed là một chiều, file gốc bất biến.
- [ ] Cổng chứng minh phải **chặn** được, không chỉ cảnh báo. Một cổng bỏ qua
      được là một cổng không tồn tại.
- [ ] Bản chốt ghi độ phủ trạng thái đã kiểm, để không ai đọc "đã chứng minh"
      thành "đã chứng minh mọi nhánh".
- [ ] **Xin model trạm thứ hai** (Q4). Nếu trạm thứ hai cũng ra 12/12 thì trình
      soạn template là chuyện quy mô; nếu ra một nửa `UNKNOWN` thì nó là việc gấp.
      Đây là phép thử rẻ nhất và quyết định nhất cho toàn bộ ADR này.
