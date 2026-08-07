# Kiến trúc frontend — hợp đồng GĐ 1.5

> **Chốt trước khi thi công.** Đây là hợp đồng: mọi thứ trong tài liệu này phải
> khoá xong **trước** khi chia việc cho người/agent khác, vì đó là những chỗ hai
> người cùng sửa sẽ đẻ ra hai hệ thống.
>
> Viết 2026-08-06. Hiện thực phần workspace của
> [ADR-0014](../10-architecture/adr/0014-frontend-workspace.md) còn nợ từ GĐ 0.
> Màn hình và luồng: [`screens.md`](screens.md).

---

## 1. Phạm vi

**Trong GĐ 1.5**

- `app/layout/` — `Shell` `Header` `PaneHost` `presets.ts`
- `Pane` / `Layout` là dữ liệu; bố cục vào URL
- `features/` — chuyển các view/panel hiện có vào đúng chỗ
- `ui/` đủ 10 component, **bốn trạng thái** cho mọi pane
- Tách bề mặt engineer (`#/eng`) khỏi vận hành (`#/ops`)
- Chuyển nhóm C (`earthed_while_live`…) sang pane `anomalies` của bề mặt vận hành
- Thang design token tối thiểu trong `styles.css`

**Ngoài GĐ 1.5 — đừng làm lẫn vào**

| Việc | Ở đâu |
|---|---|
| Pane `chat`, danh sách hội thoại | GĐ 2 |
| Trình soạn template, cổng chứng minh, `releases` | GĐ 2.5 ([ADR-0015](../10-architecture/adr/0015-engineer-authored-templates.md)) |
| Pane `alarms`, `soe` | GĐ 3 |
| Vẽ số đo lên SLD | diagram engine, chưa xếp lịch |
| Kéo-thả dock tự do | **không bao giờ** (ADR-0014 phương án bác bỏ B) |

**Backend đổi hai chỗ trong GĐ 1.5**, không hơn:

1. `/api/issues` trả kèm **nhóm** A/B/C — frontend không tự phân loại bằng cách
   đối chiếu 12 mã. Phân loại ở một chỗ, và chỗ đó là backend.
2. **Nền phân quyền** ([ADR-0016](../10-architecture/adr/0016-roles-and-capabilities.md)) — xem §12.

---

## 2. Cây thư mục đích

```
frontend/src/
  app/
    App.vue           chỉ còn <Shell>
    router.ts
    layout/
      Shell.vue       khung: Header + PaneHost
      Header.vue      tên trạm · trạng thái kết nối · chọn bố cục · VI/EN
      PaneHost.vue    đọc Layout → render lưới pane. KHÔNG biết pane nào làm gì
      panes.ts        đăng ký: PaneKind → component (một dòng một loại)
      presets.ts      ba bố cục dựng sẵn. MỘT CHỖ DUY NHẤT
  ui/                 design system — không component nào biết về trạm
  api/                client.ts  schema.d.ts  streams.ts
  scope.ts            parse/format ScopeRef (ADR-0010, I8)
  i18n/
  stores/             tách theo VÒNG ĐỜI
  features/
    station/          SldCanvas  DeviceSymbol
    monitoring/       StatePane  MeasurementPane  EnergizationPane  AnomaliesPane
    engineer/         ConnectionsPane  CoveragePane  ModelIssuesPane  BindingPane
```

### Bảng chuyển chỗ

