# Trạng thái dự án

> **File này là bộ nhớ xuyên phiên.** Mọi AI agent đọc nó đầu phiên và cập nhật cuối phiên.
> Không cập nhật = phiên sau mất trí nhớ. Đây là chi phí lớn nhất của dự án này.

**Cập nhật lần cuối**: 2026-08-10 (phiên trạm thứ hai) · **Importer chạy được trên
T220PHOCAO** ✅ — 23 ngăn, 6 thanh cái, 2 MBA. `check.py` xanh.

*Trước đó cùng ngày*: **SLD fit mặc định + tab Trạng thái** · **Chat markdown** · **ADR-0018 layout**.

---

## 🔴 Trạm thứ hai: T220PHOCAO (Phố Cao) — đo 2026-08-10

DataServer dev **không còn chạy DEMO_SAS**; project hiện tại là `T220PHOCAO`
v1052, node trạm `T220PCA`. Hình dạng address space khác DEMO ở ba chỗ — đã ghi
đầy đủ ở `docs/30-integration/oneats-dataserver.md` §2 và xử lý trong
`integration/naming.py` (mới, dùng chung cho hai importer).

**Đã xong**:

- `discover_station()` và `parse_dump()` cùng ra **23 ngăn / 6 thanh cái / 2 MBA**.
- `build_station()` phân loại **23/23 ngăn**, đặt hết thiết bị vào template.
  Ghép MBA: AT1 = D04+E06, AT2 = D10+E17+J01.
- Còn đúng 3 issue, cả 3 đều đúng: `busbar_not_in_source` cho BB41 (22kV không có
  object thanh cái — y như DEMO), và `slot_unmapped` cho DBB/EBB (xem T6).
- `probe_dataserver.py` tự dò trạm, dump được fixture trạm mới (3.287/46.149 node).
- **Dialect số hiệu LN** đã xử lý bằng `aliases` trong template + `infer_bay_type`
  đọc **chữ số đầu** của LN tiếp địa thay vì cả hai chữ số:

  | thiết bị EVN | DEMO_SAS | T220PHOCAO |
  |---|---|---|
  | -15 / -14 | `XSWI11` / `XSWI12` | `XSWI15` / `XSWI14` |
  | -25 / -24 | `XSWI21` / `XSWI22` | `XSWI25` / `XSWI24` |
  | -75 / -76 | `XSWI71` / `XSWI72` | `XSWI75` / `XSWI76` |
  | -35 / -38 | `XSWI31` / `XSWI32` | `XSWI35` / `XSWI38` |
  | -95 / -94 | `XSWI91` / `XSWI92` | `XSWI95` / `XSWI94` ⚠ |

  ⚠ **GIẢ ĐỊNH — chưa xác minh** (người dùng xác nhận chưa biết, 2026-08-10):
  không có bằng chứng nào nói -94 hay -95 nằm phía nào của máy cắt ngăn vòng.
  Cả hai nối vào **cùng một nút** (`n_b`) nên kết quả điện giống hệt nhau, chỉ
  khác chỗ vẽ trái/phải. Ghi ở `T4_BUS_TRANSFER.yaml`; giải quyết cùng Q6.

  Id thiết bị vẫn giữ cách viết của template (`device:D03.XSWI11`) để scope ref
  không đổi theo project (I8) — chỉ lúc **tra observation** mới dùng alias.

**Còn dở:**

1. **Trạm chưa có dữ liệu trường.** Mọi `PosSt`, mọi measurand đọc về
   `BadWaitingForInitialData`; **không có `IsLive` ở đâu cả** (DEMO có ở
   `<bay>/IsLive`). Chỉ `Name`, `BAY/Name`, `Subs/BB*/PPVmax`,
   `IsPowerSource` là Good. Nên sơ đồ sẽ dựng đúng hình nhưng toàn `UNDETERMINED`
   (xám) — đúng theo I2, không phải lỗi. Đối chiếu energization (`<bay>.IsLive`)
   **không dùng được** trên trạm này.

---

## ⬅ VIỆC KẾ TIẾP

1. ✅ Refactor frontend UI (shadcn-vue, dense ops, tokens.md)
2. ✅ **ADR-0018 layout** — chat trái + tab phải, SLD = tab, `?tab=`
3. ✅ **Model thật đã chạy** — người dùng xác nhận 2026-08-10
4. ✅ **Trí nhớ hội thoại** (ADR-0022)
5. ⬅ **Nhìn chat markdown + layout mới bằng mắt** — rồi tiếp tool `trace`
6. **`trace`** — tool quan trọng nhất còn thiếu
7. **Eval suite** gọi 27B thật, opt-in env, ngoài `check.py`
8. **Khung duyệt** + `draft_operation` + `control.sign` ở UI
9. Dọn legacy CSS (`button {}`, alias `--bg`) khi hết pane dùng class cũ

### Còn chưa xác minh với endpoint thật

- ✅ ~~Chưa gọi OpenRouter lần nào~~ — **đã gọi thật 2026-08-10**.
  **Còn thiếu và phải hỏi người dùng, đừng đoán** (§5.4): model nào, endpoint
  nào, câu hỏi nào đã thử, câu trả lời có đúng không, có bao nhiêu lượt tool.
- **`llm_count_tokens_before_request` vẫn mặc định TẮT.** Giờ đã có endpoint
  thật để thử — món rẻ nhất còn lại. `llm_max_turn_tokens` vẫn chặn sau khi gửi.
- Chưa có máy trạm (RTX 5090) để đo tok/s một lượt — ADR-0021 §7, GIẢ ĐỊNH.
- **Lịch sử hội thoại tốn bao nhiêu token: CHƯA ĐO.** 4 lượt văn xuôi × ~5 câu
  ước lượng vài trăm token — *ước lượng*, không phải số đo. Đo bằng `tiktoken`
  như đã làm với `digest`, đừng dùng lại con số ước.

### Bật model thật để thử

`#/eng` → khối **Mô hình ngôn ngữ** → endpoint kiểu OpenAI, model
`qwen/qwen3.6-27b`, dán key OpenRouter → **Lưu** → **Thử kết nối**. Rồi về
`#/ops/station?l=chat` và hỏi `so sánh 271 với Ben Cat`.

Chưa cấu hình thì tab hội thoại nói **chưa cấu hình** — không còn trả lời bằng
template. Sơ đồ và bảng giám sát không phụ thuộc vào model (I5).

### SỰ THẬT ĐÃ ĐO — kích thước payload `summary` (2026-08-07)

**Đo trên**: `DEMO_SAS`, ModelVersion **654**, nguồn `snapshot:opc.tcp://127.0.0.1:48050`,
13 ngăn / 80 thiết bị. **Đo lại bằng**: gọi thẳng `build_summary(store, scope)`
sau `await store.startup()`, rồi đếm token bằng **`tiktoken` `cl100k_base`**
(không phải ước lượng ký tự — xem cảnh báo dưới bảng).

| scope | payload ký tự | payload **token** | `digest` token | giảm |
|---|---:|---:|---:|---:|
| `station` | 50.339 | **20.064** | **715** | 96,4% |
| `bay:E01` | 4.969 | **1.929** | **193** | 90,0% |

Trong payload `station`: số đo 26.231 ký tự (52%), **evidence 25.532 ký tự (51%)**,
issues 219. Một `ReadingOut` = **313 ký tự**. 79 số đo; `evidence.quality` có
**159 điểm**, `evidence.limits` có 4 caveat.

> ⚠ **Ước lượng «3,2 ký tự/token» của ADR-0021 §5 là SAI — thực tế ~2,5.**
> Payload `station` không phải ~15.700 token mà là **20.064**. JSON đầy
> identifier tokenize tệ hơn tôi giả định. Kết luận không đổi (vẫn phải rút gọn),
> nhưng **đừng dùng lại con số 3,2** — dùng `tiktoken` để đo.

**Ba kết luận, và cái thứ nhất là cái không ai đoán trước:**

1. **Evidence chiếm ~một nửa payload** — 51% ở `station`, 59% ở một ngăn. Mà
   evidence **không được** đi vào context của mô hình: I3 nói nó do tool sinh và
   UI hiện riêng, `loop.py` SYSTEM cũng đã dặn *"Do not list the evidence"*. Bỏ
   evidence khỏi `digest` là **giảm một nửa mà không mất gì**.
2. Bỏ evidence thôi thì chưa đủ — phải rút gọn cả số đo. Đã làm trong
   `agent/digest.py`: một số đo còn ~50 ký tự thay vì 313 (bỏ `raw_value`,
   `deadband_*`, `source_timestamp`, làm tròn 3 chữ số có nghĩa), cắt ở
   `MAX_READINGS = 40` kèm câu chỉ cho mô hình cách thu hẹp.
3. **`source_ref` bị chặn khỏi digest vì I6, không phải vì kích thước** — đó là
   NodeId thô, không tầng nào ngoài `integration/` được thấy. Một mô hình ngôn
   ngữ không phải ngoại lệ.

**Kết quả: trần 2k/tool-digest của ADR-0021 §5 đạt được với biên rộng** — 715
token cho cả trạm. Một lượt 6 bước ≈ 4–5k token tool result, thừa chỗ trong
40–60k KV của máy trạm.

Còn một luật nữa `digest.py` phải giữ: **đơn vị `?` không bao giờ in như đơn vị.**
DataServer không công bố `EngineeringUnits` (đo 2026-08-06) nên `Vlin = 221.08`
có thể là V hoặc kV. Digest in `(thang?)` + chú giải cấm tự suy ra kV/MW.

---

## Đang ở đâu (theo code, chưa tính ADR-0021)

**GĐ 2 bước 1 và 2 XONG + ADR-0020 đã thi công.** Bước 3 cũ (nhìn nó chạy, dựng
vỏ ADR-0018) **bị chen ngang** bởi ADR-0021 — dựng vỏ trước khi đổi `agent/` là
dựng hai lần.

> **Thứ tự GĐ 2 đã chốt** (người dùng, 2026-08-07):
> 1. ✅ `agent/` + 2 tool (`resolve`, `summary`) + `LLMProvider` + streaming
> 2. ✅ `ChatPane` thật, cắm vào `PANE_COMPONENTS.chat` — một dòng, hợp đồng
>    pane không đụng tới, đúng như ADR-0014 §3 hứa
> 2b. ✅ **ADR-0020** — mô hình chọn tool (`agent/loop.py`); key + model lưu
>    trong SQLite, cấu hình ở `#/eng`. Người dùng gọi sớm điều kiện xét lại của
>    ADR-0019 §2, với lý do đúng: *"như hiện tại toàn là logic, chẳng có tí AI
>    nào cả"*
> 3. ✅ **ADR-0018 layout** — chat trái + tab phải (`?tab=`, SLD default)
> 4. ⬅ **Nhìn nó chạy bằng mắt** trên layout mới

**Bật mô hình thật** — không sửa file nào, làm trên giao diện:

1. Sinh khoá mã hoá rồi khởi động với nó (một lần cho cả máy):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   BI_SECRET_KEY=<chuỗi vừa sinh> uv run uvicorn blackinterface.api.app:app --port 8080
   ```
2. Đăng nhập `engineer` → `#/eng` → khối **Mô hình ngôn ngữ**
3. Chọn endpoint kiểu OpenAI, dán tên model + key, **Lưu**, rồi **Thử kết nối**
4. Về `#/ops/station?l=chat` và hỏi `so sánh 271 với Ben Cat` — câu này
   `plan.py` không trả lời được, chỉ vòng lặp mới làm được

**Mất `BI_SECRET_KEY` = mất key đã lưu**, phải nhập lại. Không thứ gì khác trong
database phụ thuộc vào nó.

**Thử trên giao diện** — bố cục *Hội thoại* hoặc *Sự cố* (`?l=chat` / `?l=incident`),
đăng nhập `truc`. Gõ vào ô dưới cùng:

| Gõ | Thấy gì |
|---|---|
| `271 đang thế nào?` | vệt tool `resolve → summary`, hai khối bằng chứng, một câu số liệu. Dòng «về device:D03.XCBR1» nói nó đã hiểu hỏi về đâu |
| `Lai Uyen thế nào?` | **hai nút** E01 / E02 — bấm một nút thì *cả màn hình* nhảy sang ngăn đó (không phải hỏi lại, vì câu hỏi vẫn nhập nhằng) |
| `trạng thái 999` | «Trạm này không có gì tên «999»» — **không** âm thầm trả lời về toàn trạm |
| bấm một ngăn trên sơ đồ rồi hỏi `còn số đo thì sao?` | câu không nêu tên → hiểu là hỏi về ngăn đang xem. Dòng «về …» dưới ô nhập nói trước điều đó |

Khi `BI_LLM=off` (mặc định) đầu ô ghi «Không có mô hình ngôn ngữ — câu trả lời là
số liệu đã tính». Đó là trạng thái đúng, không phải lỗi.

**Thử agent bằng curl** (không cần key, không cần mô hình):
```bash
curl -X POST http://127.0.0.1:8080/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"271 đang thế nào?"}'
```
→ `scope: device:D03.XCBR1`, `key: agent.answer.summary`, hai `EvidenceRecord`.
`POST /api/ask/stream` trả cùng nội dung theo 5 loại khung (`turn`, `tool`,
`evidence`, `token`, `answer`) — **đã chạy thật qua HTTP 2026-08-07**.

**Bật mô hình thật** (tuỳ chọn — mọi thứ trên chạy được khi không bật):
```bash
BI_LLM=openai BI_LLM_MODEL=<tên model> BI_LLM_API_KEY=<key> \
BI_LLM_BASE_URL=https://openrouter.ai/api/v1   # tại trạm: http://127.0.0.1:11434/v1 (Ollama)
```

> **Việc rẻ nhất và quyết định nhất hiện nay không phải viết code**: xin một dump
> của **trạm thứ hai** (Q4) và chạy `tools/probe_dataserver.py --dump` lên nó.
> Cả 6/6 template mới chỉ đo trên DEMO_SAS. Trạm thứ hai ra 12/12 thì ADR-0015 là
> chuyện quy mô; ra một nửa `UNKNOWN` thì nó là việc gấp và M1 phải nghĩ lại.

Trỏ vào DataServer → ra sơ đồ một sợi 13 ngăn / 80 thiết bị, **không vẽ tay,
không map point**. Mục tiêu M1 đã chứng minh được trên `DEMO_SAS`. Từ GĐ 1 sơ đồ
còn mang **số đo** (P/Q/U/I/f/nấc MBA, 79 điểm) và mỗi câu trả lời mang
**EvidenceRecord**.

**Chưa xem bằng mắt trên trình duyệt** kể từ GĐ 0. Cả GĐ 0 và GĐ 1 mới verify tới
mức build + typecheck + lint + 288 test + đối chiếu DataServer thật bằng script.

Chạy thử:
```bash
cd backend  && uv sync
cd frontend && npm install && npm run build
cd backend  && uv run uvicorn blackinterface.api.app:app --port 8080
```
→ mở `http://127.0.0.1:8080`

Hai kịch bản chạy tay, theo thứ tự:
1. `docs/40-testing/manual-test-01-topology.md` — sơ đồ + mang điện + realtime
2. `docs/40-testing/manual-test-02-measurement.md` — số đo + bằng chứng (GĐ 1)

**Đăng nhập** (ADR-0017). Lần chạy đầu tự tạo tài khoản, **mật khẩu
`blackinterface`** cho tất cả:

| Tài khoản | Vai | Thấy gì |
|---|---|---|
| `operator` | operator | sơ đồ, pane Bất thường (nhóm C). **Không** thấy `#/eng` |
| `supervisor` | supervisor | như trên + `control.sign` |
| `maintenance` | maintenance | như operator, không có control |
| `protection` | protection | sự kiện bảo vệ, `binding.read` |
| `admin` | admin | quản trị. **Không** thấy trạm |
| `engineer` | engineer | `#/eng` (Kết nối + độ phủ + cảnh báo model) + nút *Tải lại từ nguồn* |
| **`truc`** | operator+supervisor+maintenance | trạm ít người: một người kiêm nhiều việc |

