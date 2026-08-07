"""The agent, end to end, without a language model (I4).

Every test here runs against `OfflineProvider`, and that is the argument the
module exists to make: if the answers, the scopes, the refusals and the evidence
are all correct with no model in the process, then the model is not on the
correctness path. A test suite that needed an API key to check what a
disconnector is doing would be evidence of the opposite.

The tests that use `ScriptedProvider` are about the *phrasing* seam only — that
prose arrives in pieces, and that a failing model loses the wording and nothing
else.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from blackinterface.agent import brief, core, resolve, tools
from blackinterface.agent.plan import plan
from blackinterface.agent.provider import (
    LLMUnavailableError,
    OfflineProvider,
    Prompt,
    provider_for,
)
from blackinterface.agent.session import Conversation, InMemoryConversations, Turn
from blackinterface.agent.tools.station import RESOLVE, SUMMARY
from blackinterface.api import app as app_module
from blackinterface.api import authz, deps
from blackinterface.api.schemas import AnswerOut, ResolveOut, SummaryOut
from blackinterface.api.source import StationStore
from blackinterface.config import Settings
from blackinterface.domain.authz import Capability, Role, build_principal
from blackinterface.domain.models import StationGraph
from blackinterface.domain.scope import ScopeRef
from blackinterface.errors import ConfigurationError, ForbiddenError, InvalidInputError
from blackinterface.store.db import Database
from tests.conftest import SAS_TREE

# --------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def wiring(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[StationStore, Database]]:
    """A loaded store over a temporary database, wired into `deps`.

    Loaded through the app's own lifespan rather than by reaching into the
    store: the point of these tests is the path a request takes, and a graph
    installed by a back door would not have been through it.
    """
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    data_dir = tmp_path_factory.mktemp("agent-data")
    database = Database(data_dir / "test.sqlite")
    built = StationStore(
        Settings(source="fixture", fixture=SAS_TREE, data_dir=data_dir, realtime=False),
        database,
    )
    deps.use(built, database, provider=OfflineProvider(), new_conversations=InMemoryConversations())
    with TestClient(app_module.app):
        yield built, database


@pytest.fixture
def store(wiring: tuple[StationStore, Database]) -> StationStore:
    return wiring[0]


@pytest.fixture
def ctx(store: StationStore) -> tools.ToolContext:
    return tools.ToolContext(store=store, principal=build_principal("tester", [Role.OPERATOR]))


@pytest.fixture
def conversations() -> InMemoryConversations:
    return InMemoryConversations()


class ScriptedProvider:
    """A model that says exactly what it was told to, or fails on cue."""

    def __init__(self, pieces: tuple[str, ...] = (), fail_after: int | None = None) -> None:
        self.pieces = pieces
        self.fail_after = fail_after
        self.prompts: list[Prompt] = []

    @property
    def name(self) -> str:
        return "openai:scripted"

    @property
    def generated(self) -> bool:
        return True

    async def stream(self, prompt: Prompt) -> AsyncIterator[str]:
        self.prompts.append(prompt)
        for i, piece in enumerate(self.pieces):
            if self.fail_after is not None and i == self.fail_after:
                raise LLMUnavailableError("the endpoint went away")
            yield piece


async def ask(
    question: str,
    ctx: tools.ToolContext,
    conversations: InMemoryConversations,
    *,
    scope: str = "station",
    conversation_id: str | None = None,
    provider: object | None = None,
) -> AnswerOut:
    return await core.answer(
        question,
        scope,
        conversation_id,
        ctx=ctx,
        provider=provider or OfflineProvider(),  # type: ignore[arg-type]
        conversations=conversations,
    )


# ---------------------------------------------------------------- the resolver


def test_evn_number_resolves_to_one_breaker(station: StationGraph) -> None:
    match = resolve.resolve(station, "271")
    assert match.scope is not None
    assert match.scope.ref == "device:D03.XCBR1"
    assert match.scope.tier is resolve.Tier.DESIGNATION


def test_accents_do_not_matter_in_either_direction(station: StationGraph) -> None:
    """OneATS stores "Ben Cat"; an operator types "Bến Cát"."""
    assert resolve.resolve(station, "Bến Cát").scope == resolve.resolve(station, "ben cat").scope
    assert resolve.resolve(station, "Bến Cát").scope is not None


def test_a_name_two_bays_carry_is_reported_as_two(station: StationGraph) -> None:
    """`Lai Uyen` is E01 and E02. Picking one would be the dangerous answer (I8)."""
    match = resolve.resolve(station, "Lai Uyen")
    assert match.ambiguous
    assert {c.ref for c in match.candidates} == {"bay:E01", "bay:E02"}
    assert match.scope is None


def test_a_stronger_tier_wins_outright(station: StationGraph) -> None:
    """`AT1` is a transformer id; nothing weaker may dilute it."""
    match = resolve.resolve(station, "AT1")
    assert match.scope is not None
    assert match.scope.ref == "transformer:AT1"
    assert match.scope.tier is resolve.Tier.ID


def test_a_wellformed_ref_for_something_absent_is_not_a_match(station: StationGraph) -> None:
    assert not resolve.resolve(station, "bay:ZZ99").found
    assert resolve.resolve(station, "bay:D03").scope is not None


def test_a_name_is_found_inside_a_sentence(station: StationGraph) -> None:
    match = resolve.find_in_text(station, "trạng thái của máy cắt 271 thế nào?")
    assert match.scope is not None
    assert match.scope.ref == "device:D03.XCBR1"


def test_nothing_is_invented_for_a_number_the_station_does_not_have(
    station: StationGraph,
) -> None:
    assert not resolve.find_in_text(station, "cho tôi trạng thái 999").found


# -------------------------------------------------------------------- the plan


def test_a_question_naming_nothing_falls_back_to_the_pane() -> None:
    conversation = Conversation(id="c", actor="a", started_at=_now())
    made = plan("tình hình thế nào?", ScopeRef.bay("D03"), conversation)
    assert made.fallback.ref == "bay:D03"
    assert made.fallback_from == "pane"
    assert not made.names_something


def test_a_follow_up_inherits_the_conversation_while_the_pane_stands_still() -> None:
    conversation = Conversation(id="c", actor="a", started_at=_now())
    conversation.turns.append(
        Turn(
            id="1", asked_at=_now(), question="271?", scope="device:D03.XCBR1", asked_from="station"
        )
    )
    made = plan("còn số đo thì sao?", ScopeRef.station(), conversation)
    assert made.fallback.ref == "device:D03.XCBR1"
    assert made.fallback_from == "conversation"


def test_clicking_something_else_beats_what_we_were_talking_about() -> None:
    """The operator's hand is fresher intent than the last answer."""
    conversation = Conversation(id="c", actor="a", started_at=_now())
    conversation.turns.append(
        Turn(
            id="1", asked_at=_now(), question="271?", scope="device:D03.XCBR1", asked_from="station"
        )
    )
    made = plan("còn cái này?", ScopeRef.bay("E01"), conversation)
    assert made.fallback.ref == "bay:E01"
    assert made.fallback_from == "pane"


