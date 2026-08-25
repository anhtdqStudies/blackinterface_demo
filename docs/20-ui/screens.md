# Danh mục màn hình và luồng người dùng

> **Trạng thái**: bản phác thảo đầu tiên, 2026-08-06. Đây là **thiết kế**, không
> phải đo đạc — không có số nào ở đây được lấy từ trạm thật.
>
> **Tài liệu này quyết định**: có bao nhiêu pane, bao nhiêu bố cục, người dùng đi
> từ đâu tới đâu, và mỗi pane phải xử lý những trạng thái nào.
>
> **Tài liệu này KHÔNG quyết định**: màu sắc, cỡ chữ, khoảng cách — đó là
> `tokens.md` (chưa viết). Cũng không quyết định thư viện — đó là
> [ADR-0014](../10-architecture/adr/0014-frontend-workspace.md).
>
> **Hợp đồng thi công** (kiểu dữ liệu `Pane`/`Layout`, cây thư mục, thứ tự lô,
> luật `check.py`): [`frontend-architecture.md`](frontend-architecture.md).

---

## 1. Nguyên tắc: màn hình = bố cục × scope

Không có cây route. Một màn hình được xác định bởi **hai** thứ:

```
#/ops/<scope>?tab=<kind>
      ▲          ▲
      │          └── tab workspace: sld | state | measurements | …
      └── đang nói về cái gì (ADR-0010): station · vl:220kV · bay:D03 · device:D03.XCBR1
```

Hệ quả cố ý: **đổi scope không đổi bố cục, đổi bố cục không đổi scope.** Người
vận hành đang xem sơ đồ + alarm, bấm vào một ngăn → vẫn sơ đồ + alarm, chỉ là
của ngăn đó. Đây là lý do ADR-0014 nói *"bố cục không gắn với hội thoại"*, mở
rộng ra cả scope.

Thêm một loại pane = thêm 1 component + 1 dòng đăng ký. **Không** thêm route,
**không** thêm nhánh `v-if` trong view.

### Hai bề mặt, không phải một

| Bề mặt | URL | Vai trò | Vòng đời |
|---|---|---|---|
| **Operator** | `#/ops/<scope>` | vận hành | mô hình đã publish, đã pin `ModelVersion` |
| **Engineer** | `#/eng/...` | dựng & duyệt project | mô hình **chưa** publish, đang sửa |

Tách bằng route chứ không bằng pane, vì vòng đời dữ liệu khác hẳn: bề mặt
engineer làm việc trên bản nháp, bề mặt operator làm việc trên bản đã chốt. Trộn
hai cái là mở đường cho việc vận hành trên mô hình chưa duyệt.

**Luật khoá** (ADR-0014 §8): không component nào ngoài bề mặt engineer được hiện
NodeId, Dbpos thô, hay tên logical node. **Gác bằng `check.py` mục 5 từ
2026-08-07** — trước đó dòng này ghi "đã có test" mà không có test nào, và pane
`state` của operator hiện đủ cả ba.

---

## 2. Danh mục pane

Mỗi dòng là một `Pane.kind`. Cột **Scope có nghĩa** rất quan trọng: một pane
được hỏi về scope nó không phục vụ thì hiện **trạng thái rỗng có giải thích**,
không phải trống trơn, và tuyệt đối không tự nới scope ra.

### Bề mặt operator

