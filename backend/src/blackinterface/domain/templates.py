"""Bay templates: the mapping from LN instance to electrical position.

A template is NOT a drawing. It says "in a bay of this type, `XSWI1` sits
between busbar 1 and the node above the breaker". Applying it produces a
topology that is correct by construction — see docs/20-domain/bay-templates.md
and ADR-0008.

Templates are YAML in `domain/templates/`, one file per template, loaded once
and cached. They are data, not code, so a new station layout is a new file
rather than a new branch.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from blackinterface.domain.models import BayType, DeviceRole, NodeKind

TEMPLATE_DIR = Path(__file__).parent / "templates"

#: Endpoint references a slot may use besides a node declared in the template.
BUSBAR_REFS = ("BB1", "BB2", "BB9", "BB")
EARTH_REF = "EARTH"


class TemplateNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    kind: NodeKind = NodeKind.INTERNAL
    label: str = ""


class TemplateSlot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ln: str
    role: DeviceRole
    endpoints: tuple[str, str]
    order: int = 0
    side: Literal["center", "left", "right"] = "center"
    required: bool = True


class BayTemplate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: int
    title: str
    bay_type: BayType
    observed_on: tuple[str, ...] = ()
    nodes: tuple[TemplateNode, ...] = ()
    slots: tuple[TemplateSlot, ...] = ()

    @property
    def node_ids(self) -> frozenset[str]:
        return frozenset(n.id for n in self.nodes)

    def slot_for(self, ln: str) -> TemplateSlot | None:
        return next((s for s in self.slots if s.ln == ln), None)

    def validate_refs(self) -> list[str]:
        """Structural self-check: every endpoint resolves to something."""
        known = self.node_ids | frozenset(BUSBAR_REFS) | {EARTH_REF}
        return [
            f"{self.id}: slot {slot.ln} references unknown endpoint {ref!r}"
            for slot in self.slots
            for ref in slot.endpoints
            if ref not in known
        ]


class TemplateRegistry(BaseModel):
    model_config = ConfigDict(frozen=True)

    templates: tuple[BayTemplate, ...] = Field(default=())

    def for_bay_type(self, bay_type: BayType) -> BayTemplate | None:
        return next((t for t in self.templates if t.bay_type is bay_type), None)

    def by_id(self, template_id: str) -> BayTemplate | None:
        return next((t for t in self.templates if t.id == template_id), None)


def load_registry(directory: Path | None = None) -> TemplateRegistry:
    """Load every `*.yaml` in `directory` (default: the bundled template dir)."""
    directory = directory or TEMPLATE_DIR
    templates = []
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        template = BayTemplate.model_validate(raw)
        problems = template.validate_refs()
        if problems:
            raise ValueError(f"{path.name}: " + "; ".join(problems))
        templates.append(template)
    return TemplateRegistry(templates=tuple(templates))


@lru_cache(maxsize=1)
def default_registry() -> TemplateRegistry:
    return load_registry()
