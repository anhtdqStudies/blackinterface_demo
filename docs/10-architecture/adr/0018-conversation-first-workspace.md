# ADR-0018 — Hội thoại là bố cục, không phải một chế độ

- **Status**: Accepted
- **Date**: 2026-08-07
- **Supersedes**: [ADR-0014](0014-frontend-workspace.md) **§3 phần preset**
  (ba bố cục `monitor` / `chat` / `incident`). Mọi phần khác của ADR-0014 —
  hai bảng màu, pane là dữ liệu, i18n, nhiều hội thoại — **giữ nguyên**.

## Bối cảnh

Ba preset đã thi công xong ở GĐ 1.5 lô 0 và chạy được. Nhìn chúng chạy thì thấy
điều mà lúc thiết kế không thấy: **chúng không phải ba chế độ, chúng là một nút
bật/tắt chat được đóng gói thành ba.**

Đọc thẳng `app/layout/presets.ts`:

| Preset | Có chat? | Có sơ đồ? | Khác biệt thật sự |
|---|---|---|---|
| `monitor` | không | có | — |
| `incident` | có (38%) | có (62%) | **chỉ là `monitor` + chat** |
| `chat` | có (100%) | không | **chỉ là `incident` kéo sơ đồ về 0** |

Một boolean bị nâng lên thành ba trạng thái, và người dùng phải học thuộc cái nào
chứa cái gì. Người dùng nêu (2026-08-07): *"chuyển các mode như này tôi thấy về
mặt UI/UX không hay"*.

Lý do thứ hai nặng hơn, và nó nằm trong chính `document/@Station_UseCases 1.xlsx`:
**30 use case, không use case nào là "vẽ SLD"** — cả bảng là *hỏi → trả lời có
bằng chứng*. Nếu hội thoại là sản phẩm thì nó không được là một chế độ phải chuyển
vào. Thứ người ta thu gọn phải là **sơ đồ**, không phải ngược lại.

ADR-0014 §3 chốt ba preset vào 2026-08-05, **trước khi** có một dòng workspace nào
chạy. Đây là quyết định sửa lại sau khi đã nhìn thấy thứ mình dựng — đúng nghĩa
của việc dựng mỏng trước.

## Quyết định

### 1. Một bố cục, không có preset

`presets.ts` còn **một** `Layout`. Không còn `PRESET_NAMES`, không còn ba nút trên
header, không còn `?l=`.

```
┌──────────────┬──────────────────────────────┐
│              │  ┌────────────────────────┐  │
│   HỘI THOẠI  │  │     SƠ ĐỒ MỘT SỢI      │  │
│              │  └────────────────────────┘  │
│  ‹thu gọn›   │  ┌─────┬─────┬──────┬──────┐ │
│              │  │Trạng│ Số  │ Bất  │ Bằng │ │
│              │  │thái │ đo  │thg ❷ │chứng │ │
│  ___________ │  └─────┴─────┴──────┴──────┘ │
│  [ hỏi... ]  │   XSWI22 · MỞ · GOOD         │
└──────────────┴──────────────────────────────┘
```

Yêu cầu cũ của ADR-0014 *"phải ẩn được sơ đồ để chỉ còn chat"* vẫn được đáp ứng —
bằng **kéo splitter**, một hành động, không phải một preset. Yêu cầu ngược lại
(chỉ còn sơ đồ, không chat) cũng thế.

### 2. Bên phải là tab, không phải accordion

Người dùng chốt 2026-08-07. Sơ đồ nằm trên, cố định. Dưới là một thanh tab:
Trạng thái · Số đo · Mang điện · Bất thường · Bằng chứng, và về sau Alarm · SOE ·
Trend · Báo cáo.

Tab thắng accordion ở một điểm cụ thể: danh mục pane sẽ còn dài ra (module B, D,
E, F đều thêm pane). Accordion năm mục thì đọc được; accordion mười mục là một
cột toàn thanh tiêu đề.

### 3. Ràng buộc khoá — cái phải đến với người trực không được nằm sau tab không active

Đây là **cái giá của tab**, và là điều kiện để chọn tab:

- Tab `anomalies` và `alarms` mang **badge số luôn hiện**, kể cả khi không active.
- Nhóm C mức ERROR (`earthed_while_live`) xuất hiện thì **tự chuyển tab** hoặc
  nổi lên ngoài thanh tab. Không được im lặng.