| Hiện tại | Đích |
|---|---|
| `App.vue` (148 dòng, kiêm header) | `app/App.vue` + `app/layout/Shell.vue` + `Header.vue` |
| `router.ts` | `app/router.ts` |
| `views/StationView.vue` | tan ra → `presets.ts` + các pane |
| `views/BayView.vue` | tan ra → `StatePane` |
| `views/IssuesView.vue` | **tách đôi** → `AnomaliesPane` (vận hành) + `ModelIssuesPane` (kỹ thuật) |
| `views/ProjectsView.vue` | `features/engineer/ConnectionsPane.vue` |
| `components/diagram/*` | `features/station/` |
| `components/panels/MeasurementPanel.vue` | `features/monitoring/MeasurementPane.vue` |
| `components/panels/EnergizationPanel.vue` | `features/monitoring/EnergizationPane.vue` |
| `components/panels/DevicePanel.vue` | `features/monitoring/StatePane.vue` |
| `components/panels/CoveragePanel.vue` | `features/engineer/CoveragePane.vue` |
| `components/panels/IssueList.vue` | dùng lại trong cả hai pane issue |
| `ui/*` | giữ nguyên chỗ |

---

## 3. Hợp đồng Pane / Layout

```ts
// app/layout/panes.ts
export const PANE_KINDS = [
  'sld', 'state', 'measurements', 'energization', 'anomalies', 'evidence',
  'connections', 'coverage', 'model-issues', 'binding',
] as const
export type PaneKind = (typeof PANE_KINDS)[number]

export type Pane = {
  id: string                  // ổn định qua các lần render, để Vue giữ đúng DOM
  kind: PaneKind
  scope?: ScopeRef            // VẮNG = theo scope của workspace  ← mặc định
  params?: Record<string, unknown>
}

export type Layout = {
  cols: Array<{ size: number; rows: Array<{ size: number; pane: Pane }> }>
}
```

### `pane.scope` là **override tuỳ chọn**, không phải trường bắt buộc

Đây là chỗ tôi làm khác ADR-0014 một chút, và có lý do.

Nguyên tắc của [`screens.md` §1](screens.md) là *"đổi scope không đổi bố cục"* —
bấm vào một ngăn thì **cả màn hình** nói về ngăn đó. Nếu mỗi pane bắt buộc mang
scope riêng thì mỗi lần bấm phải cập nhật N pane, và chỉ cần quên một cái là màn
hình hiện **hai ngăn khác nhau mà không nói ra** — đúng loại lỗi ADR-0010 sinh ra
để chặn.

Nên: **vắng `scope` = theo URL.** Đặt `scope` là hành động có chủ ý — *"ghim ngăn
D03 ở ô này trong lúc tôi đi xem chỗ khác"*, thứ người ta thật sự cần khi phân
tích sự cố. Pane bị ghim **phải hiện nhãn ghim**, nếu không nó thành cái bẫy.

### Đăng ký pane — thêm loại pane là **một dòng**

```ts
export const PANE_COMPONENTS: Record<PaneKind, Component> = {
  sld:          defineAsyncComponent(() => import('@/features/station/SldPane.vue')),
  measurements: defineAsyncComponent(() => import('@/features/monitoring/MeasurementPane.vue')),
  // …
}
```

`PaneHost` tra bảng này. **`PaneHost` không được có `v-if` theo `kind`.** Đó là
thước đo: nếu phải sửa `PaneHost` để thêm pane thì hợp đồng đã hỏng.

### Preset

```ts
// app/layout/presets.ts — MỘT CHỖ DUY NHẤT. Không rải định nghĩa bố cục ra view.
export const PRESETS = { monitor, chat, incident } as const
export type PresetName = keyof typeof PRESETS
export const DEFAULT_PRESET: PresetName = 'monitor'
```

`chat` khai sẵn ở GĐ 1.5 nhưng ô chat hiện `Empty` với dòng *"Có ở giai đoạn
sau"* — để GĐ 2 chỉ việc cắm component vào, không phải sửa hợp đồng.

---

## 4. Hợp đồng URL

```
#/ops/<scope>?l=<preset>          vận hành
#/eng                             kỹ thuật
```

