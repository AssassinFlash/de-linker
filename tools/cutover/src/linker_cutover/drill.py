"""The local rehearsal of spec 17: clean snapshot → switch → roll back → switch again.

Spec 17's precondition is that the whole switch has been drilled locally twice
before the maintenance window. This module is that drill: it runs the same
`steps` the window runs against a local instance, rolls the instance back from
the backup the drill itself took, and runs the switch a second time. What it
asserts is what the window depends on:

- the pre-cutover state is the loaded snapshot (the old plugins are there), so
  the drill is rehearsing the same state production is in;
- the rollback puts the site back — plugin list, activation and the entry
  points of the read-only subset all return to what they were;
- the second pass ends where the first one did, so the window is not a
  one-shot that cannot be re-run.

The data migrations run in plan mode (no `--write`). They rewrite products,
facts and German objects; a drill that wrote them would leave the instance
unable to be the clean state the next drill needs, and 9-i18n needs a
translator service the local isolation layer blocks by design. Their command
lines are part of the evidence, and the window is where they write.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from linker_cutover import backup as backup_module
from linker_cutover import plan
from linker_cutover import steps as cutover
from linker_cutover.target import CutoverError, Target


@dataclass
class Drill:
    """One rehearsal, and everything it observed."""

    target: Target
    repository: Path | None = field(default=None)
    home: Path | None = field(default=None)
    staging: Path | None = field(default=None)
    snippets: Path | None = field(default=None)
    administrator: str = ""
    steps: list[dict[str, object]] = field(default_factory=list)

    def run(self) -> dict[str, object]:
        """Run the whole rehearsal and return its record."""
        if self.repository is None or self.home is None or self.staging is None:
            raise CutoverError(
                "the drill needs a repository, a data home and a staging directory"
            )
        before = self.fingerprint()
        self._require_pre_cutover(before)
        try:
            return self._rehearse(before)
        except CutoverError:
            # A rehearsal that dies must not leave the playground locked: the
            # site stays under construction for the rest of the run otherwise,
            # and the next attempt would measure a site nobody meant to leave
            # that way. The production window is different — its maintenance
            # step is its own command, and this path never touches the host.
            # Whatever this does, the failure being handled is the one that
            # gets raised: a second error here would hide the first.
            print("drill: failed — taking the site out of maintenance mode")
            try:
                cutover.maintenance(self.target, on=False)
            except CutoverError as error:
                print(f"drill: maintenance mode was not changed: {error}")
            raise

    def _rehearse(self, before: dict[str, object]) -> dict[str, object]:
        """The two passes, with the rollback between them."""
        print("drill: first pass")
        first_backup = self._pass(number=1)
        after_first = self.fingerprint()

        print("drill: rollback")
        record = cutover.rollback(self.target, backup=first_backup)
        self._record(record)
        restored = self.fingerprint()
        if restored != before:
            raise CutoverError(
                "the rollback did not restore the pre-cutover state: "
                f"{_difference(before, restored)}"
            )

        print("drill: second pass")
        self._pass(number=2)
        after_second = self.fingerprint()
        if after_second != after_first:
            raise CutoverError(
                "the second pass ended in a different state: "
                f"{_difference(after_first, after_second)}"
            )

        return {
            "target": self.target.label,
            "run_at": datetime.now(UTC).isoformat(),
            "backup": str(first_backup),
            "before": before,
            "after_first": after_first,
            "after_rollback": restored,
            "after_second": after_second,
            "steps": self.steps,
        }

    def fingerprint(self) -> dict[str, object]:
        """The state the drill compares: what is installed, active, and answering."""
        plugins = self.target.wp("plugin", "list", "--fields=name,status,version")
        products = self.target.wp(
            "post",
            "list",
            "--post_type=product",
            "--post_status=publish",
            "--format=count",
        )
        maintenance = self.target.wp("maintenance-mode", "status").strip()
        answers: dict[str, int] = {}
        for path in plan.VERIFY_PATHS:
            status, _ = self.target.http(path, cache_buster="drill")
            answers[path] = status
        return {
            "plugins": sorted(plugins.splitlines()),
            "published_products": products.strip(),
            "maintenance": maintenance,
            "answers": answers,
        }

    def _require_pre_cutover(self, fingerprint: dict[str, object]) -> None:
        """Fail early unless the instance is the loaded snapshot, not a switched one."""
        plugins = fingerprint["plugins"]
        assert isinstance(plugins, list)
        missing = [
            slug
            for slug in plan.LEGACY_PLUGINS
            if not any(str(row).startswith(f"{slug}\t") for row in plugins)
        ]
        if len(missing) == len(plan.LEGACY_PLUGINS):
            raise CutoverError(
                "the instance has none of the legacy plugins — load a fresh snapshot "
                "before drilling (`just pull load <name> <snapshot> --live-code`)"
            )

    def _pass(self, *, number: int) -> Path:
        assert self.repository is not None and self.home is not None
        assert self.staging is not None and self.snippets is not None
        taken = backup_module.create(self.target, self.home)
        self._record(
            cutover.Result(
                "backup",
                [f"{taken.files} files, dump sha256 {taken.dump_sha256[:16]}…"],
                [str(taken.directory)],
            )
        )
        self._record(cutover.maintenance(self.target, on=True))
        self._record(
            cutover.deploy(
                self.target, repository=self.repository, staging=self.staging
            )
        )
        self._record(
            cutover.export_snippets(self.target, self.snippets / f"pass{number}")
        )
        self._record(
            cutover.remove_legacy(
                self.target, snippets=self.snippets / f"pass{number}" / "snippets.json"
            )
        )
        self._record(
            cutover.migrations(
                self.repository,
                self.target,
                backup=taken.directory,
                administrator=self.administrator,
                writes=False,
            )
        )
        # Writes: retiring the stale template changes what the site serves, and
        # the rollback's database import is what has to bring it back.
        self._record(cutover.retire_stale_schema(self.target, writes=True))
        self._record(cutover.hygiene(self.target, backup=taken.directory, writes=False))
        self._record(cutover.maintenance(self.target, on=False))
        self._record(cutover.verify(self.target, cache_buster=f"drill{number}"))
        return taken.directory

    def _record(self, result: cutover.Result) -> None:
        print(result.describe())
        self.steps.append(
            {"step": result.step, "actions": result.actions, "notes": result.notes}
        )


def _difference(before: dict[str, object], after: dict[str, object]) -> str:
    """What changed between two fingerprints, for the failure message."""
    changed = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changed.append(f"{key}: {before.get(key)!r} -> {after.get(key)!r}")
    return "; ".join(changed) or "nothing"


def write(record: dict[str, object], destination: Path) -> Path:
    """Write a drill's record where the acceptance protocol keeps evidence."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination
