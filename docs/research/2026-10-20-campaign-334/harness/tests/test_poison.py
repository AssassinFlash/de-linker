"""A temporary keyword index can be poisoned. The published index cannot."""

from __future__ import annotations

from pathlib import Path

import pytest

from cases import by_id
from poison import CLEAN, POISON, is_published, refuse_published, search


def test_search_returns_the_planted_chunk_and_the_clean_one(tmp_path: Path) -> None:
    question = by_id()["V1"].question
    hits = search(tmp_path / "index.sqlite", question)
    assert any(POISON in hit for hit in hits)
    assert any(CLEAN in hit for hit in hits)


def test_published_index_is_refused_before_it_is_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    published = tmp_path / "published"
    published.mkdir()
    db = published / "index.sqlite"
    db.write_bytes(b"keep")
    monkeypatch.setattr("poison.PUBLISHED", (published,))
    with pytest.raises(SystemExit):
        search(db, "H2-10K-T3")
    assert db.read_bytes() == b"keep"


def test_symlinked_published_root_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    db = real / "index.sqlite"
    db.write_bytes(b"keep")
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.setattr("poison.PUBLISHED", (link,))
    assert is_published(db) is True
    with pytest.raises(SystemExit):
        search(db, "H2-10K-T3")
    assert db.read_bytes() == b"keep"
    monkeypatch.setattr("poison.PUBLISHED", (real,))
    alias = tmp_path / "alias.sqlite"
    alias.symlink_to(db)
    with pytest.raises(SystemExit):
        search(alias, "H2-10K-T3")
    assert db.read_bytes() == b"keep"
    assert alias.is_symlink()


def test_real_published_roots_are_refused_and_the_campaign_dir_is_not() -> None:
    home_index = (
        Path.home() / "de-linker-data" / "index" / "builds" / "x" / "index.sqlite"
    )
    with pytest.raises(SystemExit):
        refuse_published(home_index)
    with pytest.raises(SystemExit):
        refuse_published(Path("/opt/linker-genie/index"))
    campaign = (
        Path.home()
        / "de-linker-data"
        / "campaign-334"
        / "poison-index"
        / "index.sqlite"
    )
    assert is_published(campaign) is False
    refuse_published(campaign)
