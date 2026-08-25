"""Choosing the language model, and holding its key.

Three endpoints, all behind `assistant.config` (ADR-0016). None of them ever
puts the key in a response body — `AssistantConfigOut` says whether one exists
and nothing more. That is not politeness: a key in a response is a key in the
browser's memory, in a proxy's log and in whatever screenshot gets pasted into a
support chat.

Saving is not the same as working. `POST /api/assistant/test` calls the endpoint
for real and is the only thing that sets `verified_at`, so the screen can tell
"somebody typed this in" from "this reaches a model".
"""

from __future__ import annotations

from fastapi import APIRouter

from blackinterface.agent.harness import model_for
from blackinterface.agent.provider import LLMUnavailableError, probe
from blackinterface.api.authz import CALLER, requires
from blackinterface.api.deps import (
    forget_provider,
    get_assistant_repository,
    get_choice,
    get_settings_for_request,
)
from blackinterface.api.schemas import (
    AssistantConfigIn,
    AssistantConfigOut,
    AssistantProbeOut,
)
from blackinterface.domain.authz import Capability, Principal
from blackinterface.errors import ConfigurationError, InvalidInputError
from blackinterface.logs import get_logger
from blackinterface.store.assistant import AssistantConfig

log = get_logger(__name__)

router = APIRouter()


def _view(stored: AssistantConfig | None) -> AssistantConfigOut:
    """What the screen is allowed to see.

    Falls back to the environment so the screen shows *what is in force*, not
    what happens to be in the table. An engineer looking at a blank form on a
    machine that already answers questions would reasonably conclude the page
    was broken.
    """
    settings = get_settings_for_request()
    can_store = bool(settings.secret_key)
    if stored is None or not stored.configured:
        return AssistantConfigOut(
            provider=settings.llm,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout=settings.llm_timeout,
            has_key=bool(settings.llm_api_key),
            can_store_key=can_store,
            source="env",
        )
    return AssistantConfigOut(
        provider=stored.provider,
        base_url=stored.base_url,
        model=stored.model,
        timeout=stored.timeout,
        has_key=stored.has_key or bool(settings.llm_api_key),
        can_store_key=can_store,
        source="store",
        verified_at=stored.verified_at,
        updated_at=stored.updated_at,
        updated_by=stored.updated_by,
    )


@router.get(
    "/api/assistant/config",
    response_model=AssistantConfigOut,
    dependencies=[requires(Capability.ASSISTANT_CONFIG)],
)
def read_config() -> AssistantConfigOut:
    """The settings in force. Never the key."""
    return _view(get_assistant_repository().get())


@router.put(
    "/api/assistant/config",
    response_model=AssistantConfigOut,
    dependencies=[requires(Capability.ASSISTANT_CONFIG)],
)
def write_config(body: AssistantConfigIn, principal: Principal = CALLER) -> AssistantConfigOut:
    """Save the settings.

    Writes to this installation's own SQLite only. It reaches no OneATS surface
    and is not the write path invariant I1 is about — but it is still a write,
    and it is gated, audited by `updated_by`, and logged without the key.
    """
    # InvalidInputError, not ConfigurationError: this is a form somebody just
    # submitted, so it is a 400 they can fix, not a 500 about how the process
    # was started.
    if body.provider != "off" and not body.model:
        raise InvalidInputError(
            "a model name is required when the assistant is switched on",
            field="model",
        )
    repository = get_assistant_repository()
    stored = repository.save(
        provider=body.provider,
        base_url=body.base_url,
        model=body.model,
        timeout=body.timeout,
        actor=principal.user,
        api_key=body.api_key,
        # Absent means "leave the stored key alone"; "" means "remove it".
        keep_key=body.api_key is None,
    )
    # Otherwise the change appears to save and takes effect only after a restart.
    forget_provider()
    log.info(
        "assistant_configured",
        actor=principal.user,
        provider=body.provider,
        model=body.model,
        key_changed=body.api_key is not None,
    )
    return _view(stored)


@router.post(
    "/api/assistant/test",
    response_model=AssistantProbeOut,
    dependencies=[requires(Capability.ASSISTANT_CONFIG)],
)
async def test_config() -> AssistantProbeOut:
    """Call the model. The only thing that can set `verified_at`."""
    choice = get_choice()
    if choice.provider == "off":
        return AssistantProbeOut(ok=False, provider="off", error="assistant_off")
    try:
        model = model_for(get_settings_for_request(), choice)
        assert model is not None, "provider != off nên model_for phải dựng được"
        reply = await probe(model)
    except (LLMUnavailableError, ConfigurationError) as exc:
        log.warning("assistant_probe_failed", error=exc.message)
        return AssistantProbeOut(ok=False, provider=choice.model, error=exc.message)
    get_assistant_repository().mark_verified()
    return AssistantProbeOut(ok=True, provider=choice.model, reply=reply[:200])
