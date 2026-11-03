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
    old_tab = "#service-redesign .service-role-nav button { min-height: 43px;"
    new_tab = "#service-redesign .service-role-nav button { min-height: 44px;"
    if old_tab in content or new_tab in content:
        if content.count(old_tab) == 1 and content.count(new_tab) == 0:
            if states[0] != "old":
                content = content.replace(old_tab, new_tab, 1)
                return content, "old"
            content = content.replace(old_tab, new_tab, 1)
        elif not (content.count(old_tab) == 0 and content.count(new_tab) == 1):
            raise ValueError("Service role tab rule changed; nothing planned")
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


def _apply_edits(
    content: str, edits: tuple[tuple[str, str], ...], label: str
) -> tuple[str, str]:
    old = all(content.count(a) == 1 and content.count(b) == 0 for a, b in edits)
    final = all(content.count(a) == 0 and content.count(b) == 1 for a, b in edits)
    if not (old or final):
        raise ValueError(f"{label} content changed or is partial")
    if old:
        for before, after in edits:
            content = content.replace(before, after, 1)
    return content, "old" if old else "final"


def _home_motion_button(language: str) -> str:
    pause, play = (
        ("Pause slideshow", "Play slideshow")
        if language == "en"
        else ("Diashow pausieren", "Diashow abspielen")
    )
    return (
        f'<button class="epc-motion-toggle" type="button" aria-label="{pause}" '
        f'data-pause-label="{pause}" data-play-label="{play}" hidden>'
        '<svg class="epc-motion-pause" viewBox="0 0 24 24" aria-hidden="true">'
        '<path d="M9 5v14M15 5v14"/></svg>'
        '<svg class="epc-motion-play" viewBox="0 0 24 24" aria-hidden="true">'
        '<path d="m8 5 11 7-11 7Z"/></svg></button>'
    )


_HOME_TESTIMONIALS_SCRIPT_EDITS = (
    (
        '  var dots = Array.prototype.slice.call(section.querySelectorAll(".home-stor-dot"));\n'
        "  if (!track || stories.length < 2 || !prev || !next) return;\n\n"
        "  var n = stories.length;\n"
        "  var index = 0;\n"
        "  var animating = false;\n"
        '  var pending = "";\n'
        "  var paused = false;",
        '  var dots = Array.prototype.slice.call(section.querySelectorAll(".home-stor-dot"));\n'
        '  var motionButton = section.querySelector(".epc-motion-toggle");\n'
        "  if (!track || stories.length < 2 || !prev || !next) return;\n\n"
        "  var n = stories.length;\n"
        "  var index = 0;\n"
        "  var animating = false;\n"
        '  var pending = "";\n'
        "  var userPaused = false;\n"
        "  var explicitPlay = false;\n"
        "  var pointerInside = false;\n"
        "  var focusWithin = false;",
    ),
    (
        "  function autoAllowed() {\n"
        "    return !noauto && !reduceMq.matches && mq.matches && !paused;\n"
        "  }",
        "  function isPausedState() {\n"
        "    return noauto || userPaused || (reduceMq.matches && !explicitPlay);\n"
        "  }\n\n"
        "  function autoAllowed() {\n"
        "    return !noauto && !document.hidden && mq.matches && !userPaused && "
        "(explicitPlay || (!reduceMq.matches && !pointerInside && !focusWithin));\n"
        "  }\n\n"
        "  function syncMotion() {\n"
        "    var isPaused = isPausedState();\n"
        "    if (motionButton) {\n"
        "      motionButton.hidden = !mq.matches;\n"
        "      motionButton.setAttribute(\n"
        '        "aria-label",\n'
        '        motionButton.getAttribute(isPaused ? "data-play-label" : "data-pause-label") || ""\n'
        "      );\n"
        '      motionButton.classList.toggle("is-paused", isPaused);\n'
        "    }\n"
        "    if (mq.matches) {\n"
        '      section.classList.toggle("is-stor-static", isPaused);\n'
        "    }\n"
        "  }",
    ),
    (
        "    applyOrder();\n    if (!paused) startTimer();\n  }",
        "    applyOrder();\n    startTimer();\n  }",
    ),
    (
        "    if (reduceMq.matches) {\n"
        "      index = (index + dir + n) % n;\n"
        '      track.style.transition = "none";\n'
        '      track.style.transform = "translateX(0)";\n'
        "      applyOrder();\n"
        "      if (!paused) startTimer();\n"
        "      return;\n"
        "    }",
        "    if (reduceMq.matches && !explicitPlay) {\n"
        "      index = (index + dir + n) % n;\n"
        '      track.style.transition = "none";\n'
        '      track.style.transform = "translateX(0)";\n'
        "      applyOrder();\n"
        "      startTimer();\n"
        "      return;\n"
        "    }",
    ),
    (
        "  function pauseAuto() {\n"
        "    paused = true;\n"
        "    stopTimer();\n"
        "  }\n\n"
        "  function resumeAuto() {\n"
        "    paused = false;\n"
        "    if (!animating) startTimer();\n"
        "  }\n\n"
        "  function syncMode() {\n"
        "    animating = false;\n"
        '    pending = "";\n'
        "    if (finishTimer) {\n"
        "      window.clearTimeout(finishTimer);\n"
        "      finishTimer = 0;\n"
        "    }\n"
        "    if (mq.matches) {\n"
        '      section.classList.add("is-stor-carousel");\n'
        '      if (noauto || reduceMq.matches) section.classList.add("is-stor-static");\n'
        '      else section.classList.remove("is-stor-static");\n'
        '      track.style.transition = "none";\n'
        "      applyOrder();\n"
        '      track.style.transform = "translateX(0)";\n'
        "      void track.offsetWidth;\n"
        "      startTimer();\n"
        "    } else {\n"
        '      section.classList.remove("is-stor-carousel", "is-stor-play", "is-stor-static");\n'
        "      stopTimer();\n",
        "  function syncMode() {\n"
        "    animating = false;\n"
        '    pending = "";\n'
        "    if (finishTimer) {\n"
        "      window.clearTimeout(finishTimer);\n"
        "      finishTimer = 0;\n"
        "    }\n"
        "    syncMotion();\n"
        "    if (mq.matches) {\n"
        '      section.classList.add("is-stor-carousel");\n'
        '      track.style.transition = "none";\n'
        "      applyOrder();\n"
        '      track.style.transform = "translateX(0)";\n'
        "      void track.offsetWidth;\n"
        "      startTimer();\n"
        "    } else {\n"
        '      section.classList.remove("is-stor-carousel", "is-stor-play", "is-stor-static");\n'
        "      stopTimer();\n",
    ),
    (
        "  if (hoverMq.matches) {\n"
        '    section.addEventListener("mouseenter", pauseAuto);\n'
        '    section.addEventListener("mouseleave", resumeAuto);\n'
        "  }\n"
        '  section.addEventListener("focusin", pauseAuto);\n'
        '  section.addEventListener("focusout", function (event) {\n'
        "    if (!section.contains(event.relatedTarget)) resumeAuto();\n"
        "  });\n"
        '  section.addEventListener("touchstart", pauseAuto, { passive: true });\n'
        '  section.addEventListener("touchend", resumeAuto, { passive: true });\n'
        '  section.addEventListener("touchcancel", resumeAuto, { passive: true });',
        "  if (motionButton) {\n"
        '    motionButton.addEventListener("click", function () {\n'
        "      var wantsPlay = isPausedState();\n"
        "      noauto = false;\n"
        "      userPaused = !wantsPlay;\n"
        "      explicitPlay = wantsPlay;\n"
        "      syncMotion();\n"
        "      if (!animating) startTimer();\n"
        "    });\n"
        "  }\n"
        '  section.addEventListener("pointerenter", function (event) {\n'
        '    if (event.pointerType === "touch" || !hoverMq.matches) return;\n'
        "    pointerInside = true;\n"
        "    explicitPlay = false;\n"
        "    syncMotion();\n"
        "    stopTimer();\n"
        "  });\n"
        '  section.addEventListener("pointerleave", function (event) {\n'
        '    if (event.pointerType === "touch") return;\n'
        "    pointerInside = false;\n"
        "    syncMotion();\n"
        "    if (!animating) startTimer();\n"
        "  });\n"
        '  section.addEventListener("focusin", function () {\n'
        "    focusWithin = true;\n"
        "    explicitPlay = false;\n"
        "    syncMotion();\n"
        "    stopTimer();\n"
        "  });\n"
        '  section.addEventListener("focusout", function (event) {\n'
        "    focusWithin = section.contains(event.relatedTarget);\n"
        "    syncMotion();\n"
        "    if (!animating) startTimer();\n"
        "  });\n"
        '  document.addEventListener("visibilitychange", function () {\n'
        "    if (document.hidden) {\n"
        "      explicitPlay = false;\n"
        "      stopTimer();\n"
        "    } else if (!animating) {\n"
        "      startTimer();\n"
        "    }\n"
        "    syncMotion();\n"
        "  });",
    ),
)


