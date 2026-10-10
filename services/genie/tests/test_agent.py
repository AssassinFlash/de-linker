"""The per-turn tool budget, the model default, and the runner's refusal."""

from typing import Any

import pytest

from linker_genie.abilities import AbilityClient
from linker_genie.agent import (
    MAX_TOOL_CALLS,
    ToolBudget,
    _ability_runner,
    model_name,
    provider_name,
)
from linker_genie.facts import Fact, TurnFacts


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
            self, name: str, arguments: dict[str, Any] | None
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


def test_budget_facts_merge_the_parts_of_all_calls() -> None:
    budget = ToolBudget()
    for index in range(3):
        part = TurnFacts()
        part.product_ids = {4100 + index}
        budget.parts.append(part)

    merged = budget.facts()

    assert merged.product_ids == {4100, 4101, 4102}


def test_real_client_sends_no_token() -> None:
    client = AbilityClient("http://127.0.0.1:9")
    try:
        assert client._client.headers.get("authorization") is None
    finally:
        client.close()