| Luật | Vì sao |
|---|---|
| Scope không parse được → **redirect** về station | Thanh địa chỉ và màn hình không bao giờ được nói khác nhau. Đã có ở `router.beforeEach`, giữ nguyên |
| `?l=` sai tên → dùng `DEFAULT_PRESET`, **không** redirect | Bố cục sai chỉ là hiển thị, không phải câu trả lời sai về trạm. Xử lý nhẹ hơn scope sai — đây là khác biệt có chủ ý |
| Bố cục tuỳ biến (kéo giãn) → `localStorage`, khoá theo preset | Không nhét cả `Layout` vào URL ở GĐ 1.5. Chia sẻ link mang **preset**, không mang từng pixel |
| Chỉ `@/scope` sinh chuỗi scope | AGENTS.md I8 |

---

## 5. Store — chia theo vòng đời, mỗi thứ một chủ

| Store | Sở hữu | Vòng đời |
|---|---|---|
| `structure` | đồ thị, ngăn, thiết bị | đổi khi `structure_revision` đổi |
| `live` | vị trí đóng/mở, mang điện, trạng thái link | thay mỗi lần đẩy `state` |
| `measurements` | số đo | thay mỗi lần đẩy `measurement` |
| `stream` | **một** EventSource, chính sách nối lại | suốt phiên |
| `summary` | câu trả lời + evidence theo scope | theo scope đang xem |
| `workspace` | **scope + preset + bố cục tuỳ biến** | theo người dùng; sống qua F5 |
| `connections` | danh sách trạm đã nối *(đổi tên từ `projects`)* | ít khi đổi |

**`workspace` mọc thêm phần bố cục, giữ nguyên phần scope.** Scope vẫn suy từ URL
chứ **không** được sao thành `ref` thứ hai — đó là lý do bản trước phải xoá lựa
chọn bằng tay ở ba chỗ.

Không store nào được giữ **bản sao** dữ liệu của store khác. Cần ghép thì
`computed`.

---

## 6. `ui/` — 10 component, không cái nào biết về trạm điện

| Component | Có | Nhiệm vụ |
|---|---|---|
| `Panel` | ✅ | khung có tiêu đề |
| `Badge` | ✅ | nhãn nhỏ |
| `StatusDot` | ✅ | trạng thái **hệ thống** (kết nối). ADR-0014 gọi là `StateDot` — **thống nhất lấy tên `StatusDot`**, và nó **không** dùng cho trạng thái thiết bị; cái đó là `DeviceSymbol` |
| `EvidenceBlock` | ✅ | khối bằng chứng |
| `Field` | ✅ | cặp nhãn–giá trị |
| `ValueCell` | ✅ | **một con số + đơn vị + chất lượng**. Chỗ duy nhất được quyết định in hay không in đơn vị (Q7) và hiện gạch ngang khi không đọc được (I2) |
| `DataTable` | ✅ | bảng có sắp xếp, cuộn ngang trong khung của nó |
| `Empty` | ✅ | rỗng **có lý do** + việc làm tiếp |
| `Skeleton` | ✅ | đang tải, **giữ đúng chỗ** |
| `ErrorBox` | ✅ | lỗi + mã + nút thử lại |

Luật khoá: **không component nào trong `ui/` được import từ `stores/` hay
`api/`.** Nhận props, phát event. Đó là điều kiện để chia việc song song mà không
giẫm chân nhau.

`ValueCell` là chỗ tập trung một quyết định an toàn: hiện chỉ `Hz`, nấc MBA và hệ
số công suất có đơn vị; còn lại in số trần. Để rải quyết định đó ra từng pane thì
sớm muộn có pane in `kV` (xem Q7).

---

## 7. Bốn trạng thái — hợp đồng chung cho mọi pane

Mỗi pane phải xử lý đủ bốn. Không pane nào được tự chế cách hiện riêng.

```ts
type PaneState<T> =
  | { status: 'loading' }
  | { status: 'empty';  reason: string; action?: { label: string; to: string } }
  | { status: 'error';  code: string; retry: () => void }
  | { status: 'ready';  data: T; limits?: Limit[] }   // limits ≠ rỗng = SUY GIẢM
```

**Suy giảm không phải trạng thái thứ năm** — nó là `ready` có `limits`. Có dữ
liệu dùng được, chỉ kém tin hơn. Đây là trạng thái **thường gặp nhất** trên trạm
thật, và là lý do `EvidenceBlock` tồn tại.

