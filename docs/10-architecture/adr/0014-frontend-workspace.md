# ADR-0014 — Frontend: shadcn-vue, workspace nhiều pane, nhiều hội thoại, i18n

- **Status**: Accepted — **§3 phần ba preset đã bị
  [ADR-0018](0018-conversation-first-workspace.md) thay thế** (2026-08-07). Mọi
  phần khác còn hiệu lực.
- **Date**: 2026-08-05
- **Bổ sung** ADR-0009 (Vite + Vue 3 + TS). **Không supersede** — nền tảng build
  giữ nguyên, ADR này chỉ thêm lớp trên.

## Bối cảnh

Frontend hiện tại (4 view, 3.680 dòng kể cả `schema.d.ts` sinh tự động) được dựng
để **kiểm chứng API**, không phải để dùng. Người dùng nhận xét đúng, và đo được:

| Bằng chứng | Chỗ |
|---|---|
| Panel operator hiện `source_ref` = **NodeId thô**, "Dbpos thô", "Logical node" | `components/panels/DevicePanel.vue` — field debug, đi ngược tinh thần I6 ở tầng nhìn |
| Khối CSS `h2` copy-paste giống hệt qua các panel | `DevicePanel.vue` và `views/StationView.vue` |
| Không có design token nào ngoài màu và `--radius` | `styles.css` — không thang cỡ chữ, không thang khoảng cách |
| **Đụng độ ngữ nghĩa màu** | `--closed` (đỏ) nghĩa là *máy cắt đang đóng* — trạng thái **bình thường**. `App.vue` lại dùng chính nó cho *"Mất kết nối"* — **sự cố**. Tương tự `--open` (xanh lá = *dao đang mở*) dùng cho *"Trực tuyến"* |
| Trạng thái rỗng / đang tải / lỗi | chỉ là một thẻ `<p class="empty">` |
| Accessibility | không có focus style, không keyboard nav, không ARIA |

Cái đụng độ màu là **lỗi an toàn**, không phải lỗi thẩm mỹ: trong cùng một màn
hình, đỏ vừa có nghĩa "bình thường" vừa có nghĩa "hỏng".

Đồng thời, yêu cầu sản phẩm đã rõ hơn hẳn (người dùng chốt 2026-08-05):

- agent là **một luồng cạnh sơ đồ**, nhưng phải **ẩn được sơ đồ** để chỉ còn chat
- màn hình chia nhiều phần, người dùng tự mở chat / sơ đồ / bảng trạng thái
- **nhiều cuộc hội thoại**
- LLM chạy **GPU local tại trạm**; giai đoạn này gọi OpenRouter
- phải có **i18n**

## Quyết định

### 1. Thư viện UI: shadcn-vue trên Vite

Giữ nguyên ADR-0009. `shadcn-vue` có đường cài cho **Vite**, không bắt buộc Nuxt
(`shadcn-nuxt` chỉ là trang cài đặt cho Nuxt của cùng thư viện đó).

Thêm vào stack: `tailwindcss` v4 (qua `@tailwindcss/vite`), `reka-ui` (lớp
primitive), `vue-i18n`. Có MCP dùng được: `npx shadcn-vue@latest mcp init --client claude`.

Không thêm Nuxt. Lý do của ADR-0009 còn nguyên: không SSR, không Node runtime ở
production, và mỗi dependency bắc cầu là một thứ có thể vỡ khi đóng gói offline
bằng Inno Setup.

### 2. Hai bảng màu tách bạch — sửa lỗi an toàn

| Bảng | Dùng cho | Màu |
|---|---|---|
| **Trạng thái trạm** | thiết bị, dây dẫn, mang điện | đỏ/xanh lá/xanh dương/tím/xám của OneATS — **không đụng vào** |
| **Trạng thái hệ thống** | kết nối, lỗi, đang tải, drift | amber / xám / accent — **cấm dùng đỏ và xanh lá** |

Bảng màu OneATS phải nâng thành theme token của Tailwind, giữ nguyên ngữ nghĩa
đã ghi trong `styles.css`. Không để `baseColor` mặc định của shadcn nuốt mất —
đó là màu an toàn, không phải màu trang trí.

**Không trạng thái nào chỉ dựa vào màu.** Luôn kèm nhãn chữ hoặc hình dạng: màn
hình cũ ở trạm, người mù màu, và `UNDETERMINED` (I2) phải nhìn ra ngay.