def plan_home_testimonials(english: str, german: str) -> tuple[str, str]:
    """Add the EPC motion toggle to Home #testimonials and remove touchend auto-resume."""
    planned: list[str] = []
    states: list[str] = []
    for language, content in (("en", english), ("de", german)):
        if (
            len(re.findall(r'\bid="home-a"', content)) != 1
            or len(re.findall(r'<section\b[^>]*\bid="testimonials"', content)) != 1
        ):
            raise ValueError("Expected one existing Home testimonials section")
        button = _home_motion_button(language)
        prev_label = "Previous story" if language == "en" else "Vorherige Geschichte"
        prev_anchor = (
            f'<a href="#story-0" id="testi-prev" aria-label="{prev_label}">←</a>'
        )
        dots = '      <div class="home-stor-dots" aria-hidden="true">'
        edits = (
            (f"{prev_anchor}\n{dots}", f"{prev_anchor}\n      {button}\n{dots}"),
            *_HOME_TESTIMONIALS_SCRIPT_EDITS,
        )
        after, state = _apply_edits(content, edits, "Home testimonials")
        planned.append(after)
        states.append(state)
    if states[0] != states[1]:
        raise ValueError("Partially changed Home testimonials language pair")
    return planned[0], planned[1]


def plan_residential_storage(english: str, german: str) -> tuple[str, str]:
    """Add aria-label to the Residential hero prompt and align ordering copy to inquiry flow."""
    en_edits = (
        (
            '<textarea class="lk-dialog-prompt" placeholder="Search residential systems, battery compatibility, backup options, or product documents..." rows="2"></textarea>',
            '<textarea class="lk-dialog-prompt" aria-label="Search residential systems, battery compatibility, backup options, or product documents" placeholder="Search residential systems, battery compatibility, backup options, or product documents..." rows="2"></textarea>',
        ),
        (
            '<span class="lk-stat-unit">Support after the Order</span>',
            '<span class="lk-stat-unit">Support after Delivery</span>',
        ),
        (
            "<p>Datasheets for the exact models in the order, and the unit certificates requested for registration with the local grid operator.</p>",
            "<p>Datasheets for the exact models in your inquiry, and the unit certificates requested for registration with the local grid operator.</p>",
        ),
        (
            '<span class="lk-pill-tag"><span class="lk-pill-dot"></span> HOW ORDERING WORKS</span>',
            '<span class="lk-pill-tag"><span class="lk-pill-dot"></span> FROM INQUIRY TO DELIVERY</span>',
        ),
        (
            '<span class="t-title">Order confirmation</span>',
            '<span class="t-title">Proforma &amp; availability</span>',
        ),
        (
            '<img alt="Check the home inverter, battery and meter on Linker before you order" loading="lazy" src="/wp-content/uploads/2026/09/linker-check-the-home-combination-1.webp"/>\n<h3>03 · Order confirmation</h3>\n<p>Your order is checked against stock in Germany, and you get a shipping date you can plan around.</p>',
            '<img alt="Check the home inverter, battery and meter on Linker before sending your inquiry" loading="lazy" src="/wp-content/uploads/2026/09/linker-check-the-home-combination-1.webp"/>\n<h3>03 · Proforma &amp; availability</h3>\n<p>Your inquiry is checked against stock in Germany, and you receive a proforma invoice with a shipping date you can plan around.</p>',
        ),
        (
            "Combinations are sold as listed packages with the compatibility lists on file; check the pairing before ordering.",
            "Combinations are supplied as matched packages with the compatibility lists on file; check the pairing before sending your inquiry.",
        ),
        (
            "Once saved to your Partner Account, you can send the Project to Linker for a quote. Check the pairing against the compatibility lists on file before placing the trade order.",
            "Once saved to your Partner Account, you can send the project to Linker for a quote. Check the pairing against the compatibility lists on file before sending your inquiry.",
        ),
        (
            "Linker requests the certification package for low-voltage grid connection with the German Verteilnetzbetreiber (DSO) for your order:",
            "Linker requests the certification package for low-voltage grid connection with the German Verteilnetzbetreiber (DSO) for your inquiry:",
        ),
        (
            "<summary>How do trade partners access net pricing and ordering?</summary>",
            "<summary>How do trade partners access net pricing and project quotes?</summary>",
        ),
    )
    de_edits = (
        (
            '<textarea class="lk-dialog-prompt" placeholder="Suchen Sie nach Heimspeichersystemen, Batteriekompatibilität, Notstromoptionen oder Produktunterlagen..." rows="2"></textarea>',
            '<textarea class="lk-dialog-prompt" aria-label="Suchen Sie nach Heimspeichersystemen, Batteriekompatibilität, Notstromoptionen oder Produktunterlagen" placeholder="Suchen Sie nach Heimspeichersystemen, Batteriekompatibilität, Notstromoptionen oder Produktunterlagen..." rows="2"></textarea>',
        ),
        (
            '<span class="lk-stat-unit">Support nach der Bestellung</span>',
            '<span class="lk-stat-unit">Support nach der Lieferung</span>',
        ),
        (
            "<p>Datenblätter für die genauen Modelle in der Bestellung und die für die Registrierung beim örtlichen Netzbetreiber angeforderten Einheitenzertifikate.</p>",
            "<p>Datenblätter für die genauen Modelle Ihrer Anfrage und die für die Registrierung beim örtlichen Netzbetreiber angeforderten Einheitenzertifikate.</p>",
        ),
        (
            '<span class="lk-pill-tag"><span class="lk-pill-dot"></span> SO FUNKTIONIERT DIE BESTELLUNG</span>',
            '<span class="lk-pill-tag"><span class="lk-pill-dot"></span> VON DER ANFRAGE BIS ZUR LIEFERUNG</span>',
        ),
        (
            '<span class="t-title">Auftragsbestätigung</span>',
            '<span class="t-title">Proforma &amp; Verfügbarkeit</span>',
        ),
        (
            '<img alt="Prüfen Sie den Heim-Wechselrichter, den Batteriespeicher und den Zähler auf Linker, bevor Sie bestellen" loading="lazy" src="/wp-content/uploads/2026/09/linker-check-the-home-combination-1.webp"/>\n<h3>03 · Auftragsbestätigung</h3>\n<p>Ihre Bestellung wird gegen den Lagerbestand in Deutschland geprüft, und Sie erhalten ein Versanddatum, mit dem Sie planen können.</p>',
            '<img alt="Prüfen Sie den Heim-Wechselrichter, den Batteriespeicher und den Zähler auf Linker vor Ihrer Anfrage" loading="lazy" src="/wp-content/uploads/2026/09/linker-check-the-home-combination-1.webp"/>\n<h3>03 · Proforma &amp; Verfügbarkeit</h3>\n<p>Ihre Anfrage wird gegen den Lagerbestand in Deutschland geprüft, und Sie erhalten eine Proformarechnung mit einem Versanddatum, mit dem Sie planen können.</p>',
        ),
        (
            "Kombinationen werden als gelistete Pakete mit den hinterlegten Kompatibilitätslisten verkauft; prüfen Sie die Kombination vor der Bestellung.",
            "Kombinationen werden als abgestimmte Pakete mit den hinterlegten Kompatibilitätslisten geliefert; prüfen Sie die Kombination vor Ihrer Anfrage.",
        ),
        (
            "Nach dem Speichern in Ihrem Partnerkonto können Sie das Projekt für ein Angebot an Linker senden. Prüfen Sie die Kombination vor der Handelsbestellung anhand der hinterlegten Kompatibilitätslisten.",
            "Nach dem Speichern in Ihrem Partnerkonto können Sie das Projekt für ein Angebot an Linker senden. Prüfen Sie die Kombination vor Ihrer Anfrage anhand der hinterlegten Kompatibilitätslisten.",
        ),
        (
            "Für Ihre Bestellung fordert Linker das Zertifizierungspaket für den Niederspannungsanschluss an das Netz des zuständigen deutschen Verteilnetzbetreibers (VNB) an:",
            "Für Ihre Anfrage fordert Linker das Zertifizierungspaket für den Niederspannungsanschluss an das Netz des zuständigen deutschen Verteilnetzbetreibers (VNB) an:",
        ),
        (
            "<summary>Wie erhalten Handelspartner Zugang zu Nettopreisen und Bestellungen?</summary>",
            "<summary>Wie erhalten Handelspartner Zugang zu Nettopreisen und Projektangeboten?</summary>",
        ),
    )
    if (
        len(re.findall(r'\bid="tv-rs-page-v1"', english)) != 1
        or len(re.findall(r'\bid="tv-rs-page-v1"', german)) != 1
    ):
        raise ValueError("Expected one existing Residential Storage root")
    en_after, en_state = _apply_edits(english, en_edits, "Residential Storage EN")
    de_after, de_state = _apply_edits(german, de_edits, "Residential Storage DE")
    if en_state != de_state:
        raise ValueError("Partially changed Residential Storage language pair")
    return en_after, de_after


