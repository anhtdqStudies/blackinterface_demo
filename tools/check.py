#!/usr/bin/env python3
"""Repo health check. Run from anywhere: `python tools/check.py`.

Gate for "done": every check must pass. See AGENTS.md section 6.

Checks:
  1. Workspace layout (required files/dirs exist)
  2. Architecture layer boundaries (AGENTS.md I6)
  3. No forbidden OneATS write calls in source (AGENTS.md I1)
  4. Docs freshness (measured-fact docs carry a date)
  5. Backend toolchain: ruff / mypy / pytest  (skipped if uv not installed)
  6. API contract: backend/openapi.json matches the running app (ADR-0009)
  7. Frontend toolchain: typecheck / lint / format  (skipped if npm missing)

Exit code 0 = all green, 1 = something failed.
"""

from __future__ import annotations

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

LAYERS = ("domain", "integration", "diagram", "api", "agent", "store")

# domain/ must import no sibling layer (AGENTS.md I6)
DOMAIN_FORBIDDEN = tuple(layer for layer in LAYERS if layer != "domain")

# agent/ must not reach past api/ into internals (AGENTS.md I5)
AGENT_FORBIDDEN = ("integration", "diagram", "store")

# OneATS write surfaces — never call these (AGENTS.md I1,
# docs/30-integration/oneats-dataserver.md section 9)
FORBIDDEN_CALLS = (
    "PosCtl",
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
    "backend/tests/fixtures/sas_tree.json",
    "backend/openapi.json",
    "frontend/package.json",
    "frontend/src/main.ts",
    "frontend/src/api/client.ts",
)

#: Bay templates are data the topology builder depends on; an empty directory
#: means every bay silently falls through to UNKNOWN.
TEMPLATE_DIR = SRC / "domain" / "templates"

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
    scan("agent", AGENT_FORBIDDEN, "reaches other layers only through api/")

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


def check_no_write_calls(r: Report) -> None:
    """Flag *invocations* of OneATS write surfaces, not mere mentions.

    Docstrings that document the ban must not trip this check, so we match call
    syntax only: `.PosCtl(` or `call_method("...PosCtl"...)`.
    """
    section("3. Read-only enforcement (AGENTS.md I1)")
    names = "|".join(FORBIDDEN_CALLS)
    patterns = (
        re.compile(rf"\.\s*(?:{names})\s*\("),                      # obj.PosCtl(...)
        re.compile(rf"""call_method\s*\(\s*["'][^"']*(?:{names})"""),  # call_method("2:PosCtl")
    )
    hits: list[str] = []
    for path in iter_py(SRC):
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if any(p.search(line) for p in patterns):
                hits.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    if hits:
        r.fail("OneATS write surface INVOKED in source", "\n        ".join(hits))
    else:
        r.ok(f"no invocation of {len(FORBIDDEN_CALLS)} forbidden write calls")


def check_docs_dated(r: Report) -> None:
    section("4. Measured-fact docs carry a date")
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
    section("5. Backend toolchain")
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
    section("6. API contract")
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
    section("7. Frontend toolchain")
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
    check_no_write_calls(r)
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