`empty.reason` là **khoá i18n**, không phải câu văn — *"Không có số đo"* vô dụng;
*"Cấp điện áp không mang số đo — chọn một ngăn"* mới dùng được.

---

## 8. Token tối thiểu

Chưa làm `tokens.md` đầy đủ, nhưng **phải** có đủ ba thứ này trước khi ai viết
component, nếu không mỗi người tự chế khoảng cách:

- **Thang khoảng cách**: 4 8 12 16 24 32 (px, qua Tailwind)
- **Thang cỡ chữ**: `xs sm base lg xl` — số đo dùng `tabular-nums`
- **Hai bảng màu tách bạch** (ADR-0014 §2), nâng thành theme token:
  - `st-*` — trạng thái **trạm**: đỏ/xanh lá/xanh dương/tím/xám của OneATS, **không đụng vào**
  - `sys-*` — trạng thái **hệ thống**: amber/xám/accent, **cấm đỏ và xanh lá**

**Không trạng thái nào chỉ dựa vào màu.** Luôn kèm chữ hoặc hình dạng.

---

## 9. Luật `check.py` phải gác

Không có mấy dòng này thì hợp đồng trên mục trong hai tuần:

- [x] Không component nào ngoài `features/engineer/` hiện NodeId / Dbpos thô / tên LN
      — `check.py` mục 5, **gác từ 2026-08-07**. Quét `.vue` ngoài
      `features/engineer/` tìm `source_ref` · `sourceRef` · `rawDbpos` ·
      `logicalNode` · `.ln`. Ba trường đó đã bị **bỏ khỏi** `DeviceStateContent`
      (bề mặt operator); chỗ của chúng là pane `binding`, chưa làm.
      **Bài học**: suốt lô 1–2 ô này để trống với lý do "chờ lô 2", và điều thực
      sự xảy ra là lô 2 chép nguyên ba trường từ `DevicePanel` sang pane operator
      mới. Một luật chưa có máy dò không đứng yên chờ, nó bị vi phạm bởi một lần
      *dời chỗ* mà không ai coi là quyết định
- [x] `ui/**` không import `stores/**` hay `api/**` — `check.py` mục 5. Cho phép
      `import type` từ `api/` (biến mất lúc build, không mang ràng buộc); import
      giá trị thì không
- [x] `PaneHost.vue` không chứa `v-if` theo `kind` — `check.py` mục 5
- [x] Định nghĩa bố cục chỉ xuất hiện trong `app/layout/presets.ts` — `check.py` mục 5
- [x] Mọi khoá i18n dùng trong code đều tồn tại ở **cả** `vi` lẫn `en` — `check.py`
      mục 5, hai vế: `vi` và `en` phải **bằng nhau**, và mọi `t('a.b')` phải có
      thật. Khoá dựng từ mã backend (`state.${…}`, `limit.${…}`) là template
      literal nên không quét được — vế "hai ngôn ngữ bằng nhau" phủ chỗ đó
- [x] Ngữ pháp scope ở `frontend/src/scope.ts` khớp `domain/scope.py` *(đã có)*

**Cả năm máy dò đều đã được chứng minh là có dò**: sửa hỏng từng luật một, chạy
riêng mục 5, xác nhận đỏ, rồi hoàn nguyên. Đây là bài học từ lô 0 phần một
(§11) — một test "cổng có chặn" mà không kèm "máy dò có dò" thì có thể xanh rỗng.

---

## 10. Thứ tự thi công — cái gì song song được

**Lô 0 — tuần tự, một người, không chia được. ✅ XONG 2026-08-06.** Đây là hợp đồng:
`scope.ts` (giữ) → `panes.ts` → `presets.ts` → `workspace` store → `PaneHost` →
`Shell` + `Header` → token trong `styles.css`.

Ba chỗ lô 0 làm khác bản chốt ban đầu, đều có lý do ghi tại chỗ:

