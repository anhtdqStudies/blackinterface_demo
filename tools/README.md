# tools/

Script vận hành và kiểm chứng. Chạy được độc lập, **không** import `blackinterface`.
Tất cả đều **read-only** với DataServer (AGENTS.md I1).

| Script | Dùng khi |
|---|---|
| `check.py` | **Trước khi báo xong bất cứ việc gì.** Kiểm tra layout, ranh giới lớp, read-only, docs, toolchain |
| `verify_dataserver.py` | **Đầu phiên nếu động tới OPC UA.** Xác minh lại sự thật đã đo trong `docs/30-integration/` |
| `probe_dataserver.py` | Thăm dò / dump address space, xem alarm. `--dump` tạo fixture cho test |

```bash
python tools/check.py
python tools/verify_dataserver.py
python tools/probe_dataserver.py --dump --out sas_tree.json
python tools/probe_dataserver.py --alarms
```

`check.py` và `verify_dataserver.py` trả exit code 0/1 — dùng được trong CI sau này.