| kind | Nội dung | Scope có nghĩa | Module | Tình trạng |
|---|---|---|---|---|
| `sld` | Sơ đồ một sợi + overlay mang điện | `station` `vl` `transformer` | A | ✅ có (`SldCanvas`) |
| `anomalies` | **Mâu thuẫn ta tự phát hiện**: tiếp địa đóng trên đoạn có điện · hai thanh cái nối cứng báo `IsLive` ngược nhau · ta tính khác OneATS | **luôn toàn trạm** — xem dưới | A | ✅ có (lô 3) — chỉ nhóm C |
| `state` | Bảng trạng thái đóng/mở/tiếp địa | mọi scope | A | ✅ có (lô 2) — `StatePane` + `DeviceStateContent`, theo prop `scope` |
| `measurements` | Số đo P/Q/U/I/Hz/PF/nấc MBA | `bay` `busbar` `transformer` `station` | A | ✅ có |
| `energization` | Mang điện + **lý do** mang điện | mọi scope | A | ✅ có |
| `evidence` | Nguồn, độ phủ, cảnh báo của câu trả lời | bám pane nguồn | — | ✅ có |
| `chat` | Hội thoại với agent | scope là ngữ cảnh hội thoại | agent | ⬜ GĐ 2 |
| `alarms` | Alarm đang hoạt, lọc theo scope | `station` `vl` `bay` | B | ⬜ GĐ 3 |
| `soe` | Timeline sự kiện theo thời gian | mọi scope | B | ⬜ GĐ 3 |
| `report` | Báo cáo dựng sẵn | `station` `vl` | E | ⬜ GĐ 4 |
| `knowledge` | Tra cứu quy trình / SOP | tự do, không theo scope | F | ⬜ GĐ 4 |
| `trend` | Đồ thị theo thời gian | `point` `bay` | D | ⬜ GĐ 5 (chờ HIS) |

**Ngoại lệ có chủ ý: `anomalies` không đi theo scope** (người dùng chốt
2026-08-07). Mọi pane khác trả lời *về cái bạn vừa bấm*; pane này trả lời *đang
có gì sai, ở bất cứ đâu* — hai câu hỏi khác nhau. Dao tiếp địa đóng trên đoạn có
điện ở D12 không bớt khẩn cấp vì người trực đang xem E07, và lọc nó đi là giấu
đúng cái mà pane này sinh ra để hiện.

Cái giá là ô này nói khác các ô bên cạnh về thứ đang trên màn hình, nên nó
**phải tự khai**: khi workspace đang nhắm vào scope hẹp hơn `station`, pane hiện
dòng *«Toàn trạm — cố ý không lọc theo bay:D03»*. Cùng một luật với pane bị ghim
(§ hợp đồng pane): một ô không đi theo màn hình thì phải nói ra, nếu không nó
thành cái bẫy.

### Bề mặt engineer

| kind | Nội dung | Tình trạng |
|---|---|---|
| `connections` | Danh sách trạm đã nối + refresh (thay cho "Projects") | ✅ có (lô 3) |
| `coverage` | Độ phủ binding: bao nhiêu điểm gán được | ✅ có |
| `model-issues` | **Chỉ** issue về mô hình (nhóm A+B dưới đây) | ✅ có (lô 3) — lọc A+B |
| `binding` | NodeId thô, Dbpos, logical node — **chỉ ở đây** (ADR-0014 §8) | ⬜ — từ 2026-08-07 ba trường này **không hiện ở đâu cả**, chờ pane này |
| `template-editor` | Soạn template ([ADR-0015](../10-architecture/adr/0015-engineer-authored-templates.md)) | ⬜ **GĐ 2.5** |

**Không làm `bay-review` (bay-card duyệt từng ngăn).** Đo trên DEMO_SAS: 13/13
ngăn, 80/80 thiết bị, **0 ERROR**, 1 WARNING không sửa được. Màn hình đó sẽ là 13
dấu ✓ — một màn hình vô dụng. Nó được nhập từ `vision.md` viết **trước khi đo**.

### 12 mã issue chia làm ba nhóm, ba cách xử lý khác nhau

Trước lô 3 cả ba đổ chung vào một `IssuesView`. Đó là lỗi, và nhóm C là lỗi
**an toàn**. Đã tách: backend phân nhóm ở `domain/issue_groups.py` (chỗ **duy
nhất**), frontend lọc theo trường `group` chứ không theo danh sách mã cứng.