@pytest.mark.parametrize("question", ["271 thế nào", "trạng thái D03", "BB21?", "D03.XCBR1"])
def test_identifier_shapes_are_recognised(question: str) -> None:
    conversation = Conversation(id="c", actor="a", started_at=_now())
    assert plan(question, ScopeRef.station(), conversation).names_something


@pytest.mark.parametrize("question", ["tình hình thế nào", "có gì bất thường không"])
def test_plain_prose_names_nothing(question: str) -> None:
    conversation = Conversation(id="c", actor="a", started_at=_now())
    assert not plan(question, ScopeRef.station(), conversation).names_something


# ---------------------------------------------------- the registry is read-only


def test_the_registry_holds_exactly_the_two_tools() -> None:
    assert set(tools.TOOLS) == {RESOLVE, SUMMARY}


def test_every_registered_tool_demands_only_a_read() -> None:
    """The gate. Every tool's capability is one that cannot change anything (I1)."""
    for tool in tools.TOOLS.values():
        assert tool.requires in tools.READ_ONLY, tool.name


def test_registering_a_tool_that_could_change_something_is_refused() -> None:
    """The detector, proved to detect.

    A capability list nobody can violate is a list nobody has tested. This asks
    for the exact thing the rule forbids and requires it to be refused — and it
    uses `control.draft`, which is the one that becomes legitimate for *people*
    the day Module C opens, and must still never be legitimate for the agent.
    """
    with pytest.raises(tools.WriteToolError):
        tools.register(
            tools.Tool(
                name="draft_an_operation",
                description="would prepare a switching order",
                requires=Capability.CONTROL_DRAFT,
                run=lambda ctx, args: pytest.fail("must never run"),
            )
        )
    assert "draft_an_operation" not in tools.TOOLS


