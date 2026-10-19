"""The per-turn tool budget, the model default, and the runner's refusal."""

from typing import Any

import pytest

from linker_genie.abilities import AbilityClient
from linker_genie.agent import (
    MAX_TOOL_CALLS,
    ToolBudget,
    _ability_runner,
    _knowledge_runner,
    _page_runner,
    _user_prompt,
    instructions,
    model_name,
    provider_name,
)
from linker_genie.facts import Fact, TurnFacts
from linker_genie.schema import TurnMessage, TurnRequest


def test_four_calls_pass_the_fifth_is_refused() -> None:
    budget = ToolBudget()

    allowed = [budget.allow() for _ in range(5)]

    assert allowed == [True, True, True, True, False]
    assert budget.limit == MAX_TOOL_CALLS == 4


def test_the_chat_model_is_deepseek_flash_on_the_official_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GENIE_MODEL", raising=False)

    assert provider_name() == "deepseek"
    assert model_name() == "deepseek-flash"


def test_no_provider_switch_remains(monkeypatch: pytest.MonkeyPatch) -> None:
    # Owner ruling 2026-10-11: Anthropic was withdrawn as a Genie option and
    # the GENIE_PROVIDER switch deleted with it — a stale variable in a
    # serving environment must not bring the old option back.
    monkeypatch.setenv("GENIE_PROVIDER", "anthropic")
    monkeypatch.delenv("GENIE_MODEL", raising=False)

    assert provider_name() == "deepseek"
    assert model_name() == "deepseek-flash"


def test_genie_model_still_overrides_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GENIE_MODEL", "deepseek-reasoner")

    assert model_name() == "deepseek-reasoner"


def test_the_runner_answers_the_fifth_call_with_an_error_object() -> None:
    budget = ToolBudget()
    calls: list[tuple[str, dict[str, Any] | None]] = []

    class RecordingClient:
        def record(
            self,
            name: str,
            arguments: dict[str, Any] | None,
            user_context: str | None = None,
            locale: str = "en",
        ) -> tuple[dict[str, Any], TurnFacts]:
            calls.append((name, arguments))
            facts = TurnFacts()
            facts.add(Fact(id=f"p4107.{name}", value="x", source="test"))
            return {"ok": name}, facts

    runner = _ability_runner(RecordingClient(), budget, "linker/get-product")  # type: ignore[arg-type]

    first = runner({"product_id": 4107})
    while budget.allow():
        pass
    fifth = runner(None)

    assert first == {"ok": "linker/get-product"}
    assert "tool budget 4 exhausted" in fifth.get("error", "")
    assert len(calls) == 1
    assert budget.facts().facts.keys() == {"p4107.linker/get-product"}


def test_the_runner_hands_the_turn_language_to_the_ability_client() -> None:
    """A German turn's facts are collected in German: the pairing conditions
    are bilingual and an English one hydrated into a German answer is the
    R6-de failure (facts.collect; measured 2026-10-11)."""
    seen: list[str] = []

    class RecordingClient:
        def record(
            self,
            name: str,
            arguments: dict[str, Any] | None,
            user_context: str | None = None,
            locale: str = "en",
        ) -> tuple[dict[str, Any], TurnFacts]:
            seen.append(locale)
            return {"ok": name}, TurnFacts()

    budget = ToolBudget()
    runner = _ability_runner(
        RecordingClient(),  # type: ignore[arg-type]
        budget,
        "linker/search-products",
        None,
        "de",
    )
    runner({"lang": "en", "text": "H2"})

    assert seen == ["de"]


def test_the_runner_does_not_let_the_model_pick_the_tool_language() -> None:
    """#374: tool lang and the collect locale are the answer language."""
    seen: list[tuple[dict[str, Any] | None, str]] = []

    class RecordingClient:
        def record(
            self,
            name: str,
            arguments: dict[str, Any] | None,
            user_context: str | None = None,
            locale: str = "en",
        ) -> tuple[dict[str, Any], TurnFacts]:
            seen.append((arguments, locale))
            return {"ok": name}, TurnFacts()

    runner = _ability_runner(
        RecordingClient(),  # type: ignore[arg-type]
        ToolBudget(),
        "linker/get-product",
        None,
        "en",
    )
    runner({"product_id": 4107, "lang": "de"})
    assert seen == [({"product_id": 4107, "lang": "en"}, "en")]

    seen.clear()
    sizing = _ability_runner(
        RecordingClient(),  # type: ignore[arg-type]
        ToolBudget(),
        "linker/size-hint",
        None,
        "de",
        "hello",
    )
    sizing({"lang": "en", "pv_kwp": 10})
    assert seen == [({}, "de")]