**Workspace nhiều pane** (lô 0 phần hai, 2026-08-06). Header có ba nút bố cục:
*Giám sát · Hội thoại · Sự cố*. Đáng thử:

1. Đổi bố cục → **scope giữ nguyên**, chỉ query `?l=` đổi
2. Bấm một thiết bị trên sơ đồ → **mọi ô** đổi theo cùng lúc
3. Kéo giãn đường phân cách → F5 → cỡ giữ nguyên (nhớ riêng theo từng preset)
4. Gõ `?l=linhtinh` → im lặng về *Giám sát*, **không** redirect; còn scope sai
   thì vẫn bị redirect. Khác nhau có chủ ý
5. Bố cục *Hội thoại* → ô hỏi đáp thật (GĐ 2 bước 2). Chỉ còn ô *Gán điểm* là
   «Có ở giai đoạn sau»

Đáng thử tay nhất:
1. Chưa đăng nhập → mọi URL đều đưa về `#/login`, và link sâu được giữ để quay lại
2. `operator` gõ thẳng `#/eng` → bị đưa về sơ đồ; gọi thẳng API project → **403**
3. `engineer` → vào `#/eng`
4. Đăng xuất → phiên bị huỷ **ở máy chủ**, cookie cũ dán lại cũng vô dụng

Khởi động sẽ log cảnh báo liệt kê tài khoản còn dùng mật khẩu mặc định. Đổi bằng
`POST /api/password`.

**Bỏ qua đăng nhập khi phát triển** — `BI_AUTH=env`, danh tính lấy từ `BI_ROLE`:
```bash
BI_AUTH=env BI_ROLE=engineer uv run uvicorn blackinterface.api.app:app --port 8080
BI_AUTH=env BI_ROLE=operator,maintenance   # một người nhiều vai
BI_AUTH=env BI_ROLE=engineer,supervisor    # từ chối lúc khởi động, đúng thiết kế
```
**Không dùng ở trạm**: nó cấp cùng bộ quyền cho bất kỳ ai chạm tới cổng mạng.

---

## Đã xong

### Khảo sát (2026-08-04) — đo trực tiếp trên `DEMO_SAS` v654
- ✅ DataServer là **OPC UA client-server**, không phải PubSub Part 14
- ✅ Address space browse được: **17.965 node** dưới `/SAS`, NodeId ngữ nghĩa dạng chấm
- ✅ **Auto-bind 100%**: 80/80 thiết bị đóng cắt, 100% quality Good, 100% có timestamp
- ✅ **Suy loại ngăn 12/12 đúng** chỉ từ thành phần LN, không cần SLD
- ✅ Định danh EVN có sẵn trong `Name`/`SName` (`D03.XCBR1.Name = "271"`)
- ✅ Alarm dùng **interface riêng** `OAAlarm.GetActiveAlarm`, đã decode 243/243
- ✅ Subscription datachange hoạt động (200ms)
- ✅ Phát hiện lỗi trong extract SLD: sai số hiệu EVN, sót ngăn J01 22kV
- ✅ Phát hiện rủi ro bảo mật: endpoint None + Anonymous, `PosCtl` gọi được tự do
- 📄 `docs/30-integration/oneats-dataserver.md`

### Quyết định kiến trúc
- ✅ ADR-0001 Neutral Station Model là contract trung tâm
- ✅ ADR-0002 Topology suy từ DataServer, **SLD ra khỏi MVP**
- ✅ ADR-0003 Không làm canvas vẽ; template + view sinh tự động
- ✅ ADR-0004 Evidence là typed object do tool sinh
- ✅ ADR-0005 AI không nằm trên đường đi của tính đúng đắn
- ✅ ADR-0006 Stack triển khai local
- ✅ ADR-0007 Alarm dùng interface riêng

### Workspace
- ✅ `AGENTS.md` + adapter `CLAUDE.md`, `.cursor/rules/`
- ✅ Cấu trúc `docs/` (product / architecture / domain / integration / progress)
- ✅ Scaffold `backend/` theo 6 lớp, `tools/`, `frontend/` placeholder
- ✅ `tools/check.py`, `tools/probe_dataserver.py`, `tools/verify_dataserver.py`
- ✅ `uv sync` chạy được; `tools/check.py` **xanh toàn bộ**
  (layout · ranh giới lớp · read-only · docs dated · ruff · ruff format · mypy strict · pytest 11 passed)
- ✅ `tools/verify_dataserver.py` **xác nhận lại 100% sự thật đã đo** trên hệ live
- ✅ Đã kiểm chứng `check.py` thật sự bắt vi phạm: thêm file gọi `call_method("2:PosCtl")`
  → detect + exit 1; docstring ghi lệnh cấm thì không bị false positive

---

### Module #1 — Bay template + topology builder (2026-08-04) ✅

- ✅ ADR-0008 chốt schema template YAML
- ✅ 6 template: `domain/templates/T1..T6.yaml`
- ✅ `domain/bay_types.py` — suy loại ngăn, **13/13 đúng**
- ✅ `domain/topology.py` — áp template → graph, thuần, không I/O
- ✅ `integration/opcua/discovery.py` — browse live, **~1 s**
- ✅ `integration/dump.py` — đọc fixture, chạy offline
- ✅ `diagram/layout.py` — graph → toạ độ, deterministic
- ✅ `api/app.py` — Domain API, mọi endpoint không-GET chỉ ghi SQLite local,
     không bao giờ ghi OneATS (allowlist khoá trong `test_no_write_endpoint_exists`)
- ✅ `frontend/dev/index.html` — viewer SVG 1 file, không cần Node
- ✅ **96 test offline + 2 test live**, tất cả xanh
- ✅ Fixture `backend/tests/fixtures/sas_tree.json` (617 node, có meta pin ModelVersion)
- 📄 `docs/40-testing/manual-test-01-topology.md`

**Kết quả đo được (fixture = live, đã đối chiếu):**

| Chỉ số | Giá trị |
|---|---|
| Ngăn dựng được | 13/13, **0 ngăn UNKNOWN** |
| Thiết bị đóng cắt đặt vào graph | **80/80** — khớp lần đo độc lập |
| Thiết bị bị bỏ sót (`slot_unmapped`) | **0** |
| Lỗi (severity ERROR) | **0** |
| Cảnh báo | 1 — thanh cái 22kV không có trong DataServer (đúng, đã báo lên UI) |
| Thời gian dựng model | 0.015 s (fixture) · ~1 s (live) |

**Phát hiện mới trong phiên này** (đã ghi vào `docs/20-domain/bay-templates.md`):
- Thanh cái thật nằm ở `/SAS/Subs/BB11..BB29`, có `IsLive`/`Hz`/`PPV*`.
  `DBB`/`EBB` **không phải** thanh cái mà là bảo vệ so lệch → đính chính bản nháp cũ.
- `IsLive` có sẵn ở **cả cấp thanh cái lẫn cấp ngăn**, cộng `SAS_SIM.CheckLiveState`
  → ảnh hưởng trực tiếp tới module #2 (câu hỏi Q3).
- `BB29.IsLive` và `D12.IsLive` trả `BadWaitingForInitialData` → có sẵn ca thật
  để kiểm chứng invariant I2.

### Khung dự án (2026-08-04) ✅

Trước module #1 chỉ có một **lát cắt dọc**: chạy được từ OPC UA tới màn hình,
nhưng chưa có lưu trữ, cấu hình, log, xử lý lỗi, frontend thật, version control.
Phiên này bổ sung đúng những thứ **mọi module còn lại đều đụng vào**.

- ✅ **Git** — khởi tạo, commit đầu tiên gom toàn bộ hiện trạng (84 file)
- ✅ **ADR-0009** — frontend là Vite + Vue 3 + TS, thay phần frontend của ADR-0006
- ✅ `config.py` — mọi setting `BI_*` một chỗ; không nơi nào khác đọc `os.environ`
- ✅ `errors.py` + `api/errors.py` — bộ lỗi đóng, một hình dạng JSON duy nhất
- ✅ `logs.py` — structlog, người đọc được khi dev, JSON ở trạm
- ✅ `store/` — SQLite WAL, migration tiến-một-chiều, repository đầu tiên
- ✅ **Frontend thật** — routing, Pinia, component sơ đồ tách riêng, 3 view
- ✅ **Hợp đồng API cưỡng chế bằng máy**: FastAPI → `openapi.json` →
      `schema.d.ts`. Đổi field mà quên xuất → `check.py` đỏ
- ✅ Xoá `frontend/dev/index.html` (282 dòng) — không để tồn tại hai frontend
- ✅ `tools/check.py` giờ gác 7 mục, gồm cả frontend và hợp đồng API

**Chưa làm, cố ý**: `agent/`, đóng gói Inno Setup, `EvidenceRecord`.
Thiết kế chúng trước khi viết module tương ứng là đoán — đúng cái sai lầm mà
ba phát hiện của phiên trước (`get_children()` trùng, DBB/EBB, vị trí thanh cái)
đã chứng minh.

**Chưa kiểm chứng**: giao diện mới mới verify ở mức build + serve + typecheck,
**chưa xem bằng mắt trên trình duyệt**. Cần chạy `docs/40-testing/manual-test-01-topology.md`.

---

### Project + kết nối DataServer từ UI (2026-08-05) ✅

Luồng mới: mở Black Interface → **Project** → nhập tên + `opc.tcp://…` →
Kết nối → sơ đồ dựng từ nguồn đó. Kết nối thành công lưu **snapshot**
(StationObs JSON trong SQLite): mở lại project là vẽ ngay, offline được;
«Tải lại từ nguồn» mới đọc live. Khởi động lại process tự mở project gần nhất
từ snapshot (`StationStore.startup()`).

- ✅ Migration `002_projects.sql` — `projects` + `project_snapshots` (FK cascade)
- ✅ `store/projects.py` — `ProjectRepository`, store chỉ nói SQL, không biết domain
- ✅ `api/source.py` — `StationStore` theo project: `open_project` (snapshot) /
     `refresh_project` (live + thay snapshot) / fallback `BI_SOURCE` khi không có project
- ✅ `api/app.py` — `GET/POST /api/projects`, `/open`, `/refresh`, `DELETE`;
     lỗi kết nối trả trong body (`ok=false`), project giữ lại để sửa URL thử lại
- ✅ **Bỏ hardcode `SAS_PATH`**: `_find_station_root()` trong `discovery.py` —
     thử path DEMO trước (nhanh), không có thì BFS tìm node có con dạng `\d+kV`.
     Trạm mới trong DataServer giờ tìm được bất kể tên project trong cây
- ✅ Frontend: view `ProjectsView` (tạo/nhập URL/kết nối/mở/tải lại/xoá),
     nav «Project», lỗi `model_not_loaded` dẫn thẳng tới trang project
- ✅ 2 lỗi mới trong bộ đóng: `invalid_input` (400), `conflict` (409)
- ✅ 141 test offline (17 test mới: repository, luồng API project, reopen từ
     snapshot qua "restart", auto-dò root trên cây giả), check.py xanh cả 7 mục
- ⚠ Chưa kiểm chứng trên trạm thật thứ 2 (Q4): auto-dò root mới test bằng cây giả;
     `tools/probe_dataserver.py`/`verify_dataserver.py` vẫn hardcode path DEMO
- ⚠ Chưa có manual test cho luồng project (bổ sung vào `docs/40-testing/` khi chạy tay)

---

## KẾ HOẠCH ĐÃ CHỐT (2026-08-05) — đọc mục này trước

Phiên thiết kế 2026-08-05 đã đọc `document/@Station_UseCases 1.xlsx` (30 use case,
6 module) và chốt lại toàn bộ hướng đi. **Kế hoạch dưới đây thay thế mục "Việc kế
tiếp" cũ** (giữ nguyên bên dưới để tra lịch sử).

### Điều quan trọng nhất nhận ra

Thứ đã dựng xong 3 phiên qua (topology → SLD → energization → realtime) **không
phải sản phẩm, nó là nền móng**. Trong 30 use case, **không có use case nào là
"vẽ SLD"** — cả bảng là *câu hỏi → trả lời có bằng chứng*. Có hai luồng:

| | Luồng 1 (xong) | Luồng 2 (chưa) |
|---|---|---|
| Là gì | endpoint → nối → dựng lại SLD + trạng thái | hỏi tiếng Việt → trả lời có evidence |
| Ai chạy | deterministic, không LLM | LLM chọn tool + diễn đạt |
| Sống độc lập? | **có** | không — cần luồng 1 làm nền |

Và cột `Expected Result` của file use case là **cấu trúc dữ liệu** (`CB, DS, ES,
MW, MVAR`), không phải câu văn → chính tác giả nghiệp vụ đã tự tách đúng theo I3/I4.

### 5 ADR mới

| ADR | Nội dung | Ảnh hưởng |
|---|---|---|
| [0010](../10-architecture/adr/0010-scope-and-facet.md) | `scope × facet` là trục địa chỉ hoá | → invariant **I8** mới |
| [0011](../10-architecture/adr/0011-single-gated-write-path.md) | một đường ghi qua `control/`, registry rỗng; agent không có tool ghi | → **I1 viết lại** |
| [0012](../10-architecture/adr/0012-stream-cadences.md) | tách nhịp `state`/`measurement`/`alarm` trên một stream | chặn module A |
| [0013](../10-architecture/adr/0013-evidence-envelope.md) | evidence envelope trên mọi facet, làm NGAY | chặn A, B |
| [0014](../10-architecture/adr/0014-frontend-workspace.md) | shadcn-vue, workspace nhiều pane, nhiều hội thoại, i18n | chặn toàn bộ frontend |
| [0015](../10-architecture/adr/0015-engineer-authored-templates.md) | **thêm 2026-08-06** — template do engineer soạn, có phiên bản, phải chứng minh trước khi dùng | chặn GĐ 2.5; làm sống lại «chốt bản»; nâng **Q4** lên chặn |
| [0016](../10-architecture/adr/0016-roles-and-capabilities.md) | **thêm 2026-08-06** — vai và quyền: quyền là đơn vị, vai chỉ là gói; kiểm ở tầng facet; agent mượn quyền người hỏi | chạm **mọi** route, agent, evidence, giao diện → phải cắm chỗ ngay ở GĐ 1.5; **đổi cửa vào mặc định** từ SLD sang tóm tắt AI |
| [0018](../10-architecture/adr/0018-conversation-first-workspace.md) | **thêm 2026-08-07** — hội thoại là bố cục, không phải một chế độ: bỏ ba preset, còn một bố cục (chat thường trực + sơ đồ trên + tab dưới) | thay **ADR-0014 §3 phần preset**; thi công ở **đầu GĐ 2**, sau khi `ChatPane` chạy thật |
| [0019](../10-architecture/adr/0019-agent-shape.md) | **thêm 2026-08-07** — agent: lập kế hoạch (deterministic) → đọc → diễn đạt; `LLMProvider` tự viết, mặc định không mô hình; registry tool chỉ-đọc gác bằng `ast` | **thay dòng «Agent = Pydantic AI»** ở `AGENTS.md` §3; chốt hợp đồng cho `ChatPane` |

### Thứ tự thi công

