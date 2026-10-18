"""The in-conversation inquiry card (#250): the offer, and the refusal of a claim.

The card's write path is the shell's route on a real instance
(plugins/linker-commerce/tests/php/Integration/GenieInquiryTest.php); here the
service side is settled: which customer messages ask for the card, when the
service adds its action itself, and that no model sentence can say an inquiry was
sent.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import SHELL
from fastapi.testclient import TestClient

import linker_genie.app as app_module
from linker_genie.app import app
from linker_genie.facts import Fact, TurnFacts
from linker_genie.ground import check
from linker_genie.inquiry import ACTION, decide, requests_inquiry
from linker_genie.log import TurnLog
from linker_genie.schema import CardsBlock, TextBlock, TurnOutput, TurnRequest
from linker_genie.understand import nothing


@pytest.fixture(autouse=True)
def no_understanding() -> Any:
    """The turn tests inject the generator; the understanding layer has its own
    tests (test_understand.py), so these never reach the Store API or Jev."""
    app.state.prepare = nothing
    yield
    del app.state.prepare


@pytest.fixture()
def log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """A turn log in a temp dir, so tests never touch the real cache."""
    log = TurnLog(tmp_path / "turns.sqlite")
    monkeypatch.setattr(app_module, "_log", log)
    yield log
    log.close()


@pytest.mark.parametrize(
    "message",
    [
        # The ways a customer asks for it, EN.
        "Please send an inquiry for these two.",
        "Can you send my inquiry now?",
        "Submit the inquiry.",
        "I would like to send an inquiry.",
        "I'd like to place an inquiry for 4 units.",
        "Please request a quote.",
        "Let's go ahead with the inquiry.",
        "Send it as an inquiry.",
        "Please send me a quote for the H2-10K-T3.",
        "Send us a proforma.",
        "Can you prepare a request for quotation?",
        # German, Sie form and the common word orders.
        "Bitte senden Sie eine Anfrage.",
        "Bitte senden Sie mir ein Angebot.",
        "Ich möchte eine Anfrage senden.",
        "Ich würde gern ein Angebot anfragen.",
        "Anfrage bitte abschicken.",
        "Bitte eine Anfrage absenden.",
        "Können Sie ein Angebot einholen?",
        "Bitte Angebot erstellen.",
        "Ich hätte gern ein Angebot für diese Anlage.",
        "ANFRAGE SENDEN",
        # A negation in an earlier sentence does not reach the request.
        "That did not help. Please send an inquiry.",
    ],
)
def test_an_explicit_request_to_send_an_inquiry_is_matched(message: str) -> None:
    assert requests_inquiry(message)


@pytest.mark.parametrize(
    "message",
    [
        # The status question is the inquiry route's, not the card's.
        "Where is my inquiry?",
        "What is the status of my inquiry?",
        "Wo steht meine Anfrage?",
        "Wie ist der Status meiner Anfrage?",
        # Ordinary product talk.
        "Which battery fits the H2-10K-T3?",
        "Send me the datasheet.",
        "Please send the manual.",
        "Send me the documents for this inverter.",
        "I received an inquiry from my customer.",
        # Negations and hypotheticals.
        "I do not want to send an inquiry.",
        "Ich möchte keine Anfrage senden.",
        "Don't send an inquiry yet.",
        "Should I send an inquiry?",
        "What happens after I send an inquiry?",
        # Requests for a person stay with the contact card.
        "Can I talk to a person?",
    ],
)
def test_ordinary_questions_do_not_request_the_card(message: str) -> None:
    assert not requests_inquiry(message)


def test_the_service_adds_the_action_when_the_model_did_not() -> None:
    blocks: list[dict[str, Any]] = [{"type": "text", "text": "These fit.", "refs": []}]
    assert decide("Please send an inquiry.", blocks)
    # The model's own action is not doubled.
    assert not decide(
        "Please send an inquiry.",
        blocks + [{"type": "action", "name": ACTION, "args": {}}],
    )
    # A handoff answer is the team's sentence and nothing else.
    assert not decide(
        "Please send an inquiry.",
        blocks + [{"type": "handoff", "summary": "mailbox"}],
    )
    # No request, no action.
    assert not decide("Which battery fits?", blocks)


def test_a_turn_that_claims_an_inquiry_was_sent_is_refused() -> None:
    for text in (
        "I have sent your inquiry to the team.",
        "Your inquiry has been sent.",
        "I've submitted the inquiry.",
        "Ich habe Ihre Anfrage gesendet.",
        "Die Anfrage wurde gesendet.",
        "Ihre Anfrage ist gesendet worden.",
    ):
        output = TurnOutput(language="en", blocks=[TextBlock(text=text, refs=[])])
        result = check(output, TurnFacts())
        assert not result.ok
        assert any("Send button" in failure for failure in result.failures), text
    # An ordinary sentence about a document is not a claim about an inquiry.
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="I sent you the datasheet.", refs=[])],
    )
    assert check(output, TurnFacts()).ok


def _generate_claiming_sent(
    request: TurnRequest, retry: str | None
) -> tuple[TurnOutput, TurnFacts]:
    facts = TurnFacts()
    facts.product_ids = {4107}
    facts.qualified_ids = {4107}
    facts.add(Fact(id="p4107.ac_power_kw", value="10", source="selection-facts"))
    return (
        TurnOutput(
            language=request.locale,
            blocks=[
                TextBlock(
                    text="I have sent your inquiry. It has {fact:p4107.ac_power_kw} kW.",
                    refs=["4107"],
                ),
                CardsBlock(product_ids=[4107]),
            ],
        ),
        facts,
    )


def _generate_offering(
    request: TurnRequest, retry: str | None
) -> tuple[TurnOutput, TurnFacts]:
    facts = TurnFacts()
    facts.product_ids = {4107}
    facts.qualified_ids = {4107}
    return (
        TurnOutput(
            language=request.locale,
            blocks=[
                TextBlock(text="These two fit.", refs=["4107"]),
                CardsBlock(product_ids=[4107]),
            ],
        ),
        facts,
    )


def _blocks(body: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for event in body.split("\n\n"):
        if "event: block" in event:
            for line in event.splitlines():
                if line.startswith("data: "):
                    blocks.append(json.loads(line[len("data: ") :]))
    return blocks


def test_the_stream_carries_no_claim_and_the_fallback_is_grounded(log: Any) -> None:
    app.state.generate = _generate_claiming_sent
    response = TestClient(app, headers=SHELL).post(
        "/assistant/turn",
        json={
            "conversation_id": "c250-claim",
            "messages": [{"role": "user", "content": "Please send an inquiry."}],
            "locale": "en",
        },
    )
    assert response.status_code == 200
    assert "I have sent your inquiry" not in response.text


def test_an_explicit_request_ships_the_action(log: Any) -> None:
    app.state.generate = _generate_offering
    response = TestClient(app, headers=SHELL).post(
        "/assistant/turn",
        json={
            "conversation_id": "c250-offer",
            "messages": [{"role": "user", "content": "Please send an inquiry."}],
            "locale": "en",
        },
    )
    assert response.status_code == 200
    assert {
        "type": "action",
        "name": ACTION,
        "args": {},
    } in _blocks(response.text)
