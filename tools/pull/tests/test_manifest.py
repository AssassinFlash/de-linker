"""The manifest of a snapshot and the comparison of two."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from linker_pull import manifest
from linker_pull.sqldump import Insert, Value, read

FIXTURE = Path(__file__).parent / "fixtures" / "live-dump.sql"


def stats_of(lines: list[str]) -> manifest.DatabaseStats:
    stats = manifest.DatabaseStats()
    for _ in stats.observe(read(iter(lines))):
        pass
    return stats


def test_rows_and_posts_are_counted_per_table() -> None:
    stats = stats_of(FIXTURE.read_text().splitlines(keepends=True))

    assert stats.rows["wp_users"] == 3
    assert stats.rows["wp_usermeta"] == 20
    assert dict(stats.posts) == {
        "page/publish": 1,
        "product/publish": 1,
        "attachment/inherit": 1,
        "shop_order_placehold/draft": 1,
    }


def test_every_table_of_the_dump_is_listed_the_row_less_ones_too() -> None:
    # "每张表" (docs/specs/6-live-pull.md): the fixture's wp_linker_ai_conversation
    # has a CREATE TABLE and no rows, as mysqldump writes an empty table.
    stats = stats_of(FIXTURE.read_text().splitlines(keepends=True))

    created = {
        match.group(1)
        for match in re.finditer(r"CREATE TABLE `([^`]+)`", FIXTURE.read_text())
    }
    assert set(stats.tables()) == created
    empty = stats.tables()["wp_linker_ai_conversation"]
    assert empty["rows"] == 0
    assert empty["sha256"] == hashlib.sha256(b"").hexdigest()


def test_a_changed_row_changes_its_table_s_hash_and_no_other() -> None:
    lines = FIXTURE.read_text().splitlines(keepends=True)
    before = stats_of(lines).tables()
    items = list(read(iter(lines)))
    users = next(
        item
        for item in items
        if isinstance(item, Insert) and item.table.name == "wp_users"
    )
    users.rows[0][9] = Value.of("Owner (renamed)")
    after = manifest.DatabaseStats()
    for _ in after.observe(iter(items)):
        pass

    changed = {name for name, table in after.tables().items() if table != before[name]}
    assert changed == {"wp_users"}


def test_every_file_but_the_manifest_is_listed_with_its_hash(tmp_path: Path) -> None:
    (tmp_path / "uploads" / "2026").mkdir(parents=True)
    (tmp_path / "uploads" / "2026" / "a.webp").write_bytes(b"image")
    (tmp_path / "db.sql.gz").write_bytes(b"dump")
    (tmp_path / manifest.NAME).write_text("{}")
    (tmp_path / "link").symlink_to(tmp_path / "db.sql.gz")

    entries = manifest.file_entries(tmp_path)

    assert entries == {
        "db.sql.gz": {"sha256": hashlib.sha256(b"dump").hexdigest(), "bytes": 4},
        "uploads/2026/a.webp": {
            "sha256": hashlib.sha256(b"image").hexdigest(),
            "bytes": 5,
        },
    }


def snapshot_manifest(
    files: dict[str, str], tables: dict[str, tuple[int, str]], posts: dict[str, int]
) -> dict[str, Any]:
    return {
        "format": manifest.FORMAT,
        "files": {
            path: {"sha256": digest * 64, "bytes": 1} for path, digest in files.items()
        },
        "database": {
            "tables": {
                name: {"rows": rows, "sha256": digest * 64}
                for name, (rows, digest) in tables.items()
            },
            "posts": posts,
        },
    }


def test_two_manifests_compare_file_by_file_and_table_by_table(tmp_path: Path) -> None:
    old = snapshot_manifest(
        {
            "db.sql.gz": "a",
            "uploads/x.webp": "b",
            "uploads/gone.pdf": "c",
            "plugins/p/p.php": "d",
        },
        {"wp_options": (10, "a"), "wp_posts": (5, "b"), "wp_old": (1, "c")},
        {"product/publish": 106, "attachment/inherit": 2755},
    )
    new = snapshot_manifest(
        {
            "db.sql.gz": "e",
            "uploads/x.webp": "b",
            "uploads/new.pdf": "f",
            "plugins/p/p.php": "d",
        },
        {"wp_options": (12, "f"), "wp_posts": (5, "b"), "wp_new": (2, "a")},
        {"product/publish": 107, "attachment/inherit": 2755},
    )
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / manifest.NAME).write_text(json.dumps(old))

    changes = manifest.diff(manifest.read(tmp_path / "old"), new)

    assert changes.added == ["uploads/new.pdf"]
    assert changes.removed == ["uploads/gone.pdf"]
    assert changes.changed == ["db.sql.gz"]
    assert changes.unchanged == 2
    assert changes.tables == {
        "wp_new": (None, 2),
        "wp_old": (1, None),
        "wp_options": (10, 12),
    }
    assert changes.posts == {"product/publish": (106, 107)}
    assert list(changes.lines()) == [
        "files: 1 added, 1 removed, 1 changed, 2 unchanged",
        "  + uploads/new.pdf",
        "  - uploads/gone.pdf",
        "  ~ db.sql.gz",
        "tables: 3 changed",
        "  ~ wp_new: (none) -> 2 rows",
        "  ~ wp_old: 1 -> (none) rows",
        "  ~ wp_options: 10 -> 12 rows",
        "posts: 1 counts changed",
        "  ~ product/publish: 106 -> 107",
    ]
