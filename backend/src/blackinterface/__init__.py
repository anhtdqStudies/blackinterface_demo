"""Black Interface — AI-first operations layer for OneATS substation SCADA.

Layer map (see AGENTS.md §4 and docs/10-architecture/overview.md):

    domain/       L4  Neutral Station Model. Imports NO other layer.
    integration/  L5  Importers + adapters. The ONLY layer that knows NodeIds.
    diagram/      L6  graph -> layout -> ViewModel -> SVG.
    api/          L3  Typed Domain API (FastAPI, HTTP/SSE).
    agent/        L2  BlackCore (intent, tools, planner, evidence, policy).
    store/            SQLite persistence: releases, catalog snapshots, event store.

Dependency direction is one-way:

    api -> domain <- integration
    agent -> api
    diagram -> domain
    store -> domain

Seven invariants govern every change; they are listed in AGENTS.md §2.
The two most load-bearing:

    I1  MVP is READ-ONLY, enforced structurally (no write tools exist).
    I2  Never assert device state when quality != GOOD.
"""

__version__ = "0.0.1"