| GĐ | Nội dung | Đổi tính năng? |
|---|---|---|
| **0** ✅ | **Nền**: `domain/scope.py` + `domain/evidence.py` · tách `api/app.py` (651 dòng) thành routers + schemas · tách `api/source.py` (3 trách nhiệm) · shadcn-vue + Tailwind + i18n · tách store theo vòng đời · scope vào URL · `control/` rỗng + đổi luật `check.py` | **không** — 197 test hiện có phải vẫn xanh, đó là thước đo |
| **1** ✅ | **Module A** (Monitoring): `domain/measurement.py`, đọc `MMXU1`/`YLTC.TapPos`/`Subs.BB*.PPVmax,Hz`, tách nhịp SSE, `/api/summary` + evidence đầu tiên | có |
| **1.5** | **Nền UI/UX** (chèn 2026-08-06 theo yêu cầu người dùng): thi công phần workspace của ADR-0014 còn nợ — `app/layout/` + `PaneHost` + `presets.ts`, `Pane`/`Layout` vào `stores/workspace.ts`, bố cục vào URL, đủ 10 component `ui/`, bốn trạng thái mỗi pane, tách bề mặt engineer khỏi operator, **chuyển nhóm C issue sang bề mặt vận hành**. Hợp đồng: [`docs/20-ui/frontend-architecture.md`](../20-ui/frontend-architecture.md) · Màn hình: [`docs/20-ui/screens.md`](../20-ui/screens.md) | backend đổi **đúng một chỗ**: issue trả kèm nhóm A/B/C |
| **2** | **Agent lát cắt dọc, MỎNG** — chỉ 2 tool (`resolve` + `summary`). Session memory, streaming, `LLMProvider`, evidence chạy thật đầu-cuối | có |
| **2.5** | **Trình soạn template + chốt bản** ([ADR-0015](../10-architecture/adr/0015-engineer-authored-templates.md)): template vào store thay vì package · chọn theo chữ ký thay `infer_bay_type()` · trình soạn **đồ thị** (không phải canvas vẽ) · cổng chứng minh đối chiếu `IsLive` · bảng `releases` pin cả `ModelVersion` lẫn phiên bản template | có |
| **3** | **Module B** (Alarm/Event): event store + alarm + notification | có |
| **4** | **Module E** (Report) · **Module F** (Knowledge/RAG — độc lập, làm song song được) | có |
| **5** | **Module D** (Trend — chờ HIS) · **Module C** (Control — mở `control/registry.py`) | có |

**Vì sao chèn GĐ 1.5 ngay trước GĐ 2** (người dùng nêu 2026-08-06): ADR-0014 đã
chốt workspace nhiều pane từ 2026-08-05 nhưng **chưa thi công một dòng nào** —
`stores/workspace.ts` mới giữ scope, không có `Pane`/`Layout`/preset/`PaneHost`,
frontend vẫn là 4 view cố định theo route. Mà **chat LÀ một pane**: có `PaneHost`
sẵn thì GĐ 2 chỉ thêm 1 component; chưa có thì chat thành view cố định thứ 5, rồi
alarm thành thứ 6, và lúc đó đập lại tốn gấp nhiều lần. Toàn bộ frontend hiện mới
**1.314 dòng** — đây là lúc rẻ nhất.

**Vì sao agent ở GĐ 2 chứ không phải cuối**: kiến trúc agent (bộ nhớ hội thoại,
streaming, hợp đồng tool, evidence) là chỗ rủi ro cao nhất và chưa ai kiểm chứng.
Dựng mỏng lúc mới có 2 tool thì sai còn sửa được; phát hiện sai sau khi có 7 tool
là đập lại tất cả.

### Mô hình dữ liệu còn thiếu (đo từ file use case, có đích danh point)

| Cần | Point | Use case |
|---|---|---|
| ✅ Điện áp thanh cái | `Subs.BBxx.PPVmax` — **chú ý chữ m thường**, file use case ghi sai | A-01 |
| ✅ Tần số | `Subs.BBxx.Hz` + `BAYx.MMXU1.Hz` | A-01 |
| ✅ P / Q / U / I / PF | `BAYx.MMXU1.totW / totVAr / Vlin / Amax / totPF` | A-01, A-02 |
| ✅ Nấc MBA | `ATx.YLTC.TapPos` | A-01 |
| Tagging | `BAYx.XCBR1.Tagging` | A-02, C-08 |
| Alarm severity ≥ 800 + category | CRITICAL / PROTECTION / ANALOG / COMMUNICATION / OTHER | A-01, A-02, A-04 |

### Hai chỗ nhặt được, PHẢI KIỂM CHỨNG trước khi dùng (§5.4)

- **Q6 có thể có lời giải**: sheet A02 map `ES14→XSWI11`, `ES24→XSWI21`,
  `ES75→XSWI71`, `ES76→XSWI72` — tiếp địa bám số của dao cách ly cạnh nó.
  Đây là **tài liệu**, chưa phải **đo được**. Phải xác minh trên DataServer.
- **Tên chỉ danh lấy từ `Description`**, không phải `Name`/`SName` như đang dùng.

### Câu hỏi còn treo

- **Trend (D) lấy lịch sử từ đâu?** OneATS HIS đã đo được là **chưa chạy** (48010
  là `sunshine`). Người dùng chốt: *gác lại*, làm module use case trước.
- **A-06 Auxiliary** (AC/DC, UPS, battery) không thuộc ngăn nào → bộ scope chưa
  có chỗ. Không phải MVP, hoãn được, nhưng nếu có nhiều thiết bị "ngoài ngăn"
  thì bộ danh từ phải rộng ra sớm.

---

## GĐ 0 — Nền (2026-08-05) ✅

Thước đo đặt ra: **không đổi tính năng, 197 test cũ vẫn xanh**. Kết quả:
**247 test xanh** (197 cũ + 50 mới), `tools/check.py` xanh cả 7 mục, và
`backend/openapi.json` **không đổi một byte** — `git diff` rỗng. Đó là bằng
chứng mạnh nhất rằng việc tách `api/` là thuần tuý cấu trúc.

### Backend

| Việc | Kết quả |
|---|---|
| `domain/scope.py` | `ScopeRef` + `parse/format` + `parent/contains` + `exists/bays_in`. **Từ chối chứ không nới rộng**: scope sai → `InvalidInputError`, không bao giờ âm thầm thành `station`. 24 test |
| `domain/evidence.py` | `EvidenceRecord`/`Coverage`/`PointQ`/`Limit` + **`EvidenceBuilder`** |
| `control/` | `registry.COMMANDS = {}` · `guard.py` · `audit.py`. 12 test |
| `tools/check.py` | luật I1 đổi hình: cấm gọi ghi **ngoài `control/`**, `COMMANDS` rỗng (parse bằng `ast`), `agent/` cấm import `control/`. Thêm mục **so ngữ pháp scope giữa `scope.py` và `scope.ts`** |
| `api/app.py` 651 → **86 dòng** | tách thành `deps.py` · `schemas.py` · `mappers.py` · `routers/{health,projects,station,live,diagram}.py` |
| `api/source.py` 409 → **~280 dòng** | tách `broadcast.py` (revision + listener) · `reader.py` (đọc nguồn) · `watch.py` (vòng đời subscription). `StationStore` giờ chỉ trả lời "model nào đang hiện hành và đổi lúc nào" |

**Hai quyết định đáng ghi lại:**

1. **`limits` do builder suy ra, không do facet nhớ.** ADR-0013 bắt buộc `limits`
   trong 5 tình huống. Để mỗi facet tự nhớ thì luật chỉ đúng tới facet đầu tiên
   viết vội. Nên facet chỉ khai báo **sự kiện** (`point()` / `missing()` /
   `note()`), builder suy ra `points_missing` / `quality_not_good` /
   `data_stale` / `from_snapshot`. Facet thêm được cảnh báo, **không bỏ được**.
2. **`limits` và `refusal` là CODE, không phải câu chữ.** ADR-0013 ví dụ bằng
   câu tiếng Việt, nhưng frontend đã có i18n (ADR-0014) và agent trả lời theo
   ngôn ngữ người hỏi — prose nướng vào backend sẽ sai ở cả hai. Cùng lý do với
   `reason` code trong `energization.py`. Nhãn nằm ở `frontend/src/i18n/`.

**`guard.py` mặc định là TỪ CHỐI.** Chưa mô hình hoá interlock/tagging/authority
thì trả `NOT_EVALUABLE`, không im lặng. Một câu hỏi chưa hỏi không được phép đọc
thành một câu hỏi đã thông qua — đây là I2 áp cho *hành động* thay vì cho *câu nói*.

**Đã kiểm chứng luật mới thật sự bắt vi phạm** (như đã làm với luật cũ):
thêm `node.PosCtl(1)` vào `api/` → đỏ; thêm 1 lệnh vào `COMMANDS` → đỏ;
thêm `'feeder'` vào `SCOPE_KINDS` của TS → đỏ. Khôi phục → xanh.

### Frontend

| Việc | Kết quả |
|---|---|
| Stack | Tailwind **v4** (cấu hình bằng CSS `@theme`, **không** có file JS config) + `@tailwindcss/vite` + `components.json` + `lib/utils.ts` + reka-ui + lucide + vue-i18n 11 |
| **Sửa lỗi màu** | hai bảng màu tách bạch: `st-*` (trạm) và `sys-*` (phần mềm). `sys-*` **không dùng đỏ/xanh lá** |
| i18n | `vi` mặc định + `en`, lưu lựa chọn ở localStorage, có nút đổi trên header. **Mọi** chuỗi hiển thị đã chuyển sang catalogue, kể cả nhãn của `state`/`liveState`/`reason` (trước nằm cứng trong `state.ts`) |
| scope vào URL | `#/ops/bay:D03` là địa chỉ chính. `router.beforeEach` **redirect** scope sai thay vì âm thầm rơi về `station` |
| Store theo vòng đời | `station.ts` (god store) → `structure.ts` · `live.ts` · `workspace.ts` (+ `projects.ts` sẵn có) |
| `ui/` | `StatusDot.vue` · `Panel.vue` · `Badge.vue` |

**Lỗi an toàn đã sửa (đây là thứ đáng giá nhất của phần frontend).** Header cũ tô
"mất kết nối" bằng `--closed` (đỏ) và "trực tuyến" bằng `--open` (xanh lá) —
**đúng hai màu** đang mang nghĩa "máy cắt đóng" và "dao mở" trên sơ đồ cách đó
vài centimet. Đỏ khi đó vừa là trạng thái vận hành bình thường vừa là sự cố của
chính phần mềm. Giờ: `sys-ok` trung tính (trực tuyến **không** phải phát biểu an
toàn, nên không được mượn màu của một phát biểu an toàn), `sys-warn` hổ phách,
`sys-down` hồng. Ghi vào bảng bẫy §7 của `AGENTS.md`.

**`StationView` không còn state chọn cục bộ.** Trước đây `selectedBay`/
`selectedDevice` là ref, phải xoá tay ở ba chỗ, không link được, refresh là mất.
Giờ chỉ có `workspace.scope` = URL.

**Chưa xem bằng mắt trên trình duyệt.** Mới verify tới mức build + typecheck +
lint + 247 test. Giao diện đổi nhiều (Tailwind, hai bảng màu, i18n, route mới)
→ **phải chạy tay `docs/40-testing/manual-test-01-topology.md`** trước khi làm GĐ 1.

### Nợ lại từ GĐ 0, cố ý

- **`EvidenceBlock.vue` chưa làm.** Chưa endpoint nào trả `EvidenceRecord` nên
  `schema.d.ts` chưa có kiểu đó — dựng component theo phỏng đoán là đúng cái sai
  lầm mà repo này đã tránh nhiều lần. Làm ở GĐ 1 cùng facet đầu tiên.
- **`api/*.py` chưa gắn evidence.** ADR-0013 nói mọi facet phải có; hiện chưa có
  facet nào theo nghĩa đó (`/api/station`, `/api/bays` là bản đồ/cấu trúc).
  `/api/energization` là ứng viên đầu tiên, gắn ở GĐ 1.
- **Alias `--bg`/`--closed`… trong `styles.css`** vẫn còn cho các component
  chưa viết lại. Mỗi lần viết lại một view thì bớt dần; **không cái mới nào
  được dùng**.

*(Hai món đầu đã trả xong ở GĐ 1 — xem dưới.)*

---

## GĐ 1 — Module A (Monitoring) (2026-08-06) ✅

**288 test xanh** (247 → 288), `tools/check.py` xanh cả 7 mục.

### Đo trước, viết sau

Việc đầu tiên không phải là code mà là **mở DataServer ra đo**, vì file use case
và ADR-0012 đều chép point từ tài liệu chứ chưa ai kiểm. Ba thứ nhặt được:

1. **`PPVmax`, không phải `PPVMax`.** Sai case là không bind được.
2. **Không có `EngineeringUnits` trên bất kỳ measurand nào.** → quyết định thiết
   kế lớn nhất của giai đoạn, xem dưới.
3. **`/SAS/AT1/YLTC` có 5 Method điều khiển bộ đổi nấc** (`TapChg`, `MasCtl`,
   `EmerCtl`, `ParCtl`, `ResetCtl`) nằm ngay cạnh `TapPos` mà ta đọc. Đã thêm cả
   5 vào `FORBIDDEN_CALLS` của `check.py` (I1).

Fixture `sas_tree.json` dump lại từ DataServer thật: **thuần thêm** 80 node, không
xoá node nào, không NodeId nào đổi, vẫn `DEMO_SAS v654`.

### Backend

| Việc | Kết quả |
|---|---|
| `domain/measurement.py` | danh mục measurand + `Reading` + `MeasurementSet` + deadband. Thuần |
| `domain/observation.py` | tách hai họ: `state_points`/`apply_state_samples` và `measurement_points`/`apply_measurement_samples` |
| `domain/scope.py` | thêm `ScopeKind.TRANSFORMER` — `TapPos` phải có chủ thể thật, không mượn `device:` |
| `api/broadcast.py` | `Cadence` + `Listener` giữ **một chỗ cho mỗi nhịp** |
| `api/throttle.py` | giảm nhịp `measurement`, **có sườn xuống** |
| `api/summary.py` + `routers/summary.py` | facet đầu tiên mang `EvidenceRecord` |
| `LiveOut` | tách thành `StateOut` / `MeasurementOut` / `LinkOut`; SSE có 3 loại sự kiện |

### Ba quyết định thiết kế

**1. Không in đơn vị nào chưa đo được thang.** DataServer không công bố đơn vị,
nên biết `Vlin` là điện áp nhưng không biết 221.08 là V hay kV. In "221.08 V"
cạnh thanh cái 220 kV còn tệ hơn không in gì. Số nào chưa chắc thang thì hiện
**số trần + tên đại lượng**, và bằng chứng mang `LimitCode.UNIT_UNVERIFIED`.
`Hz`, hệ số công suất, nấc MBA được miễn vì không thể sai thang. → **Q7**.

**2. Deadband theo từng đại lượng, không phải một số toàn cục.** 0,5 % của 50 Hz
là 0,25 Hz — dao động rất lớn; 0,5 % của phụ tải là nhiễu. ADR-0012 nói một biến
môi trường là đủ; khi làm thì thấy không đúng, biến đó giờ chỉ là **đặt đè**.
**Nấc MBA không deadband** vì nó rời rạc như vị trí dao — làm mượt là giấu mất
thao tác đổi nấc.

**3. Throttle phải có sườn xuống.** Chặn hết trong cửa sổ thì số đo *cuối* của
một chùm không bao giờ tới, và client đứng ở một số cũ mà không có gì báo là cũ.

### Kiểm chứng trên DataServer thật (không phải fixture)

Duyệt live: 13 ngăn, 6 thanh cái, 1 MBA, **97 điểm state + 79 điểm số đo**, khớp
từng con số với đường fixture. Mở subscription 20 s: **176 monitored item,
`rejected=0`**, nhận được 1 nhịp `link`, 1 nhịp `state`, **4 nhịp `measurement`**,
và `structure_revision` **không đổi** — DEMO_SAS sinh số đo ngẫu nhiên liên tục mà
đồ thị điện không dựng lại lần nào. Đó là ADR-0012 luật 1 chạy trên dữ liệu thật.

### Frontend

`stores/stream.ts` giữ EventSource **duy nhất** và phân nhánh theo `event.type` —
đúng thứ ADR-0012 luật 3 yêu cầu, và tách hẳn "sở hữu socket" khỏi "giữ dữ liệu".
`stores/live.ts` chỉ còn nhịp `state`; `stores/measurements.ts` là nhịp
`measurement`; `stores/summary.ts` bám theo scope trên URL.

`ui/EvidenceBlock.vue` — món nợ GĐ 0 đã trả. Nó đặt **cảnh báo lên trước** xuất
xứ, vì một câu trả lời có khiếm khuyết và một câu trả lời sạch trông y hệt nhau
nếu không có gì bắt phải khác. Bảng màu **hệ thống**, không mượn đỏ/xanh lá của
trạm. `components/panels/MeasurementPanel.vue` hiện số đo và **nói rõ có áp
deadband** (ADR-0012 hệ quả 3).

