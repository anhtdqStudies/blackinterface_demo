# backend/ — Python 3.12 + uv

```bash
uv sync                       # cài môi trường (tạo .venv)
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run pytest
uv run pytest -m "not live"   # bỏ test cần DataServer thật
```

Từ gốc repo: `python tools/check.py` chạy tất cả ở trên + kiểm tra ranh giới lớp.

## Ranh giới lớp — cưỡng chế bằng công cụ

`tools/check.py` sẽ fail nếu:
- `domain/` import bất kỳ lớp anh em nào
- `agent/` import `integration/`, `diagram/`, `store/` (phải đi qua `api/`)
- `asyncua` bị import ngoài `integration/`
- source có tham chiếu tới write surface của OneATS (`PosCtl`, `Force`, `Ack*`…)

Ruff cũng chặn `asyncua` qua `flake8-tidy-imports.banned-api` (xem `pyproject.toml`).

## Test

- `tests/unit/` — không cần mạng, chạy trên fixture
- `tests/integration/` — cần DataServer thật, đánh dấu `@pytest.mark.live`

Tạo fixture: `python tools/probe_dataserver.py --dump --out tests/fixtures/sas_tree.json`
