"""The language model, behind an interface thin enough to do without.

One method, one direction: a prompt goes in, text comes out in pieces. That is
the entire surface, and it is small on purpose — everything a language model
could get *wrong* about a substation has already been decided by the time this
is called. The tools have run, the numbers are fixed, the evidence is built.
What is left is phrasing (I4, ADR-0005).

Two implementations, and the first is the important one:

  `OfflineProvider`   no model at all. The answer is still computed, still
                      carries evidence, and is still correct; only the prose is
                      a template the frontend renders. This is the default, so
                      "the product works when the model is dead" is exercised on
                      every developer machine and in every test rather than
                      being an aspiration in an ADR.

  `OpenAIProvider`    any endpoint speaking the OpenAI chat-completions API.
                      OpenRouter while developing, Ollama at the station
                      (AGENTS.md section 3). One implementation covers both
                      because the difference between them is a base URL.

The station endpoint is reached over plain HTTP rather than through a vendor
SDK. The call is one POST and a line-oriented stream; a dependency that has to
be updated in an air-gapped installation to fix a bug in a wrapper around that
is a liability, not a convenience.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from blackinterface.config import Settings
from blackinterface.errors import BlackInterfaceError, ConfigurationError
from blackinterface.logs import get_logger

log = get_logger(__name__)


class LLMUnavailableError(BlackInterfaceError):
    """The assistant's model could not be reached or refused the request.

    Deliberately *not* `SourceUnavailableError`. An operator has to be able to
    tell "we have stopped hearing from the station" from "the wording service is
    down" — the first is an event at the substation, the second is a nuisance,
    and the numbers on screen are trustworthy in one case and not the other.
    """

    code = "llm_unavailable"
    http_status = 503


@dataclass(frozen=True)
class Prompt:
    """Everything the model is told. Nothing else reaches it.

    `brief` is the deterministic rendering of what the tools found. The model
    sees the numbers as text and is asked to say them back in the reader's
    language; it is never given a way to fetch more, which is what keeps it off
    the correctness path rather than merely discouraged from it.
    """

    question: str
    brief: str
    #: Earlier turns as (question, answer), oldest first. Bounded by the caller.
    history: tuple[tuple[str, str], ...] = ()


class LLMProvider(Protocol):
    """A source of prose. Implementations must never do anything else."""

    @property
    def name(self) -> str:
        """Reported to the caller so an answer can say where its wording came
        from. Shown in the UI: computed and generated are different claims."""

    @property
    def generated(self) -> bool:
        """True when a model wrote the text, False when it was computed."""

    def stream(self, prompt: Prompt) -> AsyncIterator[str]:
        """Prose, in pieces. Empty for a provider that writes none."""


#: What the model is told about its job. Short, and every line is a constraint
#: this system enforces elsewhere anyway — the prompt is a courtesy, not a
#: control. Anything that would be a problem if the model ignored it is not
#: allowed to live here.
SYSTEM = """You explain the state of an electrical substation to the person operating it.

You are given a BRIEF: numbers a deterministic backend has already computed and
verified. Restate what the brief says, in the language the question was asked in,
in at most four sentences.

Rules:
- Never state a fact the brief does not contain. No estimates, no typical values,
  no equipment the brief does not mention.
- Where the brief says a position is undetermined, say it is undetermined. Do not
  round it to open or closed.
- Do not repeat the evidence block; the interface shows it separately.
- You cannot operate anything. If asked to switch, open, close or reset, say that
  a person has to do it and describe what would be involved.
"""


@dataclass(frozen=True)
class OfflineProvider:
    """No model. The answer is the computed one, and says so."""

    @property
    def name(self) -> str:
        return "offline"

    @property
    def generated(self) -> bool:
        return False

    def stream(self, prompt: Prompt) -> AsyncIterator[str]:
        return _no_prose()


#: An empty async iterator, spelled out rather than short-circuited. The obvious
#: `return; yield` is dead code, and `warn_unreachable` is on for a reason.
_NOTHING: tuple[str, ...] = ()


async def _no_prose() -> AsyncIterator[str]:
    for piece in _NOTHING:
        yield piece


@dataclass(frozen=True)
class OpenAIProvider:
    """An OpenAI-compatible chat-completions endpoint, streamed."""

    base_url: str
    model: str
    api_key: str | None = None
    timeout: float = 120.0
    #: Overridden in tests with a transport that answers without a network.
    client_factory: Any = field(default=None, repr=False)

    @property
    def name(self) -> str:
        return f"openai:{self.model}"

    @property
    def generated(self) -> bool:
        return True

    async def stream(self, prompt: Prompt) -> AsyncIterator[str]:
        body = {
            "model": self.model,
            "stream": True,
            "messages": _messages(prompt),
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        client = (
            self.client_factory()
            if self.client_factory is not None
            else httpx.AsyncClient(timeout=self.timeout)
        )
        try:
            async with (
                client,
                client.stream(
                    "POST",
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    json=body,
                    headers=headers,
                ) as response,
            ):
                if response.status_code >= 400:
                    detail = (await response.aread()).decode("utf-8", "replace")[:400]
                    raise LLMUnavailableError(
                        f"the model endpoint answered {response.status_code}",
                        status=response.status_code,
                        detail_text=detail,
                    )
                async for line in response.aiter_lines():
                    piece = _delta(line)
                    if piece:
                        yield piece
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"cannot reach the model endpoint: {exc}") from exc


def _messages(prompt: Prompt) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM}]
    for question, answer in prompt.history:
        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": answer})
    messages.append({"role": "user", "content": f"{prompt.question}\n\nBRIEF:\n{prompt.brief}"})
    return messages


def _delta(line: str) -> str:
    """One SSE line of an OpenAI stream -> the text it carries, or "".

    Tolerant by design. Keepalives, comments and the `[DONE]` sentinel are all
    normal traffic, and a chunk that does not parse is worth skipping rather
    than failing an answer over: the deterministic part is already correct and
    losing one token of wording is not a reason to lose the whole reply.
    """
    if not line.startswith("data:"):
        return ""
    payload = line[len("data:") :].strip()
    if not payload or payload == "[DONE]":
        return ""
    try:
        chunk = json.loads(payload)
        choices = chunk.get("choices") or []
        content = choices[0].get("delta", {}).get("content") if choices else None
    except (ValueError, AttributeError, IndexError, TypeError):
        log.debug("unparseable chunk from the model endpoint", line=line[:120])
        return ""
    return content if isinstance(content, str) else ""


def provider_for(settings: Settings) -> LLMProvider:
    """The provider this installation is configured for.

    Misconfiguration fails here, loudly. An endpoint that was asked for and
    cannot be built must not quietly become the offline provider: the answers
    would keep arriving, look ordinary, and never be the ones that were paid for.
    """
    if settings.llm == "off":
        return OfflineProvider()
    if not settings.llm_model:
        raise ConfigurationError("BI_LLM=openai needs BI_LLM_MODEL", setting="BI_LLM_MODEL")
    return OpenAIProvider(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout,
    )