def test_export_counts_as_changing_the_world() -> None:
    """`report.export` reads, then sends the result off the machine. A person does that."""
    assert Capability.REPORT_EXPORT not in tools.READ_ONLY
    assert Capability.REPORT_READ in tools.READ_ONLY


def test_a_tool_runs_as_the_caller_and_is_refused_like_the_caller(
    store: StationStore,
) -> None:
    """ADR-0016 section 5: the agent borrows permissions, it does not hold any.

    `admin` may talk to the assistant and may not read the station — the exact
    combination that would let a permission model leak through the agent if the
    tools ran as anybody but the caller.
    """
    admin = build_principal("root", [Role.ADMIN])
    assert admin.can(Capability.AGENT_ASK)
    assert not admin.can(Capability.STATION_READ)
    with pytest.raises(ForbiddenError):
        tools.call(SUMMARY, {"scope": "station"}, tools.ToolContext(store=store, principal=admin))


def test_the_catalogue_hides_what_the_caller_cannot_use() -> None:
    assert tools.catalogue(build_principal("root", [Role.ADMIN])) == ()
    assert len(tools.catalogue(build_principal("op", [Role.OPERATOR]))) == 2


def test_an_unknown_tool_is_refused(ctx: tools.ToolContext) -> None:
    with pytest.raises(InvalidInputError):
        tools.call("switch_it_off", {}, ctx)


# ------------------------------------------------------- tools carry evidence


def test_both_tools_return_evidence_naming_their_subject(ctx: tools.ToolContext) -> None:
    found = tools.call(RESOLVE, {"query": "271"}, ctx)
    read = tools.call(SUMMARY, {"scope": "bay:D03"}, ctx)
    assert found.evidence.tool == RESOLVE
    assert found.evidence.subject == "device:D03.XCBR1"
    assert read.evidence.tool == SUMMARY
    assert read.evidence.subject == "bay:D03"


def test_evidence_names_the_person_not_the_agent(ctx: tools.ToolContext) -> None:
    """I3 + ADR-0016 section 5: an answer is traceable to whoever asked for it."""
    read = tools.call(SUMMARY, {"scope": "station"}, ctx)
    assert read.evidence.actor == "tester"


def test_resolve_evidence_pins_the_model_version(ctx: tools.ToolContext) -> None:
    """ "271 is D03's breaker" is true of one model of one station, and says so."""
    found = tools.call(RESOLVE, {"query": "271"}, ctx)
    assert found.evidence.model_version == ctx.store.graph.model_version
    assert found.evidence.source.catalog_snapshot == ctx.store.graph.model_version


# ------------------------------------------------------------ a whole turn


async def test_a_question_naming_a_breaker_is_answered_about_that_breaker(
    ctx: tools.ToolContext, conversations: InMemoryConversations
) -> None:
    answer = await ask("271 đang thế nào?", ctx, conversations)
    assert answer.scope == "device:D03.XCBR1"
    assert isinstance(answer.summary, SummaryOut)
    assert answer.summary.scope == "device:D03.XCBR1"
    assert [record.tool for record in answer.evidence] == [RESOLVE, SUMMARY]