### 3. Workspace nhiều pane — pane là **dữ liệu**, không phải code bố cục

```ts
type Pane = {
  id: string
  kind: 'chat' | 'sld' | 'state-table' | 'measurements'
      | 'alarms' | 'evidence' | 'trend' | 'issues'
  scope: ScopeRef                 // ADR-0010
  params?: Record<string, unknown>
}
type Layout = { cols: Array<{ size: number; rows: Array<{ size: number; pane: Pane }> }> }
```

Vì `Layout` chỉ là JSON, ta được **miễn phí** bốn thứ: lưu `localStorage` · đưa
vào URL để gửi cho đồng nghiệp · **agent đề xuất được pane** vì nó chỉ cần sinh
một object · test được không cần trình duyệt.

**Bố cục có sẵn (preset), không xây trình soạn bố cục tự do:**

```
Giám sát              Hội thoại             Phân tích sự cố
┌──────────┬──────┐   ┌────────────────┐   ┌──────┬─────────┐
│          │trạng │   │                │   │      │  SLD    │
│   SLD    │thái  │   │      CHAT      │   │ CHAT ├─────────┤
│          ├──────┤   │  (toàn màn)    │   │      │evidence │
├──────────┤alarm │   │                │   │      ├─────────┤
│  alarm   │      │   │                │   │      │ alarm   │
└──────────┴──────┘   └────────────────┘   └──────┴─────────┘
```

Người dùng vẫn mở/đóng/kéo giãn từng pane. Nhưng **không** làm kéo-thả dock tự
do — lý do y hệt ADR-0003 (*"engineer không vẽ"*): xây trình soạn bố cục là xây
một sản phẩm khác. Preset + resize phủ 95%. Dùng `Resizable` của shadcn-vue.

Bố cục **"Hội thoại"** là hiện thực của yêu cầu "ẩn luôn sơ đồ, chỉ còn chat".

### 4. Agent đề xuất pane, người dùng chấp nhận

Tool trả payload + `suggested_pane` tuỳ chọn. Frontend render nó thành **nút bấm**
(*"Mở bảng số đo ngăn 271"*). Pane chỉ mở khi người bấm.

Agent **không bao giờ tự đổi bố cục** đang làm việc. Cùng nguyên tắc với ADR-0011:
*agent soạn phiếu, người ký*.

### 5. Nhiều hội thoại

- Danh sách hội thoại trong pane chat: đổi tên / ghim / xoá.
- Lưu ở SQLite (`store/sessions.py`), **không** ở bộ nhớ process — server tại
  trạm khởi động lại, và nhiều workstation cùng truy cập.
- Mỗi hội thoại mang một **ngữ cảnh scope**: đang nói về `bay:D03` thì câu sau
  *"còn dòng thì sao?"* mới hiểu được.
- Mỗi lượt lưu cả **tool call đã gọi + evidence** (ADR-0013) → mở lại hội thoại
  cũ vẫn tra được số đó từ đâu ra, và có nhật ký để gỡ khi agent trả lời sai.
- **Bố cục không gắn với hội thoại.** Bố cục thuộc về người dùng; hội thoại là
  danh sách riêng. Gắn hai thứ vào nhau là phức tạp không cần thiết.

### 6. Stream của agent tách khỏi stream của trạm

`/api/chat/{session}/stream` — **theo phiên**, không phải broadcast. Đây là ngoại
lệ có chủ ý với luật "một stream" của ADR-0012, vì vòng đời khác hẳn: stream trạm
sống suốt phiên làm việc và chung cho mọi client; stream chat sống trong một lượt
trả lời và riêng cho một người.

LLM chạy GPU local tại trạm → hàng đợi bớt căng, nhưng vẫn cần giới hạn số lượt
chạy đồng thời. `LLMProvider` giữ như đã chốt: OpenRouter (dev) → local (trạm),
đổi bằng config.

### 7. Cấu trúc thư mục

```
frontend/src/
  app/          App.vue  router.ts
    layout/     Shell  Header  PaneHost  presets.ts
  ui/           design system — shadcn-vue + component riêng của dự án
    Panel  Field  ValueCell  Badge  StateDot  DataTable
    Empty  Skeleton  ErrorBox  EvidenceBlock
  api/          client.ts  schema.d.ts  streams.ts
  scope.ts      parse/format ScopeRef — dùng chung với URL (ADR-0010)
  i18n/         vi.json (mặc định)  en.json
  stores/       structure.ts  live.ts  workspace.ts  chat.ts   ← tách theo VÒNG ĐỜI
  features/
    station/    SldCanvas  DeviceSymbol  camera
    monitoring/ StatePanel  MeasurementPanel  EnergizationPanel
    alarms/     AlarmList  AlarmFilter  Timeline
    chat/       ConversationList  MessageList  Composer  ToolTrace
    engineer/   ProjectsView  ReviewList  DriftPanel  PublishDialog
```

