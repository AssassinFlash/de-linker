"""Turn-owned Woo permission through the actual Store API vocabulary cache."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from conftest import SHELL
from fastapi.testclient import TestClient

import linker_genie.jev as jev
from linker_genie.abilities import AbilityClient
from linker_genie.facts import TurnFacts
from linker_genie.lexicon import Vocabulary
from linker_genie.log import TurnLog
from linker_genie.publication import PublicationClient, Snapshot
from linker_genie.schema import TextBlock, TurnOutput, TurnRequest
from linker_genie.storeapi import StoreVocabulary, VocabularyError
from linker_genie.understand import Understander

MANIFEST = "/wp-json/linker/v1/publication/manifest"
VALIDATE = "/wp-json/linker/v1/publication/validate"
PRODUCTS = "/wp-json/wc/store/v1/products"


def manifest(*ids: int) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source_revision": "source-" + "-".join(map(str, ids)),
        "compatibility_revision": "compatibility",
        "products": [
            {
                "product_id": pid,
                "product_revision": f"revision-{pid}",
                "published_locale_ids": [pid, pid + 100],
            }
            for pid in ids
        ],
        "documents": [],
    }


@dataclass
class Source:
    raw: dict[str, Any] = field(default_factory=lambda: manifest(1))
    paths: list[str] = field(default_factory=list)
    now: float = 0.0
    authority_down: bool = False
    store_down: bool = False
    after_manifest: Callable[[], None] | None = None
    before_listing: Callable[[], None] | None = None

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.paths.append(request.url.path)
        if request.url.path == MANIFEST:
            if self.authority_down:
                return httpx.Response(503)
            response = httpx.Response(200, json=self.raw)
            if self.after_manifest is not None:
                self.after_manifest()
            return response
        if request.url.path == VALIDATE:
            return httpx.Response(200, json={"valid": True})
        if request.url.path.endswith("/identify"):
            return httpx.Response(200, json={"models": []})
        if request.url.path.startswith(PRODUCTS):
            if self.before_listing is not None:
                self.before_listing()
            if self.store_down:
                return httpx.Response(503)
            german = request.url.params.get("lang") == "de"
            rows = (
                []
                if request.url.path.endswith("/categories")
                else [
                    {
                        "id": pid + 100 if german else pid,
                        "name": f"Published {pid}",
                        "attributes": [
                            {
                                "taxonomy": "pa_model",
                                "terms": [{"name": f"MODEL-{pid}"}],
                            }
                        ],
                    }
                    for pid in (1, 2)
                ]
            )
            return httpx.Response(200, json=rows, headers={"X-WP-TotalPages": "1"})
        return httpx.Response(200, json={"result": {"qualified": []}})


@pytest.fixture
def source() -> Iterator[tuple[Source, StoreVocabulary, PublicationClient]]:
    state = Source()
    transport = httpx.MockTransport(state.handle)
    authority = PublicationClient("https://wp.test", transport)
    vocabulary = StoreVocabulary(
        "https://wp.test",
        transport=transport,
        clock=lambda: state.now,
        publication=authority,
    )
    try:
        yield state, vocabulary, authority
    finally:
        vocabulary.close()
        authority.close()


def test_standalone_cold_and_warm_get_each_read_authority_once(
    source: tuple[Source, StoreVocabulary, PublicationClient],
) -> None:
    state, store, _authority = source
    cold = store.get()
    assert state.paths.count(MANIFEST) == 1
    assert set(cold.names) == {1}
    listings = state.paths.count(PRODUCTS)
    assert store.get() is cold
    assert state.paths.count(MANIFEST) == 2
    assert state.paths.count(PRODUCTS) == listings


def test_turn_cold_warm_and_ttl_reload_use_only_supplied_permission(
    source: tuple[Source, StoreVocabulary, PublicationClient],
) -> None:
    state, store, authority = source
    permission = authority.snapshot()
    state.paths.clear()
    cold = store.get(permission)
    assert set(cold.names) == {1}
    assert state.paths.count(PRODUCTS) == 2  # Native EN and DE listings.
    state.now = 599
    assert store.get(permission) is cold
    state.now = 600
    assert store.get(permission) is not cold
    assert state.paths.count(PRODUCTS) == 4
    assert MANIFEST not in state.paths


def test_cold_load_and_cache_label_use_the_same_captured_source(
    source: tuple[Source, StoreVocabulary, PublicationClient],
) -> None:
    state, store, _authority = source
    state.after_manifest = lambda: setattr(state, "raw", manifest(2))
    old = store.get()
    assert set(old.names) == {1}
    assert state.paths.count(MANIFEST) == 1
    state.after_manifest = None
    assert set(store.get().names) == {2}
    assert set(old.names) == {1}


def test_publication_changes_invalidate_cache_without_waiting_for_ttl(
    source: tuple[Source, StoreVocabulary, PublicationClient],
) -> None:
    state, store, _authority = source
    old = store.get(Snapshot.read(manifest(1)))
    added = store.get(Snapshot.read(manifest(1, 2)))
    withdrawn = store.get(Snapshot.read(manifest(2)))
    assert set(old.names) == {1}
    assert set(added.names) == {1, 2}
    assert set(withdrawn.names) == {2}
    assert set(store.get(Snapshot.read(manifest(1))).names) == {1}
    assert set(withdrawn.names) == {2}
    assert MANIFEST not in state.paths


def test_failed_reload_never_returns_or_relabels_the_previous_source(
    source: tuple[Source, StoreVocabulary, PublicationClient],
) -> None:
    state, store, _authority = source
    old = store.get(Snapshot.read(manifest(1)))
    state.store_down = True
    with pytest.raises(VocabularyError, match="503"):
        store.get(Snapshot.read(manifest(2)))
    assert store.get(Snapshot.read(manifest(1))) is old
    state.store_down = False
    assert set(store.get(Snapshot.read(manifest(2))).names) == {2}
    assert MANIFEST not in state.paths


def test_standalone_authority_failure_never_uses_warm_cached_permission(
    source: tuple[Source, StoreVocabulary, PublicationClient],
) -> None:
    state, store, _authority = source
    store.get()
    state.authority_down = True
    with pytest.raises(VocabularyError, match="unavailable"):
        store.get()
    state.authority_down = False
    state.raw = manifest(2)
    assert set(store.get().names) == {2}
    assert state.paths.count(MANIFEST) == 3


@pytest.mark.parametrize("first,second", [(1, 2), (2, 1)])
def test_concurrent_old_and_new_turn_sources_never_mix_cached_products(
    source: tuple[Source, StoreVocabulary, PublicationClient], first: int, second: int
) -> None:
    state, store, _authority = source
    listing_started, second_started, release = Event(), Event(), Event()

    def pause_first_listing() -> None:
        if not listing_started.is_set():
            listing_started.set()
            assert release.wait(3)

    def next_turn() -> Vocabulary:
        second_started.set()
        return store.get(Snapshot.read(manifest(second)))

    state.before_listing = pause_first_listing
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(store.get, Snapshot.read(manifest(first)))
        assert listing_started.wait(3)
        b = pool.submit(next_turn)
        assert second_started.wait(3)
        release.set()
        first_result, second_result = a.result(timeout=3), b.result(timeout=3)
    assert set(first_result.names) == {first}
    assert set(second_result.names) == {second}
    assert set(first_result.names) == {first}
    assert MANIFEST not in state.paths


def test_per_call_getter_does_not_replace_the_understander_default(
    source: tuple[Source, StoreVocabulary, PublicationClient],
) -> None:
    state, _store, authority = source
    calls: list[str] = []

    def getter(label: str) -> Vocabulary:
        calls.append(label)
        return Vocabulary()

    understander = Understander(lambda: getter("default"), None)
    client = AbilityClient(
        "https://wp.test",
        transport=httpx.MockTransport(state.handle),
        publication=authority,
    )
    body = TurnRequest.model_validate(
        {
            "conversation_id": "per-call",
            "messages": [{"role": "user", "content": "Hello"}],
        }
    )
    try:
        understander.prepare(body, client, get_vocabulary=lambda: getter("turn"))
        understander.prepare(body, client)
    finally:
        client.close()
    assert calls == ["turn", "default"]


def test_actual_http_cold_and_warm_turns_do_not_reread_vocabulary_permission(
    source: tuple[Source, StoreVocabulary, PublicationClient],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import linker_genie.app as service

    state, store, authority = source
    log = TurnLog(tmp_path / "turns.sqlite")
    client = AbilityClient(
        "https://wp.test",
        transport=httpx.MockTransport(state.handle),
        publication=authority,
    )
    constructed: list[str] = []

    def make_store(base_url: str, *, publication: PublicationClient) -> StoreVocabulary:
        assert publication is authority
        constructed.append(base_url)
        return store

    def generate(body: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        return TurnOutput(
            language="en",
            blocks=[TextBlock(text="Please tell me which product you need.")],
        ), TurnFacts()

    monkeypatch.setattr(service, "_log", log)
    monkeypatch.setattr(service, "_client", client)
    monkeypatch.setattr(service, "_understander", None)
    monkeypatch.setattr(service, "_vocabulary", None)
    monkeypatch.setattr(service, "StoreVocabulary", make_store)
    monkeypatch.setattr(service, "current", lambda: authority)
    monkeypatch.setattr(service, "page_reader", lambda: SimpleNamespace(read=None))
    monkeypatch.setattr(service, "vision", lambda: None)
    monkeypatch.setattr(jev, "from_env", lambda: None)
    monkeypatch.setattr(service.app.state, "publication", authority, raising=False)
    monkeypatch.delattr(service.app.state, "prepare", raising=False)
    monkeypatch.setattr(service.app.state, "generate", generate, raising=False)
    monkeypatch.setattr(
        service.app.state, "commerce", lambda ids: (TurnFacts(), []), raising=False
    )
    monkeypatch.setenv("LINKER_GENIE_WORK_PATH", str(tmp_path / "work.sqlite"))
    try:
        for endpoint in ("/turn", "/assistant/turn"):
            state.paths.clear()
            response = TestClient(service.app, headers=SHELL).post(
                endpoint,
                json={
                    "conversation_id": endpoint,
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )
            assert response.status_code == 200, response.text
            assert "event: done" in response.text
            assert state.paths.count(MANIFEST) == 1
            assert state.paths.count(VALIDATE) == 1
            assert state.paths[-1] == VALIDATE
        assert len(constructed) == 1
    finally:
        client.close()
        log.close()
