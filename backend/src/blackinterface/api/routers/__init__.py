"""HTTP surface, one module per family of endpoints.

Registration order is preserved in `app.py` and is not incidental: it is the
order paths appear in `backend/openapi.json`, and therefore in the generated
`schema.d.ts`. Reordering produces a diff that looks like a contract change.
"""

from blackinterface.api.routers import (
    agent,
    auth,
    diagram,
    health,
    issues,
    live,
    me,
    projects,
    station,
    summary,
)

__all__ = [
    "agent",
    "auth",
    "diagram",
    "health",
    "issues",
    "live",
    "me",
    "projects",
    "station",
    "summary",
]
