"""Mechanical checks for the #335 i18n and page-drift battery.

The bars are the ticket and the specs it names: EN/DE twins share block
structure, card set and cited numbers; a German answer is Sie-form and keeps
AGENTS.md §3's banned words out; a handoff names the team mailbox in that
language; a page edit is fresh only when the rendered page, the read-page
tool and the answer all carry the edit. Mixed-language and mid-thread
language turns are graded against the same rule the prompt states (#374)
and reported, not repaired.
"""

from __future__ import annotations

import re
from typing import Any

# ground.BANNED_WORDS, plus Einkaufswagen (banned-de.json). Whole words.
# Artikel stays banned in a Genie answer: the legal-citation allowance is for
# site copy (docs/specs/265-german-checks.md), not for this assistant.
BANNED = re.compile(
    r"\b(?:articles?|catalogues?|catalogs?|carts?|baskets?|"
    r"artikel[ns]?|katalog(?:e|en|s)?|einkaufswagen[s]?|"
    r"warenk(?:o|ö)rb(?:e|en|s)?)\b",
    re.IGNORECASE,
)
# banned-de.json pronouns. Whole words, so "direkt" and "Dichtung" stay.
DU = re.compile(
    r"\b(?:du|dich|dir|dein|deine|deinen|deinem|deiner|deines|"
    r"euch|euer|eure|euren|eurem|eurer|eures)\b",
    re.IGNORECASE,
)
# A measurement, not a digit inside a model code (H2-10K-T3).
_NUMBER = re.compile(r"(?<![A-Za-z0-9])(\d+(?:[.,]\d+)?)(?![A-Za-z0-9])")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# page.py leaves a sum of money out of the page text; a guest card must not
# print one either (CommerceState: the gate sentence, not the net price).
_MONEY = re.compile(r"€\s?\d|\d[\d.,]*\s?(?:€|EUR\b)")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_ENGLISH = frozenset(
    """
    a the and or with for of to from on at by which what how does did do
    is are be been can could would should your you this that these those our
    my please show tell where when why who not have has about between than
    into work works any some there here only just but if we they them
    their it its batteries battery price prices datasheet availability
    """.split()
)
_GERMAN = frozenset(
    """
    der die das den dem des ein eine einer einem einen eines und oder mit
    für fuer von zu zum zur auf aus bei nach über ueber welche welcher
    welches welchen welchem wie wo warum wieso nicht kein keine keinem
    keinen keiner ist sind bin bist seid haben habe habt hat ich sie ihnen
    ihr ihre ihrer ihrem ihren ihres mein meine meinem meinen meiner bitte
    auch dass wenn dann noch schon aber als bis durch ohne gegen um kann
    können koennen muss müssen muessen soll sollen wird werden wurde wurden
    passen passt batterien batterie speicher preis preise empfehlung
    empfehlungen kosten seite nennt
    """.split()
)

# HandoffTeam::execute. The mailbox is the site's, not a second copy.
HANDOFF_EN = "Our team will answer that at {email}."
HANDOFF_DE = "Unser Team beantwortet das unter {email}."

# Entries::prompts for the pages that do not take the preview card's questions.
DRAFT_EN = ["Check my draft", "What happens next?"]
DRAFT_DE = ["Meinen Entwurf prüfen", "Wie geht es weiter?"]
ACCOUNT_EN = ["Where is my Proforma?", "What happens next?"]
ACCOUNT_DE = ["Wo steht meine Proforma?", "Wie geht es weiter?"]
FAQ_EN = [
    "Is there a datasheet for my model?",
    "Which batteries work with my inverter?",
]
FAQ_DE = [
    "Gibt es ein Datenblatt zu meinem Modell?",
    "Welche Batterien passen zu meinem Wechselrichter?",
]
BLOG_POST_EN = [
    "Summarize this post",
    "Which products does this post apply to?",
]
BLOG_POST_DE = [
    "Worum geht es in diesem Beitrag?",
    "Welche Produkte betrifft dieser Beitrag?",
]
# Preview::copy product asks, German from linker-tools-de_DE_formal.po.
PRODUCT_EN = [
    "What pairs with the {name}?",
    "Show the documents for the {name}",
    "Compare the {name} with similar models",
]
PRODUCT_DE = [
    "{name}: Was passt dazu?",
    "{name}: Unterlagen anzeigen",
    "{name} mit ähnlichen Modellen vergleichen",
]
CATEGORY_EN = [
    "{name}: which model fits my project?",
    "{name}: how do the series differ?",
]
CATEGORY_DE = [
    "{name}: Welches Modell passt zu meinem Projekt?",
    "{name}: Worin unterscheiden sich die Serien?",
]


