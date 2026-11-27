"""The reviewed body edits are reversible across each native EN/DE page pair."""

import json
import runpy
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

MIGRATE = Path(__file__).resolve().parents[1]
ROOT = MIGRATE.parents[1]
SCRIPT = MIGRATE / "batch_s3b_body_copy.py"
COPY = json.loads((MIGRATE / "batch-s3b-body-copy.json").read_text())
PAIRS = [(13, 6913), (862, 6865), (826, 6869), (2748, 6700), (749, 6923)]


def site(tmp_path: Path, *, home: str = "http://review.test") -> Path:
    data = {
        "home": home,
        "writes": [],
        "pairs": {
            str(en): {
                "home": home,
                "pages": {
                    str(pid): "<style>.banner{color:red}</style>\n"
                    + "\n".join(row[0] for row in COPY[str(pid)])
                    + '\n<script data-site-js="example">const s = "1";</script>'
                    for pid in (en, de)
                },
                "metadata": {"original": en},
                "current": en not in (13, 826, 2748),
            }
            for en, de in PAIRS
        },
    }
    target = tmp_path / "site.json"
    target.write_text(json.dumps(data))
    return target


def cli(state: Path, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--wp",
            shlex.join([sys.executable, str(MIGRATE / "tests/fake_wp.py"), str(state)]),
            "--backup-dir",
            str(state.parent / "backups"),
            *args,
        ],
        check=ok,
        text=True,
        capture_output=True,
    )


def test_round_trip(tmp_path: Path) -> None:
    state = site(tmp_path)
    original = json.loads(state.read_text())
    cli(state)
    assert json.loads(state.read_text()) == original
    assert not (tmp_path / "backups").exists()
    cli(state, "--apply")
    published = json.loads(state.read_text())
    assert len(published["writes"]) == 5
    for en, de in PAIRS:
        pair = published["pairs"][str(en)]
        for pid in (en, de):
            body = original["pairs"][str(en)]["pages"][str(pid)]
            for before, after in COPY[str(pid)]:
                body = body.replace(before, after)
            assert pair["pages"][str(pid)] == body
        assert pair["current"] == original["pairs"][str(en)]["current"]
        if pair["current"]:
            assert pair["metadata"] != original["pairs"][str(en)]["metadata"]
    backups = list((tmp_path / "backups").glob("*-s3b.json"))
    assert len(backups) == 5
    assert all((path.stat().st_mode & 0o777) == 0o600 for path in backups)
    cli(state, "--apply")
    assert json.loads(state.read_text()) == published
    cli(state, "--restore")
    restored = json.loads(state.read_text())
    assert restored["pairs"] == original["pairs"]
    assert len(restored["writes"]) == 10
    cli(state, "--restore")
    assert json.loads(state.read_text()) == restored


@pytest.mark.parametrize("change", ["duplicate", "missing", "one-language"])
def test_rejects_ambiguous_pairs_before_any_write(tmp_path: Path, change: str) -> None:
    state = site(tmp_path)
    data = json.loads(state.read_text())
    pages = data["pairs"]["749"]["pages"]
    before, after = COPY["749"][0]
    if change == "duplicate":
        pages["749"] += before
    else:
        pages["749"] = pages["749"].replace(
            before, after if change == "one-language" else ""
        )
    state.write_text(json.dumps(data))
    assert cli(state, "--apply", ok=False).returncode
    assert json.loads(state.read_text()) == data


def test_restore_refuses_changed_page_and_translator_state(tmp_path: Path) -> None:
    state = site(tmp_path)
    cli(state, "--apply", "--page", "about")
    data = json.loads(state.read_text())
    data["pairs"]["862"]["metadata"] = {"newer": True}
    state.write_text(json.dumps(data))
    assert (
        "changed since publication"
        in cli(state, "--restore", "--page", "about", ok=False).stderr
    )
    assert json.loads(state.read_text()) == data


def test_production_requires_verified_complete_backup(tmp_path: Path) -> None:
    state = site(tmp_path, home="https://de-linker.com")
    result = cli(state, "--apply", "--page", "home", ok=False)
    assert "--full-backup" in result.stderr
    (tmp_path / "manifest.json").write_text("{}")
    result = cli(
        state, "--apply", "--page", "home", "--full-backup", str(tmp_path), ok=False
    )
    assert "not a complete production snapshot" in result.stderr
    assert json.loads(state.read_text())["writes"] == []


def test_all_reviewed_replacements_pass_public_copy_wordlists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "tools/checks"))
    terms: dict[str, Any] = runpy.run_path(str(ROOT / "tools/checks/commerce-terms.py"))
    common = terms["load_terms"]()
    german = json.loads((ROOT / "plugins/linker-i18n/data/banned-de.json").read_text())[
        "words"
    ]
    assert sum(len(rows) for rows in COPY.values()) == 36
    for en, de in PAIRS:
        for pid in (en, de):
            words = common + (german if pid == de else [])
            patterns = [(word, terms["term_pattern"](word)) for word in words]
            for _, after in COPY[str(pid)]:
                assert terms["matched_terms"](after, patterns) == [], (pid, after)
