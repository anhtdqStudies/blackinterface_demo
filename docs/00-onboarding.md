# Onboarding — ngày đầu tiên

> Dành cho **người**. `AGENTS.md` viết cho AI agent và là nguồn sự thật đầy đủ;
> file này là đường ngắn nhất để bạn chạy được hệ và hiểu vì sao nó được dựng
> như vậy. **30 phút đọc, 1 giờ chạy được.**

---

## 1. Sản phẩm này là gì (2 phút)

**Black Interface** = lớp vận hành AI-first thay thế HMI tĩnh của OneATS, cài
**local** trên server tại trạm điện. Nhắm vào **trạm không người trực và trạm ít
người**: người vận hành không phải ngồi đọc sơ đồ, mà hỏi và nhận câu trả lời có
bằng chứng.

Đúng hai mục tiêu:

1. **M1 — rút ngắn thời gian dựng project.** Trỏ vào OneATS DataServer là ra HMI
   chạy được: không vẽ tay, không map point thủ công. *Đã chứng minh trên 2 trạm.*
2. **M2 — giám sát realtime + phân tích sự cố.** Có vấn đề thì chỉ ra nguyên nhân
   cụ thể và hướng xử lý, **kèm bằng chứng**. *Mới xong nửa đầu.*

Chi tiết: [`00-product/vision.md`](00-product/vision.md).

---

## 2. Chạy nó lên (1 giờ, phần lớn là chờ tải)

