"""Golden set from fact-card rows, and the scoring of search results against it."""

from index.eval.goldset import CardRow, Evidence, build, card_rows, field_code
from index.eval.metrics import quote_in, score, words
from linker_genie.retrieval import DocumentHit

# Rows as knowledge/fact-cards/goodwe.md prints them (old repository, refs/landed/chain-tip).
CARD = """# Fact cards · GoodWe

## Model card · GW75K-ET-G10
- Brand: GoodWe

### EL · 电气参数 · Electrical

| ID | Field | Value | Unit | Scope | Evidence | Status |
|---|---|---|---|---|---|---|
| EL-10 | Max PV power | 150 | kW | — | m5735 p.2 "Max. Input Power (kW) 150" | evidenced |
| EL-11 | Max DC input voltage | 1000 | V | *1 | m5735 p.2 "Max. Input Voltage (V)*1 1000" | evidenced |
| EL-12 | MPPT voltage range | — | — | — | none in documents read | empty-no-evidence |
| IN-03 | Clearances | ≥300 mm | — | — | m6398 p.1 "≥300mm" (image); m5735 p.3 "Clearance 300 mm" | evidenced |

## Model card · LX D5.0-10

| ID | Field | Value | Unit | Scope | Evidence | Status |
|---|---|---|---|---|---|---|
| EL-10a | Max PV power | 1 | kW | — | m5735 p.4 “Max. Input Power (kW) 1” | evidenced |
| CP-01 | Listed partner | listed | — | partner: GW10K-ET; edition: V29 | m9999 p.4 "GW10K-ET" | evidenced |
"""
SHA = {5735: "d" * 64, 6398: "f" * 64}


def rows() -> list[CardRow]:
    return list(card_rows("goodwe", CARD))


def test_card_rows_belong_to_their_model_card() -> None:
    assert [(row.model, row.row_id) for row in rows()] == [
        ("GW75K-ET-G10", "EL-10"),
        ("GW75K-ET-G10", "EL-11"),
        ("GW75K-ET-G10", "EL-12"),
        ("GW75K-ET-G10", "IN-03"),
        ("LX D5.0-10", "EL-10a"),
        ("LX D5.0-10", "CP-01"),
    ]


def test_field_codes_drop_the_scope_letter_and_the_second_code() -> None:
    assert [field_code(code) for code in ("EL-02b", "EL-04 / EL-30", "BA-11")] == [
        "EL-02",
        "EL-04",
        "BA-11",
    ]


def test_questions_come_in_english_and_german_with_the_card_page_as_gold() -> None:
    questions = build(rows(), SHA)
    text = [question for question in questions if question.kind == "text"]

    by_lang = {
        question.lang: question for question in text if question.model == "LX D5.0-10"
    }
    assert (
        by_lang["en"].question
        == "What is the maximum PV input power of the LX D5.0-10?"
    )
    assert (
        by_lang["de"].question
        == "Wie hoch ist die maximale PV-Eingangsleistung beim LX D5.0-10?"
    )
    assert by_lang["en"].evidence == [
        Evidence("d" * 64, 4, "Max. Input Power (kW) 1", "m5735")
    ]


def test_one_question_per_gold_page_and_unevidenced_or_unhosted_rows_are_left_out() -> (
    None
):
    questions = build(rows(), SHA)

    text = {
        (question.model, question.code)
        for question in questions
        if question.kind == "text"
    }
    # EL-10 and EL-11 of the GW75K both cite m5735 p.2: one survives. The LX's EL-10 cites
    # p.4. EL-12 is empty-no-evidence; the CP-01 cites m9999, which the inventory lacks.
    assert len(text) == 2
    assert ("LX D5.0-10", "EL-10") in text
    assert ("LX D5.0-10", "CP-01") not in text


def test_a_drawing_read_off_the_rendered_page_is_a_figure_question_with_only_that_evidence() -> (
    None
):
    figure = [question for question in build(rows(), SHA) if question.kind == "figure"]

    assert {question.lang for question in figure} == {"en", "de"}
    assert figure[0].code == "IN-03"
    assert figure[0].evidence == [Evidence("f" * 64, 1, "≥300mm", "m6398", image=True)]


def test_words_fold_typography_and_split_on_punctuation() -> None:
    assert words("Max. Input Power (kW)*1 1’000 – ≥300mm") == [
        "max",
        "input",
        "power",
        "kw",
        "1",
        "1",
        "000",
        "300mm",
    ]


def test_a_table_quote_matches_its_row_across_other_models_columns() -> None:
    row = "| Max. Input Power (kW) | 112.5 | 120 | 150 | 150 |"

    assert quote_in("Max. Input Power (kW) 150", row)
    assert not quote_in("Max. Input Power (kW) 160", row)


def test_a_quote_may_continue_on_the_next_line_but_not_further() -> None:
    text = "Voltage Range (V)\n300 ~ 800\nother\nlast"

    assert quote_in("Voltage Range (V) 300 ~ 800", text)
    assert not quote_in("Voltage Range (V) last", text)


def hit(sha: str, page: int, text: str) -> DocumentHit:
    return DocumentHit(
        "id",
        sha,
        "https://de-linker.com/x.pdf",
        "t",
        "datasheet",
        page,
        "",
        text,
        "en",
        0.1,
    )


def test_score_reports_the_rank_of_the_first_gold_page_and_whether_the_cited_page_is_right() -> (
    None
):
    gold = [Evidence("d" * 64, 2, "Max. Input Power (kW) 150", "m5735")]
    hits = [
        hit("e" * 64, 9, "noise"),
        hit("d" * 64, 5, "Max. Input Power (kW) 150 in a summary"),
        hit("d" * 64, 2, "x"),
    ]

    result = score(hits, gold)

    assert result.rank == 3
    assert (
        result.cited_page_correct is False
    )  # the quote-bearing hit is p.5, not the gold p.2


def test_score_without_any_gold_hit() -> None:
    result = score([hit("e" * 64, 1, "nothing")], [Evidence("d" * 64, 2, "q", "m1")])

    assert (result.rank, result.cited_page_correct) == (None, None)
