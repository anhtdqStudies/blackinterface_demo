# ADR-0005 — AI không nằm trên đường đi của tính đúng đắn

- **Status**: Accepted
- **Date**: 2026-08-04

## Bối cảnh

Hai câu hỏi kiến trúc liên quan nhau:

1. Thiết kế ban đầu ghi *"Frontend không gọi thẳng Integration hay Diagram —
   mọi thứ đi qua BlackCore và Domain API"*. Nếu hiểu là **mọi** tương tác UI đi qua
   LLM agent thì: latency vài giây cho thao tác lẽ ra 50ms, tốn token cho việc không
   cần suy luận, non-deterministic ở chỗ cần deterministic, và **UI chết khi LLM chết**
   — không chấp nhận được với phòng điều khiển.
2. Mục tiêu M2 ("phân tích lỗi, đưa hướng dẫn xử lý") nghe như việc của LLM.
   Nhưng sai một bước nhân quả trong phân tích sự cố điện là sai nghiêm trọng.

Ràng buộc triển khai: máy trạm có thể air-gapped → model local nhỏ (7–14B).
Model nhỏ suy luận yếu.

## Quyết định

**Thiết kế sao cho LLM không load-bearing cho tính đúng đắn.**

### 1. Hình dạng gọi

```
Web ──┬──────────────────────────> Domain API   (deterministic: view, data, SSE)
      └──> BlackCore ────────────> Domain API   (chỉ cho lượt hội thoại NL)
```

BlackCore gọi **đúng** API mà UI gọi — không đường riêng, không quyền cao hơn.
Frontend **không** gọi thẳng `integration/` hay `diagram/` (điều này giữ nguyên),
nhưng **được** gọi thẳng `api/`.

### 2. Phân tích sự cố là engine deterministic

Bước 1–5 của quy trình phân tích là deterministic khi có topology + SOE + ngữ nghĩa
LN bảo vệ:

1. Lấy SOE theo thứ tự thời gian, độ phân giải ms
2. Tìm sự kiện khởi phát (cái đầu tiên; còn lại là hệ quả)
3. Tương quan nhân quả: bảo vệ pickup → trip → CB mở → mất nguồn ở đâu
4. Đánh giá: bảo vệ tác động đúng? backup tác động (⇒ chính hỏng)? RBRF (⇒ CB từ chối)?
5. Phạm vi ảnh hưởng: graph traversal trên topology

→ `analyze_event(t_start, t_end)` là **tool backend thật**, trả về chuỗi nhân quả
có cấu trúc. **LLM chỉ diễn đạt, không sinh ra chuỗi nhân quả.**

### 3. AI được / không được

**Được**: hiểu intent, chọn tool, chọn view, tóm tắt, giải thích kèm evidence.
**Không được**: bịa topology/connectivity/mapping, ghi OPC UA, điều khiển,
biến giả thuyết thành sự thật, tự soạn evidence (ADR-0004).

## Phương án đã bác bỏ

- **BlackCore làm proxy cho mọi request** — xem Bối cảnh §1.
- **Để LLM sinh chuỗi nhân quả sự cố** — không kiểm chứng được, sai nghiêm trọng,
  và không chạy nổi trên model 7B local.
- **Yêu cầu model lớn để bù** — biến sản phẩm thành phụ thuộc cloud, mâu thuẫn với
  ràng buộc air-gapped của trạm.

## Hệ quả

**Tích cực**
- **Bảo mật**: AI về mặt cấu trúc không làm được gì mà user không tự làm được qua UI.
  Không phải tin vào prompt.
- **Testability**: test end-to-end không cần LLM.
- **Degradation**: LLM chết → mất chat, còn nguyên HMI.
- Model 7B local là đủ → chạy được offline tại trạm.

**Tiêu cực**
- Phải viết engine phân tích deterministic — công sức lớn hơn "để LLM lo".
  Đây là chi phí có chủ đích.
- Phạm vi câu hỏi AI trả lời được bị giới hạn bởi tập tool. Chấp nhận:
  thà từ chối còn hơn bịa.
