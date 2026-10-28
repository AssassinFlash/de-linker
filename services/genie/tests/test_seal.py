"""Unlicensed bare numbers are stripped, and the required sentence is written (#439).

The baseline grader is the acceptance check. A minimal fixture may still miss a
product card or a price line; the assertions name the failure this ticket
removes. A fully built b15-de and b19 turn must come back with no failures.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from baseline.grade import Turn, answer_text, check, untraceable_numbers

from linker_genie.cycle import run
from linker_genie.facts import Fact, Qualification, TurnFacts, collect, merge
from linker_genie.figures import tag
from linker_genie.ground import (
    blob_has_figure,
    cites_outside_turn,
    drop_bare_numbers,
    rebind_figures_past_decimal,
    strip_detached_code_tails,
    strip_unlicensed_numbers,
)
from linker_genie.ground import (
    check as ground_check,
)
from linker_genie.language import language_failure
from linker_genie.route import NamedModel, Route
from linker_genie.schema import (
    ActionBlock,
    AskBlock,
    CardsBlock,
    DocumentBlock,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import finish, seal

SET = Path(__file__).parents[1] / "eval" / "baseline" / "baseline100.jsonl"
ROWS = {
    row["id"]: row
    for row in (json.loads(line) for line in SET.read_text().splitlines() if line)
}
_MANIFEST = json.loads(
    (Path(__file__).parent / "fixtures" / "339" / "manifest.json").read_text(
        encoding="utf-8"
    )
)
DOC = "Clearances ≥1500/400/500/1000/500 mm. Drill bit: Φ10."


def _facts(value: str = "") -> TurnFacts:
    gathered = TurnFacts()
    gathered.product_ids = {4107}
    gathered.qualified_ids = {4107}
    if value:
        gathered.add(Fact(id="c1.text", value=value, source="search-knowledge"))
        gathered.knowledge_products["c1"] = (4107,)
    return gathered


def _text(output: TurnOutput) -> str:
    block = output.blocks[0]
    assert isinstance(block, TextBlock)
    return block.text


def _graded(output: TurnOutput, language: str) -> Turn:
    blocks = output.model_dump()["blocks"]
    assert isinstance(blocks, list)
    return Turn(
        meta={"grounded": True, "fallback": False, "language": language},
        blocks=blocks,
        done=True,
    )


def _grade(row_id: str, output: TurnOutput) -> list[str]:
    row = ROWS[row_id]
    return check(row, _graded(output, str(row["lang"])))


def test_339_names_the_unbound_number_case() -> None:
    case = next(
        item for item in _MANIFEST["cases"] if item["id"] == "439-unbound-numbers"
    )
    assert case["issue"] == 439
    assert case["locales"] == ["en", "de"]


def test_a_newline_around_a_dropped_number_stays_a_newline() -> None:
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="line one\n10 kW\nline two")],
    )
    assert _text(strip_unlicensed_numbers(output, None)) == "line one\nline two"


def test_a_dropped_series_digit_does_not_glue_the_next_word() -> None:
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="The EcoFlow OCEAN 2 is here.")],
    )
    assert _text(strip_unlicensed_numbers(output, None)) == "The EcoFlow OCEAN is here."


def test_phi_ten_is_a_bare_number_and_does_not_select_the_degraded_sentence() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="The drill bit is Φ10.", refs=["4107"]),
            CardsBlock(product_ids=[4107]),
        ],
    )
    result = ground_check(output, _facts())
    assert result.unbound_only
    assert result.failures == ("model text contains numbers ['10']",)
    assert cites_outside_turn(result.citations) is False
    assert blob_has_figure("Drill bit: Φ10.", 10) is False


def test_a_phase_phrase_survives_a_full_strip_and_the_grader_still_flags_it() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="This inverter is 3-phase and 1-phase.", refs=["4107"]),
            CardsBlock(product_ids=[4107]),
        ],
    )
    assert ground_check(output, _facts()).ok
    stripped = strip_unlicensed_numbers(output, None)
    assert _text(stripped) == "This inverter is 3-phase and 1-phase."
    assert untraceable_numbers("3-phase and 1-phase", ["3"], None) == ["1"]


def test_a_product_answer_keeps_only_the_question_number() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="The EcoFlow OCEAN 2 is 15 kW with 30 kW PV input.",
                refs=["4107"],
            ),
            CardsBlock(product_ids=[4107]),
        ],
    )
    sealed = seal(
        output,
        _facts(),
        Route("products"),
        str(ROWS["b03-en"]["question"]),
        "other",
    )
    text = _text(sealed)
    assert "OCEAN is 15 kW" in text
    assert "30" not in text
    assert "2" not in text.split()
    assert "number 2 is in no expected fact" not in _grade("b03-en", sealed)
    assert "number 2 is in no expected fact" not in _grade("b03-de", sealed)


def test_a_documents_power_answer_is_not_cut_back_to_the_question() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="The single-phase models are 3.68 kW. The three-phase models are 10 kW."
            ),
            DocumentBlock(ref="c1"),
        ],
    )
    sealed = seal(
        output,
        _facts(),
        Route("documents"),
        str(ROWS["b02-en"]["question"]),
        "other",
    )
    assert _text(sealed) == _text(output)


def test_clearance_appends_only_a_figure_the_documents_contain() -> None:
    output = TurnOutput(
        language="de",
        blocks=[
            TextBlock(
                text="Abstände 1500 mm, 400 mm und 500 mm. Bohrhammer mit Bohrer 10."
            ),
            DocumentBlock(ref="c1"),
        ],
    )
    sealed = seal(
        output,
        _scoped_hit("c1", 4107, DOC),
        Route("documents"),
        str(ROWS["b15-de"]["question"]),
        "other",
    )
    text = _text(sealed)
    assert "1000 mm" in text
    assert "Bohrer 10" not in text
    assert "Φ10" not in text
    assert any(block.type == "document" for block in sealed.blocks)
    assert _grade("b15-de", sealed) == []

    invented = seal(
        output,
        _scoped_hit("c1", 4107, "Clearances 1500 mm and 400 mm."),
        Route("documents"),
        str(ROWS["b15-de"]["question"]),
        "other",
    )
    assert "1000" not in _text(invented)


def test_a_clearance_answer_drops_datasheet_energy() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "Rated energy 100.3 kWh, usable energy 90.2 kWh, "
                    "rated power 50.1 kW. Torque 47. The floor carries 1.5 tons."
                )
            ),
            DocumentBlock(ref="c1"),
        ],
    )
    blob = (
        "Clearances 1500 mm, 1000 mm, 500 mm and 400 mm. "
        "Rated energy 100.3 kWh. Usable energy 90.2 kWh. Rated power 50.1 kW. "
        "Torque 47. Load 1.5 tons."
    )
    sealed = seal(
        output,
        _scoped_hit("c1", 4107, blob),
        Route("documents"),
        str(ROWS["b15-en"]["question"]),
        "other",
    )
    text = _text(sealed)
    assert "100.3" not in text
    assert "90.2" not in text
    assert "50.1" not in text
    assert "47" in text
    assert "1.5" in text
    assert "1000 mm" in text
    assert _grade("b15-en", sealed) == []


def test_an_install_question_does_not_grow_a_clearance_sentence() -> None:
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="The team handles installation.")],
    )
    question = str(ROWS["b40-en"]["question"])
    for route in (Route("products"), Route("documents")):
        sealed = seal(output, _facts(DOC), route, question, "other")
        assert "mm" not in _text(sealed)
        assert "clearance" not in _text(sealed).casefold()


def test_usable_capacity_absence_is_its_own_sentence() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "The nominal capacity is 260 kWh. "
                    "The depth of discharge is 98%. "
                    "The usable figure is not printed."
                )
            ),
            DocumentBlock(ref="c1"),
        ],
    )
    sealed = seal(
        output,
        _facts("Nominal 260 kWh. Depth of discharge 98%."),
        Route("documents"),
        str(ROWS["b20-en"]["question"]),
        "other",
    )
    text = _text(sealed)
    assert text.count("The documents do not state a usable capacity.") == 1
    assert "5–95" not in text
    assert "missing /" not in " ".join(
        item for item in _grade("b20-en", sealed) if "do not state" in item
    )
    assert not any("banned figure" in item for item in _grade("b20-en", sealed))


def test_a_german_usable_paraphrase_that_already_matches_is_not_repeated() -> None:
    output = TurnOutput(
        language="de",
        blocks=[
            TextBlock(
                text=(
                    "Die nutzbare Kapazität ist nicht angegeben. "
                    "Die Nennkapazität beträgt 260 kWh. "
                    "Die Entladetiefe beträgt 98 %."
                )
            )
        ],
    )
    sealed = seal(
        output,
        _facts("Nennkapazität 260 kWh. Entladetiefe 98 %."),
        Route("documents"),
        str(ROWS["b20-de"]["question"]),
        "other",
    )
    assert "nennen keine nutzbare" not in _text(sealed).casefold()
    assert "260 kWh" in _text(sealed)


def test_a_model_code_does_not_invent_a_usable_figure() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="The documents discuss this battery."),
            DocumentBlock(ref="c1"),
        ],
    )
    blob = "Model L260 Omni. Usable capacity is not stated."
    assert blob_has_figure(blob, 260) is False
    sealed = seal(
        output,
        _facts(blob),
        Route("documents"),
        str(ROWS["b20-en"]["question"]),
        "other",
    )
    assert "260 kWh" not in _text(sealed)
    assert "The documents do not state a usable capacity." in _text(sealed)


def _scoped_hit(
    chunk: str, product: int, text: str, *, url: str = "https://example.test/data.pdf"
) -> TurnFacts:
    tagged = tag(chunk, text)
    return collect(
        "linker/search-knowledge",
        {
            "hits": [
                {
                    "chunk_id": chunk,
                    "doc_url": url,
                    "title": "Sample data",
                    "page": 2,
                    "product_ids": [product],
                    "text": tagged.text,
                    "figures": tagged.figures,
                }
            ]
        },
    )


def test_clearance_completion_binds_the_value_to_the_property() -> None:
    facts = _scoped_hit("a", 1, "Minimum clearance 500 mm; enclosure height 1500 mm.")
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="See the installation guide.", refs=["a"])],
    )

    sealed = seal(output, facts, Route("documents"), "What minimum clearance?", "other")

    assert "500 mm" in _text(sealed)
    assert "1500 mm" not in _text(sealed)


def test_clearance_completion_does_not_assert_a_negated_value() -> None:
    facts = _scoped_hit("a", 1, "The clearance is not 500 mm; use a minimum of 400 mm.")
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="See the installation guide.", refs=["a"])],
    )

    sealed = seal(output, facts, Route("documents"), "What minimum clearance?", "other")

    assert "500 mm" not in _text(sealed)
    assert "400 mm" in _text(sealed)


def test_clearance_completion_uses_real_figures_and_keeps_conditions() -> None:
    for language, source, question in (
        ("en", "Minimum clearance 725 mm.", "What minimum clearance?"),
        ("de", "Mindestabstand 725 mm.", "Welcher Mindestabstand?"),
        ("en", "| Minimum clearance (mm) | 725 |", "What minimum clearance?"),
    ):
        output = TurnOutput(
            language=language, blocks=[TextBlock(text="Info.", refs=["a"])]
        )
        sealed = seal(
            output, _scoped_hit("a", 1, source), Route("documents"), question, "other"
        )
        assert "725 mm" in _text(sealed)
        assert ("minimum clearance" if language == "en" else "Mindestabstand") in _text(
            sealed
        )

    for source in (
        "Minimum clearance 500 mm when installed outdoors.",
        "Minimum clearance 500 mm; for outdoor use only.",
        "Minimum clearance 500 mm. For outdoor use only.",
        "Minimum clearance 500 mm. This requirement applies only outdoors.",
        "For outdoor use only. Minimum clearance 500 mm.",
        "Outdoor installation. Minimum clearance 500 mm.",
    ):
        output = TurnOutput(
            language="en", blocks=[TextBlock(text="See the guide.", refs=["a"])]
        )
        sealed = seal(
            output,
            _scoped_hit("a", 1, source),
            Route("documents"),
            "What minimum clearance?",
            "other",
        )
        assert "500 mm" not in _text(sealed)

    no_figure = _scoped_hit("a", 1, "Minimum clearance 500 mm.")
    no_figure.facts.pop("a.n1")
    assert "500 mm" not in _text(
        seal(output, no_figure, Route("documents"), "What minimum clearance?", "other")
    )


def test_seal_uses_only_the_cited_model_for_automatic_document_values() -> None:
    first = _scoped_hit("a", 1, "Model A. Nominal capacity is not stated.")
    other = _scoped_hit(
        "b",
        2,
        "| Nominal Capacity (kWh) | 260 |\n| Depth of Discharge | 98% |",
        url="https://example.test/other.pdf",
    )
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="The documents describe model A.", refs=["a"]),
            DocumentBlock(ref="a"),
            DocumentBlock(ref="b"),
        ],
    )

    sealed = seal(
        output,
        merge([first, other]),
        Route("documents"),
        "What is the usable capacity?",
        "other",
    )

    assert "260" not in _text(sealed) and "98%" not in _text(sealed)


def test_seal_still_uses_the_cited_unqualified_source_when_another_hit_is_conditional() -> (
    None
):
    first = _scoped_hit(
        "a", 1, "| Nominal Capacity (kWh) | 260 |\n| Depth of Discharge | 98% |"
    )
    conditional = collect(
        "linker/search-knowledge",
        {
            "hits": [
                {
                    "chunk_id": "b",
                    "doc_url": "https://example.test/other.pdf",
                    "title": "Other model",
                    "page": 2,
                    "product_ids": [2],
                    "text": "| Reading | [n1=5 A] |\n*6: Synthetic condition. (p. 3)",
                    "figures": {"b.n1": "5 A"},
                    "qualification_required": True,
                    "qualifications": [
                        {
                            "chunk_id": "b-p3",
                            "page": 3,
                            "quote": "*6: Synthetic condition.",
                            "lang": "en",
                        }
                    ],
                }
            ]
        },
    )
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="The document describes model A.", refs=["a"]),
            DocumentBlock(ref="a"),
        ],
    )
    facts = merge([first, conditional])

    capacity = seal(
        output, facts, Route("documents"), "What is the usable capacity?", "other"
    )
    support = seal(output, facts, Route("documents"), "Does it support EnWG?", "other")

    assert "260 kWh" in _text(capacity) and "98%" in _text(capacity)
    assert "do not state whether it supports this" in _text(support)


def test_seal_does_not_treat_an_unrelated_same_source_number_as_capacity() -> None:
    facts = _scoped_hit(
        "a",
        1,
        "Nominal voltage 260 V and maximum energy 260 kWh.\n"
        "| Nominal Voltage (V) | 260 |\n"
        "| Maximum Energy (kWh) | 260 |\n"
        "| Usable Capacity (kWh) | 260 |\n"
        "| Round Trip Efficiency | 98% |",
    )
    output = TurnOutput(
        language="en", blocks=[TextBlock(text="See the data.", refs=["a"])]
    )

    sealed = seal(
        output, facts, Route("documents"), "What is usable capacity?", "other"
    )

    assert "260 kWh" not in _text(sealed) and "98%" not in _text(sealed)


def test_a_multi_model_chunk_cannot_be_relabelled_as_one_models_values() -> None:
    facts = _scoped_hit("a", 1, "| Nominal Capacity (kWh) | 260 |")
    facts.knowledge_products["a"] = (1, 2)
    output = TurnOutput(
        language="en", blocks=[TextBlock(text="See the data.", refs=["a"])]
    )
    route = Route(
        "documents", named_models=(NamedModel(code="MODEL-1", product_ids=(1,)),)
    )

    unambiguous = seal(output, facts, route, "What is usable capacity?", "other")
    ambiguous = seal(
        output, facts, Route("documents"), "What is usable capacity?", "other"
    )

    assert "260 kWh" not in _text(unambiguous)
    assert "260 kWh" not in _text(ambiguous)


def test_seal_can_combine_explicitly_cited_chunks_of_the_same_model_and_pdf() -> None:
    first = _scoped_hit("a", 1, "| Nominal Capacity (kWh) | 260 |")
    second = _scoped_hit("b", 1, "| Depth of Discharge | 98% |")
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="See the data."),
            DocumentBlock(ref="a"),
            DocumentBlock(ref="b"),
        ],
    )

    sealed = seal(
        output,
        merge([first, second]),
        Route("documents"),
        "What is the usable capacity?",
        "other",
    )

    assert "260 kWh" in _text(sealed) and "98%" in _text(sealed)


def test_conflicting_or_missing_model_scope_never_licenses_automatic_values() -> None:
    first = _scoped_hit("a", 1, "| Nominal Capacity (kWh) | 260 |")
    conflicting = _scoped_hit("a", 2, "| Nominal Capacity (kWh) | 260 |")
    missing = collect(
        "linker/search-knowledge",
        {"hits": [{"chunk_id": "a", "text": "Nominal capacity 260 kWh."}]},
    )
    output = TurnOutput(
        language="en", blocks=[TextBlock(text="See the data.", refs=["a"])]
    )

    for other in (conflicting, missing):
        facts = merge([first, other])
        sealed = seal(
            output, facts, Route("documents"), "What is usable capacity?", "other"
        )
        assert facts.knowledge_products["a"] == ()
        assert "260 kWh" not in _text(sealed)


def test_support_absence_is_written_once_and_stays_a_denial() -> None:
    present = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="The documents do not state whether it supports this."),
            DocumentBlock(ref="c1"),
        ],
    )
    sealed = seal(
        present,
        _facts(),
        Route("documents"),
        str(ROWS["b25-en"]["question"]),
        "other",
    )
    assert (
        _text(sealed).count("The documents do not state whether it supports this.") == 1
    )
    assert not any("clause asserts" in item for item in _grade("b25-en", sealed))

    missing = TurnOutput(
        language="de",
        blocks=[
            TextBlock(text="Die Unterlagen beschreiben den SAJ H2."),
            DocumentBlock(ref="c1"),
        ],
    )
    added = seal(
        missing,
        _facts(),
        Route("documents"),
        str(ROWS["b25-de"]["question"]),
        "other",
    )
    text = _text(added)
    assert "Die Unterlagen nennen keine Unterstützung." in text
    assert re.search(r"(?i)\bunterstützt\b", text) is None
    assert not any(item.startswith("missing /") for item in _grade("b25-de", added))
    assert not any("clause asserts" in item for item in _grade("b25-de", added))


def test_cited_support_answer_is_not_followed_by_a_false_absence() -> None:
    for language, source, answer, question in (
        (
            "en",
            "The device supports EnWG §14a.",
            "The device supports EnWG §14a.",
            "Does it support EnWG?",
        ),
        (
            "de",
            "Das Gerät unterstützt EnWG §14a.",
            "Das Gerät unterstützt EnWG §14a.",
            "Unterstützt es EnWG?",
        ),
        (
            "en",
            "The device does not support EnWG §14a.",
            "The device does not support EnWG §14a.",
            "Does it support EnWG?",
        ),
        (
            "de",
            "Das Gerät unterstützt EnWG §14a nicht.",
            "Das Gerät unterstützt EnWG §14a nicht.",
            "Unterstützt es EnWG?",
        ),
        (
            "en",
            "EnWG §14a is supported.",
            "The device supports EnWG §14a.",
            "Does it support EnWG?",
        ),
    ):
        facts = _scoped_hit("a", 1, source)
        output = TurnOutput(
            language=language, blocks=[TextBlock(text=answer, refs=["a"])]
        )

        sealed = seal(output, facts, Route("documents"), question, "other")

        assert _text(sealed) == answer

    conditional = _scoped_hit("a", 1, "Supports EnWG §14a with the required interface.")
    conditional.qualifications["a"] = (
        Qualification("*1: The interface is required.", 3, "a-p3", "en"),
    )
    supported = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="The device supports EnWG §14a with the required interface.",
                refs=["a"],
            )
        ],
    )
    assert _text(
        seal(
            supported, conditional, Route("documents"), "Does it support EnWG?", "other"
        )
    ) == _text(supported)


def test_a_product_page_is_not_sealed() -> None:
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="This one has 4 MPPTs.")],
    )
    sealed = seal(
        output,
        _facts(),
        Route("documents"),
        str(ROWS["b46-en"]["question"]),
        "product",
    )
    assert sealed is output


def test_a_stock_beside_answer_keeps_the_figure_the_question_names() -> None:
    output = TurnOutput(
        language="en",
        blocks=[TextBlock(text="Efficiency 97.5 %. In stock.")],
    )
    sealed = seal(
        output,
        _facts(),
        Route("products", stock=True, stock_beside=True),
        "What is the efficiency of the SAJ H2-10K-T3 and is it in stock?",
        "other",
    )
    assert _text(sealed) == "Efficiency 97.5 %. In stock."


def test_a_pairing_answer_with_a_document_is_not_rewritten() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="These inverters are released."),
            DocumentBlock(ref="c1"),
            AskBlock(field="phase", options=["single-phase", "three-phase"]),
        ],
    )
    sealed = seal(
        output, _facts(), Route("pairing"), "10 kWp three-phase home", "other"
    )
    assert _text(sealed) == "These inverters are released."
    assert sealed.blocks[2].type == "ask"


def test_no_route_is_left_alone() -> None:
    output = TurnOutput(language="en", blocks=[TextBlock(text="See the manual.")])
    assert seal(output, _facts(), None, "What minimum clearance?", "other") is output


def test_the_sizing_route_adds_the_application_ask_beside_the_configurator() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="The size depends on the home and the yearly use."),
            ActionBlock(name="open_configurator", args={}),
        ],
    )
    finished = finish(output, TurnFacts(), Route("sizing"))
    asks = [block for block in finished.blocks if isinstance(block, AskBlock)]
    assert len(asks) == 1
    assert asks[0].field == "application"
    assert asks[0].options == ["home", "commercial"]
    assert not any(block.type == "cards" for block in finished.blocks)
    assert _grade("b19-en", finished) == []

    german = TurnOutput(
        language="de",
        blocks=[
            TextBlock(text="Die Größe hängt vom Haus und vom Jahresverbrauch ab."),
            ActionBlock(name="open_configurator", args={}),
        ],
    )
    finished_de = finish(german, TurnFacts(), Route("sizing"))
    ask = next(block for block in finished_de.blocks if isinstance(block, AskBlock))
    assert ask.options == ["Wohngebäude", "Gewerbe"]
    assert _grade("b19-de", finished_de) == []

    sized = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text="A battery for 8 kWp and 6000 kWh a year goes to the configurator."
            ),
            ActionBlock(name="open_configurator", args={}),
        ],
    )
    assert _grade("b16-en", finish(sized, TurnFacts(), Route("sizing"))) == []


def test_sizing_does_not_add_a_second_ask() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="The size depends on the home."),
            ActionBlock(name="open_configurator", args={}),
            AskBlock(field="application", options=["home", "commercial"]),
        ],
    )
    finished = finish(output, TurnFacts(), Route("sizing"))
    assert [block.type for block in finished.blocks].count("ask") == 1


def _assert_one_language(language: Literal["en", "de"], line: str) -> None:
    output = TurnOutput(language=language, blocks=[TextBlock(text=line)])
    assert language_failure(output, language) is None


def test_each_service_sentence_is_one_language() -> None:
    sentences: dict[Literal["en", "de"], tuple[str, ...]] = {
        "en": (
            "The documents do not state a usable capacity.",
            "The documents do not state whether it supports this.",
            "The documents state a nominal capacity of 260 kWh and a depth of discharge of 98%.",
            "The installation documents state clearances of 1500 mm, 1000 mm, 500 mm and 400 mm.",
        ),
        "de": (
            "Die Unterlagen nennen keine nutzbare Kapazität.",
            "Die Unterlagen nennen keine Unterstützung.",
            "Die Unterlagen nennen eine Nennkapazität von 260 kWh und eine Entladetiefe von 98 %.",
            "Die Montageunterlagen nennen Abstände von 1500 mm, 1000 mm, 500 mm und 400 mm.",
        ),
    }
    for language, lines in sentences.items():
        for line in lines:
            _assert_one_language(language, line)


def test_compare_and_price_rows_lose_the_unlicensed_digits() -> None:
    compared = TurnOutput(
        language="de",
        blocks=[
            TextBlock(
                text=(
                    "Der Speicherbereich liegt bei 5–108 kWh. "
                    "Der PV-Eingang liegt bei 20 kW. Beide haben 10 kW."
                )
            )
        ],
    )
    sealed = seal(
        compared,
        _facts(),
        Route("products"),
        str(ROWS["b08-de"]["question"]),
        "other",
    )
    text = _text(sealed)
    assert "108" not in text
    assert "20" not in text.split()
    assert "10 kW" in text
    graded = _grade("b08-de", sealed)
    assert "number 5 is in no expected fact" not in graded
    assert "number 108 is in no expected fact" not in graded

    priced = TurnOutput(
        language="de",
        blocks=[
            TextBlock(
                text="Der SAJ H2-10K-T3 hat 10 kW AC-Leistung und 20 kW PV-Eingang."
            )
        ],
    )
    stripped = seal(
        priced,
        _facts(),
        Route("products"),
        str(ROWS["b21-de"]["question"]),
        "other",
    )
    body = _text(stripped)
    assert "H2-10K-T3" in body
    assert "20" not in body
    assert "10 kW" not in body
    priced_grade = _grade("b21-de", stripped)
    assert "number 20 is in no expected fact" not in priced_grade
    assert "number 10 is in no expected fact" not in priced_grade


def test_a_series_digit_is_stripped_before_the_question_can_keep_it() -> None:
    facts = _facts()
    facts.add(Fact(id="p4107.ac_power_kw", value="10", source="selection-facts"))

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request, retry
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text="The EcoFlow OCEAN 2 is {fact:p4107.ac_power_kw} kW.",
                        refs=["4107"],
                    ),
                    CardsBlock(product_ids=[4107]),
                ],
            ),
            facts,
        )

    request = TurnRequest(
        conversation_id="c1",
        messages=[
            TurnMessage(
                role="user",
                content="Do you have three-phase hybrid inverters around 15 kW?",
            )
        ],
        locale="en",
    )
    result = run(request, generate, Route("products"))
    assert result.grounded is True
    assert result.fallback is False
    assert result.attempts == 1
    text = _text(result.output)
    assert "2" not in text.split()
    assert "10" not in text
    assert any(block.type == "cards" for block in result.output.blocks)


def test_answer_text_does_not_include_the_ask_chips() -> None:
    output = finish(
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="The size depends on the house."),
                ActionBlock(name="open_configurator", args={}),
            ],
        ),
        TurnFacts(),
        Route("sizing"),
    )
    assert "home" not in answer_text(output.model_dump()["blocks"])
    assert "commercial" not in answer_text(output.model_dump()["blocks"])


def test_a_compare_question_turns_two_cards_into_a_compare_block() -> None:
    output = TurnOutput(
        language="de",
        blocks=[
            TextBlock(text="Beide haben 10 kW."),
            CardsBlock(product_ids=[4107, 6528]),
        ],
    )
    finished = finish(
        output, TurnFacts(), Route("products"), str(ROWS["b08-de"]["question"])
    )
    compared = [block for block in finished.blocks if block.type == "compare"]
    assert len(compared) == 1
    assert compared[0].product_ids == [4107, 6528]
    assert not any(block.type == "cards" for block in finished.blocks)
    assert _grade("b08-de", finished) == []

    english = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Both are 10 kW."),
            CardsBlock(product_ids=[4107, 3556]),
        ],
    )
    finished_en = finish(
        english, TurnFacts(), Route("products"), str(ROWS["b08-en"]["question"])
    )
    assert _grade("b08-en", finished_en) == []


def test_a_product_question_keeps_its_cards() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Here are two."),
            CardsBlock(product_ids=[4107, 6528]),
        ],
    )
    finished = finish(output, TurnFacts(), Route("products"), "Do you stock these?")
    assert [
        block.type for block in finished.blocks if block.type in {"cards", "compare"}
    ] == ["cards"]


def test_one_card_on_a_compare_question_stays_a_card() -> None:
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="Here is one."),
            CardsBlock(product_ids=[4107]),
        ],
    )
    finished = finish(output, TurnFacts(), Route("products"), "Compare this one.")
    assert not any(block.type == "compare" for block in finished.blocks)
    assert any(block.type == "cards" for block in finished.blocks)


def test_a_detached_grid_code_number_is_not_left_bare() -> None:
    blob = "VDE-AR-N [n4=4105]. Rated power 10 kW."
    detached = TurnOutput(
        language="en",
        blocks=[
            TextBlock(text="The VDE application rule 4105. The H2-10K-T3 is 10 kW.")
        ],
    )
    text = _text(strip_detached_code_tails(detached, blob))
    assert "4105" not in text
    assert "10 kW" in text
    assert "H2-10K-T3" in text

    kept = TurnOutput(
        language="en",
        blocks=[TextBlock(text="The code is VDE-AR-N 4105. Rated power 10 kW.")],
    )
    kept_text = _text(strip_detached_code_tails(kept, blob))
    assert "VDE-AR-N 4105" in kept_text
    assert "10 kW" in kept_text


def test_a_regulation_reference_is_not_stripped_or_untraceable() -> None:
    """The rule's own number stays. A step and a detached reading do not (#443)."""
    output = TurnOutput(
        language="de",
        blocks=[
            TextBlock(
                text=(
                    "Die Grenze steht in EnWG 14a Abs. 1 und VDE-AR-N 4105. "
                    "Methode 1 und Schritt 2 nennen 10 kW. "
                    "Der Code 4105 kWh bleibt eine Zahl. Abs. 1."
                )
            )
        ],
    )
    text = _text(drop_bare_numbers(output))
    assert "EnWG 14a Abs. 1" in text
    assert "VDE-AR-N 4105" in text
    assert text.count("Abs. 1") == 1
    assert "Methode 1" not in text
    assert "Schritt 2" not in text
    assert "10 kW" not in text
    assert "4105 kWh" not in text
    assert untraceable_numbers("The datasheet lists VDE-AR-N 4105.", []) == []
    assert untraceable_numbers("The grid code is 4105 kWh.", []) == ["4105"]
    assert untraceable_numbers("Abs. 1", []) == ["1"]
    assert untraceable_numbers("EnWG 14a Abs. 1", []) == []
    assert untraceable_numbers("3-phase and 1-phase", ["3"], None) == ["1"]
    assert untraceable_numbers("VDE-AR-N 4105/600", []) == ["600"]
    assert untraceable_numbers("EnWG 14a Abs. 1-500", []) == ["500"]
    assert untraceable_numbers("Start-up 400 V", []) == ["400"]
    assert untraceable_numbers("Time-of-use 60 Hz", []) == ["60"]
    assert untraceable_numbers("single-phase 10 kW", []) == ["10"]
    assert untraceable_numbers("grid-code 4105 kWh", []) == ["4105"]
    assert untraceable_numbers("application-rule 4105", []) == ["4105"]
    assert untraceable_numbers("§ 400", []) == ["400"]
    assert untraceable_numbers("Nach der VDE-Norm ist die Art 10 kW.", []) == ["10"]
    assert untraceable_numbers("EnWG 14a. Die Spannung ist Abs. 230 V.", []) == ["230"]
    assert untraceable_numbers("VDE-AR-N [n4=4105]", []) == []
    assert untraceable_numbers("Abschnitt 5.7.4.1 der VDE-AR-N 4105", []) == []
    assert untraceable_numbers("clause 5.7 of VDE-AR-N 4105", []) == []

    measurements = TurnOutput(
        language="de",
        blocks=[
            TextBlock(
                text=(
                    "Start-up 400 V und Time-of-use 60 Hz und single-phase 10 kW. "
                    "Nach der VDE-Norm ist die Art 10 kW. Satz 10 kW. Nr. 10 kW nach VDE. "
                    "EnWG 14a. Die Spannung ist Abs. 230 V. "
                    "VDE-AR-N 4105/600. EnWG 14a Abs. 1-500. "
                    "Abschnitt 5.7.4.1 der VDE-AR-N 4105. EnWG § 1."
                )
            )
        ],
    )
    measured = _text(drop_bare_numbers(measurements))
    assert "400" not in measured
    assert "60" not in measured
    assert "10 kW" not in measured
    assert "230" not in measured
    assert "4105/600" not in measured
    assert "1-500" not in measured
    assert "Abschnitt 5.7.4.1" in measured
    assert "VDE-AR-N 4105" in measured
    assert "EnWG § 1" in measured
    lone = _text(
        drop_bare_numbers(
            TurnOutput(language="de", blocks=[TextBlock(text="Die Grenze ist § 400.")])
        )
    )
    assert "400" not in lone


