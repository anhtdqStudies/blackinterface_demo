# ADR-0017 — Tài khoản cục bộ, phiên đăng nhập bằng cookie phía máy chủ

- **Status**: Accepted
- **Date**: 2026-08-06
- **Liên quan**: ADR-0016 (vai và quyền — chốt lược đồ bảng) · ADR-0006 (triển
  khai local tại trạm) · ADR-0011 (một đường ghi)

---

## Bối cảnh

[ADR-0016 §7](0016-roles-and-capabilities.md) đã chốt **lưu tài khoản ở SQLite
cục bộ**, kèm `external_id` để sau này liên thông. Nó cố ý **chưa** nói cách
xác thực. ADR này trả lời phần đó, và người dùng yêu cầu làm ngay
(2026-08-06): *"ghi vào trong database, làm trang đăng nhập cơ bản luôn được
không, có các tài khoản với các role liên quan luôn"*.

Điều làm bài toán này khác một màn hình đăng nhập thông thường: **trạm không
người trực nghĩa là truy cập từ xa**. Đây là bảo mật thật.

---

## Quyết định

### 1. Mật khẩu băm bằng **Argon2id**, qua `argon2-cffi`, theo tham số mặc định

Không tự chế. Không SHA-256 kèm mẹo. Không tự chọn số vòng lặp.

Một module duy nhất — `blackinterface/passwords.py` — nên chỗ cần soi lại chỉ có
một. Đặt cùng tầng với `errors.py`, `logs.py` chứ không thuộc tầng nào:
`store/` ghi chuỗi băm, `api/` kiểm nó, và **không bên nào sở hữu thuật toán**.

### 2. Phiên **lưu ở máy chủ**, không phải token tự chứa

```
đăng nhập → token ngẫu nhiên 256 bit → cookie
                                    → SHA-256 của nó vào bảng `sessions`
```

Bác bỏ token tự chứa (JWT) vì một lý do vận hành: **không rút lại được trước khi
hết hạn**. Mà "khoá tài khoản người này ngay bây giờ" mới là yêu cầu thực sự
xuất hiện. Với phiên phía máy chủ, `set_disabled()` xoá luôn phiên đang mở, và
lần gọi tiếp theo là 401.

**Chỉ lưu SHA-256 của token, không lưu token.** Ai đọc được bảng đó vẫn không
đăng nhập được thành ai cả. Dùng digest nhanh chứ không phải Argon2 là có lý do:
token là 256 bit ngẫu nhiên, không phải mật khẩu do người nghĩ ra — băm chậm ở
đây chỉ tốn thời gian mỗi request mà không thêm chút an toàn nào.

Cookie: `HttpOnly` (JS không đọc được, nên XSS không lấy được), `SameSite=Lax`,
`Secure` bật bằng `BI_COOKIE_SECURE` khi có HTTPS.

### 3. **401 và 403 là hai câu trả lời khác nhau**

| | Nghĩa | Người dùng làm gì |
|---|---|---|
| `401 unauthenticated` | chưa đăng nhập | đăng nhập |
| `403 forbidden` | đã đăng nhập, không đủ quyền | gọi người cấp quyền |

Gộp hai cái là bắt giao diện đoán, và nó sẽ đoán sai theo cả hai chiều: hiện
màn hình đăng nhập cho người đã đăng nhập, hoặc báo "không có quyền" cho người
chỉ cần đăng nhập.

### 4. Bề mặt công khai đúng **ba** đường, và được test khẳng định **bằng dấu bằng**

```python
PUBLIC_PATHS = {"/api/login", "/api/health", "/api/me"}
```

`public()` là một hàm riêng, không phải cờ của `requires()` — để *"ai mở được
cổng mạng đều gọi được"* là một chữ phải gõ ra, và grep thấy được.

`/api/me` công khai vì giao diện phải hỏi được *"có ai đăng nhập không"* **trước
khi** biết có nên hiện màn hình đăng nhập hay không. Với người lạ nó trả về danh
tính rỗng, không lộ gì.

### 5. Cài mới được **gieo sẵn một tài khoản cho mỗi vai**

| Tài khoản | Vai |
|---|---|
| `operator` `supervisor` `maintenance` `protection` `admin` `engineer` | đúng vai cùng tên |
| **`truc`** | `operator + supervisor + maintenance` |

`truc` là trạm ít người của [ADR-0016 §1](0016-roles-and-capabilities.md): một
người kiêm nhiều việc. Có nó thì cách gán đó **được chạy thật**, thay vì được
giả định là chạy.

Không tài khoản gieo sẵn nào vừa `model.edit` vừa `control.sign` —
`check_role_set()` sẽ từ chối dựng, và có một test đối chiếu trên đúng dữ liệu
được ship.

