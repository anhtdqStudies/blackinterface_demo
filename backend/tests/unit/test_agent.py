"""Agent, đầu-cuối, không gọi mô hình thật lần nào.

Sau ADR-0021 lượt hội thoại **cần** một mô hình — sàn template đã bị xoá. Nhưng
"cần một mô hình" không có nghĩa là "cần một API key": `FunctionModel` là một
danh sách quyết định viết sẵn, nên mọi test ở đây vẫn chạy trên một máy không có
key và trong CI. Đó là I4 sau khi thu hẹp: phần lõi vẫn kiểm được bằng máy.

Kịch bản viết sẵn chứ không gọi mô hình thật là cố ý. Thứ đang kiểm là **vòng
lặp làm gì với một quyết định** — từ chối nó, chạy nó, đưa kết quả về — chứ không
phải mô hình quyết định thế nào. Cái sau là việc của eval suite (ADR-0021 §10
tầng 2), chạy riêng, ngoài `check.py`.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel

from blackinterface.agent import core, digest, harness, resolve, tools
from blackinterface.agent.provider import LLMChoice, choice_from_settings
from blackinterface.agent.session import InMemoryConversations, Turn
from blackinterface.agent.tools.registry import Tool, WriteToolError, register
from blackinterface.agent.tools.station import RESOLVE, SUMMARY
from blackinterface.api import app as app_module
from blackinterface.api import authz, deps
from blackinterface.api.schemas import AnswerOut
from blackinterface.api.source import StationStore
from blackinterface.api.summary import build_summary
from blackinterface.config import Settings
from blackinterface.domain.authz import Capability, Role, build_principal
from blackinterface.domain.models import StationGraph
from blackinterface.errors import ConfigurationError
from blackinterface.store.db import Database
from tests.conftest import SAS_TREE

# --------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def wiring(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[StationStore, Database]]:
    """Store đã nạp trên một database tạm, cắm vào `deps`.

    Nạp qua chính lifespan của app chứ không thò tay vào store: thứ các test này
    kiểm là **đường đi của một request**, và một graph cài bằng cửa sau thì chưa
    từng đi qua đường đó.
    """
    if not SAS_TREE.exists():
        pytest.skip(f"thiếu fixture: {SAS_TREE}")
    data_dir = tmp_path_factory.mktemp("agent-data")
    database = Database(data_dir / "test.sqlite")
    built = StationStore(
        Settings(source="fixture", fixture=SAS_TREE, data_dir=data_dir, realtime=False),
        database,
    )
    deps.use(built, database, new_conversations=InMemoryConversations())
    with TestClient(app_module.app):
        yield built, database


@pytest.fixture
def store(wiring: tuple[StationStore, Database]) -> StationStore:
    return wiring[0]


@pytest.fixture
def station(store: StationStore) -> StationGraph:
    return store.graph


@pytest.fixture
def ctx(store: StationStore) -> tools.ToolContext:
    return tools.ToolContext(store=store, principal=build_principal("tester", [Role.OPERATOR]))


@pytest.fixture
def conversations() -> InMemoryConversations:
    return InMemoryConversations()


@pytest.fixture
def settings() -> Settings:
    return Settings()


# ------------------------------------------------------------- mô hình viết sẵn


def says(text: str) -> ModelResponse:
    """Một lượt mô hình trả lời bằng chữ."""
    return ModelResponse(parts=[TextPart(text)])


def wants(name: str, **arguments: object) -> ModelResponse:
    """Một lượt mô hình đòi gọi tool."""
    return ModelResponse(parts=[ToolCallPart(name, dict(arguments))])


class Script:
    """Mô hình có lịch trình cố định: một danh sách quyết định, theo thứ tự.

    Giữ lại `seen` để test khẳng định được **mô hình đã nhìn thấy gì** — đó là
    cách kiểm rằng kết quả tool quay về đúng dạng gọn chứ không phải payload
    đầy đủ (I3, ADR-0021 §5).
    """

    def __init__(self, *steps: ModelResponse) -> None:
        self.script = list(steps)
        self.seen: list[list[ModelMessage]] = []
        self.info: AgentInfo | None = None

    @property
    def model(self) -> FunctionModel:
        return FunctionModel(self._answer, stream_function=self._stream)

    def _answer(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        self.seen.append(list(messages))
        self.info = info
        return self.script.pop(0) if self.script else says("(hết kịch bản)")

    async def _stream(
        self, messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | DeltaToolCalls]:
        """Cùng kịch bản, nhưng chảy từng mẩu.

        Production **stream** (`agent.run_stream_events`), nên test cũng phải
        stream. Một `FunctionModel` chỉ trả nguyên khối sẽ kiểm một đường code
        khác với đường chạy thật, và khung `token` — thứ người trực nhìn thấy
        chữ chạy — sẽ không được kiểm lần nào.
        """
        for part in self._answer(messages, info).parts:
            if isinstance(part, TextPart):
                for word in part.content.split(" "):
                    yield f"{word} "
            elif isinstance(part, ToolCallPart):
                yield {
                    0: DeltaToolCall(
                        name=part.tool_name,
                        json_args=json.dumps(part.args_as_dict()),
                        tool_call_id=part.tool_call_id,
                    )
                }

    def texts(self) -> list[str]:
        """Mọi chữ mô hình từng được đưa, gộp lại — kể cả kết quả tool."""
        out: list[str] = []
        for exchange in self.seen:
            for message in exchange:
                for part in message.parts:
                    content = getattr(part, "content", None)
                    if isinstance(content, str):
                        out.append(content)
        return out


async def ask(
    question: str,
    ctx: tools.ToolContext,
    conversations: InMemoryConversations,
    settings: Settings,
    script: Script | None = None,
    *,
    scope: str = "station",
    conversation_id: str | None = None,
) -> AnswerOut:
    return await core.answer(
        question,
        scope,
        conversation_id,
        ctx=ctx,
        model=script.model if script is not None else None,
        model_name="test" if script is not None else "off",
        settings=settings,
        conversations=conversations,
    )


async def stream_names(
    question: str,
    ctx: tools.ToolContext,
    conversations: InMemoryConversations,
    settings: Settings,
    script: Script,
    *,
    scope: str = "station",
) -> list[str]:
    """Frame names from `core.run`, in order."""
    names: list[str] = []
    async for event in core.run(
        question,
        scope,
        None,
        ctx=ctx,
        model=script.model,
        model_name="test",
        settings=settings,
        conversations=conversations,
    ):
        names.append(event.name)
    return names


# ---------------------------------------------------------------- the resolver


def test_evn_number_resolves_to_one_breaker(station: StationGraph) -> None:
    match = resolve.resolve(station, "271")
    assert match.found and match.scope is not None
    assert match.scope.ref == "device:D03.XCBR1"


def test_accents_do_not_matter_in_either_direction(station: StationGraph) -> None:
    with_accents = resolve.resolve(station, "Lai Uyên")
    without = resolve.resolve(station, "lai uyen")
    assert {c.ref for c in with_accents.candidates} == {c.ref for c in without.candidates}


def test_a_name_two_bays_carry_is_reported_as_two(station: StationGraph) -> None:
    match = resolve.resolve(station, "Lai Uyen")
    assert match.ambiguous
    assert len(match.candidates) == 2


def test_a_wellformed_ref_for_something_absent_is_not_a_match(station: StationGraph) -> None:
    assert not resolve.resolve(station, "bay:NOPE").found


def test_a_name_is_found_inside_a_sentence(station: StationGraph) -> None:
    match = resolve.find_in_text(station, "cho tôi xem 271 với")
    assert match.found and match.scope is not None
    assert match.scope.ref == "device:D03.XCBR1"


def test_nothing_is_invented_for_a_number_the_station_does_not_have(
    station: StationGraph,
) -> None:
    assert not resolve.resolve(station, "999").found


# ------------------------------------------------- bản gọn đưa cho mô hình (I3)


def test_the_digest_is_a_fraction_of_the_payload(store: StationStore) -> None:
    """Lý do `digest.py` tồn tại, kiểm bằng số.

    Đo 2026-08-07: payload `station` là 20.064 token, bản gọn 715. Test này
    không khoá con số đó — nó khoá **bậc độ lớn**, thứ mà một lần thêm field vào
    `ReadingOut` có thể phá mà không ai nhận ra cho tới khi context window vỡ ở
    trạm.
    """
    out = build_summary(store, "station", actor="tester")
    assert len(digest.for_summary(out)) * 5 < len(out.model_dump_json())


def test_the_digest_never_shows_the_model_a_nodeid(store: StationStore) -> None:
    """`source_ref` bị chặn vì I6, không phải vì kích thước."""
    out = build_summary(store, "station", actor="tester")
    text = digest.for_summary(out)
    assert "ns=" not in text
    for reading in out.measurements:
        assert reading.source_ref is None or reading.source_ref not in text


def test_the_digest_carries_no_evidence(store: StationStore) -> None:
    """Evidence do tool sinh và giao diện hiện riêng — mô hình không cần thấy."""
    out = build_summary(store, "station", actor="tester")
    assert out.evidence.called_at.isoformat() not in digest.for_summary(out)


def test_an_unverified_scale_is_never_printed_as_a_unit(store: StationStore) -> None:
    """`Vlin = 221.08` có thể là V hoặc kV. In "221.08 V" cạnh thanh cái 220 kV
    còn tệ hơn không in gì."""
    out = build_summary(store, "station", actor="tester")
    text = digest.for_summary(out)
    if any(r.unit.value == "?" for r in out.measurements):
        assert "(thang?)" in text
        assert "CHƯA biết thang đo" in text


@pytest.mark.anyio
async def test_an_ambiguous_name_is_handed_back_as_a_question(
    ctx: tools.ToolContext, conversations: InMemoryConversations, settings: Settings
) -> None:
    """ "Lai Uyen" là tên của **cả** E01 lẫn E02 trên DEMO_SAS. Bản gọn phải kể cả
    hai và bảo mô hình hỏi lại — chọn hộ một cái là trả lời tự tin về nhầm ngăn."""
    script = Script(wants(RESOLVE, query="Lai Uyen"), says("Có hai ngăn tên đó, anh hỏi cái nào?"))
    answer = await ask("Lai Uyen thế nào?", ctx, conversations, settings, script)

    assert answer.resolution is not None and answer.resolution.ambiguous
    shown = "\n".join(script.texts())
    assert "hỏi người trực chọn" in shown
    assert answer.summary is None, "nhập nhằng thì không đọc gì cả"


# ---------------------------------------------------- danh mục tool và cổng duyệt


def test_the_registry_holds_exactly_the_two_tools() -> None:
    assert set(tools.TOOLS) == {RESOLVE, SUMMARY}


def test_every_registered_tool_today_demands_only_a_read() -> None:
    for tool in tools.TOOLS.values():
        assert tool.requires in tools.READ_ONLY
        assert not tool.requires_approval


def test_a_tool_that_changes_something_without_a_gate_is_refused() -> None:
    """I1 sau ADR-0021 §2: không phải "tool ghi không tồn tại", mà là **không
    có tool tự thực thi**. Thiếu cổng duyệt là hỏng ngay lúc import."""
    with pytest.raises(WriteToolError, match="TỰ THỰC THI"):
        register(
            Tool(
                name="drafts-an-operation",
                description="soạn một thao tác",
                requires=Capability.CONTROL_DRAFT,
                run=lambda ctx: None,
            )
        )
    assert "drafts-an-operation" not in tools.TOOLS


def test_a_tool_that_changes_something_is_allowed_behind_the_gate() -> None:
    """Nửa còn lại của luật, và là nửa mới: khai cổng duyệt thì được đăng ký.

    Đây là chỗ *«Agent soạn phiếu, người ký»* thôi là một khẩu hiệu và thành một
    dòng code test được.
    """
    tool = Tool(
        name="drafts-with-a-gate",
        description="soạn một thao tác, chờ chữ ký",
        requires=Capability.CONTROL_DRAFT,
        run=lambda ctx: None,
        requires_approval=True,
    )
    try:
        register(tool)
        assert tools.TOOLS["drafts-with-a-gate"].requires_approval
    finally:
        tools.TOOLS.pop("drafts-with-a-gate", None)


def test_export_counts_as_changing_the_world() -> None:
    """`report.export` đọc, rồi gửi kết quả ra khỏi máy. Agent soạn báo cáo,
    người gửi."""
    assert Capability.REPORT_EXPORT not in tools.READ_ONLY


def test_the_catalogue_hides_what_the_caller_cannot_use() -> None:
    blind = build_principal("blind", [])
    assert tools.catalogue(blind) == ()
    seeing = build_principal("op", [Role.OPERATOR])
    assert {t.name for t in tools.catalogue(seeing)} == {RESOLVE, SUMMARY}


# ------------------------------------------------------------------- một lượt


@pytest.mark.anyio
async def test_the_model_chooses_the_tools_and_they_run(
    ctx: tools.ToolContext, conversations: InMemoryConversations, settings: Settings
) -> None:
    script = Script(
        wants(RESOLVE, query="271"),
        wants(SUMMARY, scope="device:D03.XCBR1"),
        says("271 đang đóng."),
    )
    answer = await ask("271 thế nào?", ctx, conversations, settings, script)

    assert answer.text == "271 đang đóng."
    assert answer.generated
    assert answer.scope == "device:D03.XCBR1"
    assert [e.tool for e in answer.evidence] == [RESOLVE, SUMMARY]
    assert answer.summary is not None


@pytest.mark.anyio
async def test_stream_emits_structured_payloads_before_the_final_answer(
    ctx: tools.ToolContext, conversations: InMemoryConversations, settings: Settings
) -> None:
    """Giao diện hiện câu tính được trước khi mô hình viết xong — không đợi khung
    `answer`."""
    script = Script(
        wants(RESOLVE, query="271"),
        wants(SUMMARY, scope="device:D03.XCBR1"),
        says("271 đang đóng."),
    )
    names = await stream_names("271 thế nào?", ctx, conversations, settings, script)

    assert names[0] == "turn"
    assert names[-1] == "answer"
    summary_at = names.index("summary")
    answer_at = names.index("answer")
    assert summary_at < answer_at
    assert "resolution" in names
    assert names.index("resolution") < summary_at


@pytest.mark.anyio
async def test_a_scope_the_model_invented_is_refused(
    ctx: tools.ToolContext, conversations: InMemoryConversations, settings: Settings
) -> None:
    """Chỗ đáng giá nhất của cả file (I8).

    `bay:E01` **có tồn tại**, nên không tầng nào phía dưới phản đối — đó chính là
    chỗ nguy hiểm: một câu trả lời tự tin về nhầm ngăn nhìn y hệt một câu trả lời
    đúng. Từ chối quay về với mô hình dưới dạng một câu nhắc, và cách sửa đúng là
    hành vi ta muốn.
    """
    script = Script(
        wants(SUMMARY, scope="bay:E01"),  # gõ từ trí nhớ
        wants(RESOLVE, query="E01"),  # bị nhắc, làm lại cho đúng
        wants(SUMMARY, scope="bay:E01"),  # giờ thì hợp lệ
        says("E01 đang có điện."),
    )
    answer = await ask("E01 thế nào?", ctx, conversations, settings, script)

    assert answer.summary is not None, "sau khi resolve thì phải đọc được"
    # Lần đọc bị từ chối không sinh evidence: không có gì được đọc.
    assert [e.tool for e in answer.evidence] == [RESOLVE, SUMMARY]
    assert any("không phải thứ `resolve` đã trả về" in t for t in script.texts())


@pytest.mark.anyio
async def test_the_scope_on_screen_needs_no_resolving(
    ctx: tools.ToolContext, conversations: InMemoryConversations, settings: Settings
) -> None:
    """Người trực đang nhìn nó, nên mô hình không bịa ra nó."""
    script = Script(wants(SUMMARY, scope="station"), says("Trạm bình thường."))
    answer = await ask("thế nào?", ctx, conversations, settings, script, scope="station")
    assert answer.summary is not None
    assert [e.tool for e in answer.evidence] == [SUMMARY]


@pytest.mark.anyio
async def test_a_greeting_is_answered_without_reading_anything(
    ctx: tools.ToolContext, conversations: InMemoryConversations, settings: Settings
) -> None:
    """Lỗi ADR-0021 sinh ra để sửa.

    Trước đây một câu chào không kèm tool call bị coi là thất bại và rơi xuống
    sàn, mà sàn thì vô điều kiện đọc cả trạm — người dùng gõ `hello` và nhận về
    80 thiết bị. Giờ câu chào là một câu trả lời hợp lệ.
    """
    answer = await ask("hello", ctx, conversations, settings, Script(says("Chào anh.")))
    assert answer.text == "Chào anh."
    assert answer.evidence == []
    assert answer.summary is None


@pytest.mark.anyio
async def test_the_model_is_only_shown_tools_the_caller_may_use(
    store: StationStore, conversations: InMemoryConversations, settings: Settings
) -> None:
    """Agent mượn quyền người hỏi và không có quyền riêng (ADR-0016 §5)."""
    blind = tools.ToolContext(store=store, principal=build_principal("blind", []))
    script = Script(says("Tôi không đọc được gì."))
    await ask("271 thế nào?", blind, conversations, settings, script)
    assert script.info is not None
    assert script.info.function_tools == []


@pytest.mark.anyio
async def test_the_model_sees_the_digest_not_the_payload(
    ctx: tools.ToolContext, conversations: InMemoryConversations, settings: Settings
) -> None:
    """I3 bằng cấu trúc: payload đầy đủ đi ra giao diện, bản gọn đi vào mô hình."""
    script = Script(wants(SUMMARY, scope="station"), says("xong"))
    answer = await ask("thế nào?", ctx, conversations, settings, script)

    shown = "\n".join(script.texts())
    assert "ns=" not in shown, "NodeId không bao giờ tới mô hình (I6)"
    assert "raw_value" not in shown
    assert answer.summary is not None, "nhưng payload đầy đủ vẫn ra tới giao diện"
    assert answer.summary.measurements


@pytest.mark.anyio
async def test_a_dead_model_loses_the_wording_and_keeps_the_evidence(
    ctx: tools.ToolContext, conversations: InMemoryConversations, settings: Settings
) -> None:
    class Dies(Script):
        def _answer(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            if self.script:
                return super()._answer(messages, info)
            raise RuntimeError("endpoint biến mất")

    script = Dies(wants(SUMMARY, scope="station"))
    answer = await ask("thế nào?", ctx, conversations, settings, script)

    assert answer.text == "", "nửa câu về một dao đang mở tệ hơn không có câu nào"
    assert answer.llm_error is not None
    assert answer.evidence, "nhưng số đã đọc thì vẫn còn, người trực vẫn xem được"


@pytest.mark.anyio
async def test_a_turn_stops_when_the_budget_runs_out(
    ctx: tools.ToolContext, conversations: InMemoryConversations
) -> None:
    """Hết ngân sách là một kết cục nói ra được, không phải một vòng lặp vô tận."""
    tight = Settings(llm_max_tool_calls=1)
    script = Script(*[wants(SUMMARY, scope="station")] * 5)
    answer = await ask("thế nào?", ctx, conversations, tight, script)
    assert answer.llm_error is not None
    assert "ngân sách" in answer.llm_error


# --------------------------------------------------------- chưa cấu hình mô hình


@pytest.mark.anyio
async def test_with_no_model_the_tab_says_so_instead_of_inventing_one(
    ctx: tools.ToolContext, conversations: InMemoryConversations, settings: Settings
) -> None:
    """I4 sau ADR-0021 §3.

    Không còn template. Cái giữ cho giao diện dùng được khi mô hình chết là I5 —
    frontend gọi thẳng Domain API — chứ không phải một câu trả lời dựng sẵn.
    """
    answer = await ask("271 thế nào?", ctx, conversations, settings, None)
    assert answer.unconfigured
    assert answer.text == ""
    assert not answer.generated
    assert answer.evidence == []


def test_the_default_installation_needs_no_model() -> None:
    assert harness.model_for(Settings(), choice_from_settings(Settings())) is None


def test_asking_for_a_model_without_naming_one_fails_loudly() -> None:
    """Một endpoint đã được yêu cầu mà không dựng nổi tuyệt đối không được lặng
    lẽ thành "tắt"."""
    with pytest.raises(ConfigurationError):
        harness.model_for(Settings(), LLMChoice(provider="openai", model=""))


def test_the_openrouter_provider_is_pinned_when_asked() -> None:
    """Không pin thì eval suite xanh hôm nay, đỏ ngày mai, code không đổi."""
    choice = LLMChoice(provider="openai", model="qwen/qwen3.6-27b", provider_order=("a", "b"))
    body = harness._settings_for(Settings(), choice).get("extra_body")
    assert body == {"provider": {"order": ["a", "b"], "allow_fallbacks": False}}


# -------------------------------------------------------------- conversations


def test_a_conversation_belongs_to_the_person_who_opened_it() -> None:
    store = InMemoryConversations()
    mine = store.resume(None, "an")
    assert store.resume(mine.id, "binh").id != mine.id, "im lặng mở cái mới, không báo lỗi"


def test_history_skips_turns_nobody_wrote_prose_for() -> None:
    store = InMemoryConversations()
    conversation = store.resume(None, "an")
    store.append(conversation, _turn("hỏi 1", ""))
    store.append(conversation, _turn("hỏi 2", "đáp 2"))
    assert conversation.history() == (("hỏi 2", "đáp 2"),)


def _turn(question: str, answer: str) -> Turn:
    from datetime import UTC, datetime

    return Turn(
        id="t",
        asked_at=datetime.now(UTC),
        question=question,
        answer=answer,
        scope="station",
        asked_from="station",
    )


# ------------------------------------------------------------------ over HTTP


@pytest.fixture
def client(wiring: tuple[StationStore, Database]) -> Iterator[TestClient]:
    with TestClient(app_module.app) as made:
        yield made


def test_asking_needs_permission_to_ask(client: TestClient) -> None:
    authz.use(build_principal("nobody", []))
    try:
        response = client.post("/api/ask", json={"question": "thế nào?", "scope": "station"})
    finally:
        authz.use(None)
    assert response.status_code == 403


def test_an_unconfigured_install_answers_rather_than_erroring(client: TestClient) -> None:
    """Chưa cấu hình mô hình không phải một lỗi HTTP: người trực có quyền *hỏi*,
    và câu trả lời là một câu nói rõ chưa cấu hình."""
    authz.use(build_principal("op", [Role.OPERATOR]))
    try:
        response = client.post("/api/ask", json={"question": "thế nào?", "scope": "station"})
    finally:
        authz.use(None)
    assert response.status_code == 200
    assert response.json()["unconfigured"] is True
