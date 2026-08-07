#!/usr/bin/env python3
"""Repo health check. Run from anywhere: `python tools/check.py`.

Gate for "done": every check must pass. See AGENTS.md section 6.

Checks:
  1. Workspace layout (required files/dirs exist)
  2. Architecture layer boundaries (AGENTS.md I6)
  3. The single gated write path (AGENTS.md I1, ADR-0011)
  4. Every facet declares a required capability (ADR-0016)
  5. The pane contract: PaneHost blind, layouts in one file, ui/ pure, i18n (ADR-0014)
  6. Docs freshness (measured-fact docs carry a date)
  7. Backend toolchain: ruff / mypy / pytest  (skipped if uv not installed)
  8. API contract: backend/openapi.json matches the running app (ADR-0009)
  9. Frontend toolchain: typecheck / lint / format  (skipped if npm missing)

Exit code 0 = all green, 1 = something failed.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
SRC = BACKEND / "src" / "blackinterface"

LAYERS = ("domain", "integration", "diagram", "api", "agent", "store", "control")

# domain/ must import no sibling layer (AGENTS.md I6)
DOMAIN_FORBIDDEN = tuple(layer for layer in LAYERS if layer != "domain")

# agent/ must not reach past api/ into internals (AGENTS.md I5), and must never
# reach the write path at all — the agent prepares an operation, a person issues
# it (AGENTS.md I1, ADR-0011 section 3)
AGENT_FORBIDDEN = ("integration", "diagram", "store", "control")

#: The one package allowed to invoke a OneATS write surface (ADR-0011).
#: Its registry is empty, so in practice nothing writes today — but the boundary
#: is here, scannable, rather than spread across api/ routers.
WRITE_PATH = "control"

#: The registry inside it, kept empty by decision until an ADR opens a command.
REGISTRY_FILE = SRC / WRITE_PATH / "registry.py"
REGISTRY_SYMBOL = "COMMANDS"

#: The agent's tool registry (ADR-0019). Every tool declares the capability it
#: needs, and every one of those must be a read — the write half of I1 on the
#: agent's side. Read statically, because the runtime guard in `register()` only
#: sees files somebody imported, and a tool in a module nobody imports yet is
#: exactly the one that gets imported later without a second look.
AGENT_TOOLS_DIR = SRC / "agent" / "tools"
#: Where the computed answers name themselves. Their i18n keys must exist in
#: both locale files — see `check_agent_answer_keys_are_translated`.
AGENT_BRIEF = SRC / "agent" / "brief.py"
AGENT_READ_ONLY_SYMBOL = "READ_ONLY"
#: Capabilities no agent tool may ever demand. Spelled out here as well as in
#: `registry.py` on purpose: this list is what makes the check independent of the
#: file it is checking, so widening `READ_ONLY` cannot widen its own gate.
AGENT_FORBIDDEN_CAPABILITIES = (
    "ALARM_ACK",
    "CONTROL_DRAFT",
    "CONTROL_SIGN",
    "KNOWLEDGE_WRITE",
    "MODEL_CONNECT",
    "MODEL_EDIT",
    "MODEL_PUBLISH",
    "REPORT_EXPORT",
    "ACCOUNT_MANAGE",
)

#: The scope grammar exists twice — once per language (AGENTS.md I8, ADR-0010).
#: The kinds are the part that would drift, so they are compared mechanically.
SCOPE_PY = SRC / "domain" / "scope.py"
SCOPE_TS = FRONTEND / "src" / "scope.ts"

# OneATS write surfaces — callable only from control/ (AGENTS.md I1,
# docs/30-integration/oneats-dataserver.md section 9)
FORBIDDEN_CALLS = (
    "PosCtl",
    # Tap changer, browsed on /SAS/AT1/YLTC 2026-08-06 while adding Module A.
    # We read TapPos from that node; these five sit beside it as Methods, and
    # reading a node next door to a command is exactly when the boundary has to
    # be spelled out rather than assumed.
    "TapChg",
    "MasCtl",
    "EmerCtl",
    "ParCtl",
    "ResetCtl",
    "UnforceAllData",
    "EnableAlarm",
    "DisableAlarm",
    "SetTagging",
    "RemoveTagging",
    "ChangeTagging",
    "OnlineUpdate",
    "AckAll",
    "AcknowledgeByEventId",
    "AcknowledgeByNodeId",
    "AcknowledgeByObjectId",
    "GetDisabledAlarm",
)

REQUIRED_PATHS = (
    "AGENTS.md",
    "CLAUDE.md",
    ".cursor/rules/blackinterface.mdc",
    "docs/README.md",
    "docs/00-product/vision.md",
    "docs/10-architecture/overview.md",
    "docs/10-architecture/adr/README.md",
    "docs/20-domain/glossary.md",
    "docs/20-domain/bay-templates.md",
    "docs/30-integration/oneats-dataserver.md",
    "docs/90-progress/status.md",
    "docs/40-testing/manual-test-01-topology.md",
    "backend/pyproject.toml",
    "backend/src/blackinterface/__init__.py",
    "backend/src/blackinterface/domain/scope.py",
    "backend/src/blackinterface/domain/evidence.py",
    "backend/src/blackinterface/control/registry.py",
    "backend/src/blackinterface/control/guard.py",
    "backend/src/blackinterface/control/audit.py",
    "backend/tests/fixtures/sas_tree.json",
    "backend/openapi.json",
    "frontend/package.json",
    "frontend/src/main.ts",
    "frontend/src/api/client.ts",
)

#: Bay templates are data the topology builder depends on; an empty directory
#: means every bay silently falls through to UNKNOWN.
TEMPLATE_DIR = SRC / "domain" / "templates"

#: Permission is checked at the facet layer, so every facet has to say what it
#: needs (ADR-0016 section 4). Scanned here rather than only asserted in tests
#: because the failure mode is silent: a route with no declaration serves
#: everybody, and nothing about it looks wrong.
ROUTERS_DIR = SRC / "api" / "routers"
ROUTE_DECORATORS = ("get", "post", "put", "patch", "delete")

#: The two ways a facet may declare itself. `public()` is reachable with no
#: identity at all (ADR-0017), so it is counted separately and reported — a
#: growing public surface is the thing a reviewer wants to notice.
REQUIRES_CALL = "requires"
PUBLIC_CALL = "public"
GATE_CALLS = (REQUIRES_CALL, PUBLIC_CALL)

#: The capability list exists in both languages, for the same reason the scope
#: grammar does: the frontend hides what the caller cannot use, and it cannot
#: name a permission the backend never heard of. Compared mechanically.
AUTHZ_PY = SRC / "domain" / "authz.py"
AUTHZ_TS = FRONTEND / "src" / "authz.ts"

#: The pane contract (ADR-0014 section 3, docs/20-ui/frontend-architecture.md
#: section 9). Every rule below has the same shape: it is cheap to break by
#: accident, invisible in review, and expensive once two people have built on
#: the broken version.
FE_SRC = FRONTEND / "src"
PANE_HOST = FE_SRC / "app" / "layout" / "PaneHost.vue"
PRESETS_TS = FE_SRC / "app" / "layout" / "presets.ts"
PANES_TS = FE_SRC / "app" / "layout" / "panes.ts"
UI_DIR = FE_SRC / "ui"
I18N_FILES = (FE_SRC / "i18n" / "vi.ts", FE_SRC / "i18n" / "en.ts")

#: Raw binding detail — NodeId, unmapped Dbpos, logical-node name — belongs to the
#: engineer surface and nowhere else (ADR-0014 section 8, screens.md section 1).
#: The patterns match how the fields are actually spelled on screen, not the
#: concepts: `source_ref` and `.ln` come off the API model, the rest are i18n keys.
ENGINEER_ONLY_DIR = FE_SRC / "features" / "engineer"
RAW_BINDING = (
    re.compile(r"\bsource_ref\b"),
    re.compile(r"\bsourceRef\b"),
    re.compile(r"\brawDbpos\b"),
    re.compile(r"\blogicalNode\b"),
    re.compile(r"\.ln\b"),
)

#: `t('a.b')` with a literal key. Keys built from a backend code — `state.CLOSED`,
#: `limit.no_history` — are template literals and deliberately out of scope here;
#: they are covered instead by vi and en having to agree with each other.
I18N_USE = re.compile(r"\bt\(\s*'([a-z][A-Za-z0-9]*(?:\.[A-Za-z0-9_]+)+)'")

#: Key maps like `PANE_TITLE_KEY` name i18n keys as plain strings, never through
#: `t()`. Written out rather than built with a template literal precisely so this
#: scan can see them; see the comment on PANE_TITLE_KEY.
I18N_LITERAL = re.compile(r"'([a-z][A-Za-z0-9]*\.[A-Za-z0-9_.]+)'")

# docs that state measured facts and therefore must carry a date
DATED_DOCS = (
    "docs/30-integration/oneats-dataserver.md",
    "docs/90-progress/status.md",
)

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
if sys.platform == "win32":
    try:  # enable ANSI on Windows terminals that need it
        import colorama  # type: ignore[import-not-found]

        colorama.just_fix_windows_console()
    except Exception:  # pragma: no cover - cosmetic only
        GREEN = RED = YELLOW = DIM = RESET = ""


@dataclass
class Report:
    failures: list[str] = field(default_factory=list)
    skips: list[str] = field(default_factory=list)

    def ok(self, msg: str) -> None:
        print(f"  {GREEN}PASS{RESET}  {msg}")

    def fail(self, msg: str, detail: str = "") -> None:
        print(f"  {RED}FAIL{RESET}  {msg}")
        if detail:
            print(f"        {DIM}{detail.rstrip()}{RESET}")
        self.failures.append(msg)

    def skip(self, msg: str, why: str) -> None:
        print(f"  {YELLOW}SKIP{RESET}  {msg} {DIM}({why}){RESET}")
        self.skips.append(msg)


def section(title: str) -> None:
    print(f"\n{title}")


def iter_py(pkg: Path):
    if not pkg.exists():
        return
    yield from pkg.rglob("*.py")


def check_layout(r: Report) -> None:
    section("1. Workspace layout")
    missing = [p for p in REQUIRED_PATHS if not (ROOT / p).exists()]
    if missing:
        r.fail("required files missing", "\n        ".join(missing))
    else:
        r.ok(f"{len(REQUIRED_PATHS)} required paths present")

    absent = [layer for layer in LAYERS if not (SRC / layer / "__init__.py").exists()]
    if absent:
        r.fail("layer packages missing", ", ".join(absent))
    else:
        r.ok(f"all {len(LAYERS)} layer packages present")

    templates = sorted(p.name for p in TEMPLATE_DIR.glob("*.yaml"))
    if templates:
        r.ok(f"{len(templates)} bay templates: {', '.join(t.removesuffix('.yaml') for t in templates)}")
    else:
        r.fail("no bay templates", f"expected *.yaml in {TEMPLATE_DIR.relative_to(ROOT)}")


def check_layer_boundaries(r: Report) -> None:
    section("2. Architecture layer boundaries (AGENTS.md I6, I5)")

    def scan(pkg: str, forbidden: tuple[str, ...], rule: str) -> None:
        hits: list[str] = []
        for path in iter_py(SRC / pkg):
            text = path.read_text(encoding="utf-8", errors="replace")
            for other in forbidden:
                pattern = rf"^\s*(?:from|import)\s+.*\b(?:blackinterface\.)?{other}\b"
                for i, line in enumerate(text.splitlines(), 1):
                    if re.match(pattern, line):
                        hits.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
        if hits:
            r.fail(f"{pkg}/ violates: {rule}", "\n        ".join(hits))
        else:
            r.ok(f"{pkg}/ respects: {rule}")

    scan("domain", DOMAIN_FORBIDDEN, "imports no sibling layer")
    scan("agent", AGENT_FORBIDDEN, "goes through api/, and never touches control/")
    check_scope_grammar(r)

    # only integration/ may import asyncua
    hits = []
    for layer in LAYERS:
        if layer == "integration":
            continue
        for path in iter_py(SRC / layer):
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if re.match(r"^\s*(?:from|import)\s+asyncua\b", line):
                    hits.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    if hits:
        r.fail("asyncua imported outside integration/", "\n        ".join(hits))
    else:
        r.ok("asyncua confined to integration/")


def check_scope_grammar(r: Report) -> None:
    """`domain/scope.py` and `src/scope.ts` must know the same scope kinds.

    The grammar is deliberately duplicated — the alternative was structured JSON
    in every URL and pane key (see the header of scope.ts). Duplication is only
    acceptable while something checks it, so this is that something. It compares
    the *kinds*, which is the part that would drift; the rest of the grammar is
    four lines long and asserted by tests on both sides.
    """
    if not SCOPE_PY.exists() or not SCOPE_TS.exists():
        r.fail("scope grammar files missing", f"{SCOPE_PY.name} and {SCOPE_TS.name} must both exist")
        return

    py_body = re.search(
        r"class ScopeKind\(StrEnum\):(.*?)(?=\n\S)",
        SCOPE_PY.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    ts_body = re.search(
        r"SCOPE_KINDS\s*=\s*\[(.*?)\]", SCOPE_TS.read_text(encoding="utf-8"), re.DOTALL
    )
    if py_body is None or ts_body is None:
        r.fail("cannot read the scope kinds", "ScopeKind / SCOPE_KINDS no longer match the parser")
        return

    py_kinds = set(re.findall(r'^\s+[A-Z_]+ = "([a-z_]+)"', py_body.group(1), re.MULTILINE))
    ts_kinds = set(re.findall(r"'([a-z_]+)'", ts_body.group(1)))
    if py_kinds and py_kinds == ts_kinds:
        r.ok(f"scope grammar agrees across languages: {', '.join(sorted(py_kinds))}")
    else:
        r.fail(
            "scope kinds differ between domain/scope.py and src/scope.ts",
            f"python only: {sorted(py_kinds - ts_kinds)}  ts only: {sorted(ts_kinds - py_kinds)}",
        )


def check_write_path(r: Report) -> None:
    """The write path is one place, and that place is currently shut (ADR-0011).

    Three separate things are asserted, because each fails differently:

      a. no module outside control/ invokes a OneATS write surface
      b. control/registry.py lists no commands
      c. agent/ cannot import control/ (checked in check_layer_boundaries)

    (a) matches call *syntax* only — `.PosCtl(` or `call_method("...PosCtl")` —
    so a docstring documenting the ban does not trip it. (b) is parsed rather
    than grepped: a comment saying the registry is empty proves nothing.
    """
    section("3. Single gated write path (AGENTS.md I1, ADR-0011)")
    names = "|".join(FORBIDDEN_CALLS)
    patterns = (
        re.compile(rf"\.\s*(?:{names})\s*\("),                      # obj.PosCtl(...)
        re.compile(rf"""call_method\s*\(\s*["'][^"']*(?:{names})"""),  # call_method("2:PosCtl")
    )
    hits: list[str] = []
    for path in iter_py(SRC):
        if path.is_relative_to(SRC / WRITE_PATH):
            continue  # the one package allowed to hold these calls
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if any(p.search(line) for p in patterns):
                hits.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    if hits:
        r.fail(f"OneATS write surface INVOKED outside {WRITE_PATH}/", "\n        ".join(hits))
    else:
        r.ok(f"{len(FORBIDDEN_CALLS)} write calls confined to {WRITE_PATH}/")

    check_registry_empty(r)
    check_agent_tools_are_read_only(r)


def check_agent_tools_are_read_only(r: Report) -> None:
    """No tool the agent holds may demand a capability that changes anything.

    The agent never has a write tool — permanently, including after Module C
    opens the write path (AGENTS.md I1, ADR-0011 section 3, ADR-0019). Three
    things are read here, and each catches a different way that could stop being
    true:

      a. `READ_ONLY` in `agent/tools/registry.py` lists no write capability.
         Widening that set is how the rule would be relaxed by accident.
      b. every `Tool(...)` constructed under `agent/tools/` declares a
         `requires=` that is not a write capability.
      c. every one of them declares a `requires=` at all.

    (b) is the one the runtime guard cannot do. `register()` raises, but only
    for tools in a module something imported; a file added and not yet wired up
    would pass every test and fail nobody, right up until the import lands.
    """
    rel = AGENT_TOOLS_DIR.relative_to(ROOT).as_posix()
    if not AGENT_TOOLS_DIR.is_dir():
        r.fail(f"{rel}/ missing", "the agent's tool registry must exist to be checked")
        return

    forbidden = set(AGENT_FORBIDDEN_CAPABILITIES)
    problems: list[str] = []
    declared: list[str] = []

    for path in sorted(AGENT_TOOLS_DIR.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            r.fail(f"{path.relative_to(ROOT)} does not parse", str(exc))
            return
        where = path.relative_to(ROOT).as_posix()

        for node in ast.walk(tree):
            # (a) the allow-list itself
            if isinstance(node, ast.Assign | ast.AnnAssign):
                targets = (
                    [node.target] if isinstance(node, ast.AnnAssign) else list(node.targets)
                )
                if any(
                    isinstance(t, ast.Name) and t.id == AGENT_READ_ONLY_SYMBOL for t in targets
                ):
                    named = {
                        n.attr
                        for n in ast.walk(node)
                        if isinstance(n, ast.Attribute) and n.attr.isupper()
                    }
                    for bad in sorted(named & forbidden):
                        problems.append(f"{where}: {AGENT_READ_ONLY_SYMBOL} admits {bad}")

            # (b) and (c) every tool that gets built
            if not (isinstance(node, ast.Call) and _is_tool_call(node)):
                continue
            name = _keyword_text(node, "name") or "<unnamed>"
            requires = _keyword_capability(node, "requires")
            if requires is None:
                problems.append(f"{where}: tool {name} declares no requires=")
            elif requires in forbidden:
                problems.append(f"{where}: tool {name} demands {requires}, which is a write")
            else:
                declared.append(f"{name} -> {requires}")

    if problems:
        r.fail("the agent holds a tool that could change something", "\n        ".join(problems))
    elif declared:
        r.ok(f"agent tools, all read-only: {', '.join(sorted(declared))}")
    else:
        r.fail("no agent tool found", "the scan matched nothing; has the registry shape changed?")


def _is_tool_call(node: ast.Call) -> bool:
    """`Tool(...)` or `registry.Tool(...)`, however it was imported."""
    if isinstance(node.func, ast.Name):
        return node.func.id == "Tool"
    return isinstance(node.func, ast.Attribute) and node.func.attr == "Tool"


def _keyword_text(node: ast.Call, name: str) -> str | None:
    for kw in node.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
        if kw.arg == name and isinstance(kw.value, ast.Name):
            return kw.value.id  # a module constant, e.g. name=SUMMARY
    return None


def _keyword_capability(node: ast.Call, name: str) -> str | None:
    """`requires=Capability.STATION_READ` -> "STATION_READ"."""
    for kw in node.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Attribute):
            return kw.value.attr
    return None


def check_registry_empty(r: Report) -> None:
    """`control/registry.py` must declare COMMANDS as an empty dict literal.

    Parsed with ast so that neither a comment nor a computed value can dress up
    a registry that has quietly grown an entry. Opening one takes an ADR and a
    deliberate change here — which is the whole mechanism (ADR-0011 section 1).
    """
    rel = REGISTRY_FILE.relative_to(ROOT)
    if not REGISTRY_FILE.exists():
        r.fail(f"{rel} missing", "the write path must exist even while it is shut")
        return
    try:
        tree = ast.parse(REGISTRY_FILE.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        r.fail(f"{rel} does not parse", str(exc))
        return

    found: list[ast.expr | None] = [
        node.value
        for node in tree.body
        if isinstance(node, ast.AnnAssign | ast.Assign)
        for target in ([node.target] if isinstance(node, ast.AnnAssign) else node.targets)
        if isinstance(target, ast.Name) and target.id == REGISTRY_SYMBOL
    ]
    if not found:
        r.fail(f"{rel} declares no {REGISTRY_SYMBOL}", "check.py cannot verify what is not there")
    elif all(isinstance(v, ast.Dict) and not v.keys for v in found):
        r.ok(f"{rel}: {REGISTRY_SYMBOL} is empty - no command is open")
    else:
        r.fail(
            f"{rel}: {REGISTRY_SYMBOL} is no longer empty",
            "every command needs its own ADR first (ADR-0011)",
        )


def check_facets_declare_capability(r: Report) -> None:
    """Every route decorator carries `dependencies=[requires(...)]` (ADR-0016).

    Read as syntax, not as behaviour: this is the half that catches a router
    nobody registered yet. `tests/unit/test_authz.py` does the other half by
    walking the assembled app, where a file that never gets imported cannot
    hide. Both are cheap, and they fail on different mistakes.

    `requires()` with no argument is a legal declaration meaning "any caller" —
    it is still a decision written down. Which paths may use it is not decided
    here; the test holds that list, because it needs the real paths.
    """
    section("4. Every facet declares a required capability (ADR-0016)")
    if not ROUTERS_DIR.is_dir():
        r.fail("no api/routers/ to scan", f"expected {ROUTERS_DIR.relative_to(ROOT)}")
        return

    undeclared: list[str] = []
    public: list[str] = []
    total = 0
    for path in sorted(ROUTERS_DIR.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            r.fail(f"{path.relative_to(ROOT)} does not parse", str(exc))
            return
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for dec in node.decorator_list:
                if not _is_route_decorator(dec):
                    continue
                total += 1
                declared = _gate_calls(dec)
                if not declared:
                    undeclared.append(f"{path.relative_to(ROOT)}:{dec.lineno}: {node.name}()")
                elif PUBLIC_CALL in declared:
                    public.append(node.name)

    if undeclared:
        r.fail(
            "facet(s) with no requires= — they would serve everybody",
            "\n        ".join(undeclared),
        )
    elif total:
        r.ok(f"{total} facets all declare a capability")
        # Named rather than merely counted: which endpoints answer to somebody
        # with no identity is the line worth reading on every run (ADR-0017).
        r.ok(f"public, no sign-in needed: {', '.join(sorted(public)) or 'none'}")
    else:
        r.fail("no facets found", "the scan matched nothing; has the router shape changed?")

    check_capability_lists_agree(r)


def check_capability_lists_agree(r: Report) -> None:
    """`domain/authz.py` and `src/authz.ts` must know the same capabilities.

    Same shape as `check_scope_grammar`, same justification: a list duplicated
    across two languages is only acceptable while something compares them. A
    capability the frontend does not know about is a screen that stays hidden
    from someone entitled to it — a silent failure, and the wrong direction.
    """
    if not AUTHZ_PY.exists() or not AUTHZ_TS.exists():
        r.fail("capability list missing", f"{AUTHZ_PY.name} and {AUTHZ_TS.name} must both exist")
        return

    py_body = re.search(
        r"class Capability\(StrEnum\):(.*?)(?=\n\S)",
        AUTHZ_PY.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    ts_body = re.search(
        r"CAPABILITIES\s*=\s*\[(.*?)\]", AUTHZ_TS.read_text(encoding="utf-8"), re.DOTALL
    )
    if py_body is None or ts_body is None:
        r.fail("cannot read the capability list", "Capability / CAPABILITIES no longer parse")
        return

    py_caps = set(re.findall(r'^\s+[A-Z_]+ = "([a-z_.]+)"', py_body.group(1), re.MULTILINE))
    ts_caps = set(re.findall(r"'([a-z_.]+)'", ts_body.group(1)))
    if py_caps and py_caps == ts_caps:
        r.ok(f"{len(py_caps)} capabilities agree across languages")
    else:
        r.fail(
            "capabilities differ between domain/authz.py and src/authz.ts",
            f"python only: {sorted(py_caps - ts_caps)}  ts only: {sorted(ts_caps - py_caps)}",
        )


def _is_route_decorator(dec: ast.expr) -> bool:
    """`@router.get(...)` and friends. A bare `@router.get` cannot exist."""
    return (
        isinstance(dec, ast.Call)
        and isinstance(dec.func, ast.Attribute)
        and dec.func.attr in ROUTE_DECORATORS
        and isinstance(dec.func.value, ast.Name)
        and dec.func.value.id == "router"
    )


def _gate_calls(dec: ast.Call) -> set[str]:
    """Which gate functions this route's `dependencies=[...]` names."""
    return {
        el.func.id
        for kw in dec.keywords
        if kw.arg == "dependencies" and isinstance(kw.value, ast.List)
        for el in kw.value.elts
        if isinstance(el, ast.Call) and isinstance(el.func, ast.Name) and el.func.id in GATE_CALLS
    }


def check_pane_contract(r: Report) -> None:
    """The frontend workspace contract (ADR-0014, frontend-architecture.md §9).

    Five rules, all of them things a reasonable person breaks by accident:
    `PaneHost` learning what a pane means, a layout defined somewhere nobody
    thinks to look, a `ui/` component reaching into a store, raw binding detail
    drifting onto the operator's screen, and an i18n key that exists in one
    language only.
    """
    section("5. The pane contract")
    if not FE_SRC.exists():
        r.skip("pane contract", "frontend/src not present")
        return

    check_pane_host_is_blind(r)
    check_layouts_live_in_presets(r)
    check_ui_is_pure(r)
    check_binding_stays_on_the_engineer_surface(r)
    check_i18n_keys(r)


def check_pane_host_is_blind(r: Report) -> None:
    """`PaneHost` renders panes; it must never know what one is.

    The measure ADR-0014 chose for "did the contract survive" is exactly this: if
    adding a pane means editing `PaneHost`, adding a pane is no longer one line
    and the register has stopped being the extension point.
    """
    if not PANE_HOST.exists():
        r.fail("PaneHost.vue missing", f"expected at {PANE_HOST.relative_to(ROOT)}")
        return
    text = PANE_HOST.read_text(encoding="utf-8")
    branches = [
        line.strip()
        for line in text.splitlines()
        if re.search(r"v-(?:if|else-if)=\"[^\"]*\bkind\b", line)
    ]
    if branches:
        r.fail(
            "PaneHost.vue branches on pane kind",
            "\n".join(branches) + "\nAdd the kind to PANE_COMPONENTS instead.",
        )
    else:
        r.ok("PaneHost.vue does not branch on pane kind")


def check_layouts_live_in_presets(r: Report) -> None:
    """A layout is data, and all of it lives in one file.

    A `cols:` sprinkled through a view is a layout nobody can find the day it
    needs changing — and two of them are two products.
    """
    stray = sorted(
        path.relative_to(ROOT).as_posix()
        for path in [*FE_SRC.rglob("*.ts"), *FE_SRC.rglob("*.vue")]
        if path != PRESETS_TS
        and re.search(r"^\s*cols:\s*\[", path.read_text(encoding="utf-8"), re.MULTILINE)
    )
    if stray:
        r.fail(
            "a layout is defined outside presets.ts",
            "\n".join(stray) + f"\nMove it into {PRESETS_TS.relative_to(ROOT).as_posix()}.",
        )
    else:
        r.ok("layouts are defined only in app/layout/presets.ts")


def check_ui_is_pure(r: Report) -> None:
    """`ui/` takes props and emits events. Nothing in it may read a store.

    This is what makes the design system safe to hand to somebody else in
    parallel: a component that reaches into `stores/` cannot be worked on without
    knowing the rest of the app, which is the coordination cost the split exists
    to avoid.

    A *type-only* import from `api/` is allowed — it disappears at build time and
    carries no coupling. A value import does not.
    """
    if not UI_DIR.exists():
        r.skip("ui/ purity", "no ui/ directory yet")
        return
    offenders: list[str] = []
    for path in sorted([*UI_DIR.rglob("*.vue"), *UI_DIR.rglob("*.ts")]):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not re.match(r"\s*import\b", line):
                continue
            if "@/stores" in line or ("@/api" in line and "import type" not in line):
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{i}: {line.strip()}")
    if offenders:
        r.fail("a ui/ component imports stores/ or api/", "\n".join(offenders))
    else:
        r.ok("ui/ imports no store and no API client")


def check_binding_stays_on_the_engineer_surface(r: Report) -> None:
    """NodeId, raw Dbpos and logical-node names appear on one surface only.

    ADR-0014 section 8 and screens.md section 1 both say it, and until now
    neither was enforced — so the fields simply followed `DevicePanel` into the
    operator's state pane when lô 2 rewrote it. That is how this class of rule
    fails: not by argument, by a move.

    Why it matters is not tidiness. The operator screen is read while somebody
    decides whether a section is safe to touch, and every field that cannot
    inform that decision competes with the ones that can. The place for
    `ns=2;s=SAS.D03.XCBR1.Pos` is the `binding` pane, where the question being
    asked is about the mapping itself.
    """
    offenders: list[str] = []
    for path in sorted(FE_SRC.rglob("*.vue")):
        if ENGINEER_ONLY_DIR in path.parents:
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(pattern.search(line) for pattern in RAW_BINDING):
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{i}: {line.strip()}")
    if offenders:
        r.fail(
            "raw binding detail outside the engineer surface",
            "\n".join(offenders)
            + "\nNodeId / Dbpos / logical-node names belong to features/engineer/"
            + " (ADR-0014 §8).",
        )
    else:
        r.ok("no NodeId, raw Dbpos or logical-node name outside features/engineer/")


def _i18n_keys(path: Path) -> set[str]:
    """Flatten one locale file into dotted keys.

    A brace-tracking read rather than a JS parse. It holds because these files
    are prettier-formatted object literals: a nested group is a line ending in
    `{`, anything else with a `key:` is a leaf. If that ever stops being true the
    counts printed below will disagree between the two languages and say so.
    """
    keys: set[str] = set()
    stack: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("//", "/*", "*")):
            continue
        if line.startswith(("}", ")")) and stack:
            stack.pop()
            continue
        m = re.match(r"^(?:'([^']+)'|([A-Za-z_][\w-]*)):\s*(.*)$", line)
        if not m:
            continue
        name = m.group(1) or m.group(2)
        if m.group(3).rstrip().endswith("{"):
            stack.append(name)
        else:
            keys.add(".".join([*stack, name]))
    return keys


def check_i18n_keys(r: Report) -> None:
    """Every key used exists, and `vi` and `en` hold the same set.

    Both halves are needed. The first catches a typo; the second catches the
    common case — a key added to Vietnamese while writing the feature and never
    added to English, which surfaces to an ATS reviewer as raw machine text on
    the screen (GD 1.5 acceptance: *"switching VI/EN shows no key names"*).
    """
    missing_file = [p.name for p in I18N_FILES if not p.exists()]
    if missing_file:
        r.fail("locale file missing", ", ".join(missing_file))
        return

    vi, en = (_i18n_keys(p) for p in I18N_FILES)
    if vi != en:
        r.fail(
            "vi and en do not carry the same keys",
            f"vi only: {sorted(vi - en)[:12]}  en only: {sorted(en - vi)[:12]}",
        )
        return

    used: set[str] = set()
    for path in [*FE_SRC.rglob("*.vue"), *FE_SRC.rglob("*.ts")]:
        if path.parent == I18N_FILES[0].parent:
            continue
        text = path.read_text(encoding="utf-8")
        used |= set(I18N_USE.findall(text))
        if path in (PANES_TS, PRESETS_TS):
            used |= set(I18N_LITERAL.findall(text))

    unknown = sorted(key for key in used if key not in vi)
    if unknown:
        r.fail("i18n key used but not defined", "\n".join(unknown))
    else:
        r.ok(f"{len(vi)} i18n keys, identical in vi and en; {len(used)} used and all defined")

    check_agent_answer_keys_are_translated(r, vi)


def check_agent_answer_keys_are_translated(r: Report, defined: set[str]) -> None:
    """Every answer the backend can compute has words in both languages (ADR-0019).

    When there is no model, the assistant answers with an i18n key and arguments
    rather than a sentence — the backend cannot know whether the reader wants
    Vietnamese or English, so it does not write prose at all (`agent/brief.py`,
    same reasoning as the limit codes in `domain/evidence.py`).

    That only works while the two halves agree. This is the same shape as the
    scope grammar and the capability list: a contract that exists in two
    languages, compared mechanically, because the failure is silent. A key the
    frontend has never heard of renders as `agent.answer.denied` on screen —
    machine text where an operator expected to be told why they were refused.
    """
    if not AGENT_BRIEF.exists():
        r.fail(f"{AGENT_BRIEF.name} missing", "the computed answers are defined there")
        return
    emitted = set(re.findall(r'^KEY_\w+ = "([\w.]+)"', AGENT_BRIEF.read_text("utf-8"), re.M))
    if not emitted:
        r.fail("no computed answer keys found", "has agent/brief.py changed shape?")
        return
    absent = sorted(emitted - defined)
    if absent:
        r.fail(
            "the backend can emit an answer the interface cannot render",
            "\n        ".join(absent) + "\n        add them to i18n/vi.ts and i18n/en.ts",
        )
    else:
        r.ok(f"{len(emitted)} computed answers translated in both languages")


def check_docs_dated(r: Report) -> None:
    section("6. Measured-fact docs carry a date")
    for rel in DATED_DOCS:
        path = ROOT / rel
        if not path.exists():
            r.fail(f"{rel} missing")
            continue
        head = path.read_text(encoding="utf-8", errors="replace")[:2000]
        if re.search(r"\d{4}-\d{2}-\d{2}", head):
            r.ok(f"{rel} dated")
        else:
            r.fail(f"{rel} has no YYYY-MM-DD near the top", "see docs/README.md rule 1")


def _is_onedrive_lock(output: str) -> bool:
    return "Access is denied" in output or "os error 396" in output


def check_backend_toolchain(r: Report) -> None:
    section("7. Backend toolchain")
    if not shutil.which("uv"):
        r.skip("ruff / mypy / pytest", "uv not installed - see AGENTS.md section 6")
        return
    if not (BACKEND / ".venv").exists():
        r.skip("ruff / mypy / pytest", "run `cd backend && uv sync` first")
        return

    for label, cmd in (
        ("ruff check", ["uv", "run", "ruff", "check", "."]),
        ("ruff format", ["uv", "run", "ruff", "format", "--check", "."]),
        ("mypy", ["uv", "run", "mypy", "src"]),
        ("pytest", ["uv", "run", "pytest"]),
    ):
        proc = subprocess.run(cmd, cwd=BACKEND, capture_output=True, text=True)
        if proc.returncode != 0 and _is_onedrive_lock(proc.stdout + proc.stderr):
            # OneDrive occasionally holds .venv while uv reinstalls the editable
            # package. Transient; one retry clears it. See AGENTS.md section 7.
            proc = subprocess.run(cmd, cwd=BACKEND, capture_output=True, text=True)
        if proc.returncode == 0:
            r.ok(label)
        elif label == "pytest" and proc.returncode == 5:
            # exit 5 = no tests collected; a bare scaffold is not a failure
            r.skip(label, "no tests collected yet")
        else:
            out = (proc.stdout + proc.stderr).strip()
            r.fail(label, out[:1500])


def check_api_contract(r: Report) -> None:
    """backend/openapi.json is the frontend's source of types (ADR-0009).

    If it drifts from the running app, the frontend compiles against an API that
    no longer exists — and the mismatch shows up at runtime in a substation
    rather than at build time here.
    """
    section("8. API contract")
    if not shutil.which("uv") or not (BACKEND / ".venv").exists():
        r.skip("openapi.json freshness", "backend environment not set up")
        return
    cmd = ["uv", "run", "python", "../tools/export_openapi.py", "--check"]
    proc = subprocess.run(cmd, cwd=BACKEND, capture_output=True, text=True)
    if proc.returncode != 0 and _is_onedrive_lock(proc.stdout + proc.stderr):
        proc = subprocess.run(cmd, cwd=BACKEND, capture_output=True, text=True)
    if proc.returncode == 0:
        r.ok("backend/openapi.json is up to date")
    else:
        r.fail("backend/openapi.json is stale", (proc.stdout + proc.stderr).strip()[:800])


def check_frontend_toolchain(r: Report) -> None:
    section("9. Frontend toolchain")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm is None:
        r.skip("typecheck / lint / format", "npm not installed")
        return
    if not (FRONTEND / "node_modules").exists():
        r.skip("typecheck / lint / format", "run `cd frontend && npm install` first")
        return

    for label, args in (
        ("typecheck", ["run", "typecheck"]),
        ("lint", ["run", "lint"]),
        ("format", ["run", "format:check"]),
    ):
        proc = subprocess.run([npm, *args], cwd=FRONTEND, capture_output=True, text=True)
        if proc.returncode == 0:
            r.ok(label)
        else:
            r.fail(f"frontend {label}", (proc.stdout + proc.stderr).strip()[:1500])

    if not (FRONTEND / "dist" / "index.html").exists():
        r.skip("built SPA", "run `cd frontend && npm run build` to serve a UI")
    else:
        r.ok("frontend/dist present - the API will serve a UI")


def main() -> int:
    print(f"Black Interface repo check  {DIM}{ROOT}{RESET}")
    r = Report()
    check_layout(r)
    check_layer_boundaries(r)
    check_write_path(r)
    check_facets_declare_capability(r)
    check_pane_contract(r)
    check_docs_dated(r)
    check_backend_toolchain(r)
    check_api_contract(r)
    check_frontend_toolchain(r)

    print()
    if r.failures:
        print(f"{RED}FAILED{RESET} - {len(r.failures)} check(s):")
        for f in r.failures:
            print(f"  - {f}")
        print("\nDo not report work as done until this is green (AGENTS.md section 6).")
        return 1
    msg = f"{GREEN}ALL CHECKS PASSED{RESET}"
    if r.skips:
        msg += f" {DIM}({len(r.skips)} skipped){RESET}"
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
