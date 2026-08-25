"""One place that knows how this installation is configured.

Every setting is a `BI_*` environment variable, optionally from a `.env` file
next to the working directory. Nothing else in the codebase reads `os.environ`
directly — if you need a knob, add it here so it shows up in one list.

`domain/` must NOT import this module: the domain layer is pure and takes its
inputs as arguments (AGENTS.md I6). The architecture test enforces that.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

#: <repo>/backend/src/blackinterface/config.py -> <repo>
REPO_ROOT = Path(__file__).resolve().parents[3]

SourceKind = Literal["fixture", "opcua"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BI_", env_file=".env", extra="ignore")

    # ---- where the station model comes from
    source: SourceKind = "fixture"
    fixture: Path = REPO_ROOT / "backend" / "tests" / "fixtures" / "sas_tree.json"

    # ---- OneATS DataServer (READ-ONLY, AGENTS.md I1)
    opcua_url: str = "opc.tcp://127.0.0.1:48050"
    opcua_user: str | None = None
    opcua_password: str | None = None
    opcua_timeout: float = 30.0

    # ---- realtime
    #: Hold a subscription open on the active source's measured points, so the
    #: screen follows the station instead of the last browse. Off makes every
    #: model a still photograph refreshed only by /api/reload.
    realtime: bool = True
    #: OPC UA publishing interval. The floor on how stale a position can be;
    #: the server batches its notifications into this window.
    opcua_publish_ms: float = 500.0

    # ---- measurements (ADR-0012)
    #: Override every measurand's own deadband with this percentage. Left unset
    #: on purpose: one percentage cannot serve both power and frequency, so the
    #: per-quantity defaults in `domain/measurement.py` are the sane answer and
    #: this exists only for an installation that has measured better ones.
    measurement_deadband_pct: float | None = None
    #: Slowest rate at which a measurement pulse reaches open streams. Trailing
    #: edge, so the last reading of a burst always arrives — see `throttle.py`.
    measurement_throttle_ms: float = 1000.0

    # ---- who is using this installation (ADR-0016, ADR-0017)
    #: `session` — identity comes from signing in; accounts live in SQLite.
    #: `env`     — no login at all; the whole process runs as `BI_ROLE`. For
    #:             development and for automated checks. Never at a station:
    #:             it hands the same permissions to anyone who can reach the port.
    auth: Literal["session", "env"] = "session"

    #: Only read when `auth="env"`. Comma separated, because one person holding
    #: several roles is the normal case at a lightly-manned station:
    #:     BI_ROLE=operator,maintenance
    role: str = "operator"
    user: str = "local"

    #: How long a sign-in lasts. A shift plus a margin — long enough not to
    #: interrupt handover, short enough that a forgotten browser stops working.
    session_hours: float = 12.0
    session_cookie: str = "bi_session"
    #: Set true behind HTTPS. Left false because a station install is plain HTTP
    #: on the local network today, and a Secure cookie there is simply never sent
    #: — which looks like a broken login rather than a security setting.
    cookie_secure: bool = False

    #: Create one account per role on a database that has none, so a fresh
    #: install can be signed in to. See `api/accounts.py` for the list.
    seed_accounts: bool = True
    #: The password those accounts get. Known, therefore not a secret — the app
    #: says so at startup for every account that still has it.
    seed_password: str = "blackinterface"

    # ---- the language model (ADR-0019)
    #: `off`    — no model at all. Questions are still answered, deterministically
    #:            and from the same tools; only the phrasing is a template. This
    #:            is the default because I4 requires the product to work without
    #:            a model, and a default that needs a key would make that claim
    #:            untested on every machine that has one.
    #: `openai` — any endpoint speaking the OpenAI chat-completions API. That is
    #:            OpenRouter while developing and Ollama at the station, which is
    #:            the whole reason this is one setting rather than two backends.
    #: These four are the *fallback*. Once somebody sets the assistant up through
    #: the interface, the row in `assistant_config` wins — the station's own
    #: answer should beat the machine's default, not the other way round. They
    #: stay because CI and a developer's laptop have no interface to fill in.
    llm: Literal["off", "openai"] = "off"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    #: The model this product is developed *and* deployed on (ADR-0021 §7).
    #: Deliberately the same in both places: developing on something larger and
    #: swapping at commissioning is how a harness that works all through
    #: development gets lost at step four on the day it matters.
    llm_model: str = "qwen/qwen3.6-27b"
    llm_api_key: str | None = None
    #: Generous: a local model on station hardware is slow to first token, and
    #: the stream is already showing progress by then.
    llm_timeout: float = 120.0
    #: OpenRouter providers allowed to serve `llm_model`, best first, comma
    #: separated. Empty lets OpenRouter choose — fine on a laptop, **not** fine
    #: for the eval suite: one model id routes to several providers, each with
    #: its own sampling defaults and tool-call parser, so an unpinned run is
    #: green today and red tomorrow with no code change (ADR-0021 §7).
    llm_provider_order: str = ""

    # ---- ngân sách một lượt hội thoại (ADR-0021 §5)
    #:
    #: Đặt theo **hồ sơ máy trạm**, không theo máy dev: RTX 5090 32GB, Qwen 27B
    #: Q4 ≈ 17GB trọng số, còn ~12GB KV ≈ 40-60k token dùng được. Máy dev qua API
    #: có thừa chỗ, và đó chính là lý do phải đặt trần ở đây — nếu không, cái
    #: chạy được suốt kỳ phát triển sẽ không chạy được ở trạm.
    #:
    #: Chừa biên cho Q4: đo được là 40-60k, nhận 24k. Phần dư là chỗ cho lượng
    #: tử hoá làm mô hình nhớ kém đi, thứ không test từ xa được.
    llm_max_turn_tokens: int = 24_000
    #: Thay `MAX_STEPS = 6` cứng của ADR-0020. Sáu là hai `resolve` + hai
    #: `summary` cộng chỗ hồi lại sau một lần bị từ chối; mười cho câu nhiều
    #: bước thật mà vẫn chặn được vòng lặp lạc đề.
    llm_max_tool_calls: int = 10
    llm_max_requests: int = 12
    #: Câu trả lời tối đa năm câu (xem `agent/harness.py` SYSTEM). Trần này là
    #: cái chặn một mô hình quyết định viết luận văn.
    llm_max_output_tokens: int = 1_200
    #: Đếm token **trước** khi gửi, để một lượt vượt trần hỏng ở đây chứ không
    #: hỏng ở đầu kia sau khi đã trả tiền.
    #:
    #: **Mặc định TẮT, và đó là một quyết định chứ không phải quên bật.** Không
    #: phải model nào cũng đếm trước được — `FunctionModel` ném thẳng
    #: `Token counting ahead of the request is not supported`, và một endpoint
    #: OpenAI-compatible bất kỳ có thể cũng vậy. Bật nó lên khi chưa biết endpoint
    #: có đỡ được không là đánh đổi một tối ưu lấy nguy cơ *mọi* câu hỏi đều hỏng.
    #: `llm_max_turn_tokens` vẫn chặn sau khi gửi, và đó mới là cái giữ ngân sách.
    #: Bật ở trạm sau khi đã thử thật với vLLM.
    llm_count_tokens_before_request: bool = False
    #: Bao nhiêu lượt trước được kể lại cho mô hình (ADR-0022 §1).
    #:
    #: Chỉ **văn xuôi** — không tool call, không số đo, không evidence. Nhỏ có
    #: chủ ý: câu trả lời đến từ tool chứ không từ transcript, và lịch sử càng
    #: dài thì càng mời mô hình trả lời bằng trí nhớ thay vì bằng số của phút
    #: này. `0` tắt hẳn trí nhớ, và tắt nó là một cách chẩn đoán hợp lệ khi nghi
    #: mô hình đang bám vào câu cũ.
    llm_history_turns: int = 4

    #: Encrypts the API key stored in SQLite. Random, not a chosen password —
    #: see `store/secrets.py`, which also spells out what this does not protect
    #: against. Unset means the key cannot be stored through the interface;
    #: `BI_LLM_API_KEY` still works, so a developer is never blocked by it.
    secret_key: str = ""

    # ---- local storage
    data_dir: Path = REPO_ROOT / "data"
    db_name: str = "blackinterface.sqlite"

    # ---- logging
    log_level: str = "INFO"
    log_json: bool = False  # True in production; human-readable while developing
    #: Level for asyncua's own loggers, which are noisy in a way ours are not:
    #: it reports every publish at INFO, and with `opcua_publish_ms=500` on a
    #: station whose analog points never sit still that is two multi-kilobyte
    #: lines a second. At the default WARNING the link's failures still show and
    #: its routine breathing does not. Raise it to INFO or DEBUG to watch the
    #: protocol; prefer sending it to `log_opcua_file` when you do.
    log_opcua_level: str = "WARNING"
    #: Send everything asyncua says to this file instead of the console. Useful
    #: exactly when `log_opcua_level` is loud: the protocol trace is kept, in
    #: full, somewhere it cannot bury the application's own log.
    log_opcua_file: Path | None = None

    # ---- HTTP
    #: The Vite dev server runs on its own port and calls this API cross-origin.
    #: In production the frontend is served from the same origin and this is unused.
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_name

    @property
    def frontend_dir(self) -> Path | None:
        """The built SPA, or None when it has not been built yet.

        There is deliberately no fallback UI: a stale second frontend is worse
        than none (ADR-0009). Build it with `cd frontend && npm run build`.
        """
        dist = REPO_ROOT / "frontend" / "dist"
        return dist if (dist / "index.html").exists() else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
