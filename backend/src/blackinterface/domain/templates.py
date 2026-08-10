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
    """One logical node's electrical position within a bay.

    `aliases` exist because two measured projects number the same physical
    device differently: DEMO_SAS calls the busbar-1 earth switch `XSWI11`,
    T220PHOCAO calls it `XSWI15` after its EVN designation `-15`. Same
    apparatus, same terminals, so it is one slot with two spellings rather
    than two templates. See docs/30-integration/oneats-dataserver.md §2.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ln: str
    role: DeviceRole
    endpoints: tuple[str, str]
    order: int = 0
    side: Literal["center", "left", "right"] = "center"
    required: bool = True
    aliases: tuple[str, ...] = ()

    @property
    def names(self) -> tuple[str, ...]:
        """Every spelling this slot answers to, canonical one first."""
        return (self.ln, *self.aliases)


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
        return next((s for s in self.slots if ln in s.names), None)

    def validate_refs(self) -> list[str]:
        """Structural self-check: every endpoint resolves, every name is unique."""
        known = self.node_ids | frozenset(BUSBAR_REFS) | {EARTH_REF}
        problems = [
            f"{self.id}: slot {slot.ln} references unknown endpoint {ref!r}"
            for slot in self.slots
            for ref in slot.endpoints
            if ref not in known
        ]
        # An LN claimed by two slots would place one device at two positions,
        # and which one won would depend on file order.
        seen: dict[str, str] = {}
        for slot in self.slots:
            for name in slot.names:
                if name in seen:
                    problems.append(
                        f"{self.id}: {name} is claimed by both {seen[name]} and {slot.ln}"
                    )
                seen[name] = slot.ln
        return problems


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
