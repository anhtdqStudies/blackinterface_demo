# ADR-0001 — Neutral Station Model là contract trung tâm

- **Status**: Accepted
- **Date**: 2026-08-04

## Bối cảnh

Hệ phải hợp nhất nhiều nguồn không đồng nhất: OPC UA address space của OneATS
(NodeId dạng `ns=2;s=D03.XCBR1.PosSt`), CIM/DataModel, SLD extract, và sau MVP là
SmartHIS + SOP. Mỗi nguồn có mô hình định danh riêng.

Nếu UI/AI/API chạm thẳng vào các nguồn này thì: đổi nguồn = sửa mọi lớp; AI thấy
NodeId thô và có thể bịa; không có chỗ nào gắn provenance để làm evidence.

## Quyết định

**Mọi nguồn đi qua Neutral Station Model. UI, AI, API không bao giờ chạm raw
CIM / SCD / DataModel / OPC UA NodeId.**

Nội dung model:

| Thành phần | Ghi chú |
|---|---|
| **Identity** | `black_id` ổn định + `source_refs[]` (opcua_nodeid, cim_mrid, sld_element_id) |
| **Topology** | node-breaker (connectivity node + terminals) — khớp mô hình OneATS (manual A.5) nên import không mất mát |
| **Geometry** | lớp riêng, tham chiếu id topology |
| **Binding** | `point_ref = {black_id, measurement_kind, node_id, snapshot_id, bound_by}` |
| **Provenance** | theo từng field: importer nào, rule nào, ai xác nhận, khi nào |
| **Validation issues** | gắn vào object, có severity |

Ràng buộc:
- **`NodeId` không bao giờ là primary key** — nó đổi khi project OneATS recompile.
- Chỉ `integration/` được biết NodeId. `domain/` không import lớp nào khác.
- Model **immutable + versioned + content-addressed**. Release = hash nội dung model.
  Evidence trích dẫn release hash.
- Bus-branch model chỉ derive khi cần phân tích; node-breaker là dạng lưu trữ.

## Phương án đã bác bỏ

- **Dùng NodeId làm khoá chính** — hấp dẫn vì NodeId của OneATS đọc được bằng mắt
  (`D03.XCBR1.PosSt`), nhưng nó gắn với build của project OneATS. Recompile là gãy
  toàn bộ release cũ và mọi evidence đã trả lời.
- **Cho AI truy cập trực tiếp OPC UA** — mất chỗ gắn provenance, mất khả năng cưỡng chế
  read-only bằng cấu trúc, và AI có thể tham chiếu node không tồn tại.
- **Dùng thẳng CIM làm domain model** — CIM quá rộng và nặng cho phạm vi một trạm;
  ta chỉ cần một tập con, cộng thêm binding/provenance mà CIM không có.

## Hệ quả

**Tích cực**
- Đổi/thêm nguồn (SmartHIS, SOP, trạm dùng Modbus) không lan ra UI/AI.
- Provenance có chỗ để sống → evidence-first khả thi (ADR-0004).
- Test được: dựng model từ fixture, không cần DataServer thật.

**Tiêu cực**
- Thêm một lớp ánh xạ phải bảo trì.
- Cần kỷ luật: mọi cám dỗ "gọi tắt xuống OPC UA cho nhanh" phải bị chặn ở code review.
  Cưỡng chế bằng ranh giới import (xem `tools/check.py`).
