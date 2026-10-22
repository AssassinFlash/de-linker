"""Tests of 12-site-chrome.py against the header thumbnails' resolving form.

The header partials resolve their menu thumbnails through their own src —
the live site's own form (spec 12 item 8 as of 2026-10-14; debt family 12
fixNote in docs/debt/ADJUDICATION-2026-10-14.md). This migration used to
defer them back to data-src after its pairs ran, so an `apply --write`
re-run would have written the empty-box form back over the fix on an
instance (the script is re-run on instances: docs/acceptance/2026-10-13/
e2e-and-fixes/README.md, docs/specs/17-cutover.md). The defer transform is
retired; these tests pin its retirement: the real header steps must leave
the shipped partials byte-identical, nothing may introduce data-src, the
deferral switch must be gone, and the verify guard must refuse the
deferred form.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent.parent
HEADER_PARTIALS = {
    "header-en": REPO_ROOT
    / "plugins/linker-commerce/content/livecanvas/partials/header.html",
    "header-de": REPO_ROOT
    / "plugins/linker-commerce/content/livecanvas/partials/de/header.html",
}

# Keep the original seven desktop and five drawer photos, resolving through
# their own src. The full-site loading repair makes both sets native lazy;
# the visible brand logo remains eager. See navigation-image-loading/spec.md
# under docs/acceptance/2026-10-22/full-site for the measured request evidence.
LAZY_CLASSES = (
    "tv-mega-featured-img",
    "tv-mega-link-thumb",
    "tv-app-mega-stack-thumb",
)
DESKTOP_IMAGES = 7
RAIL_IMAGES = 5


def load_script() -> ModuleType:
    """12-site-chrome.py is a script, not an importable module name."""
    spec = importlib.util.spec_from_file_location(
        "twelve_site_chrome", HERE.parent / "12-site-chrome.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


chrome = load_script()


def fake_ids() -> dict[str, dict[str, int]]:
    """steps() reads one entry per step; the marketing surfaces drop out
    when their id is 0, which is what the surface loop checks."""
    keys = [
        "header",
        "footer",
        "linker-advisor",
        "linker-planner",
        "design-canvas",
        "quote-configurator",
        "quote-configurator-2",
        "request-a-project",
        "utility-storage",
        "terms-of-sale",
    ]
    keys += list(chrome.SURFACES)
    return {key: {"en": 0, "de": 0} for key in keys}


def header_step(step_key: str) -> Any:
    return next(step for step in chrome.steps(fake_ids()) if step.key == step_key)


def image_tags(html: str) -> list[str]:
    return re.findall(r"<img\b[^>]*>", html, re.S)


@pytest.mark.parametrize("step_key", sorted(HEADER_PARTIALS))
def test_a_header_step_leaves_the_shipped_partial_byte_identical(step_key: str) -> None:
    """An instance flow ending in this migration must come out of it with
    the partial's own images: the step may rewrite tool names and drop the
    Site Detail links, nothing else."""
    html = HEADER_PARTIALS[step_key].read_text()
    changes: list[str] = []
    result = header_step(step_key).apply(html, changes.append)

    assert result == html, "the header step rewrote the shipped partial"
    assert all("data-src" not in change for change in changes)


@pytest.mark.parametrize("step_key", sorted(HEADER_PARTIALS))
def test_a_re_run_writes_no_data_src_onto_the_menu_images(step_key: str) -> None:
    """The regression this pins: `present` writes the repo partial, the
    migration runs again over the instance's copy — and the copy must keep
    a resolving src on every menu image."""
    html = HEADER_PARTIALS[step_key].read_text()
    assert "data-src" not in html, "the shipped partial carries the deferred form"
    step = header_step(step_key)
    reports: list[str] = []
    once = step.apply(html, reports.append)
    twice = step.apply(once, reports.append)

    assert "data-src" not in once and "data-src" not in twice
    assert chrome.unresolved_menu_images(once) == []
    assert chrome.unresolved_menu_images(twice) == []


def test_the_menu_image_deferral_switch_is_gone() -> None:
    assert not hasattr(chrome, "defer_menu_images")
    assert "menu_images" not in chrome.Step.__init__.__code__.co_varnames
    with pytest.raises(TypeError):
        chrome.Step("header-en", 1, 1, [], [], menu_images=True)


def test_the_verify_guard_refuses_the_deferred_empty_box_form() -> None:
    """do_verify runs unresolved_menu_images over both header partials on
    the instance; a re-run or a hand edit that defers an image again must
    be caught there rather than shown as an empty box. The src check is
    quote-independent: single- and double-quoted markup are both judged by
    the value, and a single-quoted resolving src is no fault (the review
    round's item 7: the old substring check read it as missing)."""
    assert chrome.unresolved_menu_images('<img data-src="/x.webp" alt="">')
    assert chrome.unresolved_menu_images("<img data-src='/x.webp' alt=''>")
    assert chrome.unresolved_menu_images('<img alt="" class="tv-mega-link-thumb">')
    assert chrome.unresolved_menu_images(
        '<img src="" alt="" class="tv-mega-link-thumb">'
    )
    assert chrome.unresolved_menu_images("<img src='' alt=''>")
    assert chrome.unresolved_menu_images('<img src="/x.webp" alt="">') == []
    assert chrome.unresolved_menu_images("<img src='/x.webp' alt=''>") == []
    for partial in HEADER_PARTIALS.values():
        assert chrome.unresolved_menu_images(partial.read_text()) == []


@pytest.mark.parametrize("step_key", sorted(HEADER_PARTIALS))
def test_a_re_run_keeps_both_closed_menu_photo_sets_native_lazy(step_key: str) -> None:
    """A migration re-run must keep actual photos resolvable without
    restoring eager drawer downloads or the retired data-src hydration."""
    reports: list[str] = []
    html = header_step(step_key).apply(
        HEADER_PARTIALS[step_key].read_text(), reports.append
    )
    tags = image_tags(html)
    lazy = [tag for tag in tags if 'loading="lazy"' in tag]
    eager = [tag for tag in tags if 'loading="eager"' in tag]
    desktop = [
        tag for tag in tags if any(f'class="{name}"' in tag for name in LAZY_CLASSES)
    ]
    rails = re.findall(
        r'<a[^>]*class="tv-mobile-rail-card"[^>]*>(<img\b[^>]*>)', html, re.S
    )

    assert all('src="' in tag for tag in tags)
    assert len(desktop) == DESKTOP_IMAGES
    assert len(rails) == RAIL_IMAGES
    assert len(lazy) == DESKTOP_IMAGES + RAIL_IMAGES
    assert set(lazy) == set(desktop) | set(rails)
    assert len(tags) == len(lazy) + len(eager)
    assert len(eager) == 1 and "tv-brand-logo" in eager[0]
