# ADR-0016 — Vai và quyền: quyền là đơn vị, vai chỉ là gói; kiểm ở tầng facet

- **Status**: Accepted
- **Date**: 2026-08-06
- **Liên quan**: ADR-0010 (`scope × facet`) · ADR-0011 (một đường ghi, agent
  không có tool ghi) · ADR-0006 (triển khai local tại trạm) · ADR-0015 (template
  do engineer soạn)

---

## Bối cảnh

### Bối cảnh sản phẩm mới rõ (người dùng nêu 2026-08-06)

> *"Black Interface sinh ra cho các trạm **không người trực** và **trạm ít
> người**, tức là user không cần thiết phải quan sát SLD mà có thể dùng AI để
> tóm tắt phân tích báo cáo tình hình."*

Hai hệ quả trực tiếp, và cái thứ hai đổi hẳn tính chất bài toán:

1. **Màn hình mặc định không phải SLD.** Không ai ngồi nhìn sơ đồ cả ca. Cửa vào
   là **bản tóm tắt do AI dựng**; SLD là nơi *xác minh* khi cần nhìn tận mắt.
2. **Trạm không người trực nghĩa là truy cập từ xa.** Nên phân quyền ở đây là
   **bảo mật thật**, không phải chỉ chống thao tác nhầm. Bản nháp trước của phân
   tích này giả định có phòng điều khiển khoá cửa — giả định đó không còn đúng.

### ATS đã có mô hình vai — và nó khác mô hình ta tự nghĩ ra

`document/@Station_UseCases 1.xlsx` (tài liệu gốc của ATS) khai 5 actor với ma
trận actor × chức năng:

| Actor | Mô tả trong tài liệu | Chức năng |
|---|---|---|
| **Operator** — Vận hành viên | giám sát, trực tiếp thao tác, xử lý sự cố theo quy trình | A B C D E F |
| **Supervisor** — Trạm trưởng | giám sát ca trực, vận hành viên, điều phối chung, hỗ trợ xử lý sự cố lớn | B C E |
| **Maintenance** — Kỹ thuật viên | đảm bảo kỹ thuật cho trạm; kiểm tra thiết bị, truyền thông, nguồn AC/DC | A B D F |
| **Protection** — Kỹ sư relay | cài đặt, phân tích bảo vệ / reclose / trip / interlock, relay logic | B C F |
| **Admin** — Quản trị | quyền, tài liệu, knowledge base, audit | F + platform admin |

Bốn điều rút ra:

- **Hình dạng đúng**: họ cũng nghĩ theo ma trận vai × chức năng.
- **Độ mịn chưa đủ**: ở mức module thì *"có C"* không phân biệt được **soạn** lệnh
  với **ký** lệnh. Quyền phải mịn hơn một bậc.
- **Supervisor có C** — xác nhận việc tách `draft`/`sign` là đúng thực tế vận hành.
- **Không actor nào dựng mô hình.** Vì trong thế giới của họ Grid Designer đã dựng
  xong trước rồi. **Đó chính là bước sản phẩm này tự động hoá**, nên ta cần một
  vai mà danh sách của họ không có.

### Vì sao phải chốt bây giờ, khi Module C còn ở GĐ 5

Không phải vì màn hình đăng nhập khó. Vì bốn thứ này ăn vào khắp kiến trúc:

| Thứ | Giá nếu để sau |
|---|---|
| Mỗi API phải biết ai gọi | sửa lại **toàn bộ** route |
| **Agent gọi cùng bộ facet với người** | quyền nằm ở Vue thì agent đi vòng qua hết |
| Bằng chứng phải ghi ai hỏi | evidence cũ mất dấu vĩnh viễn |
| Giao diện ẩn/hiện theo quyền | ẩn theo *tên vai* cứng thì thêm vai là sửa khắp component |

---

## Quyết định

### 1. **Quyền** là đơn vị. **Vai** chỉ là gói dựng sẵn. Một người giữ nhiều vai

Đây là quyết định gốc, và nó hoà tan câu hỏi *"chia nhiều vai có ổn không"*.

```
quyền hiệu lực của một người  =  HỢP của các vai người đó giữ
```

Số vai chỉ gây phiền khi chúng **loại trừ nhau**. Ở đây không:

| Trạm | Cách gán |
|---|---|
| Trạm lớn, đủ người | A giữ `operator`, B giữ `supervisor` → hai người, tách nhiệm vụ thật |
| **Trạm ít người** | một tài khoản giữ `operator + supervisor + maintenance` |
| **Trạm không người trực** | trung tâm giữ `supervisor`; đội lưu động giữ `maintenance` |