def test_a_figure_fact_does_not_license_a_detached_grid_code() -> None:
    facts = _facts("VDE-AR-N [n4=4105]. The H2 is 10 kW, 12 kW and 15 kW.")
    facts.add(Fact(id="c1.n4", value="4105", source="search-knowledge"))
    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "The German VDE application rule 4105. "
                    "Models are 10 kW, 12 kW and 15 kW."
                )
            ),
            DocumentBlock(ref="c1"),
        ],
    )
    sealed = seal(
        output,
        facts,
        Route("documents"),
        str(ROWS["b25-en"]["question"]),
        "other",
    )
    text = _text(sealed)
    assert "4105" not in text
    assert "10 kW" in text
    assert "12 kW" in text
    assert "15 kW" in text
    assert "The documents do not state whether it supports this." in text
    assert not any("4105" in item for item in _grade("b25-en", sealed))


def test_a_figure_after_a_decimal_stays_with_the_model_on_that_line() -> None:
    line = "- **H2-30K-T3-DE** — AC power 29.999 kW, PV input 45 kW"
    rebound = rebind_figures_past_decimal(
        TurnOutput(language="en", blocks=[TextBlock(text=line)])
    )
    text = _text(rebound)
    assert "29.999 kW" in text
    assert "H2-30K-T3-DE PV input 45 kW" in text
    untouched = "- **H2-30K-T3-DE** — AC power 29.999 kW"
    assert (
        _text(
            rebind_figures_past_decimal(
                TurnOutput(language="en", blocks=[TextBlock(text=untouched)])
            )
        )
        == untouched
    )
    ranged = "The voltage is 702.5 V to 936 V."
    assert (
        _text(
            rebind_figures_past_decimal(
                TurnOutput(language="en", blocks=[TextBlock(text=ranged)])
            )
        )
        == ranged
    )

    output = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "Our documents do not state whether the SAJ H2 supports this.\n"
                    "- **H2-25K-T3** — AC power 25 kW, PV input 45 kW\n"
                    "- **H2-30K-T3-DE** — AC power 29.999 kW, PV input 45 kW"
                )
            ),
            DocumentBlock(ref="c1"),
        ],
    )
    sealed = seal(
        output,
        _facts("The H2-30K-T3-DE is 29.999 kW."),
        Route("documents"),
        str(ROWS["b25-en"]["question"]),
        "other",
    )
    failures = _grade("b25-en", sealed)
    assert failures == []
