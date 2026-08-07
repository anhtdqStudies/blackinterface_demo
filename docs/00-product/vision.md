# Black Interface — Tầm nhìn sản phẩm

## Vấn đề

Vận hành trạm điện trên OneATS hiện tại dựa vào Grid Designer / Grid Viewer:

1. **Dựng project tốn thời gian.** Kỹ sư vẽ tay sơ đồ một sợi bằng công cụ vẽ,
   rồi gán từng thiết bị với từng point trong DataServer qua OPC UA. Mỗi trạm
   là hàng trăm thao tác thủ công, lặp lại cho mọi trạm dù cấu trúc ngăn giống nhau.
2. **Giám sát tốn thời gian.** Người vận hành phải biết đi đúng màn hình, đúng tab,
   đúng symbol. Khó tra cứu, khó giải thích.
3. **Có alarm nhưng không có phân tích.** Alarm báo *có vấn đề*, không nói *vấn đề gì*,
   *vì sao*, *xử lý thế nào*. Muốn biết thì phải tự đọc log.

## Sản phẩm

Lớp vận hành AI-first **thay thế HMI tĩnh**, cài **local** trên server tại trạm.
Thay vì "mở đúng màn hình để xem trạng thái", người dùng hỏi bằng ngôn ngữ tự nhiên
và hệ thống trả lời kèm bằng chứng.

### Hai mục tiêu — đúng hai cái

**M1. Rút ngắn thời gian dựng project**
Trỏ vào OneATS DataServer (đã dựng xong) → ra HMI chạy được. Không vẽ tay, không map
point thủ công.
*Đã đo được tính khả thi:* 100% thiết bị đóng cắt auto-bind, 12/12 loại ngăn suy đúng
từ DataServer. Xem `docs/30-integration/oneats-dataserver.md`.

**M2. Giám sát realtime + phân tích sự cố**
Alarm vẫn chạy như cũ. Khi có vấn đề, hệ thống dựng chuỗi nhân quả, xác định phạm vi
ảnh hưởng, đề xuất hướng xử lý — kèm evidence.

### Ba trụ cột

| Trụ cột | Nội dung |
|---|---|
| **Conversation** | Chat-first workspace, hỏi bằng tiếng Việt tự nhiên |
| **Evidence** | Mọi câu trả lời có nguồn: tool nào, scope nào, quality/timestamp, hạn chế gì |
| **View** | SLD, panel đo, alarm list, timeline… **sinh theo ngữ cảnh**, không vẽ sẵn |

---

## Nguyên tắc: Topology là tài sản, bản vẽ là view

Quyết định sản phẩm quan trọng nhất (ADR-0003).

- **Topology (đồ thị liên kết điện)** — bắt buộc, đầy đủ, luôn có. Không phải để vẽ đẹp
  mà vì thiếu nó thì không trả lời được: *"thanh cái C22 còn điện không"*,
  *"ngăn nào mất nguồn khi CB 271 nhảy"*, *"đoạn này đã cắt điện và tiếp địa chưa"*.
  Một bảng point không bao giờ trả lời được những câu này.
- **Bản vẽ** — sinh ra từ topology, lúc cần, theo scope cần. Không phải asset
  engineer phải bảo trì.

Hệ quả: **engineer không vẽ, engineer xác nhận.** Không có canvas kéo-thả tự do —
làm vậy là viết lại Grid Designer, đúng cái đang muốn thay thế.

---

## Hai vai trò

| Vai trò | Làm gì | Workspace |
|---|---|---|
| **Engineer** | Kết nối DataServer, duyệt topology auto-derive, sửa ngoại lệ, publish | Engineer Config |
| **Operator** | Xem HMI đã publish, hỏi AI, theo dõi realtime/alarm | Operator AI |

---

## Luồng dựng project (đã đơn giản hoá theo ADR-0002)

```
nhập endpoint DataServer
   → browse address space          (~17.9k node, 2–3 phút)
   → suy bay_type từ LN            12/12 đúng
   → áp bay template → topology    deterministic, correct-by-construction
   → auto-bind PosSt/Name/quality  100%
   → engineer duyệt ngoại lệ       ~5 phút
   → publish, pin ModelVersion
```

**Không file nào. Không vẽ gì.** SLD *không* nằm trong MVP — xem ADR-0002.

---

## Phạm vi MVP

**Trong phạm vi**
- Một trạm, **read-only**
- Auto-derive topology + binding từ DataServer
- Bay-card review UI (engineer chỉ chạm chỗ có cảnh báo)
- Release có hash, pin `ModelVersion`
- SLD sinh tự động + overlay live, alarm list, measurement panel
- Event store cục bộ + SOE (nền cho M2)
- 4 tool: `list_bays`, `get_bay_snapshot`, `get_active_alarms`, `resolve_object`

**Trong phạm vi, nhưng ở GIAI ĐOẠN CUỐI** *(chốt 2026-08-05, ADR-0011)*
- **Module C — Control**: điều khiển đóng/mở MC, tăng/giảm nấc MBA (C-09),
  đặt tagging (C-07). Đi qua `control/` — đường ghi duy nhất, registry hiện rỗng.
- Phần **đọc** của module C (C-01 interlock, C-02 authority, C-08 tagging) làm
  được sớm hơn, và `guard.py` dùng lại được cho cả hai.
- **Agent không bao giờ có tool ghi** — kể cả sau khi mở. Agent soạn phiếu, người ký.

**Ngoài phạm vi MVP**
- Import SLD (giữ cho phase sau, chỉ để đối chiếu)
- SmartHIS / trend dài hạn
- SOP RAG
- Multi-project, multi-station (OCC)
- Canvas kéo-thả

---

## Ba rủi ro kỹ thuật thật sự còn lại

Không rủi ro nào nằm ở chỗ tưởng là khó (parse SLD, map point).

1. **Suy trạng thái mang điện (energization / coloring)** — lan truyền từ Source trên
   graph. Lưu ý `IsLive` đã tồn tại ở cấp bay trong DataServer: phải kiểm tra OneATS
   đã tính sẵn chưa, nếu rồi thì đối chiếu chứ đừng tính lại mù.
2. **Event store + SOE** — `GetActiveAlarm` chỉ cho hiện tại. Không tự buffer thì
   M2 không tồn tại.
3. **Decode struct alarm cho chắc** — bản reverse-engineer chạy 243/243 nhưng field
   cuối còn lệch. Cần xin ATS định nghĩa chính thức.