1. **`PANE_KINDS` có 11 loại, không phải 10** — thêm `chat`. Preset *Hội thoại*
   phải diễn đạt được bằng **dữ liệu** ngay từ GĐ 1.5; nếu `chat` chưa phải một
   `kind` thì preset đó không tồn tại được, và GĐ 2 sẽ phải sửa chính cái hợp
   đồng vừa đóng băng. Loại chưa có component trỏ vào `PaneLater.vue`.
2. **Kích thước kéo giãn do `reka-ui` giữ (`autoSaveId`), không đưa vào store.**
   Store giữ *chọn preset nào*; pixel thì để một chủ duy nhất. Hai chủ sẽ lệch
   ngay lần đầu ai đó đổi cỡ cửa sổ giữa lúc đang kéo.
3. **Bảy pane trong `features/` là bản chuyển tiếp của lô 0**, bọc panel cũ
   nguyên trạng. Không bọc thì `PaneHost` không có gì để render và màn hình đang
   chạy sẽ thụt lùi — mà code chưa chạy thật thì đúng là cái bẫy "xanh rỗng".
   Lô 2 viết lại ruột chúng; hợp đồng hai props vào là thứ phải chốt trước.

**Lô 1 — song song được ngay sau lô 0. ✅ XONG 2026-08-06.** Component thuần trong `ui/`, mỗi cái một
file, không đụng store: `Field` `ValueCell` `DataTable` `Empty` `Skeleton`
`ErrorBox`. Logic hiển thị số đo tập trung ở `ui/valueCell.ts`; `MeasurementPanel`
dùng `DataTable` + `ValueCell`; `MeasurementPane`/`EvidencePane` dùng `Skeleton`/
`ErrorBox`.

**Lô 2 — song song, sau lô 1. ✅ XONG 2026-08-07.** Ruột pane viết lại trong
`features/` — không còn bọc `components/panels/` (trừ `SldCanvas`). Dùng đủ
`Field` · `ValueCell` · `DataTable` · `Skeleton` · `ErrorBox` · `Empty` · bốn
trạng thái pane. `components/panels/` giữ lại cho `views/` legacy tới lô 3.

**Lô 3 — tuần tự lại.** Tách route `#/eng`, chuyển nhóm C sang bề mặt vận hành,
xoá `views/`, chạy `check.py`.

Giao lô 1 hoặc lô 2 **trước khi lô 0 xong** thì ra hai design system — đúng cái
GĐ 1.5 sinh ra để tránh.

---

## 11. Nền phân quyền — cắm chỗ, chưa dựng nhà

Theo [ADR-0016](../10-architecture/adr/0016-roles-and-capabilities.md). Mục tiêu
của GĐ 1.5 **không** phải làm xong đăng nhập, mà là làm cho việc thêm đăng nhập
sau này **không phải sửa route nào**.

### Làm — **xong 2026-08-06**

| Việc | Ở đâu | Trạng thái |
|---|---|---|
| `Capability` enum (19 quyền) | `domain/authz.py` | ✅ |
| `ROLES: dict[Role, frozenset[Capability]]` | `domain/authz.py` | ✅ 6 gói vai |
| `check_role_set()` — luật tách nhiệm vụ | `domain/authz.py` | ✅ `engineer` + vai có `control.sign` bị **từ chối khi dựng**, không chỉ khi kiểm |
| `Principal(user, roles, capabilities)` | `api/authz.py` | ✅ dựng từ `BI_ROLE` |
| `get_principal()` | `api/authz.py` | ✅ |
| `requires=` trên **18/18** facet | mọi router | ✅ mặc định **từ chối** |
| `GET /api/me` | `api/routers/me.py` | ✅ |
| `EvidenceRecord.actor` | `domain/evidence.py` | ✅ `/api/summary` ghi tên người hỏi |
| Session store + ẩn theo **quyền** | `stores/session.ts`, `authz.ts` | ✅ hỏi `can('model.connect')`, không hỏi tên vai |
| Cửa vào theo vai | `router.ts` `landingFor()` | ✅ chỗ cắm; bảng đầy đủ ở [screens.md §4.0](screens.md) khi có `PaneHost` |

