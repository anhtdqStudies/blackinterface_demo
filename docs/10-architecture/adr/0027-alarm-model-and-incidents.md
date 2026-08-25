# ADR-0027 — Alarm: phân loại, gom cụm thành sự cố, và hướng dẫn xử lý

- **Status**: Accepted
- **Date**: 2026-08-13
- **Liên quan**: [ADR-0026](0026-alarm-channels.md) (kênh dữ liệu) ·
  [ADR-0013](0013-evidence-envelope.md) (evidence) · [ADR-0010](0010-scope-and-facet.md) (scope)

## Bối cảnh

Đo trên DEMO_SAS 2026-08-13: trạm **bình thường** có **243 alarm active**, phân bố:

| point suffix | số lượng | thực chất |
|---|---|---|
| `.PosSt` / `.PosSt1` | 90 | vị trí đóng cắt — `CB 271 STATUS` = `2 (CLOSED)`, máy cắt đóng bình thường |
| `.TimeFail` | 41 | relay mất đồng bộ thời gian — **bất thường thật** |
| `.SG1` | 35 | nhóm chỉnh định đang dùng — bình thường |
| `.FAC2xx` | ~20 | trạng thái aptomat tủ AC |
| `.OilTmpTr` `.OilLevAlm` `.Vlin` `.PPVmax` | 4 | **bất thường thật** |

Toàn bộ 243 `t_active` nằm trong cùng **570 ms** — thời điểm nạp project.

Nói cách khác: cái OneATS gọi là "active alarm" phần lớn là **danh sách điểm đang
được giám sát kèm giá trị hiện tại**, không phải nhật ký sự kiện. Đổ 243 dòng đó lên
giao diện là tái tạo đúng cái HMI mà sản phẩm này định thay thế
(`docs/00-product/vision.md`: *"Alarm báo có vấn đề, không nói vấn đề gì"*).

Và `team.md` B3 đề xuất lọc bằng `severity >= 800` — **sai với dữ liệu thật**: chỉ 1
alarm đạt ngưỡng đó (`OilTmpTr`), trong khi `ABNORMAL VOLTAGE` (650) và 41 `TimeFail`
(360) đều là bất thường thật.

## Quyết định

### 1. Phân loại bằng bảng tra, không bằng ngưỡng severity

Severity dùng để **xếp hạng**, không dùng để **phân loại**. Khoá phân loại là bộ ba:

```
(category, point suffix, actor có rỗng không)  ->  AlarmClass
```

```python
class AlarmClass(StrEnum):
    FAULT   = "fault"     # bất thường thật
    STATUS  = "status"    # trạng thái đóng cắt — KHÔNG tự tạo sự cố
    CONFIG  = "config"    # nhóm chỉnh định, cấu hình
    ACTION  = "action"    # do người vận hành thao tác (actor khác rỗng)
    UNKNOWN = "unknown"   # chưa có luật
```

**`UNKNOWN` phải hiện lên giao diện, không được im lặng bỏ qua.** Một alarm chưa có
luật là lỗ hổng trong bảng, và lỗ hổng im lặng thì không ai vá (cùng lý lẽ với I7).

**`ACTION` thắng mọi phân loại khác.** `actor` khác rỗng nghĩa là có người vừa thao
tác — không bao giờ được báo là sự cố. Thiếu luật này thì lúc trình diễn, người vận
hành mở một máy cắt và hệ thống lập tức báo động kèm hướng dẫn xử lý.

Bảng nằm ở `domain/alarm_rules/*.yaml`, không phải `if` lồng nhau: mỗi trạm một
dialect point, và bảng sẽ bị sửa thường xuyên hơn code.

### 2. Gom cụm thành `Incident` — deterministic, không LLM

Đo được một chuỗi lan truyền thật (2026-08-13, thao tác trên simulator):

```
05:04:16.727  D01.XCBR1.PosSt     CB 231 STATUS      1 (OPENED)  sev 200
05:04:16.736  E01.MMXU1.Vlin      ABNORMAL VOLTAGE               sev 650
05:04:16.747  D01.MMXU1.Vlin      ABNORMAL VOLTAGE               sev 650
05:04:16.751  Subs.BB11.PPVmax    ABNORMAL VOLATGE               sev 650
05:04:16.754  Subs.BB12.PPVmax    ABNORMAL VOLATGE               sev 650
05:04:16.757  Subs.BB19.PPVmax    ABNORMAL VOLATGE               sev 650
05:04:16.780  E02.MMXU1.Vlin      ABNORMAL VOLTAGE               sev 650
05:04:16.814  E04.MMXU1.Vlin      ABNORMAL VOLTAGE               sev 650
```

