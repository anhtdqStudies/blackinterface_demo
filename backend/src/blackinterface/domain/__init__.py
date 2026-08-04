"""L4 — Neutral Station Model. The contract every other layer speaks.

RULES (AGENTS.md I6):
  * This package imports NO other blackinterface layer. Ever.
  * No OPC UA NodeId, CIM mRID or IEC 61850 path appears here as a primary key.
    They live only in `source_refs[]` as opaque provenance strings.
  * Models are immutable, versioned, content-addressed. A Release is the hash
    of the model; EvidenceRecord cites that hash.

Contents (planned):
  identity.py    black_id + source_refs
  topology.py    node-breaker graph: connectivity nodes, terminals, devices
  binding.py     point_ref: black_id -> measurement_kind -> node_id @ snapshot
  evidence.py    EvidenceRecord, Coverage, PointQ  (see ADR-0004)
  templates/     bay template YAML (see docs/20-domain/bay-templates.md)
"""