def plan_commercial_storage(english: str, german: str) -> tuple[str, str]:
    """Add aria-label to the Commercial hero prompt in EN/DE."""
    en_edits = (
        (
            '<textarea class="lk-dialog-prompt" placeholder="Search outdoor cabinets, peak-shaving, or datasheets..." rows="2"></textarea>',
            '<textarea class="lk-dialog-prompt" aria-label="Search outdoor cabinets, peak-shaving, or datasheets" placeholder="Search outdoor cabinets, peak-shaving, or datasheets..." rows="2"></textarea>',
        ),
    )
    de_edits = (
        (
            '<textarea class="lk-dialog-prompt" placeholder="Suchen Sie nach Außenschränken, Lastspitzenkappung oder Datenblättern..." rows="2"></textarea>',
            '<textarea class="lk-dialog-prompt" aria-label="Suchen Sie nach Außenschränken, Lastspitzenkappung oder Datenblättern" placeholder="Suchen Sie nach Außenschränken, Lastspitzenkappung oder Datenblättern..." rows="2"></textarea>',
        ),
    )
    if (
        len(re.findall(r'\bid="tv-cs-page-v1"', english)) != 1
        or len(re.findall(r'\bid="tv-cs-page-v1"', german)) != 1
    ):
        raise ValueError("Expected one existing Commercial Storage root")
    en_after, en_state = _apply_edits(english, en_edits, "Commercial Storage EN")
    de_after, de_state = _apply_edits(german, de_edits, "Commercial Storage DE")
    if en_state != de_state:
        raise ValueError("Partially changed Commercial Storage language pair")
    return en_after, de_after


