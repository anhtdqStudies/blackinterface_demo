"""Which alarms are faults, and which are just the station describing itself.

A table, not a chain of `if`s, and loaded from YAML for the same reason bay
templates are (`templates.py`): every substation has its own point dialect, and
this table will be edited far more often than the code around it.

Why not simply threshold on severity: measured on DEMO_SAS, exactly one active
alarm reaches severity 800, while `ABNORMAL VOLTAGE` sits at 650 and 41 relay
`TimeFail` alarms sit at 360 — all three are real. Severity ranks; it does not
classify (ADR-0027 section 1).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from blackinterface.domain.alarm import AlarmClass

RULES_DIR = Path(__file__).parent / "alarm_rules"


class AlarmRule(BaseModel):
    """One row of the table. First match wins, so order in the file matters."""

    #: Last dotted segment of the point, e.g. `PosSt` in `D03.XCBR1.PosSt`.
    suffixes: tuple[str, ...] = ()
    #: OneATS category, when the rule only applies to one: "Limit Alarm" etc.
    category: str | None = None
    #: Regex against the alarm message, for rules a suffix cannot express.
    message_pattern: str | None = None
    klass: AlarmClass = AlarmClass.UNKNOWN
    note: str = ""

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


class AlarmRuleSet(BaseModel):
    """The table for one station dialect."""

    name: str
    description: str = ""
    rules: list[AlarmRule] = Field(default_factory=list)

    def classify(
        self,
        *,
        point: str,
        category: str = "",
        message: str = "",
        actor: str | None = None,
    ) -> AlarmClass:
        """Classify one alarm. `point` is the dotted path or a point scope ref.

        An operator action outranks everything. If somebody moved this switch,
        it is not a fault however the rest of the table reads — and getting this
        wrong means the demo alarms loudly every time a breaker is thrown on
        purpose (ADR-0027 section 1).
        """
        if actor:
            return AlarmClass.ACTION
        suffix = point.rsplit(".", 1)[-1]
        for rule in self.rules:
            if rule.matches(suffix=suffix, category=category, message=message):
                return rule.klass
        return AlarmClass.UNKNOWN


def load_rule_set(path: Path) -> AlarmRuleSet:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AlarmRuleSet.model_validate(raw)


_cached: AlarmRuleSet | None = None


def default_rule_set() -> AlarmRuleSet:
    """The bundled table. Loaded once; the file does not change at runtime."""
    global _cached
    if _cached is None:
        _cached = load_rule_set(RULES_DIR / "default.yaml")
    return _cached
