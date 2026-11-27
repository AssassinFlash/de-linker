"""Genie reads a named inverter's sourced backup requirements in the customer's language."""

from typing import Any

import httpx
import pytest

from linker_genie.abilities import AbilityClient
from linker_genie.app import _check_shipped_publication
from linker_genie.cycle import run
from linker_genie.facts import TurnFacts, collect, merge
from linker_genie.jev import Intent, Reading
from linker_genie.lexicon import Category, Match, Product, build
from linker_genie.publication import PublicationChanged, Snapshot
from linker_genie.route import Call, Route, Subject, plan
from linker_genie.schema import (
    CardsBlock,
    DocumentBlock,
    Locale,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import prepared_answer
from linker_genie.understand import Understander

PID, ACCESSORY = 1945, 90
MODEL = "GW50K-ET-10"
QUESTIONS: dict[Locale, str] = {
    "en": "Which GoodWe transfer switch and software version does the GW50K-ET-10 need for backup operation?",
    "de": "Welchen GoodWe-Umschalter und welche Softwareversion benötigt der GW50K-ET-10 für Ersatzstrom?",
}
CONDITIONS = {
    "en": "Single-inverter backup requires a separate STS200-80-10 with cabinet software 4.400 or later.",
    "de": "Für den Ersatzstrombetrieb eines einzelnen Wechselrichters ist ein separater STS200-80-10 mit Schranksoftware ab Version 4.400 erforderlich.",
}
URL = "https://site.test/wp-content/uploads/cabinet.pdf"


def route_for(lang: Locale, message: str) -> Route:
    reading = Reading(
        "pairing_compatibility", 0.99 if lang == "en" else 0.77, 0.1, 0, 0, 1, 0
    )
    return plan(
        message,
        [
            Match("model", MODEL, MODEL, frozenset({PID}), "GW50K ET 10"),
            Match("brand", "GoodWe", "goodwe", frozenset({PID}), "GoodWe"),
        ],
        reading,
        Subject((PID,), {PID: "inverters"}, {PID: MODEL}),
        lang,
    )


def product() -> dict[str, Any]:
    return {
        "product_id": PID,
        "model": MODEL,
        "requirements": [
            {
                "inverter_product_id": PID,
                "kind": "backup",
                "applicability": {
                    "operating_mode": "backup",
                    "topology": "single_converter",
                },
                "conditions": [CONDITIONS],
                "documents": [
                    {
                        "product_id": ACCESSORY,
                        "document_id": "cabinet",
                        "document_revision": "v1",
                        "page": 31,
                        "url": URL,
                        "title": "STS200-80-10 manual",
                    }
                ],
            }
        ],
    }


def answer(lang: Locale, payload: dict[str, Any]) -> tuple[dict[str, Any], TurnFacts]:
    question = QUESTIONS[lang]
    route = route_for(lang, question)
    args = {"product_id": PID, "lang": lang, "requirement_kind": "backup"}
    assert route.name == "requirements"
    assert route.calls == (Call("linker/get-product", args),)
    facts = collect("linker/get-product", payload, lang)
    facts.tool_calls.append(
        {"name": "linker/get-product", "arguments": args, "ok": True, "result": payload}
    )
    draft = prepared_answer(facts, route, lang, question=question)
    assert draft is not None
    request = TurnRequest(
        conversation_id="backup",
        messages=[TurnMessage(role="user", content=question)],
        locale=lang,
    )
    result = run(request, lambda *_: (draft, TurnFacts()), route, facts)
    assert result.grounded and not result.fallback
    assert isinstance(result.output.blocks[0], TextBlock)
    return result.output.model_dump(), result.facts


@pytest.mark.parametrize("lang", ["en", "de"])
def test_manufacturer_condition_and_accessory_document_keep_their_owners(
    lang: Locale,
) -> None:
    shipped, facts = answer(lang, product())
    text, document = shipped["blocks"]
    assert MODEL in text["text"] and CONDITIONS[lang] in text["text"]
    assert document["url"] == URL + "#page=31"
    permit = Snapshot(
        "s",
        {PID: {}, ACCESSORY: {}},
        {
            "cabinet": {
                "document_revision": "v1",
                "product_ids": [ACCESSORY],
                "url": URL,
            }
        },
        "r",
    )
    _check_shipped_publication(shipped, facts, permit)
    assert document["evidence_product_id"] == ACCESSORY
    permit.documents["cabinet"]["product_ids"] = [PID]
    with pytest.raises(PublicationChanged, match="association changed"):
        _check_shipped_publication(shipped, facts, permit)


@pytest.mark.parametrize("missing", ["requirement", "revision", "owner"])
def test_backup_equipment_stays_unconfirmed_without_its_evidence(missing: str) -> None:
    payload = product()
    if missing == "requirement":
        payload["requirements"] = []
    elif missing == "revision":
        del payload["requirements"][0]["documents"][0]["document_revision"]
    else:
        payload["requirements"][0]["inverter_product_id"] = ACCESSORY
    category = Category(1, "Inverters", "inverters", 0)
    vocabulary = build(
        [
            Product(
                PID,
                MODEL,
                "et",
                (("GoodWe", "goodwe"),),
                (),
                (MODEL,),
                ((category.name, category.slug),),
            )
        ],
        [category],
    )
    payload["faq"] = [
        {
            "question": "Which backup switch?",
            "answer": "See the backup equipment manual.",
        }
    ]
    client = AbilityClient(
        "http://site.test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"result": payload})
        ),
    )
    request = TurnRequest(
        conversation_id="backup",
        messages=[TurnMessage(role="user", content=QUESTIONS["en"])],
        locale="en",
    )
    prepared = Understander(
        lambda: vocabulary, None, search=lambda _: {"hits": []}
    ).prepare(request, client)
    assert prepared.route.name == "documents"
    assert prepared.results[0]["result"]["faq"] == payload["faq"]
    assert [call["name"] for call in prepared.facts.tool_calls] == [
        "linker/get-product",
        "linker/search-knowledge",
    ]
    assert prepared.results[1]["arguments"]["product_ids"] == [PID]
    assert not any(
        f.source == "product-requirement" for f in prepared.facts.facts.values()
    )
    assert (
        prepared_answer(prepared.facts, prepared.route, "en", question=QUESTIONS["en"])
        is None
    )


def test_other_specs_in_a_backup_question_still_read_the_manual() -> None:
    route = route_for("en", QUESTIONS["en"] + " What is the MPPT operating range?")
    assert route.name == "documents"
    assert {c.ability for c in route.calls} == {
        "linker/get-product",
        "linker/search-knowledge",
    }
    assert (
        next(c for c in route.calls if c.ability == "linker/get-product").arguments[
            "requirement_kind"
        ]
        == "backup"
    )


def test_battery_partners_and_backup_use_their_own_lookups() -> None:
    route = route_for(
        "en",
        "Which batteries work with the GoodWe GW50K-ET-10, and which transfer switch do I need for backup?",
    )
    assert route.name == "pairing"
    pair, requirement = route.calls
    assert pair.ability == "linker/search-products" and pair.arguments["with_pairings"]
    assert requirement.arguments == {
        "product_id": PID,
        "lang": "en",
        "requirement_kind": "backup",
    }
    assert not route.catalog_only


def test_backup_and_sizing_preserve_the_configurator_and_project_size() -> None:
    route = route_for(
        "en", QUESTIONS["en"] + " How should I size the system for 40 kWp?"
    )
    assert route.name == "sizing" and route.action == "open_configurator"
    sizing, requirement = route.calls
    assert sizing.ability == "linker/size-hint" and sizing.arguments["pv_kwp"] == 40
    assert requirement.arguments == {
        "product_id": PID,
        "lang": "en",
        "requirement_kind": "backup",
    }


@pytest.mark.parametrize("description", [" transfer switch", ""])
def test_a_transfer_switch_is_the_subject_of_its_product_faq_and_manual(
    description: str,
) -> None:
    model = "GW125K-STS-G10"
    message = f"Which inverters are compatible with the GoodWe {model}{description}?"
    route = plan(
        message,
        [Match("model", model, model, frozenset({2403}), "GW125K STS G10")],
        Reading("pairing_compatibility", 0.99, 0.1, 0, 0, 1, 0),
        Subject((2403,), {2403: "accessories"}, {2403: model}),
        "en",
    )
    assert route.name == "documents"
    assert Call("linker/get-product", {"product_id": 2403, "lang": "en"}) in route.calls
    assert (
        Call(
            "linker/search-knowledge",
            {"query": message, "lang": "en", "product_ids": [2403]},
        )
        in route.calls
    )


