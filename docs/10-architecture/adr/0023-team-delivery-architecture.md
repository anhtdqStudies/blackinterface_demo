# ADR-0023 — Năm module, ba chủ sở hữu, và lát cắt dọc là đơn vị giao việc

- **Status**: Accepted
- **Date**: 2026-08-10
- **Supersedes**: không. Đây là ADR đầu tiên nói về **cách làm việc** chứ không
  về sản phẩm. Nó không đổi một invariant nào và không đổi một ranh giới lớp nào
  — `AGENTS.md` §4.1 vẫn là chiều phụ thuộc duy nhất.

## Bối cảnh

Tới 2026-08-10, repo là sản phẩm của **một người**: 22 ADR, 8 invariant,
~12.000 dòng backend, ~11.000 dòng frontend, 418 test, dựng trong 7 ngày. Mọi
quyết định nằm trong một cái đầu và mọi file có một người sửa.

Từ tuần sau có **ba người**. Điều đó làm hỏng ba giả định mà repo đang dựa vào
mà chưa ai viết ra:

| Giả định ngầm | Vỡ ở đâu khi có 3 người |
|---|---|
| Một người sửa mọi file, nên không cần nói ai sở hữu gì | Hai người sửa `api/schemas.py` cùng lúc; hai người cùng đặt migration số `006` |
| `status.md` là bộ nhớ chung, ai cũng ghi vào | 1.625 dòng, một file, mọi PR đụng → conflict mỗi ngày → người ta bỏ luật |
| Ai cũng có DataServer trên `127.0.0.1:48050` | Người viết tool phải chờ người viết importer đọc xong dữ liệu |

Phản xạ tự nhiên là chia theo **lớp** — "A làm domain, B làm api". Đó là cái bẫy:
mọi tính năng đều xuyên nhiều lớp, nên chia ngang thì tính năng nào cũng cần hai
người và một lần bàn giao.

Sở trường của ba người **không** trùng với ranh giới lớp: chủ dự án mạnh về
harness của agent và là người duy nhất làm được frontend; dev A mạnh về tool và
các module use case; dev B mạnh về kết nối DataServer và mô hình hoá.

## Quyết định

### 1. Năm module, mỗi module một chủ sở hữu *hợp đồng*

| # | Module | Thư mục | Hợp đồng ra ngoài | Chủ |
|---|---|---|---|---|
| M1 | Mô hình trạm | `integration/` `domain/` `diagram/` | `domain/models.py` + `scope.py` | Dev B |
| M2 | Domain API | `api/` `store/` | **`backend/openapi.json`** | Dev A |
| M3 | BlackCore | `agent/` | `agent/tools/registry.py` | Chủ dự án (tool: dev A) |
| M4 | Đường ghi có duyệt | `control/` | `COMMANDS = {}` | Chủ dự án |
| M5 | Vỏ & giao hàng | `frontend/` `tools/` `installer/` | `frontend/src/api/schema.d.ts` | Chủ dự án |

Chiều phụ thuộc không đổi: `M1 ← M2 ← M3`, `M5 → M2`, và **`M4` không ai import
được** (I1, `check.py` mục 2).

### 2. Module là đơn vị **sở hữu**, lát cắt dọc là đơn vị **giao việc**

- **Sở hữu module** = ai có tiếng nói cuối cùng khi hợp đồng của nó đổi, và ai
  phải review PR chạm vào nó.
- **Giao việc** = một lát cắt xuyên nhiều module, một người làm hết. Ví dụ *"đọc
  alarm"* của dev B đi từ `integration/opcua/alarms.py` qua `domain/alarm.py` tới
  `api/broadcast.py` — ba module, một người, một PR.

Người sở hữu module không phải người viết mọi dòng trong đó; họ là người **duyệt**.

### 3. Danh sách file độc quyền

Chỉ **chủ dự án** được sửa: `AGENTS.md` · `docs/10-architecture/adr/**` ·
`tools/check.py` · `domain/scope.py` · `control/**` · `agent/{core,harness,digest,session,provider,config}.py` ·
`frontend/**` · `docs/90-progress/{status,questions,risks,team}.md`.

Ai cần đổi thì mở issue, **không tự sửa**. Lý do: bảy file này là nơi các
invariant sống. `check.py` bắt được vi phạm cú pháp, nó không bắt được ý định.

### 4. Ba luật chống va chạm

1. **Số migration cấp trước.** Dev A giữ `006`, `008`, `010`…; Dev B giữ `007`,
   `009`, `011`… Đụng số migration là hỏng database, không phải conflict text.
2. **`openapi.json` không bao giờ merge tay.** Conflict thì
   `git checkout --theirs backend/openapi.json` rồi chạy lại
   `uv run python ../tools/export_openapi.py`.
