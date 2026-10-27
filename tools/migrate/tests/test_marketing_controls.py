"""Existing paired markup must change only the reviewed control spans."""

import importlib.util
import json
import subprocess
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


def test_installer_native_consumer_initializes_without_scrolling() -> None:
    source = (Path(__file__).parent / "fixtures" / "installer-tabset.html").read_text()
    before = (source + UNCHANGED, source + UNCHANGED)
    after = controls.plan_pair("installer", *before)
    assert controls.plan_pair("installer", *after) == after
    assert all(UNCHANGED in text for text in after)
    script = after[0].split("<script>\n", 1)[1].split("\n</script>", 1)[0]
    program = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const calls = [];
const tabs = Array.from({length:3}, (_, index) => ({
  handlers:{},setAttribute(){},
  addEventListener(event, action){this.handlers[event]=action},
  scrollIntoView(options){calls.push({index,options})},focus(){},
}));
const panels = tabs.map(() => ({setAttribute(){},querySelector(){return null}}));
const page = {querySelectorAll(selector){
  return selector === '.lk-timeline-node' ? tabs : panels;
}};
vm.runInNewContext(JSON.parse(process.argv[1]), {page});
assert.equal(calls.length, 0);
tabs[1].handlers.click();
assert.equal(calls[0].index, 1);
assert.equal(calls[0].options.block, 'nearest');
assert.equal(calls[0].options.inline, 'nearest');
tabs[1].handlers.keydown({key:'ArrowRight', preventDefault(){}});
assert.equal(calls[1].index, 2);
"""
    subprocess.run(["node", "-e", program, json.dumps(script)], check=True)


def test_installer_refuses_changed_scroll_consumers_and_partial_pairs() -> None:
    old = (Path(__file__).parent / "fixtures" / "installer-tabset.html").read_text()
    final = controls.plan_pair("installer", old, old)[0]
    for text in (old, final):
        for changed in (
            text.replace("block:'nearest'", "block:'center'"),
            text.replace("tabs[index].scrollIntoView", "tabs[0].scrollIntoView"),
            text.replace("    show(0", "    tabs[0].scrollIntoView();\n    show(0"),
            text.replace('rows="', 'rows="4" rows="', 1),
        ):
            with pytest.raises(ValueError):
                controls.plan_pair("installer", changed, text)
    with pytest.raises(ValueError, match="Partially changed language pair"):
        controls.plan_pair("installer", old, final)


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


def capability() -> str:
    return (
        '<main id="tv-cp-page-v1">'
        '<div class="lk-story-name mb-1">Stefan &quot;S&quot; &amp; Team</div>'
        '<div class="lk-story-name">Dirk van de Berg</div>'
        '<div class="lk-testi-pill-bar active" data-index="0"></div>'
        '<div class="lk-testi-pill-bar" data-index="1"></div>'
        + UNCHANGED
        + "<script>testiPills.forEach(function(p, i) {\n"
        "          p.classList.toggle('active', i === idx);\n"
        "        });</script></main>"
    )


def test_capability_native_markers_preserve_source_and_author_names() -> None:
    old = capability()
    en, de = controls.plan_pair("capability", old, old)
    assert en == de
    assert controls.plan_pair("capability", en, de) == (en, de)
    assert UNCHANGED in en and en.count("\\") == old.count("\\")
    assert en.count('<button type="button" class="lk-testi-pill-bar') == 2
    assert 'aria-label="Stefan &quot;S&quot; &amp; Team" aria-pressed="true"' in en
    assert 'aria-label="Dirk van de Berg" aria-pressed="false"' in en
    assert "p.setAttribute('aria-pressed', String(i === idx));" in en


def test_capability_refuses_partial_controls_pair_and_changed_sources() -> None:
    old = capability()
    final = controls.plan_pair("capability", old, old)[0]
    for changed in (
        old.replace('<div class="lk-story-name">Dirk van de Berg</div>', "").replace(
            '<div class="lk-testi-pill-bar" data-index="1"></div>', ""
        ),
        old.replace('data-index="1"', 'data-index="2"'),
        old.replace('class="lk-story-name"', 'class="renamed"'),
        old.replace("testiPills.forEach", "otherPills.forEach"),
        old.replace('<div class="lk-testi-pill-bar" data-index="1"></div>', ""),
        final.replace('aria-pressed="false"', 'aria-pressed="true"'),
    ):
        with pytest.raises(ValueError):
            controls.plan_pair("capability", changed, old)
    with pytest.raises(ValueError, match="Partially changed language pair"):
        controls.plan_pair("capability", old, final)


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


@pytest.mark.parametrize("tabs,language", [("stageTabs", "en"), ("roleTabs", "de")])
def test_one_final_service_group_is_refused(tabs: str, language: str) -> None:
    pair = {lang: services(lang) for lang in ("en", "de")}
    pair[language] = pair[language].replace(handler(tabs), handler(tabs, True))
    with pytest.raises(ValueError, match="Partially changed service handlers"):
        controls.plan_pair("services", pair["en"], pair["de"])


@pytest.mark.parametrize(
    "tabs,fault",
    [
        ("stageTabs", "missing"),
        ("roleTabs", "duplicate"),
        ("stageTabs", "drift"),
        ("roleTabs", "both"),
    ],
)
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
    with pytest.raises(ValueError, match="Unknown marketing control family"):
        controls.plan_pair("home", utility("en"), utility("de"))


@pytest.mark.parametrize(
    "tabs,fault",
    [
        ("stageTabs", "keyboard_only"),
        ("roleTabs", "scroll_only"),
        ("stageTabs", "missing_focus"),
        ("roleTabs", "changed_target"),
    ],
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
