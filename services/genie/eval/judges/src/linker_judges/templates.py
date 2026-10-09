"""Questions and the five answer classes, in English and German.

Every answer is built from the reference's own value (correct, paraphrase), from a value
the table never prints (numeric tamper), from another model's value in the same row
(wrong model), or from the correct sentence plus a statement outside Genie's remit
(out of scope answered). Styles rotate so that wording, length and unit choice vary
independently of correctness (the style-adversarial part of the set).
"""

from __future__ import annotations

from dataclasses import dataclass

from .numbers import Quantity, rewrite, show


@dataclass(frozen=True)
class Field:
    en: str
    de_article: str
    de: str


FIELDS = {
    "max_pv_power": Field(
        "maximum PV array power", "die", "maximale PV-Generatorleistung"
    ),
    "max_apparent_power": Field(
        "maximum apparent power", "die", "maximale Scheinleistung"
    ),
    "rated_output_current": Field("rated output current", "der", "Ausgangs-Nennstrom"),
    "max_ac_input_current": Field(
        "maximum AC input current", "der", "maximale AC-Eingangsstrom"
    ),
    "max_output_current": Field(
        "maximum on-grid output current", "der", "maximale netzseitige Ausgangsstrom"
    ),
    "usable_energy": Field("usable energy", "die", "nutzbare Energie"),
    "nominal_energy": Field("nominal energy", "die", "Nennenergie"),
    "weight": Field("weight", "das", "Gewicht"),
    "nominal_voltage": Field("nominal voltage", "die", "Nennspannung"),
    "max_pv_input_power": Field(
        "maximum PV input power", "die", "maximale PV-Eingangsleistung"
    ),
    "max_charge_current": Field(
        "maximum continuous charging current", "der", "maximale Dauerladestrom"
    ),
    "max_charge_discharge_power": Field(
        "maximum charging/discharging power", "die", "maximale Lade-/Entladeleistung"
    ),
    "pack_count": Field("number of battery packs", "die", "Anzahl der Batteriepacks"),
    "ac_power": Field("AC power", "die", "AC-Leistung"),
    "max_pv_input": Field("maximum PV input", "die", "maximale PV-Eingangsleistung"),
}

# German genitive of the product noun: "die Nennspannung des Batteriesystems B2-20.0-HV1".
CATEGORY_GENITIVE = {
    "inverter": "Wechselrichters",
    "system": "Speichersystems",
    "battery": "Batteriesystems",
    "module": "Batteriemoduls",
}

# Statements outside the remit (AGENTS.md §2: stock is only ever "in stock"; no
# Incoterms; company, service and logistics questions go to the team).
OUT_OF_REMIT = {
    "en": (
        "We have 40 units in stock, ready to ship.",
        "We can deliver it within 3 working days.",
        "We ship it DAP to your site.",
        "Our technicians can also install it for you.",
        "If you order today, it will arrive by Friday.",
    ),
    "de": (
        "Wir haben 40 Stück auf Lager, sofort versandbereit.",
        "Wir können innerhalb von 3 Werktagen liefern.",
        "Wir liefern DAP an Ihre Baustelle.",
        "Unsere Techniker können die Installation gleich mit übernehmen.",
        "Wenn Sie heute bestellen, ist die Ware bis Freitag bei Ihnen.",
    ),
}


def question(field: str, category: str, model: str, lang: str) -> str:
    spec = FIELDS[field]
    if lang == "en":
        if field == "pack_count":
            return f"How many battery packs does the {model} have?"
        return f"What is the {spec.en} of the {model}?"
    if field == "pack_count":
        return f"Aus wie vielen Batteriepacks besteht das {model}?"
    return f"Wie hoch ist {spec.de_article} {spec.de} des {CATEGORY_GENITIVE[category]} {model}?"


def statement(field: str, category: str, model: str, value: str, lang: str) -> str:
    """The plain answer sentence carrying `value` (already formatted)."""
    spec = FIELDS[field]
    if lang == "en":
        if field == "pack_count":
            return f"The {model} has {value} battery packs."
        return f"The {spec.en} of the {model} is {value}."
    if field == "pack_count":
        return f"Das {model} besteht aus {value} Batteriepacks."
    article = spec.de_article.capitalize()
    return f"{article} {spec.de} des {CATEGORY_GENITIVE[category]} {model} beträgt {value}."


def paraphrase(
    style: int,
    field: str,
    category: str,
    model: str,
    quantity: Quantity,
    lang: str,
    page: int | None,
) -> str:
    """A correct answer in one of four styles: other unit, terse, chatty, citing."""
    spec = FIELDS[field]
    source_en = f"the datasheet (page {page})" if page else "the product data"
    source_de = f"Datenblatt (Seite {page})" if page else "Produktdaten"
    if style == 0:
        value = rewrite(quantity, lang)
        if lang == "en":
            if field == "pack_count":
                return f"It is built from {value} battery packs."
            return f"For the {model}, the {spec.en} comes to {value}."
        if field == "pack_count":
            return f"Es ist aus {value} Batteriepacks aufgebaut."
        return f"Beim Modell {model} liegt {spec.de_article} {spec.de} bei {value}."
    if style == 1:
        return show(quantity, lang, thousands=True) + "."
    sentence = statement(field, category, model, show(quantity, lang), lang)
    if style == 2:
        return styled(sentence, lang, verbose=True)
    if lang == "en":
        return f"According to {source_en}, {sentence[0].lower()}{sentence[1:]}"
    return f"Laut {source_de}: {sentence}"


def styled(sentence: str, lang: str, verbose: bool) -> str:
    """An error answer, plain or wrapped in the same friendly frame as style 2."""
    if not verbose:
        return sentence
    if lang == "en":
        return (
            "Thanks for asking! I checked the specifications for you: "
            + sentence
            + " Let me know if you need any other values."
        )
    return (
        "Danke für Ihre Frage! Ich habe die technischen Daten für Sie geprüft: "
        + sentence
        + " Sagen Sie gern Bescheid, wenn Sie weitere Werte brauchen."
    )