def test_budget_facts_merge_the_parts_of_all_calls() -> None:
    budget = ToolBudget()
    for index in range(3):
        part = TurnFacts()
        part.product_ids = {4100 + index}
        budget.parts.append(part)

    merged = budget.facts()

    assert merged.product_ids == {4100, 4101, 4102}


def test_a_runner_times_each_call_on_the_clock() -> None:
    """#336: a tool call the model makes is timed as model.tool.<ability>."""
    from linker_genie.timing import Timing

    class RecordingClient:
        def record(
            self,
            name: str,
            arguments: dict[str, Any] | None,
            user_context: str | None = None,
            locale: str = "en",
        ) -> tuple[dict[str, Any], TurnFacts]:
            return {"ok": name}, TurnFacts()

    clock = Timing()
    runner = _ability_runner(
        RecordingClient(),  # type: ignore[arg-type]
        ToolBudget(),
        "linker/get-product",
        clock=clock,
    )
    runner({"product_id": 4107})
    record = clock.as_log()
    # The ability's own name, the one the turn log's tool_calls carry too.
    assert set(record) == {"model.tool.linker/get-product", "total"}
    assert record["model.tool.linker/get-product"] >= 0


def test_a_runner_without_a_clock_answers_as_before() -> None:
    class RecordingClient:
        def record(
            self,
            name: str,
            arguments: dict[str, Any] | None,
            user_context: str | None = None,
            locale: str = "en",
        ) -> tuple[dict[str, Any], TurnFacts]:
            return {"ok": name}, TurnFacts()

    runner = _ability_runner(
        RecordingClient(),  # type: ignore[arg-type]
        ToolBudget(),
        "linker/get-product",
    )
    assert runner({"product_id": 4107}) == {"ok": "linker/get-product"}


def test_a_refused_tool_call_is_absent_from_the_record_not_timed() -> None:
    """#336 review: skipped is not fast — a call the budget refused never enters
    its phase, so it cannot read as an instant tool call."""
    from linker_genie.timing import Timing

    class RecordingClient:
        def record(
            self,
            name: str,
            arguments: dict[str, Any] | None,
            user_context: str | None = None,
            locale: str = "en",
        ) -> tuple[dict[str, Any], TurnFacts]:
            return {"ok": name}, TurnFacts()

    clock = Timing()
    budget = ToolBudget()
    runner = _ability_runner(
        RecordingClient(),  # type: ignore[arg-type]
        budget,
        "linker/get-product",
        clock=clock,
    )
    while budget.allow():
        pass
    assert "budget 4 exhausted" in runner({"product_id": 4107})["error"]
    assert "model.tool.linker/get-product" not in clock.as_log()


def test_a_page_read_without_a_reader_is_absent_from_the_record() -> None:
    """The other refusal guard (#336 review): no page reader, no phase."""
    from linker_genie.timing import Timing

    clock = Timing()
    runner = _page_runner(
        None,
        ToolBudget(),
        TurnRequest(
            conversation_id="c",
            messages=[TurnMessage(role="user", content="what does this page say?")],
        ),
        clock=clock,
    )
    assert "cannot be read" in runner(None)["error"]
    assert "model.tool.linker/read-page" not in clock.as_log()


def test_the_prompt_tells_a_guest_inquiry_to_ask_for_a_login() -> None:
    """C2-anon-de: both prompts and the per-turn reminder name the login
    placeholder. The service fills the sentence in the answer language."""
    from linker_genie.template import HANDOFF_PLACEHOLDER, LOGIN_PLACEHOLDER

    for locale in ("en", "de"):
        prompt = instructions(locale)
        assert LOGIN_PLACEHOLDER in prompt
        assert HANDOFF_PLACEHOLDER in prompt
        assert "{fact:handoff.sentence_en}" not in prompt
        assert "{fact:handoff.sentence_de}" not in prompt
    german = instructions("de")
    assert "login_required" in german
    assert "handoff-team dafür nicht" in german

    request = TurnRequest(
        conversation_id="c-guest",
        locale="de",
        messages=[TurnMessage(role="user", content="Wo steht meine Proforma?")],
        user={"logged_in": False},  # type: ignore[arg-type]
    )
    reminder = _user_prompt(request, None)
    assert "logged_in=False" in reminder
    assert "login_required" in reminder
    assert LOGIN_PLACEHOLDER in reminder
    assert HANDOFF_PLACEHOLDER in reminder
    assert "{fact:handoff.sentence_en}" not in reminder
    assert "{fact:handoff.sentence_de}" not in reminder
    assert "do not call handoff-team" in reminder