def banned_words(text: str) -> list[str]:
    """Banned vocabulary in a shipped answer, lowercased, in order."""
    return [match.group(0).lower() for match in BANNED.finditer(text)]


def du_pronouns(text: str) -> list[str]:
    """du-form pronouns. Sie-form German does not use them."""
    return [match.group(0).lower() for match in DU.finditer(text)]


def standalone_numbers(text: str) -> list[str]:
    """Numbers that are not part of a model code, with a comma read as a dot."""
    found: list[str] = []
    for match in _NUMBER.finditer(text):
        raw = match.group(1).replace(",", ".")
        if "." in raw:
            raw = raw.rstrip("0").rstrip(".")
        found.append(raw)
    return found


def emails_in(text: str) -> list[str]:
    return _EMAIL.findall(text)


def money_in(text: str) -> bool:
    return _MONEY.search(text) is not None


def language_of(text: str) -> str:
    """`en`, `de`, `mixed` or `neutral`, the #374 vote on closed-class words.

    An umlaut is German before the lists. A brand or a model code is neither.
    """
    english = False
    german = False
    for word in _WORD.findall(text.lower()):
        if any(letter in word for letter in "äöüß"):
            german = True
            continue
        if word in _GERMAN:
            german = True
        elif word in _ENGLISH:
            english = True
    if english and german:
        return "mixed"
    if german:
        return "de"
    if english:
        return "en"
    return "neutral"


def visible_text(blocks: list[dict[str, Any]]) -> str:
    """What the customer reads: text, handoff summary, and card price lines."""
    parts: list[str] = []
    for block in blocks:
        kind = block.get("type")
        if kind == "text" and isinstance(block.get("text"), str):
            parts.append(block["text"])
        elif kind == "handoff" and isinstance(block.get("summary"), str):
            parts.append(block["summary"])
        elif kind == "cards":
            for price in block.get("prices") or []:
                if isinstance(price, dict) and isinstance(price.get("text"), str):
                    parts.append(price["text"])
    return "\n".join(parts)


def block_types(blocks: list[dict[str, Any]]) -> list[str]:
    return [str(block.get("type")) for block in blocks]


def card_ids(blocks: list[dict[str, Any]]) -> list[int]:
    ids: list[int] = []
    for block in blocks:
        if block.get("type") in ("cards", "compare"):
            for raw in block.get("product_ids") or []:
                if isinstance(raw, int):
                    ids.append(raw)
    return ids


