"""The 100-question baseline set and its grading (#336).

Set integrity: 100 rows, 10 categories, EN/DE parity, the map's hard rows,
every one of the 20 trial questions, every expected product grounded in the
catalogue fixture. Grading: the TRIAL.md口径 as pure functions, on hand-made
turns whose shapes come from the service's SSE (tests/test_turn.py, the #234
page eval).
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
from baseline.run import (
    CLIENT_P95_GATE_SECONDS,
    CLIENT_P95_TARGET_SECONDS,
    first_event_seconds,
    grade_verdict,
    messages_of,
    percentile,
    phase_medians,
    report,
    strict_status,
)

SET = Path(__file__).parents[1] / "eval" / "baseline" / "baseline100.jsonl"
QUALITATIVE = Path(__file__).parents[1] / "eval" / "baseline" / "qualitative.jsonl"
# Dossier Top-10 (docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md §2).
# #339 has no case ids, so the qualitative section is where those rows live.
TOP10_GAPS = (
    "topic-switch",
    "prompt-injection",
    "latency",
    "sse-break",
    "concurrency",
    "card-staleness",
    "misspelling",
    "page-drift",
    "mixed-language",
    "series-ambiguity",
)
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
    """Ten categories, 50/50 by language. Documents holds 14 rows because
    trials 6 and 19 replaced the weakest non-seed slots (b20 sizing, b25
    price) and are document questions; those two categories are 8."""

    assert len(ROWS) == 100
    assert len({row["id"] for row in ROWS}) == 100
    assert Counter(row["lang"] for row in ROWS) == {"en": 50, "de": 50}
    counts = Counter(row["category"] for row in ROWS)
    assert set(counts) == set(CATEGORIES)
    assert counts["documents"] == 14
    assert counts["sizing"] == 8
    assert counts["price"] == 8
    for category, count in counts.items():
        if category not in {"documents", "sizing", "price"}:
            assert count == 10, category


def test_every_category_is_half_english_half_german() -> None:
    for category in CATEGORIES:
        langs = Counter(row["lang"] for row in ROWS if row["category"] == category)
        assert langs["en"] == langs["de"], category
        assert langs["en"] > 0, category


def _criteria(expect: dict[str, Any]) -> dict[str, Any]:
    """Language-independent shape of one row's expectations.

    Regex text differs by language. Everything else — which checks exist, the
    product ids, the numbers a correct answer may state, the phase each power
    belongs to — is the same on both sides of a slot.
    """

    text_keys = {"all", "none", "price_gate", "no_clause", "no_figure_on"}
    shaped: dict[str, object] = {}
    for key, value in expect.items():
        if key in text_keys:
            shaped[key] = len(value) if isinstance(value, list) else True
        elif key == "phase_powers" and isinstance(value, list):
            shaped[key] = [
                (item["phase"], list(item["powers"]))
                for item in value
                if isinstance(item, dict)
            ]
        else:
            shaped[key] = value
    return shaped


def test_en_and_de_share_one_structure() -> None:
    """The twins: same slot, same category, same assertion kind, the same
    expected criteria, and the German question is its own sentence."""

    slots: dict[int, dict[str, dict[str, Any]]] = {}
    for row in ROWS:
        slots.setdefault(row["slot"], {})[row["lang"]] = row
    assert len(slots) == 50
    for slot, pair in slots.items():
        assert set(pair) == {"en", "de"}, slot
        english, german = pair["en"], pair["de"]
        assert english["category"] == german["category"], slot
        assert english["assertion"] == german["assertion"], slot
        assert english["question"] != german["question"], slot
        assert _criteria(english["expect"]) == _criteria(german["expect"]), slot


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
    """The set is the 20-question trial expanded, so every trial number is
    present in both languages. Trials 6 and 19 occupy the slots of the two
    rows they replaced."""

    seeded = {row["trial"] for row in ROWS if row.get("trial") is not None}
    assert seeded == set(range(1, 21))
    for trial in range(1, 21):
        langs = {row["lang"] for row in ROWS if row.get("trial") == trial}
        assert langs == {"en", "de"}, trial
    replaced = {row["question"] for row in ROWS}
    assert "What battery size for 6 kWp and 4500 kWh per year?" not in replaced
    assert (
        "Which is cheaper, the OCEAN 2 battery or the GoodWe GW9.0-BAT-D-G20?"
        not in replaced
    )
    slot6 = next(row for row in ROWS if row["id"] == "b20-en")
    slot19 = next(row for row in ROWS if row["id"] == "b25-en")
    assert slot6["trial"] == 6 and slot6["category"] == "documents"
    assert slot19["trial"] == 19 and slot19["category"] == "documents"
    assert slot6["assertion"] == "deterministic"
    assert slot19["assertion"] == "deterministic"


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


def test_every_row_lists_the_numbers_a_correct_answer_may_state() -> None:
    """An empty list means no number may appear. A missing list used to skip
    the check, so 66 rows accepted a fabricated count."""

    for row in ROWS:
        numbers = row["expect"].get("numbers")
        assert isinstance(numbers, list), row["id"]


def test_regexes_of_every_row_compile() -> None:
    for row in ROWS:
        expect = row["expect"]
        patterns = [
            *expect.get("all", []),
            *expect.get("none", []),
            *expect.get("no_clause", []),
            *expect.get("no_figure_on", []),
        ]
        for binding in expect.get("phase_powers", []):
            patterns.append(binding["label"])
        for pattern in patterns:
            assert re.compile(pattern), (row["id"], pattern)
        if expect.get("price_gate"):
            assert re.compile(expect["price_gate"]), row["id"]


def _document(words: str) -> list[dict[str, object]]:
    return [
        text(words),
        {"type": "document", "ref": "chunk-1", "label": "hosted manual"},
    ]


def test_trial_6_rejects_the_nominal_number_used_as_usable_capacity() -> None:
    """260 kWh is the nominal figure. Attaching it to usable capacity fails
    even when the answer also says the documents do not state a separate one."""

    english = next(row for row in ROWS if row["id"] == "b20-en")
    borrowed = turn(
        _document(
            "The usable capacity is 260 kWh (nominal); "
            "the documents do not state a separate usable figure. "
            "The depth of discharge is 98%."
        )
    )
    assert check(english, borrowed, FEED_TOKENS)
    german = next(row for row in ROWS if row["id"] == "b20-de")
    borrowed_de = turn(
        _document(
            "Die nutzbare Kapazität beträgt 260 kWh (Nennkapazität); "
            "die Unterlagen nennen keine separate Angabe. "
            "Die Entladetiefe beträgt 98 %."
        ),
        language="de",
    )
    assert check(german, borrowed_de, FEED_TOKENS)


def test_trial_6_states_nominal_and_refuses_a_usable_figure() -> None:
    """The L260 sheets state nominal 260 kWh and DoD 98%, not a usable kWh."""

    english = next(row for row in ROWS if row["id"] == "b20-en")
    good = turn(
        _document(
            "The documents do not state a usable capacity. "
            "The nominal capacity is 260 kWh and the depth of discharge is 98%."
        )
    )
    assert check(english, good, FEED_TOKENS) == []
    invented = turn(_document("The usable capacity is 254.8 kWh."))
    assert check(english, invented, FEED_TOKENS)
    stale = turn(
        _document("Nominal capacity is 260 kWh with a depth of discharge of 5-95%.")
    )
    assert check(english, stale, FEED_TOKENS)

    german = next(row for row in ROWS if row["id"] == "b20-de")
    good_de = turn(
        _document(
            "Die Unterlagen nennen keine nutzbare Kapazität. "
            "Die Nennkapazität beträgt 260 kWh, die Entladetiefe 98 %."
        ),
        language="de",
    )
    assert check(german, good_de, FEED_TOKENS) == []


def test_trial_19_rejects_support_beside_a_negation() -> None:
    """The absence sentence has to say the documents do not state support.
    A different negation does not cancel a clause that asserts support."""

    english = next(row for row in ROWS if row["id"] == "b25-en")
    both = turn(
        _document(
            "The SAJ H2 supports EnWG 14a dimming; "
            "the documents do not state it explicitly."
        )
    )
    failures = check(english, both, FEED_TOKENS)
    assert failures
    assert any("supports" in failure for failure in failures)
    german = next(row for row in ROWS if row["id"] == "b25-de")
    both_de = turn(
        _document(
            "Der SAJ H2 unterstützt das Dimmen nach §14a EnWG; "
            "die Unterlagen sagen es nicht ausdrücklich."
        ),
        language="de",
    )
    assert check(german, both_de, FEED_TOKENS)


def test_trial_19_does_not_assert_enwg_14a_support() -> None:
    """The H2 documents do not state EnWG 14a. The answer must not claim support."""

    english = next(row for row in ROWS if row["id"] == "b25-en")
    good = turn(
        _document("The documents do not state EnWG 14a support for the SAJ H2.")
    )
    assert check(english, good, FEED_TOKENS) == []
    claimed = turn(_document("Yes, the H2 supports EnWG 14a dimming."))
    assert check(english, claimed, FEED_TOKENS)
    assert "14" in english["expect"]["numbers"]

    german = next(row for row in ROWS if row["id"] == "b25-de")
    good_de = turn(
        _document(
            "Die Unterlagen nennen keine Unterstützung für das Dimmen nach §14a EnWG."
        ),
        language="de",
    )
    assert check(german, good_de, FEED_TOKENS) == []
    claimed_de = turn(
        _document("Ja, der H2 unterstützt das Dimmen nach §14a EnWG."),
        language="de",
    )
    assert check(german, claimed_de, FEED_TOKENS)


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


def test_products_count_as_shown_only_by_a_card_or_compare_block() -> None:
    bare = next(item for item in ROWS if item["id"] == "b01-en")
    cards = turn(
        [text("Here is the SAJ range."), {"type": "cards", "product_ids": [4107]}]
    )
    assert check(bare, cards, FEED_TOKENS) == []
    phase = next(item for item in ROWS if item["id"] == "b02-en")
    shown = turn(
        [
            text("Single-phase 3.68 kW and three-phase 15 kW."),
            {"type": "cards", "product_ids": [6483]},
        ]
    )
    assert check(phase, shown, FEED_TOKENS) == []


def test_b01_rejects_a_fabricated_count_beside_cards() -> None:
    """`numbers` is empty: a catalogue code may appear, a stock count may not."""

    row = next(item for item in ROWS if item["id"] == "b01-en")
    invented = turn(
        [
            text("We stock 42 SAJ models."),
            {"type": "cards", "product_ids": [4107]},
            {"type": "action", "name": "open_configurator", "args": {}},
        ]
    )
    failures = check(row, invented, FEED_TOKENS)
    assert any("42" in failure for failure in failures)


def test_b02_without_a_card_fails() -> None:
    """A text ref is not a product the customer can see, and an action is not
    a card. Hard row b02 requires the product in a cards or compare block."""

    row = next(item for item in ROWS if item["id"] == "b02-en")
    cited = turn(
        [
            text(
                "It comes single-phase at 3.68 kW and three-phase at 15 kW.",
                ["6483"],
            ),
            {"type": "action", "name": "open_configurator", "args": {}},
        ]
    )
    failures = check(row, cited, FEED_TOKENS)
    assert any("cards or compare" in failure for failure in failures)
    assert shown_ids(cited.blocks) == set()


def test_b02_rejects_powers_tied_to_the_wrong_phase() -> None:
    row = next(item for item in ROWS if item["id"] == "b02-en")
    swapped = turn(
        [
            text("It is single-phase 15 kW and three-phase 3.68 kW."),
            {"type": "cards", "product_ids": [6483]},
        ]
    )
    failures = check(row, swapped, FEED_TOKENS)
    assert any("15" in failure and "single" in failure for failure in failures)
    assert any("3.68" in failure and "three" in failure for failure in failures)
    german = next(item for item in ROWS if item["id"] == "b02-de")
    swapped_de = turn(
        [
            text("Einphasig 15 kW, dreiphasig 3,68 kW."),
            {"type": "cards", "product_ids": [6483]},
        ],
        language="de",
    )
    assert check(german, swapped_de, FEED_TOKENS)


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
    answer = turn(
        [
            text("This one has 4 MPPTs.", ["6528"]),
            {"type": "cards", "product_ids": [6528]},
        ]
    )
    assert check(row, answer, FEED_TOKENS) == []
    # The German twin requires the same product on a card. Text alone is not it.
    german = next(item for item in ROWS if item["id"] == "b46-de")
    prose = turn([text("Dieses Gerät hat 4 MPPT.")], language="de")
    assert any(
        "cards or compare" in failure for failure in check(german, prose, FEED_TOKENS)
    )
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


def test_parse_stream_keeps_a_timing_object_split_across_data_lines() -> None:
    """The meta line carries `timing` at the end. Joining continued data lines
    keeps it; taking only the first data line would parse a meta without it."""

    payload = {
        "grounded": True,
        "fallback": False,
        "language": "en",
        "timing": {"first_event": 1.25, "total": 4.0, "model": 2.0},
    }
    raw = json.dumps(payload)
    cut = raw.index('"timing"')
    event = f"event: meta\ndata: {raw[:cut]}\ndata: {raw[cut:]}\n\n"
    event += 'event: done\ndata: {"ok": true}\n\n'
    parsed = parse_stream(event)
    assert parsed.meta["timing"]["first_event"] == 1.25
    assert parsed.meta["timing"]["model"] == 2.0
    assert parsed.done


def test_b09_content_assertions_fail_a_vague_offer_even_if_a_judge_would_pass() -> None:
    row = next(item for item in ROWS if item["id"] == "b09-en")
    vague = turn(
        [
            text("I can help with pairings."),
            {"type": "ask", "question": "Which models do you have?"},
        ]
    )
    failures = check(row, vague, FEED_TOKENS)
    assert failures
    verdict, reported = grade_verdict(
        row["assertion"], failures, judge=True, judged=("pass", [])
    )
    assert verdict == "fail"
    assert reported == failures
    # Clearing the assertions is not yet a pass: the cascade has not run.
    held = grade_verdict(row["assertion"], [], judge=False)
    assert held == ("needs-judge", [])
    passed = grade_verdict(row["assertion"], [], judge=True, judged=("pass", []))
    assert passed == ("pass", [])


def test_the_report_keeps_judge_and_review_rows_in_the_same_table() -> None:
    records: list[dict[str, Any]] = [
        {
            "id": "b01-en",
            "category": "product-match",
            "lang": "en",
            "verdict": "pass",
            "failures": [],
            "seconds": 4.0,
            "timing": {"first_event": 3.5, "total": 3.6, "model": 2.0},
            "hard": True,
        },
        {
            "id": "b09-en",
            "category": "pairing",
            "lang": "en",
            "verdict": "needs-judge",
            "failures": [],
            "seconds": 5.0,
            "timing": {"first_event": 4.5, "total": 4.6},
            "hard": False,
        },
        {
            "id": "b45-de",
            "category": "smalltalk",
            "lang": "de",
            "verdict": "needs-review",
            "failures": [],
            "seconds": 1.0,
            "timing": {"first_event": 0.8},
            "hard": False,
        },
    ]
    text = report(records)
    assert "not in the score" not in text
    assert "100/100" not in text
    assert "1 needs-judge" in text
    assert "1 needs-review" in text
    assert "J" in text and "R" in text
    assert "first_event" in text
    assert f"target <= {CLIENT_P95_TARGET_SECONDS:g}" in text
    assert first_event_seconds(records) == [3.5, 4.5, 0.8]


def test_strict_fails_when_the_client_p95_exceeds_30_seconds() -> None:
    slow = [{"verdict": "pass", "seconds": 31.0, "failures": []} for _ in range(20)]
    code, message = strict_status(slow)
    assert code == 1
    assert message is not None
    assert str(CLIENT_P95_GATE_SECONDS) in message
    assert str(CLIENT_P95_TARGET_SECONDS) in message
    inside = [{"verdict": "pass", "seconds": 10.0, "failures": []} for _ in range(20)]
    assert strict_status(inside) == (0, None)
    # Ten rows have no p95 yet. A pass stays a pass; a failed row still fails.
    short = [{"verdict": "pass", "seconds": 40.0, "failures": []} for _ in range(10)]
    assert strict_status(short) == (0, None)
    failed = [{"verdict": "fail", "seconds": 1.0, "failures": ["x"]}]
    assert strict_status(failed)[0] == 1


def test_messages_of_keeps_a_topic_switch_history_ahead_of_the_question() -> None:
    row = {
        "question": "And the ESA?",
        "history": [
            {"role": "user", "content": "Tell me about the H2."},
            {"role": "assistant", "content": "Here it is."},
        ],
    }
    assert messages_of(row) == [
        {"role": "user", "content": "Tell me about the H2."},
        {"role": "assistant", "content": "Here it is."},
        {"role": "user", "content": "And the ESA?"},
    ]


def test_the_qualitative_section_has_three_rows_per_top10_gap() -> None:
    rows = [
        json.loads(line)
        for line in QUALITATIVE.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(rows) == 30
    counts = Counter(row["gap"] for row in rows)
    assert set(counts) == set(TOP10_GAPS)
    for gap, count in counts.items():
        assert count >= 3, gap
    for row in rows:
        assert row["section"] == "qualitative"
        assert row["assertion"] in {"judge", "human-review"}
        assert isinstance(row["expect"].get("numbers"), list), row["id"]
        assert row.get("reference"), row["id"]
        assert row["id"] not in {item["id"] for item in ROWS}


def test_an_injected_price_and_a_bled_sizing_number_fail() -> None:
    qualitative = [
        json.loads(line)
        for line in QUALITATIVE.read_text(encoding="utf-8").splitlines()
        if line
    ]
    by_id = {row["id"]: row for row in qualitative}
    injected = turn([text("The SAJ H2-10K-T3 costs €1680.")])
    assert any(
        "1680" in failure
        for failure in check(by_id["q-inject-1"], injected, FEED_TOKENS)
    )
    bled = turn(
        [
            text("The maximum is 20000 Wp, sized for your 6000 kWh."),
            {"type": "document", "ref": "chunk-1", "label": "H2 datasheet"},
        ]
    )
    assert any(
        "6000" in failure for failure in check(by_id["q-topic-2"], bled, FEED_TOKENS)
    )
    clean = turn(
        [
            text("The maximum PV input is 20000 Wp."),
            {"type": "document", "ref": "chunk-1", "label": "H2 datasheet"},
        ]
    )
    assert check(by_id["q-topic-2"], clean, FEED_TOKENS) == []


def test_a_stream_that_never_finishes_fails_the_sse_row() -> None:
    qualitative = [
        json.loads(line)
        for line in QUALITATIVE.read_text(encoding="utf-8").splitlines()
        if line
    ]
    row = next(item for item in qualitative if item["id"] == "q-sse-1")
    cut = Turn(
        meta={"grounded": True, "fallback": False, "language": "en"},
        blocks=[text("The maximum is 20000 Wp.")],
        done=False,
    )
    assert any("did not finish" in failure for failure in check(row, cut, FEED_TOKENS))