| Nhóm | Mã | Sửa thế nào | Hiện ở đâu |
|---|---|---|---|
| **A — mô hình chưa suy được** | `bay_type_unknown` `template_missing` `slot_missing` `slot_unmapped` | **Không bấm nút được.** Phải sửa template/luật. Việc của ATS, hoặc của trình soạn template ở GĐ 2.5 | engineer |
| **B — sự thật về DataServer** | `busbar_not_in_source` `busbar_unreferenced` `unknown_voltage_code` `transformer_unpaired` `transformer_winding_unresolved` | Chấp nhận, hoặc **chỉ tay** — engineer chỉ cần đúng **hai** ô override: loại ngăn, ghép cuộn MBA | engineer |
| **C — trạng thái vận hành** | `earthed_while_live` `energization_conflict` `energization_mismatch` | **Không sửa gì cả** — phải điều tra | **operator**, pane `anomalies` |

`earthed_while_live` là ERROR nghĩa là *"tiếp địa đang đóng trên đoạn đo được là
có điện"*. Đó là **sự cố hoặc dữ liệu sai**, không phải lỗi mô hình. Chôn nó
trong tab engineer là để người trực không bao giờ nhìn thấy.

---

## 3. Bố cục vận hành (ADR-0018 — thi công 2026-08-10)

Một layout duy nhất. Không preset, không `?l=`. URL: `#/ops/<scope>?tab=<kind>`.

```
┌────────────────────────────────────────────────────────────────────────────┐
│  BLACK INTERFACE   Trạm Bến Cát        [● Trực tuyến]   [VI|EN]  [Kỹ thuật]│
├───────────────┬────────────────────────────────────────────────────────────┤
│ HỘI THOẠI [+] │  NGĂN D03 — Hóc Môn                                        │
│ ‹thu gọn›     │  [Sơ đồ][Trạng thái][Số đo][Mang điện][Bất thường❷][BC]  │
│ ───────────── │  ┌──────────────────────────────────────────────────────┐  │
│ transcript    │  │ tab active — full height (SLD hoặc bảng)             │  │
│               │  └──────────────────────────────────────────────────────┘  │
│ [Về D03]      │                                                            │
│ [ hỏi... ]    │                                                            │
└───────────────┴────────────────────────────────────────────────────────────┘
```

- **Trái (~32%)**: `chat` thường trực; thu gọn bằng splitter + nút.
- **Phải**: thanh tab gồm **Sơ đồ** (mặc định) + các pane giám sát; tab active chiếm 100% chiều cao.
- **Chip scope** trên composer; **nút đề xuất tab** sau câu trả lời agent (người bấm, không tự chuyển).
- Tab `anomalies`: badge số; nhóm C ERROR → tự chuyển tab (trừ khi người dùng vừa chọn tab khác).

Legacy `?l=monitor|chat|incident` → bỏ query, layout mới.

### 3.1 Bề mặt engineer — `#/eng` (một màn hình, không phải một quy trình)

```
┌────────────────────────────────────────────────────────────────────────────┐
│  KỸ THUẬT · Bến Cát 220kV     DataServer v654          [ Chốt bản ▸ ]      │
├────────────────────────────────────────────────────────────────────────────┤
│  KẾT NỐI                                                                   │
│  ● Bến Cát 220kV   opc.tcp://127.0.0.1:48050      [Tải lại] [Xoá]         │
│    Ảnh chụp 2026-08-06 10:32 · ModelVersion 654                            │
│                                                    [ + Nối trạm mới ]      │
├────────────────────────────────────────────────────────────────────────────┤
│  ĐỘ PHỦ   ████████████████████  13/13 ngăn · 80/80 thiết bị · 159/159 điểm │
├────────────────────────────────────────────────────────────────────────────┤
│  VẤN ĐỀ MÔ HÌNH                                                     [1]    │
│                                                                            │
│  Nhóm B — sự thật về DataServer                                            │
│  ⚠ busbar_not_in_source · J01                                              │
│    Ngăn J01 nối thanh cái BB41 nhưng DataServer không có đối tượng đó.     │
│    Đã thêm dạng suy diễn, KHÔNG mang dữ liệu sống.                         │
│    [ Chấp nhận và ghi nhận ]                                               │
│                                                                            │
│  (Nhóm A — cần template mới → chép mô tả gửi ATS, xem GĐ 2.5)              │
├────────────────────────────────────────────────────────────────────────────┤
│  ▸ Chi tiết kỹ thuật   (mở sẵn ở bề mặt này, đóng ở bề mặt vận hành)       │
│     D17.XCBR1.PosSt → ns=2;s=/SAS/BAY17/XCBR1/PosSt                        │
└────────────────────────────────────────────────────────────────────────────┘
```