async def test_an_ambiguous_name_reads_nothing_and_asks_back(
    ctx: tools.ToolContext, conversations: InMemoryConversations
) -> None:
    """The important half is `summary is None`: nothing was read about a guess."""
    answer = await ask("Lai Uyen thế nào?", ctx, conversations)
    assert answer.key == brief.KEY_AMBIGUOUS
    assert answer.summary is None
    assert isinstance(answer.resolution, ResolveOut)
    assert answer.resolution.ambiguous
    assert answer.params["count"] == 2
    assert answer.params["query"] == "Lai Uyen", "quote the name back, not the sentence"


async def test_an_unknown_number_is_not_widened_into_a_station_answer(
    ctx: tools.ToolContext, conversations: InMemoryConversations
) -> None:
    """Answering about the station would look like an answer, and would not be one."""
    answer = await ask("cho tôi trạng thái 999", ctx, conversations)
    assert answer.key == brief.KEY_UNKNOWN
    assert answer.summary is None
    assert answer.params["query"] == "999", "quote back the name, not the sentence"


async def test_prose_with_no_name_answers_about_the_pane(
    ctx: tools.ToolContext, conversations: InMemoryConversations
) -> None:
    answer = await ask("tình hình thế nào?", ctx, conversations, scope="bay:D03")
    assert answer.scope == "bay:D03"
    assert answer.key == brief.KEY_SUMMARY


async def test_a_follow_up_stays_on_the_subject(
    ctx: tools.ToolContext, conversations: InMemoryConversations
) -> None:
    first = await ask("271?", ctx, conversations)
    second = await ask(
        "còn số đo thì sao?", ctx, conversations, conversation_id=first.conversation_id
    )
    assert second.conversation_id == first.conversation_id
    assert second.scope == "device:D03.XCBR1"


async def test_an_account_that_may_ask_but_not_look_is_told_which_permission(
    store: StationStore, conversations: InMemoryConversations
) -> None:
    admin = tools.ToolContext(store=store, principal=build_principal("root", [Role.ADMIN]))
    answer = await ask("trạng thái trạm?", admin, conversations)
    assert answer.key == brief.KEY_DENIED
    assert answer.params["missing"] == Capability.STATION_READ.value
    assert answer.evidence == []


async def test_the_offline_answer_is_computed_and_says_so(
    ctx: tools.ToolContext, conversations: InMemoryConversations
) -> None:
    answer = await ask("tình hình thế nào?", ctx, conversations)
    assert answer.provider == "offline"
    assert answer.generated is False
    assert answer.text == ""
    assert answer.key == brief.KEY_SUMMARY
    assert answer.params["devices"] == 80


async def test_an_undetermined_position_survives_into_the_brief(
    ctx: tools.ToolContext,
) -> None:
    """I2 all the way to the wording: nothing rounds UNDETERMINED to open or closed."""
    read = tools.call(SUMMARY, {"scope": "station"}, ctx)
    assert isinstance(read.payload, SummaryOut)
    digest = brief.for_summary(read.payload)
    counted = read.payload.switch_states
    assert digest.params["undetermined"] == counted.get("UNDETERMINED", 0) + counted.get(
        "INTERMEDIATE", 0
    )
    assert "undetermined" in digest.facts


# -------------------------------------------------------------- conversations


def test_a_conversation_belongs_to_the_person_who_opened_it() -> None:
    """Resuming someone else's id starts a fresh one — no error, no leak."""
    kept = InMemoryConversations()
    mine = kept.resume(None, "alice")
    kept.append(mine, Turn(id="1", asked_at=_now(), question="271?", scope="device:D03.XCBR1"))

    theirs = kept.resume(mine.id, "bob")
    assert theirs.id != mine.id
    assert theirs.turns == []
    assert kept.resume(mine.id, "alice").id == mine.id


def test_history_skips_turns_nobody_wrote_prose_for() -> None:
    conversation = Conversation(id="c", actor="a", started_at=_now())
    conversation.turns.append(Turn(id="1", asked_at=_now(), question="a?", answer=""))
    conversation.turns.append(Turn(id="2", asked_at=_now(), question="b?", answer="yes"))
    assert conversation.history() == (("b?", "yes"),)