def test_real_client_sends_no_token() -> None:
    client = AbilityClient("http://127.0.0.1:9")
    try:
        assert client._client.headers.get("authorization") is None
    finally:
        client.close()


def test_the_prompt_lists_the_document_refs_the_route_fetched() -> None:
    from linker_genie.agent import _user_prompt
    from linker_genie.facts import Document, TurnFacts
    from linker_genie.route import Route
    from linker_genie.schema import TurnRequest
    from linker_genie.understand import Prepared

    facts = TurnFacts()
    facts.documents["p4106.document.0"] = Document(
        "https://de-linker.test/a.pdf", "SAJ CHS2 Datasheet", None
    )
    prepared = Prepared(route=Route("documents"), facts=facts)
    request = TurnRequest.model_validate(
        {"conversation_id": "c", "messages": [{"role": "user", "content": "CB2?"}]}
    )
    prompt = _user_prompt(request, None, prepared)
    assert (
        "Document refs you may link, and no others: p4106.document.0 = SAJ CHS2 Datasheet"
        in prompt
    )


def test_the_knowledge_runner_records_the_ranking_and_hands_the_model_its_view() -> (
    None
):
    from linker_genie.agent import _knowledge_runner

    def search(arguments: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "ranking": "vector",
            "encoder": "google/gemini-embedding-2",
            "index_version": "v1",
            "hits": [
                {
                    "chunk_id": "c1",
                    "doc_url": "https://de-linker.com/x.pdf",
                    "title": "Manual",
                    "page": 2,
                    "section": "",
                    "text": "[n1=3] MPPT",
                    "figures": {"c1.n1": "3"},
                }
            ],
        }

    budget = ToolBudget()
    runner = _knowledge_runner(search, budget, "en")

    seen = runner({"query": "MPPT", "lang": "en"})

    assert "doc_url" not in seen["hits"][0] and "figures" not in seen["hits"][0]
    facts = budget.facts()
    assert facts.facts["c1.n1"].value == "3"
    assert facts.tool_calls == [
        {
            "name": "linker/search-knowledge",
            "arguments": {"query": "MPPT", "lang": "en"},
            "ok": True,
            "ranking": "vector",
            "encoder": "google/gemini-embedding-2",
            "index_version": "v1",
            "result": search({}),
        }
    ]


def _document_payload() -> dict[str, Any]:
    return {
        "ranking": "vector",
        "hits": [
            {
                "chunk_id": "c1",
                "title": "M",
                "page": 2,
                "doc_url": "https://de-linker.com/m.pdf",
                "section": "",
                "text": "[n1=3] MPPT",
                "figures": {"c1.n1": "3"},
            }
        ],
    }


def test_a_routed_document_search_reads_like_the_models_own_call() -> None:
    from linker_genie.route import Call, Route
    from linker_genie.understand import Prepared

    arguments = {"query": "How many MPPT?", "lang": "en"}
    prepared = Prepared(
        route=Route("documents", calls=(Call("linker/search-knowledge", arguments),)),
        results=[
            {
                "name": "linker/search-knowledge",
                "arguments": arguments,
                "result": _document_payload(),
            }
        ],
    )
    request = TurnRequest(
        conversation_id="c",
        messages=[TurnMessage(role="user", content="How many MPPT?")],
    )

    prompt = _user_prompt(request, None, prepared)

    assert '"text": "[n1=3] MPPT"' in prompt
    assert "doc_url" not in prompt and '"figures"' not in prompt


def test_a_model_ability_failure_is_recorded_and_still_raises() -> None:
    """The 500 reaches `call_failures` before pydantic-ai sees the raise."""
    from linker_genie.abilities import AbilityError
    from linker_genie.route import Route
    from linker_genie.understand import Prepared

    prepared = Prepared(route=Route("model"))

    class Dying:
        def record(
            self,
            name: str,
            arguments: dict[str, Any] | None,
            user_context: str | None = None,
            locale: str = "en",
        ) -> tuple[dict[str, Any], TurnFacts]:
            raise AbilityError(f"{name} returned 500 for {{}}", fatal=True)

    runner = _ability_runner(
        Dying(),  # type: ignore[arg-type]
        ToolBudget(),
        "linker/search-products",
        prepared=prepared,
    )
    with pytest.raises(AbilityError, match="returned 500"):
        runner({"series": "saj-h2"})
    assert prepared.log["call_failures"] == [
        {
            "text": "linker/search-products: linker/search-products returned 500 for {}",
            "kind": "ability",
        }
    ]


