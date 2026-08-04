# ADR-0003 — Không làm canvas vẽ; template + view sinh tự động

- **Status**: Accepted
- **Date**: 2026-08-04

## Bối cảnh

Hai hướng được cân nhắc cho phần View:

- **Hướng 1**: từ SLD + DataModel → mô hình hoá lại một SLD giống HMI hiện tại,
  hệ tự vẽ, user chỉnh sửa → publish.
- **Hướng 2**: không vẽ SLD; lúc cần thì sinh một phần SLD, vì "cũng không ai xem".

Ý tưởng ban đầu nghiêng về: extract thiết bị từ SLD rồi **kéo thiết bị vào vẽ lại**.

## Quyết định

**Tách hai khái niệm đang bị gộp: topology là tài sản, bản vẽ là view.**

1. **Topology (đồ thị liên kết điện)** — bắt buộc, đầy đủ, luôn có. Không phải để vẽ đẹp
   mà vì thiếu nó thì không trả lời được *"thanh cái C22 còn điện không"*,
   *"ngăn nào mất nguồn khi CB 271 nhảy"*, *"đoạn này đã cắt điện và tiếp địa chưa"*.
2. **Bản vẽ** — sinh từ topology, lúc cần, theo scope cần (view ngăn, view đoạn thanh cái,
   view đường đi từ nguồn, view toàn trạm). Không phải asset engineer bảo trì.
3. **Không có canvas kéo-thả tự do.** Engineer **xác nhận**, không **vẽ**.
   UI là bay-card: mỗi ngăn một thẻ, engineer chỉ chạm chỗ có cảnh báo.
4. Layout **sinh tự động** từ template (bay = cột, busbar = rail ngang,
   thiết bị xếp dọc theo slot order). Override của engineer lưu dưới dạng
   **sparse patch layer** (`{bay_id: {x_order: 3}}`), **không** lưu toạ độ tuyệt đối —
   để import lại không thổi bay công sức chỉnh tay.

## Phương án đã bác bỏ

- **Canvas vẽ tự do (hướng 1 nguyên bản)** — đó là viết lại Grid Designer, đúng cái
  đang muốn thay thế. Khối lượng lớn (symbol library, routing, snapping, layering),
  và đưa một bước thủ công vào critical path của *mọi* project → giết value prop.
  Cũng tái tạo lại đúng failure mode đang muốn thoát: layout vẽ tay trôi khỏi model.
- **Bỏ hẳn topology (hướng 2 nguyên bản)** — nhận định "không ai xem SLD" đúng trong
  vận hành bình thường (lúc đó người ta nhìn alarm), nhưng **sai ở đúng thời điểm
  quan trọng nhất**: khi có sự cố, sơ đồ là công cụ số một. Mà đó chính là lúc
  mục tiêu M2 kích hoạt. Một bảng point không thay thế được topology.
- **Lưu toạ độ tuyệt đối cho từng shape** — làm re-import phá công sức chỉnh tay.

## Hệ quả

**Tích cực**
- Thời gian polish của engineer: phút, không phải ngày. Và re-runnable.
- Bài toán *tái dựng đồ thị từ chuỗi mơ hồ* (không giải được) → *tra bảng template*
  (giải được, verify được).
- View sinh theo ngữ cảnh hợp với chat-first hơn là một màn hình cố định.

**Tiêu cực / cần chú ý**
- Phải xây thư viện bay template (ADR-0002, `docs/20-domain/bay-templates.md`).
  Ước tính 6 template phủ hết DEMO_SAS — vài ngày, không phải vài tuần.
- Ngăn không khớp template nào → `UNKNOWN`, phải có đường thoát cho engineer.
  **Không đoán**, ghi validation issue với lý do cụ thể.
- Chất lượng auto-layout quyết định cảm nhận sản phẩm. Cần đầu tư vào layout engine
  hơn là vào editor.