BATTERY = 1949
BATTERY_MODEL = "LX C101-10"
PAIR_QUESTIONS: dict[Locale, str] = {
    "en": "Is the LX C101-10 battery compatible with the GW50K-ET-10, and which transfer switch do I need for backup?",
    "de": "Ist der LX C101-10 mit dem GW50K-ET-10 kompatibel, und welchen Umschalter brauche ich für den Ersatzstrom?",
}


def exact_route(
    lang: Locale,
    message: str,
    models: dict[int, str],
    devices: dict[int, str],
    intent: Intent = "pairing_compatibility",
) -> Route:
    return plan(
        message,
        [
            Match("model", model, model, frozenset({pid}), model)
            for pid, model in models.items()
        ],
        Reading(intent, 0.99, 0.1, 0, 0, 1, 0),
        Subject(tuple(models), devices, models, catalog_models=tuple(models.values())),
        lang,
    )


@pytest.mark.parametrize(
    ("lang", "question"),
    [
        ("en", PAIR_QUESTIONS["en"]),
        ("de", PAIR_QUESTIONS["de"]),
        ("en", PAIR_QUESTIONS["en"].removesuffix("?") + ", please?"),
        ("de", PAIR_QUESTIONS["de"].removesuffix("?") + ", bitte?"),
        (
            "en",
            "Is the LX C101-10 battery compatible with the GW50K-ET-10, and which transfer switch and BMS firmware do I need for backup?",
        ),
        (
            "de",
            "Ist der LX C101-10 mit dem GW50K-ET-10 kompatibel, und welchen STS und welche BMS-Firmware brauche ich für den Ersatzstrom?",
        ),
    ],
)
@pytest.mark.parametrize("omit_backup", [False, True], ids=["normal", "fallback"])
def test_named_battery_and_inverter_keep_pair_and_backup_conditions_and_pages(
    lang: Locale, question: str, omit_backup: bool
) -> None:
    route = exact_route(
        lang,
        question,
        {BATTERY: BATTERY_MODEL, PID: MODEL},
        {PID: "inverters", BATTERY: "battery-systems"},
    )
    pair_call = Call("linker/check-compatibility", {"product_ids": [BATTERY, PID]})
    requirement_call = Call(
        "linker/get-product",
        {"product_id": PID, "lang": lang, "requirement_kind": "backup"},
    )
    assert route.name == "pairing" and route.calls == (pair_call, requirement_call)
    bms = {
        "en": "The battery requires BMS version 25600 or later.",
        "de": "Die Batterie benötigt die BMS-Version 25600 oder höher.",
    }
    pair_url = "https://site.test/battery-compatibility.pdf"
    pair = {
        "verdict": "released",
        "conditions": [bms],
        "documents": [
            {
                "url": pair_url,
                "page": 6,
                "document_id": "pairing",
                "document_revision": "v1",
                "product_id": BATTERY,
            }
        ],
    }
    parts = []
    for call, payload in [(pair_call, pair), (requirement_call, product())]:
        facts = collect(call.ability, payload, lang)
        facts.tool_calls.append(
            {
                "name": call.ability,
                "arguments": call.arguments,
                "ok": True,
                "result": payload,
            }
        )
        parts.append(facts)
    facts = merge(parts)
    facts.product_ids.update([PID, BATTERY])
    text = "{fact:compat.condition.0}"
    if not omit_backup:
        text += f"\n\n{{fact:p{PID}.requirement.backup.0}}"
    draft = TurnOutput(
        language=lang,
        blocks=[
            TextBlock(text=text, refs=[str(PID), str(BATTERY)]),
            DocumentBlock(ref="compat.document.0"),
            CardsBlock(product_ids=[BATTERY, PID]),
        ],
    )
    request = TurnRequest(
        conversation_id="pair-backup",
        locale=lang,
        messages=[TurnMessage(role="user", content=question)],
    )
    result = run(request, lambda *_: (draft, TurnFacts()), route, facts)
    assert result.fallback == omit_backup
    prose = "\n".join(
        block.text for block in result.output.blocks if isinstance(block, TextBlock)
    )
    assert bms[lang] in prose and CONDITIONS[lang] in prose
    shipped = result.output.model_dump()
    permission = Snapshot(
        "s",
        {PID: {}, BATTERY: {}, ACCESSORY: {}},
        {
            "pairing": {
                "document_revision": "v1",
                "product_ids": [BATTERY],
                "url": pair_url,
            },
            "cabinet": {
                "document_revision": "v1",
                "product_ids": [ACCESSORY],
                "url": URL,
            },
        },
        "r",
    )
    _check_shipped_publication(shipped, result.facts, permission)
    assert {
        (block["url"], block["evidence_product_id"])
        for block in shipped["blocks"]
        if block["type"] == "document"
    } == {(pair_url + "#page=6", BATTERY), (URL + "#page=31", ACCESSORY)}


