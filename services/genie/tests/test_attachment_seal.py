"""A grounded attachment figure survives the final numeric seal.

The recorded reading is real; the model drafts are synthetic correct answers.
The original provider draft was not captured. No provider runs in these tests.
"""

import json
from pathlib import Path

import pytest

from linker_genie.attachments import record
from linker_genie.cycle import run
from linker_genie.facts import Fact, TurnFacts
from linker_genie.ground import check
from linker_genie.hydrate import hydrate
from linker_genie.route import Route
from linker_genie.schema import (
    AttachmentReading,
    HandoffBlock,
    Locale,
    PageContext,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import seal

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/539/attachment-report.json").read_text()
)


def _facts(language: str = "en") -> TurnFacts:
    reading = AttachmentReading.model_validate(FIXTURE["reading"])
    return record(reading, language)[1]


def _prose(output: TurnOutput) -> str:
    return "\n".join(b.text for b in output.blocks if isinstance(b, TextBlock))


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("page_type", [None, "other"])
def test_cited_report_figures_survive_the_real_cycle(
    language: Locale, page_type: str | None
) -> None:
    facts = _facts(language)
    draft = TurnOutput(
        language=language,
        blocks=[
            TextBlock(
                text=(
                    "File: fresh-guest-report-50667-en.pdf. "
                    "Report created: {fact:att1.n2} "
                    "{fact:att1.n3}:{fact:att1.n4}:{fact:att1.n5} UTC; "
                    "annual consumption: {fact:att1.n9}; "
                    "PV array: {fact:att1.n10}; "
                    "grid: three-phase; page {fact:att1.n1}."
                    if language == "en"
                    else "Datei: fresh-guest-report-50667-en.pdf. "
                    "Bericht erstellt: {fact:att1.n2} "
                    "{fact:att1.n3}:{fact:att1.n4}:{fact:att1.n5} UTC; "
                    "Jahresverbrauch: {fact:att1.n9}; "
                    "PV-Anlage: {fact:att1.n10}; "
                    "Netzanschluss: dreiphasig; Seite {fact:att1.n1}."
                ),
                refs=["att1"],
            )
        ],
    )
    question = (
        FIXTURE["question"]
        if language == "en"
        else "Lesen Sie aus der beigefügten PDF den Erstellungszeitpunkt, "
        "Jahresverbrauch, die PV-Leistung und den Netzanschluss. "
        "Nennen Sie den Dateinamen und die Seite."
    )
    request = TurnRequest(
        conversation_id="offline-attachment-report",
        locale=language,
        messages=[TurnMessage(role="user", content=question)],
        page_context=PageContext() if page_type is None else PageContext(type="other"),
    )
    assert check(draft, facts, Route("model")).ok
    expected = _prose(hydrate(draft, facts))
    assert "2026-10-23 10:31:13" in expected
    assert "10 kWp" in expected
    result = run(request, lambda _request, _retry: (draft, facts), Route("model"))
    assert result.grounded and not result.fallback
    assert result.attempts == 1
    assert result.failures == ()
    assert _prose(result.output) == expected


@pytest.mark.parametrize("ref", ["att1", "att1.n9"])
def test_only_the_block_citing_the_reading_gets_its_allowance(ref: str) -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Consumption: 4,500 kWh.", refs=[ref]),
            TextBlock(text="Unrelated consumption: 4,500 kWh."),
        ],
    )
    result = seal(output, _facts(), Route("model"), "Read my report.", None)
    cited, unrelated = result.blocks
    assert isinstance(cited, TextBlock)
    assert isinstance(unrelated, TextBlock)
    assert "4,500" in cited.text
    assert "4,500" not in unrelated.text


def test_a_figure_ref_does_not_license_other_figures_of_that_file() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Consumption 4,500 kWh; array 10 kWp.", refs=["att1.n9"])
        ],
    )
    result = _prose(seal(output, _facts(), Route("model"), "Read my report.", None))
    assert "4,500" in result
    assert "10 kWp" not in result


@pytest.mark.parametrize("ref", ["att2", "att999", "att1.text"])
def test_another_or_missing_reading_does_not_license_these_figures(ref: str) -> None:
    facts = _facts()
    facts.add(Fact("att2", "other.pdf", "read-attachment"))
    facts.add(Fact("att2.n1", "42 kWh", "read-attachment"))
    output = TurnOutput(
        language="en", blocks=[TextBlock(text="Consumption 4,500 kWh.", refs=[ref])]
    )
    assert "4,500" not in _prose(
        seal(output, facts, Route("model"), "Read my report.", None)
    )


def test_a_filename_or_other_source_is_not_an_attachment_figure() -> None:
    facts = TurnFacts()
    facts.add(Fact("att1", "report-4500.pdf", "read-attachment"))
    facts.add(Fact("att1.n1", "4500 kWh", "selection-facts"))
    output = TurnOutput(
        language="en", blocks=[TextBlock(text="Consumption 4500 kWh.", refs=["att1"])]
    )
    assert "4500" not in _prose(
        seal(output, facts, Route("model"), "Read my report.", None)
    )


def test_a_handoff_does_not_borrow_the_other_blocks_reading() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Array 10 kWp.", refs=["att1"]),
            HandoffBlock(summary="A different request for 4500 kWh."),
        ],
    )
    result = seal(output, _facts(), Route("model"), "Read my report.", None)
    cited, handoff = result.blocks
    assert isinstance(cited, TextBlock)
    assert isinstance(handoff, HandoffBlock)
    assert "10 kWp" in cited.text
    assert "4500" not in handoff.summary


@pytest.mark.parametrize(
    ("text", "failure"),
    [
        ("Array {fact:att1.n999}", "not in this turn's tools"),
        ("Array 9999999 kWp", "model text contains numbers"),
    ],
)
def test_attachment_presence_does_not_bypass_grounding(text: str, failure: str) -> None:
    output = TurnOutput(language="en", blocks=[TextBlock(text=text, refs=["att1"])])
    result = check(output, _facts(), Route("model"))
    assert not result.ok
    assert any(failure in item for item in result.failures)


def test_an_attachment_amount_is_still_rejected_before_sealing() -> None:
    _, facts = record(
        AttachmentReading(id="att1", name="quote.pdf", kind="document", text="99 EUR")
    )
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="Your file lists {fact:att1.n1}.", refs=["att1"])],
    )
    result = check(output, facts, Route("model"))
    assert not result.ok
    assert any("amount of money" in item for item in result.failures)


def test_clearance_and_documents_keep_their_existing_numeric_rules() -> None:
    output = TurnOutput(
        language="en", blocks=[TextBlock(text="Array 10 kWp.", refs=["att1"])]
    )
    facts = _facts()
    clearance = seal(output, facts, Route("model"), "What minimum clearance?", None)
    assert "10 kWp" not in _prose(clearance)
    documents = seal(output, facts, Route("documents"), "Read my report.", None)
    assert _prose(documents) == _prose(output)
    no_reading = seal(output, TurnFacts(), Route("model"), "Read my report.", None)
    assert "10 kWp" not in _prose(no_reading)
