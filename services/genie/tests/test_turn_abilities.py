"""A turn's fixed Woo input set, with fresh PHP tools and final authority reads."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Barrier, Lock
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from conftest import SHELL
from fastapi.testclient import TestClient

import turn_latency
from linker_genie.abilities import Abilities, AbilityClient, AbilityError, gather
from linker_genie.facts import Document, DocumentEvidence, TurnFacts
from linker_genie.lexicon import Vocabulary
from linker_genie.log import TurnLog
from linker_genie.page import PageReader
from linker_genie.prices import Lookup, commerce_lookup
from linker_genie.publication import PublicationClient, Snapshot
from linker_genie.schema import (
    CardsBlock,
    DocumentBlock,
    TextBlock,
    TurnOutput,
    TurnRequest,
)
from linker_genie.understand import Prepared, nothing

MANIFEST = "/wp-json/linker/v1/publication/manifest"
VALIDATE = "/wp-json/linker/v1/publication/validate"
SEARCH = "/wp-json/wp-abilities/v1/abilities/linker/search-products/run"


def manifest(product_id: int = 1) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source_revision": f"source-{product_id}",
        "compatibility_revision": "compatibility",
        "products": [
            {
                "product_id": product_id,
                "product_revision": f"product-{product_id}",
                "published_locale_ids": [product_id, product_id + 100],
            }
        ],
        "documents": [
            {
                "document_id": f"doc-{product_id}",
                "document_revision": f"revision-{product_id}",
                "blob_sha256": "a" * 64,
                "url": f"https://wp.test/{product_id}.pdf",
                "aliases": [f"https://wp.test/alias-{product_id}.pdf"],
                "product_ids": [product_id],
            }
        ],
    }


@contextmanager
def clients(
    raw: dict[str, Any],
    payload: dict[str, Any] | Callable[[httpx.Request], dict[str, Any]] | None = None,
    validate: Callable[[httpx.Request], httpx.Response] | None = None,
) -> Iterator[tuple[AbilityClient, PublicationClient, list[httpx.Request]]]:
    requests: list[httpx.Request] = []
    lock = Lock()

    def handle(request: httpx.Request) -> httpx.Response:
        with lock:
            requests.append(request)
        if request.url.path == MANIFEST:
            return httpx.Response(200, json=raw)
        if request.url.path == VALIDATE:
            if validate is not None:
                return validate(request)
            return httpx.Response(200, json={"valid": True})
        result = payload(request) if callable(payload) else payload
        return httpx.Response(
            200,
            json={
                "result": result
                if result is not None
                else {
                    "qualified": [],
                    "excluded": {"by_reason": {}},
                    "unknown_fields": [],
                }
            },
        )

    transport = httpx.MockTransport(handle)
    authority = PublicationClient("https://wp.test", transport)
    client = AbilityClient(
        "https://wp.test", transport=transport, publication=authority
    )
    try:
        yield client, authority, requests
    finally:
        client.close()
        authority.close()


def test_four_tools_share_only_the_whole_turn_authority_reads() -> None:
    with clients(manifest()) as (client, authority, requests):
        permission = authority.snapshot()
        turn = client.for_turn(permission)
        for text in ("EcoFlow PowerOcean", "PowerOcean", "EcoFlow", "home-storage"):
            assert turn.run("linker/search-products", {"text": text})["qualified"] == []
        authority.validate(permission)

    assert Counter(request.url.path for request in requests) == {
        MANIFEST: 1,
        SEARCH: 4,
        VALIDATE: 1,
    }


def test_standalone_tools_still_refresh_and_validate_each_call() -> None:
    with clients(manifest()) as (client, _authority, requests):
        for _ in range(4):
            client.run("linker/search-products")
    assert Counter(request.url.path for request in requests) == {
        MANIFEST: 4,
        SEARCH: 4,
        VALIDATE: 4,
    }


def test_binding_a_turn_does_not_replace_the_standalone_current_source() -> None:
    raw = manifest()
    with clients(raw, {"product_id": 2}) as (client, authority, requests):
        turn = client.for_turn(authority.snapshot())
        raw.update(manifest(2))
        with pytest.raises(AbilityError, match="no longer published"):
            turn.run("linker/get-product", {"product_id": 2})
        assert client.run("linker/get-product", {"product_id": 2})["product_id"] == 2
        # A subsequent standalone call sees the withdrawal too, without waiting.
        raw["products"] = []
        with pytest.raises(AbilityError, match="no longer published"):
            client.run("linker/get-product", {"product_id": 2})
    assert (
        sum(request.url.path.endswith("get-product/run") for request in requests) == 1
    )


def test_concurrent_turns_keep_their_permissions_and_customer_contexts_separate() -> (
    None
):
    overlap = Barrier(2)

    def payload(request: httpx.Request) -> dict[str, Any]:
        overlap.wait(timeout=5)
        return {"product_id": int(request.url.params["input[product_id]"])}

    with clients(manifest(), payload) as (client, _authority, requests):
        turns = [client.for_turn(Snapshot.read(manifest(pid))) for pid in (1, 2)]

        def use_turn(index: int) -> None:
            pid = index + 1
            assert (
                turns[index].run(
                    "linker/get-product", {"product_id": pid}, f"customer-{pid}"
                )["product_id"]
                == pid
            )
            with pytest.raises(AbilityError, match="no longer published"):
                turns[index].run("linker/get-product", {"product_id": 3 - pid})

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(use_turn, (0, 1)))
    assert len(requests) == 2
    for request in requests:
        pid = request.url.params["input[product_id]"]
        assert request.headers["X-Linker-User-Context"] == f"customer-{pid}"


@pytest.mark.parametrize("product_id", [2, 999])
def test_new_or_unpublished_input_members_never_reach_the_php_tool(
    product_id: int,
) -> None:
    with clients(manifest()) as (client, _authority, requests):
        turn = client.for_turn(Snapshot.read(manifest()))
        with pytest.raises(AbilityError) as caught:
            turn.run("linker/compare-products", {"product_ids": [1, product_id]})
        assert caught.value.fatal
    assert requests == []


@pytest.mark.parametrize(
    "payload",
    [
        {"qualified": [{"product_id": 1}, {"product_id": 2}]},
        {"products": [{"product_id": 1}, {"product_id": 999}]},
        {"qualified": [{"product_id": 1, "pairings": [{"product_id": 2}]}]},
        {"documents": [{"url": "https://wp.test/new.pdf"}]},
    ],
)
def test_every_returned_candidate_pairing_and_document_stays_within_the_turn(
    payload: dict[str, Any],
) -> None:
    with clients(manifest(), payload) as (client, _authority, requests):
        turn = client.for_turn(Snapshot.read(manifest()))
        with pytest.raises(AbilityError) as caught:
            turn.record("linker/search-products")
        assert caught.value.fatal
    assert [request.url.path for request in requests] == [SEARCH]


def test_document_inputs_and_alias_outputs_use_the_same_bound_permission() -> None:
    with clients(
        manifest(), {"documents": [{"url": "https://wp.test/alias-1.pdf#page=1"}]}
    ) as (client, _authority, requests):
        turn = client.for_turn(Snapshot.read(manifest()))
        with pytest.raises(AbilityError, match="document is no longer published"):
            turn.run(
                "linker/get-product",
                {"product_id": 1, "url": "https://wp.test/new.pdf"},
            )
        assert turn.run("linker/get-product", {"product_id": 101})["documents"]
    assert len(requests) == 1


@pytest.mark.parametrize(
    "arguments",
    [
        {"product_ids": ["1", "2"]},
        {"product_ids": (1, 2)},
        {"inverter_id": "1", "battery_id": "2"},
        {"product_id": "2"},
        {"product_ids": [True, "2"]},
        {"product_id": 1.0},
        {"product_ids": [1, 2.0]},
        {"product_ids": [1, ["2"]]},
        {"product_ids": [1, {"id": "2"}]},
        {"product_ids": {"0": "1", "1": "2"}},
        {"product_ids": None},
        {"battery_id": False},
        {"product_ids[0]": 1, "product_ids[1]": 2},
        {"product_ids][0": 1, "product_ids][1": 2},
        {"product.ids": ["1", "2"]},
        {"product ids": ["1", "2"]},
        {"product_id\x00": "2"},
    ],
)
def test_ambiguous_id_inputs_never_reach_a_verdict_only_php_response(
    arguments: dict[str, Any],
) -> None:
    raw = manifest()
    permission = Snapshot.read(raw)
    # Woo may have published a second member after the turn captured S0.
    raw["products"].extend(manifest(2)["products"])
    with clients(raw, {"verdict": "released", "conditions": []}) as (
        client,
        _authority,
        requests,
    ):
        with pytest.raises(AbilityError):
            client.for_turn(permission).run("linker/check-compatibility", arguments)
    assert requests == []


@pytest.mark.parametrize(
    "arguments",
    [
        {"product_ids": [1, 102]},
        {"inverter_id": 1, "battery_id": 102},
    ],
)
def test_native_integer_ids_and_published_locale_ids_allow_verdict_only_responses(
    arguments: dict[str, Any],
) -> None:
    raw = manifest()
    raw["products"].extend(manifest(2)["products"])
    with clients(raw, {"verdict": "released", "conditions": []}) as (
        client,
        _authority,
        requests,
    ):
        result = client.for_turn(Snapshot.read(raw)).run(
            "linker/check-compatibility", arguments
        )
    assert result["verdict"] == "released"
    assert len(requests) == 1
    sent = dict(requests[0].url.params)
    assert "102" in sent.values() and "1" in sent.values()


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "draft",
        "bytes",
        "outage",
        "new_member",
        "new_url",
        "new_owner",
        "page_revoked",
    ],
)
def test_complete_turn_shares_its_tools_and_still_refuses_final_authority_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str | None,
) -> None:
    import json

    import linker_genie.app as service

    seen: list[Abilities] = []
    raw = manifest()
    if failure == "new_owner":
        raw["products"].extend(manifest(2)["products"])
    refused_before_validation = failure in {
        "new_member",
        "new_url",
        "new_owner",
        "page_revoked",
    }
    model_finished = False
    validated: list[dict[str, Any]] = []

    def validate(request: httpx.Request) -> httpx.Response:
        validated.append(json.loads(request.content))
        assert model_finished
        # The only final Woo read occurs after the computed answer is logged,
        # before any SSE bytes are released. It must retain the old citation.
        (stored,) = log._db.execute("SELECT output FROM turns").fetchone()
        document = next(
            block
            for block in json.loads(stored)["blocks"]
            if block["type"] == "document"
        )
        assert document["document_id"] == "doc-1"
        assert document["document_revision"] == "revision-1"
        if failure == "outage":
            return httpx.Response(503)
        return httpx.Response(200, json={"valid": failure not in {"draft", "bytes"}})

    def payload(request: httpx.Request) -> dict[str, Any]:
        if request.url.path.endswith("get-product/run"):
            return {
                "product_id": 1,
                "commerce": {
                    "price_line": "Sign in to see prices.",
                    "price_reason": "login",
                },
            }
        return {
            "qualified": [
                {
                    "product_id": 1,
                    "pairings": [
                        {
                            "product_id": 1,
                            "verdict": "released",
                            "documents": [
                                {
                                    "document_id": "doc-1",
                                    "document_revision": "revision-1",
                                    "product_id": 1,
                                    "url": "https://wp.test/alias-1.pdf",
                                    "page": 2,
                                }
                            ],
                        }
                    ],
                }
            ]
        }

    def prepare(
        body: TurnRequest,
        tools: Abilities,
        *,
        get_vocabulary: Callable[[], Vocabulary] | None = None,
        on_stage: Callable[[str], None] | None = None,
    ) -> Prepared:
        assert get_vocabulary is not None
        seen.append(tools)
        if failure == "page_revoked":
            raw["products"] = []
            pages = PageReader("https://wp.test", publication=authority)
            try:
                pages.read(body.page_context, "Show current products.", False)
            finally:
                pages.close()
        result = nothing(body)
        _payload, result.facts = tools.record(
            "linker/search-products", {"text": "initial"}
        )
        return result

    def lookup(tools: Abilities, body: TurnRequest, deadline: float) -> Lookup:
        seen.append(tools)
        return commerce_lookup(tools, body, deadline)

    def make_generate(
        tools: Abilities, **_kwargs: Any
    ) -> Callable[[TurnRequest, str | None], tuple[TurnOutput, TurnFacts]]:
        seen.append(tools)

        def generate(
            body: TurnRequest, retry: str | None
        ) -> tuple[TurnOutput, TurnFacts]:
            nonlocal model_finished
            assert retry is None
            parts = [
                tools.record("linker/search-products", {"text": text})[1]
                for text in ("one", "two", "three")
            ]
            model_finished = True
            facts = gather(parts)
            product_id = 1
            document_url = "https://wp.test/1.pdf"
            if failure == "draft":
                raw["products"] = []
            elif failure == "bytes":
                raw["documents"][0]["document_revision"] = "replacement-bytes"
                raw["documents"][0]["blob_sha256"] = "b" * 64
            elif failure == "new_member":
                raw["products"].extend(manifest(2)["products"])
                # A derived result may be newer than the turn's original source.
                # Even otherwise grounded output must remain inside original S0.
                product_id = 2
                facts.product_ids.add(2)
                facts.qualified_ids.add(2)
                facts.commerce[2] = {"price_line": "Sign in", "price_reason": "login"}
            elif failure == "new_url":
                document_url = "https://wp.test/new.pdf"
                raw["documents"].append(
                    {**raw["documents"][0], "document_id": "new", "url": document_url}
                )
            evidence = (
                DocumentEvidence("doc-1", "revision-1", 2)
                if failure == "new_owner"
                else None
            )
            facts.documents["fixture-document"] = Document(
                document_url, "Manual", 1, evidence
            )
            return TurnOutput(
                language="en",
                blocks=[
                    TextBlock(text="Current results.", refs=[str(product_id)]),
                    CardsBlock(product_ids=[product_id]),
                    DocumentBlock(ref="fixture-document"),
                    DocumentBlock(ref="compat.document.1.0"),
                ],
            ), facts

        return generate

    log = TurnLog(tmp_path / "turns.sqlite")
    with clients(raw, payload, validate) as (client, authority, requests):
        monkeypatch.setattr(service, "_client", client)
        monkeypatch.setattr(service, "_log", log)
        monkeypatch.setattr(service.app.state, "publication", authority, raising=False)
        for attribute in ("prepare", "commerce", "generate"):
            monkeypatch.delattr(service.app.state, attribute, raising=False)
        monkeypatch.setattr(
            service, "understander", lambda: SimpleNamespace(prepare=prepare)
        )
        monkeypatch.setattr(service, "page_reader", lambda: SimpleNamespace(read=None))
        monkeypatch.setattr(service, "commerce_lookup", lookup)
        monkeypatch.setattr(service, "make_generate", make_generate)
        monkeypatch.setenv("LINKER_GENIE_WORK_PATH", str(tmp_path / "work.sqlite"))
        response = TestClient(service.app, headers=SHELL).post(
            "/assistant/turn",
            json={
                "conversation_id": "scoped-turn",
                "messages": [{"role": "user", "content": "Show current products."}],
                "page_context": {"type": "product", "product_id": 1}
                if failure == "page_revoked"
                else {},
            },
        )
    if refused_before_validation:
        # Give any start note left by the request time to pass the report's grace period.
        with log._db:
            log._db.execute("UPDATE turn_starts SET created_at = '2020-01-01 00:00:00'")
    log.close()

    assert len(seen) == (1 if failure == "page_revoked" else 3)
    assert all(tools is seen[0] for tools in seen)
    if refused_before_validation:
        assert response.status_code == 409, response.text
        assert response.json() == {"detail": "publication_changed"}
        assert "event: block" not in response.text
        assert validated == []
        assert Counter(request.url.path for request in requests)[MANIFEST] == (
            2 if failure == "page_revoked" else 1
        )
        assert turn_latency.main([str(log.path)]) == 1  # No completed turns.
        report = capsys.readouterr().out
        assert "completed=0 incomplete=1 unfinished=0" in report
        return
    assert validated[0]["products"] == [
        {"product_id": 1, "product_revision": "product-1"}
    ]
    assert validated[0]["documents"] == [
        {"document_id": "doc-1", "document_revision": "revision-1", "product_id": 1}
    ]
    assert Counter(request.url.path for request in requests)[SEARCH] == 4
    assert (
        sum(request.url.path.endswith("get-product/run") for request in requests) == 1
    )
    if failure is None:
        assert response.status_code == 200, response.text
        assert "Current results." in response.text
        assert Counter(request.url.path for request in requests)[MANIFEST] == 1
        assert Counter(request.url.path for request in requests)[VALIDATE] == 1
        assert requests[-1].url.path == VALIDATE
        blocks = [
            json.loads(event.split("data: ", 1)[1])
            for event in response.text.split("\n\n")
            if event.startswith("event: block\n")
        ]
        document = next(block for block in blocks if block["type"] == "document")
        assert document["document_id"] == "doc-1"
        assert document["document_revision"] == "revision-1"
        compat = next(
            block for block in blocks if block.get("ref") == "compat.document.1.0"
        )
        assert compat["evidence_product_id"] == 1
        assert compat["document_id"] == "doc-1"
        assert compat["document_revision"] == "revision-1"
    else:
        assert response.status_code == (503 if failure == "outage" else 409), (
            response.text
        )
        assert "Current results." not in response.text
        assert "event: block" not in response.text


@pytest.mark.parametrize(
    "scenario",
    [
        "one-model",
        "same-model-follow-up",
        "comparison",
        "no-jev",
        "page-comparison",
        "port-count",
        "mixed-claim",
    ],
)
def test_named_document_turn_cites_the_evidence_for_its_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    import asyncio
    import json

    from pydantic_ai.messages import (
        ModelMessage,
        ModelResponse,
        ToolCallPart,
        ToolReturnPart,
        UserPromptPart,
    )
    from pydantic_ai.models.function import AgentInfo, FunctionModel

    import linker_genie.app as service
    from linker_genie.agent import make_generate
    from linker_genie.jev import Reading
    from linker_genie.lexicon import Entry, normalize
    from linker_genie.understand import Understander

    # Turn 825: the first search found a datasheet and manual excerpts, but not
    # the charging/discharging row. The Woo figures already name the row's page.
    uploads = "https://de-linker.com/wp-content/uploads"
    manual = f"{uploads}/2026/10/SAJ_H2_10-30K_User-Manual_DE-EN_EU.pdf"
    datasheet = f"{uploads}/2026/09/H2-10-30K-T2T3-datasheet-EN-BEU.pdf"
    german_sheet = f"{uploads}/2026/10/SAJ_H2_15-30K-T3_Datasheet_DE.pdf"
    goodwe = f"{uploads}/2026/10/GW_ESA-261kWh_User-Manual-EN_V1.6.pdf"
    wrong_ref = "be488dc6630c-p2-model-c306bdd9d52ddb78"
    manual_excerpt = "770ccafa080c-p38-model-6360f4a8d9a0e6ce"
    other_ref = "0adfb3d5e6df-p94-model-22fab7a3876a695b"
    question = (
        "How many battery inputs does the SAJ H2-25K-T3 have, and what is the "
        "maximum charge and discharge current per input?"
    )
    page_comparison = scenario == "page-comparison"
    figure_id = 1279 if page_comparison else 1179
    comparison = scenario == "comparison" or page_comparison
    follow_up = scenario == "same-model-follow-up"
    no_jev = scenario == "no-jev"
    port_count = scenario == "port-count"
    mixed_claim = scenario == "mixed-claim"
    # Page context uses the translated ID while Woo also accepts its canonical ID.
    page_context = {"type": "product", "product_id": 1279} if page_comparison else {}
    if page_comparison:
        question = "Compare this inverter's battery inputs and current with GW125/261-ESA-LCN-G10."
    elif comparison:
        question += " Compare the battery inputs with the GoodWe GW125/261-ESA-LCN-G10."
    elif port_count:
        question = "How many battery inputs does the SAJ H2-25K-T3 have?"
    elif mixed_claim:
        question += " Does the battery input also have reverse polarity protection?"
    vocabulary = Vocabulary()
    for model, pid in (("H2-25K-T3", 1179), ("GW125/261-ESA-LCN-G10", 6321)):
        vocabulary.add(normalize(model), Entry("model", model, model, frozenset({pid})))
    reading = Reading("documents_specs", 0.99, float(page_comparison), 0, 0, 0, 0)
    jev = None if no_jev else SimpleNamespace(read=lambda *_args: reading)

    def hit(ref: str, url: str, page: int, pid: int, text: str) -> dict[str, Any]:
        document = next(doc for doc in raw["documents"] if doc["url"] == url)
        return {
            "chunk_id": ref,
            "doc_url": url,
            "page": page,
            "document_id": document["document_id"],
            "document_revision": document["document_revision"],
            "evidence_product_id": pid,
            "product_ids": [pid],
            "text": text,
        }

    searches: list[list[int]] = []

    def search(arguments: dict[str, Any] | None) -> dict[str, Any]:
        assert arguments is not None
        searches.append(arguments.get("product_ids", [1179, 6321]))
        scope = [1179 if pid == 1279 else pid for pid in searches[-1]]
        hits = []
        if 1179 in scope:
            hits.extend(
                [
                    hit(
                        wrong_ref,
                        german_sheet,
                        2,
                        1179,
                        "| Max. Lade-/Entladestrom [A] | 50/50 |\n"
                        "| Schutz vor Verpolung des Akku-Eingangs | Integriert |",
                    ),
                    hit(
                        manual_excerpt,
                        manual,
                        38,
                        1179,
                        "| Model | H2-25K-T3 |\n| Battery Voltage Range [V] | 180 - 800 |",
                    ),
                ]
            )
        if 6321 in scope:
            hits.append(
                hit(other_ref, goodwe, 94, 6321, "GoodWe technical specifications")
            )
        return {"hits": hits, "ranking": "vector"}

    def product(request: httpx.Request) -> dict[str, Any]:
        if request.url.path == SEARCH:
            return {"qualified": [{"product_id": 1179, "title": "SAJ H2-25K-T3"}]}
        pid = int(request.url.params["input[product_id]"])
        if pid == 6321:
            return {"product_id": pid, "title": "GoodWe GW125/261-ESA-LCN-G10"}
        figures = {
            "n_battery_ports": {
                "value": "2",
                "unit": "",
                "citation": {"url": datasheet, "page": 2},
            },
            **{
                f"max_battery_{direction}_a": {
                    "value": "50",
                    "unit": "A",
                    "citation": {"url": manual, "page": 38},
                    "evidence_refs": ["doc-0:p38", "doc-0:p43", "doc-1:p2"],
                    "qualifier": {
                        "quantity_kind": "maximum",
                        "scope": "per_battery_port",
                        "direction": direction,
                        "ports": ["BAT1", "BAT2"],
                        "source_expression": "2*50 A",
                    },
                }
                for direction in ("charge", "discharge")
            },
        }
        return {
            "product_id": pid,
            "title": "SAJ H2-25K-T3",
            "figures": figures,
            "documents": [
                document
                for document in raw["documents"]
                if (1179 if pid == 1279 else pid) in document["product_ids"]
            ],
        }

    understander = Understander(None, jev, search=search)

    def respond(messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        returns = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        lookups = [part for part in returns if part.tool_name == "linker_get_product"]
        if not lookups and not port_count and (not comparison or page_comparison):
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "linker_get_product",
                        {
                            "arguments": {
                                "product_id": figure_id
                                if follow_up or no_jev or page_comparison
                                else 6321
                            },
                        },
                    )
                ]
            )
        if len(lookups) == 1 and no_jev and len(returns) == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "linker_get_product",
                        {
                            "arguments": {"product_id": 6321},
                        },
                    )
                ]
            )
        if not (page_comparison or port_count) and not any(
            part.tool_name == "linker_search_knowledge" for part in returns
        ):
            arguments = (
                {"query": "Maximum battery charging current"}
                if follow_up
                else {
                    "query": "GoodWe ESA GW125/261-ESA-LCN-G10 technical data",
                    "product_ids": [6321],
                }
            )
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "linker_search_knowledge",
                        {"arguments": arguments},
                    )
                ]
            )
        if follow_up or page_comparison:
            product_result = returns[0].content
            assert isinstance(product_result, dict)
            assert product_result.get("product_id") == figure_id
        search_result = returns[-1].content if returns else {}
        assert isinstance(search_result, dict)
        other_found = page_comparison or any(
            item["chunk_id"] == other_ref for item in search_result.get("hits", [])
        )
        text = (
            f"The SAJ inverter has {{fact:{figure_id}.n_battery_ports}} battery inputs."
        )
        if not port_count:
            text += f"\n\n{{fact:p{figure_id}.max_battery_charge_a}}\n\n{{fact:{figure_id}.max_battery_discharge_a}}"
        prompt = next(
            part.content
            for message in messages
            for part in message.parts
            if isinstance(part, UserPromptPart)
        )
        assert isinstance(prompt, str)
        refs = [str(figure_id)]
        if mixed_claim:
            text += "\n\nThe battery input has reverse polarity protection."
            refs.append(wrong_ref)
        elif (
            not (no_jev or port_count)
            and "separate claim you actually make" not in prompt
        ):
            refs.append(wrong_ref)
        blocks: list[dict[str, Any]] = (
            []
            if no_jev or port_count
            else [{"type": "document", "ref": manual_excerpt}]
        )
        if other_found:
            text += "\n\nThe GoodWe manual gives the other product's technical specifications."
            refs.extend(["6321", other_ref])
            blocks.append({"type": "cards", "product_ids": [figure_id, 6321]})
        blocks.insert(0, {"type": "text", "text": text, "refs": refs})
        return ModelResponse(
            parts=[ToolCallPart("final_result", {"language": "en", "blocks": blocks})]
        )

    raw = manifest(1179)
    raw["products"].extend(manifest(6321)["products"] + manifest(1181)["products"])
    raw["documents"] = [
        {
            "document_id": f"doc-{index}",
            "document_revision": f"revision-{index}",
            "blob_sha256": "a" * 64,
            "url": url,
            "product_ids": associated_ids,
        }
        for index, (url, associated_ids) in enumerate(
            [
                (manual, [1179, 1181]),
                (datasheet, [1179, 1181]),
                (german_sheet, [1179]),
                (goodwe, [6321]),
            ]
        )
    ]
    log = TurnLog(tmp_path / "turns.sqlite")
    with clients(raw, product) as (client, authority, requests):
        for attribute in ("prepare", "generate"):
            monkeypatch.delattr(service.app.state, attribute, raising=False)
        monkeypatch.setattr(service, "_client", client)
        monkeypatch.setattr(service, "_log", log)
        monkeypatch.setattr(service.app.state, "publication", authority, raising=False)
        monkeypatch.setattr(
            service.app.state, "commerce", lambda _ids: (TurnFacts(), []), raising=False
        )
        monkeypatch.setattr(service, "understander", lambda: understander)
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

            def run_model(
                body: TurnRequest, retry: str | None
            ) -> tuple[TurnOutput, TurnFacts]:
                with asyncio.Runner() as runner:
                    runner.get_loop()
                    return generate(body, retry)

            return run_model

        monkeypatch.setattr(service, "make_generate", generate_with_model)
        monkeypatch.setenv("LINKER_GENIE_WORK_PATH", str(tmp_path / "work.sqlite"))
        response = TestClient(service.app, headers=SHELL).post(
            "/assistant/turn",
            json={
                "conversation_id": "turn-825",
                "messages": [{"role": "user", "content": question}],
                "page_context": page_context,
            },
        )
    log.close()

    assert response.status_code == 200, response.text
    blocks = [
        json.loads(event.split("data: ", 1)[1])
        for event in response.text.split("\n\n")
        if event.startswith("event: block\n")
    ]
    urls = {block["url"] for block in blocks if block["type"] == "document"}
    text = next(block["text"] for block in blocks if block["type"] == "text")
    assert "2 battery inputs" in text, response.text
    if port_count:
        assert urls == {f"{datasheet}#page=2"}
        return
    subject = " for SAJ H2-25K-T3" if comparison else ""
    assert f"The maximum charge current{subject} is 50 A per battery input." in text
    assert f"The maximum discharge current{subject} is 50 A per battery input." in text
    if comparison:
        assert set(searches[0]) == ({1279, 6321} if page_comparison else {1179, 6321})
        assert searches[1:] == ([] if page_comparison else [[6321]])
        assert f"{goodwe}#page=94" in urls
        assert any(block.get("product_ids") == [figure_id, 6321] for block in blocks)
    else:
        assert all(6321 not in block.get("product_ids", []) for block in blocks)
        assert f"{goodwe}#page=94" not in urls
        assert "GoodWe" not in text
        assert searches == (
            [[1179], [1179]] if follow_up else ([] if no_jev else [[1179]])
        )
        product_requests = [
            request.url.params["input[product_id]"]
            for request in requests
            if request.url.path.endswith("get-product/run")
        ]
        assert product_requests == (["1179", "1179"] if follow_up else ["1179"])
    # Both current placeholders use Woo's reviewed page 38 citation. The only
    # retrieved excerpt on that page lacks the 2*50 A row and is not its source.
    current_links = [
        block for block in blocks if block.get("url") == f"{manual}#page=38"
    ]
    assert [block["ref"] for block in current_links] == [
        f"p{figure_id}.max_battery_charge_a.source"
    ]
    assert current_links[0]["evidence_product_id"] == 1179
    assert current_links[0]["document_id"] == "doc-0"
    assert current_links[0]["document_revision"] == "revision-0"
    assert all(block.get("ref") != manual_excerpt for block in blocks)
    assert len(current_links) == 1 and current_links[0]["label"].endswith("pp. 38, 43")
    assert f"{manual}#page=43" not in urls
    assert f"{datasheet}#page=2" in urls
    assert (f"{german_sheet}#page=2" in urls) == mixed_claim
    if mixed_claim:
        assert "The battery input has reverse polarity protection." in text
