"""Danh mục tool của agent. Chỉ đọc, và chỉ đọc bằng cấu trúc — xem `registry`.

Import package này **chính là** thứ đăng ký các tool. Không cái nào tự đăng ký
từ một đường plugin hay một file cấu hình: tập việc agent làm được là một danh
sách nằm trong source control, soát được bằng một cái diff.
"""

from blackinterface.agent.tools import station  # noqa: F401  (import là để đăng ký tool)
from blackinterface.agent.tools.registry import (
    READ_ONLY,
    TOOLS,
    Tool,
    ToolContext,
    WriteToolError,
    authorize,
    catalogue,
    register,
    result,
)

__all__ = [
    "READ_ONLY",
    "TOOLS",
    "Tool",
    "ToolContext",
    "WriteToolError",
    "authorize",
    "catalogue",
    "register",
    "result",
]