Lý do không phải thẩm mỹ. Nhóm C được chuyển từ bề mặt engineer sang bề mặt vận
hành ở GĐ 1.5 lô 3 **chính vì** chôn nó trong tab engineer là để người trực không
bao giờ nhìn thấy ([screens.md §2](../../20-ui/screens.md)). Chôn nó sau một tab
không active là lặp lại đúng lỗi đó, chỉ tinh vi hơn.

### 4. Địa chỉ hoá: `?tab=` thay `?l=`

`#/ops/<scope>?tab=<kind>`. Giữ nguyên luật của ADR-0014 §3: **scope sai thì
redirect, tab sai thì im lặng về mặc định.** Lý do không đổi — tab sai chỉ bày sai
cách; scope sai làm thanh địa chỉ và màn hình nói khác nhau về trạm.

### 5. Hợp đồng pane không đổi

`Pane` / `PaneKind` / `PANE_COMPONENTS` / `PaneProps` / quy tắc ghim: **giữ
nguyên**. Một nhóm tab là một cách xếp pane khác, không phải một thứ khác. Cụ
thể `Layout` mọc thêm một dạng ô:

```ts
type Slot = { pane: Pane } | { tabs: Pane[]; active: PaneKind }
```

`PaneHost` vẫn không được rẽ nhánh theo `kind` — `check.py` mục 5 giữ nguyên.

## Phương án đã bác bỏ

**A. Giữ accordion, chỉ thêm cột chat.** Thay đổi ít nhất, và giữ được khả năng
liếc nhiều mục cùng lúc — thứ mà người trực ca cần còn lập trình viên thì không.
Bác vì danh mục pane sẽ dài ra đáng kể (B/D/E/F), và vì §3 đã mua lại phần lớn
cái mất bằng badge + tự chuyển tab. **Ghi lại để phiên sau không đề xuất lại**:
nếu chạy tay thấy người trực bỏ sót thứ nằm trong tab không active dù đã có badge,
thì phương án này là đường lui, và §3 là chỗ đo xem có cần lui không.

**B. Bố cục lai: một ô Bất thường luôn hiện + tab cho phần còn lại.** An toàn nhất
về mặt hiển thị, nhưng nó là **một preset cứng thứ hai** đội lốt bố cục — vẫn phải
quyết trước cái gì đáng được ô cố định. Nếu §3 chứng minh badge là không đủ thì
đây, chứ không phải A, là hình dạng nên lấy.

**C. Trình soạn bố cục tự do (dock editor).** Đã bác ở ADR-0014 phương án B, lý do
còn nguyên và **mạnh hơn** sau ADR này: giờ chỉ còn một bố cục để nuôi.

**D. Giữ ba preset, chỉ đổi nhãn.** Không giải quyết gì — vấn đề là *phải chuyển
chế độ*, không phải chế độ tên gì.

## Hệ quả

- `presets.ts` co lại còn một bố cục; `PRESET_LABEL_KEY`, `isPresetName`,
  `layoutFor` và ba nút trên `Header.vue` biến mất. `workspace.preset` →
  `workspace.tab`.
- `InspectorPane.vue` tan ra: chuỗi `v-if` theo `SectionId` (dòng 175–187) được
  thay bằng `PANE_COMPONENTS`. Đó là một `PaneHost` thu nhỏ **đang rẽ nhánh theo
  kind** — `check.py` mục 5 không bắt vì luật chỉ soi `PaneHost.vue`. Sau ADR này
  luật nên soi cả nó.
- Kích thước kéo giãn nhớ theo preset (`bi.inspector.sections.${preset}`) → nhớ
  một bộ duy nhất. Khoá localStorage cũ thành rác, xoá được.
- **Làm ở đầu GĐ 2, sau khi `ChatPane` chạy thật** (người dùng chốt cùng ngày).
  Đóng bề ngang cột chat khi trong đó còn là `PaneLater.vue` là đoán — và ba
  preset bị bỏ ở đây chính là kết quả của một lần đoán như thế.

## Nguồn

- Người dùng, 2026-08-07 (kèm ảnh màn hình đang chạy + ảnh tham chiếu Cursor)
- `document/@Station_UseCases 1.xlsx` — 30 use case, 0 use case "vẽ SLD"
- `frontend/src/app/layout/presets.ts` — ba bố cục, đo trực tiếp
