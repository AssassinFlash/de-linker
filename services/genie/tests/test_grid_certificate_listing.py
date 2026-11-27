from typing import Any

import pytest

from linker_genie.app import _check_shipped_publication
from linker_genie.cycle import run
from linker_genie.facts import TurnFacts, collect
from linker_genie.publication import PublicationChanged, Snapshot
from linker_genie.route import NamedModel, Route
from linker_genie.schema import Locale, TurnMessage, TurnRequest
from linker_genie.template import prepared_answer


def source(model: str, lang: Locale) -> tuple[dict[str, Any], Route, int]:
    owner = 8978 if model == "GW100K-HT" else 8980
    pid = owner if lang == "en" else owner + 1
    docs = [
        {
            "document_id": name,
            "document_revision": "r1",
            "url": f"https://de-linker.test/{name}.pdf",
            "title": title,
            "title_de": {
                "DNV": "GoodWe HT – NC RfG für Polen, PTPiREE und PSE",
                "SGS": "GoodWe HT – VDE-AR-N 4110 für Deutschland, SGS 2621/0136-CER",
            }.get(name, ""),
            "type": "certificate",
            "product_ids": [8978, 8980],
        }
        for name, title in [
            ("EN50549", "GoodWe HT EN 50549-1 Certificate"),
            ("DNV", "GoodWe HT Certificate for Poland — NC RfG, PTPiREE / PSE"),
            (
                "SGS",
                "GoodWe HT Unit Certificate for Germany — VDE-AR-N 4110, SGS 2621/0136-CER",
            ),
        ]
    ]
    return (
        {"product_id": pid, "model": model, "brand": "GoodWe", "documents": docs},
        Route("documents", named_models=(NamedModel(model, (pid,)),)),
        owner,
    )


def receipt(row: dict[str, Any], owner: int, lang: Locale) -> TurnFacts:
    facts = collect("linker/get-product", row, lang, evidence_owner=owner)
    facts.tool_calls.append(
        {
            "name": "linker/get-product",
            "arguments": {"product_id": row["product_id"]},
            "ok": True,
            "result": row,
        }
    )
    return facts


@pytest.mark.parametrize("model", ["GW100K-HT", "GW120K-HT"])
@pytest.mark.parametrize("lang", ["en", "de"])
def test_grid_document_list_for_model_and_countries(model: str, lang: Locale) -> None:
    row, route, owner = source(model, lang)
    facts = receipt(row, owner, lang)
    question = (
        f"Which German and Polish grid connection certificates are available for the GoodWe {model}?"
        if lang == "en"
        else f"Welche deutschen und polnischen Netzanschlussnachweise liegen für den GoodWe {model} vor?"
    )
    draft = prepared_answer(facts, route, lang, question=question)
    assert draft is not None
    request = TurnRequest(
        conversation_id="grid",
        locale=lang,
        messages=[TurnMessage(role="user", content=question)],
    )
    result = run(request, lambda *_: (draft, TurnFacts()), route, facts)
    assert result.grounded and not result.fallback, result.failures
    shipped = result.output.model_dump()
    lines = [b["text"] for b in shipped["blocks"] if b["type"] == "text"]
    assert "VDE-AR-N 4110" in lines[0] and "2621/0136-CER" in lines[0]
    assert "NC RfG" in lines[1] and "PTPiREE" in lines[1] and "PSE" in lines[1]
    assert row["documents"][2]["title_de" if lang == "de" else "title"] in lines[0]
    assert row["documents"][1]["title_de" if lang == "de" else "title"] in lines[1]
    permit = Snapshot(
        "s", {owner: {}}, {d["document_id"]: d for d in row["documents"]}, "r"
    )
    _check_shipped_publication(shipped, result.facts, permit)
    docs = [b for b in shipped["blocks"] if b["type"] == "document"]
    assert [(d["document_id"], d["evidence_product_id"]) for d in docs] == [
        ("SGS", owner),
        ("DNV", owner),
    ]
    assert all(d["url"].endswith("#page=1") for d in docs)
    permit.documents["SGS"]["product_ids"] = []
    with pytest.raises(PublicationChanged, match="association changed"):
        _check_shipped_publication(shipped, result.facts, permit)


def test_requested_country_and_withdrawn_or_replaced_originals() -> None:
    model = "GW100K-HT"
    row, route, owner = source(model, "en")
    question = f"Which grid certificate is available in Poland for {model}?"
    facts = receipt(row, owner, "en")
    draft = prepared_answer(facts, route, "en", question=question)
    assert draft and len(draft.blocks) == 2
    assert (
        prepared_answer(
            facts, route, "en", question=question + " What firmware is required?"
        )
        is None
    )
    polish = row["documents"][1]
    polish["product_ids"] = [8980]
    assert (
        prepared_answer(receipt(row, owner, "en"), route, "en", question=question)
        is None
    )
    polish.update(
        product_ids=[owner], document_revision="r2", title="Neue Prüfung für Polen"
    )
    facts = receipt(row, owner, "en")
    draft = prepared_answer(facts, route, "en", question=question)
    assert draft is not None
    assert facts.facts[f"p{owner}.document.1.title"].value == "Neue Prüfung für Polen"
    evidence = facts.documents[f"p{owner}.document.1"].evidence
    assert evidence is not None and evidence.document_revision == "r2"
    polish.update(title="New equipment certificate")
    assert (
        prepared_answer(receipt(row, owner, "en"), route, "en", question=question)
        is None
    )


def test_german_language_in_eu_declaration_title_is_not_a_grid_jurisdiction() -> None:
    model = "H2-25K-T3"
    row, route, owner = source(model, "en")
    row.update(brand="SAJ", documents=[row["documents"][0]])
    row["documents"][0]["title"] = (
        "EU declaration of conformity for the SAJ H2 inverters, "
        "13 languages including English and German (names the H2-25K-T3)"
    )
    question = f"Which German grid certificates are available for the SAJ {model}?"
    assert (
        prepared_answer(receipt(row, owner, "en"), route, "en", question=question)
        is None
    )
