"""The 100-question baseline set and its grading (#336).

Set integrity: composition (10 categories × 5 slots × EN/DE), the map's hard
rows, EN/DE structural parity, every expected product grounded in the catalogue
fixture. Grading: the TRIAL.md口径 as pure functions, on hand-made turns whose
shapes come from the service's SSE (tests/test_turn.py, the #234 page eval).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from baseline.grade import (
    NEXT_STEP_BLOCKS,
    Turn,
    answer_text,
    check,
    number_variants,
    parse_stream,
    shown_ids,
    untraceable_numbers,
)
from baseline.run import percentile, phase_medians

SET = Path(__file__).parents[1] / "eval" / "baseline" / "baseline100.jsonl"
CATEGORIES = (
    "product-match",
    "pairing",
    "documents",
    "sizing",
    "price",
    "inquiry",
    "handoff",
    "company-logistics",
    "smalltalk",
    "page-awareness",
)
ROWS = [
    json.loads(line) for line in SET.read_text(encoding="utf-8").splitlines() if line
]
BY_LANG = {lang: [row for row in ROWS if row["lang"] == lang] for lang in ("en", "de")}

# The catalogue the fixture feed carries (services/engine/tests/fixtures/feed.json,
# 106 products, the same count the live Store API held on 2026-10-19): every
# product id the set expects must be a product of this world.
FEED = json.loads(
    (
        Path(__file__).parents[2] / "engine" / "tests" / "fixtures" / "feed.json"
    ).read_text(encoding="utf-8")
)
FEED_IDS = {int(product["id"]) for product in FEED["products"]}
FEED_TOKENS = {
    str(product["model"]): str(product["model"]) for product in FEED["products"]
}


def turn(blocks: list[dict[str, object]], **meta: object) -> Turn:
    """A well-formed turn: grounded, not a fallback, answering in `language`."""

    return Turn(
        meta={"grounded": True, "fallback": False, "language": "en", **meta},
        blocks=blocks,
        done=True,
    )


def text(words: str, refs: list[str] | None = None) -> dict[str, object]:
    return {"type": "text", "text": words, "refs": refs or []}


# ---------------------------------------------------------------- set integrity


def test_the_set_is_100_rows_of_10_categories() -> None:
    assert len(ROWS) == 100
    assert len({row["id"] for row in ROWS}) == 100
    counts = Counter(row["category"] for row in ROWS)
    assert set(counts) == set(CATEGORIES)
    assert set(counts.values()) == {10}


def test_every_category_is_half_english_half_german() -> None:
    for category in CATEGORIES:
        langs = Counter(row["lang"] for row in ROWS if row["category"] == category)
        assert langs == {"en": 5, "de": 5}, category


def test_en_and_de_share_one_structure() -> None:
    """The twins: same slot, same category, same assertion kind, and the German
    question is its own sentence, never the English one (AGENTS.md §3)."""

    slots: dict[int, dict[str, dict[str, object]]] = {}
    for row in ROWS:
        slots.setdefault(row["slot"], {})[row["lang"]] = row
    assert len(slots) == 50
    for slot, pair in slots.items():
        assert set(pair) == {"en", "de"}, slot
        english, german = pair["en"], pair["de"]
        assert english["category"] == german["category"], slot
        assert english["assertion"] == german["assertion"], slot
        assert english["question"] != german["question"], slot


def test_the_maps_hard_rows_are_all_present() -> None:
    """#329's gate: trials 1, 8, 10 and 14 must give products, manual steps or
    the configurator - no fallback, no sales@. They lead the file (the smoke
    slice) in both languages."""

    hard = [row for row in ROWS if row.get("hard")]
    assert sorted(row["trial"] for row in hard if row["lang"] == "en") == [1, 8, 10, 14]
    assert sorted(row["trial"] for row in hard if row["lang"] == "de") == [1, 8, 10, 14]
    for row in hard:
        assert row["expect"].get("no_handoff"), row["id"]
    ids = [row["id"] for row in ROWS[:10]]
    assert ids == [
        "b01-en",
        "b01-de",
        "b02-en",
        "b02-de",
        "b15-en",
        "b15-de",
        "b16-en",
        "b16-de",
        "b36-en",
        "b36-de",
    ]


def test_the_trials_seed_their_semantics() -> None:
    seeded = {row["trial"] for row in ROWS if row.get("trial") is not None}
    # The trial rows the set carries: the map's four, the five the spec's own
    # gate names (2, 3, 4, 5, 13), and the rest of the 20 as they fit.
    assert {1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20} <= seeded


def test_expected_products_exist_in_the_catalogue() -> None:
    expected: set[int] = set()
    for row in ROWS:
        expect = row["expect"]
        expected.update(int(pid) for pid in expect.get("products", []))
        expected.update(int(pid) for pid in expect.get("products_any", []))
        for group in expect.get("compare", []):
            expected.update(int(pid) for pid in group)
    assert expected <= FEED_IDS, sorted(expected - FEED_IDS)


def test_every_row_names_its_grounding() -> None:
    for row in ROWS:
        assert row.get("ground"), row["id"]


def test_judge_rows_carry_a_reference_review_rows_do_not_pretend() -> None:
    for row in ROWS:
        if row["assertion"] == "judge":
            assert row.get("reference"), row["id"]
        if row["assertion"] == "human-review":
            assert not row.get("reference"), row["id"]


def test_regexes_of_every_row_compile() -> None:
    for row in ROWS:
        expect = row["expect"]
        for pattern in [*expect.get("all", []), *expect.get("none", [])]:
            assert re.compile(pattern), (row["id"], pattern)
        if expect.get("price_gate"):
            assert re.compile(expect["price_gate"]), row["id"]


# -------------------------------------------------------------------- grading


def stream(*blocks: dict[str, object], meta: dict[str, object] | None = None) -> str:
    payload = meta or {"grounded": True, "fallback": False, "language": "en"}
    events: list[tuple[str, object]] = [("meta", payload)]
    events.extend(("block", block) for block in blocks)
    events.append(("done", {"ok": True}))
    return "".join(
        f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events
    )


def test_parse_stream_reads_meta_blocks_and_done() -> None:
    parsed = parse_stream(
        stream(
            {"type": "text", "text": "Two kilowatts.", "refs": ["4107"]},
            {"type": "cards", "product_ids": [4107], "prices": []},
        )
    )
    assert parsed.done
    assert parsed.meta["grounded"] is True
    assert shown_ids(parsed.blocks) == {4107}
    assert answer_text(parsed.blocks) == "Two kilowatts."


def test_a_fallback_turn_fails_every_row() -> None:
    row = {"id": "x", "lang": "en", "category": "documents", "expect": {}}
    fallen = Turn(
        meta={"grounded": False, "fallback": True, "language": "en"}, done=True
    )
    failures = check(row, fallen, FEED_TOKENS)
    assert any("fell back" in failure for failure in failures)
    assert any("ungrounded" in failure for failure in failures)


def test_a_hard_row_that_deflects_to_the_mailbox_fails() -> None:
    row = next(item for item in ROWS if item["id"] == "b15-en")
    handed = turn(
        [
            text("Our team will answer that at sales@de-linker.com."),
            {"type": "handoff", "summary": "warranty"},
        ]
    )
    failures = check(row, handed, FEED_TOKENS)
    assert any("handoff" in failure for failure in failures)
    assert any("sales@de-linker.com" in failure for failure in failures)


def test_a_clearance_answer_with_all_four_values_passes() -> None:
    row = next(item for item in ROWS if item["id"] == "b15-en")
    good = turn(
        [
            text("Keep 1500 mm above, 1000 mm below, 500 mm left and 400 mm right."),
            {"type": "document", "ref": "chunk-1", "label": "CB2 guide"},
        ]
    )
    assert check(row, good, FEED_TOKENS) == []


def test_a_missing_clearance_value_fails() -> None:
    row = next(item for item in ROWS if item["id"] == "b15-en")
    thin = turn(
        [
            text("Keep 1500 mm above and 1000 mm below."),
            {"type": "document", "ref": "chunk-1", "label": "CB2 guide"},
        ]
    )
    failures = check(row, thin, FEED_TOKENS)
    # `500 mm` inside `1500 mm` must not satisfy the 500 mm clearance.
    assert any("500 ?mm" in failure and "1500" not in failure for failure in failures)
    assert any("400 ?mm" in failure for failure in failures)


def test_numbers_are_traceable_through_units_and_catalogue_codes() -> None:
    assert number_variants("20.000") == {20.0, 20000.0}
    assert number_variants("8,03") == {8.03}
    # The trial's own example: 20000 Wp == 20 kWp == 15.000 Wp style agreement.
    assert untraceable_numbers("20000 Wp", ["20"]) == []
    assert untraceable_numbers("20 kWp", ["20000"]) == []
    assert untraceable_numbers("15.000 Wp", ["15"]) == []
    # A number no fact backs is fabricated.
    assert untraceable_numbers("It needs 4700 Wp.", ["20000"]) == ["4700"]
    # Model codes carry their digits with them.
    assert untraceable_numbers("The H2-10K-T3", [], {"H2-10K-T3": "SAJ"}) == []
    # The Store API prints the model with its brand prefix; the answer need not.
    catalog = {"EF HD-P1-3K68-S2": "EcoFlow", "CB2-100.3-HV5": "SAJ"}
    assert untraceable_numbers("The HD-P1-3K68-S2", [], catalog) == []
    # A series prefix on its own (CB2) is still the product code.
    assert untraceable_numbers("The CB2 cabinet", [], catalog) == []
    # A designation from the manual for equipment we do not sell (CH2).
    assert untraceable_numbers("with the CH2 inverter", [], catalog) == []
    # A measurement is not a designation: its digits are checked.
    assert untraceable_numbers("1500mm", [], catalog) == ["1500"]


def test_the_wrong_power_fails_the_number_check() -> None:
    row = next(item for item in ROWS if item["id"] == "b11-en")
    wrong = turn(
        [
            text("The maximum is 15000 Wp."),
            {"type": "document", "ref": "chunk-1", "label": "H2 datasheet"},
        ]
    )
    failures = check(row, wrong, FEED_TOKENS)
    assert any("15000" in failure for failure in failures)


def test_products_count_as_shown_by_card_or_citation() -> None:
    # The bare word row demands cards; the phase row takes a citation instead.
    bare = next(item for item in ROWS if item["id"] == "b01-en")
    cards = turn(
        [text("Here is the SAJ range."), {"type": "cards", "product_ids": [4107]}]
    )
    assert check(bare, cards, FEED_TOKENS) == []
    phase = next(item for item in ROWS if item["id"] == "b02-en")
    cited = turn(
        [
            text(
                "It comes single-phase and three-phase.",
                ["6483"],
            ),
            {"type": "cards", "product_ids": [6483]},
        ]
    )
    assert check(phase, cited, FEED_TOKENS) == []


def test_a_brand_answer_without_cards_fails_the_bare_word_row() -> None:
    row = next(item for item in ROWS if item["id"] == "b01-en")
    greeting = turn([text("Hi! What are you looking for today?")])
    failures = check(row, greeting, FEED_TOKENS)
    assert any("cards" in failure for failure in failures)
    assert any("none of products" in failure for failure in failures)


def test_the_sizing_row_wants_the_configurator_and_refuses_cards() -> None:
    row = next(item for item in ROWS if item["id"] == "b16-en")
    configurator = turn(
        [
            text("The Solution Configurator sizes the battery."),
            {"type": "action", "name": "open_configurator", "args": {}},
        ]
    )
    assert check(row, configurator, FEED_TOKENS) == []
    dump = turn(
        [
            text("Here are inverters."),
            {"type": "cards", "product_ids": [4107, 4108, 2063]},
        ]
    )
    failures = check(row, dump, FEED_TOKENS)
    assert any("open_configurator" in failure for failure in failures)
    assert any("must not carry a cards block" in failure for failure in failures)


def test_the_compare_row_needs_both_products_in_one_block() -> None:
    row = next(item for item in ROWS if item["id"] == "b08-en")
    both = turn(
        [
            text("One is three-phase, the other a power module."),
            {"type": "compare", "product_ids": [4107, 3556]},
        ]
    )
    assert check(row, both, FEED_TOKENS) == []
    one = turn([{"type": "compare", "product_ids": [4107]}])
    assert any("compare" in failure for failure in check(row, one, FEED_TOKENS))


def test_the_price_row_reads_the_gate_sentence_off_the_card() -> None:
    row = next(item for item in ROWS if item["id"] == "b21-en")
    gated = turn(
        [
            text("The card shows the price for your account."),
            {
                "type": "cards",
                "product_ids": [4107],
                "prices": [
                    {
                        "product_id": 4107,
                        "text": "Net price after partner sign-in",
                        "reason": "login",
                    }
                ],
            },
        ]
    )
    assert check(row, gated, FEED_TOKENS) == []
    priced = turn(
        [
            text("It costs 1680."),
            {
                "type": "cards",
                "product_ids": [4107],
                "prices": [{"product_id": 4107, "text": "€1,680.00"}],
            },
        ]
    )
    failures = check(row, priced, FEED_TOKENS)
    assert any(
        "price line" in failure or "must not match" in failure for failure in failures
    )
    assert any("1680" in failure for failure in failures)


def test_the_company_row_is_one_mailbox_sentence() -> None:
    row = next(item for item in ROWS if item["id"] == "b36-en")
    referral = turn(
        [
            {
                "type": "handoff",
                "summary": "Our team will answer that at sales@de-linker.com.",
            },
        ],
        language="en",
    )
    assert check(row, referral, FEED_TOKENS) == []
    invented = turn(
        [
            text("Yes, we deliver across the EU within 5 days."),
            {
                "type": "handoff",
                "summary": "Our team will answer that at sales@de-linker.com.",
            },
        ]
    )
    failures = check(row, invented, FEED_TOKENS)
    assert any("5" in failure for failure in failures)  # a delivery days promise


def test_the_person_row_needs_the_exact_sentence_and_the_card() -> None:
    row = next(item for item in ROWS if item["id"] == "b31-en")
    proper = turn(
        [
            text("Someone from the Linker team can get in touch with you by email."),
            {"type": "contact", "reason": "asked"},
        ]
    )
    assert check(row, proper, FEED_TOKENS) == []
    without_card = turn(
        [text("Someone from the Linker team can get in touch with you by email.")]
    )
    assert any(
        "contact" in failure for failure in check(row, without_card, FEED_TOKENS)
    )


def test_the_inquiry_row_answers_with_the_login_sentence() -> None:
    row = next(item for item in ROWS if item["id"] == "b26-en")
    login = turn([text("Please log in to your account to view this inquiry.")])
    assert check(row, login, FEED_TOKENS) == []
    mailbox = turn(
        [
            {
                "type": "handoff",
                "summary": "Our team will answer that at sales@de-linker.com.",
            }
        ]
    )
    failures = check(row, mailbox, FEED_TOKENS)
    assert any("missing" in failure for failure in failures)
    assert any("sales@de-linker.com" in failure for failure in failures)


def test_the_page_row_cites_the_page_and_the_page_product_answers() -> None:
    row = next(item for item in ROWS if item["id"] == "b46-en")
    answer = turn([text("This one has 4 MPPTs.", ["6528"])])
    assert check(row, answer, FEED_TOKENS) == []
    vague = turn([text("Which model do you mean?")])
    failures = check(row, vague, FEED_TOKENS)
    assert any("4" in failure or "MPPT" in failure for failure in failures)


def test_citing_the_page_counts_only_with_a_page_ref() -> None:
    row = next(item for item in ROWS if item["id"] == "b48-en")
    cited = turn([text("Peak shaving means shifting demand.", ["page"])])
    assert check(row, cited, FEED_TOKENS) == []
    uncited = turn([text("Peak shaving means shifting demand.")])
    assert any(
        "cite the page" in failure for failure in check(row, uncited, FEED_TOKENS)
    )


def test_a_german_answer_to_an_english_row_fails() -> None:
    row = next(item for item in ROWS if item["id"] == "b11-en")
    german = turn(
        [
            text("Die maximale PV-Eingangsleistung beträgt 20000 Wp."),
            {"type": "document", "ref": "chunk-1", "label": "H2"},
        ],
        language="de",
    )
    failures = check(row, german, FEED_TOKENS)
    assert any("answered in 'de'" in failure for failure in failures)


def test_forbidden_words_fail_any_row() -> None:
    row = {"id": "x", "lang": "en", "category": "smalltalk", "expect": {}}
    basket = turn([text("I added it to your basket.")])
    assert any("basket" in failure for failure in check(row, basket, FEED_TOKENS))


def test_next_step_blocks_cover_every_move_the_shell_offers() -> None:
    assert NEXT_STEP_BLOCKS == (
        "ask",
        "cards",
        "compare",
        "action",
        "document",
        "parts",
        "contact",
        "handoff",
    )


def test_percentiles_print_the_gate_number() -> None:
    # 100 rows: p50 is the 50th value, p95 the 95th (nearest rank).
    values = [float(n) for n in range(1, 101)]
    assert percentile(values, 0.5) == 50.0
    assert percentile(values, 0.95) == 95.0
    assert percentile([], 0.5) is None


def test_phase_medians_summarize_the_service_timing() -> None:
    timings: list[dict[str, Any]] = [
        {"route": 1.0, "model": 4.0, "total": 5.0},
        {"route": 2.0, "model": 6.0, "total": 8.0, "note": "x"},
        {"route": 3.0, "model": 5.0, "total": 9.0},
    ]
    assert phase_medians(timings) == {"route": 2.0, "model": 5.0, "total": 8.0}
    assert phase_medians([]) == {}
