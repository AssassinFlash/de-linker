"""Guard the existing bilingual story photos and their responsive sources."""

import importlib.util
from collections.abc import Callable
from pathlib import Path

import pytest

path = Path(__file__).parents[1] / "home-story-images.py"
spec = importlib.util.spec_from_file_location("home_story_images", path)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PREFIX = "/wp-content/uploads/2026/09/linker-"


def page() -> str:
    return (
        '<div id="home-a"><section id="testimonials">'
        '<article id="story-0"><img src="'
        + PREFIX
        + 'installers-buy-through-linker.webp" alt="One" loading="eager" '
        'decoding="async" width="2048" height="1360" fetchpriority="low"></article>'
        '<article id="story-1"><img src="'
        + PREFIX
        + 'contractors-buy-through-linker.webp" alt="Zwei" loading="eager" '
        'decoding="async" width="2400" height="1600" fetchpriority="low"></article>'
        '<article id="story-2"><img src="'
        + PREFIX
        + 'grid-projects-buy-through-linker.webp" alt="Three" loading="eager" '
        'decoding="async" width="2048" height="1360" fetchpriority="low"></article>'
        "</section><script>const example = \"<img src='unrelated.webp'>\";</script></div>"
    )


def test_responsive_sources_keep_every_existing_byte_and_are_repeatable() -> None:
    original = page()
    result = module.plan(original)
    assert result.count('sizes="(max-width: 600px) 120vw, 2400px"') == 3
    assert result.count('loading="eager"') == 3
    assert "linker-installers-buy-through-linker-768x510.webp 768w" in result
    assert "linker-contractors-buy-through-linker-768x512.webp 768w" in result
    assert "linker-grid-projects-buy-through-linker-1024x680.webp 1024w" in result
    for inserted in module.INSERTIONS.values():
        result = result.replace(inserted, "", 1)
    assert result == original
    assert module.plan(module.plan(original)) == module.plan(original)


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s.replace('loading="eager"', 'loading="lazy"', 1),
        lambda s: s.replace('width="2048"', 'width="2000"', 1),
        lambda s: s.replace('id="story-1"', 'id="story-0"', 1),
        lambda s: s.replace(
            'fetchpriority="low"', 'fetchpriority="low" loading="eager"', 1
        ),
        lambda s: s.replace(
            "</section>",
            '<img src="' + PREFIX + 'grid-projects-buy-through-linker.webp"></section>',
        ),
        lambda s: s.replace('alt="One"', 'alt="One" srcset="other.webp 1w"', 1),
    ],
)
def test_ambiguous_or_changed_original_is_rejected(
    change: Callable[[str], str],
) -> None:
    with pytest.raises(ValueError):
        module.plan(change(page()))


def test_partial_responsive_edit_is_rejected() -> None:
    result = module.plan(page())
    inserted = next(iter(module.INSERTIONS.values()))
    with pytest.raises(ValueError):
        module.plan(result.replace(inserted, "", 1))


def test_languages_cannot_be_adopted_from_mixed_original_and_final_states() -> None:
    original = page()
    updated = module.plan(original)
    with pytest.raises(ValueError):
        module.plan_pair(updated, original)
    assert module.plan_pair(original, original) == (updated, updated)
    assert module.plan_pair(updated, updated) == (updated, updated)
