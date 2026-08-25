"""Handling guidance, looked up by key — never written by a model (I3).

The shape matters more than the current contents. Guidance is *data* keyed on
`(point suffix | message pattern, category)`, returned as a typed object beside
the evidence. When Module F (Knowledge/RAG, phase 4) arrives it replaces the
**source** of that same field and nothing else moves: not the tool, not the
schema, not the pane. Putting the text in a system prompt instead would mean
rewriting all three.

**Everything bundled today is `draft`.** The station has no written incident
procedure yet (2026-08-13), so these were composed by an agent and reviewed by
nobody with operational authority. `status` travels with the payload and the UI
is required to show it: guidance that has not been approved must not look
identical to guidance that has (ADR-0027 section 3).
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

PLAYBOOK_DIR = Path(__file__).parent / "playbooks"


class PlaybookStatus(StrEnum):
    """How much authority this guidance carries. Shown, never hidden."""

    #: Composed by an agent from the alarm definition. Not operationally reviewed.
    DRAFT = "draft"
    #: Signed off by someone accountable for operating this substation.
    APPROVED = "approved"


class PlaybookStep(BaseModel):
    text: str
    caution: str = ""


class Playbook(BaseModel):
    """Guidance for one kind of alarm."""

    id: str
    title: str
    status: PlaybookStatus = PlaybookStatus.DRAFT
    summary: str = ""
    steps: list[PlaybookStep] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)

    suffixes: tuple[str, ...] = ()
    category: str | None = None
    message_pattern: str | None = None

    def matches(self, *, suffix: str, category: str, message: str) -> bool:
        if self.suffixes and suffix not in self.suffixes:
            return False
        if self.category is not None and self.category != category:
            return False
        if self.message_pattern is not None and not re.search(
            self.message_pattern, message, re.IGNORECASE
        ):
            return False
        return bool(self.suffixes or self.category or self.message_pattern)


class PlaybookRegistry(BaseModel):
    playbooks: list[Playbook] = Field(default_factory=list)

    def find(self, *, point: str, category: str = "", message: str = "") -> Playbook | None:
        """First match wins, or `None`.

        `None` means *we have no guidance for this*, and callers must say exactly
        that. The one thing forbidden is letting a model fill the gap: an
        invented switching procedure reads just as confidently as a real one.
        """
        suffix = point.rsplit(".", 1)[-1]
        for playbook in self.playbooks:
            if playbook.matches(suffix=suffix, category=category, message=message):
                return playbook
        return None


def load_registry(directory: Path | None = None) -> PlaybookRegistry:
    """Load every `*.yaml` in `directory` (default: the bundled playbook dir)."""
    target = directory or PLAYBOOK_DIR
    playbooks: list[Playbook] = []
    for path in sorted(target.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        playbooks.append(Playbook.model_validate(raw))
    return PlaybookRegistry(playbooks=playbooks)


_cached: PlaybookRegistry | None = None


def default_registry() -> PlaybookRegistry:
    global _cached
    if _cached is None:
        _cached = load_registry()
    return _cached
