"""Application state, in one module so there is one thing to swap.

Routers reach the store through `get_store()` rather than by importing the
object. The difference matters: a name imported at module load is a snapshot,
and the tests that build a store over a temp directory would then be talking to
a different object than the handlers are. Going through a function means the
lookup happens per call, so replacing `deps.store` replaces it everywhere.

This is also the only module that constructs anything at import time. Keeping
that in one place is what lets `app.py` stay a composition root and nothing else.
"""

from __future__ import annotations

from pydantic_ai.models import Model

from blackinterface.agent.harness import model_for
from blackinterface.agent.provider import LLMChoice, choice_from_settings
from blackinterface.agent.session import Conversations
from blackinterface.api.conversations import StoredConversations
from blackinterface.api.source import StationStore
from blackinterface.config import Settings, get_settings
from blackinterface.store.assistant import AssistantRepository
from blackinterface.store.conversations import ConversationRepository
from blackinterface.store.db import Database

settings: Settings = get_settings()
database: Database = Database(settings.db_path)
store: StationStore = StationStore(settings, database)
#: Transcripts survive a restart (ADR-0022 §2). Built over `database` at import
#: like the store, so a test that swaps the database through `use()` gets a
#: conversation store pointing at the same temporary file.
conversations: Conversations = StoredConversations(ConversationRepository(database))

#: Built on first use, not at import. A misconfigured model must not stop the
#: process from starting: `/api/health` has to stay answerable so somebody can
#: see why the assistant is refusing, and the station screens do not need a model
#: at all (I4).
_model: Model | None = None
_model_built = False
#: Set when a test pins a model, so `forget_provider()` cannot undo it.
_provider_pinned = False


def get_store() -> StationStore:
    """The live station store. Read per call — see the module docstring."""
    return store


def get_database() -> Database:
    return database


def get_conversations() -> Conversations:
    return conversations


def get_assistant_repository() -> AssistantRepository:
    return AssistantRepository(database, settings.secret_key)


def get_settings_for_request() -> Settings:
    """This installation's settings, looked up per call like everything else."""
    return settings


def get_choice() -> LLMChoice:
    """Which model to use: the station's own answer, else the environment.

    This is the only place the precedence lives. `agent/` may not import
    `store/` (ADR-0019 §8), so the merge cannot happen down there, and doing it
    in the settings screen would leave `/api/ask` reading a different source
    than the screen shows.
    """
    stored = get_assistant_repository().get()
    if stored is None or not stored.configured:
        return choice_from_settings(settings)
    return LLMChoice(
        provider=stored.provider,
        base_url=stored.base_url,
        model=stored.model,
        # Falling back to the environment key lets somebody point the station at
        # a different model without re-entering a key that already works.
        api_key=stored.api_key or settings.llm_api_key,
        timeout=stored.timeout,
    )


def get_model() -> Model | None:
    """The model to answer with, or `None` when the assistant is switched off.

    `None` is not an error and not a degraded mode: it means nobody has
    configured a model yet, and `agent/core.py` turns it into "chưa cấu hình" on
    the conversation tab. The station screens never ask for it (I4, I5).
    """
    global _model, _model_built
    if not _model_built:
        _model = model_for(settings, get_choice())
        _model_built = True
    return _model


def get_model_name() -> str:
    """What the answer reports as the source of its wording."""
    choice = get_choice()
    return choice.model if choice.provider != "off" and choice.model else "off"


def forget_provider() -> None:
    """Drop the cached provider so the next question rebuilds it.

    Called when the configuration is saved. Without it, changing the model in
    the interface would appear to work and change nothing until a restart —
    the kind of bug that gets diagnosed as "the AI is ignoring us".
    """
    global _model, _model_built
    if not _provider_pinned:
        _model, _model_built = None, False


def use(
    new_store: StationStore,
    new_database: Database | None = None,
    *,
    model: Model | None = None,
    new_conversations: Conversations | None = None,
) -> None:
    """Point the application at a different store. For tests and for nothing else."""
    global store, database, conversations, _model, _model_built, _provider_pinned
    store = new_store
    if new_database is not None:
        database = new_database
        # Rebuild rather than leave it pointing at the previous file. A test
        # that swaps in a temp database and then reads a transcript would
        # otherwise be reading the developer's own, which is both a wrong test
        # and a surprising way to find out about it.
        conversations = StoredConversations(ConversationRepository(database))
    if model is not None:
        _model = model
        _model_built = True
        _provider_pinned = True
    if new_conversations is not None:
        conversations = new_conversations