### Một lỗi thiết kế bắt được khi chạy thật

Chạy app lên rồi gọi `/api/summary?scope=station` thì thấy **89/159 điểm bị gắn
«dữ liệu cũ»** trên một trạm hoàn toàn khoẻ mạnh. Nguyên nhân: `SourceTimestamp`
của OPC UA nói lúc giá trị **được sinh ra**, nên một dao cách ly không nhúc nhích
suốt một ngày mang timestamp một ngày tuổi — mà vẫn là hiện tại.

Một cảnh báo luôn bật là cảnh báo vô nghĩa: nó dạy người vận hành bỏ qua khối
bằng chứng, đúng thứ khối đó sinh ra để chống. Đã sửa: `EvidenceBuilder.point()`
nhận `expect_refresh`, chỉ điểm **được kỳ vọng cập nhật liên tục** (số đo) mới bị
xét cũ; vị trí đóng cắt thì không. `age_ms` vẫn báo cho mọi điểm — tuổi vẫn đáng
xem, chỉ là không phải lỗi.

Còn nợ: trường hợp **RTU chết sau lưng DataServer** (link xanh nhưng một điểm
ngừng cập nhật) giờ không phát hiện được nữa. Cần "chu kỳ cập nhật kỳ vọng" theo
từng điểm, mà ta chưa đo được — đừng đoán.

### Nợ lại từ GĐ 1, cố ý

- **`/api/energization` vẫn chưa mang evidence.** GĐ 0 hẹn gắn ở đây, nhưng khi
  làm thì thấy `summary` là chỗ đúng hơn: nó là *phán quyết về một scope*, còn
  `/api/energization` là bản đồ toàn trạm. Facet nào sinh sau cứ theo khuôn
  `api/summary.py`.
- **Giá trị theo pha chưa đọc** (`AphsA/B/C`, `WphsA/B/C`, …). `MMXU1` có 26 con,
  ta lấy 6. Chưa có use case cho từng pha — thêm khi có, đừng thêm trước.
- **`MSQI1` (thành phần đối xứng) chưa đọc.** Cùng lý do.
- **`Tagging` chưa đọc** dù use case A-02/C-08 cần. Thuộc Module B/C.
- **Kịch bản chạy tay**: `docs/40-testing/manual-test-02-measurement.md`.
- **Số đo chưa lên sơ đồ**, mới ở panel bên phải. Vẽ nhãn lên SLD là việc của
  diagram engine, không phải của giai đoạn này.

---

## Việc kế tiếp — BẢN CŨ (trước 2026-08-05, giữ để tra lịch sử)

### 0. Xem lại giao diện mới bằng mắt — ✅ **ĐÃ CHẠY TAY 2026-08-05**
Người dùng xác nhận: **energization và realtime chạy đúng trên trình duyệt**,
"về cơ bản khá ổn". Đổi trạng thái ở FEP → màn hình đổi theo, không cần bấm gì.
Còn tồn đọng là **UI/UX**, người dùng sẽ nêu cụ thể ở phiên tiếp → gom vào việc
#5 (diagram engine), đừng tự đoán rồi sửa trước.

Kịch bản `docs/40-testing/manual-test-01-topology.md` vẫn là chuẩn để chạy lại
sau mỗi thay đổi hình học. Trọng tâm TC-03: **hai thanh cái phải tách bạch được
bằng mắt** (làn riêng + chấm nối), và cả trạm nằm trong **một hình**, 220kV lật
ngược ở trên.

**Còn thiếu so với bản Grid Designer** (bảng so sánh):
- [ ] Giá trị đo trên đầu mỗi ngăn (kV/kA/MW/MVar) — nguồn `MMXU1`, chưa vào model
- [ ] Hz/kV cạnh mỗi thanh cái — nguồn `Subs.BB*`, đã browse được, chưa vào model
- [x] ~~Ký hiệu MBA AT1 nối 220↔110~~ — **ĐÍNH CHÍNH 2026-08-05**: bằng chứng
      ghép ngăn CÓ trong DataServer (`BAY/Name` = "AT1 Incoming" ở cả D01 lẫn
      E07 + nhóm `/SAS/AT1` mang `YPTR`/`YLTC`). Đã vẽ, xem phiên 2026-08-05
- [x] ~~Tên ngăn dạng chữ ("Ben Cat", "Hoc Mon")~~ — **ĐÍNH CHÍNH 2026-08-05**:
      DataServer CÓ mang, ở `<bay>/BAY/Name`. Đã vào model và hiển thị

### 1. ~~Energization solver~~ ✅ **XONG 2026-08-05** — xem mục riêng bên dưới

### 2. ~~Realtime (subscription + SSE)~~ ✅ **XONG 2026-08-05** — xem mục riêng bên dưới

### 3. Event store + SOE ← **BẮT ĐẦU TỪ ĐÂY**
Không có cái này thì mục tiêu M2 không tồn tại.
- [ ] Schema SQLite cho event (dedupe theo `event_id`, retention, ack state)
- [ ] Poll/subscribe `GetActiveAlarm` → ghi store
- [ ] Query SOE theo cửa sổ thời gian, độ phân giải ms

### 4. Evidence + snapshot/release
- [ ] `EvidenceRecord` + `Coverage` + `PointQ` (ADR-0004)
- [ ] Catalog snapshot + release hash + pin `ModelVersion` (I7)
      *(fixture đã có meta `ModelName`/`ModelVersion` — dùng làm nền)*
- [ ] Phát hiện drift: NodeId không resolve được → nổi lên UI, cấm im lặng

### 5. Diagram engine — hoàn thiện
- [ ] **UI/UX người dùng sẽ nêu ở phiên tới** — chưa ghi được vì chưa nghe.
      Ghi nguyên văn góp ý vào đây khi nhận, đừng diễn giải lại.
- [ ] Sparse patch layer cho override của engineer
- [ ] Bố cục ngăn nối thanh cái (D17/E05) chưa chuẩn thẩm mỹ SLD
- [ ] Export SVG tĩnh

### 6. BlackCore + Frontend Nuxt
- [ ] Pydantic AI agent, tool registry (**không có write tool**)
- [ ] `LLMProvider` interface (OpenRouter dev → Ollama trạm)
- [ ] Nuxt: chat shell, bay-card review, evidence panel
      *(tham chiếu hành vi: `frontend/dev/index.html`)*

---

### Diagram v2 theo góp ý người dùng (2026-08-05) ✅

Người dùng đối chiếu với bản vẽ OneATS (`document/DEMO_SLD.pdf`) và nêu 3 điểm.

1. **MBA nối 220↔110 — đã vẽ, có bằng chứng.** Phát hiện mới đo được
   (2026-08-05, fixture + cấu trúc live):
   - `/SAS/220kV/D01/BAY/Name` = `/SAS/110kV/E07/BAY/Name` = `"AT1 Incoming"`
   - `/SAS/AT1` là nhóm ngang cấp điện áp, mang `YPTR` (MBA) + `YLTC` (OLTC)
   → luật ghép: nhóm MBA + id xuất hiện trong tên ngăn ở ≥2 cấp điện áp.
   Không đủ bằng chứng → `transformer_unpaired` warning, vẽ cuộn dây rời như cũ.
   - `domain`: `Transformer` + `pair_transformers()`; importers đọc nhóm AT*
   - `diagram`: ký hiệu 2 vòng tròn trong khe giữa 2 band, link chạy làn riêng
     cạnh ngăn, cắt ngang thanh cái **không chấm** = không nối (I3 giữ nguyên)
2. **Tên ngăn dạng chữ** — `BAY/Name` vào `Bay.name`: "Ben Cat", "Hoc Mon",
   "Lai Uyen" hiện dưới mã ngăn, đúng như bản vẽ Grid Designer.
3. **DS vs ES + giãn khoảng** — ES: thoi nhỏ hơn (6px vs 10px), gạch tiếp địa
   to và xa thân hơn; `SIDE_OFFSET` 54→68; bỏ chữ loại ngăn thừa ở caption.
4. **Thu phóng** — SVG thành camera: lăn chuột zoom quanh con trỏ, kéo để pan,
   nút «Vừa màn hình» (phím `f`), tab cấp điện áp = focus camera vào band.
   Toạ độ vẫn 100% từ backend; frontend chỉ đổi viewBox.

147 test offline (6 test mới khoá pairing + hình học link), check.py xanh cả 7 mục.
**Chưa xem bằng mắt trên trình duyệt** — việc #0 vẫn đứng.

### Diagram v2.1 — cuộn thứ ba 22kV của AT1 (2026-08-05) ✅

Người dùng hỏi: "còn 22kV thì sao, BB41 (suy ra) theo SLD phải nối vào AT1".
Đo lại fixture → tìm được **nguồn bằng chứng thứ hai** (BAY/Name của J01 rỗng
nên luật cũ không bắt được):

- **Số hiệu máy cắt theo quy ước EVN (TT 44/2014/TT-BCT)**: ngăn MBA có số
  `<mã cấp điện áp>3<số thứ tự MBA>` → AT1 sở hữu **231** (220kV), **131**
  (110kV), **431** (22kV). Trong fixture chỉ đúng 3 ngăn này khớp `^\d31$`;
  đường dây là x71/x72, liên lạc 112/212 — không đụng.
- `pair_transformers()`: match theo `BAY/Name` **hoặc** số máy cắt; id MBA
  không có đúng 1 chữ số cuối → không sinh luật số (thà không ghép còn hơn
  ghép sai). AT1 giờ ghép `(D01, E07, J01)` — 3 cấp điện áp.
- `layout` — qua 3 vòng góp ý cùng ngày, chốt ở **band 22kV nằm giữa**:
  `_band_order()`: cấp điện áp mà *mọi* ngăn vẽ được đều là cuộn ≥3 của MBA
  thì được nhấc lên ngay dưới band cao áp của MBA đó và **lật ngược**
  (terminal chĩa lên MBA, BB41 suy ra chìm xuống đáy band) — đúng bố cục dải
  giữa của tờ Grid Designer. Cấp 22kV có xuất tuyến thật thì giữ nguyên vị trí
  → khi đó link dùng tuyến dự phòng `_free_lane` (đường dọc nửa-bước-cột,
  giữa 2 cột luôn trống vì fitting rộng nhất vươn ±96 < ±105). Link ngắn:
  terminal → làn cạnh ngăn → hành lang `TX_DROP=52` → đáy vòng tròn 3
  (`TX_TAP=30`). Cắt ngang không chấm (I3).
- **Bug sửa kèm**: band không có thanh cái vòng (22kV không BB49) đặt terminal
  sai phía — `terminal_y` chỉ lấy `max(rail_y)` = thanh cái chính trên cùng,
  terminal chui lên sát busbar thay vì nằm quá dãy thiết bị. Giờ
  `max(spine_bottom, max(rail_y))`.
- Frontend: MBA có ≥3 ngăn → thêm vòng tròn thứ ba (tâm `y+14`, r16 — phải
  khớp `TX_TAP` backend), nhãn hạ xuống `y+52`.
- BB41 vẫn «(suy ra)» — đo được `/SAS/Subs` chỉ có BB11/12/19, BB21/22/29;
  nhãn phản ánh đúng nguồn, không sửa.

148 test (1 test mới khoá hình học link cuộn 3), check.py xanh cả 7 mục,
dist đã build lại. **Vẫn chưa xem bằng mắt trên trình duyệt** — việc #0.

---

### Energization solver (2026-08-05) ✅ — việc #1, và **câu trả lời cho Q3**

Hướng đã chốt với người dùng: **tự giải từ topology, rồi đối chiếu với `IsLive`
của OneATS** — không đọc lại kết quả của OneATS rồi gọi là của mình.

**Cách làm** (`domain/energization.py`, thuần, không I/O):

1. **Chia đảo (island)**: union-find, chỉ thiết bị `CLOSED` mới nối 2 node.
   `UNDETERMINED`/`INTERMEDIATE` **không** nối. Node `EARTH` bị loại khỏi phân
   hoạch — hai đoạn cùng tiếp địa không phải một dây dẫn.
2. **Gieo mầm CHỈ từ thanh cái** (`Subs.BB*.IsLive`, quality GOOD). **Cố ý
   không** dùng `<bay>.IsLive` làm mầm: OneATS suy ngăn *từ* thanh cái, dùng nó
   thì kết quả của ta chỉ là chép lại của họ, mất luôn giá trị đối chiếu.
3. **Lan truyền**: qua MBA thì mang *nguyên trạng thái* (đóng điện một cuộn là
   đóng điện cả máy — không có dao ở giữa); qua thiết bị không đọc được vị trí
   thì **chỉ mang nghi ngờ** → `UNKNOWN`, không bao giờ `LIVE`, càng không `DEAD`.
4. **Còn lại**: `DEAD` (mọi đường tới nguồn đều mở) — trừ khi đảo có thanh cái mà
   `IsLive` hỏng thì `UNKNOWN`. **Không bao giờ suy ra "hết điện"** từ thiếu dữ liệu.

Trạng thái: `LIVE` / `DEAD` / `EARTHED` / `UNKNOWN`, kèm `reason` (mã, không phải
câu chữ — UI tự dịch) và `via` (MBA/thiết bị nào mang phán quyết vào).

**Kết quả đối chiếu trên DEMO_SAS: 7/7 ngăn khớp `IsLive` của OneATS.**
Đây là bằng chứng mạnh nhất tới giờ rằng bộ template ngăn của ta đúng — hai
đường tính hoàn toàn độc lập ra cùng đáp số. Ca đắt nhất: **E02** mọi dao đều mở
trừ `-9`, nên đường dây có điện *vòng qua* ngăn từ thanh cái vòng BB19, trong khi
chính ngăn thì chết — đúng vế 2 của Lua `(C19L and 171-9C)`, và là lý do
`T1_LINE` v2 chuyển `XSWI9` sang phía đường dây.

Các ca khác đo được:
- **BB29** (`BadWaitingForInitialData`) → `UNKNOWN`, xám nét đứt. Đúng yêu cầu
  an toàn ở manual-test-01 ca 6.
- **D12** mọi dao mở → 2 đoạn `DEAD` riêng biệt, lý do `isolated`.
- **22kV** không có điểm đo nào → `LIVE` qua AT1 (`via=AT1`), và OneATS cũng nói
  `J01.IsLive=True` → khớp. Node cuộn hạ áp lấy theo luật template: đầu của dao
  `TRANSFORMER_DISCONNECTOR` không phải node nội bộ — với T2 là `n_tr`, với T5 là
  `BB41`. Tức **BB41 "suy ra" chính là cuộn 22kV của AT1**, không phải thanh cái ma.

**API/Frontend**: `GET /api/energization` trả `node_state` theo connectivity node;
`RailView`/`EdgeView`/`JunctionView` giờ mang `node_id` để frontend **ghép** màu.
Hình học và trạng thái điện tách rời — chính là thứ cho phép module realtime sau
này đẩy phán quyết mới mà không cần layout lại. Panel bên phải hiện số đảo theo
trạng thái + dòng "Khớp OneATS 7/7".

**Sửa kèm**: bỏ cạnh stub tiếp địa trong layout — nó trùng với ký hiệu tự vẽ và
luôn đi xuống, nên ở band 220kV lật ngược nó chĩa ngược hướng bãi tiếp địa.

168 test (20 test mới), check.py xanh cả 7 mục.

---

### Realtime — subscription + SSE (2026-08-05) ✅ — việc #2

Trước đó model là **ảnh chụp lúc dựng**: đổi dao ở FEP thì màn hình không đổi cho
tới khi bấm «Tải lại từ nguồn». Giờ màn hình bám theo trạm.

**Chia hai pha, đúng như bản chất bài toán:**

| Pha | Làm gì | Tần suất |
|---|---|---|
| Khám phá — `discovery.py` | duyệt cây → cấu trúc, template, graph, hình học | hiếm (mở/tải lại project) |
| Theo dõi — `monitor.py` | subscribe đúng các điểm đã biết địa chỉ | server **đẩy** khi có đổi |

