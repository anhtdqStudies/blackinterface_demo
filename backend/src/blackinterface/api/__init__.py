"""L3 — Typed Domain API. Semantic operations over HTTP/SSE.

The frontend calls this layer DIRECTLY for deterministic work; BlackCore calls
the exact same endpoints for natural-language turns (AGENTS.md I5). BlackCore
has no private path and no elevated privilege.

Every tool-shaped endpoint returns (payload, EvidenceRecord) — evidence is
produced HERE, never composed by the LLM (ADR-0004).

Quality gate enforced at this layer, not in a prompt (AGENTS.md I2):
  quality != GOOD  ->  state = UNDETERMINED, and the caller must not assert.
"""
