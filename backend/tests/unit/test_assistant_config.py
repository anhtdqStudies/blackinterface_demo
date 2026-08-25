"""Storing the model's API key, and choosing the model from the interface.

Two things are being asserted, and only one of them is about SQLite:

  1. The key is sealed at rest and **never leaves through the API**. Every path
     out of this feature is checked for it, not just the obvious one.
  2. The environment is a fallback, not a competitor. What the station's
     engineer configured wins, and the screen says which source is in force —
     otherwise saving settings on a machine whose environment overrides them
     looks like a bug in the save button.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.models.openai import OpenAIChatModel

from blackinterface.agent.harness import model_for
from blackinterface.agent.session import InMemoryConversations
from blackinterface.api import app as app_module
from blackinterface.api import authz, deps
from blackinterface.api.source import StationStore
from blackinterface.config import Settings
from blackinterface.domain.authz import Role, build_principal
from blackinterface.store.assistant import AssistantRepository
from blackinterface.store.db import Database
from blackinterface.store.secrets import SecretsUnavailableError, seal, unseal
from tests.conftest import SAS_TREE

SECRET = "test-secret-not-a-real-one"

# ------------------------------------------------------------------- sealing


def test_a_sealed_key_is_not_readable_in_the_file() -> None:
    """The point of the exercise: a copy of the database is not a copy of the key."""
    token = seal("sk-live-abc123", SECRET)
    assert b"sk-live-abc123" not in token
    assert unseal(token, SECRET) == "sk-live-abc123"


def test_the_wrong_secret_opens_nothing_and_does_not_raise() -> None:
    """A rotated BI_SECRET_KEY must look like "no key", not like a crash.

    The honest response to an unreadable key is the same as to a missing one:
    the assistant is off. Raising would take down `/api/assistant/config`, which
    is the one screen somebody would use to fix it.
    """
    token = seal("sk-live-abc123", SECRET)
    assert unseal(token, "a-different-secret") is None
    assert unseal(token, "") is None


def test_storing_a_key_without_a_secret_refuses_rather_than_storing_plaintext() -> None:
    with pytest.raises(SecretsUnavailableError):
        seal("sk-live-abc123", "")


# ---------------------------------------------------------------- repository


@pytest.fixture
def repository(tmp_path_factory: pytest.TempPathFactory) -> AssistantRepository:
    database = Database(tmp_path_factory.mktemp("assistant") / "test.sqlite")
    database.migrate()
    return AssistantRepository(database, SECRET)


def test_nothing_configured_reads_as_nothing(repository: AssistantRepository) -> None:
    assert repository.get() is None


def test_a_saved_key_comes_back_decrypted(repository: AssistantRepository) -> None:
    saved = repository.save(
        provider="openai",
        base_url="https://openrouter.ai/api/v1",
        model="some/model",
        timeout=60.0,
        actor="engineer",
        api_key="sk-live-abc123",
        keep_key=False,
    )
    assert saved.api_key == "sk-live-abc123"
    assert saved.configured and saved.has_key
    assert saved.updated_by == "engineer"


def test_changing_the_model_keeps_the_key(repository: AssistantRepository) -> None:
    """The screen never receives the key, so it cannot send it back unchanged."""
    repository.save(
        provider="openai",
        base_url="https://openrouter.ai/api/v1",
        model="first/model",
        timeout=60.0,
        actor="engineer",
        api_key="sk-live-abc123",
        keep_key=False,
    )
    changed = repository.save(
        provider="openai",
        base_url="https://openrouter.ai/api/v1",
        model="second/model",
        timeout=60.0,
        actor="engineer",
        api_key=None,
        keep_key=True,
    )
    assert changed.model == "second/model"
    assert changed.api_key == "sk-live-abc123"


def test_an_empty_key_removes_it(repository: AssistantRepository) -> None:
    repository.save(
        provider="openai",
        base_url="u",
        model="m",
        timeout=60.0,
        actor="e",
        api_key="sk-live-abc123",
        keep_key=False,
    )
    cleared = repository.save(
        provider="openai",
        base_url="u",
        model="m",
        timeout=60.0,
        actor="e",
        api_key="",
        keep_key=False,
    )
    assert cleared.api_key is None


def test_saving_forgets_that_it_ever_worked(repository: AssistantRepository) -> None:
    """`verified_at` is about *these* settings. Carrying it across a change
    would show a green tick for an endpoint nobody has reached."""
    repository.save(
        provider="openai",
        base_url="u",
        model="m",
        timeout=60.0,
        actor="e",
        api_key="k",
        keep_key=False,
    )
    repository.mark_verified()
    verified = repository.get()
    assert verified is not None and verified.verified_at

    repository.save(
        provider="openai",
        base_url="u",
        model="other",
        timeout=60.0,
        actor="e",
        api_key=None,
        keep_key=True,
    )
    after = repository.get()
    assert after is not None and after.verified_at is None


# --------------------------------------------------------------- over HTTP


@pytest.fixture(scope="module")
def wiring(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Database]:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    data_dir = tmp_path_factory.mktemp("assistant-api")
    database = Database(data_dir / "test.sqlite")
    settings = Settings(
        source="fixture",
        fixture=SAS_TREE,
        data_dir=data_dir,
        realtime=False,
        secret_key=SECRET,
    )
    previous = deps.settings
    deps.settings = settings
    deps.use(
        StationStore(settings, database),
        database,
        new_conversations=InMemoryConversations(),
    )
    with TestClient(app_module.app):
        yield database
    deps.settings = previous


@pytest.fixture
def client(wiring: Database) -> Iterator[TestClient]:
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_the_config_endpoint_never_returns_the_key(client: TestClient) -> None:
    """The assertion that matters most in this file.

    Checked against the whole serialised body rather than field by field: a
    field added later that happened to carry the key would pass a field-by-field
    check and fail this one.
    """
    client.put(
        "/api/assistant/config",
        json={
            "provider": "openai",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "some/model",
            "api_key": "sk-live-SECRETVALUE",
        },
    )
    body = client.get("/api/assistant/config")
    assert body.status_code == 200
    assert "sk-live-SECRETVALUE" not in body.text
    assert body.json()["has_key"] is True
    assert body.json()["source"] == "store"


def test_the_stored_choice_beats_the_environment(client: TestClient) -> None:
    client.put(
        "/api/assistant/config",
        json={"provider": "openai", "base_url": "http://local", "model": "station/model"},
    )
    choice = deps.get_choice()
    assert choice.provider == "openai"
    assert choice.model == "station/model"
    assert isinstance(model_for(deps.settings, choice), OpenAIChatModel)


def test_switching_off_falls_back_to_the_environment(client: TestClient) -> None:
    """`off` in the table is not "use the table's blanks" — it is "not configured
    here", and `BI_LLM` is then what is in force. Otherwise a developer with a
    model in their environment could not explain why the station ignored it."""
    client.put("/api/assistant/config", json={"provider": "off"})
    assert deps.get_choice().provider == deps.settings.llm
    assert client.get("/api/assistant/config").json()["source"] == "env"


def test_switching_on_without_a_model_name_is_refused(client: TestClient) -> None:
    response = client.put("/api/assistant/config", json={"provider": "openai", "model": ""})
    assert response.status_code == 400


def test_testing_an_assistant_that_is_off_says_so_rather_than_pretending(
    client: TestClient,
) -> None:
    client.put("/api/assistant/config", json={"provider": "off"})
    body = client.post("/api/assistant/test").json()
    assert body["ok"] is False
    assert body["error"] == "assistant_off"


def test_configuring_the_assistant_needs_the_capability(client: TestClient) -> None:
    """`operator` may ask the assistant but may not choose which model answers.

    Two different rights on purpose (ADR-0016): using a tool and deciding what
    the installation trusts are not the same decision.
    """
    authz.use(build_principal("op", [Role.OPERATOR]))
    try:
        assert client.get("/api/assistant/config").status_code == 403
        assert client.put("/api/assistant/config", json={"provider": "off"}).status_code == 403
    finally:
        authz.use(build_principal("test", [Role.OPERATOR, Role.ENGINEER]))
