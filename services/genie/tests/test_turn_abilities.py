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

from linker_genie.abilities import Abilities, AbilityClient, AbilityError, gather
from linker_genie.facts import TurnFacts
from linker_genie.log import TurnLog
from linker_genie.prices import Lookup, commerce_lookup
from linker_genie.publication import PublicationClient, Snapshot
from linker_genie.schema import CardsBlock, TextBlock, TurnOutput, TurnRequest
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


@pytest.mark.parametrize("failure", [None, "draft", "bytes", "outage"])
def test_complete_turn_shares_its_tools_and_still_refuses_final_authority_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str | None
) -> None:
    import json

    import linker_genie.app as service

    seen: list[Abilities] = []
    raw = manifest()
    model_finished = False
    validated: list[dict[str, Any]] = []

    def validate(request: httpx.Request) -> httpx.Response:
        validated.append(json.loads(request.content))
        assert model_finished
        if failure == "outage":
            return httpx.Response(503)
        return httpx.Response(200, json={"valid": failure is None})

    def payload(request: httpx.Request) -> dict[str, Any]:
        if request.url.path.endswith("get-product/run"):
            return {
                "product_id": 1,
                "commerce": {
                    "price_line": "Sign in to see prices.",
                    "price_reason": "login",
                },
            }
        return {"qualified": [{"product_id": 1}]}

    def prepare(body: TurnRequest, tools: Abilities) -> Prepared:
        seen.append(tools)
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
            if failure == "draft":
                raw["products"] = []
            elif failure == "bytes":
                raw["documents"][0]["document_revision"] = "replacement-bytes"
            return TurnOutput(
                language="en",
                blocks=[
                    TextBlock(text="Current results.", refs=["1"]),
                    CardsBlock(product_ids=[1]),
                ],
            ), gather(parts)

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
            "/turn",
            json={
                "conversation_id": "scoped-turn",
                "messages": [{"role": "user", "content": "Show current products."}],
            },
        )
    log.close()

    assert len(seen) == 3 and all(tools is seen[0] for tools in seen)
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
        assert Counter(request.url.path for request in requests)[MANIFEST] == 2
        assert Counter(request.url.path for request in requests)[VALIDATE] == 3
    else:
        assert response.status_code == (503 if failure == "outage" else 409), (
            response.text
        )
        assert "Current results." not in response.text
        assert "event: block" not in response.text
