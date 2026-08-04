"""SQLite persistence: releases, catalog snapshots, event store.

One file, WAL mode, separate read/write connections (ADR-0006).
Do NOT introduce MongoDB / Postgres / Redis without a new ADR.

Built now:
  db.py         connection handling, WAL, forward-only migrations
  meta.py       app_meta key/value repository - the pattern later ones follow
  migrations/   NNN_name.sql, consecutive from 001, never edited once applied

Planned (schema written with the module, not before):
  releases      immutable published models, addressed by content hash,
                pinned to OADataModel.ModelVersion (AGENTS.md I7)
  snapshots     frozen point catalogs; runtime resolves NodeIds against these
  events        locally buffered alarms/events -> SOE for fault analysis.
                Required because OAAlarm.GetActiveAlarm only reports the
                CURRENT state (ADR-0007).

Rule: no SQL outside this package. Repositories return plain Python.
"""