**Danh sách theo dõi tự sinh từ chính observation** — `watch_points(obs)` gom mọi
`PointSample.source_ref` của `PosSt` và `IsLive` (DEMO_SAS: **97 điểm**). Không có
registry song song nào phải giữ đồng bộ; thêm một ngăn vào trạm là tự động được
theo dõi. Để làm được thế phải sửa `discovery.py`: trước đây nó ghi NodeId của
*logical node* vào `source_ref` thay vì của **biến** sinh ra giá trị (dump đã đúng
sẵn) — vừa là lỗi truy vết, vừa là thứ chặn subscription.

**Vá rồi dựng lại, không sửa tại chỗ.** `apply_samples` (thuần) thay đúng những
điểm có `source_ref` trong lô, rồi `build_station` chạy lại toàn bộ. Đo được:
`build_station` 0.71 ms + `solve_energization` 0.21 ms → ~1 ms mỗi lô. Trả 1 ms để
đổi lấy bảo đảm graph sau khi cập nhật **giống hệt** graph dựng mới — thứ mà sửa
tại chỗ không hứa được.

**Hai hành vi an toàn, có test:**
- **Mất kết nối ≠ tin tức về trạm.** Rớt link → `connected=false`, giá trị cũ giữ
  nguyên, header hiện chấm đỏ «Mất kết nối». Không bịa vị trí, cũng không xoá
  trắng sơ đồ (trạm rỗng trông như trạm cắt hết điện).
- **Gộp lô, không lấy mẫu.** Mọi thay đổi đều được áp; chỉ hoãn dựng lại 200 ms để
  một thao tác ngăn (máy cắt + vài dao trong vài trăm ms) vẽ lại **một lần**, ở
  trạng thái nhất quán, thay vì 5 lần qua các tổ hợp chưa từng tồn tại.
- Điểm server từ chối (snapshot cũ hơn model đang chạy) → đếm vào `rejected`, hiện
  «Trực tuyến (thiếu điểm)» màu vàng. Tươi chỗ này đứng chỗ kia còn tệ hơn cũ đều.

**API**: `GET /api/live` (poll) và `GET /api/stream` (SSE) trả **cùng một tài liệu
`LiveOut`** → frontend chỉ có một đường code áp dụng, không có nhánh riêng cho lần
đầu. `structure_revision` tách khỏi `revision`: đổi hình học mới phải tải lại bản
vẽ, đổi trạng thái thì chỉ tô lại.

**Đo thật trên DataServer (2026-08-05, DEMO_SAS v654):**
- duyệt cây 0.70 s → 97 điểm → subscribe **97/97 nhận, 0 từ chối**
- `/api/live`: `connected=true`, 8 đảo, **0 sai lệch** với OneATS (như bản fixture)
- SSE qua HTTP thật: `text/event-stream`, sự kiện đầu 12.7 KB, đủ trạng thái

Vòng thông báo được chứng minh bằng `tests/integration/test_monitor_roundtrip.py`:
dựng **server OPC UA cục bộ**, tự ghi giá trị, khẳng định lô về tới callback. Dùng
server riêng chính vì test này **ghi** — OneATS chỉ đọc (I1), không được chọc.

Cấu hình mới: `BI_REALTIME` (mặc định bật), `BI_OPCUA_PUBLISH_MS` (mặc định 500).

**197 test** (29 test mới), check.py xanh cả 7 mục.

---

## Nhật ký phiên gần nhất

### 2026-08-10 — Trí nhớ hội thoại (ADR-0022) ✅

Người dùng chạy được agent với model thật, rồi hỏi đúng ba lỗ cùng lúc:

> «thế hoàn thành phần memory cho hệ thống, hiện tại cũng chưa làm theo
> conversation, thấy tất cả chỉ là 1 session thì phải?»

Đúng cả ba, và chúng là **ba lỗ khác nhau** bị gộp thành một triệu chứng:

| Lỗ | Trước | Sau |
|---|---|---|
| Mô hình nhớ câu trước? | `message_history=None` — `Conversation.history()` viết từ 2026-08-07, **chưa ai gọi lần nào** | `harness.history()` → 4 lượt văn xuôi gần nhất |
| Nhiều hội thoại? | frontend giữ đúng một id, không danh sách | `GET/DELETE /api/conversations`, menu chọn trên `ChatPane` |
| Sống qua restart? | `OrderedDict` trong process | bảng `conversations` + `conversation_turns` (migration 005) |

**Quyết định trọng tâm, và nó là quyết định an toàn chứ không phải ngân sách:
mô hình đọc LỜI, không đọc SỐ.** `message_history` chỉ mang cặp `(câu hỏi, văn
xuôi)`. Không tool call, không digest, không evidence — dù Pydantic AI sẵn sàng
nhận lại nguyên khối `ModelMessage` và mọi harness chat đều làm thế.

Lý do riêng của trạm biến áp: **trạm đổi trạng thái trong lúc người ta đang nói
về nó.** Nếu lượt 5 còn nhìn thấy `271 CLOSED` mà tool trả về ở lượt 1, thì
đường trả lời rẻ nhất là đọc trí nhớ thay vì gọi tool — và mô hình sẽ đi đường
rẻ nhất. Ra một câu trôi chảy, đúng-lúc-mười-phút-trước, và **không có gì trên
màn hình nói rằng nó cũ**. I2 không bắt được: quality vẫn GOOD, timestamp vẫn
mới, chỉ có điều con số không đến từ lần đọc này.

Hệ quả tự bảo vệ: **`ctx.seen` không thừa kế.** Mỗi lượt bắt đầu với đúng một
ref — scope của pane. Nhớ *«lượt trước nói về Bến Cát»* vẫn phải `resolve` lại
trước khi `summary` chịu chạy. **Trí nhớ để hiểu câu hỏi, không bao giờ để trả
lời.** Có test riêng cho điều này.

**Transcript chỉ lưu lời.** Không evidence, không payload `summary`. Một
`EvidenceRecord` là phát biểu về *một khoảnh khắc*; đọc lại ba ngày sau dưới một
tiêu đề hội thoại là mời người ta đọc số cũ như số đang sống. Mở lại hội thoại
hiện câu hỏi + văn xuôi + dấu thời gian, và **giao diện nói thẳng là không có
bằng chứng** — một lượt cũ hiện trống trơn trông y hệt một lượt bị mất bằng
chứng. Muốn số hiện tại thì hỏi lại: rẻ, và luôn đúng.

Cũng vì thế transcript **không phải audit log**. Audit là `control/audit.py`,
chỉ-append, cho hành động. Hội thoại là thứ để cuộn lại, và xoá được.

**Cách ly tài khoản**: hội thoại thuộc về người mở nó. Của người khác → `resume`
im lặng mở luồng mới; `GET`/`DELETE` trả **404, không phải 403** — 403 xác nhận
id đó tồn tại. Khoá ở tầng SQL (`WHERE actor = ?` trên cả `append`), không ở
tầng người gọi cẩn thận.

**Trần**: 4 lượt vào context (`llm_history_turns`, đặt được), 40 lượt mỗi hội
thoại, **50 hội thoại mỗi tài khoản** — theo tài khoản chứ không toàn cục, để
một người trực hỏi nhiều không đẩy được luồng của kỹ sư ra ngoài.

**File mới**: `store/conversations.py` · `store/migrations/005_conversations.sql`
· `api/conversations.py` (nối protocol của `agent/` với `store/` — `agent/` không
import được `store/`) · `api/routers/conversations.py` ·
`features/assistant/ConversationMenu.vue` · `tests/unit/test_conversation_memory.py`.

**Kiểm chứng**: `check.py` xanh 9/9 · **418 test** (396 → 418, 22 test mới) ·
mypy strict 75 file · 231 khoá i18n khớp vi/en. Hai test đáng đọc nếu chỉ đọc
hai: `test_the_model_is_not_told_last_turns_readings` (digest lượt trước **không**
lọt vào lịch sử) và `test_a_remembered_scope_still_has_to_be_resolved_again`.

**Còn nợ, cố ý**: chưa đo lịch sử tốn bao nhiêu token thật; chưa có nút đổi tên
hội thoại (tiêu đề suy từ câu hỏi đầu — bắt đặt tên trước khi biết luồng đi đâu
là ô nhập không ai điền); `binding` vẫn là pane duy nhất chưa có ruột.

### 2026-08-07 — GĐ 2 bước 1: lát cắt dọc của agent ✅

Hình dạng viết thành [ADR-0019](../10-architecture/adr/0019-agent-shape.md).
Ba bước, đúng thứ tự: **lập kế hoạch (deterministic) → đọc → diễn đạt**.

**Bảy module mới trong `agent/`**, không cái nào quá 260 dòng:

| File | Việc |
|---|---|
| `resolve.py` | `"271"` → `device:D03.XCBR1`. Bốn tầng mạnh dần (name → designation → id → ref), **dừng ở tầng đầu tiên tìm thấy**. Bỏ dấu hai chiều: OneATS lưu `Ben Cat`, người trực gõ `Bến Cát` |
| `plan.py` | Chọn scope nào để đọc. **Đây là chỗ I4 đứng** |
| `tools/registry.py` | Hợp đồng tool + cổng quyền. `READ_ONLY` là danh sách trắng |
| `tools/station.py` | Hai tool: `resolve`, `summary` |
| `brief.py` | Cái tool tìm được, nói hai lần: `facts` cho mô hình, khoá i18n + tham số cho người |
| `provider.py` | `LLMProvider` một phương thức. `OfflineProvider` + `OpenAIProvider` |
| `session.py` | Bộ nhớ hội thoại. Protocol + bản trong-tiến-trình |
| `core.py` | Một lượt. **Một generator phục vụ cả hai endpoint** |

**Hai quyết định đáng đọc lại nếu sau này thấy lạ:**

1. **Mô hình không chọn tool.** Với 2 tool và một resolver deterministic, để nó
   chọn chỉ thêm một kiểu hỏng. Điều kiện xét lại ghi ở ADR-0019 §2 — quanh
   module B, khi danh mục tool đủ lớn để "chọn cái nào" là phán đoán thật.
2. **Pydantic AI bị bác** (ADR-0019 phương án A), dù `AGENTS.md` §3 đã ghi nó từ
   2026-08-04. Nó giải bài toán vòng lặp gọi tool do mô hình điều khiển — đúng
   bài toán (1) nói chưa nên có. Đường lui còn nguyên: `LLMProvider` một phương
   thức, bọc lại là chuyện một file.

**Ba chỗ cố ý không đoán** — cả ba đều có test khoá:

- `Lai Uyen` là tên của **cả E01 lẫn E02** trên DEMO_SAS → trả về hai, **không
  đọc gì cả**, hỏi lại. Đây là lý do `resolve` là một tool riêng chứ không phải
  một hàm tiện ích: nhập nhằng là một *câu trả lời*, không phải một lỗi.
- Hỏi `"trạng thái 999"` → *"trạm này không có gì tên 999"*, **không** âm thầm
  trả lời về scope đang mở. Trả lời về chỗ khác trông y hệt một câu trả lời.
- Mô hình chết giữa chừng → **bỏ phần chữ đã gửi**. Nửa câu về việc dao nào đang
  mở tệ hơn không có câu nào.

**Bốn lớp cưỡng chế I1 phía agent** (ADR-0019 §4). Lớp 2–4 thừa so với lớp 1
*hôm nay*; ngày module C mở, `control.draft` thành quyền hợp pháp của một số tài
khoản, mà agent thì mượn quyền người hỏi — không có ba lớp kia, đúng ngày đó mô
hình phân quyền chạy đúng thiết kế sẽ lặng lẽ trao cho agent một tool ghi.

**Hai máy dò mới trong `check.py`, cả hai đã bẻ thử và xác nhận đỏ rồi phục hồi:**

| Mục | Luật | Bẻ bằng cách |
|---|---|---|
| 3 | mọi `Tool(...)` dưới `agent/tools/` khai `requires=` và không khai capability ghi | đổi `summary` sang `CONTROL_DRAFT` → đỏ |
| 5 | mọi khoá `KEY_*` trong `brief.py` có trong **cả** `vi.ts` và `en.ts` | đổi tên khoá ở cả hai file → đỏ |

Máy dò mục 3 đọc bằng `ast`, **không tin `register()` lúc chạy**: guard lúc chạy
chỉ thấy file có ai đó import, còn một tool thêm vào mà chưa nối dây thì qua được
mọi test — cho tới lúc lệnh import xuất hiện.

**Trạng thái**: `check.py` xanh 9/9 · **393 test** (348 + 45 mới) · mypy strict
sạch 69 file. Toàn bộ 45 test agent chạy **không có mô hình nào** — đó là lập
luận, không phải tiện lợi.

**Còn nợ, cố ý** (ghi ở ADR-0019 §8 + Hệ quả):
- Hội thoại **mất khi khởi động lại** — protocol đã có, bản SQLite làm cùng
  module B khi transcript trở thành thứ để soát lại
- Chưa có endpoint liệt kê hội thoại; client giữ id
- `AnswerOut.text` chỉ có chữ khi `BI_LLM=openai`. Chưa ai chạy thử với mô hình
  thật — `OpenAIProvider` mới có test bằng `ScriptedProvider`, **chưa gọi mạng
  lần nào**. Đây là thứ đầu tiên nên thử tay khi có key.

### 2026-08-07 — ADR-0020: mô hình chọn tool, key vào SQLite ✅

Người dùng nêu ba ý, và ý thứ ba là **một sự thật, không phải một ý kiến**:

> «phải dùng AI vào chứ, còn quyết định là do người phụ trách cơ mà?»
> «như hiện tại nó đơn giản toàn là logic, chẳng có tí AI nào cả»

Đúng: `BI_LLM=off` mặc định, planner là regex, resolver là so chuỗi. Không có
một dòng mô hình nào chạy.

**Một chỗ tôi đã hiểu sai I4 và cần ghi lại để phiên sau không lặp**: I4 nói LLM
không được **khẳng định** sự thật và hệ phải test được không cần LLM. `AGENTS.md`
§2 I4 vốn đã viết rõ *"LLM chỉ: hiểu ý định, **chọn tool**, chọn view, diễn đạt"*.
ADR-0019 §2 (mô hình không chọn tool) là quyết định của phiên viết nó, **chặt hơn
mức invariant đòi**. ADR-0020 nới đúng phần dư.

**Và lập luận «AI không thêm khả năng nào» của ADR-0019 §2 sai ở một chỗ cụ thể**:
`plan.py` chọn *một* scope và đọc *một* lần. Đó là giới hạn của **hình dạng**,
không phải của số lượng tool — nên «đợi tới module B» là đợi nhầm thứ.

| Câu hỏi | `plan.py` | `loop.py` |
|---|---|---|
| `271 thế nào?` | ✅ | ✅ |
| `ngăn Lai Uyên bên 110 có điện không?` | ❌ regex không bắt được | ✅ |
| `so sánh 271 với 272` | ❌ chỉ gọi summary một lần | ✅ |
| `tại sao E01 mất điện?` | ❌ | ✅ |

**Bốn thứ mô hình vẫn không làm được, không thứ nào dựa vào prompt:**

1. Tool nào cũng chỉ-đọc — không có tool ghi để chọn (I1).
2. `tools.call()` từ chối theo quyền **người hỏi**; danh mục đưa cho mô hình cũng
   đã lọc theo quyền (ADR-0016 §5).
3. **Scope ref phải đã được trả về cho nó.** Gõ `bay:E01` từ trí nhớ → bị từ
   chối kèm câu «gọi resolve trước». Đây là điểm mới đáng giá nhất: `bay:E01`
   **có tồn tại**, nên không tầng nào phía dưới phản đối — một câu trả lời tự tin
   về **nhầm ngăn** nhìn y hệt một câu đúng.
4. Mọi con số hiển thị lấy từ payload tool; chữ mô hình nằm field riêng (I3).

**Đường deterministic là SÀN, không phải chế độ hỏng.** Chạy khi không cấu hình,
mô hình chết, không parse được, **và khi mô hình trả lời mà chưa đọc gì**. Điều
kiện cuối đáng ghi: chữ không có bằng chứng là phỏng đoán, tệ hơn câu tính được.
**53 test agent vẫn chạy không mô hình nào** — I4 nguyên vẹn.

