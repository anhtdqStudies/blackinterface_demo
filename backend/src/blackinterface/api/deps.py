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

from blackinterface.agent.provider import LLMProvider, provider_for
from blackinterface.agent.session import Conversations, InMemoryConversations
from blackinterface.api.source import StationStore
from blackinterface.config import Settings, get_settings
from blackinterface.store.db import Database

settings: Settings = get_settings()
database: Database = Database(settings.db_path)
store: StationStore = StationStore(settings, database)
conversations: Conversations = InMemoryConversations()

#: Built on first use, not at import. A misconfigured `BI_LLM` must not stop the
#: process from starting: `/api/health` has to stay answerable so somebody can
#: see why the assistant is refusing, and the station screens do not need a model
#: at all (I4).
_provider: LLMProvider | None = None


def get_store() -> StationStore:
    """The live station store. Read per call — see the module docstring."""
    return store


def get_database() -> Database:
    return database


def get_conversations() -> Conversations:
    return conversations


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = provider_for(settings)
    return _provider


def use(
    new_store: StationStore,
    new_database: Database | None = None,
    *,
    provider: LLMProvider | None = None,
    new_conversations: Conversations | None = None,
) -> None:
    """Point the application at a different store. For tests and for nothing else."""
    global store, database, conversations, _provider
    store = new_store
    if new_database is not None:
        database = new_database
    if provider is not None:
        _provider = provider
    if new_conversations is not None:
        conversations = new_conversations
