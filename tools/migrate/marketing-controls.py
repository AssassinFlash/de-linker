"""Plan narrow corrections to existing marketing controls.

This module does not write WordPress. Use the existing reviewed_page_pair
transport with a verified recovery baseline, a current scoped pair increment,
reviewed current-state digest, and exact post-write readback.
"""

from __future__ import annotations

import re
from html import escape, unescape


def _utility(content: str) -> tuple[str, str]:
    if len(re.findall(r'<section\b[^>]*\bid="workflow"', content)) != 1:
        raise ValueError("Expected one existing workflow section")
    old, new = 'href="#exec-deck-nav"', 'href="#workflow"'
    if content.count(old) == 1 and content.count(new) == 0:
        return content.replace(old, new, 1), "old"
    if content.count(old) == 0 and content.count(new) == 1:
        return content, "final"
    raise ValueError("Workflow link changed or is ambiguous; nothing planned")


def _services(content: str) -> tuple[str, str]:
    states: list[str] = []
    for tabs, select in (("stageTabs", "showStage"), ("roleTabs", "showRole")):
        old = (
            "if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {\n"
            "        event.preventDefault();\n"
            "        const next = (i + (event.key === 'ArrowRight' ? 1 : -1) "
            f"+ {tabs}.length) % {tabs}.length;"
        )
        new = (
            "if (['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) {\n"
            "        event.preventDefault();\n"
            "        const next = event.key === 'Home' ? 0\n"
            f"          : event.key === 'End' ? {tabs}.length - 1\n"
            "          : (i + (event.key === 'ArrowRight' ? 1 : -1) "
            f"+ {tabs}.length) % {tabs}.length;"
        )
        action = f"\n        {select}(next);\n        {tabs}[next].focus();"
        old += action + "\n      }"
        new += (
            action + f"\n        {tabs}[next].scrollIntoView({{ block: 'nearest', "
            "inline: 'nearest' });\n      }"
        )
        if content.count(old) == 1 and content.count(new) == 0:
            states.append("old")
            content = content.replace(old, new, 1)
        elif content.count(old) == 0 and content.count(new) == 1:
            states.append("final")
        else:
            raise ValueError("Service key handler changed; nothing planned")
    if states[0] != states[1]:
        raise ValueError("Partially changed service handlers; inspect before retrying")
    return content, states[0]


def _installer(content: str) -> tuple[str, str]:
    start = "  function tabSet(tabSelector, panelSelector, activeAttr) {"
    end = "  tabSet('.lk-timeline-node', '.lk-timeline-stage', 'data-active');"
    if content.count(start) != 1 or content.count(end) != 1:
        raise ValueError("Installer timeline changed; nothing planned")
    first = content.index(start)
    last = content.index(end, first) + len(end)
    block = content[first:last]
    edits = (
        ("function show(index) {", "function show(index, reveal = true) {"),
        (
            "if (tabs[index]) tabs[index].scrollIntoView({block:'nearest',inline:'nearest'});",
            "if (reveal && tabs[index]) tabs[index].scrollIntoView({block:'nearest',inline:'nearest'});",
        ),
        ("    show(0);", "    show(0, false);"),
    )
    fields = re.findall(r'<textarea\b[^>]*\sid="installer-mobile-query"[^>]*>', content)
    if len(fields) != 1 or fields[0].count(" rows=") != 1:
        raise ValueError("Expected one native Installer prompt")
    if block.count(".scrollIntoView(") != 1:
        raise ValueError("Installer scroll consumer changed; nothing planned")
    old = all(block.count(a) == 1 and b not in block for a, b in edits)
    final = all(a not in block and block.count(b) == 1 for a, b in edits)
    field = fields[0]
    if final and field.count('rows="3"') == 1:
        return content, "final"
    if not old or field.count('rows="2"') != 1:
        raise ValueError(
            "Partially changed Installer controls; inspect before retrying"
        )
    for before, after in edits:
        block = block.replace(before, after, 1)
    content = content[:first] + block + content[last:]
    return content.replace(field, field.replace('rows="2"', 'rows="3"'), 1), "old"