def plan_installer_ordering(english: str, german: str) -> tuple[str, str]:
    """Align Installer ordering/Bestellung wording to the inquiry workflow."""
    en_edits = (
        (
            "Warehouse stock in Germany, confirmed dispatch dates, and project documentation with the order.",
            "Warehouse stock in Germany, confirmed dispatch dates, and project documentation with your inquiry.",
        ),
        (
            "Communication schematics and meter connection guides come from the manuals on file; the grid compliance files are requested for your order.",
            "Communication schematics and meter connection guides come from the manuals on file; the grid compliance files are requested for your inquiry.",
        ),
        (
            "Unit certificates and grid connection documents, requested for your order.",
            "Unit certificates and grid connection documents, requested for your inquiry.",
        ),
        (
            "Wiring schematics and connection references come from the manuals on file. Linker requests the grid certificates for your order.",
            "Wiring schematics and connection references come from the manuals on file. Linker requests the grid certificates for your inquiry.",
        ),
        (
            "Unit certificates and CE declarations for DSO submission, requested for your order.",
            "Unit certificates and CE declarations for DSO submission, requested for your inquiry.",
        ),
        (
            '<img alt="Linker coordinates the warranty using your original order records" loading="lazy" src="/wp-content/uploads/2026/09/linker-warranty-coordination-for-installers.webp"/>',
            '<img alt="Linker coordinates the warranty using your original project records" loading="lazy" src="/wp-content/uploads/2026/09/linker-warranty-coordination-for-installers.webp"/>',
        ),
        (
            "If equipment requires service, Linker coordinates the warranty case with the manufacturer using your original project and order records.",
            "If equipment requires service, Linker coordinates the warranty case with the manufacturer using your original project records.",
        ),
        (
            "Backed by original project order records.",
            "Backed by original project records.",
        ),
        (
            '<img alt="Size, quote and order through the Linker Partner Portal" loading="lazy" src="/wp-content/uploads/2026/09/linker-the-installer-ordering-hub.webp"/>',
            '<img alt="Size, quote and send inquiries through the Linker Partner Portal" loading="lazy" src="/wp-content/uploads/2026/09/linker-the-installer-ordering-hub.webp"/>',
        ),
        (
            "        Order &amp; Delivery",
            "        Proforma &amp; Delivery",
        ),
        (
            '<img alt="Inverter, battery and meters sized on Linker before you order" loading="lazy" src="/wp-content/uploads/2026/09/linker-components-sized-on-linker-1.webp"/>',
            '<img alt="Inverter, battery and meters sized on Linker before sending your inquiry" loading="lazy" src="/wp-content/uploads/2026/09/linker-components-sized-on-linker-1.webp"/>',
        ),
        (
            "Inverter power, battery capacity, and matching metering options are sized to the load profile, with the compatibility lists and wiring references on file to check before ordering.",
            "Inverter power, battery capacity, and matching metering options are sized to the load profile, with the compatibility lists and wiring references on file to check before sending your inquiry.",
        ),
        (
            '<img alt="Order and follow the shipment through your Linker account" loading="lazy" src="/wp-content/uploads/2026/09/linker-equipment-to-your-schedule-1.webp"/>',
            '<img alt="Send inquiries and follow the shipment through your Linker account" loading="lazy" src="/wp-content/uploads/2026/09/linker-equipment-to-your-schedule-1.webp"/>',
        ),
        (
            "       STAGE 04 · ORDER &amp; DELIVERY",
            "       STAGE 04 · PROFORMA &amp; DELIVERY",
        ),
        (
            "Orders are checked against stock in Germany and dispatched with a confirmed delivery date.",
            "Inquiries are checked against stock in Germany and confirmed with a proforma invoice and delivery date.",
        ),
        (
            '<img alt="Wiring, documents and warranty stay available after the order through Linker" loading="lazy" src="/wp-content/uploads/2026/09/linker-support-on-site-and-beyond-1.webp"/>',
            '<img alt="Wiring, documents and warranty stay available after delivery through Linker" loading="lazy" src="/wp-content/uploads/2026/09/linker-support-on-site-and-beyond-1.webp"/>',
        ),
        (
            "       STAGE 05 · AFTER THE ORDER",
            "       STAGE 05 · AFTER DELIVERY",
        ),
        (
            "     Five questions installers ask before ordering.",
            "     Five questions installers ask before sending an inquiry.",
        ),
        (
            "Combinations are sold as listed packages with the compatibility lists on file; check the pairing before ordering.",
            "Combinations are supplied as matched packages with the compatibility lists on file; check the pairing before sending your inquiry.",
        ),
        (
            "Linker requests the certification package for grid connection with the local Verteilnetzbetreiber (DSO) for your storage order.",
            "Linker requests the certification package for grid connection with the local Verteilnetzbetreiber (DSO) for your storage inquiry.",
        ),
        (
            "Once the order is confirmed, you receive a dispatch date based on current availability.",
            "Once the proforma invoice is confirmed, you receive a dispatch date based on current availability.",
        ),
        (
            "Open Warranty &amp; Replacements from your order with the serial number, model and fault description, and our team in Germany opens the case.",
            "Contact us with your invoice or proforma reference, serial number, model and fault description, and our team in Germany opens the case.",
        ),
    )
    de_edits = (
        (
            "Lagerbestand in Deutschland, bestätigte Versandtermine und Projektdokumentation mit der Bestellung.",
            "Lagerbestand in Deutschland, bestätigte Versandtermine und Projektdokumentation zu Ihrer Anfrage.",
        ),
        (
            "Kommunikationsschaltpläne und Anleitungen zum Zähleranschluss stammen aus den hinterlegten Handbüchern; die Netzanschluss-Dokumente werden für Ihre Bestellung angefordert.",
            "Kommunikationsschaltpläne und Anleitungen zum Zähleranschluss stammen aus den hinterlegten Handbüchern; die Netzanschluss-Dokumente werden für Ihre Anfrage angefordert.",
        ),
        (
            "        Einheitenzertifikate und Netzanschlussdokumente, für Ihre Bestellung angefordert.",
            "        Einheitenzertifikate und Netzanschlussdokumente, für Ihre Anfrage angefordert.",
        ),
        (
            "Verdrahtungspläne und Anschlussinformationen stammen aus den hinterlegten Handbüchern. Linker fordert die Netzanschlusszertifikate für Ihre Bestellung an.",
            "Verdrahtungspläne und Anschlussinformationen stammen aus den hinterlegten Handbüchern. Linker fordert die Netzanschlusszertifikate für Ihre Anfrage an.",
        ),
        (
            "         Einheitenzertifikate und CE-Erklärungen für die Einreichung beim Netzbetreiber, für Ihre Bestellung angefordert.",
            "         Einheitenzertifikate und CE-Erklärungen für die Einreichung beim Netzbetreiber, für Ihre Anfrage angefordert.",
        ),
        (
            '<img alt="Linker koordiniert die Garantie anhand Ihrer ursprünglichen Bestellunterlagen" loading="lazy" src="/wp-content/uploads/2026/09/linker-warranty-coordination-for-installers.webp"/>',
            '<img alt="Linker koordiniert die Garantie anhand Ihrer ursprünglichen Projektunterlagen" loading="lazy" src="/wp-content/uploads/2026/09/linker-warranty-coordination-for-installers.webp"/>',
        ),
        (
            "Wenn Ausrüstung einen Service benötigt, koordiniert Linker den Garantiefall mit dem Hersteller anhand Ihrer ursprünglichen Projekt- und Bestelldatensätze.",
            "Wenn Ausrüstung einen Service benötigt, koordiniert Linker den Garantiefall mit dem Hersteller anhand Ihrer ursprünglichen Projektunterlagen.",
        ),
        (
            '<img alt="Auslegung, Angebot und Bestellung über das Linker-Partnerportal" loading="lazy" src="/wp-content/uploads/2026/09/linker-the-installer-ordering-hub.webp"/>',
            '<img alt="Auslegung, Angebot und Anfrage über das Linker-Partnerportal" loading="lazy" src="/wp-content/uploads/2026/09/linker-the-installer-ordering-hub.webp"/>',
        ),
        (
            "        Auftrag &amp; Lieferung",
            "        Proforma &amp; Lieferung",
        ),
        (
            '<img alt="Wechselrichter, Batteriespeicher und Zähler auf Linker ausgelegt, bevor Sie bestellen" loading="lazy" src="/wp-content/uploads/2026/09/linker-components-sized-on-linker-1.webp"/>',
            '<img alt="Wechselrichter, Batteriespeicher und Zähler auf Linker vor Ihrer Anfrage ausgelegt" loading="lazy" src="/wp-content/uploads/2026/09/linker-components-sized-on-linker-1.webp"/>',
        ),
        (
            "Wechselrichterleistung, Batteriekapazität und passende Messoptionen werden auf das Lastprofil dimensioniert; die hinterlegten Kompatibilitätslisten und Verdrahtungsunterlagen prüfen Sie vor der Bestellung.",
            "Wechselrichterleistung, Batteriekapazität und passende Messoptionen werden auf das Lastprofil dimensioniert; die hinterlegten Kompatibilitätslisten und Verdrahtungsunterlagen prüfen Sie vor Ihrer Anfrage.",
        ),
        (
            '<img alt="Bestellung und Sendungsverfolgung über Ihr Linker-Konto" loading="lazy" src="/wp-content/uploads/2026/09/linker-equipment-to-your-schedule-1.webp"/>',
            '<img alt="Anfragen und Sendungsverfolgung über Ihr Linker-Konto" loading="lazy" src="/wp-content/uploads/2026/09/linker-equipment-to-your-schedule-1.webp"/>',
        ),
        (
            "       PHASE 04 · BESTELLUNG & LIEFERUNG",
            "       PHASE 04 · PROFORMA & LIEFERUNG",
        ),
        (
            "Bestellungen werden gegen den Lagerbestand in Deutschland geprüft und mit einem bestätigten Lieferdatum versandt.",
            "Anfragen werden gegen den Lagerbestand in Deutschland geprüft und mit Proformarechnung sowie Lieferdatum bestätigt.",
        ),
        (
            '<img alt="Verkabelung, Dokumente und Garantie bleiben nach der Bestellung über Linker verfügbar" loading="lazy" src="/wp-content/uploads/2026/09/linker-support-on-site-and-beyond-1.webp"/>',
            '<img alt="Verkabelung, Dokumente und Garantie bleiben nach der Lieferung über Linker verfügbar" loading="lazy" src="/wp-content/uploads/2026/09/linker-support-on-site-and-beyond-1.webp"/>',
        ),
        (
            "       PHASE 05 · NACH DER BESTELLUNG",
            "       PHASE 05 · NACH DER LIEFERUNG",
        ),
        (
            "     Fünf Fragen, die Installateure vor der Bestellung stellen.",
            "     Fünf Fragen, die Installateure vor einer Anfrage stellen.",
        ),
        (
            "Kombinationen werden als gelistete Pakete mit den hinterlegten Kompatibilitätslisten verkauft; prüfen Sie die Kombination vor der Bestellung.",
            "Kombinationen werden als abgestimmte Pakete mit den hinterlegten Kompatibilitätslisten geliefert; prüfen Sie die Kombination vor Ihrer Anfrage.",
        ),
        (
            "Für Ihre Speicherbestellung fordert Linker das Zertifizierungspaket für den Anschluss an das Netz des örtlichen Verteilnetzbetreibers (VNB) an.",
            "Für Ihre Speicheranfrage fordert Linker das Zertifizierungspaket für den Anschluss an das Netz des örtlichen Verteilnetzbetreibers (VNB) an.",
        ),
        (
            "Sobald die Bestellung bestätigt ist, erhalten Sie ein Versanddatum auf Basis der aktuellen Verfügbarkeit.",
            "Sobald die Proformarechnung bestätigt ist, erhalten Sie ein Versanddatum auf Basis der aktuellen Verfügbarkeit.",
        ),
        (
            "Öffnen Sie „Garantie &amp; Ersatz“ aus Ihrer Bestellung mit Seriennummer, Modell und Fehlerbeschreibung; unser Team in Deutschland eröffnet den Fall.",
            "Kontaktieren Sie uns mit Ihrer Rechnungs- oder Proforma-Referenz, Seriennummer, Modell und Fehlerbeschreibung; unser Team in Deutschland eröffnet den Fall.",
        ),
    )
    if (
        len(re.findall(r'\bid="installer-journal"', english)) != 1
        or len(re.findall(r'\bid="installer-journal"', german)) != 1
    ):
        raise ValueError("Expected one existing Installer root")
    en_after, en_state = _apply_edits(english, en_edits, "Installer ordering EN")
    de_after, de_state = _apply_edits(german, de_edits, "Installer ordering DE")
    if en_state != de_state:
        raise ValueError("Partially changed Installer ordering language pair")
    return en_after, de_after