**Key vào SQLite** (`004_assistant.sql`, bảng riêng — không nhét `app_meta`):

- Fernet, khoá dẫn xuất từ `BI_SECRET_KEY`. **DB thắng env.**
- Quyền thứ 20 `assistant.config` — **không** dùng `model.*`, vì `model` ở đó
  nghĩa là *model trạm*; một chữ hai nghĩa trong tên quyền là bẫy.
- **API không bao giờ trả key**; test tìm chuỗi key trong *toàn bộ* body chứ
  không kiểm từng field.
- **Lưu ≠ chạy được.** Chỉ nút «Thử kết nối» gọi thật mới đặt `verified_at`, và
  mọi lần lưu đều xoá nó.
- `store/secrets.py` nói rõ nó **không** chống được người có shell trên máy đang
  chạy — nói thẳng còn hơn để chữ «đã mã hoá» làm việc nó không làm được.

**Máy dò mới ở `check.py` mục 3**: mọi `Tool(...)` phải khai `parameters=`. Đã bẻ
thử (xoá schema của `summary`) → đỏ đúng chỗ → phục hồi.

**Kiểm chứng qua HTTP thật** (server tạm, dữ liệu tạm, 2026-08-07):

| Kiểm | Kết quả |
|---|---|
| key có nằm plaintext trong file SQLite/WAL? | **không** — chỉ có token `gAAAAA…` trong WAL |
| GET config có trả key không? | không; `has_key: true` |
| «Thử kết nối» tới endpoint chết | `ok:false` + lý do thật, không im lặng |
| `operator` gọi `/api/assistant/config` | **403** |
| `operator` gọi `/api/ask` | 200 — hỏi được, không cấu hình được |

**Còn nợ, cố ý**: câu trả lời cuối của vòng lặp về nguyên khối, chưa chảy từng
chữ (ADR-0020 §4); `OpenAIProvider` **vẫn chưa gọi mạng lần nào** — nay đã có nút
để trả món nợ đó ngay khi có key.

### 2026-08-07 — GĐ 2 bước 2: ô hỏi đáp thật ✅

`PANE_COMPONENTS.chat` đổi từ `PaneLater.vue` sang `ChatPane.vue`. **Một dòng.**
Không sửa `PaneHost`, không sửa presets, không sửa hợp đồng pane — đây là lần đầu
lời hứa của ADR-0014 §3 được thử bằng một pane thật, và nó đứng.

**Năm file mới**, không cái nào quá 130 dòng:

| File | Việc |
|---|---|
| `stores/chat.ts` | Hội thoại. Là store chứ không phải ref trong component vì pane bị unmount mỗi lần đổi bố cục — luồng reset theo bố cục thì không phải luồng |
| `features/assistant/ChatPane.vue` | Vỏ: cổng quyền, transcript, tự cuộn |
| `features/assistant/TurnBlock.vue` | Một lượt: câu hỏi → vệt tool → bằng chứng → câu trả lời |
| `features/assistant/AnswerBody.vue` | Câu tính được, nút chọn khi nhập nhằng, khối *Diễn giải*, bằng chứng |
| `features/assistant/AskBox.vue` | Ô nhập. Enter gửi, Shift+Enter xuống dòng |

**Ba chỗ đáng đọc lại:**

1. **Số liệu và chữ không bao giờ nối vào nhau.** `key`/`params` ra trước, luôn
   luôn — kể cả khi có mô hình. Chữ của mô hình nằm khối riêng, có nhãn *Diễn
   giải*, màu nhạt hơn. Nối hai thứ vào một đoạn là lúc màn hình không còn nói
   được nửa nào đo được (I3).
2. **Bằng chứng hiện trước khi chữ hiện xong.** Khung `evidence` về ngay sau mỗi
   tool; khung `token` còn đang chảy. Thứ tự đó là chủ ý.
3. **Bấm một ứng viên khi nhập nhằng thì *cả màn hình* nhảy sang đó**, chứ không
   hỏi lại. Câu hỏi vẫn chứa cái tên nhập nhằng — hỏi lại thì lại nhập nhằng.
   Chuyển scope mới là cách giải thật, và câu sau chỉ cần nói "thế nào?".

**Một thứ phải sửa ở backend**: `TurnStartOut` và `ToolCallOut` không nằm trong
request lẫn response body nào nên **không lọt vào `openapi.json`** — frontend sẽ
phải gõ tay hai type, đúng thứ ADR-0009 sinh ra để chặn. Thêm `AskFrameOut`
(RootModel hợp của 5 payload khung) vào `responses` của `/api/ask/stream`, cộng
một lớp `EventStream` khai `media_type` để tài liệu không nói dối là endpoint trả
`application/json`. Giờ cả 5 loại khung sinh type tự động.

**Kiểm chứng**: `check.py` xanh 9/9 · 199 khoá i18n · `POST /api/ask/stream` chạy
thật qua HTTP trên server dev, đủ 5 loại khung, `271` → `device:D03.XCBR1`.
**Chưa xem bằng mắt trên trình duyệt** — đó là việc của bước 3.

### 2026-08-06 — Tài khoản trong SQLite + màn hình đăng nhập ✅

Người dùng yêu cầu làm luôn thay vì để tới GĐ 2.5. Lược đồ bảng đã chốt sẵn ở
ADR-0016 §7 nên đây là hiện thực; phần chưa quyết — **cách xác thực** — viết
thành [ADR-0017](../10-architecture/adr/0017-local-accounts-and-sessions.md).

- Migration `003_users.sql`: `users` (có `external_id`, `password_changed_at`),
  `user_roles` (một người **nhiều** vai), `sessions`.
- `passwords.py` — **Argon2id** qua `argon2-cffi`, tham số mặc định của thư viện.
  Một module duy nhất để chỗ cần soi lại chỉ có một.
- **Phiên lưu phía máy chủ, không phải JWT.** Lý do vận hành: token tự chứa
  không rút lại được trước khi hết hạn, mà *"khoá người này ngay"* mới là thao
  tác thật sự cần. `set_disabled()` xoá luôn phiên đang mở.
- Cookie `HttpOnly` + `SameSite=Lax`; **chỉ SHA-256 của token vào bảng**, nên đọc
  được bảng vẫn không đăng nhập được thành ai.
- **401 ≠ 403** — một cái sửa được bằng đăng nhập, một cái không. Gộp lại là bắt
  giao diện đoán, và nó sẽ đoán sai theo cả hai chiều.
- Bề mặt công khai đúng **ba** đường (`/api/login` `/api/health` `/api/me`), test
  khẳng định **bằng dấu bằng**. `public()` là hàm riêng chứ không phải cờ của
  `requires()`, để "ai cũng gọi được" là một chữ phải gõ ra và grep thấy.
- Gieo 7 tài khoản (6 vai + `truc` nhiều vai), **chỉ khi bảng chưa có ai** — kiểm
  từng tên thì tài khoản quản trị viên đã xoá sẽ mọc lại.
- `password_changed_at IS NULL` → khởi động log cảnh báo nêu tên. Mỗi lần khởi
  động, không phải một lần lúc gieo.
- Frontend: `LoginView.vue`, guard chuyển hướng có giữ link sâu, nút đăng xuất,
  và **không gọi gì về trạm khi chưa đăng nhập** (nếu không, màn hình đăng nhập
  tự rải 401 ra console và một cái login chạy tốt trông như hỏng).

**Một lỗi bắt được trong lúc làm**: `/api/me` lúc đầu tự đọc cookie thay vì đi
qua `get_principal()`. Test phát hiện ngay vì override của test bị bỏ qua — và
đó chính xác là dạng lỗi đáng sợ: **hai chỗ trả lời câu hỏi "ai đang gọi"**, sớm
muộn sẽ trả lời khác nhau. Giờ mọi facet đi qua đúng một hàm.

`test_accounts.py` cố ý **không dùng override** — nó chạy đường thật, có cookie:
`test_authz.py` chứng minh cổng từ chối sai principal, file này chứng minh trình
duyệt trở thành đúng principal. Thiếu vế sau là bỏ trống nửa quan trọng.

Nợ ghi rõ trong ADR-0017: **chưa chống dò mật khẩu**, chưa có bảng nhật ký kiểm
toán, chưa có màn hình quản lý tài khoản.

### 2026-08-06 — GĐ 1.5 lô 1: design system `ui/` ✅

Đủ 10/10 component theo [`frontend-architecture.md` §6](../20-ui/frontend-architecture.md).
Logic hiển thị số đo (I2, Q7) tập trung ở `ui/valueCell.ts`; `ValueCell.vue` là
biểu diễn duy nhất trên màn hình.

Tích hợp tối thiểu: `MeasurementPanel` → `DataTable` + `ValueCell`;
`MeasurementPane` → `Skeleton`/`Empty`; `EvidencePane` → `Skeleton`/`ErrorBox`.
`Field.vue` sẵn sàng — lô 2 gắn vào `StatePane`/`DevicePanel`.

`check.py` xanh, dist build lại. **Chưa xem bằng mắt** — xem hướng dẫn test ở
phiên Cursor tiếp theo hoặc chạy tay preset *Giám sát*.

### 2026-08-07 — GĐ 1.5 lô 2: ruột pane viết lại ✅

Ruột pane chuyển hẳn vào `features/` — không còn bọc `components/panels/` (trừ
`SldCanvas`). Mỗi pane dùng bốn trạng thái: `Skeleton` · `ErrorBox` · `Empty` ·
`ready` (nội dung + `Field`/`ValueCell`/…).

| Pane | File |
|---|---|
| Số đo | `features/monitoring/MeasurementPane.vue` |
| Trạng thái | `StatePane.vue` + `DeviceStateContent.vue` (`Field`) |
| Mang điện | `EnergizationPane.vue` |
| Sơ đồ | `SldPane.vue` (+ Skeleton/ErrorBox khi load model) |
| Độ phủ | `features/engineer/CoveragePane.vue` |
| Cảnh báo model | `ModelIssuesPane.vue` + `features/shared/IssueList.vue` |

`components/panels/` giữ cho `views/` legacy — **lô 3 đã xoá** (xem dưới). Test browser: lô 1 + lô 2
pass trên preset *Giám sát* và *Sự cố*. `check.py` xanh.

### 2026-08-07 — GĐ 1.5 polish: layout inspector (screens.md §3.1) ✅

Preset *Giám sát* đổi sang **SLD full height trái (72%) + inspector phải (28%)** —
không còn dải Bất thường dưới sơ đồ, không còn 3 pane xếp chồng bên phải.

| File | Việc |
|---|---|
| `features/monitoring/InspectorPane.vue` | Accordion: Trạng thái · Số đo · Mang điện · Bất thường · Bằng chứng |
| `features/monitoring/ScopeHeader.vue` | Tiêu đề scope + «Về toàn trạm» |
| `ui/CollapsibleSection.vue` | Hàng accordion tái dùng |
| `app/layout/presets.ts` | `kind: inspector`; incident = SLD + inspector |
| `app/layout/PaneFrame.vue` | `params.chrome: minimal` — bỏ header IN HOA trùng |
| `app/layout/Header.vue` | 2 hàng: tên trạm + link; segmented preset + metadata mờ |

Trạng thái mở/đóng section nhớ theo preset (`localStorage` `bi.inspector.*`).

**2026-08-07 bổ sung:** mỗi section có **scroll riêng** + **kéo đổi chiều cao** (reka-ui
splitter dọc); card `mx-2` để viền không sát mép.

### 2026-08-07 — GĐ 1.5 lô 3: `#/eng`, issue nhóm A/B/C, xoá legacy ✅

**Backend**
- `domain/issue_groups.py` — 12 mã → nhóm A/B/C (duy nhất nơi phân loại).
- `ValidationIssueOut` + trường `group` trên mọi response có issue.
- `GET /api/issues` — danh sách issue kèm nhóm (`station.read`).

**Frontend**
- `#/eng` — `EngView.vue`: Kết nối + Độ phủ + Cảnh báo model (A+B); nút **Chốt bản** → `#/ops/station`.
- `ConnectionsPane`, `AnomaliesPane` (chỉ nhóm C) — thay `PaneLater`.
- `ModelIssuesPane` lọc A+B; preset *Giám sát* / *Sự cố* dùng `anomalies`.
- Router: `landingFor(engineer)` → `#/eng`; redirect `/projects`, `/issues`, `/bay/:id`.
- Header: bỏ link Issues/Projects; thêm **Kỹ thuật** (`model.connect`).
- Xoá: `BayView`, `IssuesView`, `ProjectsView`, `components/panels/*`.

Đáng thử:
1. `engineer` đăng nhập → vào `#/eng`, nối/mở project, xem issue A+B.
2. `operator` → preset *Giám sát*, ô **Bất thường** chỉ nhóm C (nếu có).
3. `#/projects` / `#/issues` / `#/bay/D03` → redirect hợp lý.
4. `python tools/check.py` xanh.

### 2026-08-07 — Sửa click SLD + số đo khi chọn thiết bị ✅

**Triệu chứng:** click symbol trên sơ đồ “không ra gì”; pane *Số đo* trống dù
DataServer có MMXU trên ngăn.

**Nguyên nhân (đã đo trên trình duyệt):**
1. Sơ đồ mặc định *fit cả trạm* → symbol ~**4 px** trên màn hình, click trúng nền
   pan thay vì thiết bị.
2. Kéo/pan trên `<svg>` nuốt click (pointer capture).
3. Số đo backend gom theo `bay:D03`; click thiết bị set `device:…` — pane phải
   leo lên scope cha (`stores/measurements.ts` `forPane`).
4. Trình duyệt cache chunk JS cũ (`MeasurementPane-*.js`) sau `npm run build`.

**Đã sửa:**
- `SldCanvas` / `DeviceSymbol`: không pan khi chạm symbol; click nhãn **ngăn**
  chọn `bay:…`; giữ zoom do người dùng tự chỉnh (không auto-zoom khi click).
- `workspace.go()` giữ query `?l=`.
- `MeasurementPane` + `forPane` — hiện dòng *Số đo của bay:…* khi leo scope.

**Cách thử lại:** `npm run build` → **Ctrl+Shift+R** (hard refresh) → preset
*Giám sát* → click **271** (máy cắt đỏ) hoặc nhãn **D03** trên sơ đồ → cột phải:
*Trạng thái* + *Số đo* (6 hàng MMXU). URL: `#/ops/device:D03.XCBR1?l=monitor`.

`check.py` xanh (2026-08-07).

### 2026-08-07 — Soát lại lô 0–3 trước khi mở GĐ 2 ✅

Người dùng yêu cầu kiểm xem lô 0–3 đã đủ để chuyển giai đoạn chưa. Cổng tự động
xanh sạch ngay từ đầu (`check.py` 9/9, **348 test**, typecheck/lint/format,
`openapi.json` đồng bộ, `dist/` mới hơn mọi file `src/`), và cấu trúc khớp hợp
đồng `frontend-architecture.md`. Nhưng đọc kỹ thì ra **hai lỗ mà chính cổng
không nhìn thấy** — cả hai đều thuộc loại repo này đã bị cắn nhiều lần:

**1. Luật khoá ADR-0014 §8 bị vi phạm, và bị vi phạm bằng một lần *dời chỗ*.**
`features/monitoring/DeviceStateContent.vue` — pane *Trạng thái* của **operator**
— hiện `device.ln`, **Dbpos thô**, và `source_ref` (NodeId). `screens.md` §1 ghi
*"đã có test"*: không có test nào. `frontend-architecture.md` §9 để ô trống với
lý do *"chờ lô 2 chuyển panel xong, vì hôm nay `DevicePanel` vẫn hiện"* — và cái
thực sự xảy ra ở lô 2 là ba trường đó được **chép nguyên** từ `DevicePanel` sang
pane mới. Không ai quyết định gì cả; nó chỉ đi theo lúc viết lại.

