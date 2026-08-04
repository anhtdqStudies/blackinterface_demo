"""Architecture invariants, enforced at test time.

Complements `tools/check.py` (static scan) by exercising the real import graph:
a module can satisfy a regex scan and still pull in a forbidden layer through a
transitive import. These tests catch that.

See AGENTS.md section 2 and docs/10-architecture/overview.md.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

import blackinterface

LAYERS = ("domain", "integration", "diagram", "api", "agent", "store")

# AGENTS.md I6 — domain is the contract; it depends on nothing else. Not on a
# sibling layer, and not on process-wide concerns either: a pure domain takes
# its inputs as arguments, so it must not reach for config or a database.
FORBIDDEN_TRANSITIVE: dict[str, tuple[str, ...]] = {
    "domain": (
        *(f"blackinterface.{layer}" for layer in LAYERS if layer != "domain"),
        "blackinterface.config",
        "blackinterface.logs",
    ),
    # AGENTS.md I5 — agent reaches the rest of the system only through api.
    "agent": ("blackinterface.integration", "blackinterface.diagram", "blackinterface.store"),
}

# AGENTS.md I6 — only integration may speak OPC UA.
OPCUA_ALLOWED_PREFIX = "blackinterface.integration"


@contextmanager
def _clean_import(prefixes: tuple[str, ...]) -> Iterator[None]:
    """Hide matching modules so an import is observed from scratch, then restore.

    Restoring matters: re-importing a module creates *new* class objects, and a
    session-scoped fixture built before the swap would then fail isinstance
    checks against them. Leaking that state breaks unrelated tests.
    """
    saved = {name: mod for name, mod in sys.modules.items() if name.startswith(prefixes)}
    for name in saved:
        del sys.modules[name]
    try:
        yield
    finally:
        for name in [m for m in sys.modules if m.startswith(prefixes)]:
            del sys.modules[name]
        sys.modules.update(saved)


def _import_layer_fresh(layer: str) -> set[str]:
    """Import a layer in a clean namespace; return the blackinterface modules it pulls in."""
    with _clean_import(("blackinterface",)):
        importlib.import_module(f"blackinterface.{layer}")
        return {m for m in sys.modules if m.startswith("blackinterface.")}


@pytest.mark.parametrize("layer", LAYERS)
def test_layer_imports_cleanly(layer: str) -> None:
    importlib.import_module(f"blackinterface.{layer}")


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_TRANSITIVE))
def test_layer_does_not_reach_forbidden_layers(layer: str) -> None:
    loaded = _import_layer_fresh(layer)
    violations = sorted(
        module
        for module in loaded
        for forbidden in FORBIDDEN_TRANSITIVE[layer]
        if module == forbidden or module.startswith(forbidden + ".")
    )
    assert not violations, (
        f"blackinterface.{layer} transitively imports {violations}. See AGENTS.md invariants I5/I6."
    )


def test_asyncua_confined_to_integration() -> None:
    """No layer other than integration may import asyncua, even transitively."""
    for layer in LAYERS:
        if layer == "integration":
            continue
        with _clean_import(("blackinterface", "asyncua")):
            importlib.import_module(f"blackinterface.{layer}")
            assert "asyncua" not in sys.modules, (
                f"blackinterface.{layer} pulls in asyncua. Only "
                f"{OPCUA_ALLOWED_PREFIX} may (AGENTS.md I6)."
            )


def test_every_layer_package_exists() -> None:
    found = {m.name for m in pkgutil.iter_modules(blackinterface.__path__)}
    missing = set(LAYERS) - found
    assert not missing, f"missing layer packages: {sorted(missing)}"


def test_every_layer_documents_its_role() -> None:
    """Each layer's __init__ carries a docstring stating its responsibility.

    This is what a cold agent reads first; an undocumented layer is how the
    architecture erodes.
    """
    for layer in LAYERS:
        module = importlib.import_module(f"blackinterface.{layer}")
        doc = (module.__doc__ or "").strip()
        assert len(doc) > 80, f"blackinterface.{layer} needs a real module docstring"