@pytest.mark.parametrize("extra", ["GW120K-HT", "GW999K-ET", "XYZ-123-456"])
@pytest.mark.parametrize("lang", ["en", "de"])
def test_backup_for_a_named_pair_needs_an_unambiguous_inverter(
    extra: str, lang: Locale
) -> None:
    models = {BATTERY: BATTERY_MODEL, PID: MODEL}
    devices = {PID: "inverters", BATTERY: "battery-systems"}
    if extra == "GW120K-HT":
        models[8980] = extra
        devices[8980] = "inverters"
    conjunction = "oder" if lang == "de" else "or"
    question = PAIR_QUESTIONS[lang].replace(MODEL, f"{MODEL} {conjunction} {extra}")
    route = exact_route(lang, question, models, devices)
    assert route.name == "clarify" and not route.calls
    assert all(code in route.answer for code in (MODEL, BATTERY_MODEL, extra))
    assert (
        "welchen Wechselrichter und welche Batterie"
        if lang == "de"
        else "Which inverter and battery"
    ) in route.answer


@pytest.mark.parametrize(
    ("lang", "extra"),
    [
        ("en", "Please also give the MPPT operating voltage range from the datasheet."),
        (
            "de",
            "Bitte nennen Sie auch den MPPT-Betriebsspannungsbereich aus dem Datenblatt.",
        ),
    ],
)
def test_a_third_document_question_keeps_both_products_and_the_inverter_requirement(
    lang: Locale, extra: str
) -> None:
    question = PAIR_QUESTIONS[lang] + " " + extra
    route = exact_route(
        lang,
        question,
        {BATTERY: BATTERY_MODEL, PID: MODEL},
        {PID: "inverters", BATTERY: "battery-systems"},
    )
    assert route.name == "documents"
    assert {call.ability for call in route.calls} == {
        "linker/check-compatibility",
        "linker/get-product",
        "linker/search-knowledge",
    }
    assert (
        Call(
            "linker/get-product",
            {"product_id": PID, "lang": lang, "requirement_kind": "backup"},
        )
        in route.calls
    )
    assert (
        Call("linker/get-product", {"product_id": BATTERY, "lang": lang}) in route.calls
    )


@pytest.mark.parametrize(
    ("message", "intent", "route_name", "tools"),
    [
        (
            "For the LX C101-10 and GW50K-ET-10, which transfer switch and BMS firmware do I need for backup?",
            "documents_specs",
            "pairing",
            {"linker/check-compatibility", "linker/get-product"},
        ),
        (
            "For the LX C101-10 and GW50K-ET-10, which transfer switch do I need for backup? How should I size the system for 40 kWp?",
            "sizing",
            "sizing",
            {"linker/size-hint", "linker/check-compatibility", "linker/get-product"},
        ),
        (
            "Compare the LX C101-10 and GW50K-ET-10, and give their backup equipment requirements.",
            "compare",
            "compare",
            {
                "linker/compare-products",
                "linker/check-compatibility",
                "linker/get-product",
            },
        ),
    ],
)
def test_two_named_devices_keep_backup_evidence_across_intents(
    message: str, intent: Intent, route_name: str, tools: set[str]
) -> None:
    route = exact_route(
        "en",
        message,
        {BATTERY: BATTERY_MODEL, PID: MODEL},
        {PID: "inverters", BATTERY: "battery-systems"},
        intent,
    )
    assert route.name == route_name and {call.ability for call in route.calls} == tools
    assert (
        Call(
            "linker/get-product",
            {"product_id": PID, "lang": "en", "requirement_kind": "backup"},
        )
        in route.calls
    )