Đã bỏ ba trường khỏi bề mặt operator (chỗ của chúng là pane `binding`, chưa làm)
và **dựng máy dò**: `check.py` mục 5 quét `.vue` ngoài `features/engineer/` tìm
`source_ref` · `sourceRef` · `rawDbpos` · `logicalNode` · `.ln`. Đã chứng minh
máy dò có dò (thêm lại một dòng vi phạm → đỏ → hoàn nguyên).

> Bài học ghi lại vì nó sẽ lặp: **một luật hoãn gác không đứng yên chờ.** Lý do
> hoãn ("chờ lô 2") chính là lý do nó bị phá — lô 2 là lần viết lại, và viết lại
> là lúc code cũ được chép đi mà không ai đọc lại luật.

**2. `test_every_code_emitted_in_domain_is_classified` xanh rỗng.** Tên nói là
quét `domain/`, thân hàm chỉ `assert len(ALL_KNOWN) == 12`. `issue_group()`
**raise** với mã lạ và `/api/issues` gọi nó cho mọi issue → mã thứ 13 thêm vào
sẽ không phải thiếu nhãn mà là **500 trên đúng trang người trực mở ra để xem có
gì sai**. Nay test quét thật bằng regex `code="…"` trên cả package `domain/`, so
hai chiều, và tự khẳng định tìm được ≥12 mã **trước khi** so — để chính nó không
xanh rỗng lần nữa. Chứng minh có dò: thêm `code="a_thirteenth_code"` vào
`domain/topology.py` → đỏ → hoàn nguyên. (Hiện trạng 12 mã phát ra = 12 mã phân
loại, không có lỗi đang chạy.)

**Ba chỗ nhỏ sửa kèm:**
- Nút **«Chốt bản»** ở `#/eng` chỉ là `RouterLink` sang `#/ops/station` — không
  chốt gì. Chốt bản là ADR-0015 (bảng `releases`, pin `ModelVersion`), chưa tồn
  tại. Đổi nhãn thành **«Sang màn vận hành»** / *"To the operator view"*.
- `EvidencePane.retry()` gọi lại `props.scope`, trong khi thứ hiện trên màn hình
  do `summary.follow()` nạp theo **workspace scope**. Bằng nhau khi không ghim,
  lệch ngay khi có ghim. Store giờ giữ `asking` = scope của câu trả lời đang
  hiện, và retry hỏi lại đúng câu đã hỏng.
- `screens.md` §2 còn ghi `state` = *"mới là DevicePanel"*, `anomalies` = *"đang
  nằm nhầm ở bề mặt engineer"*, `model-issues` = *"đang lẫn nhóm C"* — lô 3 đã
  sửa cả ba từ hôm trước, bảng chưa cập nhật.

**Đã hỏi và đã chốt cùng ngày** — người dùng: *"bất thường thì luôn giữ cả
trạm"*. Nên hành vi hiện tại là **đúng**, không phải nợ. Đã ghi thành ngoại lệ có
chủ ý trong `screens.md` §2 và trong docstring của `AnomaliesPane`, kèm phần bù
bắt buộc: khi workspace nhắm vào scope hẹp hơn `station`, pane **tự khai** dòng
*«Toàn trạm — cố ý không lọc theo bay:D03»*. Cùng luật với pane bị ghim — một ô
không đi theo màn hình thì phải nói ra, nếu không nó thành cái bẫy.

`check.py` xanh 9/9, 348 test. **Toàn bộ GĐ 0 + 1 + 1.5 đã được commit** — trước
phiên này chúng nằm trong working tree, 103 path đổi + 7.284 dòng thêm, commit
gần nhất còn là GĐ 1.

### 2026-08-06 — GĐ 1.5 lô 0, phần hai: hợp đồng pane ✅ (lô 0 XONG)

Hiện thực phần workspace của [ADR-0014](../10-architecture/adr/0014-frontend-workspace.md),
theo [hợp đồng frontend §3–§10](../20-ui/frontend-architecture.md).

**Bố cục giờ là dữ liệu.** `app/layout/panes.ts` giữ `Pane`/`Layout` và bảng
`PANE_COMPONENTS` — thêm một loại pane là **một dòng**, không phải một nhánh
`v-if`. `presets.ts` giữ cả ba bố cục, và là **chỗ duy nhất** được định nghĩa
bố cục.

- `#/ops/<scope>?l=<preset>` — chủ thể ở path, cách bày ở query. **Scope sai thì
  redirect, preset sai thì im lặng về mặc định**: chỉ cái đầu mới khiến thanh
  địa chỉ và màn hình nói khác nhau về trạm.
- `pane.scope` **vắng = đi theo URL**. Đặt scope là hành động ghim có chủ ý, và
  ô bị ghim **phải hiện nhãn ghim** — không thì màn hình lặng lẽ nói về hai ngăn.
- `App.vue` còn đúng một dòng `<Shell />`. Header, vòng đời stream và banner lỗi
  tách ra `app/layout/` — ba việc khác nhau, ba lý do đổi khác nhau.
- `StationView.vue` **xoá**; cách bày cũ (sơ đồ trái, sidebar phải) giờ chỉ là
  `presets.monitor`, một object trong ba.
- Bảy pane trong `features/` bọc panel cũ nguyên trạng — bản chuyển tiếp, lô 2
  viết lại ruột. Bọc để màn hình đang chạy không thụt lùi.

**`check.py` mục 5 mới — bốn luật của hợp đồng**: `PaneHost` không rẽ nhánh theo
`kind` · bố cục chỉ ở `presets.ts` · `ui/**` không import `stores/`/`api/` · khoá
i18n có đủ ở **cả** `vi` lẫn `en`. Và **cả năm máy dò đều đã chứng minh là có
dò** — phá hỏng từng luật, chạy riêng mục 5, xác nhận đỏ, hoàn nguyên. Đây là
bài học của phần một, áp dụng ngay chứ không chờ bị cắn lần nữa.

**Một chỗ suýt rò**: `summary.follow()` trước đây gọi từ view, giờ gọi từ pane —
mà pane bị dựng lại mỗi lần đổi preset. Không có chốt idempotent thì mỗi lần đổi
bố cục lại thêm một watcher, và hệ quả là **tải lên máy chủ tại trạm**, không
phải màn hình vỡ. Đã chốt trong store.

`check.py` xanh toàn bộ, 308 test. **Chưa xem bằng mắt** — cần chạy tay.

### 2026-08-06 — GĐ 1.5 lô 0, phần một: nền phân quyền ✅

Hiện thực [ADR-0016](../10-architecture/adr/0016-roles-and-capabilities.md).
Làm trước mọi thứ khác trong lô 0 vì nó **chạm mọi route** — để sau là viết lại,
không phải bổ sung.

**Backend**
- `domain/authz.py` — 19 quyền, 6 gói vai, `capabilities_for()` hợp các vai.
  `parse_roles("operator,maintenance")` để một người giữ nhiều vai chạy thật
  ngay từ đầu, không phải phát hiện là hỏng khi có màn hình đăng nhập.
- `check_role_set()` — **luật tách nhiệm vụ cưỡng chế lúc dựng principal**, không
  phải lúc kiểm. Chỉ có luật hợp thì `engineer + supervisor` sẽ **cộng ra đúng
  tài khoản ADR-0016 cấm**: vừa sửa mô hình vừa ký lệnh dựa trên mô hình đó.
- `api/authz.py` — `Principal`, `requires()`, `iter_api_routes()`. Đặt ở đây chứ
  không ở `deps.py` (khác hợp đồng một chỗ, đã ghi lý do trong
  [frontend-architecture.md §11](../20-ui/frontend-architecture.md)).
- **18/18 facet khai `requires=`.** Mặc định là từ chối. Chỉ `/api/me` và
  `/api/health` được khai `requires()` rỗng — và danh sách đó được test khẳng
  định **bằng dấu bằng**, không phải bằng "chứa".
- `GET /api/me` → `{user, roles, capabilities}`.
- `EvidenceRecord.actor` — `/api/summary` ghi tên người hỏi. Không có trường này
  thì không có nhật ký kiểm toán, và mất là mất vĩnh viễn.
- `BI_ROLE` / `BI_USER` trong `config.py`.

**Frontend**
- `authz.ts` (danh sách quyền, đối chiếu chéo bằng `check.py`), `stores/session.ts`.
- Component hỏi `can('model.connect')`, **không** hỏi `roles.includes('engineer')`.
  Hỏi theo tên vai thì thêm một vai là phải sửa mọi component đã gọi tên vai cũ.
- `main.ts` **đợi** `/api/me` trước khi mount, nếu không guard sẽ đá engineer ra
  khỏi chính màn hình của họ mỗi lần F5.
- Lỗi khi đọc `/api/me` → session **rỗng quyền**, không bao giờ rơi về "cho qua".

**`check.py` mục 4 mới** — quét AST mọi decorator route; đối chiếu danh sách
quyền giữa hai ngôn ngữ (cùng khuôn mẫu với ngữ pháp scope).

**Một lỗi đáng ghi**: bản đầu của test *"mọi facet đều khai `requires=`"* **xanh
một cách rỗng**. FastAPI 0.141 bọc mỗi `include_router` vào một lớp vỏ, nên
`app.routes` không chứa endpoint nào — duyệt lớp trên cùng tìm được 0 route và
mọi khẳng định đều đúng vô nghĩa. Bắt được nhờ một test khác *(chỉ `/api/me` và
`/api/health` mở)* fail. Nay `iter_api_routes()` đi xuống, và test tự khẳng định
tìm được đủ số route **trước khi** kiểm bất cứ thứ gì. Đây là lý do một test
"cổng có chặn" phải luôn đi kèm một test "máy dò có dò".

`check.py` xanh toàn bộ, 308 test.

**Còn lại của lô 0**: `panes.ts` → `presets.ts` → `workspace` mọc phần bố cục →
`PaneHost` → `Shell`/`Header` → token trong `styles.css`. *(Xong cùng ngày — xem
mục «lô 0, phần hai» ở trên.)*

### 2026-08-05 — Làm rõ nguồn dữ liệu + chốt thiết kế project/connect
- Người dùng đổi project trong DataServer nhưng sơ đồ không đổi → nguyên nhân:
  `BI_SOURCE=fixture` là mặc định, backend vẽ từ `sas_tree.json`, không đụng
  DataServer. Model chỉ dựng lại lúc khởi động hoặc `POST /api/reload`.
- Chốt thiết kế "tạo project → nhập URL DataServer → tải và vẽ":
  có lưu snapshot. Người dùng sau đó đổi thứ tự: **làm trước** energization.
- Điểm gãy đã nhận diện cho trạm mới: `SAS_PATH` hardcode trong `discovery.py`.

### 2026-08-05 — Hiện thực project + connect (xem mục Đã xong cùng tên)
- Toàn bộ luồng tạo/mở/tải lại/xoá project chạy được, offline test bằng cách
  patch `_observe_opcua` trả fixture — không cần DataServer.
- `.env` của người dùng (`BI_SOURCE=opcua`) giờ chỉ còn là fallback khi
  **chưa có** project nào active; có thể xoá sau khi tạo project đầu tiên.
- **Chưa xem giao diện mới bằng mắt** — cả trang Project lẫn sơ đồ (việc #0
  vẫn đứng nguyên). Người dùng nói sơ đồ "chưa ưng ý" → khi chạy tay, ghi cụ
  thể chỗ chưa ưng vào status để sửa trong việc #5 (diagram engine).

---

## Câu hỏi mở / chờ người khác

| # | Câu hỏi | Hỏi ai | Chặn việc gì |
|---|---|---|---|
| Q1 | **Định nghĩa struct chính thức của alarm ExtensionObject** (ns=2, TypeId 5803) | Team DataServer, ATS | Việc #3 — hiện đang reverse-engineer, field cuối còn lệch |
| Q2 | ATS đã có thư viện bay template chuẩn EVN chưa? | Nội bộ ATS | ~~Việc #1~~ — đã tự dựng 6 template. Vẫn hữu ích để đối chiếu ở trạm khác |
| Q3 | `IsLive` (thanh cái + ngăn) và `SAS_SIM.CheckLiveState`: OneATS tính thế nào? Vì sao `BB29`/`D12` trả `BadWaitingForInitialData`? | Team DataServer | **Đã tự trả lời phần chính (2026-08-05)**: OneATS suy `<bay>.IsLive` **từ** `Subs.BB*.IsLive` qua Lua `CheckLiveState`. Ta gieo mầm từ thanh cái, tự giải, đối chiếu → **7/7 khớp**. Còn hỏi: vì sao 2 điểm kia hỏng, và mầm của chính thanh cái từ đâu ra |
| Q4 | Có trạm thật thứ 2–3 để verify ADR-0002 + ADR-0008 không? | Nội bộ ATS | **CHẶN** (nâng từ Cao, 2026-08-06) — mã thanh cái theo cấp điện áp và quy ước LN mới đo trên **1 trạm**; cả 6/6 template đều `observed_on: DEMO_SAS v654`. ADR-0015 đứng hay đổ tuỳ câu này: trạm thứ hai ra 12/12 thì trình soạn template là chuyện quy mô, ra một nửa `UNKNOWN` thì là việc gấp. **Phép thử rẻ nhất và quyết định nhất của cả dự án** — chỉ cần một dump, `tools/probe_dataserver.py --dump` đã có sẵn |
| Q4b | Quy ước đánh số LN (`XSWI1`=dao thanh cái 1, `XSWI7`=dao đường dây…) là **chuẩn cố định** của OneATS cho mọi project, hay **cấu hình được** lúc dựng bằng Grid Designer? | Team DataServer / Grid Designer, ATS | **CHẶN** cùng Q4. Nếu đặt tự do thì `infer_bay_type()` sập ở trạm sau và toàn bộ M1 phải nghĩ lại. Có thể `document/UserManual/OneATS_UserManual_Chapter-F_OneATS-GridStudio.pdf` đã trả lời — **chưa đọc** |
| Q5 | Account read-only trên DataServer: xin ở đâu? | Team vận hành | Invariant I1 khi triển khai thật |
| Q8 | **ATS đã có hệ thống tài khoản người dùng để liên thông chưa?** (2026-08-06) | Nội bộ ATS | ADR-0016 chốt lưu tài khoản ở SQLite cục bộ + `external_id` để móc sang nguồn ngoài. Trả lời sớm thì `external_id` trỏ đúng chỗ ngay lần đầu; trả lời muộn thì có giai đoạn **hai nơi cấp quyền**, người nghỉ việc phải xoá hai chỗ |
| Q6 | **Dao tiếp địa nối vào node nào?** `-75/-76` quanh `-7`, `-35/-38` quanh `-3`, `-94/-95` quanh `-9` | Team thiết kế / bản vẽ Grid Designer | Đang đọc từ ảnh chụp SLD, **chưa chứng minh**. Không ảnh hưởng energization, nhưng ảnh hưởng câu hỏi an toàn ("đoạn này đã tiếp địa chưa") ở module #2+ |
| Q7 | **Thang đo của số đo là gì?** DataServer không công bố `EngineeringUnits`/`EURange` trên bất kỳ measurand nào (đã kiểm từng biến, 2026-08-06). `Vlin` = 221.08 — V hay kV? `totW` = 87.43 — W hay MW? | Team DataServer, ATS | Hiện **không in đơn vị** cho áp/dòng/công suất, chỉ in số + tên đại lượng, và gắn `LimitCode.UNIT_UNVERIFIED`. Chặn việc hiện đơn vị đúng trên UI và mọi câu agent nói về độ lớn |

---

## Nợ kỹ thuật / rủi ro đã biết