Ba việc, hết:

1. **Nối trạm** — tạo, tải lại, xoá (đã có ở backend)
2. **Xem vấn đề mô hình** — chấp nhận cái không sửa được; override đúng **hai** thứ:
   loại ngăn và ghép cuộn MBA
3. **Chốt bản** — pin `ModelVersion` + hash + phiên bản template ([ADR-0015 §6](../10-architecture/adr/0015-engineer-authored-templates.md))

**Không có publish theo nghĩa "chọn một trong nhiều bản".** Topology suy tất định
từ DataServer, nên hai project cùng một DataServer cho ra kết quả giống hệt nhau
— không có gì để chọn. "Chốt bản" là **đóng băng để về sau phát hiện drift**, một
nút bấm chứ không phải một quy trình. Từ GĐ 2.5 nó mang thêm nghĩa thứ hai: bộ
template này đã qua cổng chứng minh.

Ở GĐ 2.5 màn hình này mọc thêm một mục: **trình soạn template**.

---

## 4. Luồng người dùng

### 4.0 Từ đăng nhập tới thao tác — luồng chuẩn cho mọi vai

Đây là luồng gốc; §4.1–4.3 là các nhánh của nó. Vai và quyền theo
[ADR-0016](../10-architecture/adr/0016-roles-and-capabilities.md).

```
mở trình duyệt
      │
      ▼
  đã đăng nhập chưa?
      │
      ├── chưa ──► MÀN HÌNH ĐĂNG NHẬP
      │              │  tên + mật khẩu
      │              ▼
      │           backend trả:  { user, roles[], capabilities[] }
      │              │          quyền hiệu lực = HỢP của các vai
      │              ▼
      └── rồi ─────► CỬA VÀO THEO VAI  ← không phải ai cũng vào SLD
                     │
     ┌───────────────┼──────────────┬──────────────┬─────────────┐
     ▼               ▼              ▼              ▼             ▼
  operator /     maintenance    protection      engineer      admin
  supervisor          │              │              │             │
     │                │              │              │             │
  TÌNH HÌNH TRẠM   SỨC KHOẺ      SỰ KIỆN        #/eng        TÀI KHOẢN
  (AI tóm tắt)     KỸ THUẬT      BẢO VỆ                      NHẬT KÝ
     │             truyền thông  trip/reclose                KNOWLEDGE
     │             nguồn AC/DC   interlock
     ▼
  ┌──────────────────────────────────────────────────────┐
  │  "Trạm bình thường. 3 cảnh báo, 1 đáng chú ý:        │
  │   D03 bảo vệ khoảng cách khởi động lúc 10:42."       │
  │                                                      │
  │   [ Xem sơ đồ ]   [ Hỏi thêm ]   [ Xem cảnh báo ]    │
  └──────────────────────────────────────────────────────┘
     │
     ├── hỏi AI ─────────► trả lời + BẰNG CHỨNG (+ đề xuất mở pane)
     │
     ├── [Xem sơ đồ] ────► #/ops/station?l=monitor   ← xác minh bằng mắt
     │
     ├── bấm cảnh báo ───► scope nhảy tới ngăn đó
     │
     └── cần thao tác ───► SOẠN PHIẾU  (cần control.draft)
                              │
                              ▼
                           phiếu "CHỜ KÝ"
                              │
                              ▼
                           KÝ  (cần control.sign — có thể cùng người,
                                có thể người khác, tuỳ trạm gán vai)
                              │
                              ▼
                           control/ kiểm lại lần nữa → lệnh xuống trạm
```

**Cửa vào không phải SLD.** Sản phẩm nhắm vào **trạm không người trực và trạm ít
người**: không ai ngồi nhìn sơ đồ cả ca. Cửa vào là **bản tóm tắt AI dựng**; SLD
là nơi **xác minh** khi bản tóm tắt nói có chuyện.

