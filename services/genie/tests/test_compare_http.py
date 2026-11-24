"""Technical comparison and fallback product scope through the turn endpoint."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from conftest import SHELL
from fastapi.testclient import TestClient
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from test_turn_abilities import SEARCH, clients, manifest

import linker_genie.app as service
from linker_genie.abilities import Abilities
from linker_genie.agent import make_generate
from linker_genie.facts import TurnFacts, collect, merge
from linker_genie.jev import Reading
from linker_genie.lexicon import Entry, Vocabulary, normalize
from linker_genie.log import TurnLog
from linker_genie.schema import TextBlock, TurnOutput, TurnRequest
from linker_genie.understand import Understander, nothing

SAJ = 1179
GOODWE = 6321
BATTERY = 2067
MODELS = {SAJ: "H2-25K-T3", GOODWE: "GW125/261-ESA-LCN-G10", BATTERY: "B2-10.0-HV1"}
PAIR = {"device_class": "inverters", "text": MODELS[SAJ], "with_pairings": True}


@pytest.mark.parametrize(
    "scenario",
    [
        "compare",
        "indexed-current",
        "pairing",
        "pairing-flag",
        "foreign-product",
        "foreign-knowledge",
    ],
)
def test_turn_keeps_model_scope_with_or_without_jev(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    indexed = scenario == "indexed-current"
    compare = scenario in {"compare", "indexed-current"}
    other = 2003 if indexed else GOODWE
    models = {**MODELS, 2003: "L260-OMNI"}
    pairing = scenario == "pairing"
    raw = manifest(SAJ)
    for pid in (other, BATTERY):
        product = manifest(pid)
        raw["products"].extend(product["products"])
        raw["documents"].extend(product["documents"])
    vocabulary = Vocabulary()
    for pid, model in models.items():
        vocabulary.add(normalize(model), Entry("model", model, model, frozenset({pid})))
    question = "What is the maximum charge current per input for the H2-25K-T3?"
    if compare:
        question = (
            "Compare the SAJ H2-25K-T3 and GoodWe GW125/261-ESA-LCN-G10. "
            "What is the SAJ's maximum charge current per input?"
        )
    if indexed:
        question = (
            "Compare the SAJ H2-25K-T3 and L260-OMNI. "
            "What are their maximum battery and AC currents?"
        )
    if pairing:
        question = "Which battery is compatible with the H2-25K-T3?"
    jev = (
        SimpleNamespace(
            read=lambda *_: Reading("compare", 0.6 if indexed else 0.99, 0, 0, 0, 0, 0)
        )
        if compare
        else None
    )

    def woo(request: httpx.Request) -> dict[str, Any]:
        path = request.url.path
        if path.endswith("/compare-products/run"):
            assert compare
            assert {
                int(value)
                for key, value in request.url.params.multi_items()
                if key.startswith("input[product_ids][")
            } == {SAJ, other}
            # Native compare-products returns selection facts and rows, not cited figures.
            powers = {SAJ: 25, other: 125}
            return {
                "products": [
                    {
                        "product_id": pid,
                        "title": models[pid],
                        "url": f"https://wp.test/p/{pid}",
                        "facts": {"ac_power_kw": kw},
                    }
                    for pid, kw in powers.items()
                ],
                "rows": [
                    {
                        "field": "ac_power_kw",
                        "label": "Rated AC power",
                        "values": powers,
                    }
                ],
            }
        if path == SEARCH:
            assert not compare
            row: dict[str, Any] = {"product_id": SAJ, "title": MODELS[SAJ]}
            if request.url.params.get("input[with_pairings]") == "true":
                row["pairings"] = [
                    {
                        "product_id": BATTERY,
                        "verdict": "released_with_accessory",
                        "conditions": [
                            f"Use the {MODELS[BATTERY]} battery with its control module."
                        ],
                        "documents": [
                            {
                                "document_id": f"doc-{SAJ}",
                                "document_revision": f"revision-{SAJ}",
                                "product_id": SAJ,
                                "url": f"https://wp.test/{SAJ}.pdf",
                                "page": 3,
                            }
                        ],
                    }
                ]
            return {"qualified": [row]}
        assert path.endswith("/get-product/run")
        pid = int(request.url.params["input[product_id]"])
        product = {"product_id": pid, "title": models[pid]}
        if pid == SAJ:
            product["figures"] = {
                "max_battery_charge_a": {
                    "value": "50",
                    "unit": "A",
                    "citation": {"url": f"https://wp.test/{pid}.pdf", "page": 38},
                    "qualifier": {
                        "quantity_kind": "maximum",
                        "scope": "per_battery_port",
                        "direction": "charge",
                    },
                }
            }
        if indexed:
            document = next(
                doc for doc in raw["documents"] if pid in doc["product_ids"]
            )
            product["documents"] = [document]
            if pid == SAJ:
                seeds = json.loads(
                    (
                        Path(__file__).resolve().parents[3]
                        / "tools/migrate/1132-h2-port-current.json"
                    ).read_text()
                )["products"][str(SAJ)]["figures"]
                product["figures"] = {
                    f"max_battery_{direction}_a": {
                        **seeds[f"max_battery_{direction}_a"]["expect"],
                        "qualifier": seeds[f"max_battery_{direction}_a"]["set"][
                            "qualifier"
                        ],
                        "citation": {"url": document["url"], "page": 38},
                    }
                    for direction in ("charge", "discharge")
                }
        return product

    searched: list[set[int]] = []

    def search(arguments: dict[str, Any] | None) -> dict[str, Any]:
        assert arguments is not None
        searched.append(set(arguments["product_ids"]))
        hits = []
        if indexed:
            for pid, chunk, value, page, text in (
                (
                    SAJ,
                    "saj-current",
                    "50 A",
                    38,
                    "| Max. Lade-/Entladestrom [A] | [n1=50 A]/[n2=50 A] |",
                ),
                (other, "l260-ac", "181 A", 2, "| Max AC Current (A) | [n1=181 A] |"),
            ):
                if pid not in arguments["product_ids"]:
                    continue
                document = next(
                    doc for doc in raw["documents"] if pid in doc["product_ids"]
                )
                hits.append(
                    {
                        "chunk_id": chunk,
                        "doc_url": document["url"],
                        "document_id": document["document_id"],
                        "document_revision": document["document_revision"],
                        "evidence_product_id": pid,
                        "doc_type": "datasheet",
                        "product_ids": [pid],
                        "page": page,
                        "text": text,
                        "figures": {
                            f"{chunk}.n1": value,
                            **({f"{chunk}.n2": value} if pid == SAJ else {}),
                        },
                    }
                )
        return {"hits": hits, "ranking": "vector"}

    get_saj = ("linker_get_product", {"product_id": SAJ})
    knowledge = ("linker_search_knowledge", {"query": "Battery current limits"})
    pair_search = ("linker_search_products", PAIR)
    denied: dict[str, tuple[str, dict[str, Any]]] = {
        "pairing-flag": pair_search,
        "foreign-product": ("linker_get_product", {"product_id": BATTERY}),
        "foreign-knowledge": (
            "linker_search_knowledge",
            {"query": "Battery current limits", "product_ids": [BATTERY]},
        ),
    }
    calls: list[tuple[str, dict[str, Any]]]
    if indexed:
        calls = []  # The question names both models and asks for the two current ratings.
    elif compare:
        calls = [knowledge]
    elif pairing:
        calls = [pair_search]
    else:
        calls = [denied[scenario], get_saj, knowledge]

    def respond(messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        returns: list[dict[str, Any]] = []
        for message in messages:
            for part in message.parts:
                if isinstance(part, ToolReturnPart):
                    assert isinstance(part.content, dict)
                    returns.append(part.content)
        if returns and scenario in denied:
            assert "error" in returns[0]
        if len(returns) < len(calls):
            name, arguments = calls[len(returns)]
            return ModelResponse(parts=[ToolCallPart(name, {"arguments": arguments})])
        if indexed:
            corrected = any(
                "The previous answer failed grounding" in str(part.content)
                for message in messages
                for part in message.parts
                if hasattr(part, "content")
            )
            battery = (
                "{fact:p1179.max_battery_charge_a}\n{fact:p1179.max_battery_discharge_a}"
                if corrected
                else "Maximum battery charge current: {fact:saj-current.n1}\nMaximum battery discharge current: {fact:saj-current.n2}"
            )
            blocks: list[dict[str, Any]] = [
                {
                    "type": "text",
                    "text": battery
                    + "\nThe maximum AC current for L260-OMNI is {fact:l260-ac.n1}.",
                    "refs": ["saj-current", "l260-ac"],
                },
                {"type": "compare", "product_ids": [SAJ, other]},
            ]
        elif pairing:
            assert returns[0]["qualified"][0]["pairings"][0]["product_id"] == BATTERY
            blocks = [
                {
                    "type": "text",
                    "text": f"The SAJ inverter has a documented pairing with the {MODELS[BATTERY]} battery and its control module.",
                    "refs": [str(SAJ), str(BATTERY)],
                },
                {"type": "cards", "product_ids": [SAJ, BATTERY]},
                {"type": "document", "ref": f"compat.document.{BATTERY}.0"},
            ]
        else:
            if not compare:
                assert "max_battery_charge_a" in returns[1]["figures"]
            blocks = [
                {
                    "type": "text",
                    "text": "{fact:p1179.max_battery_charge_a}",
                    "refs": [str(SAJ)],
                }
            ]
            if compare:
                blocks.append({"type": "compare", "product_ids": [SAJ, GOODWE]})
        return ModelResponse(
            parts=[ToolCallPart("final_result", {"language": "en", "blocks": blocks})]
        )

    with clients(raw, woo) as (client, authority, requests):
        for attribute in ("prepare", "generate"):
            monkeypatch.delattr(service.app.state, attribute, raising=False)
        monkeypatch.setattr(service.app.state, "publication", authority, raising=False)
        monkeypatch.setattr(
            service.app.state, "commerce", lambda _ids: (TurnFacts(), []), raising=False
        )
        monkeypatch.setattr(service, "_client", client)
        log = TurnLog(tmp_path / "turns.sqlite")
        monkeypatch.setattr(service, "_log", log)
        monkeypatch.setattr(
            service, "understander", lambda: Understander(None, jev, search=search)
        )
        monkeypatch.setattr(
            service,
            "store_vocabulary",
            lambda: SimpleNamespace(get=lambda _permission: vocabulary),
        )
        monkeypatch.setattr(service, "page_reader", lambda: SimpleNamespace(read=None))

        def generate_with_model(
            tools: Abilities, **kwargs: Any
        ) -> Callable[[TurnRequest, str | None], tuple[TurnOutput, TurnFacts]]:
            generate = make_generate(
                tools, model=FunctionModel(respond), search=search, **kwargs
            )

            def run(
                body: TurnRequest, retry: str | None
            ) -> tuple[TurnOutput, TurnFacts]:
                with asyncio.Runner() as runner:
                    runner.get_loop()
                    return generate(body, retry)

            return run

        monkeypatch.setattr(service, "make_generate", generate_with_model)
        monkeypatch.setenv("LINKER_GENIE_WORK_PATH", str(tmp_path / "work.sqlite"))
        try:
            response = TestClient(service.app, headers=SHELL).post(
                "/assistant/turn",
                json={
                    "conversation_id": "technical-turn",
                    "messages": [{"role": "user", "content": question}],
                },
            )
        finally:
            log.close()

    assert response.status_code == 200, response.text
    blocks = [
        json.loads(event.split("data: ", 1)[1])
        for event in response.text.split("\n\n")
        if event.startswith("event: block\n")
    ]
    if indexed:
        texts = "\n".join(block["text"] for block in blocks if block["type"] == "text")
        assert (
            "The maximum charge current for H2-25K-T3 is 50 A per battery input."
            in texts
        )
        assert (
            "The maximum discharge current for H2-25K-T3 is 50 A per battery input."
            in texts
        )
        assert "The maximum AC current for L260-OMNI is 181 A." in texts
        assert {
            (block["url"], block["evidence_product_id"])
            for block in blocks
            if block["type"] == "document"
        } == {
            (f"https://wp.test/{SAJ}.pdf#page=38", SAJ),
            (f"https://wp.test/{other}.pdf#page=2", other),
        }
        return
    pairing_queries = [
        request
        for request in requests
        if request.url.params.get("input[with_pairings]") == "true"
    ]
    assert len(pairing_queries) == int(pairing)
    if pairing:
        assert any(
            block.get("type") == "cards" and BATTERY in block["product_ids"]
            for block in blocks
        )
        link = next(block for block in blocks if block.get("type") == "document")
        assert link["url"] == f"https://wp.test/{SAJ}.pdf#page=3"
        assert link["evidence_product_id"] == SAJ
        return
    subject = f" for {MODELS[SAJ]}" if compare else ""
    assert any(
        block.get("text")
        == f"The maximum charge current{subject} is 50 A per battery input."
        for block in blocks
    )
    assert f"https://wp.test/{SAJ}.pdf#page=38" in response.text
    assert searched == [{SAJ, GOODWE} if compare else {SAJ}]
    assert sorted(
        int(request.url.params["input[product_id]"])
        for request in requests
        if request.url.path.endswith("/get-product/run")
    ) == ([SAJ, GOODWE] if compare else [SAJ])
    comparisons = [
        block["product_ids"] for block in blocks if block["type"] == "compare"
    ]
    assert comparisons == ([[SAJ, GOODWE]] if compare else [])


@pytest.mark.parametrize(
    "scenario", ["misattributed", "independent", "warning", "warning-then-error"]
)
def test_ac_current_cannot_support_a_shared_battery_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    # The Woo publication feed captured the L260-OMNI's AC rating on page 2.
    feed_path = (
        Path(__file__).resolve().parents[2]
        / "engine/tests/fixtures/scenario-feed-2026-10-09.json"
    )
    pylon = next(
        p for p in json.loads(feed_path.read_text())["products"] if p["id"] == 2003
    )
    ac = pylon["figures"]["max_ac_current_a"]
    raw = manifest(SAJ)
    other = manifest(2003)
    other["documents"][0]["url"] = ac["citation"]["url"]
    raw["products"] += other["products"]
    raw["documents"] += other["documents"]
    facts = merge(
        [
            collect(
                "linker/get-product",
                {
                    "product_id": SAJ,
                    "title": MODELS[SAJ],
                    "documents": raw["documents"][:1],
                    "figures": {
                        "max_battery_charge_a": {
                            "value": "50",
                            "unit": "A",
                            "qualifier": {
                                "scope": "per_battery_port",
                                "direction": "charge",
                                "quantity_kind": "maximum",
                            },
                            "citation": {"url": raw["documents"][0]["url"], "page": 38},
                        }
                    },
                },
            ),
            collect(
                "linker/get-product",
                {
                    "product_id": 2003,
                    "title": pylon["model"],
                    "figures": {"max_ac_current_a": ac},
                    "documents": other["documents"],
                },
            ),
        ]
    )
    claim = {
        "misattributed": "The other inverter has a total current of {fact:p2003.max_ac_current_a} for both battery inputs.",
        "independent": "The maximum AC current for the L260-OMNI is {fact:p2003.max_ac_current_a}.",
        "warning-then-error": "Do not use a shared limit from the SAJ because the L260-OMNI supplies a total current of {fact:p2003.max_ac_current_a} for both battery inputs.",
        "warning": "Do not use a shared limit of {fact:p2003.max_ac_current_a} for both battery inputs: that is the L260-OMNI’s maximum AC current.",
    }[scenario]
    draft = TurnOutput(
        language="en",
        blocks=[TextBlock(text="{fact:p1179.max_battery_charge_a}\n" + claim)],
    )
    with (
        clients(raw) as (client, authority, _),
        closing(TurnLog(tmp_path / "turns.sqlite")) as log,
    ):
        monkeypatch.setattr(service, "_client", client)
        monkeypatch.setattr(service, "_log", log)
        monkeypatch.setattr(service.app.state, "publication", authority, raising=False)
        monkeypatch.setattr(service.app.state, "prepare", nothing, raising=False)
        monkeypatch.setattr(
            service.app.state, "generate", lambda *_: (draft, facts), raising=False
        )
        monkeypatch.setenv("LINKER_GENIE_WORK_PATH", str(tmp_path / "work.sqlite"))
        response = TestClient(service.app, headers=SHELL).post(
            "/assistant/turn",
            json={
                "conversation_id": "ac-vs-battery",
                "messages": [
                    {
                        "role": "user",
                        "content": "Compare the maximum battery and AC currents for both inverters.",
                    }
                ],
            },
        )
    assert response.status_code == 200
    if scenario in {"misattributed", "warning-then-error"}:
        assert "181 A for both battery inputs" not in response.text
    else:
        texts = [
            json.loads(event.split("data: ", 1)[1]).get("text", "")
            for event in response.text.split("\n\n")
            if event.startswith("event: block\n")
        ]
        assert any(
            "50 A per battery input." in text
            and claim.replace("{fact:p2003.max_ac_current_a}", "181 A") in text
            for text in texts
        )
        assert ac["citation"]["url"] + "#page=2" in response.text