def _capability(content: str) -> tuple[str, str]:
    names = re.findall(r'<div class="lk-story-name\b[^"]*"[^>]*>([^<]+)</div>', content)
    # This reviewed pair has exactly two stories; changed content needs review.
    if len(names) != 2:
        raise ValueError("Expected the two existing Capability story names")
    old_handler = (
        "testiPills.forEach(function(p, i) {\n"
        "          p.classList.toggle('active', i === idx);\n"
        "        });"
    )
    new_handler = old_handler.replace(
        "\n        });",
        "\n          p.setAttribute('aria-pressed', String(i === idx));\n        });",
    )
    track = "  var lkTestiTrack=document.getElementById('testi-track');\n"
    old_position = (
        "    var x=active.getBoundingClientRect().left-vp.getBoundingClientRect().left+lkTestiX;\n"
        "    var max=lkTestiTrack.scrollWidth-vp.clientWidth;\n"
        "    x=Math.max(0,Math.min(Math.round(x),max));\n"
        "    lkTestiX=x;"
    )
    new_position = (
        "    var x=active.offsetLeft;\n"
        "    var max=lkTestiTrack.scrollWidth-vp.clientWidth;\n"
        "    x=Math.max(0,Math.min(Math.round(x),max));"
    )
    edits = [
        (old_handler, new_handler),
        (
            track + "  var lkTestiX=0;\n  function lkTestiFollow(){",
            track + "  function lkTestiFollow(){",
        ),
        (
            "if(fits){lkTestiX=0;lkTestiTrack.style.transform='';return;}",
            "if(fits){lkTestiTrack.style.transform='';return;}",
        ),
        (old_position, new_position),
    ]
    for index, name in enumerate(names):
        classes = "lk-testi-pill-bar" + (" active" if index == 0 else "")
        attributes = f'class="{classes}" data-index="{index}"'
        edits.append(
            (
                f"<div {attributes}></div>",
                f'<button type="button" {attributes} '
                f'aria-label="{escape(unescape(name), quote=True)}" '
                f'aria-pressed="{"true" if index == 0 else "false"}"></button>',
            )
        )
    old = all(content.count(a) == 1 and b not in content for a, b in edits)
    final = all(a not in content and content.count(b) == 1 for a, b in edits)
    controls = re.findall(r'<(?:div|button)\b[^>]*class="lk-testi-pill-bar\b', content)
    if len(controls) != len(names) or not (old or final):
        raise ValueError("Capability story controls changed or are partial")
    if final:
        return content, "final"
    for before, after in edits:
        content = content.replace(before, after, 1)
    return content, "old"


def plan_thank_you_blog(english: str, german: str) -> tuple[str, str]:
    """Localize the existing Blog card without changing any other page bytes."""
    old = '<a href="/blog/" class="lk-path-row">'
    new = '<a href="/de/blog/" class="lk-path-row">'
    if english.count(old) != 1 or english.count(new) != 0:
        raise ValueError("English Blog card changed; inspect the page pair")
    if german.count(old) == 1 and german.count(new) == 0:
        return english, german.replace(old, new, 1)
    if german.count(old) == 0 and german.count(new) == 1:
        return english, german
    raise ValueError("German Blog card changed or is ambiguous; nothing planned")


