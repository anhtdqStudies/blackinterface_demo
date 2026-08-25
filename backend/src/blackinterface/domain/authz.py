"""Who may ask what (ADR-0016).

Capability is the unit; a role is only a named bundle of capabilities, and one
person may hold several roles. That is what makes the same build serve a large
station with a full shift and an unattended one where a single account does
everything — the difference is which bundles are assigned, not which code runs.

    effective capabilities = union of the roles held

Granularity is *module x verb*, one notch finer than the actor matrix in
`document/@Station_UseCases 1.xlsx`. At module granularity "has C" cannot tell
drafting an operation apart from signing it, and that boundary is the single
most expensive thing to retrofit once Module C exists.

Pure by the rules of this layer: no config, no database, no HTTP. Enforcement
lives at the facet layer in `api/authz.py`, because the agent calls facets
directly and would walk around anything checked in the UI.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum


class Capability(StrEnum):
    """One permission. The letters are the OneATS modules in AGENTS.md."""

    STATION_READ = "station.read"  # A - diagram, state, measurements
    ALARM_READ = "alarm.read"  # B
    ALARM_ACK = "alarm.ack"  # B - acknowledge an alarm
    EVENT_READ = "event.read"  # B - sequence of events
    TREND_READ = "trend.read"  # D
    REPORT_READ = "report.read"  # E
    REPORT_EXPORT = "report.export"  # E - export, send outside
    KNOWLEDGE_READ = "knowledge.read"  # F
    KNOWLEDGE_WRITE = "knowledge.write"  # F - edit the knowledge base
    PROTECTION_READ = "protection.read"  # protection settings, interlock, relay logic
    AGENT_ASK = "agent.ask"  # ask the AI
    #: Choose the language model and hold its key. Deliberately NOT one of the
    #: `model.*` capabilities: those mean the *station* model, and one word doing
    #: two jobs in a permission name is a mistake somebody makes exactly once,
    #: at the worst moment.
    ASSISTANT_CONFIG = "assistant.config"
    CONTROL_DRAFT = "control.draft"  # C - DRAFT an operation ticket
    CONTROL_SIGN = "control.sign"  # C - SIGN an operation ticket
    MODEL_CONNECT = "model.connect"  # connect a DataServer, reload
    MODEL_EDIT = "model.edit"  # templates, overrides (ADR-0015)
    MODEL_PUBLISH = "model.publish"  # freeze a release
    BINDING_READ = "binding.read"  # raw NodeId, Dbpos (ADR-0014 section 8)
    AUDIT_READ = "audit.read"  # who did what
    ACCOUNT_MANAGE = "account.manage"  # manage accounts


class Role(StrEnum):
    """A named bundle. The first five are ATS's own actor names — kept verbatim
    because that is the vocabulary their customers already use."""

    OPERATOR = "operator"
    SUPERVISOR = "supervisor"
    MAINTENANCE = "maintenance"
    PROTECTION = "protection"
    ADMIN = "admin"
    #: The sixth, which ATS's matrix has no actor for: in their world Grid
    #: Designer had already built the model. That is the step this product
    #: automates, so it needs a role of its own (ADR-0015).
    ENGINEER = "engineer"


_OPERATOR = frozenset(
    {
        Capability.STATION_READ,
        Capability.ALARM_READ,
        Capability.ALARM_ACK,
        Capability.EVENT_READ,
        Capability.TREND_READ,
        Capability.REPORT_READ,
        Capability.REPORT_EXPORT,
        Capability.KNOWLEDGE_READ,
        Capability.AGENT_ASK,
        Capability.CONTROL_DRAFT,
    }
)

#: Role -> what it grants. The whole permission model is this table plus the
#: union rule; adding a role is adding a row, not editing a facet.
ROLES: dict[Role, frozenset[Capability]] = {
    Role.OPERATOR: _OPERATOR,
    Role.SUPERVISOR: _OPERATOR | {Capability.CONTROL_SIGN, Capability.AUDIT_READ},
    # No control at all, per ATS's matrix (A B D F).
    Role.MAINTENANCE: frozenset(
        {
            Capability.STATION_READ,
            Capability.ALARM_READ,
            Capability.EVENT_READ,
            Capability.TREND_READ,
            Capability.KNOWLEDGE_READ,
            Capability.AGENT_ASK,
        }
    ),
    Role.PROTECTION: frozenset(
        {
            Capability.ALARM_READ,
            Capability.EVENT_READ,
            Capability.KNOWLEDGE_READ,
            Capability.AGENT_ASK,
            Capability.PROTECTION_READ,
            Capability.BINDING_READ,
            Capability.CONTROL_DRAFT,
        }
    ),
    # Grants rights to others; holds none of the operational ones itself.
    Role.ADMIN: frozenset(
        {
            Capability.KNOWLEDGE_READ,
            Capability.KNOWLEDGE_WRITE,
            Capability.AGENT_ASK,
            Capability.AUDIT_READ,
            Capability.ACCOUNT_MANAGE,
            # Whoever holds the accounts holds the outbound API key too: both are
            # "what this installation trusts", and neither is an operating right.
            Capability.ASSISTANT_CONFIG,
        }
    ),
    Role.ENGINEER: frozenset(
        {
            Capability.STATION_READ,
            Capability.ALARM_READ,
            Capability.KNOWLEDGE_READ,
            Capability.AGENT_ASK,
            Capability.MODEL_CONNECT,
            Capability.MODEL_EDIT,
            Capability.MODEL_PUBLISH,
            Capability.BINDING_READ,
            # The engineer is who commissions the installation, and choosing the
            # model is part of commissioning it. At a station with no admin on
            # site, requiring one would leave the assistant switched off.
            Capability.ASSISTANT_CONFIG,
        }
    ),
}


class RoleConflictError(ValueError):
    """A combination of roles that breaks a separation-of-duty rule.

    A plain `ValueError` subclass rather than a `BlackInterfaceError`: this
    layer states the rule, and the layer that has an HTTP status decides how to
    report it.
    """


def check_role_set(roles: Iterable[Role]) -> None:
    """Reject combinations no single account may hold, whatever the station size.

    One rule today, and it is the one worth spelling out: whoever can change the
    model an operation is reasoned about must not also be the one who signs that
    operation off. Defining "correct" and then marking your own work destroys the
    meaning of both — so `engineer` cannot be combined with a role granting
    `control.sign`, not even at a station with one person (ADR-0016 section 3).

    Note this is stricter than the union rule on its own. Without it, holding
    `engineer` + `supervisor` would quietly produce exactly the account the ADR
    forbids.
    """
    held = set(roles)
    if Role.ENGINEER not in held:
        return
    signers = sorted(r for r in held if Capability.CONTROL_SIGN in ROLES[r])
    if signers:
        raise RoleConflictError(
            f"role 'engineer' cannot be combined with {signers}: whoever edits the model "
            f"must not sign operations that rely on it (ADR-0016 section 3)"
        )


def capabilities_for(roles: Iterable[Role]) -> frozenset[Capability]:
    """The union of what these roles grant. Empty set for no roles — deny by default."""
    held = list(roles)
    check_role_set(held)
    return frozenset[Capability]().union(*(ROLES[r] for r in held)) if held else frozenset()


@dataclass(frozen=True)
class Principal:
    """Who is calling, and what they may therefore do.

    `capabilities` is derived from `roles` when the principal is built, never
    stored independently: two fields that can disagree about the same fact is
    how a permission model rots.

    In this layer because it is plain data about a person, and because both the
    account store and the HTTP gate need it — putting it in either one would
    make the other import it sideways.
    """

    user: str
    display_name: str = ""
    roles: tuple[Role, ...] = ()
    capabilities: frozenset[Capability] = field(default_factory=frozenset)

    @property
    def is_anonymous(self) -> bool:
        """Nobody is signed in. Distinct from "signed in with no permissions":
        one needs a login screen, the other needs an administrator."""
        return not self.user

    def can(self, capability: Capability) -> bool:
        return capability in self.capabilities


def build_principal(user: str, roles: Iterable[Role], display_name: str = "") -> Principal:
    held = tuple(roles)
    return Principal(
        user=user,
        display_name=display_name or user,
        roles=held,
        capabilities=capabilities_for(held),
    )


#: Nobody. Every capability check fails against it, which is the point: an
#: unrecognised caller is refused rather than quietly given a default role.
ANONYMOUS = Principal(user="")


def parse_roles(value: str) -> tuple[Role, ...]:
    """Parse `"operator,maintenance"` into roles, in the order written.

    Comma-separated on purpose: the one-person-several-roles rule is exercised
    from the first day rather than discovered to be broken when a login screen
    finally arrives.
    """
    names = [part.strip() for part in value.split(",") if part.strip()]
    roles: list[Role] = []
    for name in names:
        try:
            role = Role(name)
        except ValueError:
            known = ", ".join(sorted(r.value for r in Role))
            raise ValueError(f"unknown role {name!r}; known roles are: {known}") from None
        if role not in roles:
            roles.append(role)
    check_role_set(roles)
    return tuple(roles)
