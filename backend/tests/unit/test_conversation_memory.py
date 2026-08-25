"""Trí nhớ hội thoại (ADR-0022) — nhớ được lời, và **chỉ** lời.

Ba nhóm, và nhóm thứ hai là nhóm đáng đọc nếu chỉ đọc một nhóm:

  1. Transcript sống qua restart, và không rò sang tài khoản khác.
  2. **Mô hình thấy văn xuôi, không thấy số.** Đây là chỗ ADR-0022 §1 hoặc đứng
     hoặc đổ. Một test khẳng định lịch sử tới được mô hình; một test khác khẳng
     định số đo của lượt trước **không** tới. Cái thứ hai là cái giữ I2: một
     trạm đổi trạng thái trong lúc người ta đang nói về nó, và một mô hình còn
     nhìn thấy `CLOSED` của bốn lượt trước có đường trả lời rẻ hơn là gọi tool.
  3. `ctx.seen` không thừa kế: nhớ để **hiểu câu hỏi**, không phải để trả lời.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from blackinterface.agent import core, harness, tools
from blackinterface.agent.session import (
    Conversation,
    InMemoryConversations,
    Turn,
    title_for,
)
from blackinterface.agent.tools.station import RESOLVE, SUMMARY
from blackinterface.api import app as app_module
from blackinterface.api import authz, deps
from blackinterface.api.conversations import StoredConversations
from blackinterface.api.source import StationStore
from blackinterface.config import Settings
from blackinterface.domain.authz import Role, build_principal
from blackinterface.store.conversations import ConversationRepository, TurnRow
from blackinterface.store.db import Database
from tests.conftest import SAS_TREE
from tests.unit.test_agent import Script, says, wants

NOW = datetime(2026, 8, 10, 9, 0, tzinfo=UTC)


def a_turn(n: int, *, answer: str = "", scope: str = "") -> Turn:
    return Turn(
        id=f"t{n}",
        asked_at=NOW + timedelta(minutes=n),
        question=f"câu hỏi {n}",
        answer=answer,
        scope=scope,
        asked_from="station",
    )


def a_row(n: int, *, answer: str = "", scope: str = "") -> TurnRow:
    turn = a_turn(n, answer=answer, scope=scope)
    return TurnRow(
        turn_id=turn.id,
        asked_at=turn.asked_at.isoformat(),
        question=turn.question,
        answer=turn.answer,
        scope=turn.scope,
        asked_from=turn.asked_from,
    )


# ============================================================ 1. trên đĩa


@pytest.fixture
def db(tmp_path_factory: pytest.TempPathFactory) -> Database:
    database = Database(tmp_path_factory.mktemp("conversations") / "test.sqlite")
    database.migrate()
    return database


@pytest.fixture
def repository(db: Database) -> ConversationRepository:
    return ConversationRepository(db)


def test_a_conversation_outlives_the_process(db: Database) -> None:
    """Lý do tồn tại của migration 005: hỏi tiếp sau khi khởi động lại.

    "Khởi động lại" ở đây là một `Database` mới trên cùng một file — cùng thứ mà
    một tiến trình mới sẽ thấy, và khác hẳn `InMemoryConversations`, thứ mất
    sạch.
    """
    first = StoredConversations(ConversationRepository(db))
    opened = first.resume(None, "truc")
    first.append(opened, a_turn(1, answer="271 đang đóng", scope="device:D03.XCBR1"))

    reborn = StoredConversations(ConversationRepository(Database(db.path)))
    found = reborn.load(opened.id, "truc")

    assert found is not None
    assert [t.question for t in found.turns] == ["câu hỏi 1"]
    assert found.history() == (("câu hỏi 1", "271 đang đóng"),)


def test_resume_brings_the_turns_with_it(db: Database) -> None:
    """`resume()` phải nạp cả lượt cũ.

    Trả về một cái vỏ rỗng thì `history()` rỗng, mô hình mất trí nhớ, và
    **không có gì hỏng** — đúng loại lỗi khó thấy nhất, nên nó có test riêng.
    """
    store = StoredConversations(ConversationRepository(db))
    opened = store.resume(None, "truc")
    store.append(opened, a_turn(1, answer="đã trả lời"))

    again = store.resume(opened.id, "truc")

    assert again.id == opened.id
    assert len(again.turns) == 1


def test_another_account_gets_a_new_thread_not_an_error(db: Database) -> None:
    """Nối vào hội thoại của người khác: im lặng mở cái mới.

    Báo lỗi là xác nhận id đó có thật — một rò rỉ nhỏ về ai đã hỏi gì, lúc nào.
    """
    store = StoredConversations(ConversationRepository(db))
    mine = store.resume(None, "truc")
    store.append(mine, a_turn(1, answer="x"))

    theirs = store.resume(mine.id, "operator")

    assert theirs.id != mine.id
    assert theirs.turns == []
    assert store.load(mine.id, "operator") is None
    assert store.delete(mine.id, "operator") is False
    assert store.load(mine.id, "truc") is not None


def test_the_list_is_per_account(db: Database) -> None:
    store = StoredConversations(ConversationRepository(db))
    for actor, count in (("truc", 2), ("operator", 1)):
        for n in range(count):
            opened = store.resume(None, actor)
            store.append(opened, a_turn(n, answer="x"))

    assert len(store.list("truc")) == 2
    assert len(store.list("operator")) == 1
    assert store.list("nobody") == ()


def test_the_newest_conversation_is_listed_first(db: Database) -> None:
    store = StoredConversations(ConversationRepository(db))
    older = store.resume(None, "truc")
    store.append(older, a_turn(1, answer="x"))
    newer = store.resume(None, "truc")
    store.append(newer, a_turn(9, answer="x"))

    assert [c.id for c in store.list("truc")] == [newer.id, older.id]


def test_the_title_is_the_first_question_and_does_not_drift(db: Database) -> None:
    store = StoredConversations(ConversationRepository(db))
    opened = store.resume(None, "truc")
    store.append(opened, Turn(id="a", asked_at=NOW, question="271 đang thế nào?", answer="x"))
    store.append(opened, Turn(id="b", asked_at=NOW, question="còn số đo thì sao?", answer="y"))

    assert store.list("truc")[0].title == "271 đang thế nào?"


def test_a_long_question_is_cut_and_whitespace_collapsed() -> None:
    assert title_for("  hỏi   nhiều    khoảng trắng ") == "hỏi nhiều khoảng trắng"
    assert len(title_for("x" * 500)) == 80


def test_only_the_last_turns_are_kept(db: Database) -> None:
    """Trần lượt: cái cũ rơi, hội thoại không phình vô hạn."""
    repository = ConversationRepository(db, max_turns=3)
    repository.open("c1", "truc", NOW.isoformat())
    for n in range(6):
        repository.append("c1", "truc", a_row(n, answer="x"))

    kept = [t.question for t in repository.turns("c1", "truc")]
    assert kept == ["câu hỏi 3", "câu hỏi 4", "câu hỏi 5"]


def test_only_the_newest_conversations_are_kept(db: Database) -> None:
    """Trần hội thoại, tính **theo từng tài khoản**.

    Theo tài khoản chứ không toàn cục: một người trực hỏi nhiều không được phép
    đẩy luồng của kỹ sư ra khỏi bộ nhớ.
    """
    repository = ConversationRepository(db, max_conversations=2)
    for n in range(4):
        repository.open(f"c{n}", "truc", (NOW + timedelta(minutes=n)).isoformat())
        repository.append(f"c{n}", "truc", a_row(n, answer="x"))
    repository.open("other", "operator", NOW.isoformat())
    repository.append("other", "operator", a_row(0, answer="x"))

    assert [c.id for c in repository.list("truc")] == ["c3", "c2"]
    assert [c.id for c in repository.list("operator")] == ["other"]


def test_a_turn_cannot_be_appended_to_someone_elses_conversation(
    repository: ConversationRepository,
) -> None:
    """Khoá ở tầng SQL, không phải ở tầng người gọi cẩn thận."""
    repository.open("c1", "truc", NOW.isoformat())
    repository.append("c1", "operator", a_row(1, answer="x"))

    assert repository.turns("c1", "truc") == []


def test_deleting_takes_the_turns_with_it(repository: ConversationRepository) -> None:
    repository.open("c1", "truc", NOW.isoformat())
    repository.append("c1", "truc", a_row(1, answer="x"))

    assert repository.delete("c1", "truc") is True
    assert repository.get("c1", "truc") is None
    rows = repository.db.connection.execute(
        "SELECT COUNT(*) AS n FROM conversation_turns WHERE conversation_id = 'c1'"
    ).fetchone()
    assert rows["n"] == 0


def test_nothing_but_words_is_written(db: Database) -> None:
    """ADR-0022 §2 nói bằng schema: bảng không có chỗ cho một số đo.

    Kiểm bằng cột chứ không bằng nội dung: một cột mới thêm vào sau này để «tiện
    xem lại» sẽ làm test này đỏ, và đó đúng là lúc cần đọc lại ADR.
    """
    columns = {
        row["name"]
        for row in db.connection.execute("PRAGMA table_info(conversation_turns)").fetchall()
    }
    assert columns == {
        "conversation_id",
        "turn_id",
        "asked_at",
        "question",
        "answer",
        "scope",
        "asked_from",
    }


# =========================================== 2. mô hình thấy lời, không thấy số


@pytest.fixture(scope="module")
def wiring(tmp_path_factory: pytest.TempPathFactory) -> Iterator[StationStore]:
    if not SAS_TREE.exists():
        pytest.skip(f"thiếu fixture: {SAS_TREE}")
    data_dir = tmp_path_factory.mktemp("memory-data")
    database = Database(data_dir / "test.sqlite")
    built = StationStore(
        Settings(source="fixture", fixture=SAS_TREE, data_dir=data_dir, realtime=False),
        database,
    )
    deps.use(built, database)
    with TestClient(app_module.app):
        yield built


@pytest.fixture
def store(wiring: StationStore) -> StationStore:
    return wiring


@pytest.fixture
def ctx(store: StationStore) -> tools.ToolContext:
    return tools.ToolContext(store=store, principal=build_principal("truc", [Role.OPERATOR]))


@pytest.fixture
def settings() -> Settings:
    return Settings()


def spoke(question: str, answer: str) -> Turn:
    return Turn(id=f"t-{question}", asked_at=NOW, question=question, answer=answer)


def test_history_is_pairs_of_prose(settings: Settings) -> None:
    conversation = Conversation(id="c", actor="truc", started_at=NOW)
    conversation.turns = [spoke("hỏi 1", "đáp 1"), spoke("hỏi 2", "đáp 2")]

    messages = harness.history(conversation, settings)

    assert [type(m).__name__ for m in messages] == [
        "ModelRequest",
        "ModelResponse",
        "ModelRequest",
        "ModelResponse",
    ]


def test_a_turn_with_no_prose_is_not_replayed(settings: Settings) -> None:
    """Một message assistant rỗng dạy mô hình rằng trả lời rỗng là được."""
    conversation = Conversation(id="c", actor="truc", started_at=NOW)
    conversation.turns = [spoke("hỏi 1", ""), spoke("hỏi 2", "đáp 2")]

    assert len(harness.history(conversation, settings)) == 2


def test_history_is_capped_by_settings() -> None:
    conversation = Conversation(id="c", actor="truc", started_at=NOW)
    conversation.turns = [spoke(f"hỏi {n}", f"đáp {n}") for n in range(10)]

    assert len(harness.history(conversation, Settings(llm_history_turns=2))) == 4
    assert harness.history(conversation, Settings(llm_history_turns=0)) == []


async def test_the_model_is_told_what_was_said_before(
    ctx: tools.ToolContext, settings: Settings
) -> None:
    """Lượt hai: mô hình phải nhìn thấy câu hỏi và câu trả lời của lượt một."""
    conversations = InMemoryConversations()
    first = Script(says("271 đang đóng."))
    opened = await core.answer(
        "271 thế nào?",
        "station",
        None,
        ctx=ctx,
        model=first.model,
        model_name="test",
        settings=settings,
        conversations=conversations,
    )

    second = Script(says("Vẫn thế."))
    await core.answer(
        "còn bây giờ?",
        "station",
        opened.conversation_id,
        ctx=tools.ToolContext(store=ctx.store, principal=ctx.principal),
        model=second.model,
        model_name="test",
        settings=settings,
        conversations=conversations,
    )

    said = second.texts()
    assert any("271 thế nào?" in s for s in said), "câu hỏi cũ phải có trong lịch sử"
    assert any("271 đang đóng." in s for s in said), "câu trả lời cũ phải có trong lịch sử"


async def test_the_model_is_not_told_last_turns_readings(
    ctx: tools.ToolContext, settings: Settings
) -> None:
    """**Chỗ ADR-0022 §1 đứng hoặc đổ.**

    Lượt một đọc thật một ngăn, nên digest của nó có tên đại lượng trong đó.
    Lượt hai không được nhìn thấy digest ấy: một trạm đổi trạng thái trong lúc
    người ta nói về nó, và số của mười phút trước đọc y hệt số của bây giờ.
    """
    conversations = InMemoryConversations()
    first = Script(
        wants(RESOLVE, query="271"), wants(SUMMARY, scope="device:D03.XCBR1"), says("Đã đọc.")
    )
    opened = await core.answer(
        "271 thế nào?",
        "station",
        None,
        ctx=ctx,
        model=first.model,
        model_name="test",
        settings=settings,
        conversations=conversations,
    )
    assert any("D03" in s for s in first.texts()), "lượt một phải thật sự đọc được gì đó"

    second = Script(says("Vâng."))
    await core.answer(
        "thế à?",
        "station",
        opened.conversation_id,
        ctx=tools.ToolContext(store=ctx.store, principal=ctx.principal),
        model=second.model,
        model_name="test",
        settings=settings,
        conversations=conversations,
    )

    replayed = " ".join(second.texts())
    assert "thiết bị đóng cắt:" not in replayed, "digest của lượt trước lọt vào lịch sử"
    assert "(thang?)" not in replayed, "số đo của lượt trước lọt vào lịch sử"


# ================================================= 3. nhớ ≠ được phép trả lời


async def test_a_remembered_scope_still_has_to_be_resolved_again(
    ctx: tools.ToolContext, settings: Settings
) -> None:
    """`ctx.seen` **không** thừa kế từ lịch sử (ADR-0022 §1, hệ quả).

    Mô hình nhớ lượt trước nói về `bay:E01` thì vẫn phải `resolve` lần nữa —
    `bay:E01` có thật, nên không tầng nào phía dưới phản đối, và một câu trả lời
    tự tin về nhầm ngăn trông y hệt một câu đúng.
    """
    conversations = InMemoryConversations()
    first = Script(wants(RESOLVE, query="271"), says("Xong."))
    opened = await core.answer(
        "271 thế nào?",
        "station",
        None,
        ctx=ctx,
        model=first.model,
        model_name="test",
        settings=settings,
        conversations=conversations,
    )

    fresh = tools.ToolContext(store=ctx.store, principal=ctx.principal)
    second = Script(wants(SUMMARY, scope="device:D03.XCBR1"), says("Đành chịu."))
    await core.answer(
        "còn bây giờ?",
        "station",
        opened.conversation_id,
        ctx=fresh,
        model=second.model,
        model_name="test",
        settings=settings,
        conversations=conversations,
    )

    assert fresh.summary is None, "summary chạy được trên một ref chỉ đến từ trí nhớ"
    nudged = second.texts()
    assert any("không phải thứ `resolve` đã trả về" in s for s in nudged), (
        "phải bị `ModelRetry` nhắc gọi resolve trước"
    )


# ================================================================ 4. qua HTTP


@pytest.fixture
def client(wiring: StationStore) -> Iterator[TestClient]:
    """A signed-in operator, and an empty transcript table.

    The wiring is module-scoped, so without the wipe each test would inherit
    whatever the previous one seeded — and a list endpoint asserted against a
    growing pile passes for the wrong reason. The turns go with them by FK
    cascade, which is also this fixture quietly checking that they do.
    """
    deps.get_database().connection.execute("DELETE FROM conversations")
    authz.use(build_principal("truc", [Role.OPERATOR]))
    with TestClient(app_module.app) as made:
        yield made
    authz.use(None)


def _seed(actor: str, question: str) -> str:
    conversations = deps.get_conversations()
    opened = conversations.resume(None, actor)
    conversations.append(opened, Turn(id="t1", asked_at=NOW, question=question, answer="đáp"))
    return opened.id


def test_the_endpoint_lists_only_my_conversations(client: TestClient) -> None:
    mine = _seed("truc", "của tôi")
    _seed("operator", "của người khác")

    body = client.get("/api/conversations").json()

    assert [c["id"] for c in body] == [mine]
    assert body[0]["title"] == "của tôi"
    assert body[0]["turns"] == 1


def test_reading_someone_elses_conversation_is_404_not_403(client: TestClient) -> None:
    """403 xác nhận nó tồn tại. 404 không nói gì cả — và không nói gì là đúng."""
    theirs = _seed("operator", "của người khác")

    assert client.get(f"/api/conversations/{theirs}").status_code == 404
    assert client.delete(f"/api/conversations/{theirs}").status_code == 404


def test_a_reopened_transcript_carries_no_evidence(client: TestClient) -> None:
    """Mở lại thì thấy lời, không thấy số (ADR-0022 §2)."""
    mine = _seed("truc", "271 thế nào?")

    body = client.get(f"/api/conversations/{mine}").json()

    assert body["transcript"][0]["question"] == "271 thế nào?"
    assert "evidence" not in body
    assert "summary" not in str(body.keys())


def test_deleting_returns_what_is_left(client: TestClient) -> None:
    kept = _seed("truc", "giữ lại")
    gone = _seed("truc", "bỏ đi")

    body = client.delete(f"/api/conversations/{gone}").json()

    assert [c["id"] for c in body] == [kept]