def plan_thank_you_inquiry(english: str, german: str) -> tuple[str, str]:
    """Align the project inquiry links and their claims with the existing form."""
    changes = (
        (
            "/solution-configurator/",
            "/proforma-request/",
            (
                (
                    "the contact page and the full project request both reach the same colleague.",
                    "the contact page and the project inquiry both reach the Linker team.",
                ),
                (
                    "The full intake. Loads, phase supply, existing PV and timeline sharpen the reply.",
                    "Share your project details. Loads, phase supply, existing PV and timeline sharpen the reply.",
                ),
                (
                    "Should I send a full project request as well?",
                    "Should I send a project request as well?",
                ),
                (
                    'If you already know the site type, system goal and rough size, yes. Send the <a href="/solution-configurator/">full project request</a> and the reply comes back scoped to design, availability and price.',
                    'If you already know the site type, system goal and rough size, yes. Send the <a href="/solution-configurator/">project request</a> and the reply comes back scoped to design, availability and price.',
                ),
                (
                    "The full project request carries loads, phase supply, existing PV and timeline, so the reply starts from the whole picture. A single addition fits better through the contact page.",
                    "Include the loads, phase supply, existing PV and timeline in your inquiry so our team can see the whole project. A single addition fits better through the contact page.",
                ),
            ),
        ),
        (
            "/de/loesungskonfigurator/",
            "/de/proforma-anfrage/",
            (
                (
                    "erreichen sowohl die Kontaktseite als auch die vollständige Projektanfrage denselben Kollegen.",
                    "erreichen Sie das Team von Linker über die Kontaktseite oder die Projektanfrage.",
                ),
                (
                    "Die vollständige Erfassung. Lasten, Phasenversorgung, bestehende PV und Zeitplan präzisieren die Antwort.",
                    "Beschreiben Sie Ihr Projekt. Angaben zu den Lasten, zum Netzanschluss, zur vorhandenen PV-Anlage und zum Zeitplan helfen uns bei der Auswahl.",
                ),
                (
                    "Soll ich auch eine vollständige Projektanfrage senden?",
                    "Soll ich auch eine Projektanfrage senden?",
                ),
                (
                    'Wenn Sie die Projektart, das Systemziel und die ungefähre Größe bereits kennen, ja. Senden Sie die <a href="/de/loesungskonfigurator/">vollständige Projektanfrage</a> und die Antwort kommt auf Auslegung, Verfügbarkeit und Preis zugeschnitten zurück.',
                    'Wenn Sie die Projektart, das Systemziel und die ungefähre Größe bereits kennen, ja. Senden Sie die <a href="/de/loesungskonfigurator/">Projektanfrage</a> und die Antwort kommt auf Auslegung, Verfügbarkeit und Preis zugeschnitten zurück.',
                ),
                (
                    "Die vollständige Projektanfrage enthält Lasten, Phasenversorgung, bestehende PV und Zeitplan, sodass die Antwort vom Gesamtbild ausgeht. Eine einzelne Ergänzung passt besser über die Kontaktseite.",
                    "Nennen Sie uns in Ihrer Anfrage die Lasten, den Netzanschluss, die vorhandene PV-Anlage und Ihren Zeitplan. So haben wir das gesamte Projekt im Blick. Eine einzelne Ergänzung passt besser über die Kontaktseite.",
                ),
            ),
        ),
    )
    planned: list[str] = []
    states: list[str] = []
    for content, (old_path, new_path, edits) in zip(
        (english, german), changes, strict=True
    ):
        # The FAQ text contains the path, so compare its final form after the
        # same path substitution used by the other three links.
        final_edits = tuple(
            (old, new.replace(old_path, new_path)) for old, new in edits
        )
        old = (
            content.count(old_path) == 4
            and content.count(new_path) == 0
            and all(
                content.count(a) == 1 and content.count(b) == 0 for a, b in final_edits
            )
        )
        final = (
            content.count(old_path) == 0
            and content.count(new_path) == 4
            and all(
                content.count(a) == 0 and content.count(b) == 1 for a, b in final_edits
            )
        )
        if not (old or final):
            raise ValueError("Thank You inquiry content changed or is partial")
        if old:
            for before, after in edits:
                content = content.replace(before, after, 1)
            content = content.replace(old_path, new_path)
        planned.append(content)
        states.append("old" if old else "final")
    if states[0] != states[1]:
        raise ValueError("Partially changed Thank You language pair")
    return planned[0], planned[1]


def plan_pair(family: str, english: str, german: str) -> tuple[str, str]:
    """Accept a complete old or final pair; preserve all other source bytes."""
    if family == "thank_you_blog":
        return plan_thank_you_blog(english, german)
    if family == "thank_you_inquiry":
        return plan_thank_you_inquiry(english, german)
    families = {
        "utility": ("tv-utility-page-v1", _utility),
        "services": ("service-redesign", _services),
        "installer": ("installer-journal", _installer),
        "capability": ("tv-cp-page-v1", _capability),
    }
    if family not in families:
        raise ValueError("Unknown marketing control family")
    root, transform = families[family]
    planned: list[str] = []
    states: list[str] = []
    for content in (english, german):
        if len(re.findall(r'\bid="' + root + '"', content)) != 1:
            raise ValueError("Expected one existing marketing root")
        after, state = transform(content)
        planned.append(after)
        states.append(state)
    if states[0] != states[1]:
        raise ValueError("Partially changed language pair; inspect before retrying")
    return planned[0], planned[1]
