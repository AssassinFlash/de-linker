"""The cutover of de-linker.com onto the new tree (docs/specs/17-cutover.md).

Every step runs against a `Target`, which is one local WordPress instance or
the production host; the steps themselves never know which. The local drill
(`linker-cutover drill`) runs the same steps against an instance, rolls them
back and runs them again, which is the article of evidence spec 17 asks for
before the maintenance window.
"""

from __future__ import annotations

from linker_cutover.target import CutoverError, Target, local_target, remote_target

__all__ = ["CutoverError", "Target", "local_target", "remote_target"]
