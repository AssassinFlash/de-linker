"""manifest.json of a snapshot, and the difference between two of them.

The manifest lists every file of the snapshot with its sha256 and size, and
every table of the database dump with its row count and the sha256 of its
rows as written; tools/pull/manifest.schema.json describes it. Two manifests
compare file by file and table by table (`linker-pull diff`).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from linker_pull.anonymize import TABLE_PREFIX
from linker_pull.sqldump import CREATE_TABLE, Insert, Line

FORMAT = 1
NAME = "manifest.json"
# Read in pieces this large while hashing.
CHUNK = 1 << 20


class DatabaseStats:
    """Rows and a sha256 per table, and posts per type and status, of a dump as it is written."""

    def __init__(self) -> None:
        self.rows: Counter[str] = Counter()
        self.hashes: dict[str, Any] = {}
        self.posts: Counter[str] = Counter()

    def observe(self, items: Iterator[Line]) -> Iterator[Line]:
        for item in items:
            if isinstance(item, Insert):
                self._insert(item)
            else:
                create = CREATE_TABLE.match(item)
                if create:
                    # Every table of the dump is listed — the row-less ones
                    # too ("每张表", docs/specs/6-live-pull.md): a table no
                    # rows were written for, or whose rows the pseudonymizer
                    # dropped, counts 0 rows and hashes nothing.
                    self.hashes.setdefault(create.group(1), hashlib.sha256())
            yield item

    def _insert(self, insert: Insert) -> None:
        table = insert.table
        digest = self.hashes.setdefault(table.name, hashlib.sha256())
        for row in insert.rows:
            digest.update(("(" + ",".join(value.raw for value in row) + ")\n").encode())
        self.rows[table.name] += len(insert.rows)
        if table.name == TABLE_PREFIX + "posts":
            post_type = table.index("post_type")
            post_status = table.index("post_status")
            for row in insert.rows:
                self.posts[f"{row[post_type].text}/{row[post_status].text}"] += 1

    def tables(self) -> dict[str, dict[str, object]]:
        return {
            name: {"rows": self.rows[name], "sha256": self.hashes[name].hexdigest()}
            for name in sorted(self.hashes)
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def file_entries(root: Path) -> dict[str, dict[str, object]]:
    """Every file under `root` but the manifest: relative path -> sha256 and size."""
    entries: dict[str, dict[str, object]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative == NAME:
            continue
        entries[relative] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    return entries


def write(root: Path, manifest: dict[str, Any]) -> None:
    (root / NAME).write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")


def read(root: Path) -> dict[str, Any]:
    path = root / NAME if root.is_dir() else root
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError(f"{path} is not a format-{FORMAT} snapshot manifest")
    return data


@dataclass
class Diff:
    """What changed from one snapshot to the next."""

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    unchanged: int = 0
    # table -> (rows before, rows after); None where the table did not exist.
    tables: dict[str, tuple[int | None, int | None]] = field(default_factory=dict)
    posts: dict[str, tuple[int, int]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "files": {
                "added": self.added,
                "removed": self.removed,
                "changed": self.changed,
                "unchanged": self.unchanged,
            },
            "tables": {
                name: {"rows_before": before, "rows_after": after}
                for name, (before, after) in self.tables.items()
            },
            "posts": {
                key: {"before": before, "after": after}
                for key, (before, after) in self.posts.items()
            },
        }

    def lines(self) -> Iterator[str]:
        yield (
            f"files: {len(self.added)} added, {len(self.removed)} removed, "
            f"{len(self.changed)} changed, {self.unchanged} unchanged"
        )
        for mark, paths in (
            ("+", self.added),
            ("-", self.removed),
            ("~", self.changed),
        ):
            for path in paths:
                yield f"  {mark} {path}"
        yield f"tables: {len(self.tables)} changed"
        for name, (before, after) in self.tables.items():
            yield f"  ~ {name}: {_count(before)} -> {_count(after)} rows"
        yield f"posts: {len(self.posts)} counts changed"
        for key, (before, after) in self.posts.items():
            yield f"  ~ {key}: {before} -> {after}"


def diff(old: dict[str, Any], new: dict[str, Any]) -> Diff:
    result = Diff()
    old_files: dict[str, Any] = old["files"]
    new_files: dict[str, Any] = new["files"]
    for path in sorted(old_files.keys() | new_files.keys()):
        if path not in old_files:
            result.added.append(path)
        elif path not in new_files:
            result.removed.append(path)
        elif old_files[path]["sha256"] != new_files[path]["sha256"]:
            result.changed.append(path)
        else:
            result.unchanged += 1
    old_tables: dict[str, Any] = old["database"]["tables"]
    new_tables: dict[str, Any] = new["database"]["tables"]
    for name in sorted(old_tables.keys() | new_tables.keys()):
        before, after = old_tables.get(name), new_tables.get(name)
        if before is None or after is None or before["sha256"] != after["sha256"]:
            result.tables[name] = (
                before["rows"] if before else None,
                after["rows"] if after else None,
            )
    old_posts: dict[str, int] = old["database"]["posts"]
    new_posts: dict[str, int] = new["database"]["posts"]
    for key in sorted(old_posts.keys() | new_posts.keys()):
        if old_posts.get(key, 0) != new_posts.get(key, 0):
            result.posts[key] = (old_posts.get(key, 0), new_posts.get(key, 0))
    return result


def _count(rows: int | None) -> str:
    return "(none)" if rows is None else f"{rows:,}"
