"""L2 — BlackCore: intent, tool registry, planner, evidence, policy.

MAY:  understand intent, pick tools, pick views, summarise, explain with evidence.
MUST NOT: invent topology/connectivity/mapping, write to OPC UA, execute control,
          turn hypotheses into facts, or compose evidence text itself.

The tool registry contains NO write tool. That is the structural half of
invariant I1; the read-only OPC UA account is the other half.

Deterministic reasoning (topology, layout, energization, fault causal chains)
belongs in the backend, not here (ADR-0005). The agent orchestrates and phrases.
"""
