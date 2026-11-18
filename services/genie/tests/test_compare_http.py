"""Technical comparison and fallback product scope through the turn endpoint."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import linker_genie.app as service
import pytest
from conftest import SHELL
from fastapi.testclient import TestClient
from linker_genie.abilities import Abilities
from linker_genie.agent import make_generate
from linker_genie.facts import TurnFacts
from linker_genie.jev import Reading
from linker_genie.lexicon import Entry, Vocabulary, normalize
from linker_genie.log import TurnLog
from linker_genie.schema import TurnOutput, TurnRequest
from linker_genie.understand import Understander
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from test_turn_abilities import SEARCH, clients, manifest

SAJ = 1179
GOODWE = 6321
BATTERY = 2067
MODELS = {SAJ: "H2-25K-T3", GOODWE: "GW125/261-ESA-LCN-G10", BATTERY: "B2-10.0-HV1"}
PAIR = {"device_class": "inverters", "text": MODELS[SAJ], "with_pairings": True}


@pytest.mark.parametrize(
    "scenario",
    ["compare", "pairing", "pairing-flag", "foreign-product", "foreign-knowledge"],
)
def test_turn_keeps_model_scope_with_or_without_jev(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    compare = scenario == "compare"
    pairing = scenario == "pairing"
    raw = manifest(SAJ)
    for pid in (GOODWE, BATTERY):
        product = manifest(pid)
        raw["products"].extend(product["products"])
        raw["documents"].extend(product["documents"])
    vocabulary = Vocabulary()
    for pid, model in MODELS.items():
        vocabulary.add(normalize(model), Entry("model", model, model, frozenset({pid})))
    question = "What is the maximum charge current per input for the H2-25K-T3?"
    if compare:
        question = (
            "Compare the SAJ H2-25K-T3 and GoodWe GW125/261-ESA-LCN-G10. "
            "What is the SAJ's maximum charge current per input?"
        )
    if pairing:
        question = "Which battery is compatible with the H2-25K-T3?"
    jev = (
        SimpleNamespace(read=lambda *_: Reading("compare", 0.99, 0, 0, 0, 0, 0))
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
            } == {SAJ, GOODWE}
            # Native compare-products returns selection facts and rows, not cited figures.
            powers = {SAJ: 25, GOODWE: 125}
            return {
                "products": [
                    {
                        "product_id": pid,
                        "title": MODELS[pid],
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
                        "documents": [{"url": f"https://wp.test/{SAJ}.pdf", "page": 3}],
                    }
                ]
            return {"qualified": [row]}
        assert path.endswith("/get-product/run")
        pid = int(request.url.params["input[product_id]"])
        product = {"product_id": pid, "title": MODELS[pid]}
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
        return product

    searched: list[set[int]] = []

    def search(arguments: dict[str, Any] | None) -> dict[str, Any]:
        assert arguments is not None
        searched.append(set(arguments["product_ids"]))
        return {"hits": [], "ranking": "vector"}

    get_saj = ("linker_get_product", {"product_id": SAJ})
    knowledge = ("linker_search_knowledge", {"query": "Battery current limits"})
    pair_search = ("linker_search_products", PAIR)
    denied = {
        "pairing-flag": pair_search,
        "foreign-product": ("linker_get_product", {"product_id": BATTERY}),
        "foreign-knowledge": (
            "linker_search_knowledge",
            {"query": "Battery current limits", "product_ids": [BATTERY]},
        ),
    }
    if compare:
        calls = [get_saj, ("linker_get_product", {"product_id": GOODWE}), knowledge]
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
        if pairing:
            assert returns[0]["qualified"][0]["pairings"][0]["product_id"] == BATTERY
            blocks: list[dict[str, Any]] = [
                {
                    "type": "text",
                    "text": f"The SAJ inverter has a documented pairing with the {MODELS[BATTERY]} battery and its control module.",
                    "refs": [str(SAJ), str(BATTERY)],
                },
                {"type": "cards", "product_ids": [SAJ, BATTERY]},
                {"type": "document", "ref": f"compat.document.{BATTERY}.0"},
            ]
        else:
            assert "max_battery_charge_a" in returns[0 if compare else 1]["figures"]
            blocks = [
                {
                    "type": "text",
                    "text": "The SAJ has a maximum charge current of {fact:p1179.max_battery_charge_a} per input.",
                    "refs": [str(SAJ)],
                }
            ]
            if compare:
                assert returns[1]["product_id"] == GOODWE
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
        assert f"https://wp.test/{SAJ}.pdf#page=3" in response.text
        return
    assert "50 A per input" in response.text
    assert f"https://wp.test/{SAJ}.pdf#page=38" in response.text
    assert searched == [{SAJ, GOODWE} if compare else {SAJ}]
    assert [
        int(request.url.params["input[product_id]"])
        for request in requests
        if request.url.path.endswith("/get-product/run")
    ] == ([SAJ, GOODWE] if compare else [SAJ])
    comparisons = [
        block["product_ids"] for block in blocks if block["type"] == "compare"
    ]
    assert comparisons == ([[SAJ, GOODWE]] if compare else [])