Store tách theo **vòng đời**, không theo tính năng — đây là lý do store hiện tại
sẽ phình: nó ôm cấu trúc, dữ liệu sống và lựa chọn UI trong cùng một chỗ.

### 8. Field kỹ thuật gập lại

NodeId, Dbpos thô, logical node → khối *"Chi tiết kỹ thuật"*, mặc định **đóng**;
mặc định **mở** ở bề mặt engineer. Operator không cần, và nó phá cảm giác sản phẩm.

### 9. i18n

`vue-i18n`, `vi` mặc định + `en`.

Backend đã sẵn sàng một nửa: `reason` của energization và `error.code` vốn đã trả
**mã**, không phải câu chữ — đó chính là khoá i18n. Phần phải rà: nhãn nào đang
là câu tiếng Việt sinh từ backend thì đổi thành `code + params`.

**Ngôn ngữ giao diện khác ngôn ngữ câu trả lời của LLM.** Hai cấu hình riêng —
người dùng có thể để UI tiếng Anh mà vẫn hỏi/đáp tiếng Việt.

## Phương án đã bác bỏ

### A. Chuyển sang Nuxt để dùng `shadcn-nuxt`
**Bác bỏ** — cùng một thư viện, `shadcn-vue` chạy trên Vite. Đổi sang Nuxt là trả
giá (dependency bắc cầu cho bản cài offline, lớp build Nitro không dùng) để lấy
thứ đã có sẵn.

### B. Kéo-thả dock tự do (dockview / golden-layout)
Mạnh nhất. **Bác bỏ** — là một sản phẩm riêng, và lặp lại đúng cái bẫy ADR-0003
đã tránh. Preset + resize đủ.

### C. Chat là một route riêng thay vì một pane
Đơn giản hơn. **Bác bỏ** — mất đúng giá trị chính: vừa hỏi vừa nhìn sơ đồ. Bố
cục "Hội thoại" đã cho trường hợp chat toàn màn.

### D. Tự viết design system từ đầu
Kiểm soát tối đa, ít dependency. **Bác bỏ** — người dùng yêu cầu đi nhanh, và
accessibility (focus, keyboard, ARIA) tự viết thì tốn và sẽ làm dở.

### E. Giữ `styles.css` thủ công, chỉ thêm component shadcn
**Bác bỏ** — shadcn-vue dựa trên Tailwind; trộn hai hệ style là có hai nguồn sự
thật về khoảng cách và màu, đúng thứ đang gây copy-paste CSS hiện nay.

## Hệ quả

**Tích cực**

- Thêm loại pane = 1 component + 1 dòng đăng ký, không đẻ nhánh `v-if`.
- Chat, click sơ đồ và danh sách alarm dùng **chung một cơ chế chọn** (scope trong URL).
- Bố cục chia sẻ được bằng link, khôi phục được sau khi đóng trình duyệt.
- Accessibility và trạng thái rỗng/lỗi được thư viện lo phần lớn.
- Sửa được lỗi an toàn về màu.

**Tiêu cực**

- Tailwind v4 thay `styles.css` → viết lại style của mọi component hiện có.
  Đây là công việc thật, nằm ở GĐ 0.
- Nhiều dependency hơn ADR-0009 dự tính → phải kiểm chứng lại việc vendor cho
  bản cài offline. **Rủi ro có thật**, phải thử `npm ci --offline` trước khi
  đóng gói, không để tới lúc cài ở trạm mới biết.
- shadcn-vue là **copy component vào repo**, không phải dependency thường →
  code trong `ui/` là code của ta, ta bảo trì. Đánh đổi có chủ ý.

**Việc phải làm để ADR này không mục**

- `npm run check` phải gác cả Tailwind/i18n (không để key i18n thiếu lọt qua).
- Test khoá: không component nào ngoài `features/engineer/` hiển thị NodeId.
- Preset bố cục nằm trong `app/layout/presets.ts` — một chỗ, không rải trong view.