Gieo **chỉ khi bảng chưa có ai**, không phải kiểm từng tên. Nếu kiểm từng tên
thì tài khoản quản trị viên đã xoá sẽ lặng lẽ mọc lại.

### 6. Mật khẩu mặc định được **nói to ở mỗi lần khởi động**

Cột `password_changed_at`; `NULL` nghĩa là chưa từng đổi. Mỗi lần khởi động log
cảnh báo liệt kê những tài khoản còn dùng mật khẩu cài đặt.

Ở mỗi lần khởi động chứ không phải một lần lúc gieo: cảnh báo chỉ hiện lần đầu
là cảnh báo tắt đúng lúc nó bắt đầu có ý nghĩa.

Có `POST /api/password` để tự đổi mật khẩu. Gieo mật khẩu mặc định mà không cho
đường đổi thì là làm nửa vời.

### 7. Giữ `BI_AUTH=env` cho phát triển

`BI_AUTH=env` → không có đăng nhập, cả tiến trình chạy dưới `BI_ROLE`. Đây là
cách thử sáu bề mặt nhanh mà không phải đăng nhập lại sáu lần.

**Không bao giờ dùng ở trạm** — nó cấp cùng một bộ quyền cho bất kỳ ai chạm tới
cổng mạng. Mặc định là `session`.

---

## Phương án đã bác bỏ

### A. JWT / token tự chứa
Không cần bảng phiên, mở rộng dễ. **Bác bỏ** — không rút lại được trước khi hết
hạn, mà đó chính là thao tác cần nhất. Và "mở rộng" không phải bài toán của một
tiến trình trên một máy tại một trạm (ADR-0006).

### B. Token trong `localStorage` + header `Authorization`
Quen tay với SPA. **Bác bỏ** — JS đọc được nghĩa là XSS lấy được. Cookie
`HttpOnly` thì không. Đổi lại phải nghĩ tới CSRF, và `SameSite=Lax` cộng với
việc mọi thao tác đổi trạng thái đều là POST đã xử lý phần đó.

### C. HTTP Basic
Ít mã nhất. **Bác bỏ** — không đăng xuất được, trình duyệt tự gửi lại, không
diễn đạt được vai, và mật khẩu đi kèm **mọi** request.

### D. Không gieo tài khoản, bắt tạo bằng CLI lúc cài
Sạch hơn về bảo mật. **Bác bỏ ở giai đoạn này** — không đăng nhập được thì không
thử được gì, và mục đích trước mắt là chạy tay trên trình duyệt. Giảm nhẹ bằng
§6: mật khẩu mặc định bị nêu tên mỗi lần khởi động.

### E. Đợi ATS trả lời Q8 rồi mới làm
Tránh được nguồn danh tính thứ hai. **Bác bỏ** — Q8 treo đã lâu và không thể
chặn việc thử giao diện. `external_id` giữ cửa mở: liên thông sau là điền một
cột, không phải di trú dữ liệu.

---

## Hệ quả

### Tích cực

- Đăng nhập, đăng xuất, khoá tài khoản đều **có hiệu lực ngay**.
- `EvidenceRecord.actor` giờ mang **tên người thật**, không phải `"local"`.
- Giao diện phân biệt được "hãy đăng nhập" với "bạn không có quyền".
- Thử một vai là đăng nhập bằng tài khoản đó — không cần khởi động lại backend.

### Phải chấp nhận

- **Có mật khẩu là có nghĩa vụ**: đổi mật khẩu, khoá tài khoản, và đến lúc nào
  đó là chính sách mật khẩu. Hiện chỉ chặn dưới 8 ký tự.
- **Chưa có chống dò mật khẩu.** Không giới hạn số lần thử, không khoá tạm. Chấp
  nhận được khi còn ở mạng nội bộ; **không chấp nhận được khi mở ra ngoài** —
  ghi lại là nợ.
- **Chưa có nhật ký kiểm toán**, mới có log. `audit.read` đã có tên nhưng chưa
  có bảng đứng sau.
- **Chưa có màn hình quản lý tài khoản.** `account.manage` tồn tại, chỗ dùng nó
  thì chưa. Sửa vai vẫn phải bằng SQL.
- Đổi mật khẩu **không** kết thúc các phiên khác của chính người đó. Nên có, chưa làm.
- Vẫn còn **hai nguồn danh tính** nếu ATS đã có sẵn một (Q8 của ADR-0016).

### Việc phải làm để ADR này không mục

- [ ] Giới hạn số lần đăng nhập sai **trước khi** mở ra ngoài mạng trạm
- [ ] Bảng nhật ký kiểm toán để `audit.read` có nghĩa
- [ ] Màn hình quản lý tài khoản cho `account.manage`
- [ ] Đổi mật khẩu thì huỷ mọi phiên khác của người đó
- [ ] Bật `BI_COOKIE_SECURE` khi triển khai có HTTPS
