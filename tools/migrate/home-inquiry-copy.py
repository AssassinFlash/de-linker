#!/usr/bin/env python3
"""Replace the two reviewed homepage scene strings without reserializing HTML.

This module plans content only. The paired writer separately checks the backup,
native language pair, transaction, translation baseline and independent readback.
"""

from __future__ import annotations

import re

COPY = {
    "en": (
        "Order online or quote a project.",
        "Use the partner portal for direct wholesale orders, or request a quote "
        "for the equipment your installation needs.",
        "Net prices and project quotes.",
        "Approved partners can view net prices when signed in. Our team prepares "
        "equipment quotes in response to your inquiry, whether or not you have an account.",
    ),
    "de": (
        "Online bestellen oder ein Projekt anfragen.",
        "Nutzen Sie das Partnerportal für direkte Großhandelsbestellungen, oder "
        "fordern Sie ein Angebot für die Geräte an, die Ihre Installation benötigt.",
        "Nettopreise und Projektangebote.",
        "Mit einem freigeschalteten Konto sehen Sie Nettopreise, wenn Sie angemeldet "
        "sind. Unser Team erstellt Angebote für die benötigten Geräte auf Anfrage, "
        "auch ohne Kundenkonto.",
    ),
}

# This exact saved LC structure is the migration boundary. A layout change must
# be reviewed rather than guessed by a broad document-wide text replacement.
SCENE = re.compile(
    r'(<div class="scene-card home-scene-card"><div class="scene-card-body">)'
    r"<h4>([^<]*)</h4><p>([^<]*)</p>"
)


def plan_pair(english: str, german: str) -> tuple[str, str]:
    """Accept the complete old pair or complete final pair; reject partial edits."""
    planned: list[str] = []
    states: list[str] = []
    for language, content in (("en", english), ("de", german)):
        matches = list(SCENE.finditer(content))
        if len(matches) != 1:
            raise ValueError(f"Expected one unchanged {language} scene structure")
        match = matches[0]
        old_heading, old_body, heading, body = COPY[language]
        observed = (match[2], match[3])
        if observed == (old_heading, old_body):
            states.append("old")
        elif observed == (heading, body):
            states.append("final")
        else:
            raise ValueError(f"Unreviewed {language} scene text; nothing planned")
        replacement = f"{match[1]}<h4>{heading}</h4><p>{body}</p>"
        planned.append(content[: match.start()] + replacement + content[match.end() :])
    if states[0] != states[1]:
        raise ValueError("Partially changed language pair; inspect before retrying")
    return planned[0], planned[1]


def main() -> None:
    """Candidate application is deliberately limited to the owned local instance."""
    import argparse
    import hashlib
    import json
    from datetime import UTC, datetime
    from pathlib import Path

    from reviewed_page_pair import invoke, read

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--rollback", type=Path)
    args = parser.parse_args()
    current = read(args.wp, 13, 6913)
    if current["home"] != "http://127.0.0.1:9410":
        parser.error(
            "Candidate writes and reads require the owned home_image_loading instance"
        )
    before = tuple(current["pages"][str(i)] for i in (13, 6913))
    target_metadata = None
    if args.rollback:
        receipt = json.loads(args.rollback.read_text())
        original = Path(receipt["backup"])
        if (
            hashlib.sha256(original.read_bytes()).hexdigest()
            != receipt["backup_sha256"]
        ):
            raise ValueError("Original recovery record changed; refusing rollback")
        saved = json.loads(original.read_text())
        if saved["before"]["home"] != current["home"]:
            raise ValueError("Rollback backup belongs to a different environment")
        expected = receipt["after"]
        if (
            current["pages"] != expected["pages"]
            or current["metadata"] != expected["metadata"]
        ):
            raise ValueError("Concurrent page or baseline edit; refusing rollback")
        after = tuple(saved["before"]["pages"][str(i)] for i in (13, 6913))
        target_metadata = saved["before"]["metadata"]
    else:
        after = plan_pair(*before)
    if before == after:
        if not current["current"]:
            raise ValueError(
                "Text is already final but its translation baseline is stale"
            )
        print(json.dumps({"changed": False, "baseline_current": True}))
        return
    changes = [
        {"id": i, "before": old, "after": new}
        for i, old, new in zip((13, 6913), before, after, strict=True)
    ]
    report = {
        "write": args.write,
        "pages": [
            {
                "id": change["id"],
                "before_sha256": hashlib.sha256(change["before"].encode()).hexdigest(),
                "after_sha256": hashlib.sha256(change["after"].encode()).hexdigest(),
                "backslashes_before": change["before"].count("\\"),
                "backslashes_after": change["after"].count("\\"),
            }
            for change in changes
        ],
    }
    if args.write:
        args.evidence.mkdir(parents=True, exist_ok=True)
        path = args.evidence / f"home-copy-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}.json"
        # A small exact row/value recovery point, not another full database copy.
        record = {
            "before": current,
            "planned": changes,
            "mode": "restore" if args.rollback else "adopt",
        }
        with path.open("x") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)
        path.chmod(0o600)
        payload = {
            "mode": record["mode"],
            "changes": changes,
            "metadata_before": current["metadata"],
        }
        if target_metadata is not None:
            payload["metadata_restore"] = target_metadata
        write_receipt = invoke(args.wp, payload)
        observed = read(args.wp, 13, 6913)
        if observed["pages"] != {
            str(i): text for i, text in zip((13, 6913), after, strict=True)
        }:
            raise RuntimeError(f"Fresh content readback failed; inspect backup {path}")
        if target_metadata is not None:
            if observed["metadata"] != target_metadata:
                raise RuntimeError(
                    f"Fresh rollback metadata readback failed; inspect {path}"
                )
        elif (
            not observed["current"]
            or observed["metadata"] != write_receipt["expected_metadata"]
        ):
            raise RuntimeError(f"Fresh baseline readback failed; inspect {path}")
        result_path = path.with_suffix(".result.json")
        result = {
            "backup": str(path),
            "backup_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "after": observed,
            "write_receipt": write_receipt,
        }
        # Keep the only exact pre-write recovery point immutable. Failure or
        # interruption writing this separate receipt cannot truncate it.
        with result_path.open("x") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        result_path.chmod(0o600)
        report["backup"] = str(path)
        report["result"] = str(result_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
