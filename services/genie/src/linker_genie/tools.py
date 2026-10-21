"""Names and limits every module of a turn shares, defined once.

`agent`, `route`, `understand`, `page` and `facts` import each other in a chain; the
constants they all read live here so that none of them copies another's.
"""

from __future__ import annotations

# Tool calls one turn makes, the route's and the model's together
# (docs/specs/13-genie.md §B: "每轮 ≤4 次工具调用").
MAX_TOOL_CALLS = 4
# The page read this process runs itself (page.py, #234).
READ_PAGE = "linker/read-page"
# The saved solution this process reads through the shell's read-only ability
# (solution.py, #496).
READ_SOLUTION = "linker/read-solution"
# The attachments this process reads itself (attachments.py, #236): one tool call in
# the turn log per file read, so the quality check sees what the answer read.
READ_ATTACHMENT = "linker/read-attachment"
