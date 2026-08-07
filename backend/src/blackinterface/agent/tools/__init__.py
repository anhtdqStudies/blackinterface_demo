"""The agent's tool registry. Read-only, and structurally so — see `registry`.

Importing this package is what registers the tools. Nothing registers itself
from a plugin path or a configuration file: the set of things the agent can do
is a list in source control, reviewable in a diff.
"""

from blackinterface.agent.tools import station  # noqa: F401  (import registers the tools)
from blackinterface.agent.tools.registry import (
    READ_ONLY,
    TOOLS,
    Tool,
    ToolArgs,
    ToolContext,
    ToolResult,
    WriteToolError,
    call,
    catalogue,
    register,
)

__all__ = [
    "READ_ONLY",
    "TOOLS",
    "Tool",
    "ToolArgs",
    "ToolContext",
    "ToolResult",
    "WriteToolError",
    "call",
    "catalogue",
    "register",
]
