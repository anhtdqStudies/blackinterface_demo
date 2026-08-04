# ADR-0008 — Bay template là YAML khai báo, slot ánh xạ LN → vị trí điện

**Status**: Accepted · **Date**: 2026-08-04
**Liên quan**: ADR-0002 (topology từ DataServer), ADR-0003 (không canvas vẽ)

---

## Bối cảnh

Sau ADR-0002, topology phải sinh ra từ DataServer. DataServer cho biết **ngăn nào
có logical node nào** nhưng **không cho biết chúng đấu với nhau ra sao** — không có
connectivity node, không có terminal, không có quan hệ điện.

Đo ngày 2026-08-04 trên `DEMO_SAS` v654 cho thấy điều bù lại: quy ước đánh số LN
của ATS/EVN **đã mã hoá sẵn vị trí điện**. `XSWI1` luôn là dao chọn thanh cái 1,
`XSWI7` luôn là dao đường dây, `XSWI91/92` luôn là tiếp địa phía thanh cái vòng.
Xác nhận trực tiếp: `D03.XSWI1.SName = "-1"`, `D03.XSWI71.SName = "-75"`.

Vậy bài toán *tái dựng đồ thị từ dữ liệu mơ hồ* (không giải được — xem ADR-0002)
trở thành bài toán *tra bảng*.

Câu hỏi còn lại: bảng đó ở dạng nào.

---

## Quyết định

**Template là file YAML khai báo trong `domain/templates/`, một file một loại ngăn.**

Mỗi template gồm:

- `bay_type` — loại ngăn nó phục vụ; **duy nhất một template cho một loại**
- `nodes[]` — connectivity node nội bộ, khai báo theo **thứ tự dọc từ thanh cái xuống**
- `slots[]` — mỗi slot ánh xạ `ln` → `role` + `endpoints[2]` + gợi ý bố cục

`endpoints` dùng 3 loại tham chiếu:

| Dạng | Nghĩa | Giải quyết lúc build |
|---|---|---|
| `n_*` | node nội bộ của template | `{bay_id}.{node_id}` |
| `BB1` `BB2` `BB9` `BB` | thanh cái của cấp điện áp | tra `Subs.BB<mã cấp><chỉ số>` |
| `EARTH` | đất | một node đất dùng chung toàn trạm |

Ví dụ (`T1_LINE.yaml`):

```yaml
slots:
  - {ln: XSWI1,  role: busbar_selector,   endpoints: [BB1, n_bb],     order: 0}
  - {ln: XCBR1,  role: breaker,           endpoints: [n_bb, n_mid],   order: 2}
  - {ln: XSWI7,  role: line_disconnector, endpoints: [n_mid, n_line], order: 3}
  - {ln: XSWI71, role: earth_switch,      endpoints: [n_line, EARTH], order: 4, side: left,
     required: false}
```

Ba hệ quả trực tiếp của thiết kế này:

1. **Trạm mới = file YAML mới**, không phải nhánh code mới.
2. **Bố cục sinh từ template**, không phải heuristic trong code vẽ.
   `order` + `side` là dữ liệu; `diagram/layout.py` chỉ dịch chúng ra toạ độ.
3. **Thiếu slot bắt buộc = ERROR có tên**, không phải graph khuyết âm thầm.

---

## Phương án đã bác bỏ

### A. Template viết bằng Python (class/dataclass)
Mạnh hơn, nhưng thêm loại ngăn thành sửa code → phải review, phải test, phải
release. Kỹ sư trạm không sửa được. **Bác bỏ**: template là *dữ liệu cấu hình của
một trạm cụ thể*, không phải logic sản phẩm.

### B. Suy đấu nối bằng thuật toán từ tên thiết bị
Chính là thứ ADR-0002 đã chứng minh không làm được: tên không phải định danh duy
nhất (`DS9` xuất hiện 4 lần trên C29). **Bác bỏ.**

### C. Không có node nội bộ — nối thẳng thiết bị với thiết bị
Đơn giản hơn nhưng sai mô hình: ba dao chọn thanh cái cùng nối vào **một điểm
chung** trước máy cắt. Không có connectivity node thì không biểu diễn được điểm
chung đó, và energization solver (module #2) sẽ không chạy được. **Bác bỏ.**

### D. Nhét luôn toạ độ x/y vào template
Trói template vào một kích thước hiển thị. **Bác bỏ**: template giữ *thứ tự* và
*phía* (`order`, `side`); `diagram/` giữ khoảng cách pixel.

---

## Hệ quả

**Tốt**

- 13/13 ngăn của `DEMO_SAS` dựng đúng, **80/80 thiết bị đóng cắt được đặt vào graph**,
  0 lỗi. Con số 80 khớp với lần đo độc lập trước đó.
- Không khớp template thì `UNKNOWN` + báo lý do, **không đoán** (ADR-0005 tinh thần).
- Test được không cần DataServer: fixture → observation → graph.

**Phải chấp nhận**

- Trạm dùng quy ước LN khác ATS/EVN sẽ không tự nhận dạng. Chấp nhận được: sản
  phẩm nhắm vào trạm do ATS dựng.
- Mã thanh cái theo cấp điện áp (`BB2x` = 220kV) **mới đo được cho 110kV và 220kV**.
  22kV/35kV/500kV là GIẢ ĐỊNH — đã ghi rõ trong `topology.py`, và khi không tìm
  thấy thì tạo placeholder + cảnh báo chứ không im lặng.
- Kết luận này mới verify trên **một trạm**. Câu hỏi mở Q4.

**Đính chính một điểm trong bản nháp trước**

`docs/20-domain/bay-templates.md` §T6 ban đầu coi `DBB`/`EBB` **là thanh cái**.
Đo lại cho thấy chúng là **bảo vệ so lệch thanh cái** (F87B1..3, F50BF) — thanh cái
thật nằm ở `/SAS/Subs/BB11..BB29`, có `IsLive`, `Hz`, `PPV*`. Template T6 giữ tên
`BUSBAR_PROTECTION` và không sinh thiết bị nào.
