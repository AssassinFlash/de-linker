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

# (Original, previously published, current) descriptions, desktop then mobile.
ROOF_COPY = {
    "header-en": (
        (
            "Organise the goal, site and existing equipment into a project direction you can keep refining.",
            "Bring your goal, site and existing equipment into a complete solution with a bill of materials. The Roof detail step adds the building's layout.",
            "Bring your goal, site and existing equipment into a complete solution with a bill of materials. You can add a roof layout if needed.",
        ),
        (
            "Organise the project direction and keep refining it.",
            "Configure a complete solution with a bill of materials. The Roof detail step adds the layout.",
            "Configure a complete solution with a bill of materials. You can add a roof layout if needed.",
        ),
    ),
    "header-de": (
        (
            "Organisieren Sie Ziel, Standort und vorhandene Ausrüstung in eine Projektrichtung, die Sie weiter verfeinern können.",
            "Führen Sie Ziel, Standort und vorhandene Ausrüstung zu einer vollständigen Lösung mit Stückliste zusammen. Der Schritt Dachdetails nimmt die Dachfläche auf.",
            "Führen Sie Ziel, Standort und vorhandene Ausrüstung zu einer vollständigen Lösung mit Stückliste zusammen. Bei Bedarf können Sie die Dachfläche einzeichnen.",
        ),
        (
            "Organisieren Sie die Projektrichtung und verfeinern Sie sie weiter.",
            "Konfigurieren Sie eine vollständige Lösung mit Stückliste. Der Schritt Dachdetails nimmt die Dachfläche auf.",
            "Konfigurieren Sie eine vollständige Lösung mit Stückliste. Bei Bedarf können Sie die Dachfläche einzeichnen.",
        ),
    ),
}


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
@pytest.mark.parametrize("version", [0, 1], ids=["original", "previously-published"])
def test_header_roof_copy_reaches_the_shipped_partial(
    step_key: str, version: int
) -> None:
    final = HEADER_PARTIALS[step_key].read_text()
    source = final
    for descriptions in ROOF_COPY[step_key]:
        assert source.count(descriptions[2]) == 1
        source = source.replace(descriptions[2], descriptions[version], 1)

    assert header_step(step_key).planned(source) == final


@pytest.mark.parametrize("step_key", sorted(HEADER_PARTIALS))
@pytest.mark.parametrize("invalid", ["unknown", "duplicated", "mixed"])
def test_header_rejects_unrecognized_or_ambiguous_roof_copy(
    step_key: str, invalid: str
) -> None:
    final = HEADER_PARTIALS[step_key].read_text()
    original, previous, current = ROOF_COPY[step_key][0]
    span = '<span class="tv-tool-desc">{}</span>'
    malformed = {
        "unknown": span.format("Unknown planner description."),
        "duplicated": span.format(current) * 2,
        "mixed": span.format(original) + span.format(previous),
    }[invalid]

    with pytest.raises(SystemExit, match=step_key):
        header_step(step_key).planned(final.replace(span.format(current), malformed, 1))


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


def verify_header(
    monkeypatch: pytest.MonkeyPatch, step_key: str, body: str, legacy: str = ""
) -> int:
    ids = fake_ids()
    ids["header"] = {"en": 17, "de": 6909}
    header = next(step for step in chrome.steps(ids) if step.key == step_key)
    monkeypatch.setattr(chrome, "resolve", lambda wp: ids)
    monkeypatch.setattr(chrome, "steps", lambda ids: [header])
    monkeypatch.setattr(chrome, "read_post", lambda wp, post_id: {"post_content": body})
    monkeypatch.setattr(chrome, "seo_meta", lambda wp: {})

    class FixtureWP:
        slugs = iter(
            ["solution-configurator", "loesungskonfigurator", "genie", "genie"]
        )

        def run(self, *args: str) -> str:
            return next(self.slugs)

        def json(self, *args: str) -> list[str]:
            return []

        def eval_php(self, source: str, ids: list[int]) -> dict[str, dict[str, str]]:
            return (
                {"17": {"content": legacy}} if source == chrome.LEGACY_META_PHP else {}
            )

    return int(chrome.do_verify(FixtureWP()))


def test_verify_rejects_a_stale_german_header_mirror_after_the_page_is_current(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    german = HEADER_PARTIALS["header-de"].read_text()
    stale = german
    for _, previous, current in ROOF_COPY["header-de"]:
        stale = stale.replace(current, previous, 1)
    ids = fake_ids()
    ids["header"] = {"en": 17, "de": 6909}
    header = next(step for step in chrome.steps(ids) if step.key == "header-de")

    assert verify_header(monkeypatch, "header-de", german, stale) == 1
    assert "_linker_de_content" in capsys.readouterr().out
    assert chrome.legacy_meta_updates(
        [header], {6909: german}, {"17": {"content": stale}}
    ) == [(17, {"_linker_de_content": german})]
    assert verify_header(monkeypatch, "header-de", german, german) == 0


@pytest.mark.parametrize("step_key", sorted(HEADER_PARTIALS))
@pytest.mark.parametrize("slot", ["desktop", "mobile"])
@pytest.mark.parametrize("extra_version", ["previous", "current"])
def test_verify_rejects_two_roof_descriptions_in_one_slot(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    step_key: str,
    slot: str,
    extra_version: str,
) -> None:
    body = HEADER_PARTIALS[step_key].read_text()
    index, css = (
        (0, "tv-tool-desc") if slot == "desktop" else (1, "tv-mobile-link-desc")
    )
    _, previous, current = ROOF_COPY[step_key][index]
    final_span = f'<span class="{css}">{current}</span>'
    extra = previous if extra_version == "previous" else current
    assert body.count(final_span) == 1
    contested = body.replace(
        final_span, f'<span class="{css}">{extra}</span>{final_span}', 1
    )
    assert chrome.stale_tokens(contested) == []
    assert verify_header(monkeypatch, step_key, body) == 0
    capsys.readouterr()

    result = verify_header(monkeypatch, step_key, contested)
    output = capsys.readouterr().out
    assert result == 1, output
    assert f"FAIL {step_key}:" in output
    assert css in output
    assert "verify: FAILED" in output


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