Giữ nguyên **5 tên của ATS** làm gói mặc định — đó là ngôn ngữ khách hàng của họ
đã dùng, đừng phát minh từ mới — **cộng một vai thứ sáu** cho bước ATS không có.

### 2. Danh sách quyền

Mịn hơn module một bậc: **module × động từ**.

```python
class Capability(StrEnum):
    STATION_READ     = "station.read"      # A — sơ đồ, trạng thái, số đo
    ALARM_READ       = "alarm.read"        # B
    ALARM_ACK        = "alarm.ack"         # B — xác nhận cảnh báo
    EVENT_READ       = "event.read"        # B — SOE
    TREND_READ       = "trend.read"        # D
    REPORT_READ      = "report.read"       # E
    REPORT_EXPORT    = "report.export"     # E — xuất, gửi ra ngoài
    KNOWLEDGE_READ   = "knowledge.read"    # F
    KNOWLEDGE_WRITE  = "knowledge.write"   # F — sửa knowledge base
    PROTECTION_READ  = "protection.read"   # cài đặt bảo vệ, interlock, relay logic
    AGENT_ASK        = "agent.ask"         # hỏi AI
    CONTROL_DRAFT    = "control.draft"     # C — SOẠN phiếu thao tác
    CONTROL_SIGN     = "control.sign"      # C — KÝ phiếu thao tác
    MODEL_CONNECT    = "model.connect"     # nối DataServer, tải lại
    MODEL_EDIT       = "model.edit"        # template, override (ADR-0015)
    MODEL_PUBLISH    = "model.publish"     # chốt bản
    BINDING_READ     = "binding.read"      # NodeId, Dbpos thô (ADR-0014 §8)
    AUDIT_READ       = "audit.read"        # nhật ký ai làm gì
    ACCOUNT_MANAGE   = "account.manage"    # quản lý tài khoản
```

**`CONTROL_DRAFT` và `CONTROL_SIGN` là hai quyền riêng.** Đây là chỗ đáng giá
nhất của cả ADR này, và nó tốn đúng hai dòng ở đây so với việc viết lại toàn bộ
luồng Module C sau này.

Tách **quyền**, không bắt buộc tách **người**: trạm một người trực thì gán cả hai
cho một tài khoản — vẫn hai bước bấm, vẫn ghi đúng nhật ký, và không ai phải dùng
chung mật khẩu (thứ tệ hơn hẳn việc không có phân quyền, vì nó làm nhật ký nói dối).

### 3. Sáu gói vai

| Vai | Quyền |
|---|---|
| `operator` | `station.read` `alarm.read` `alarm.ack` `event.read` `trend.read` `report.read` `report.export` `knowledge.read` `agent.ask` **`control.draft`** |
| `supervisor` | tất cả của `operator` + **`control.sign`** + `audit.read` |
| `maintenance` | `station.read` `alarm.read` `event.read` `trend.read` `knowledge.read` `agent.ask` — **không có control** |
| `protection` | `alarm.read` `event.read` `knowledge.read` `agent.ask` `protection.read` `binding.read` `control.draft` |
| `admin` | `knowledge.write` `audit.read` `account.manage` `knowledge.read` `agent.ask` |
| **`engineer`** | `station.read` `alarm.read` `knowledge.read` `agent.ask` **`model.connect` `model.edit` `model.publish` `binding.read`** |

Ba nguyên tắc tách nhiệm vụ, cả ba đều cố ý:

1. **`engineer` không bao giờ có `control.sign`** — kể cả ở trạm một người. Người
   sửa được mô hình mà lệnh dựa vào thì không được tự ký lệnh. Người vừa định
   nghĩa "đúng" vừa tự chấm mình là mất luôn ý nghĩa của cả hai.
2. **`admin` không có quyền vận hành.** Cấp quyền cho người khác được, không tự
   cấp cho mình. Muốn vận hành thì phải được gán thêm vai vận hành, và việc gán
   đó nằm trong nhật ký.
3. **`maintenance` không có control** — theo đúng ma trận của ATS (A B D F).

`engineer` là vai thứ sáu ATS không có, vì nó phục vụ bước mà sản phẩm này tự
động hoá (ADR-0015).

### 4. Kiểm quyền ở **tầng facet** — một chỗ, không phải ba

