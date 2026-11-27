"""Standalone product measurements with their published Woo datasheet page."""

from __future__ import annotations

import re

from linker_genie.facts import Fact, TurnFacts
from linker_genie.route import Route
from linker_genie.schema import DocumentBlock, Locale, TextBlock, TurnOutput
from linker_genie.source_models import model_pattern

# Words outside the model, manufacturer and measurement may identify the
# document or frame the question. An additional criterion needs its own answer.
_FRAME = frozenset(
    "what is the of does have according to its datasheet for battery cabinet inverter "
    "in how many which are a an please state list der die das dem den des ein eines von "
    "für wie viel viele welche welchen ist hat beträgt gibt an nennt laut datenblatt "
    "batterieschrank batterie wechselrichter".split()
)
_PARAMETERS = (
    (
        r"usable (?:energy|capacity)|nutzbare (?:energie|kapazität)",
        "system_usable_energy_kwh",
        "The usable energy of the {model} is {value}.",
        "Die nutzbare Energie des {model} beträgt {value}.",
    ),
    (
        r"(?:how many |number of |wie viele |anzahl (?:der )?)(?:independent |unabhängige[nr]? )?(?:mppt trackers?|mpp[- ]trackers?|mppts?)",
        "n_mppt",
        "The {model} has {value} MPPTs.",
        "Der {model} hat {value} MPP-Tracker.",
    ),
    (
        r"mppt operating voltage range(?: in volts?)?|mppt-betriebsspannungsbereich(?: in volt)?",
        "mppt_voltage_range_v",
        "The MPPT operating voltage range of the {model} is {value}.",
        "Der MPPT-Betriebsspannungsbereich des {model} beträgt {value}.",
    ),
)


def datasheet_parameter_answer(
    facts: TurnFacts, route: Route, question: str, language: Locale
) -> TurnOutput | None:
    if route.show_products or len(route.named_models) != 1:
        return None
    model = route.named_models[0]
    if model.is_conflict or not model.searched_known or len(model.product_ids) != 1:
        return None
    model_match = model_pattern(model.code)
    if not model_match.search(question):
        return None
    pid = model.product_ids[0]
    product = next(
        (
            call["result"]
            for call in facts.tool_calls
            if call["name"] == "linker/get-product"
            and call["result"].get("product_id") == pid
        ),
        None,
    )
    if not product:
        return None
    text = model_match.sub(" ", question).casefold()
    brand = product.get("brand")
    if brand:
        text = re.sub(rf"\b{re.escape(brand.casefold())}\b", " ", text)
    for metric, field, en, de in _PARAMETERS:
        rest, count = re.subn(rf"\b(?:{metric})\b", " ", text)
        if field == "system_usable_energy_kwh":
            rest = re.sub(r"\bin kwh\b", " ", rest)
        if count != 1 or not set(re.findall(r"\w+", rest)) <= _FRAME:
            continue
        key = f"p{pid}.{field}"
        figure = facts.facts.get(key)
        ref = f"{key}.source"
        doc = facts.documents.get(ref)
        if (
            not figure
            or figure.source != "datasheet-figures"
            or not doc
            or not doc.evidence
        ):
            return None
        if not any(
            row.get("type") == "datasheet" and row.get("url") == doc.url
            for row in product.get("documents", [])
        ):
            return None
        answer = (de if language == "de" else en).format(
            model=model.code, value=f"{{fact:{key}}}"
        )
        if figure.qualifier:
            condition = figure.qualifier.get(language)
            if not isinstance(condition, str) or not condition:
                return None
            condition_id = f"{key}.condition"
            facts.add(Fact(id=condition_id, value=condition, source=figure.source))
            facts.supporting_documents[condition_id] = (ref,)
            answer += f"\n\n{{fact:{condition_id}}}"
        return TurnOutput(
            language=language,
            blocks=[TextBlock(text=answer, refs=[str(pid)]), DocumentBlock(ref=ref)],
        )
    return None
