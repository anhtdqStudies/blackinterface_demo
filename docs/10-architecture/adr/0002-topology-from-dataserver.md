# ADR-0002 — Topology suy từ DataServer, SLD ra khỏi MVP

- **Status**: Accepted
- **Date**: 2026-08-04

## Bối cảnh

Thiết kế ban đầu: input project gồm 2 file — SLD (topology + geometry seed) và
OneATS DataModel (point catalog + runtime binding). Câu hỏi mở: có cần DataModel không,
vì quét DataServer cũng ra?

Đã đo trực tiếp trên hệ chạy thật (`docs/30-integration/oneats-dataserver.md`, 2026-08-04),
so sánh hai nguồn trên cùng một trạm:

| | DataServer | SLD extract (CV) |
|---|---|---|
| Số ngăn | 13 (có J01 22kV) | 12 — **sót J01** |
| Số hiệu EVN | 271, 212, 112… đúng | **179 sai cho 4 ngăn** (D03/D04/E01/E02) |
| Loại ngăn | suy đúng 12/12 | có sẵn |
| Thiết bị đóng cắt | 80, đầy đủ | thiếu (D01: 6 vs 7) |
| Trạng thái + quality + ts | có, realtime | không |
| Dữ liệu thiếu | 0% | 20–26% thiếu tên, 36–40% thiếu connections |

Thêm nữa: chuỗi `connections` của SLD extract **không thể dựng thành graph** —
tên thiết bị không phải instance id (`C29-DS9,C29-DS9,C29-DS9,C29-DS9-ES94`:
bốn dao cách ly khác nhau cùng tên).

## Quyết định

1. **DataServer OPC UA browse là nguồn chính** cho device catalog, định danh, binding.
2. **Bỏ import file DataModel** khỏi luồng bắt buộc (giữ như enrichment tùy chọn
   cho trường hợp chưa có DataServer chạy).
3. **Bỏ SLD khỏi MVP.** Giữ cho phase sau như nguồn đối chiếu tùy chọn.
4. Topology sinh từ **bay template** (ADR-0003) áp lên device list của DataServer.
5. Point catalog phải **freeze thành snapshot có hash**, pin vào release kèm
   `OADataModel.ModelVersion`. Runtime chỉ lấy giá trị live (invariant I7).

Luồng build:
```
endpoint DataServer → browse → suy bay_type → áp template → auto-bind
→ engineer duyệt ngoại lệ → publish (pin ModelVersion)
```

## Phương án đã bác bỏ

- **Giữ SLD làm nguồn topology chính** — thua trên mọi trục đo được, và chuỗi
  `connections` về nguyên tắc không parse được thành graph.
- **Yêu cầu file DataModel export** — tạo thêm failure mode đồng bộ (file lỗi thời),
  trong khi browse cho dữ liệu tươi hơn và đầy đủ hơn.
- **Live browse mọi lúc, không snapshot** — vi phạm evidence-first: mọi câu trả lời
  đã đưa ra sẽ thành nói dối hồi tố khi ai đó sửa project OneATS. Cũng chặn khả năng
  engineering offline (trạm thường air-gapped).

## Hệ quả

**Tích cực**
- Mục tiêu M1 đạt ở mức mạnh hơn dự kiến: **không file nào, không vẽ gì**.
- Gỡ hẳn service CV extract SLD khỏi critical path.
- Ít failure mode hơn (không đồng bộ file, không parse ảnh).

**Tiêu cực / cần chú ý**
- Phụ thuộc DataServer phải chạy được lúc build. Giảm nhẹ bằng snapshot: browse một lần,
  đóng băng, sau đó làm việc offline được.
- Mất thứ tự trái-phải của ngăn trên màn hình mà SLD cung cấp. Giảm nhẹ: thứ tự
  alphabet bay id đã đúng thứ tự vật lý trên trạm này (D01, D03, D04, D12, D17);
  engineer kéo lại mất 5 giây nếu sai.
- Chưa verify trên trạm thứ hai. **Cần kiểm chứng trên 2–3 trạm thật** trước khi
  coi là kết luận chung — hiện mới đo trên `DEMO_SAS`.