```
        người bấm nút            agent gọi tool
              │                        │
              └───────────┬────────────┘
                          ▼
              ┌───────────────────────┐
              │   TẦNG FACET          │  ← kiểm ở ĐÂY. Nguồn sự thật duy nhất
              │   requires=Capability │
              └───────────────────────┘
```

| Tầng | Vai trò |
|---|---|
| **Facet (backend)** | **Thẩm quyền.** Mỗi facet khai `requires=` |
| Giao diện | Ẩn nút cho đỡ rối. **Không phải bảo mật** |
| `control/` | Kiểm **lại lần nữa** mọi lệnh ghi. Chỗ này không được sai (ADR-0011) |

Quyền nằm trong component Vue thì agent **đi vòng qua toàn bộ**, vì nó gọi thẳng
facet. Và agent chắc chắn sẽ có (GĐ 2).

### 5. Agent chạy **dưới quyền người đang hỏi**

Agent không bao giờ là một tài khoản có quyền riêng. `maintenance` hỏi AI thì AI
chỉ đọc được đúng những gì `maintenance` đọc được, và bằng chứng ghi tên
`maintenance` chứ không phải "agent".

Cộng với I1 (**agent vĩnh viễn không có tool ghi**): agent không leo quyền được
theo cả hai đường — không có công cụ ghi, và quyền đọc thì mượn của người hỏi.

### 6. Quyền là **chiều thứ ba** trên lưới đã có, không phải hệ thống mới

```
được phép?  =  f( quyền , facet , scope )
                          ▲        ▲
                          └────────┴── ADR-0010, đã có sẵn
```

Nên *"người này chỉ được thao tác trên `vl:110kV`"* diễn đạt được bằng từ vựng
hiện có, không phải phát minh gì. Ràng buộc theo scope **chưa làm ở giai đoạn
này**, nhưng chỗ cắm đã sẵn.

### 7. Tài khoản lưu ở SQLite cục bộ, để ngỏ cửa liên thông

Người dùng chốt 2026-08-06: *"nên gán luôn tài khoản vào sqlite… sau này có thể
đồng bộ database ngược cũng được"*. Đồng ý, vì:

- Triển khai là **local, offline, tại trạm** (ADR-0006). Trạm không người trực có
  thể không có domain controller nào để dựa vào.
- SQLite + migration đã có sẵn; thêm một bảng là việc nhỏ.
- Truy cập từ xa làm cho xác thực thành **yêu cầu**, không còn là tuỳ chọn.

Một chi tiết thiết kế **bắt buộc** để sau này liên thông được mà không phải dời dữ liệu:

```sql
CREATE TABLE users (
  id           INTEGER PRIMARY KEY,
  username     TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  password_hash TEXT,          -- NULL khi danh tính đến từ nguồn ngoài
  external_id  TEXT UNIQUE,    -- ← chỗ móc vào tài khoản ATS/AD sau này
  disabled_at  TEXT
);
CREATE TABLE user_roles (user_id INTEGER, role TEXT);   -- một người NHIỀU vai
```

`external_id` là bản lề: khi ATS có hệ thống tài khoản, mỗi dòng ở đây **móc**
vào danh tính bên đó thay vì phải xoá đi làm lại. Không có trường này thì việc
liên thông về sau là di trú dữ liệu, có nó thì chỉ là điền thêm một cột.

**Mật khẩu phải băm bằng thuật toán chuyên dụng** (argon2 hoặc bcrypt), không bao
giờ lưu thô, không tự chế. Đây là hệ quả trực tiếp của việc truy cập từ xa.

### 8. Cửa vào **theo vai**, và cửa vào **không phải SLD**

Đây là chỗ ADR này chạm vào sản phẩm chứ không chỉ bảo mật.

Với trạm không người trực, giả định *"mở app ra là thấy sơ đồ"* sai. Đăng nhập
xong, mỗi vai vào thẳng thứ họ cần:

| Vai | Màn hình đầu tiên |
|---|---|
| `operator` `supervisor` | **Tình hình trạm** — AI tóm tắt + cảnh báo. SLD là tab cạnh bên |
| `maintenance` | Sức khoẻ thiết bị: truyền thông, nguồn AC/DC, điểm mất chất lượng |
| `protection` | Sự kiện bảo vệ: trip, reclose, khởi động, interlock |
| `engineer` | Màn hình kỹ thuật (`#/eng`) |
| `admin` | Tài khoản, nhật ký, knowledge base |

SLD **không biến mất** — nó là nơi xác minh khi bản tóm tắt nói có chuyện. Nhưng
nó không còn là cửa vào mặc định cho ai cả.

---

## Phương án đã bác bỏ