def test_turns_are_capped() -> None:
    kept = InMemoryConversations(max_turns=3)
    conversation = kept.resume(None, "alice")
    for i in range(10):
        kept.append(conversation, Turn(id=str(i), asked_at=_now(), question=str(i)))
    assert [t.id for t in conversation.turns] == ["7", "8", "9"]


# ------------------------------------------------------------ the phrasing seam


async def test_generated_prose_arrives_in_pieces_and_is_kept_whole(
    ctx: tools.ToolContext, conversations: InMemoryConversations
) -> None:
    model = ScriptedProvider(("Ngăn ", "D03 ", "đang mang điện."))
    pieces = []
    final: AnswerOut | None = None
    async for event in core.run(
        "tình hình D03?",
        "station",
        None,
        ctx=ctx,
        provider=model,  # type: ignore[arg-type]
        conversations=conversations,
    ):
        if event.name == "token":
            pieces.append(event.data.model_dump()["text"])
        if isinstance(event.data, AnswerOut):
            final = event.data
    assert pieces == ["Ngăn ", "D03 ", "đang mang điện."]
    assert final is not None
    assert final.text == "Ngăn D03 đang mang điện."
    assert final.generated is True


async def test_the_model_only_ever_sees_the_brief(
    ctx: tools.ToolContext, conversations: InMemoryConversations
) -> None:
    """It is handed text and returns text. No store, no graph, no tools (I4)."""
    model = ScriptedProvider(("ok",))
    await ask("271?", ctx, conversations, provider=model)
    assert len(model.prompts) == 1
    assert "device:D03.XCBR1" in model.prompts[0].brief
    assert model.prompts[0].question == "271?"


async def test_a_dead_model_loses_the_wording_and_nothing_else(
    ctx: tools.ToolContext, conversations: InMemoryConversations
) -> None:
    """The answer that matters was computed before the model was asked (I4)."""
    model = ScriptedProvider(("Ngăn D03 ", "đang"), fail_after=1)
    answer = await ask("tình hình D03?", ctx, conversations, provider=model)
    assert answer.llm_error
    assert answer.generated is False
    assert answer.text == "", "half a sentence about a substation is worse than none"
    assert answer.key == brief.KEY_SUMMARY
    assert isinstance(answer.summary, SummaryOut)
    assert answer.evidence


def test_the_default_installation_needs_no_model() -> None:
    assert isinstance(provider_for(Settings(data_dir=SAS_TREE.parent)), OfflineProvider)


def test_asking_for_a_model_without_naming_one_fails_loudly() -> None:
    """A misconfigured endpoint must not quietly become the offline provider."""
    with pytest.raises(ConfigurationError):
        provider_for(Settings(llm="openai", llm_model="", data_dir=SAS_TREE.parent))


# ------------------------------------------------------------------ over HTTP


@pytest.fixture
def client(wiring: tuple[StationStore, Database]) -> Iterator[TestClient]:
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_ask_answers_over_http(client: TestClient) -> None:
    body = client.post("/api/ask", json={"question": "271 thế nào?"}).json()
    assert body["scope"] == "device:D03.XCBR1"
    assert body["summary"]["scope"] == "device:D03.XCBR1"
    assert [record["tool"] for record in body["evidence"]] == [RESOLVE, SUMMARY]


def test_the_stream_carries_the_same_answer_as_the_poll(client: TestClient) -> None:
    """One code path, two deliveries — the reasoning behind /api/live and /api/stream."""
    whole = client.post("/api/ask", json={"question": "tình hình D03?"}).json()
    with client.stream("POST", "/api/ask/stream", json={"question": "tình hình D03?"}) as response:
        frames = [line for line in response.iter_lines() if line.startswith("event:")]
    names = [line.removeprefix("event: ") for line in frames]
    assert names[0] == "turn"
    assert names[-1] == "answer"
    assert names.count("evidence") == 2
    assert whole["key"] == brief.KEY_SUMMARY


def test_asking_needs_permission_to_ask(client: TestClient) -> None:
    """The endpoint's own gate, distinct from the per-tool one above."""
    authz.use(build_principal("nobody", []))
    assert client.post("/api/ask", json={"question": "271?"}).status_code == 403


def _now() -> datetime:
    return datetime.now(UTC)
