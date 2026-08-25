# Thử tay Module B — Alarm và sự cố

> **Cập nhật**: 2026-08-13. Cần DataServer thật đang chạy ở
> `opc.tcp://127.0.0.1:48050`, và cần thao tác được trên simulator OneATS.

## 0. Chạy

```bash
cd backend  && uv sync
cd frontend && npm install && npm run build
cd backend  && BI_SOURCE=opcua BI_AUTH=env BI_ROLE=operator \
               uv run uvicorn blackinterface.api.app:app --port 8080
# -> http://127.0.0.1:8080
```

`BI_AUTH=env` bỏ qua đăng nhập cho tiện thử. **Không dùng ở trạm.**

Vào `#/ops/station`, chọn tab **Sự cố**.

## 1. Trạm yên — phải thấy gì

Đây là phép thử quan trọng nhất, và nó là phép thử về cái **không** hiện ra.

| Mong đợi | Vì sao |
|---|---|
| Dòng đếm: `Toàn trạm: 0 sự cố · ~120 trạng thái · N chưa phân loại` | 243 alarm active được phân loại, không đổ thẳng lên màn |
| Danh sách sự cố **rỗng**, chữ "Không có sự cố nào đang mở." | Trạm đang bình thường |
| **Không** thấy dòng nào kiểu `CB 271 STATUS` | Máy cắt đóng bình thường không phải sự cố (ADR-0027 §1) |

Nếu thấy hàng chục dòng trạng thái đóng cắt → bảng phân loại
`domain/alarm_rules/default.yaml` không khớp dialect của trạm này.

Nếu thấy **"Chưa đọc được danh sách alarm"** → subscription chưa lên. Xem log
`alarm subscription established`. Đây cố ý khác với "không có sự cố": chưa nhìn
thì không được nói là không có (I2).

## 2. Tạo một sự cố

Trên OneATS Data Editor / HMI, **mở máy cắt 271** (`D03.XCBR1.PosSt`).
Hoặc `D01.XCBR1` — đó là ngăn đã dùng để đo chuỗi lan truyền.

Trong **≤ 1 giây** tab Sự cố phải đổi.

| Mong đợi | Vì sao |
|---|---|
| Xuất hiện **một** thẻ sự cố, không phải 7–8 dòng rời | Gom cụm theo cửa sổ 200 ms + vùng điện |
| Tiêu đề là alarm nặng nhất, thường `ABNORMAL VOLTAGE` sev 650 | Xếp theo severity |
| Mục **Alarm trong cụm** liệt kê các điểm điện áp kèm mốc mili giây | Đo được: 7 alarm trong 87 ms |
| Mục **Bằng chứng đi kèm** có `...XCBR1.PosSt` | Máy cắt mở là dữ kiện, không phải lý do báo động |
| Dòng chữ nghiêng: *"...chưa phải chuỗi nhân quả"* | Gom cụm ≠ nhân quả. `trace` chưa có (ADR-0024) |
| Khối **Hướng dẫn xử lý** kèm nhãn đỏ **BẢN NHÁP — chưa được duyệt** | ADR-0027 §3 |

### Bẫy đáng chú ý

Nếu anh thao tác bằng tài khoản OneATS thì alarm mang trường `actor`, và hệ
phân loại nó là **thao tác**, không phải sự cố → **sẽ không có thẻ sự cố nào**.

Đây là hành vi đúng và cố ý: người vận hành đóng cắt bình thường không được
báo động. Muốn thấy sự cố thì phải là thay đổi *không* do người gây ra — ví dụ
để simulator tự sinh, hoặc ép một giá trị đo vượt ngưỡng.

Cách phân biệt trên màn: thẻ sự cố có dòng *"Do ... thao tác"* thì đó là
đường `actor`.

## 3. Thu hẹp phạm vi — và luôn đọc dòng "Đang xét phạm vi"

Pane có **hai** con số nói về hai thứ khác nhau, đây là chỗ dễ hiểu nhầm nhất:

| Dòng | Phạm vi |
|---|---|
| `Toàn trạm: N sự cố · ...` | **luôn là cả trạm** — thu hẹp không được giấu chuyện hỏng ở chỗ khác |
| `Đang xét phạm vi: ...` | phạm vi mà **danh sách bên dưới** đang nói về |

