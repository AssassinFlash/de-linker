#!/usr/bin/env python3
"""Add the reviewed trade-standard row to the EN/DE Services & Support pair.

The content lives in WordPress, not this repository. Planning is pure and
idempotent; ``--write`` uses the existing reviewed-pair transaction so a
partially changed EN/DE pair cannot be saved. The row's styling is owned by
WindPress in ``service-intro.css``; this migration changes only page markup.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent


def _module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pair = _module("reviewed_pair", "reviewed_page_pair.py")
writer = _module("content_writer", "repair-legal-script.py")

SERVICE_LEDGER_INSERTION_POINT = '<div class="service-ledger">'
ROOT = 'id="service-redesign"'

EN_MARKUP = """<div class="lk-trade-standards" aria-label="Services for trade customers">
<dl>
<div><dt>Delivery</dt><dd>Orders ship from our warehouse. Where delivery is required, freight is quoted separately for the destination.</dd></div>
<div><dt>Training</dt><dd>We provide product training for installers.</dd></div>
<div><dt>After-sales</dt><dd>Our team handles after-sales support. Warranty terms follow the order.</dd></div>
<div><dt>Resellers</dt><dd>We work with distributors and resellers.</dd></div>
</dl>
</div>"""

PREVIOUS_EN_MARKUP = EN_MARKUP.replace(
    'aria-label="Services for trade customers"',
    'aria-label="Trade standards"',
)
DE_MARKUP = """<div class="lk-trade-standards" aria-label="Leistungen für Fachpartner">
<dl>
<div><dt>Lieferung</dt><dd>Bestellungen versenden wir ab Lager. Bei Lieferungen berechnen wir die Fracht gesondert nach Zielort.</dd></div>
<div><dt>Produktschulung</dt><dd>Für Installateure bieten wir Produktschulungen an.</dd></div>
<div><dt>Kundendienst</dt><dd>Unser Team übernimmt den Kundendienst. Garantiebedingungen richten sich nach der Bestellung.</dd></div>
<div><dt>Wiederverkäufer</dt><dd>Wir arbeiten mit Distributoren und Wiederverkäufern zusammen.</dd></div>
</dl>
</div>"""

MARKUP = (EN_MARKUP, DE_MARKUP)
FORBIDDEN = (
    "Incoterms",
    "EXW",
    "DAP",
    "free shipping",
    "kostenloser Versand",
    "business days",
    "Werktage",
)


def _insert_block(content: str, block: str, anchor: str) -> str:
    if block in content:
        return content
    if content.count(anchor) != 1:
        raise ValueError("Services page changed; the reviewed anchor is not unique")
    return content.replace(anchor, block + "\n" + anchor, 1)


def plan_page(content: str, language: str) -> str:
    """Add exactly one reviewed standards row, preserving every other byte."""
    if language not in {"en", "de"} or content.count(ROOT) != 1:
        raise ValueError("Expected one EN or DE Services & Support page")
    markup = EN_MARKUP if language == "en" else DE_MARKUP
    if any(value in markup for value in FORBIDDEN):
        raise ValueError("Forbidden trade promise entered the reviewed row")
    if markup in content:
        return content
    if language == "en":
        previous_count = content.count(PREVIOUS_EN_MARKUP)
        if previous_count == 1:
            return content.replace(PREVIOUS_EN_MARKUP, markup, 1)
        if previous_count > 1:
            raise ValueError("Services page holds more than one previous reviewed row")
    return _insert_block(content, markup, SERVICE_LEDGER_INSERTION_POINT)


def plan_pair(english: str, german: str) -> tuple[str, str]:
    """Accept a complete old or final pair and refuse a mixed increment."""
    return plan_page(english, "en"), plan_page(german, "de")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def prune_page_backups(backup_dir: Path, keep: int = 3) -> list[str]:
    """Keep the bounded set of completed page snapshots after a verified write."""
    backups = sorted(backup_dir.glob("industry-standards-before-*.json"), reverse=True)
    removed = []
    for path in backups[keep:]:
        payload = json.loads(path.read_text())
        if payload.get("readback_verified"):
            path.unlink()
            removed.append(str(path))
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument("--en", type=int, default=2748)
    parser.add_argument("--de", type=int, default=6700)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--rollback", type=Path)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--full-backup", type=Path)
    args = parser.parse_args()
    if args.write and args.rollback:
        parser.error("--write and --rollback are mutually exclusive")
    if args.rollback:
        backup = json.loads(args.rollback.read_text())
        current = pair.read(args.wp, args.en, args.de)
        changes = backup["changes"]
        if current["pages"] != {
            str(change["id"]): change["after"] for change in changes
        }:
            raise RuntimeError("The reviewed pages changed after the backup was made")
        pair.invoke(
            args.wp,
            {
                "mode": "restore",
                "changes": [
                    {
                        "id": change["id"],
                        "before": change["after"],
                        "after": change["before"],
                    }
                    for change in changes
                ],
                "metadata_before": current["metadata"],
                "metadata_restore": backup["snapshot"]["metadata"],
            },
        )
        restored = pair.read(args.wp, args.en, args.de)
        if (
            restored["pages"] != backup["snapshot"]["pages"]
            or restored["metadata"] != backup["snapshot"]["metadata"]
        ):
            raise RuntimeError("Rollback readback differs from the pre-write snapshot")
        print(json.dumps({"rolled_back": str(args.rollback)}, indent=2))
        return

    snapshot = pair.read(args.wp, args.en, args.de)
    before = [snapshot["pages"][str(args.en)], snapshot["pages"][str(args.de)]]
    after = list(plan_pair(*before))
    changes = [
        {"id": page_id, "before": old, "after": new}
        for page_id, old, new in zip((args.en, args.de), before, after, strict=True)
    ]
    result = {
        "write": args.write,
        "pages": [
            {
                "id": change["id"],
                "changed": change["before"] != change["after"],
                "before_sha256": digest(change["before"]),
                "after_sha256": digest(change["after"]),
            }
            for change in changes
        ],
    }
    if not args.write or all(item["changed"] is False for item in result["pages"]):
        print(json.dumps(result, indent=2))
        return
    if args.backup_dir is None:
        parser.error("--write requires --backup-dir")
    if urlsplit(snapshot["home"]).hostname in {"de-linker.com", "www.de-linker.com"}:
        if (
            args.full_backup is None
            or not (args.full_backup / "manifest.json").is_file()
        ):
            parser.error("Production requires a completed --full-backup")
        writer.verify_full_backup(args.full_backup)

    args.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = args.backup_dir / f"industry-standards-before-{stamp}.json"
    with backup_path.open("x") as handle:
        json.dump({"snapshot": snapshot, "changes": changes}, handle, indent=2)
    backup_path.chmod(0o600)
    pair.invoke(
        args.wp,
        {
            "mode": "adopt",
            "changes": changes,
            "metadata_before": snapshot["metadata"],
        },
    )
    readback = pair.read(args.wp, args.en, args.de)
    if readback["pages"] != {str(args.en): after[0], str(args.de): after[1]}:
        raise RuntimeError(f"Paired readback differs; backup: {backup_path}")
    saved = json.loads(backup_path.read_text())
    saved["readback_verified"] = True
    backup_path.write_text(json.dumps(saved, indent=2))
    removed = prune_page_backups(args.backup_dir)
    print(
        json.dumps(
            {
                **result,
                "backup": str(backup_path),
                "backups_removed": removed,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
