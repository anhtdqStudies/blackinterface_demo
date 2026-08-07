"""The wire format. Every response body the Domain API can produce.

These names are a contract, not an implementation detail: they become the schema
names in `backend/openapi.json`, which becomes `frontend/src/api/schema.d.ts`,
which the frontend compiles against (ADR-0009). Renaming one here renames a type
in the frontend, and `tools/check.py` will say so.

Kept apart from the routers deliberately. A router should read as a list of what
the API offers; a hundred lines of field declarations above the first endpoint
buries that.
"""

from __future__ import annotations

from pydantic import BaseModel

from blackinterface.domain.energization import CrossCheck, Island, LiveState
from blackinterface.domain.evidence import EvidenceRecord
from blackinterface.domain.issue_groups import IssueGroup
from blackinterface.domain.measurement import Quantity, Unit
from blackinterface.domain.models import Quality, Severity, SwitchState


class MeOut(BaseModel):
    """The caller's identity and permissions (ADR-0016, ADR-0017).

    `capabilities` is the field the UI switches on. `roles` is for display and
    for support calls — "which roles is this account holding" is the first
    question when somebody reports a missing button.

    `authenticated=False` means nobody is signed in, which is not an error: it
    is what `/api/me` answers before the login screen has been used.
    """

    user: str
    display_name: str = ""
    roles: list[str]
    capabilities: list[str]
    authenticated: bool = False
    #: `session` — signed in with an account. `env` — identity comes from
    #: `BI_ROLE`, so there is nothing to sign in or out of and the UI hides both.
    auth_mode: str = "session"


class LoginIn(BaseModel):
    username: str
    password: str


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str


class HealthOut(BaseModel):
    ok: bool
    loaded: bool
    source: str
    load_error: str | None = None
    load_seconds: float | None = None
    project_id: int | None = None
    project_name: str | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    opcua_url: str
    created_at: str
    updated_at: str
    has_snapshot: bool
    model_name: str | None
    model_version: str | None
    captured_at: str | None
    snapshot_saved_at: str | None
    active: bool


class ProjectCreateIn(BaseModel):
    name: str
    opcua_url: str


class ProjectLoadOut(BaseModel):
    """Result of creating/opening/refreshing a project.

    `ok=False` means the project exists but its source could not be read —
    the row is kept so the operator can fix the URL or the network and retry.
    """

    project: ProjectOut
    ok: bool
    error: str | None = None


class ValidationIssueOut(BaseModel):
    """A builder issue on the wire, with its UI group (A/B/C)."""

    severity: Severity
    code: str
    message: str
    subject: str | None = None
    group: IssueGroup


class IssuesOut(BaseModel):
    issues: list[ValidationIssueOut]


class StationOut(BaseModel):
    name: str
    model_version: str | None
    captured_at: str | None
    source: str
    voltage_levels: list[str]
    bay_count: int
    device_count: int
    busbar_count: int
    node_count: int
    load_seconds: float | None
    coverage: dict[str, int]
    issues: list[ValidationIssueOut]


class DeviceOut(BaseModel):
    id: str
    ln: str
    role: str
    name: str
    short_name: str
    state: SwitchState
    quality: Quality
    value: float | int | bool | str | None
    source_timestamp: str | None
    source_ref: str | None
    terminals: list[str]


class BayOut(BaseModel):
    id: str
    name: str
    voltage_level: str
    bay_type: str
    template_id: str | None
    device_count: int
    is_live: bool | None
    is_live_quality: Quality
    logical_nodes: list[str]
    issues: list[ValidationIssueOut]


class BayDetailOut(BayOut):
    devices: list[DeviceOut]


class BusbarOut(BaseModel):
    id: str
    name: str
    voltage_level: str
    index: int
    is_live: bool | None
    quality: Quality
    inferred: bool


class EnergizationOut(BaseModel):
    """Which conductors are live, why, and whether OneATS agrees.

    `node_state` is keyed by connectivity node so the drawing can be coloured by
    joining on `RailView.node_id` / `EdgeView.node_id` — geometry and
    energisation stay separate, which is what will let the realtime module push
    a new verdict without re-laying-out the station.
    """

    islands: list[Island]
    node_state: dict[str, LiveState]
    checks: list[CrossCheck]
    issues: list[ValidationIssueOut]
    summary: dict[str, int]