3. **`api/schemas.py` và `api/app.py` chỉ thêm vào cuối**, mỗi người một khối có
   comment tên luồng.

### 5. Hai bắt tay giữ cho không ai chờ ai

**Fixture là hợp đồng (M1 → M2).** Dev B nộp `backend/tests/fixtures/*.json`
**trước** khi viết reader live. Dev A viết facet và tool trên
`integration/dump.py`, không cần DataServer, không cần chờ. Đường offline và
đường online đọc cùng một `StationObs`, nên fixture không phải bản mô phỏng —
nó là cùng một hợp đồng.

**Schema trước, ruột sau (M2 → M5).** PR đầu tiên của mỗi tính năng là *schema +
endpoint trả dữ liệu thật*, merge sớm. Chủ dự án `npm run api:types` rồi dựng
pane song song với việc dev A hoàn thiện bên dưới. Đổi schema sau khi pane đã
dựng là lỗi quy trình, không phải việc frontend phải chạy theo.

Ràng buộc: endpoint trong PR đầu phải trả **dữ liệu thật**, không mock. Dựng
giao diện trên hình dạng tưởng tượng là dựng hai lần.

### 6. `status.md` tách ra

```
docs/90-progress/status.md      hiện tại, ~150 dòng, chỉ chủ dự án sửa
docs/90-progress/team.md        ai sở hữu gì, làm gì tuần này
docs/90-progress/questions.md   Q1..Q8 chờ ATS
docs/90-progress/risks.md       nợ kỹ thuật
docs/90-progress/log/           MỖI PHIÊN/PR MỘT FILE MỚI — không ai đụng ai
```

`AGENTS.md` §5.2 đổi từ *"cập nhật `status.md`"* thành *"viết một file trong
`log/`"*. Đây là chỗ luật cũ chắc chắn sẽ bị bỏ nếu giữ nguyên: một luật buộc ba
người ghi vào cùng một file là một luật tự phá.

### 7. Definition of Done

Một PR xong khi: `python tools/check.py` **xanh** · có test · chạm endpoint thì
đã chạy `export_openapi.py` · có một file trong `log/` · diff ≤ ~600 dòng.

## Phương án đã bác bỏ

**Chia theo lớp** (A làm domain, B làm api). Bác vì mọi tính năng xuyên lớp:
thêm alarm là đụng `integration/` + `domain/` + `api/` + `agent/`. Chia ngang
biến mỗi tính năng thành một chuỗi bàn giao, và bàn giao là chỗ lịch trình trượt.

**Tách "core agent" và "tool" cho hai người.** Trong code hai cái này tách thật —
`registry.py` là seam, `ToolReturn` là hợp đồng, và cái tách đó đáng giữ. Nhưng
làm ranh giới người thì hỏng: thêm `trace` là đụng `tools/`, rồi `digest.py` phải
rút gọn payload của nó, rồi `harness.py` phải cho nó vào danh mục theo quyền.
Ba file, hai chủ, một tính năng. Gộp thành M3 và tách theo **tính năng**.

**Một repo cho mỗi module.** Bác vì `check.py` là cổng chạy trên **toàn bộ** cây:
nó so `SCOPE_KINDS` giữa Python và TypeScript, so 20 capability giữa hai ngôn
ngữ, so `openapi.json` với `schema.d.ts`. Tách repo là mất đúng thứ đang giữ ba
người khỏi lệch nhau, để đổi lấy một sự độc lập mà chưa ai cần.

**Không giao đóng gói cho ai.** Bác một nửa: đóng gói (Inno Setup, Windows
Service, vendor wheel air-gapped, vLLM tại trạm) **hoãn tới sau demo nội bộ**, vì
demo chạy từ source được. Nhưng nó được ghi vào `risks.md` kèm ước lượng 3–4
tuần, chứ không im lặng biến mất khỏi kế hoạch.

## Hệ quả

- Ba người có ba vùng gần như rời nhau. Chỗ giao duy nhất là `api/schemas.py`,
  `api/app.py` và `openapi.json`, và cả ba đều có luật riêng ở §4.
- **Chủ dự án ôm hai vị trí hub** — harness (mọi tool đi qua) và frontend (mọi
  tính năng hiện ra). Cứu cánh là hai hợp đồng ở §5: `register()` để dev A tự
  thêm tool mà không chạm `harness.py`, và `openapi.json` để không phải hỏi nhau
  schema là gì. Giữ hai hợp đồng sạch thì không thành nút cổ chai; buông một
  trong hai thì cả hai dev đứng.
- Người sở hữu module phải **review**, nên review là việc có lịch, không phải
  việc làm khi rảnh.
- ADR này sẽ phải xét lại nếu đội lớn hơn 4 người, hoặc nếu `frontend/` có người
  thứ hai chạm vào — lúc đó §3 (độc quyền) là thứ vỡ trước.