### A. Chỉ hai vai: engineer và operator
Đơn giản nhất, và là hình dạng `screens.md` đang giả định. **Bác bỏ** — ma trận
của ATS có 5 actor với 5 nhu cầu khác nhau; `protection` và `maintenance` là vai
thật, có việc thật. Và gộp `operator` với `supervisor` là xoá mất ranh giới
soạn/ký, thứ đắt nhất để dựng lại sau.

### B. Vai là hằng số cứng trong code, mỗi người đúng một vai
Dễ hiểu, dễ kiểm. **Bác bỏ** — trạm ít người thì một người phải kiêm nhiều việc.
Vai loại trừ nhau buộc họ đăng xuất/đăng nhập liên tục hoặc dùng chung tài khoản.
Cả hai đều làm nhật ký nói dối.

### C. Kiểm quyền ở giao diện, backend tin frontend
Nhanh nhất. **Bác bỏ** — agent gọi thẳng facet, không đi qua giao diện. Và với
truy cập từ xa thì đây không phải phân quyền, chỉ là ẩn nút.

### D. Không lưu tài khoản, dùng danh tính Windows của máy trạm
Không phải quản mật khẩu. **Bác bỏ** — phụ thuộc cách từng trạm dựng máy, và
không diễn đạt được vai riêng của phần mềm này (`control.sign` không phải khái
niệm của Windows). Vẫn để ngỏ qua `external_id` nếu sau này muốn.

### E. Chờ tới Module C (GĐ 5) mới làm phân quyền
Đúng lúc cần nhất. **Bác bỏ** — bốn chỗ ăn vào kiến trúc ở §Bối cảnh: mọi route,
agent, evidence, giao diện. Đợi tới GĐ 5 thì đó là viết lại, không phải bổ sung.

### F. Ràng buộc quyền theo scope ngay từ đầu (*"chỉ thao tác trên 110kV"*)
Mạnh và đúng hướng. **Bác bỏ ở giai đoạn này** — chưa có nhu cầu đã đo được, và
nó nhân đôi số trường hợp phải kiểm. Chỗ cắm đã sẵn ở §6; mở khi có yêu cầu thật.

---

## Hệ quả

### Tích cực

- Thêm vai = thêm một gói quyền. Không sửa facet, không sửa component.
- Agent không thể thấy nhiều hơn người hỏi — thành **tính chất kiến trúc**, không
  phải điều phải nhớ.
- Trạm ít người và trạm lớn dùng **cùng một bản dựng**, khác nhau ở cấu hình gán vai.
- Bằng chứng ghi được ai hỏi → nhật ký kiểm toán (yêu cầu của vai Admin theo ATS)
  gần như miễn phí.
- Ranh giới soạn/ký có sẵn khi Module C tới, không phải đập lại.

### Phải chấp nhận

- **Bảng người dùng cục bộ là nguồn danh tính thứ hai** nếu ATS đã có sẵn một
  nguồn. Người nghỉ việc phải xoá ở hai chỗ cho tới khi liên thông xong.
  `external_id` giảm nhẹ chứ không xoá được rủi ro này. **Vẫn phải hỏi ATS** —
  câu hỏi mở Q8.
- Có mật khẩu là có nghĩa vụ: băm đúng cách, đổi mật khẩu, khoá tài khoản. Không
  làm được nửa vời.
- Mỗi facet phải khai `requires=`. Quên khai là hở — nên mặc định phải là **từ
  chối**, và `check.py` phải bắt facet nào chưa khai.
- `screens.md` viết trước ADR này lấy SLD làm cửa vào mặc định. **Phải sửa** theo
  §8; đây là việc thật, nằm trong GĐ 1.5.

### Việc phải làm để ADR này không mục

- [ ] Mặc định là **từ chối**: facet không khai `requires=` thì không chạy được,
      không phải chạy tự do.
- [ ] `check.py` gác: mọi facet đều khai `requires=`; không component nào ngoài
      `features/engineer/` đọc `binding.read`.
- [ ] Test khoá: **agent không bao giờ đọc được nhiều hơn người gọi nó.**
- [ ] Test khoá: `engineer` không bao giờ có `control.sign`, kể cả khi giữ nhiều vai.
- [ ] `EvidenceRecord` mang `actor` — không có thì không có nhật ký kiểm toán.
- [ ] **Hỏi ATS (Q8)**: đã có hệ thống tài khoản nào để liên thông chưa? Trả lời
      sớm thì `external_id` trỏ đúng chỗ ngay lần đầu.