**Quyền quyết định nhìn thấy gì, không chỉ bấm được gì.** Nút nào không có quyền
thì **không hiện**, không phải hiện rồi báo lỗi. Nhưng đó chỉ là cho đỡ rối — thẩm
quyền thật nằm ở tầng facet của backend (ADR-0016 §4).

**Một người giữ nhiều vai.** Trạm ít người: một tài khoản giữ
`operator + supervisor + maintenance`, cửa vào là Tình hình trạm, và ký được phiếu
mình vừa soạn — vẫn hai bước bấm, vẫn ghi đúng tên trong nhật ký.

### 4.1 Operator — ca trực bình thường

```
mở trình duyệt
    │
    ▼
#/ops/station?l=monitor          bố cục Giám sát, cả trạm
    │
    ├── liếc SLD ──────────────► không có gì lạ → không thao tác gì
    │
    ├── bấm một ngăn trên SLD
    │       │
    │       ▼
    │   #/ops/bay:D03?l=monitor  ◄── URL đổi, BỐ CỤC GIỮ NGUYÊN
    │       │                        panel phải đổi sang D03
    │       │
    │       └── bấm nút [↑] ──► quay lên #/ops/vl:220kV
    │
    └── bấm một alarm trong pane alarms
            │
            ▼
        scope nhảy tới ngăn của alarm đó — cùng một cơ chế chọn
        (ADR-0014 hệ quả: chat, click SLD, click alarm dùng CHUNG scope trong URL)
```

### 4.2 Operator — có sự cố

```
alarm nổi lên
    │
    ▼
bấm alarm → scope = bay:D03
    │
    ▼
đổi bố cục sang [Phân tích sự cố]     ◄── scope GIỮ NGUYÊN
    │
    ▼
hỏi agent: "vì sao D03 mất điện?"
    │   (không cần nói "D03" — chip ngữ cảnh đã mang scope)
    ▼
agent trả lời + BẰNG CHỨNG + đề xuất pane
    │
    ├── người bấm [Xem SOE đầy đủ] ──► pane soe mở ra
    │
    └── người KHÔNG bấm ────────────► không có gì thay đổi
                                       agent không bao giờ tự đổi bố cục
```

### 4.3 Engineer — nối một trạm mới

```
#/eng
    │
    ▼
[+ Nối trạm mới] → nhập endpoint DataServer
    │
    ▼
browse address space          ~2–3 phút, PHẢI có tiến độ + huỷ được
    │                          (17.9k node — màn hình đứng im 3 phút là hỏng)
    ▼
khớp chữ ký → áp template → auto-bind      (đo được: 13/13 ngăn, 80/80 thiết bị)
    │
    ├── nhóm A (thiếu template) ──► chép mô tả gửi ATS. Ngăn đó hiện rõ là
    │                                "chưa dựng được", KHÔNG đoán bừa
    ├── nhóm B ──────────────────► [Chấp nhận] hoặc override (loại ngăn / cuộn MBA)
    └── nhóm C ──────────────────► KHÔNG hiện ở đây. Đẩy sang pane `anomalies`
    │                                của bề mặt vận hành
    ▼
[Chốt bản] → pin ModelVersion + hash + phiên bản template
    │        (từ GĐ 2.5: phải qua cổng chứng minh, 0 lệch với IsLive)
    ▼
#/ops/station
```

### 4.4 Chỗ chuyển giữa hai bề mặt

Chỉ **hai** cửa, không có cửa nào khác:

- `#/eng` → **Chốt bản** → `#/ops/station`
- `#/ops/*` → menu → `#/eng` (phải bấm có chủ ý)

Không có nút "sửa nhanh" từ màn hình operator. Sửa mô hình là việc có duyệt và
có publish, không phải thao tác giữa ca.

---

## 5. Bốn trạng thái bắt buộc của mọi pane

Đây là chỗ frontend hiện tại yếu nhất — mọi thứ đang là một thẻ `<p class="empty">`.
**Mỗi** pane phải xử lý đủ bốn, và ba trong số đó dùng **màu hệ thống**, không
bao giờ đỏ/xanh lá:

