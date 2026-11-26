import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import batch_r3_pages as batch
from batch_r3_pages import page_changes, services_story_photo


def test_home_desk_preserves_primary_and_headline_on_rerun() -> None:
    hero = (
        "<h1>Linking Value. Serving You.</h1>"
        '<div class="hero-capsules" data-linker-planner-entry="home-hero">'
        '<a href="/solution-configurator/">Compare systems</a></div>'
    )
    result = page_changes("home", "en", hero, {})
    assert result.startswith(hero)
    assert result.count("[linker_whatsapp]") == 1
    assert page_changes("home", "en", result, {}) == result


def test_solution_corrects_only_the_conflicting_project_and_preserves_card_text() -> (
    None
):
    source = (
        '<div class="lk-topbar"><a href="mailto:sales@de-linker.com">sales@de-linker.com</a></div>'
        '<div class="lk-story-media-tag">UTILITY BESS · 2.5 MWH</div>'
        "<p>Stefan Hartmann</p><p>On a 2.5 MWh project, having a dedicated technical team "
        "coordinating the container specification and delivery schedule made the process very manageable.</p>"
        "<div>1.2 MWh Liquid-Cooled System</div><p>Another customer’s unedited words.</p>"
        '<section id="contact"><a class="lk-btn-outline">Contact</a></section>'
    )
    result = page_changes("solution", "en", source, {})
    assert "COMMERCIAL BESS · 1.2 MWH" in result
    assert "1.2 MWh project" in result
    assert "coordinating the liquid-cooled system specification" in result
    assert "<p>Another customer’s unedited words.</p>" in result
    assert page_changes("solution", "en", result, {}) == result


def test_services_photo_changes_only_the_image_on_stefans_card() -> None:
    old = "/wp-content/uploads/2026/09/linker-partners-on-bess-support.webp"
    new = "/wp-content/uploads/2026/11/linker-trusted-on-commercial-bess-r3.webp"
    media = {"src": new, "srcset": f"{new} 1376w", "width": 1376, "height": 768}
    for alt in (
        "Project partners on Linker support",
        "Projektpartner über den Support von Linker",
    ):
        photo = f'<img alt="{alt}" loading="lazy" src="{old}" srcset="{old} 2336w" sizes="(max-width: 768px) 132px, 248px"/>'
        card = (
            '<div class="lk-story-card"><div class="lk-story-hero-media">'
            + photo
            + '</div><div class="lk-story-name">Stefan Hartmann</div><p>1.2 MWh</p></div>'
        )
        other = card.replace("Stefan Hartmann", "Dirk van de Berg")
        source = "<h1>Services</h1>" + other + card + other
        expected = (
            card.replace(old, new)
            .replace("2336w", "1376w")
            .replace("/>", ' width="1376" height="768"/>')
        )
        result = services_story_photo(source, media)
        assert result == "<h1>Services</h1>" + other + expected + other
        assert services_story_photo(result, media) == result


def test_services_read_uses_the_page_pair_without_a_recovery_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    photo = {
        "src": "/wp-content/uploads/2026/11/linker-trusted-on-commercial-bess-r3.webp",
        "srcset": "story.webp 1376w",
        "width": 1376,
        "height": 768,
    }
    card = (
        '<div class="lk-story-card"><img src="/wp-content/uploads/2026/09/linker-partners-on-bess-support.webp"/>'
        '<div class="lk-story-name">Stefan Hartmann</div></div>'
    )
    current = services_story_photo(card, photo)
    pages = {"2748": current, "6700": current}
    monkeypatch.setattr(batch.pairs, "read", lambda *_: {"pages": pages})
    monkeypatch.setattr(
        batch, "media_call", lambda *_, **__: {"photos": {batch.STORY: photo}}
    )
    folder = tmp_path / "unused"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "batch_r3_pages.py",
            "--wp",
            "wp",
            "--backup-dir",
            str(folder),
            "--services-story-only",
            "read",
        ],
    )
    batch.main()
    pages["6700"] = card
    with pytest.raises(ValueError, match="expected state"):
        batch.main()
    assert not folder.exists()