class DeviceLiveOut(BaseModel):
    """A switching device's position, and how much to trust it.

    `value` is the raw Dbpos behind `state`, carried so a panel showing live
    data can still show its provenance — an operator questioning a symbol
    should not have to refetch the bay to see what the DataServer actually
    said (I6).
    """

    state: SwitchState
    quality: Quality
    value: float | int | bool | str | None = None
    source_timestamp: str | None = None


class LinkOut(BaseModel):
    """The state of the subscription itself.

    `connected=False` does not mean the station is down — it means we have
    stopped hearing about it. What is on screen is then the last thing we knew,
    which is worth showing and worth labelling, but is not the present tense.
    """

    revision: int = 0
    realtime: bool  # a subscription is configured for this source at all
    connected: bool
    watching: int = 0
    rejected: int = 0
    error: str | None = None
    since: str | None = None


class StateOut(BaseModel):
    """What the station *is*: positions, `IsLive`, and the solved energisation.

    The `state` cadence of the stream (ADR-0012). Every field here is discrete
    and safety-relevant, so nothing on this path is throttled or deadbanded.

    `structure_revision` is the geometry's version. A client whose copy no
    longer matches must refetch the drawing before trusting these keys to join
    onto it.
    """

    loaded: bool
    revision: int
    structure_revision: int
    updated_at: str | None = None
    devices: dict[str, DeviceLiveOut] = {}
    bay_is_live: dict[str, bool | None] = {}
    energization: EnergizationOut | None = None


class ReadingOut(BaseModel):
    """One analog value, with everything needed to distrust it.

    `unit` is `"?"` when the scale was never measured — see the module
    docstring of `domain/measurement.py`. A client must then print the quantity
    name instead of inventing a unit.

    `value` is null unless quality is GOOD. The raw number is still on
    `raw_value` for provenance, so a panel can show what the DataServer said
    without implying the number is usable (I2, I6).
    """

    id: str  # "bay:D03/MMXU1.totW" — unique across the station
    subject: str  # canonical scope ref, e.g. "bay:D03"
    measurand: str  # "MMXU1.totW"
    quantity: Quantity
    unit: Unit
    value: float | None = None
    raw_value: float | int | bool | str | None = None
    quality: Quality
    source_timestamp: str | None = None
    source_ref: str | None = None
    #: The thresholds this reading had to clear to be pushed. Carried per
    #: reading so "why has this number not moved" is answerable from the
    #: payload rather than from the source code (ADR-0012 consequence 3).
    deadband_pct: float = 0.0
    deadband_abs: float = 0.0


class MeasurementOut(BaseModel):
    """What the station is *reading*. The `measurement` cadence.

    Keyed by subject so a panel scoped to `bay:D03` looks up exactly its own
    readings. Subjects with no instrument transformers are simply absent —
    an empty list would claim we looked and found nothing.
    """

    revision: int
    measured_at: str | None = None
    #: Non-null when an installation overrode every per-quantity deadband.
    deadband_override_pct: float | None = None
    readings: dict[str, list[ReadingOut]] = {}


class LiveOut(BaseModel):
    """Everything that moves, in one document — the shape `/api/live` returns.

    The stream sends these three as separate typed events at their own rates
    (ADR-0012); the poll endpoint hands over all three at once, because a
    client that has just connected needs the whole present tense before it can
    render anything. Same schemas either way, so there is still one code path
    applying each cadence.
    """

    state: StateOut
    measurement: MeasurementOut
    link: LinkOut