Khác hợp đồng ban đầu một chỗ: `Principal` nằm ở **`api/authz.py`** chứ không
phải `api/deps.py`. `deps.py` giữ **trạng thái ứng dụng** (store, database);
trộn máy móc phụ thuộc của FastAPI vào đó làm nhoè cả hai. Cùng một khuôn mẫu:
`authz.py` sở hữu principal đúng như `deps.py` sở hữu store, kể cả hàm `use()`
để test đổi người gọi.

`BI_ROLE=engineer` là mẹo quan trọng: **đổi biến môi trường là đổi vai**, nên thử
được cả sáu bề mặt ngay hôm nay mà không cần một dòng đăng nhập nào. Nhận danh
sách ngăn cách bằng dấu phẩy — `BI_ROLE=operator,maintenance` — để luật *"một
người nhiều vai"* được chạy thật ngay từ đầu.

### Chưa làm trong GĐ 1.5

Bảng `users` / `user_roles` · băm mật khẩu · màn hình đăng nhập · phiên · nhật ký
kiểm toán. Lược đồ bảng đã chốt ở [ADR-0016 §7](../10-architecture/adr/0016-roles-and-capabilities.md)
(kèm `external_id` để sau liên thông với tài khoản ATS mà không phải di trú).

### Luật `check.py` thêm — **đã gác**

- [x] Mọi facet khai `requires=` — `check.py` mục 4, quét AST từng decorator
- [x] Danh sách quyền khớp nhau giữa `domain/authz.py` và `src/authz.ts` (cùng
      khuôn mẫu với ngữ pháp scope)
- [x] Test khoá: không facet nào lọt cổng — duyệt trên **app đã lắp**, kèm một
      test cố tình quên `requires=` để chứng minh máy dò có dò
- [x] Test khoá: `engineer` không bao giờ có `control.sign`, kể cả khi giữ nhiều vai
- [x] Test khoá: `agent/` không tự dựng được `Principal`

Một bài học đáng ghi: bản đầu của test *"mọi facet đều khai"* **xanh một cách
rỗng**. FastAPI 0.141 bọc mỗi `include_router` vào một lớp vỏ, nên `app.routes`
không chứa endpoint nào — duyệt lớp trên cùng tìm được 0 route và mọi khẳng định
đều đúng vô nghĩa. Nay có `iter_api_routes()` đi xuống, và test tự khẳng định
tìm được đủ số route trước khi kiểm bất cứ thứ gì.

### Thứ tự

Nền phân quyền là **lô 0** cùng với hợp đồng pane. Nó chạm mọi route, nên làm
trước khi ai bắt đầu lô 1 hay lô 2.

---

## 12. Nghiệm thu GĐ 1.5

Xong nghĩa là:

- [ ] `check.py` xanh, kể cả các luật mới ở §9 và §11
- [ ] `BI_ROLE=engineer` và `BI_ROLE=operator` cho ra **hai cửa vào khác nhau**
- [ ] Facet quên khai `requires=` thì **không chạy được** (thử bằng một test cố tình quên)
- [ ] Ba preset đổi qua lại được, **scope giữ nguyên khi đổi bố cục**
- [ ] Bấm vào ngăn trên SLD → mọi pane không ghim đều đổi theo
- [ ] F5 → về đúng scope **và** đúng bố cục
- [ ] Tắt DataServer → sơ đồ giữ nguyên, mọi pane vào trạng thái **suy giảm**,
      không pane nào trắng
- [ ] `earthed_while_live` hiện ở bề mặt **vận hành**, không phải kỹ thuật
- [ ] Đổi VI/EN không lòi mã máy
- [ ] Kịch bản chạy tay mới: `docs/40-testing/manual-test-03-workspace.md`