| Rủi ro | Mức | Ghi chú |
|---|---|---|
| Struct alarm reverse-engineered, chưa có spec chính thức | **Cao** | Q1. ATS đổi format là vỡ |
| Kết luận "không cần SLD" mới đo trên 1 trạm (`DEMO_SAS`) | **Cao** | Q4. Trạm khác có thể lệch quy ước đặt tên |
| Mã thanh cái theo cấp điện áp: 22kV/35kV/500kV là **GIẢ ĐỊNH** | Trung bình | `topology.py: VOLTAGE_BUSBAR_CODE`. Sai thì sinh placeholder + cảnh báo, không im lặng |
| `tools/` chạy bằng python hệ thống, backend chạy trong venv → lệch bản asyncua | Thấp | Đã xử lý `StatusCode` vs `StatusCode_`. Chạy tools qua `uv run` nếu cần chắc |
| Điểm Modbus/DNP không theo quy ước 61850 → không auto-bind được | Trung bình | Trạm pha trộn sẽ có tỷ lệ thủ công cao hơn |
| Endpoint DataServer không bảo mật (None + Anonymous) | **Cao** | Tồn tại độc lập với Black Interface; phải báo team vận hành |
| CPU-only tại trạm → LLM chậm | Trung bình | ADR-0006. Giảm nhẹ: câu trả lời ngắn + structured view |
| SQLite ghi đồng thời (event store + reader) | Thấp | Bật WAL, tách connection đọc/ghi |
| Git chưa có remote — chỉ tồn tại trên máy này | Trung bình | Ổ cứng hỏng là mất. Đẩy lên GitHub/GitLab nội bộ ATS khi được phép |
| `.venv` trong OneDrive bị khoá lúc `uv sync` | Thấp | Đã set `link-mode = "copy"`; `check.py` tự retry 1 lần |

---

## Nhật ký phiên

### 2026-08-06 (cuối phiên, tiếp 2) — ADR-0016: vai và quyền
- **Bối cảnh sản phẩm người dùng nêu, quan trọng, chưa từng ghi ở đâu**: Black
  Interface nhắm vào **trạm KHÔNG NGƯỜI TRỰC và trạm ÍT NGƯỜI** — *"user không
  cần thiết phải quan sát SLD mà có thể dùng AI để tóm tắt phân tích báo cáo"*.
- Người dùng đưa ảnh **ma trận actor của chính ATS** (`document/@Station_UseCases 1.xlsx`):
  Operator · Supervisor (Trạm trưởng) · Maintenance · Protection (kỹ sư relay) ·
  Admin, kèm bảng actor × chức năng A–F. Bốn điều rút ra:
  - hình dạng đúng (ma trận), nhưng **mức module quá thô**: *"có C"* không phân
    biệt được **soạn** lệnh với **ký** lệnh;
  - **Supervisor có C** → xác nhận việc tách `control.draft` / `control.sign`;
  - **Protection và Maintenance là vai thật** — bản đề xuất trước của tôi bỏ sót;
  - **không actor nào dựng mô hình**, vì thế giới của họ có Grid Designer làm
    trước rồi → đó đúng là bước ta tự động hoá, nên ta cần vai thứ sáu `engineer`.
- **Rút lại một câu ở lượt trước**: tôi nói *"phân quyền ở đây chủ yếu chống nhầm
  lẫn, không chống kẻ xấu, vì máy nằm trong phòng điều khiển"*. Trạm không người
  trực nghĩa là **truy cập từ xa** → phân quyền là bảo mật thật. Điều này biến
  việc lưu tài khoản từ *tuỳ chọn* thành *cần*.
- Người dùng chốt: **lưu tài khoản vào SQLite luôn** (*"sau này có thể đồng bộ
  database ngược cũng được"*), và **chưa cần làm màn hình đăng nhập**.
- Viết [ADR-0016](../10-architecture/adr/0016-roles-and-capabilities.md): **quyền
  là đơn vị, vai chỉ là gói, một người giữ nhiều vai** (hoà tan lo ngại "chia quá
  nhiều vai") · 19 quyền ở mức *module × động từ* · 6 gói vai giữ đúng 5 tên của
  ATS + `engineer` · kiểm ở **tầng facet** vì agent gọi thẳng facet, không đi qua
  giao diện · **agent mượn quyền người hỏi**, không có quyền riêng · bảng `users`
  có `external_id` làm bản lề để sau liên thông mà không phải di trú.
- Ba nguyên tắc tách nhiệm vụ, cố ý: `engineer` **không bao giờ** có
  `control.sign` · `admin` không có quyền vận hành · `maintenance` không có control.
- **Sửa `screens.md`**: cửa vào mặc định đổi từ **SLD** sang **tóm tắt AI**, mỗi
  vai vào thẳng thứ mình cần. SLD thành nơi *xác minh*, không phải cửa vào. Thêm
  §4.0 luồng đăng nhập → thao tác.
- **Sửa `frontend-architecture.md`**: thêm §11 nền phân quyền vào **lô 0** của
  GĐ 1.5 — `Capability` · `Principal` qua mọi route · `requires=` mặc định **từ
  chối** · `/api/me` · `EvidenceRecord.actor` · vai lấy từ `BI_ROLE` để thử được
  cả sáu bề mặt mà chưa cần đăng nhập.
- Thêm câu hỏi mở **Q8** (ATS đã có hệ thống tài khoản chưa).
- **Chưa động vào code.** Chỉ tài liệu.

### 2026-08-06 (cuối phiên, tiếp) — ADR-0015: template do engineer soạn
- Người dùng truy vai trò engineer: *"engineer có thể CRUD project à?"*, *"tinh
  chỉnh cái gì? review cái gì?"*, rồi *"template này chỉ viết riêng cho DEMO thôi à?"*
- Rà code trả lời, ra **ba phát hiện**:
  1. `IssuesView` đang trộn **ba loại** issue cần ba cách xử lý khác nhau: (A) mô
     hình chưa suy được → sửa bằng **code/template**; (B) sự thật về DataServer →
     chỉ chấp nhận hoặc chỉ tay; (C) `earthed_while_live` /
     `energization_conflict` / `energization_mismatch` → **trạng thái vận hành,
     phải nổi lên màn hình operator**, chôn trong tab engineer là nguy hiểm.
  2. Bảng `releases` **không tồn tại**; `LAST_MODEL_VERSION` khai báo rồi nhưng
     **không chỗ nào ghi hay đọc** ngoài test → phát hiện drift (I7) chưa nối.
  3. `docs/20-domain/bay-templates.md` phát biểu *"cấu trúc ngăn do loại ngăn
     quyết định, không do trạm"* như **sự thật**, trong khi mới đo **một trạm** →
     đã gắn `GIẢ ĐỊNH — chưa xác minh` theo §5.4, thêm **Q4b**, nâng **Q4 lên CHẶN**.
- Tôi đề xuất "template là mã sản phẩm, đừng cho engineer sửa" → **người dùng
  không đồng ý và có lý**: ta mới đo một trạm, sơ đồ 1½ máy cắt/tứ giác cần
  template mới, chờ ATS ra bản dựng thì sản phẩm không nhân bản được.
- Đọc lại ADR-0008 thì thấy **nó vốn đã định cho engineer sửa** — lý do bác bỏ
  phương án Python chính là *"kỹ sư trạm không sửa được"*. Chọn YAML là để mở
  đường đó, chỉ là đường chưa bao giờ được dựng. ADR-0015 hoàn tất, không lật.
- Viết [ADR-0015](../10-architecture/adr/0015-engineer-authored-templates.md):
  template vào store của bản cài · trình soạn **đồ thị** không phải canvas vẽ ·
  bộ sinh vẫn là mã, cấm sửa tại trạm · chọn template bằng **chữ ký** thay
  `infer_bay_type()` · **cổng chứng minh** đối chiếu `IsLive` chặn việc chốt bản ·
  release pin cả `ModelVersion` lẫn phiên bản template.
- **Rút lại** kết luận "chốt bản đã chết" của lượt trước: nó đúng khi template là
  hằng số; template do người soạn thì lại có thật một thứ để duyệt và đóng băng.
- Hạn chế đã ghi thẳng vào ADR, đừng quảng cáo quá: **cổng chứng minh chỉ mạnh
  bằng các trạng thái trạm tình cờ đang ở**. Dao chưa bao giờ mở thì nhánh qua nó
  không được kiểm — chính lỗi `T1_LINE` v1 vẫn lọt nếu không ngăn nào đang ăn
  điện từ thanh cái vòng.
- Thi công thành **GĐ 2.5**, sau agent. GĐ 1.5 giữ thuần frontend.
- **Chưa động vào code.** Chỉ tài liệu.

### 2026-08-06 (cuối phiên) — Người dùng nêu UI/UX, chèn GĐ 1.5
- Nguyên văn yêu cầu: *"tôi muốn giao diện được thiết kế đồng nhất ngay từ đầu để
  sau này đỡ phải sửa lại"*, *"tốt nhất là phác thảo được các màn hình có thể
  dựng, flow user dùng"*, và hỏi có tận dụng Cursor/Codex làm song song được không.
- Kiểm lại: ADR-0014 đã chốt **nguyên tắc** (2 bảng màu, pane là dữ liệu, 3
  preset, cấu trúc thư mục) nhưng **chưa có** danh mục màn hình và luồng người
  dùng — đúng khoảng trống người dùng chỉ ra. Và phần đã chốt thì **chưa thi
  công**: không có `app/layout/`, không có `PaneHost`/`presets.ts`, `features/`
  chưa tồn tại, `ui/` mới 4/10 component.
- Người dùng chọn: chèn **GĐ 1.5 trước GĐ 2**; giao trước **danh mục màn hình +
  flow**, chưa làm token/prototype/handoff.
- Viết [`docs/20-ui/screens.md`](../20-ui/screens.md): 15 loại pane, 3 preset bố
  cục + màn hình engineer (ASCII wireframe), 4 luồng người dùng, bốn trạng thái
  bắt buộc của mọi pane, bảng "cái KHÔNG làm", bảng lệch với code hôm nay.
- **Chưa động vào code.** Backend không đổi, không chạy lại test.
- Điều kiện để chia việc cho Cursor/Codex, ghi lại để phiên sau không quên:
  component thuần trong `ui/` (nhận props, không đụng store) chia được; còn
  `PaneHost`, `presets.ts`, store và `scope.ts` là kiến trúc — một người làm.

### 2026-08-06 — GĐ 1: Module A (Monitoring)
- Người dùng chốt cách làm việc: **họ chỉ test tay trên giao diện**, còn test tự
  động là việc của agent; và **giữ codebase sạch, chia nhỏ module/component theo
  kiến trúc**. Từ đây báo cáo nên nói về cấu trúc và lý do, không phải số test.
- Mở DataServer đo trước khi viết code → bắt được `PPVmax` (không phải `PPVMax`),
  phát hiện **không có `EngineeringUnits`**, và 5 Method điều khiển bộ đổi nấc
  nằm ngay cạnh `TapPos`.
- Dump lại fixture: thuần thêm 80 node, không xoá, không NodeId nào đổi.
- Hiện thực ADR-0012 đầy đủ. Trong lúc làm phát hiện ADR **sai hai chỗ** (case
  của `PPVmax`, và giả định một deadband toàn cục là đủ) → ghi vào cuối ADR thay
  vì sửa phần đã accepted.
- `EvidenceRecord` lần đầu đi ra API qua `/api/summary`, và `EvidenceBlock.vue`
  lần đầu hiện nó lên màn hình. Đây là món nợ có chủ ý từ GĐ 0, trả đúng lúc có
  kiểu thật trong `schema.d.ts` thay vì dựng theo phỏng đoán.
- Kiểm chứng trên DataServer thật: 176 điểm subscribe, `rejected=0`, 20 s chạy
  → 4 nhịp `measurement`, `structure_revision` không đổi. Luật 1 đứng vững.

### 2026-08-04 — Khảo sát OneATS + dựng workspace
- Đọc manual OneATS (8 chương), phân tích `document/SLD_serviceOut/`
- Kết nối DataServer live, dump address space, đo auto-bind + bay-type inference
- Decode struct alarm
- Chốt 7 ADR, dựng workspace + tài liệu + công cụ kiểm tra
- **Chuyển hướng lớn**: SLD ra khỏi MVP (ADR-0002); không làm canvas vẽ (ADR-0003);
  alarm không dùng OPC UA A&C (ADR-0007)

### 2026-08-04 — Module #1: bay template + topology + viewer
- Chốt ADR-0008 (schema template YAML), hiện thực 6 template
- Dựng chuỗi: dump/live → `StationObs` → template → `StationGraph` → `DiagramView` → SVG
- Viewer 1 file HTML để nhìn kết quả ngay, không cần Node
- 96 test offline + 2 test live; `tools/check.py` xanh toàn bộ
- Đính chính: `DBB`/`EBB` là bảo vệ so lệch, không phải thanh cái
- Bắt được 1 lỗi thật lúc test live: `get_children()` của OneATS trả trùng
  → 320 thiết bị thay vì 80. Đã dedupe theo NodeId + ghi vào bảng bẫy

### 2026-08-04 — Sửa topology theo ground truth + layout kiểu Grid Designer
- **Phát hiện nguồn sự thật mới**: `document/DEMO_SAS-MODELExplorer.xlsx` chứa
  mã Lua `CheckLiveState` — chính công thức OneATS dùng để tính `IsLive`.
  Xem `AGENTS.md` §5.5.
- **Sửa lỗi thật trong template v1**: `XSWI9` (`-9`) ở ngăn đường dây và MBA
  nối vào **phía đường dây**, bỏ qua máy cắt — không phải phía thanh cái.
  Template cũ sẽ báo "đường dây mất điện" khi thực tế đang được cấp qua
  thanh cái vòng. T1, T2 → v2.
- Sửa T5 (22kV): `-3` nằm **trước** máy cắt, không phải sau.
- Xác nhận T3 (nối thanh cái) và T4 (nối vòng) đã đúng.

### 2026-08-04 — Sơ đồ đọc được: làn thanh cái + gộp cả trạm một hình
Người dùng đối chiếu với ảnh chụp HMI OneATS và chỉ ra hai chỗ sai.

- **Lỗi đọc hình, đã sửa**: `-1` và `-2` vẽ chung một đường thẳng đứng, nên
  đường đó chạm cả BB21 lẫn BB22 tại cùng một điểm — hình luôn trông như có
  đường dẫn xuyên qua cả hai thanh cái, **bất kể dao đang ở đâu**. Cũng vậy
  với đuôi đường dây cắt ngang BB29 đúng chỗ `-9` nối vào.
  Sửa: mỗi dao nối thanh cái có **làn x riêng** (`_assign_lanes`), mỗi chỗ nối
  thật có **chấm** (`JunctionView`), cắt ngang không chấm = không nối.
  Khoá bằng `test_no_conductor_runs_through_another_devices_busbar_connection`
  — test này duyệt mọi đoạn dây và mọi chấm nối trong cùng ngăn.
- **Gộp cả trạm vào một hình**: `layout_station()` + `GET /api/diagram`.
  220kV lật ngược (thanh cái chính xuống dưới, đường dây đi lên), 110kV và 22kV
  bình thường → hai nhóm thanh cái quay vào nhau, đúng cách bản vẽ Grid
  Designer của trạm đang trình bày. Tab cấp điện áp giờ chỉ để nhảy tới dải.
- Ngăn MBA kết thúc bằng ký hiệu cuộn dây; **cố ý không vẽ** đường nối D01↔E07
  vì DataServer không có bằng chứng ghép ngăn (I3).
- 124 test offline xanh; `tools/check.py` xanh cả 7 mục.
- `tests/unit/test_topology_ground_truth.py` — mỗi test trích đúng dòng Lua nó khoá
- Layout theo Grid Designer: 2 thanh cái chính ở trên, ngăn ở giữa,
  **thanh cái vòng ở phía đầu ra**, terminal dưới cùng
- Ký hiệu theo Grid Designer: máy cắt = ô vuông đặc, dao = hình thoi đặc
- **Đính chính bảng màu**: dây dẫn xanh dương = có điện (không phải đỏ).
  Thiết bị vẫn đỏ = đóng.

### 2026-08-04 — Khung dự án
- Init git, commit toàn bộ hiện trạng; branch `skeleton/project-structure`
- ADR-0009: bỏ Nuxt, dùng Vite + Vue 3 + TS
- Thêm `config.py` / `errors.py` / `logs.py` / `store/` (SQLite WAL + migration)
- Dựng frontend thật, xoá viewer tạm 282 dòng
- Nối hợp đồng API bằng máy: `openapi.json` → `schema.d.ts`, `check.py` gác
- `tools/check.py`: 7 mục, xanh toàn bộ. Backend 107 test + 2 live