def price_lines(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") != "cards":
            continue
        for price in block.get("prices") or []:
            if isinstance(price, dict):
                lines.append(price)
    return lines


def handoff_summary(blocks: list[dict[str, Any]]) -> str | None:
    for block in blocks:
        summary = block.get("summary")
        if block.get("type") == "handoff" and isinstance(summary, str):
            return summary
    return None


def _structure_split(
    en_blocks: list[dict[str, Any]], de_blocks: list[dict[str, Any]]
) -> tuple[str | None, str | None]:
    """A block-type defect, or a document-count note.

    An ask block is optional on either side. A document-count difference is
    a note: retrieval can add a document without changing the card set. Any
    other block-type difference is a defect.
    """
    en_types = [kind for kind in block_types(en_blocks) if kind != "ask"]
    de_types = [kind for kind in block_types(de_blocks) if kind != "ask"]
    if en_types == de_types:
        return None, None
    en_core = [kind for kind in en_types if kind != "document"]
    de_core = [kind for kind in de_types if kind != "document"]
    if en_core == de_core:
        return None, (
            f"document count en {en_types.count('document')} "
            f"de {de_types.count('document')}; retrieval can add a document "
            "without changing the card set"
        )
    return f"block types en {en_types} de {de_types}", None


def _figure_split(en_text: str, de_text: str) -> tuple[str | None, str | None]:
    """A number defect, or a note when one side only adds figures.

    The shared figures were graded. Extras on one side (the German voltage
    window, or kWh steps the other prose omits) stay a note in the data.
    Disjoint figures are a defect. Order and repeated tokens are not.
    """
    en_nums = standalone_numbers(en_text)
    de_nums = standalone_numbers(de_text)
    en_set = set(en_nums)
    de_set = set(de_nums)
    if en_set == de_set:
        return None, None
    shared = en_set & de_set
    en_only = en_set - de_set
    de_only = de_set - en_set
    rendered = "numbers en " + ",".join(en_nums) + " de " + ",".join(de_nums)
    if shared and (not en_only or not de_only):
        return None, (rendered + "; shared figures match and one side adds figures")
    return rendered, None


def twin_notes(
    en_blocks: list[dict[str, Any]],
    de_blocks: list[dict[str, Any]],
    *,
    expect_numbers: bool,
) -> list[str]:
    """Justified notes. These are graded, and they are not defects."""
    notes: list[str] = []
    if expect_numbers:
        _defect, note = _figure_split(visible_text(en_blocks), visible_text(de_blocks))
        if note:
            notes.append(note)
    _structure_defect, structure_note = _structure_split(en_blocks, de_blocks)
    if structure_note:
        notes.append(structure_note)
    return notes


def twin_reasons(
    en_blocks: list[dict[str, Any]],
    de_blocks: list[dict[str, Any]],
    *,
    expect_cards: bool,
    expect_handoff: bool,
    expect_numbers: bool,
) -> list[str]:
    """Hard mismatches between one English turn and its German twin.

    A document-count difference and a one-sided extra figure are notes
    (`twin_notes`), not defects. An ask block is ignored.
    """
    reasons: list[str] = []
    en_text = visible_text(en_blocks)
    de_text = visible_text(de_blocks)
    en_banned = banned_words(en_text)
    de_banned = banned_words(de_text)
    if en_banned:
        reasons.append("en banned words: " + ", ".join(en_banned))
    if de_banned:
        reasons.append("de banned words: " + ", ".join(de_banned))
    du = du_pronouns(de_text)
    if du:
        reasons.append("de du-form: " + ", ".join(du))
    en_lang = language_of(en_text)
    de_lang = language_of(de_text)
    if en_lang not in ("en", "neutral"):
        reasons.append(f"en answer language is {en_lang}")
    if de_lang not in ("de", "neutral"):
        reasons.append(f"de answer language is {de_lang}")
    en_ids = set(card_ids(en_blocks))
    de_ids = set(card_ids(de_blocks))
    if expect_cards and not en_ids:
        reasons.append("en has no cards")
    if expect_cards and not de_ids:
        reasons.append("de has no cards")
    if en_ids != de_ids:
        reasons.append(f"card set en {sorted(en_ids)} de {sorted(de_ids)}")
    en_handoff = handoff_summary(en_blocks)
    de_handoff = handoff_summary(de_blocks)
    if expect_handoff and en_handoff is None:
        reasons.append("en has no handoff")
    if expect_handoff and de_handoff is None:
        reasons.append("de has no handoff")
    if (en_handoff is None) != (de_handoff is None):
        reasons.append("handoff on one side only")
    if en_handoff is not None and de_handoff is not None:
        reasons.extend(handoff_reasons(en_handoff, de_handoff))
    if expect_numbers:
        defect, _note = _figure_split(en_text, de_text)
        if defect:
            reasons.append(defect)
    structure_defect, _structure_note = _structure_split(en_blocks, de_blocks)
    if structure_defect:
        reasons.append(structure_defect)
    return reasons


def handoff_reasons(en_summary: str, de_summary: str) -> list[str]:
    """The mailbox sentence is the tool's sentence for that language."""
    reasons: list[str] = []
    en_mail = emails_in(en_summary)
    de_mail = emails_in(de_summary)
    if len(en_mail) != 1 or len(de_mail) != 1 or en_mail[0] != de_mail[0]:
        reasons.append(f"mailbox en {en_mail} de {de_mail}")
        return reasons
    email = en_mail[0]
    if en_summary != HANDOFF_EN.format(email=email):
        reasons.append("en handoff is not the mailbox sentence")
    if de_summary != HANDOFF_DE.format(email=email):
        reasons.append("de handoff is not the German mailbox sentence")
    return reasons


def price_reasons(
    lines: list[dict[str, Any]], locale: str, *, guest: bool
) -> list[str]:
    """A guest card's price line is the page's sentence, in the turn language."""
    reasons: list[str] = []
    if not lines:
        return ["no price line on the card"]
    for line in lines:
        text = line.get("text")
        if not isinstance(text, str) or not text:
            reasons.append(f"empty price line for {line.get('product_id')}")
            continue
        lang = language_of(text)
        if lang not in (locale, "neutral"):
            reasons.append(f"price line language {lang} for locale {locale}: {text}")
        if guest and money_in(text):
            reasons.append(f"guest card prints a sum: {text}")
        if guest and line.get("reason") is None and money_in(text):
            reasons.append(f"guest price has no reason: {text}")
    return reasons


def prompt_reasons(
    prompts: list[str],
    locale: str,
    *,
    minimum: int = 2,
    must_name: str | None = None,
    english_exact: list[str] | None = None,
    german_exact: list[str] | None = None,
) -> list[str]:
    """Opening suggestions: at least two, in the page language, naming the page."""
    reasons: list[str] = []
    if len(prompts) < minimum:
        reasons.append(f"{len(prompts)} prompts, want at least {minimum}")
    if english_exact is not None and locale == "en" and prompts != english_exact:
        reasons.append(f"en prompts {prompts} != {english_exact}")
    if german_exact is not None and locale == "de" and prompts != german_exact:
        reasons.append(f"de prompts {prompts} != {german_exact}")
    for prompt in prompts:
        if locale == "de":
            banned = banned_words(prompt)
            du = du_pronouns(prompt)
            if banned:
                reasons.append(f"prompt banned {banned}: {prompt}")
            if du:
                reasons.append(f"prompt du-form {du}: {prompt}")
            lang = language_of(prompt)
            # A prompt that is only a model name ("SAJ H2-10K-T3: …") still
            # has German around the name when the page is German. Neutral is
            # a model-only chip, which the preview card does not ship.
            if lang == "en":
                reasons.append(f"german prompt is english: {prompt}")
        else:
            banned = banned_words(prompt)
            if banned:
                reasons.append(f"prompt banned {banned}: {prompt}")
    if must_name:
        if not any(must_name in prompt for prompt in prompts):
            reasons.append(f"no prompt names {must_name!r}")
    return reasons


def drift_attribution(
    *,
    http_has_marker: bool,
    tool_called: bool,
    tool_has_marker: bool,
    answer_has_marker: bool,
) -> str:
    """Where a page edit landed: the render, the read-page cache, or the answer.

    `http_has_marker` is a fresh GET of the page the customer would reload.
    `tool_has_marker` is the `linker/read-page` body (`result.text`) only.
    The shell's `title` is not the body: counting it made
    `title-fresh-body-stale` unreachable and labelled a stale body
    `model-ignored-fresh-page`. A title the shell sends can reach the answer
    without a read; a body token cannot, so a marker with no read is the
    prompt title.
    """
    if not http_has_marker:
        return "edit-not-rendered"
    if not tool_called:
        if answer_has_marker:
            return "answered-from-prompt-title"
        return "page-not-read"
    if tool_has_marker and answer_has_marker:
        return "fresh"
    if not tool_has_marker and not answer_has_marker:
        return "stale-cache"
    if not tool_has_marker and answer_has_marker:
        return "title-fresh-body-stale"
    return "model-ignored-fresh-page"


def title_with_marker(original: str, marker: str) -> str:
    """The product title plus a marker, keeping a trailing parenthetical.

    `Preview::product_name` strips only a parenthetical at the end, so the
    marker stays in the name the opening prompts use.
    """
    match = re.search(r"\s*(\([^()]*\))\s*$", original)
    if match is None:
        return f"{original.strip()} {marker}"
    base = original[: match.start()].strip()
    return f"{base} {marker} {match.group(1)}"


def filled(templates: list[str], name: str) -> list[str]:
    return [item.format(name=name) for item in templates]


def answer_language_reasons(question: str, answer: str, page_locale: str) -> list[str]:
    """#374: a clear question language wins; mixed or neutral follows the page.

    Reported for the language cases. A mixed question has no single language,
    so the page locale is the rule the prompt actually states.
    """
    wanted = language_of(question)
    if wanted in ("neutral", "mixed"):
        wanted = page_locale
    got = language_of(answer)
    if got == "neutral":
        return []
    if got != wanted:
        return [f"answer {got}, want {wanted}"]
    return []