class SummaryOut(BaseModel):
    """How one scope is doing right now — the first evidence-bearing facet.

    Answers the question Module A exists for ("what is the state of D03?") in
    one call, and attaches the `EvidenceRecord` that says how far that answer
    can be trusted: which points were asked for, which came back, how old they
    are, and what is degraded about them (ADR-0013).

    The evidence is built by this endpoint, never by a language model (I3).
    """

    scope: str
    kind: str  # ScopeKind of `scope`, so a client need not re-parse it
    label: str  # display name of the subject, "" when it has none
    bays: list[str]
    switch_states: dict[str, int]  # SwitchState -> count, over `bays`
    node_states: dict[str, int]  # LiveState -> count, over the same scope
    measurements: list[ReadingOut]
    issues: list[ValidationIssueOut]
    evidence: EvidenceRecord


class ScopeCandidateOut(BaseModel):
    """One thing a piece of text could have named."""

    scope: str
    kind: str
    label: str
    #: How strong the match was: `ref` | `id` | `designation` | `name`.
    #: Carried so a client can say *why* it thinks the operator meant this.
    tier: str
    matched: str  # the text that matched, as the model spells it


class ResolveOut(BaseModel):
    """What a name refers to — the deterministic half of every question (I8).

    `scope` is non-null only when exactly one thing matched. Several matches is
    a normal answer, not an error: "Lai Uyen" is the name of two bays on
    DEMO_SAS, and the right response is to ask which, never to pick one.
    """

    query: str
    scope: str | None = None
    label: str = ""
    ambiguous: bool = False
    candidates: list[ScopeCandidateOut] = []


class AskIn(BaseModel):
    """A question, and where the person asking was looking when they asked it.

    `scope` is the fallback subject, used when the question names nothing —
    "còn số đo thì sao?" means *this* bay, and the pane knows which one.
    `conversation_id` continues an existing thread; omit it to start one.
    """

    question: str
    scope: str = "station"
    conversation_id: str | None = None


class TurnStartOut(BaseModel):
    """First frame of `POST /api/ask/stream`: what is about to happen.

    Sent before any tool runs so the interface can show the conversation
    advancing, and can say up front whether a language model is involved at all.
    """

    conversation_id: str
    turn_id: str
    provider: str
    generated: bool


class ToolCallOut(BaseModel):
    """A frame announcing one tool, before it runs.

    Emitted rather than merely logged because "reading bay:D03" is the honest
    account of what the assistant is doing, and the alternative — a spinner — is
    where a system stops being inspectable.
    """

    tool: str
    args: dict[str, str | int | float | bool | None] = {}


class TokenOut(BaseModel):
    """One piece of generated prose. Only ever a fragment of `AnswerOut.text`."""

    text: str


class AnswerOut(BaseModel):
    """One turn of conversation, with everything behind it.

    The same object arrives two ways: whole from `POST /api/ask`, and in pieces
    from `POST /api/ask/stream`. Same schema either way, so a client applies an
    answer with one code path whichever it used — the reasoning behind
    `/api/live` and `/api/stream` (ADR-0012), for the same reason.

    Prose and facts are separate fields on purpose (I3). `text` is what a
    language model wrote and is labelled as interpretation; `summary`,
    `resolution` and `evidence` are computed and are what the interface may
    show as fact. When `generated` is false there is no model in the loop at
    all and `key`/`params` carry a computed statement for the frontend to
    render in its own language.
    """

    conversation_id: str
    turn_id: str
    question: str
    scope: str  # the scope actually answered about, after resolution
    provider: str  # "offline" | "openai:<model>"
    generated: bool  # a language model wrote `text`
    text: str = ""
    #: i18n key + arguments for the computed statement. Present whenever the
    #: answer could be computed, including alongside generated prose, so the UI
    #: still has something correct to show if it chooses not to trust the model.
    key: str | None = None
    params: dict[str, str | int | float | bool | None] = {}
    resolution: ResolveOut | None = None
    summary: SummaryOut | None = None
    #: Every record produced by this turn, one per tool that ran. The canonical
    #: place a client looks for evidence — a tool added later shows up here
    #: without the interface learning its payload shape (ADR-0013).
    evidence: list[EvidenceRecord] = []
    #: Set when the model was configured, was asked, and failed. The answer is
    #: still here and still correct; only the wording is the computed one. A
    #: silent downgrade would make an outage invisible (I4).
    llm_error: str | None = None
