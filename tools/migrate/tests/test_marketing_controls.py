"""Existing paired markup must change only the reviewed control spans."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "marketing_controls", Path(__file__).parents[1] / "marketing-controls.py"
)
assert spec and spec.loader
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)

UNCHANGED = r"""<p>Current wording: Grüße, inquiry details and approved copy.</p>
<a href="/contact/?source=https%3A%2F%2Fde-linker.com%2Fservices-support%2F">Contact</a>
<script>const svg='\u003csvg>'; const words=/\s+/g; const line='a\nb';</script>
"""


def utility(language: str, final: bool = False) -> str:
    href = "workflow" if final else "exec-deck-nav"
    title = "Project workflow" if language == "en" else "Projektablauf"
    return (
        '<main id="tv-utility-page-v1" lang="'
        + language
        + '"><a href="#'
        + href
        + '">'
        + title
        + '</a><section id="workflow"><h2>'
        + title
        + '</h2><nav id="exec-deck-nav">Existing cards</nav></section>'
        + UNCHANGED
        + "</main>"
    )


def handler(tabs: str, final: bool = False) -> str:
    if final:
        key_span = (
            "if (['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) {\n"
            "        event.preventDefault();\n"
            "        const next = event.key === 'Home' ? 0\n"
            f"          : event.key === 'End' ? {tabs}.length - 1\n"
            "          : (i + (event.key === 'ArrowRight' ? 1 : -1) "
            f"+ {tabs}.length) % {tabs}.length;"
        )
    else:
        key_span = (
            "if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {\n"
            "        event.preventDefault();\n"
            "        const next = (i + (event.key === 'ArrowRight' ? 1 : -1) "
            f"+ {tabs}.length) % {tabs}.length;"
        )
    select = "showStage" if tabs == "stageTabs" else "showRole"
    scroll = (
        f"        {tabs}[next].scrollIntoView({{ block: 'nearest', inline: 'nearest' }});\n"
        if final
        else ""
    )
    return (
        f"{tabs}.forEach((tab, i) => {{\n"
        "  tab.addEventListener('keydown', (event) => {\n"
        "      " + key_span + f"\n        {select}(next);\n"
        f"        {tabs}[next].focus();\n" + scroll + "      }\n  });\n});\n"
    )


def services(language: str, final: bool = False) -> str:
    title = "Services & support" if language == "en" else "Service & Support"
    return (
        f'<main id="service-redesign" lang="{language}"><h1>{title}</h1>'
        + UNCHANGED
        + "<script>\n"
        + handler("stageTabs", final)
        + handler("roleTabs", final)
        + "</script></main>"
    )


PAGES = {"utility": utility, "services": services}


@pytest.mark.parametrize("family", PAGES)
def test_complete_old_pair_changes_only_control_spans(family: str) -> None:
    page = PAGES[family]
    before = tuple(page(language) for language in ("en", "de"))
    after = controls.plan_pair(family, *before)
    assert after == tuple(page(language, final=True) for language in ("en", "de"))
    for original, saved in zip(before, after, strict=True):
        assert original.count(UNCHANGED) == saved.count(UNCHANGED) == 1
        assert original.count("\\") == saved.count("\\")
        assert saved.encode().endswith(b"</main>")


@pytest.mark.parametrize("family", PAGES)
def test_complete_final_pair_is_exact_idempotent_noop(family: str) -> None:
    pair = tuple(PAGES[family](language, final=True) for language in ("en", "de"))
    assert controls.plan_pair(family, *pair) == pair
    assert controls.plan_pair(family, *controls.plan_pair(family, *pair)) == pair


@pytest.mark.parametrize("family", PAGES)
@pytest.mark.parametrize("english_final", [False, True])
def test_partial_language_pair_is_refused(family: str, english_final: bool) -> None:
    page = PAGES[family]
    with pytest.raises(ValueError, match="Partially changed language pair"):
        controls.plan_pair(
            family, page("en", english_final), page("de", not english_final)
        )


@pytest.mark.parametrize("family", PAGES)
@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("duplicate", [False, True])
def test_missing_or_duplicate_root_in_either_language_is_refused(
    family: str, language: str, duplicate: bool
) -> None:
    pair = {lang: PAGES[family](lang) for lang in ("en", "de")}
    root = "tv-utility-page-v1" if family == "utility" else "service-redesign"
    marker = f'id="{root}"'
    pair[language] = (
        pair[language] + f"<div {marker}></div>"
        if duplicate
        else pair[language].replace(marker, 'id="changed"')
    )
    with pytest.raises(ValueError, match="one existing marketing root"):
        controls.plan_pair(family, pair["en"], pair["de"])


@pytest.mark.parametrize(
    "changed",
    [
        utility("en").replace('id="workflow"', 'id="changed"'),
        utility("en") + '<section id="workflow"></section>',
        utility("en").replace('href="#exec-deck-nav"', 'href="#changed"'),
        utility("en") + '<a href="#exec-deck-nav">Duplicate</a>',
        utility("en") + '<a href="#workflow">Partial</a>',
        utility("en", True) + '<a href="#workflow">Duplicate</a>',
    ],
)
def test_utility_missing_drifted_or_ambiguous_structure_is_refused(
    changed: str,
) -> None:
    with pytest.raises(ValueError):
        controls.plan_pair("utility", changed, utility("de"))


@pytest.mark.parametrize("tabs", ["stageTabs", "roleTabs"])
@pytest.mark.parametrize("language", ["en", "de"])
def test_one_final_service_group_is_refused(tabs: str, language: str) -> None:
    pair = {lang: services(lang) for lang in ("en", "de")}
    pair[language] = pair[language].replace(handler(tabs), handler(tabs, True))
    with pytest.raises(ValueError, match="Partially changed service handlers"):
        controls.plan_pair("services", pair["en"], pair["de"])


@pytest.mark.parametrize("tabs", ["stageTabs", "roleTabs"])
@pytest.mark.parametrize("fault", ["missing", "duplicate", "drift", "both"])
def test_service_changed_or_ambiguous_handler_is_refused(tabs: str, fault: str) -> None:
    original = services("en")
    replacement = {
        "missing": "",
        "duplicate": handler(tabs) * 2,
        "drift": handler(tabs).replace("event.preventDefault();", "return;"),
        "both": handler(tabs) + handler(tabs, True),
    }[fault]
    changed = original.replace(handler(tabs), replacement)
    with pytest.raises(ValueError, match="Service key handler changed"):
        controls.plan_pair("services", changed, services("de"))


def test_unreviewed_page_family_is_refused() -> None:
    with pytest.raises(ValueError, match="Only Utility and Services"):
        controls.plan_pair("home", utility("en"), utility("de"))


@pytest.mark.parametrize("tabs", ["stageTabs", "roleTabs"])
@pytest.mark.parametrize(
    "fault", ["keyboard_only", "scroll_only", "missing_focus", "changed_target"]
)
def test_partial_or_drifted_focus_scroll_path_is_refused(tabs: str, fault: str) -> None:
    scroll = f"        {tabs}[next].scrollIntoView({{ block: 'nearest', inline: 'nearest' }});\n"
    old, final = handler(tabs), handler(tabs, True)
    changed = {
        "keyboard_only": final.replace(scroll, ""),
        "scroll_only": old.replace(
            f"{tabs}[next].focus();\n", f"{tabs}[next].focus();\n{scroll}"
        ),
        "missing_focus": old.replace(f"{tabs}[next].focus();", ""),
        "changed_target": final.replace(
            f"{tabs}[next].scrollIntoView", f"{tabs}[0].scrollIntoView"
        ),
    }[fault]
    with pytest.raises(ValueError, match="Service key handler changed"):
        controls.plan_pair(
            "services", services("en").replace(old, changed), services("de")
        )