def plan_faq_ordering(english: str, german: str) -> tuple[str, str]:
    """Align FAQ & Documents page body ordering/Bestellung wording to the inquiry workflow."""
    en_edits = (
        (
            '<a class="rd-qk" href="#rd-general">Ordering</a>',
            '<a class="rd-qk" href="#rd-general">Inquiries</a>',
        ),
        (
            '<button type="button" class="rd-gcat on" data-gcat="gc0"><span>Ordering & delivery</span><span class="k">4</span></button>',
            '<button type="button" class="rd-gcat on" data-gcat="gc0"><span>Inquiries & delivery</span><span class="k">4</span></button>',
        ),
        (
            "There is no pallet minimum. Orders start from individual units, delivered across the EU. Equipment ships according to project schedules, with trade quotes detailing destination freight.",
            "There is no pallet minimum. Inquiries start from individual units, delivered across the EU. Equipment ships according to project schedules, with trade quotes detailing destination freight.",
        ),
        (
            '<summary>Can different brands be combined in one project order?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Yes. Inverters, batteries, smart meters, and accessories from different brands can be combined in one order. They ship together under a unified invoice; check each pairing against the compatibility lists on file before ordering.</p></div>',
            '<summary>Can different brands be combined in one project inquiry?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Yes. Inverters, batteries, smart meters, and accessories from different brands can be combined in one project inquiry. They ship together under a unified invoice; check each pairing against the compatibility lists on file before sending your inquiry.</p></div>',
        ),
        (
            "Both. Installers can order packaged systems with matching balance-of-system components, or source individual replacement units and accessories.",
            "Both. Installers can request packaged systems with matching balance-of-system components, or source individual replacement units and accessories.",
        ),
        (
            "Linker handles any claim for you, from your order.",
            "Linker handles any claim for you, based on your project records.",
        ),
        (
            'Open Warranty &amp; Replacements from your order. The signed-in account confirms the order, and the form keeps the serial number, model, and fault description with that order. Linker handles the diagnostic exchange with the manufacturer\'s technical desk. <a href="/contact/?intent=support&amp;source=https%3A%2F%2Fde-linker.com%2Ffaq-download%2F&amp;kind=document&amp;source_id=932" data-linker-contact="{&quot;url&quot;:&quot;https://de-linker.com/faq-download/&quot;,&quot;kind&quot;:&quot;document&quot;,&quot;intent&quot;:&quot;support&quot;,&quot;source_id&quot;:932}">Open Warranty &amp; Replacements</a>.',
            'For a warranty claim, contact us with your invoice or proforma reference, serial number, model, and fault description. Linker handles the diagnostic exchange with the manufacturer\'s technical desk. <a href="/contact/?intent=support&amp;source=https%3A%2F%2Fde-linker.com%2Ffaq-download%2F&amp;kind=document&amp;source_id=932" data-linker-contact="{&quot;url&quot;:&quot;https://de-linker.com/faq-download/&quot;,&quot;kind&quot;:&quot;document&quot;,&quot;intent&quot;:&quot;support&quot;,&quot;source_id&quot;:932}">Contact us about Warranty &amp; Replacements</a>.',
        ),
        (
            '<summary>What technical support is included with an order?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Linker provides sizing tools and wiring references before the order, and live commissioning troubleshooting from the engineering desk in Germany.</p></div>',
            '<summary>What technical support is included with a project?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Linker provides sizing tools and wiring references during planning, and live commissioning troubleshooting from the engineering desk in Germany.</p></div>',
        ),
        (
            "Linker requests the certificates for the models in your order.",
            "Linker requests the certificates for the models in your inquiry.",
        ),
        (
            '<summary>Are Declarations of Conformity provided with orders?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Yes, on request: Linker requests the CE Declarations of Conformity and relevant test certificates for the models in your order.</p></div>',
            '<summary>Are Declarations of Conformity provided on request?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Yes, on request: Linker requests the CE Declarations of Conformity and relevant test certificates for the models in your inquiry.</p></div>',
        ),
    )
    de_edits = (
        (
            '<a class="rd-qk" href="#rd-general">Bestellung</a>',
            '<a class="rd-qk" href="#rd-general">Anfragen</a>',
        ),
        (
            '<div class="rd-sechead"><span class="rd-kicker">Vor Ihrer Bestellung</span><h2 class="rd-hlg">Kaufmännische Regeln und Handelsbedingungen.</h2></div>',
            '<div class="rd-sechead"><span class="rd-kicker">Vor Ihrer Anfrage</span><h2 class="rd-hlg">Kaufmännische Regeln und Handelsbedingungen.</h2></div>',
        ),
        (
            '<button type="button" class="rd-gcat on" data-gcat="gc0"><span>Bestellung & Lieferung</span><span class="k">4</span></button>',
            '<button type="button" class="rd-gcat on" data-gcat="gc0"><span>Anfrage & Lieferung</span><span class="k">4</span></button>',
        ),
        (
            "Es gibt kein Palettenminimum. Bestellungen starten ab einzelnen Einheiten, geliefert in der gesamten EU. Ausrüstung wird gemäß Projektzeitplänen versandt, wobei Handelsangebote die Frachtkosten zum Zielort ausweisen.",
            "Es gibt kein Palettenminimum. Anfragen sind ab einzelnen Einheiten möglich, geliefert in der gesamten EU. Ausrüstung wird gemäß Projektzeitplänen versandt, wobei Handelsangebote die Frachtkosten zum Zielort ausweisen.",
        ),
        (
            '<summary>Können verschiedene Marken in einer Projektbestellung kombiniert werden?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Ja. Wechselrichter, Batteriespeicher, Smart Meter und Zubehör verschiedener Marken können in einer Bestellung kombiniert werden. Sie werden zusammen mit einer einheitlichen Rechnung geliefert; prüfen Sie jede Kombination vor der Bestellung anhand der hinterlegten Kompatibilitätslisten.</p></div>',
            '<summary>Können verschiedene Marken in einer Projektanfrage kombiniert werden?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Ja. Wechselrichter, Batteriespeicher, Smart Meter und Zubehör verschiedener Marken können in einer Projektanfrage kombiniert werden. Sie werden zusammen mit einer einheitlichen Rechnung geliefert; prüfen Sie jede Kombination vor Ihrer Anfrage anhand der hinterlegten Kompatibilitätslisten.</p></div>',
        ),
        (
            "Beides. Installateure können paketierte Systeme mit passenden Balance-of-System-Komponenten bestellen oder einzelne Ersatzeinheiten und Zubehör beziehen.",
            "Beides. Installateure können paketierte Systeme mit passenden Balance-of-System-Komponenten anfragen oder einzelne Ersatzeinheiten und Zubehör beziehen.",
        ),
        (
            "Linker wickelt jeden Anspruch für Sie ab, ausgehend von Ihrer Bestellung.",
            "Linker wickelt jeden Anspruch für Sie ab, ausgehend von Ihren Projektunterlagen.",
        ),
        (
            'Öffnen Sie Garantie & Ersatz aus Ihrer Bestellung. Das angemeldete Konto bestätigt die Bestellung, und das Formular hält Seriennummer, Modell und Fehlerbeschreibung bei dieser Bestellung. Linker übernimmt den diagnostischen Austausch mit dem technischen Support des Herstellers. <a href="/de/kontakt/?intent=support&#038;source=https%3A%2F%2Fde-linker.com%2Fde%2Ffaq-dokumente%2F&#038;kind=document&#038;source_id=6863" data-linker-contact="{&quot;url&quot;:&quot;https://de-linker.com/de/faq-dokumente/&quot;,&quot;kind&quot;:&quot;document&quot;,&quot;intent&quot;:&quot;support&quot;,&quot;source_id&quot;:6863}">Garantie & Ersatz öffnen</a>.',
            'Für einen Garantieanspruch kontaktieren Sie uns mit Ihrer Rechnungs- oder Proforma-Referenz, Seriennummer, Modell und Fehlerbeschreibung. Linker übernimmt den diagnostischen Austausch mit dem technischen Support des Herstellers. <a href="/de/kontakt/?intent=support&#038;source=https%3A%2F%2Fde-linker.com%2Fde%2Ffaq-dokumente%2F&#038;kind=document&#038;source_id=6863" data-linker-contact="{&quot;url&quot;:&quot;https://de-linker.com/de/faq-dokumente/&quot;,&quot;kind&quot;:&quot;document&quot;,&quot;intent&quot;:&quot;support&quot;,&quot;source_id&quot;:6863}">Kontakt zu Garantie & Ersatz</a>.',
        ),
        (
            '<summary>Welcher technische Support ist bei einer Bestellung enthalten?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Linker stellt vor der Bestellung Auslegungswerkzeuge und Verdrahtungsunterlagen bereit und unterstützt bei der Inbetriebnahme mit Live-Fehlersuche durch das technische Team in Deutschland.</p></div>',
            '<summary>Welcher technische Support ist bei einem Projekt enthalten?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Linker stellt bei der Planung Auslegungswerkzeuge und Verdrahtungsunterlagen bereit und unterstützt bei der Inbetriebnahme mit Live-Fehlersuche durch das technische Team in Deutschland.</p></div>',
        ),
        (
            "Linker fordert die Zertifikate für die Modelle in Ihrer Bestellung an.",
            "Linker fordert die Zertifikate für die Modelle Ihrer Anfrage an.",
        ),
        (
            '<summary>Werden Konformitätserklärungen mit Bestellungen bereitgestellt?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Ja, auf Anfrage: Linker fordert die CE-Konformitätserklärungen und relevanten Prüfzertifikate für die Modelle in Ihrer Bestellung an.</p></div>',
            '<summary>Werden Konformitätserklärungen auf Anfrage bereitgestellt?<span class="pm" aria-hidden="true"></span></summary><div class="rd-fa"><p>Ja, auf Anfrage: Linker fordert die CE-Konformitätserklärungen und relevanten Prüfzertifikate für die Modelle Ihrer Anfrage an.</p></div>',
        ),
    )
    if (
        len(re.findall(r'\bid="rd-general"', english)) != 1
        or len(re.findall(r'\bid="rd-general"', german)) != 1
    ):
        raise ValueError("Expected one existing FAQ & Documents general section")
    en_after, en_state = _apply_edits(english, en_edits, "FAQ ordering EN")
    de_after, de_state = _apply_edits(german, de_edits, "FAQ ordering DE")
    if en_state != de_state:
        raise ValueError("Partially changed FAQ ordering language pair")
    return en_after, de_after


def plan_pair(family: str, english: str, german: str) -> tuple[str, str]:
    """Accept a complete old or final pair; preserve all other source bytes."""
    paired_families = {
        "thank_you_blog": plan_thank_you_blog,
        "thank_you_inquiry": plan_thank_you_inquiry,
        "home_testimonials": plan_home_testimonials,
        "residential_storage": plan_residential_storage,
        "commercial_storage": plan_commercial_storage,
        "installer_ordering": plan_installer_ordering,
        "faq_ordering": plan_faq_ordering,
    }
    if family in paired_families:
        return paired_families[family](english, german)
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