Danh sách rỗng trong khi dòng đầu báo 82 sự cố là **hợp lệ** nếu phạm vi đang
xét không chứa cái nào. Trước khi kết luận là lỗi, đọc dòng thứ hai.

Thử lần lượt: `#/ops/station` → `#/ops/vl:220kV` → `#/ops/bay:D03`. Số phải
thu hẹp dần và không bao giờ nhảy về 0 khi cấp trên còn khác 0 *trong cùng nhánh*.

Đo 2026-08-13 sau khi sửa lỗi phạm vi:

```
station     alarm=252  incident=4
vl:220kV    alarm=75   incident=2
vl:110kV    alarm=81   incident=8
busbar:BB21 alarm=68   incident=8
bay:D03     alarm=14   incident=1
```

> **Lỗi đã gặp và đã sửa (2026-08-13)**: mọi phạm vi `vl:` / `busbar:` /
> `transformer:` đều trả **0** vì `AlarmStore` lọc bằng `ScopeRef.contains`, mà
> hàm đó trả `False` cho các loại đó với nghĩa *"không quyết định được từ id"*,
> không phải *"không thuộc"*. Giờ đi qua `bays_in(graph, ref)` như `summary.py`.
> Khoá lại bằng `test_voltage_level_scope_reaches_the_alarms_in_its_bays`.

## 4. Kiểm tra thẳng API

```bash
curl "http://127.0.0.1:8080/api/alarms?scope=station" | jq '.counts'
curl "http://127.0.0.1:8080/api/alarms?scope=station&include_status=true" | jq '.alarms | length'
curl "http://127.0.0.1:8080/api/incidents?scope=station" | jq '.incidents[0].playbook.status'
curl "http://127.0.0.1:8080/api/incidents?scope=bay:KHONGCO" -i | head -1   # phải 404
```

`evidence.limits` luôn có `quality_not_good`: OneATS **không** điền trường
`Quality` của A&C, nên không alarm nào khẳng định được chất lượng điểm phía sau
nó. Nói ra còn hơn để người đọc tưởng là GOOD (I2).

## 4b. Cách thử tay cho hợp lý

Ba thói quen, rút ra từ đúng những lần hụt trong phiên 2026-08-13:

**1. So màn hình với API, đừng chỉ nhìn màn hình.** Mỗi lần thấy lạ, chạy
`curl` cho cùng phạm vi. Nó tách được "backend sai" khỏi "frontend không hỏi".

**2. Đổi một biến mỗi lần.** Đổi phạm vi thì đừng đóng cắt; đóng cắt thì giữ
nguyên phạm vi. Trong phiên vừa rồi, "82 sự cố mà danh sách rỗng" nhìn như lỗi
gom cụm, thực tế là lỗi phạm vi — hai thứ đổi cùng lúc nên mất một vòng để tách.

**3. Không kết luận từ sự im lặng.** "Không thấy gì" chỉ có nghĩa khi biết chắc
đã có kích thích trong lúc đang nhìn. Với alarm, kích thích là một thao tác
đóng cắt **và** nhìn thấy dòng đếm nhảy. Dòng đếm đến từ SSE nên nó là bằng
chứng độc lập rằng backend vẫn đang nghe. Đây là bài học đã làm ADR-0007 sai
suốt 9 ngày — xem ADR-0026.

## 5. Chạy tự động

```bash
cd backend
uv run pytest tests/unit/test_alarm_decode.py tests/unit/test_alarm_rules.py \
              tests/unit/test_incident.py tests/unit/test_alarms_api.py -q
uv run pytest -m live tests/integration/test_alarms_live.py -s   # cần DataServer
```

Bộ test offline dùng `tests/fixtures/alarm_bodies.json` (90 body thật) và
`tests/fixtures/alarm_cascade.json` (chuỗi lan truyền đo được 2026-08-13), nên
chạy được không cần DataServer.

## 6. Chưa có, đừng tìm

- **Sequence of Events / lịch sử**: `store/events.py` chưa viết. Đóng ứng dụng
  là mất, chỉ có hiện tại.
- **Ack alarm**: `OAAlarm.Ack*` là bề mặt ghi, đóng theo I1.
- **Chuỗi nhân quả**: `trace`, ADR-0024, chưa viết.
- **Hướng dẫn đã duyệt**: toàn bộ playbook là `draft`.