def test_a_model_encoder_failure_is_recorded_and_still_raises() -> None:
    from linker_genie.embedding import EmbeddingError
    from linker_genie.route import Route
    from linker_genie.understand import Prepared

    prepared = Prepared(route=Route("model"))

    def search(_arguments: dict[str, Any] | None) -> dict[str, Any]:
        raise EmbeddingError("gemini-embedding-2: HTTP 502 on attempt 2 of 2")

    runner = _knowledge_runner(search, ToolBudget(), prepared=prepared)
    with pytest.raises(EmbeddingError, match="HTTP 502 on attempt 2 of 2"):
        runner({"query": "MPPT"})
    assert prepared.log["call_failures"] == [
        {
            "text": "linker/search-knowledge: gemini-embedding-2: HTTP 502 on attempt 2 of 2",
            "kind": "retrieval",
        }
    ]

    def url_error(_arguments: dict[str, Any] | None) -> dict[str, Any]:
        raise EmbeddingError("gemini-embedding-2: URLError after 2 attempts: timed out")

    again = Prepared(route=Route("model"))
    runner = _knowledge_runner(url_error, ToolBudget(), prepared=again)
    with pytest.raises(EmbeddingError, match="URLError after 2 attempts"):
        runner({"query": "MPPT"})
    assert again.log["call_failures"] == [
        {
            "text": (
                "linker/search-knowledge: gemini-embedding-2: "
                "URLError after 2 attempts: timed out"
            ),
            "kind": "retrieval",
        }
    ]


def test_a_failed_routed_document_search_ends_the_generation() -> None:
    from linker_genie.agent import make_generate
    from linker_genie.knowledge import KnowledgeUnavailable
    from linker_genie.route import Route
    from linker_genie.understand import Prepared

    prepared = Prepared(
        route=Route("documents"),
        knowledge_error="linker/search-knowledge: gemini: HTTP 401 on attempt 1 of 2",
    )
    generate = make_generate(
        AbilityClient("http://127.0.0.1:9"), model=object(), prepared=prepared
    )
    request = TurnRequest(
        conversation_id="c", messages=[TurnMessage(role="user", content="MPPT?")]
    )

    with pytest.raises(KnowledgeUnavailable, match="HTTP 401"):
        generate(request, None)


def test_the_route_runs_the_document_search_in_process() -> None:
    from linker_genie.embedding import EmbeddingError
    from linker_genie.route import Call, Route
    from linker_genie.understand import Prepared, _run_calls

    class NoWordPress:
        def record(self, *args: Any, **kwargs: Any) -> Any:
            raise AssertionError("the document search is not a WordPress ability")

    arguments = {"query": "MPPT", "lang": "en"}
    route = Route("documents", calls=(Call("linker/search-knowledge", arguments),))
    request = TurnRequest(
        conversation_id="c", messages=[TurnMessage(role="user", content="MPPT")]
    )

    prepared = Prepared(route=route)
    _run_calls(prepared, request, NoWordPress(), lambda _: _document_payload())  # type: ignore[arg-type]

    assert prepared.facts.facts["c1.n1"].value == "3"
    assert prepared.facts.tool_calls[0]["ranking"] == "vector"
    assert prepared.results[0]["result"]["hits"][0]["doc_url"].endswith("m.pdf")
    assert prepared.knowledge_error is None

    def broken(_: Any) -> dict[str, Any]:
        raise EmbeddingError("gemini: URLError after 2 attempts")

    failed = Prepared(route=route)
    _run_calls(failed, request, NoWordPress(), broken)  # type: ignore[arg-type]

    assert failed.knowledge_error == (
        "linker/search-knowledge: gemini: URLError after 2 attempts"
    )
    assert failed.log["call_failures"] == [
        {
            "text": "linker/search-knowledge: gemini: URLError after 2 attempts",
            "kind": "retrieval",
        }
    ]
    assert failed.results == []