| Trạng thái | Trông thế nào | Sai thì sao |
|---|---|---|
| **Đang tải** | `Skeleton` giữ đúng chỗ, không nhảy layout | Nhảy layout khi dữ liệu về = người dùng bấm nhầm |
| **Rỗng có lý do** | Câu giải thích + việc làm tiếp theo | *"Không có số đo"* là vô dụng. Phải là *"Cấp điện áp không mang số đo — chọn một ngăn"* |
| **Lỗi** | `ErrorBox` + mã lỗi + nút thử lại | Nuốt lỗi rồi hiện trống = **trạm rỗng trông y hệt trạm cắt hết điện** |
| **Suy giảm** | Có dữ liệu **nhưng** kèm cảnh báo | Đây là cái `EvidenceBlock` làm. Mất kết nối mà vẫn hiện số như bình thường là lừa người vận hành |

Trạng thái **suy giảm** là loại riêng, không phải "lỗi nhẹ". Nó có dữ liệu dùng
được, chỉ là kém tin hơn — và đó là trạng thái *thường gặp nhất* trên trạm thật.

---

## 6. Ràng buộc màn hình

- **Thiết kế cho ≥ 1280 px.** Đây là màn hình phòng điều khiển, không phải điện
  thoại. Dưới 1024 px xếp chồng một cột và bỏ pane phụ — dùng được, không tối ưu.
- **Không trạng thái nào chỉ dựa vào màu** (ADR-0014 §2). Luôn kèm chữ hoặc hình
  dạng: màn hình cũ ở trạm, người mù màu, và `UNDETERMINED` (I2) phải nhìn ra ngay.
- **Bàn phím đi được hết**: Tab qua pane, `Esc` đóng pane, `/` nhảy vào ô chat.
- **Không tự làm mới trang.** Realtime đến qua SSE; F5 giữa ca là mất chỗ đang xem.

---

## 7. Cái KHÔNG làm

| Không làm | Vì sao |
|---|---|
| Dock kéo-thả tự do | Là một sản phẩm riêng. Preset + resize phủ 95% (ADR-0014, phương án bác bỏ B) |
| Canvas vẽ SLD | Chính là Grid Designer đang muốn thay thế (ADR-0003) |
| Chat thành route riêng | Mất giá trị chính: vừa hỏi vừa nhìn sơ đồ (ADR-0014 pbác C) |
| Agent tự đổi bố cục | Agent soạn phiếu, người ký (ADR-0011) |
| Dashboard tuỳ biến kiểu Grafana | Không phải bài toán này. Scope + preset là đủ |
| Dark/light toggle ở GĐ này | Phòng điều khiển dùng một chế độ. Thêm sau nếu ai xin |

---

## 8. Lệch giữa tài liệu này và code hôm nay

Ghi ra để không tự lừa mình. Đây là phạm vi **GĐ 1.5**.

| Cần | Có | Việc |
|---|---|---|
| `app/layout/` — `Shell` `Header` `PaneHost` `presets.ts` | ❌ `App.vue` 148 dòng làm luôn header | dựng mới |
| `Pane` / `Layout` / preset trong `stores/workspace.ts` | ❌ store chỉ giữ scope | thêm, giữ nguyên phần scope |
| `features/{station,monitoring,alarms,chat,engineer}/` | ❌ `views/` + `components/panels/` | chuyển chỗ |
| `ui/`: 10 component | ⚠️ 4 (`Panel` `Badge` `StatusDot` `EvidenceBlock`) | thêm `Field` `ValueCell` `DataTable` `Empty` `Skeleton` `ErrorBox` |
| Bốn trạng thái mỗi pane | ❌ chỉ có `<p class="empty">` | làm cùng lúc với `ui/` |
| Bề mặt engineer tách khỏi operator | ❌ `/projects` `/issues` nằm lẫn | tách route |
| Bố cục vào URL (`?l=`) | ❌ | thêm |

Toàn bộ frontend hiện là **1.314 dòng**. Đập lại bây giờ rẻ hơn sau GĐ 2 nhiều,
vì chat **là một pane** — chưa có `PaneHost` thì nó sẽ thành view cố định thứ 5.
