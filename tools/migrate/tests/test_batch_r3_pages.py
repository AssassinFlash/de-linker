import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from batch_r3_pages import page_changes


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