Cần: **Python 3.12** (không phải 3.13 — wheel còn lệch), [`uv`](https://docs.astral.sh/uv/),
Node 20+.

```bash
# backend
cd backend && uv sync

# frontend  (chưa build thì API chạy nhưng KHÔNG có giao diện — cố ý)
cd ../frontend && npm install && npm run build

# chạy
cd ../backend && uv run uvicorn blackinterface.api.app:app --port 8080
```

Mở `http://127.0.0.1:8080`. Đăng nhập `engineer` / `blackinterface`.

**Chưa có DataServer?** Không sao — mọi thứ chạy được offline từ fixture. Đó là
thiết kế, không phải giải pháp tình thế: `integration/dump.py` và
`integration/opcua/discovery.py` cùng sinh ra một `StationObs`, nên fixture là
cùng một hợp đồng với hệ live.

**Bỏ qua đăng nhập khi dev**: `BI_AUTH=env BI_ROLE=engineer uv run uvicorn …`
Không bao giờ dùng ở trạm — nó cấp cùng bộ quyền cho bất kỳ ai chạm cổng mạng.

### Cổng phải xanh trước mọi PR

```bash
python tools/check.py     # 9 mục: layout, ranh giới lớp, read-only, hợp đồng
                          # pane, i18n, docs có ngày, ruff+mypy+pytest, OpenAPI,
                          # typecheck+lint frontend
```

**Không được báo "xong" khi `check.py` chưa xanh.** Fail thì nói rõ là fail, kèm
output. Không giấu, không hedging.

Bẫy Windows: repo nằm trong OneDrive, `uv sync` có thể báo `os error 396` /
`Access is denied`. Chạy lại lần hai — `check.py` tự retry một lần.

---

## 3. Tám luật bất biến (10 phút — đọc kỹ nhất phần này)

Vi phạm bất kỳ luật nào = **sai, kể cả khi code chạy được**. Nghĩ là cần phá luật
thì **dừng và hỏi**, đừng tự quyết. Bản đầy đủ: [`AGENTS.md`](../AGENTS.md) §2.

| | Luật | Vì sao |
|---|---|---|
| **I1** | Một đường ghi duy nhất qua `control/`, và **cửa đang đóng** (`COMMANDS = {}`). Agent **không bao giờ** có tool tự thực thi — **agent soạn phiếu, người ký** | Đây là thứ quyết định sản phẩm có được cho vào trạm điện hay không |
| **I2** | **Không khẳng định trạng thái khi quality không GOOD.** `quality != GOOD` → `UNDETERMINED`, cấm nói "đang đóng/mở" | Luật an toàn, không phải luật thẩm mỹ |
| **I3** | Evidence là **typed object do tool sinh**, không phải văn bản LLM viết. Mọi con số trong prose phải truy được về `metadata` của một `ToolReturn` | |
| **I4** | **LLM không nằm trên đường đi của tính đúng đắn.** Topology, energization, chuỗi nhân quả → backend deterministic | ADR-0005, mệnh đề lõi, không đổi |
| **I5** | Frontend gọi **thẳng** Domain API. BlackCore dùng **đúng** API đó, không có đường riêng, không có quyền cao hơn | |
| **I6** | Không lớp nào chạm raw NodeId ngoài `integration/`. **NodeId không bao giờ là primary key** | |
| **I7** | Release là **immutable** và pin theo snapshot có hash. NodeId không resolve được = **drift**, phải nổi lên UI, **cấm im lặng fallback** | |
| **I8** | Địa chỉ hoá bằng **`scope × facet`**, không bằng use case. Thêm use case mà phải thêm tool cho agent → **thiết kế đã sai** | Cách đúng là thêm một bộ lọc hoặc một scope |

`tools/check.py` cưỡng chế I1, I6, I8 bằng `ast` — không phải bằng lời dặn.

### Luật riêng của dự án này: đo, đừng nhớ

Số liệu về OneATS phải ghi kèm **ngày đo** và **cách đo lại**. Chưa đo thì viết
rõ `GIẢ ĐỊNH — chưa xác minh`. **Cấm** trích số từ trí nhớ hoặc từ manual PDF như
thể đã đo — manual đã sai so với hệ chạy thật ít nhất một lần.

---

## 4. Bốn cái bẫy sẽ cắn bạn trong tuần đầu

Bảng đầy đủ 30 dòng ở `AGENTS.md` §7. Bốn cái hay gặp nhất:

| Tưởng | Thực tế |
|---|---|
| Alarm dùng OPC UA A&C | **Sai.** OneATS dùng interface riêng `OAAlarm.GetActiveAlarm(NodeId[])`. Subscribe event chuẩn → 0 event |
| `PosSt` là boolean | **Sai.** Dbpos 4 giá trị: `0`=INTERMEDIATE `1`=OPEN `2`=CLOSED `3`=BAD |
| Đỏ = có điện | **Sai.** OneATS: **thiết bị** đỏ=đóng / xanh lá=mở; **dây dẫn** xanh dương=có điện. Và **cấm** dùng màu của sơ đồ để báo trạng thái phần mềm — `sys-*` không bao giờ dùng đỏ hoặc xanh lá |
| Không đọc được vị trí dao → coi như mở | **Sai và nguy hiểm.** Thiếu dữ liệu không bao giờ được suy ra "hết điện" — đó là câu khiến người ta chạm tay vào |

---

## 5. Bạn sở hữu gì, làm gì

[`90-progress/team.md`](90-progress/team.md) — bảng sở hữu, hai bắt tay giữa ba
người, việc cụ thể, lịch 6 tuần. Luật đằng sau nó:
[ADR-0023](10-architecture/adr/0023-team-delivery-architecture.md).

**Ba điều nhớ ngay:**

1. **Số migration đã cấp trước** — Dev A: `006`, `008`… · Dev B: `007`, `009`…
   Đụng số là hỏng database, không phải conflict text.
2. **`backend/openapi.json` không bao giờ merge tay.** Conflict thì
   `git checkout --theirs` rồi chạy lại `uv run python ../tools/export_openapi.py`.
3. **Cuối mỗi phiên/PR: viết một file trong [`90-progress/log/`](90-progress/log/).**
   Không sửa `status.md` — đó là file của chủ dự án.

---

## 6. Đọc gì tiếp, theo nhu cầu

| Khi nào | Đọc |
|---|---|
| Luôn luôn, trước khi sửa gì | [`AGENTS.md`](../AGENTS.md) |
| Đang ở đâu, việc kế tiếp | [`90-progress/status.md`](90-progress/status.md) |
| Động tới OPC UA / DataServer / alarm | [`30-integration/oneats-dataserver.md`](30-integration/oneats-dataserver.md) |
| Gặp thuật ngữ lạ (61850, CIM, EVN) | [`20-domain/glossary.md`](20-domain/glossary.md) |
| Thêm module hoặc đổi ranh giới lớp | [`10-architecture/overview.md`](10-architecture/overview.md) |
| Định làm khác một quyết định đã chốt | [`10-architecture/adr/`](10-architecture/adr/) — **ADR là immutable**, muốn đổi thì viết ADR mới |
| Làm bất kỳ module use case nào (A–F) | `document/@Station_UseCases 1.xlsx` — dùng làm **bộ đề kiểm tra độ phủ**, không phải khuôn mẫu code từng dòng (I8) |

Không đọc `document/UserManual/*.pdf` trừ khi thật sự cần — đã chắt lọc vào `docs/`.

---

## 7. Ngôn ngữ

- Trao đổi với nhau: **tiếng Việt**.
- Code, tên biến, docstring, commit message: **tiếng Anh**.
- Tài liệu trong `docs/`: tiếng Việt, thuật ngữ kỹ thuật giữ nguyên tiếng Anh.