Một máy cắt mở → 7 alarm điện áp trên 4 ngăn và 3 thanh cái, **trong 87 ms**.

Luật gom:

1. **Thời gian** — cửa sổ mặc định **200 ms**, tính trên `t_active` của DataServer
   (độ phân giải 100 ns), **không** tính trên thời điểm ta nhận được. Chuỗi thật gói
   trong 87 ms; cửa sổ hàng giây sẽ nuốt cả những thứ không liên quan.
2. **Không gian** — cùng ngăn, **hoặc** cùng vùng mang điện trước thời điểm sự cố
   (`domain/energization.py`). Sự cố lan theo điện, không theo tên ngăn: `Subs.BB11`
   không cùng ngăn với `D01` nhưng cùng một chuỗi.
3. **Hạt giống** — chỉ `FAULT` tạo sự cố. `STATUS` cùng cửa sổ, cùng phạm vi thì được
   **hút vào làm bằng chứng**: máy cắt mở là dữ kiện quan trọng nhất của sự cố nhưng
   không phải lý do báo động.
4. **Chống rung** — một point vào/ra nhiều lần trong cửa sổ thì nén thành một mục
   *đang dao động*, không phải N sự cố. Trong chính chùm đo được, `E01.MMXU1.Vlin`
   xen kẽ `LoLimitExceeded` (sev 650) và `ReturnToNormal` (sev 0) nhiều lần.

Toàn bộ bước này là hàm thuần, dựng lại mỗi lô. Cùng lý lẽ với `build_station`
(0,7 ms — `AGENTS.md` §7): dựng lại rẻ và **bảo đảm** kết quả giống hệt tính mới,
sửa tại chỗ thì không hứa được điều đó.

**Gom cụm cho ta *nhóm*, không phải *quan hệ nhân quả*.** Chuỗi nhân quả là `trace`
(ADR-0024, chưa viết). Không được để giao diện ngụ ý rằng alarm đầu tiên trong cụm
là nguyên nhân — nó chỉ là cái đến sớm nhất.

### 3. Hướng dẫn xử lý là **dữ liệu tra theo khoá**, không phải văn LLM

```
(point suffix | mẫu message, loại thiết bị)  ->  Playbook
```

- `domain/playbooks/*.yaml`, nạp như `domain/templates.py`.
- Trả về **typed object** trong payload, kèm `EvidenceRecord` (I3: hướng dẫn do tool
  sinh, không phải mô hình viết).
- Không khớp → trả rỗng và nói rõ *chưa có hướng dẫn*. **Cấm để LLM tự chế.**

**Mỗi playbook mang một trường `status`.** Hiện toàn bộ là `draft` — chúng do agent
soạn, **chưa ai có thẩm quyền vận hành duyệt** (2026-08-13: trạm chưa có tài liệu xử
lý sự cố). Giao diện **bắt buộc** hiển thị trạng thái này ngay cạnh nội dung. Một
hướng dẫn chưa duyệt trông giống hệt hướng dẫn đã duyệt là cách nhanh nhất để biến
một công cụ hữu ích thành một mối nguy.

Module F (Knowledge/RAG, GĐ 4) sau này chỉ thay **nguồn** của cùng trường đó — không
đụng tool, không đụng schema, không đụng giao diện. Đó là lý do chọn hình dạng này
thay vì nhét vào system prompt.

## Hệ quả

**Tích cực**
- 243 dòng nhiễu → vài sự cố có nghĩa. Đây là toàn bộ lý do tồn tại của module.
- Bảng phân loại và playbook là dữ liệu → sửa được mà không cần deploy lại.
- `ACTION` tách thao tác của người khỏi sự cố ngay ở tầng domain.

**Tiêu cực / rủi ro**
- Bảng phân loại phải nuôi theo từng trạm. `UNKNOWN` nổi lên giao diện là cơ chế
  phát hiện thiếu luật, và nó sẽ ồn lúc mới lắp một trạm mới. Chấp nhận.
- Cửa sổ 200 ms suy từ **một** chuỗi đo được. Cần đo thêm vài chuỗi nữa; tham số hoá
  `BI_ALARM_CLUSTER_WINDOW_MS` để chỉnh không cần sửa code.
- Playbook `draft` do agent soạn có thể sai về nghiệp vụ điện. Giảm thiểu bằng nhãn
  trạng thái hiện rõ, không bằng việc tin rằng nội dung đúng.
