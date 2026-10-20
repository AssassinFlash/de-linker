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
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
    _clients,
    ask,
    close_clients,
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
            *expect.get("absence_any", []),
            *expect.get("no_clause", []),
            *expect.get("no_figure_on", []),
        ]
        for binding in expect.get("phase_powers", []):
            patterns.append(binding["label"])
        for binding in expect.get("figure_subjects", []):
            patterns.append(binding["subject"])
        for binding in expect.get("context_numbers", []):
            patterns.append(binding["context"])
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


def test_trial_6_allows_nominal_and_dod_beside_the_denial() -> None:
    """The nominal sentence and the L260 heading are not a usable-capacity figure.
    A number bound to that phrase still fails."""

    english = next(row for row in ROWS if row["id"] == "b20-en")
    stated = turn(
        _document(
            "### Usable capacity of the L260-OMNI\n"
            "Our documents do not state a separate usable-capacity figure for the "
            "L260-OMNI. The closest values the datasheet gives are the nominal "
            "capacity of 260 kWh and a depth of discharge of 98% for a single "
            "string, so the usable share of the nominal energy follows from that "
            "depth of discharge rather than from a stated usable figure."
        )
    )
    assert check(english, stated, FEED_TOKENS) == []
    bound = turn(_document("The usable capacity is the nominal 260 kWh."))
    assert check(english, bound, FEED_TOKENS)

    german = next(row for row in ROWS if row["id"] == "b20-de")
    stated_de = turn(
        _document(
            "Unsere Unterlagen weisen für den L260-OMNI keine eigene **nutzbare "
            "Kapazität** aus. Die Nennkapazität beträgt 260 kWh, die Entladetiefe 98%."
        ),
        language="de",
    )
    assert check(german, stated_de, FEED_TOKENS) == []
    verb_final = turn(
        _document(
            "Eine ausdrücklich als **nutzbare Kapazität** bezeichnete Angabe nennen "
            "unsere Unterlagen für den L260-OMNI nicht. Die Nennkapazität beträgt "
            "260 kWh, die Entladetiefe 98%."
        ),
        language="de",
    )
    assert check(german, verb_final, FEED_TOKENS) == []


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


def test_trial_19_allows_supports_inside_the_absence_sentence() -> None:
    """'do not state whether … supports' is the absence, not a support claim.
    A later clause that asserts support still fails."""

    english = next(row for row in ROWS if row["id"] == "b25-en")
    absence = turn(
        _document(
            "The documents do not state whether the SAJ H2 supports EnWG 14a dimming."
        )
    )
    assert check(english, absence, FEED_TOKENS) == []
    contrasted = turn(
        _document(
            "The documents do not state whether it is dimmed, but the SAJ H2 "
            "supports EnWG 14a."
        )
    )
    failures = check(english, contrasted, FEED_TOKENS)
    assert any("supports" in failure for failure in failures)

    german = next(row for row in ROWS if row["id"] == "b25-de")
    absence_de = turn(
        _document(
            "Die Unterlagen nennen keine Unterstützung, und sie sagen nicht, "
            "ob der SAJ H2 das Dimmen nach §14a EnWG unterstützt."
        ),
        language="de",
    )
    assert check(german, absence_de, FEED_TOKENS) == []
    claimed_de = turn(
        _document(
            "Die Unterlagen nennen keine Unterstützung. "
            "Der SAJ H2 unterstützt das Dimmen nach §14a EnWG."
        ),
        language="de",
    )
    assert check(german, claimed_de, FEED_TOKENS)


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


def _banned(failures: list[str]) -> bool:
    return any("banned figure" in failure for failure in failures)


def test_trial_6_rejects_comes_to_liegt_bei_apposition_and_not_but() -> None:
    """The judge's copulas and a number set against the phrase are the figure.
    'not 95 but 260' re-asserts 260. Bare 'nominal' is not another subject."""

    english = next(row for row in ROWS if row["id"] == "b20-en")
    comes_to = "The usable capacity comes to 260 kWh."
    nominal_model = "The usable capacity of the nominal L260 is 260 kWh."
    predicate = "The usable capacity is the nominal capacity of 260 kWh."
    apposition = "260 kWh usable capacity."
    not_but = "The usable capacity is not 95 kWh but 260 kWh."
    for words in (comes_to, nominal_model, predicate, apposition, not_but):
        failures = check(english, turn(_document(words)), FEED_TOKENS)
        assert _banned(failures), words

    german = next(row for row in ROWS if row["id"] == "b20-de")
    liegt = "Die nutzbare Kapazität liegt bei 260 kWh."
    liegt_filler = "Die nutzbare Kapazität liegt damit bei 260 kWh."
    apposition_de = "260 kWh nutzbare Kapazität."
    for words in (liegt, liegt_filler, apposition_de):
        failures = check(german, turn(_document(words), language="de"), FEED_TOKENS)
        assert _banned(failures), words


def test_trial_6_rejects_a_glued_unit_and_a_reassertion_after_and() -> None:
    """260kWh is the same figure as 260 kWh. and/und and a comma end the
    denial, the same way but does. and/und before the nominal noun does not."""

    english = next(row for row in ROWS if row["id"] == "b20-en")
    glued = turn(
        _document(
            "The documents do not state a usable capacity. "
            "The usable capacity is 260kWh. "
            "The nominal capacity is 260 kWh and the depth of discharge is 98%."
        )
    )
    failures = check(english, glued, FEED_TOKENS)
    assert _banned(failures), failures
    assert any("260kWh" in failure for failure in failures)
    assert not any("nominal capacity is" in failure for failure in failures)
    reasserted = "The usable capacity is not 95 kWh and is 260 kWh."
    comma = "The usable capacity is not 95 kWh, is 260 kWh."
    for words in (reasserted, comma):
        assert _banned(check(english, turn(_document(words)), FEED_TOKENS)), words
    kept = turn(
        _document(
            "The documents do not state a usable capacity. "
            "The usable capacity is not 95 kWh and the nominal capacity is 260 kWh "
            "and the depth of discharge is 98%."
        )
    )
    assert check(english, kept, FEED_TOKENS) == []

    german = next(row for row in ROWS if row["id"] == "b20-de")
    glued_de = turn(
        _document(
            "Die Unterlagen nennen keine nutzbare Kapazität. "
            "Die nutzbare Kapazität liegt bei 260kWh. "
            "Die Nennkapazität beträgt 260 kWh und die Entladetiefe 98%."
        ),
        language="de",
    )
    failures = check(german, glued_de, FEED_TOKENS)
    assert _banned(failures), failures
    assert any("260kWh" in failure for failure in failures)
    assert not any("Nennkapazität" in failure for failure in failures)
    und = "Die nutzbare Kapazität ist nicht 95 kWh und beträgt 260 kWh."
    comma_de = "Die nutzbare Kapazität ist nicht 95 kWh, sie beträgt 260 kWh."
    for words in (und, comma_de):
        failed = check(german, turn(_document(words), language="de"), FEED_TOKENS)
        assert _banned(failed), words
    kept_de = turn(
        _document(
            "Die Unterlagen nennen keine nutzbare Kapazität. "
            "Die nutzbare Kapazität beträgt nicht 95 kWh und die Nennkapazität "
            "beträgt 260 kWh und die Entladetiefe 98%."
        ),
        language="de",
    )
    assert check(german, kept_de, FEED_TOKENS) == []


def test_trial_6_rejects_inverted_copula_dash_bare_number_and_liegt_filler() -> None:
    """The copula can run backwards, a dash, colon or a bare number can present
    260, and liegt … bei can wrap the German phrase across any filler width.
    A separator presents with or without spaces around it."""

    english = next(row for row in ROWS if row["id"] == "b20-en")
    inverted = "The nominal capacity of 260 kWh is the usable capacity."
    dash = "The usable capacity — 260 kWh."
    bare = "The usable capacity 260 kWh."
    inverted_dash = "260 kWh — the usable capacity."
    inverted_colon = "260 kWh: the usable capacity."
    inverted_dash_unspaced = "260 kWh—the usable capacity."
    inverted_hyphen_spaced = "260 kWh - the usable capacity."
    inverted_colon_unspaced = "260 kWh:the usable capacity."
    inverted_dash_space_before = "260 kWh —the usable capacity."
    inverted_hyphen_unspaced = "260 kWh-the usable capacity."
    for words in (
        inverted,
        dash,
        bare,
        inverted_dash,
        inverted_colon,
        inverted_dash_unspaced,
        inverted_hyphen_spaced,
        inverted_colon_unspaced,
        inverted_dash_space_before,
        inverted_hyphen_unspaced,
    ):
        failures = check(english, turn(_document(words)), FEED_TOKENS)
        assert _banned(failures), words

    german = next(row for row in ROWS if row["id"] == "b20-de")
    liegt = "Beim Modell L260-OMNI liegt die nutzbare Energie bei 260 kWh."
    filler = "Die nutzbare Kapazität liegt damit bei 260 kWh."
    four_words = "Die nutzbare Kapazität liegt nach Angaben im Datenblatt bei 260 kWh."
    inverted_dash_de = "260 kWh – die nutzbare Kapazität."
    inverted_colon_de = "260 kWh: die nutzbare Kapazität."
    inverted_dash_unspaced_de = "260 kWh—die nutzbare Kapazität."
    inverted_hyphen_spaced_de = "260 kWh - die nutzbare Kapazität."
    inverted_colon_unspaced_de = "260 kWh:die nutzbare Kapazität."
    inverted_dash_space_before_de = "260 kWh —die nutzbare Kapazität."
    for words in (
        liegt,
        filler,
        four_words,
        inverted_dash_de,
        inverted_colon_de,
        inverted_dash_unspaced_de,
        inverted_hyphen_spaced_de,
        inverted_colon_unspaced_de,
        inverted_dash_space_before_de,
    ):
        failures = check(german, turn(_document(words), language="de"), FEED_TOKENS)
        assert _banned(failures), words


def test_trial_6_although_is_concessive_not_a_contrast() -> None:
    """'not stated although the nominal capacity is 260' states 260 as the
    nominal figure. although/though do not cancel the denial the way but does."""

    english = next(row for row in ROWS if row["id"] == "b20-en")
    concessive = turn(
        _document(
            "The documents do not state a usable capacity. "
            "The usable capacity is not stated although the nominal capacity is "
            "260 kWh and the depth of discharge is 98%."
        )
    )
    assert check(english, concessive, FEED_TOKENS) == []
    though = "The usable capacity is not stated though the nominal capacity is 260 kWh."
    assert not _banned(check(english, turn(_document(though)), FEED_TOKENS))


def test_trial_6_does_not_read_digits_inside_a_model_token() -> None:
    """'L260 usable capacity' is the model, not the figure 60 or 260."""

    english = next(row for row in ROWS if row["id"] == "b20-en")
    for words in ("L260 usable capacity.", "The L260 is the usable capacity."):
        failures = check(english, turn(_document(words)), FEED_TOKENS)
        assert not _banned(failures), words

    german = next(row for row in ROWS if row["id"] == "b20-de")
    model = "L260 nutzbare Kapazität."
    failures = check(german, turn(_document(model), language="de"), FEED_TOKENS)
    assert not _banned(failures), model


def test_trial_6_allows_the_nominal_noun_on_its_own_figure() -> None:
    """'nominal capacity of 260' passes when that noun labels 260.
    A comma or 'and' before that noun starts a new claim. A plain denial
    ('is not 260') does not."""

    english = next(row for row in ROWS if row["id"] == "b20-en")
    own_noun = turn(
        _document(
            "The documents do not state a usable capacity, the nominal capacity "
            "is 260 kWh and the depth of discharge is 98%."
        )
    )
    assert check(english, own_noun, FEED_TOKENS) == []
    denied = turn(
        _document(
            "The documents do not state a usable capacity. "
            "The usable capacity is not 260 kWh. "
            "The nominal capacity is 260 kWh and the depth of discharge is 98%."
        )
    )
    assert check(english, denied, FEED_TOKENS) == []

    german = next(row for row in ROWS if row["id"] == "b20-de")
    own_de = turn(
        _document(
            "Die Unterlagen nennen keine nutzbare Kapazität, die Nennkapazität "
            "beträgt 260 kWh und die Entladetiefe 98%."
        ),
        language="de",
    )
    assert check(german, own_de, FEED_TOKENS) == []
    bare_de = turn(
        _document(
            "Die Unterlagen nennen keine nutzbare Kapazität. "
            "Die Nennkapazität 260 kWh und die Entladetiefe 98% stehen im Datenblatt."
        ),
        language="de",
    )
    assert check(german, bare_de, FEED_TOKENS) == []


def test_trial_19_bounds_whether_and_accepts_that() -> None:
    """and/und starts a new claim. that/dass keeps the absence. A comma after
    the binder does too. 'supports EnWG and RCR' stays inside the absence."""

    english = next(row for row in ROWS if row["id"] == "b25-en")
    continued = turn(
        _document(
            "The documents do not state whether the H2 supports EnWG 14a, "
            "and the H2 supports EnWG 14a."
        )
    )
    failures = check(english, continued, FEED_TOKENS)
    assert any("supports" in failure for failure in failures)
    that = turn(
        _document(
            "The documents do not state that the SAJ H2 supports EnWG 14a dimming."
        )
    )
    assert check(english, that, FEED_TOKENS) == []
    and_inside = turn(
        _document(
            "The documents do not state whether the SAJ H2 supports EnWG 14a and RCR."
        )
    )
    assert check(english, and_inside, FEED_TOKENS) == []
    appositive = turn(
        _document(
            "The documents do not state whether the SAJ H2, a three-phase hybrid, "
            "supports EnWG 14a dimming."
        )
    )
    assert check(english, appositive, FEED_TOKENS) == []
    comma_after = turn(
        _document(
            "The documents do not state whether, the SAJ H2 supports EnWG 14a dimming."
        )
    )
    assert any(
        "supports" in failure for failure in check(english, comma_after, FEED_TOKENS)
    )

    german = next(row for row in ROWS if row["id"] == "b25-de")
    und = turn(
        _document(
            "Die Unterlagen nennen keine Unterstützung, und der SAJ H2 "
            "unterstützt das Dimmen nach §14a EnWG."
        ),
        language="de",
    )
    assert check(german, und, FEED_TOKENS)
    dass = turn(
        _document(
            "Die Unterlagen nennen keine Unterstützung dafür, dass der SAJ H2 "
            "das Dimmen nach §14a EnWG unterstützt."
        ),
        language="de",
    )
    assert check(german, dass, FEED_TOKENS) == []


def _cards(words: str, product_id: int, language: str = "en") -> Turn:
    return turn(
        [text(words), {"type": "cards", "product_ids": [product_id]}],
        language=language,
    )


def test_b03_binds_each_pv_figure_to_its_model() -> None:
    """40 kW is GW20K's PV input. On GW15K it fails. 30 kW is 3585's and
    2063's own, so on GW20K it fails the same way. 12 is H2-12K-T3's AC
    rating, a true figure of the second model the answer names; 40 is not
    allowlisted."""

    english = next(row for row in ROWS if row["id"] == "b03-en")
    assert english["expect"]["numbers"] == ["15", "5", "108", "30", "12"]
    borrowed = _cards("GW15K-ETA-G20 has 40 kW PV input.", 3585)
    failures = check(english, borrowed, FEED_TOKENS)
    assert any("not a figure of GW15K-ETA-G20" in failure for failure in failures)
    own = _cards("GW15K-ETA-G20 has 30 kW PV input.", 3585)
    assert check(english, own, FEED_TOKENS) == []
    borrowed_30 = _cards("GW20K-ETA-G20 has 30 kW PV input.", 3585)
    assert any(
        "not a figure of GW20K-ETA-G20" in failure
        for failure in check(english, borrowed_30, FEED_TOKENS)
    )
    neighbour = _cards("GW20K-ETA-G20 has 40 kW PV input.", 3585)
    assert check(english, neighbour, FEED_TOKENS) == []
    ecoflow = _cards("EF HD-P3-15K-G2 has 24 kW PV input.", 3585)
    assert check(english, ecoflow, FEED_TOKENS) == []
    series = _cards("The OCEAN range has 24 kW PV input.", 3585)
    assert any("not tied" in failure for failure in check(english, series, FEED_TOKENS))
    bare = _cards("The PV input is 40 kW.", 3585)
    assert any("not tied" in failure for failure in check(english, bare, FEED_TOKENS))

    german = next(row for row in ROWS if row["id"] == "b03-de")
    borrowed_de = _cards("Der GW15K-ETA-G20 hat 40 kW PV-Eingang.", 3585, "de")
    assert any(
        "not a figure of GW15K-ETA-G20" in failure
        for failure in check(german, borrowed_de, FEED_TOKENS)
    )
    own_de = _cards("Der GW15K-ETA-G20 hat 30 kW PV-Eingang.", 3585, "de")
    assert check(german, own_de, FEED_TOKENS) == []
    borrowed_30_de = _cards("Der GW20K-ETA-G20 hat 30 kW PV-Eingang.", 3585, "de")
    assert any(
        "not a figure of GW20K-ETA-G20" in failure
        for failure in check(german, borrowed_30_de, FEED_TOKENS)
    )


def test_b03_pairs_respectively_and_accepts_a_denial() -> None:
    """respectively pairs by order. A denial of 40 kW is not a claim of it."""

    english = next(row for row in ROWS if row["id"] == "b03-en")
    paired = _cards(
        "GW20K-ETA-G20 and GW15K-ETA-G20 have 40 and 30 kW, respectively.",
        3585,
    )
    assert check(english, paired, FEED_TOKENS) == []
    swapped = _cards(
        "GW20K-ETA-G20 and GW15K-ETA-G20 have 30 and 40 kW, respectively.",
        3585,
    )
    assert any(
        "not a figure of GW15K-ETA-G20" in failure
        for failure in check(english, swapped, FEED_TOKENS)
    )
    denial = _cards("The GW15K-ETA-G20 does not have 40 kW PV input.", 3585)
    assert check(english, denial, FEED_TOKENS) == []

    german = next(row for row in ROWS if row["id"] == "b03-de")
    paired_de = _cards(
        "Der GW20K-ETA-G20 und der GW15K-ETA-G20 haben 40 und 30 kW, respektive.",
        3585,
        "de",
    )
    assert check(german, paired_de, FEED_TOKENS) == []
    denial_de = _cards(
        "Der GW15K-ETA-G20 hat keine 40 kW PV-Eingang.",
        3585,
        "de",
    )
    assert check(german, denial_de, FEED_TOKENS) == []


def test_b25_binds_each_pv_figure_to_its_h2_model() -> None:
    """24/40/45 kW belong to H2-12K/20K/25K/30K. H2-15K does not own 40."""

    english = next(row for row in ROWS if row["id"] == "b25-en")
    assert "40" not in english["expect"]["numbers"]
    absence = (
        "The documents do not state whether the SAJ H2 supports EnWG 14a dimming. "
    )
    wrong = turn(_document(absence + "The H2-15K-T3 has 40 kW PV input."))
    failures = check(english, wrong, FEED_TOKENS)
    assert any("not a figure of H2-15K-T3" in failure for failure in failures)
    right = turn(_document(absence + "The H2-20K-T3 has 40 kW PV input."))
    assert check(english, right, FEED_TOKENS) == []
    watts = turn(_document(absence + "The H2-20K-T3 PV input is 40000 Wp."))
    assert check(english, watts, FEED_TOKENS) == []
    bare = turn(_document(absence + "The PV input is 40 kW."))
    assert any("not tied" in failure for failure in check(english, bare, FEED_TOKENS))

    german = next(row for row in ROWS if row["id"] == "b25-de")
    absence_de = "Die Unterlagen nennen keine Unterstützung für EnWG 14a. "
    wrong_de = turn(
        _document(absence_de + "Der H2-15K-T3 hat 40 kW PV-Eingang."),
        language="de",
    )
    assert any(
        "not a figure of H2-15K-T3" in failure
        for failure in check(german, wrong_de, FEED_TOKENS)
    )
    right_de = turn(
        _document(absence_de + "Der H2-20K-T3 hat 40 kW PV-Eingang."),
        language="de",
    )
    assert check(german, right_de, FEED_TOKENS) == []


def test_b25_restricts_4105_to_the_vde_ar_n_context() -> None:
    """VDE-AR-N 4105 is the Standard row on the H2 datasheets, not a figure:
    the digits as a measurement (4105 kWh, 4105000 Wh, 4105 A/W/V) fail."""

    english = next(row for row in ROWS if row["id"] == "b25-en")
    assert "4105" not in english["expect"]["numbers"]
    assert english["expect"]["context_numbers"] == [
        {"number": "4105", "context": "(?i)VDE-AR-N"}
    ]
    absence = "The documents do not state whether the SAJ H2 supports EnWG 14a. "
    named = turn(
        _document(
            absence + "The datasheet lists VDE-AR-N 4105 among the grid standards."
        )
    )
    assert check(english, named, FEED_TOKENS) == []
    # The clause naming the code does not license another 4105 in the same
    # clause: the occurrence must be the code's own number.
    for mixed_sentence in (
        "The datasheet lists VDE-AR-N 4105 and reports 4105 kWh.",
        "The datasheet lists VDE-AR-N 4105 for Germany, and the battery is 4105 kWh.",
    ):
        failures = check(
            english, turn(_document(absence + mixed_sentence)), FEED_TOKENS
        )
        assert any("context" in failure for failure in failures), mixed_sentence
    for sentence in (
        "The grid code is 4105 kWh.",
        "The grid code is 4105000 Wh.",
        "The current is 4105 A.",
        "The power is 4105 W.",
        "The voltage is 4105 V.",
    ):
        failures = check(english, turn(_document(absence + sentence)), FEED_TOKENS)
        assert any("context" in failure for failure in failures), sentence
        assert not any("in no expected fact" in failure for failure in failures), (
            sentence
        )

    german = next(row for row in ROWS if row["id"] == "b25-de")
    assert "4105" not in german["expect"]["numbers"]
    assert german["expect"]["context_numbers"] == english["expect"]["context_numbers"]
    absence_de = "Die Unterlagen nennen keine Unterstützung für EnWG 14a. "
    named_de = turn(
        _document(absence_de + "Das Datenblatt führt VDE-AR-N 4105 auf."),
        language="de",
    )
    assert check(german, named_de, FEED_TOKENS) == []
    for sentence in (
        "Die Netzregel ist 4105 kWh.",
        "Die Netzregel ist 4105000 Wh.",
        "Der Strom ist 4105 A.",
        "Die Leistung ist 4105 W.",
        "Die Spannung ist 4105 V.",
    ):
        failures = check(
            german, turn(_document(absence_de + sentence), language="de"), FEED_TOKENS
        )
        assert any("context" in failure for failure in failures), sentence


def test_b47_allows_the_manual_10_ms_switching_time() -> None:
    """The manual's '<10' switching row is an allowlisted 10. 11 ms is not."""

    english = next(row for row in ROWS if row["id"] == "b47-en")
    assert "10" in english["expect"]["numbers"]
    good = turn([text("The internal bypass passes grid power in 10 ms.", ["page"])])
    assert check(english, good, FEED_TOKENS) == []
    invented = turn([text("The internal bypass passes grid power in 11 ms.", ["page"])])
    assert any("11" in failure for failure in check(english, invented, FEED_TOKENS))

    german = next(row for row in ROWS if row["id"] == "b47-de")
    good_de = turn(
        [text("Der interne Bypass führt das Netz in 10 ms.", ["page"])],
        language="de",
    )
    assert check(german, good_de, FEED_TOKENS) == []


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


def test_b15_cabinet_dimensions_from_the_quick_guide_are_traceable() -> None:
    """Page 1 of the quick guide prints 1065 x 650 x 1221 mm beside the clearances.

    The cited chunk is a70cb4c39824-p1 ([n1=1065 mm], [n2=650 mm], [n3=1221 mm]).
    """
    row = next(item for item in ROWS if item["id"] == "b15-de")
    sized = turn(
        [
            text(
                "Maße des Schranks: 1065 mm Höhe, 650 mm Breite und 1221 mm Tiefe. "
                "Mindestabstand 1500 mm."
            ),
            {"type": "document", "ref": "a70cb4c39824-p1-5a1f6421"},
        ],
        language="de",
    )
    failures = check(row, sized, FEED_TOKENS)
    assert not any(item.startswith("number ") for item in failures), failures


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
    # A hyphenated accessory code (b09-de, EF BD-JC-S2) is a name. The digit
    # in the last segment is not a measurement. ground.bare_numbers agrees.
    assert (
        untraceable_numbers(
            "Für eine Kaskade ist der Anschlusskasten EF BD-JC-S2 erforderlich.",
            [],
        )
        == []
    )
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


def test_a_bare_number_in_a_product_name_is_not_figure_evidence() -> None:
    """The live catalogue's display names carry bare numbers ("SAJ H2-25K-T3
    (25 kW three-phase)", "EcoFlow OCEAN 2"). Splitting those into codes made
    every bare 25 or 2 in a name evidence for any figure in an answer. A
    mixed model/SKU part and a compound of catalogue parts are still codes."""

    catalog = {"SAJ H2-25K-T3": "SAJ H2-25K-T3 (25 kW three-phase)"}
    assert untraceable_numbers("The extension runs 25 months.", [], catalog) == ["25"]
    assert untraceable_numbers("The H2-25K-T3 is listed.", [], catalog) == []
    assert untraceable_numbers("The extension runs 25 months.", ["25"], catalog) == []

    bat = {"GW5.1-BAT-D-G20": "GoodWe GW5.1-BAT-D-G20 (5.12 kWh)"}
    assert untraceable_numbers("Die BAT-D-G20-Serie.", [], bat) == []
    assert untraceable_numbers("Die Serie hat 20 Module.", [], bat) == ["20"]
    # The range label mixes two catalogue models (GW3K-EHA-G20 and H2-10K-T3
    # supply the 3K and 10K parts); the 10K is a designation, not a figure.
    assert untraceable_numbers("The GW3K–10K-EHA-G20 range.", [], FEED_TOKENS) == []

    ocean = {"EcoFlow OCEAN 2": "EcoFlow OCEAN 2 (2 kWh)"}
    assert untraceable_numbers("The EcoFlow OCEAN 2.", [], ocean) == ["2"]


def test_trial_7_warranty_figures_are_row_values_not_catalogue_codes() -> None:
    """12, 15, 20, 25 and 30 are the warranty document's own periods and caps
    (a786dcf5aeef p.1 and p.4). They pass because the row lists them, not
    because a product name happens to contain the same digits."""

    row = next(item for item in ROWS if item["id"] == "b13-en")
    assert {"12", "15", "20", "25", "30"} <= set(row["expect"]["numbers"])
    sentence = (
        "The limited warranty runs 10 years from 2026: 12 months after "
        "production, 30 months for lower-power on-grid inverters, 20 kW rated "
        "power, 25 kW and above, and the Lynx window from 15 May 2023."
    )
    assert untraceable_numbers(sentence, row["expect"]["numbers"], FEED_TOKENS) == []
    assert untraceable_numbers(
        "The warranty runs 42 months.", row["expect"]["numbers"], FEED_TOKENS
    ) == ["42"]


def test_b14_export_limit_zero_is_the_manual_range() -> None:
    """0 is the Total Power lower bound [0 - 5000] on the H2 manual, index
    page 55 (chunk 770ccafa080c-p55-9908ba56, tagged n19). The production
    answer stated that range. Both language rows license the digit, because
    the German answer cites the same chunk. A figure the manual does not
    show still fails."""

    sentence = (
        "Enter the value in the field that appears; in the user manual the "
        "Total Power field is shown as a range from 0 to 5000."
    )
    for row_id in ("b14-en", "b14-de"):
        row = next(item for item in ROWS if item["id"] == row_id)
        assert "0" in row["expect"]["numbers"]
        assert (
            untraceable_numbers(sentence, row["expect"]["numbers"], FEED_TOKENS) == []
        )
        assert untraceable_numbers(
            "Set the export limit to 7.", row["expect"]["numbers"], FEED_TOKENS
        ) == ["7"]
    english = next(item for item in ROWS if item["id"] == "b14-en")
    shown = turn(
        [
            text(
                "Open Export/Generation Limitation Settings and set the "
                "export limit. " + sentence,
                ["770ccafa080c-p55-9908ba56"],
            ),
            {
                "type": "document",
                "ref": "770ccafa080c-p55-9908ba56",
                "label": "SAJ H2 10-30K user manual · p. 55",
                "url": "https://de-linker.com/manual.pdf#page=55",
            },
        ]
    )
    assert check(english, shown, FEED_TOKENS) == []


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


def test_b02_binds_each_bullets_powers_to_that_bullet() -> None:
    """The labels sit on their own bullet lines; the next bullet's label is
    not nearer just because a newline is a short character span. The r6 run
    read "4.6 kW" as three-phase and failed a correct answer."""

    row = next(item for item in ROWS if item["id"] == "b02-en")
    answer = turn(
        [
            text(
                "### Single-phase or three-phase\n\n"
                "The EcoFlow OCEAN range is offered in both versions: the product "
                "data lists single-phase hybrid inverters as well as three-phase "
                "hybrid inverters, and the cards below show the phase of each "
                "model.\n\n"
                "- Single-phase models, in the order of the cards below: 3 kW, "
                "3.68 kW and 4.6 kW.\n"
                "- Three-phase models, in the order of the cards below: 5 kW, "
                "6 kW and 8 kW."
            ),
            {"type": "cards", "product_ids": [6483]},
        ]
    )
    assert check(row, answer, FEED_TOKENS) == []

    # The same figures inside one prose line: the label that introduces the
    # list owns its numbers even though the next label is character-wise
    # nearer to 3.68 and 4.6.
    prose = turn(
        [
            text(
                "The versions shown below differ in phase and in rated AC "
                "power: the single-phase units are rated at 3 kW, 3.68 kW and "
                "4.6 kW, while the three-phase units are rated at 5 kW, 6 kW "
                "and 8 kW."
            ),
            {"type": "cards", "product_ids": [6483]},
        ]
    )
    assert check(row, prose, FEED_TOKENS) == []
    # A label right after its kW figure, or as the copula's predicate, owns
    # that figure.
    apposition = turn(
        [
            text("15 kW three-phase and 3.68 kW single-phase."),
            {"type": "cards", "product_ids": [6483]},
        ]
    )
    assert check(row, apposition, FEED_TOKENS) == []
    predicate = turn(
        [
            text(
                "Both single- and three-phase units exist; the 10 kW model is "
                "single-phase and the 15 kW model is three-phase."
            ),
            {"type": "cards", "product_ids": [6483]},
        ]
    )
    assert check(row, predicate, FEED_TOKENS) == []

    german = next(item for item in ROWS if item["id"] == "b02-de")
    answer_de = turn(
        [
            text(
                "Einphasige Modelle: 3 kW, 3,68 kW und 4,6 kW.\n"
                "Dreiphasige Modelle: 5 kW, 6 kW und 8 kW."
            ),
            {"type": "cards", "product_ids": [6483]},
        ],
        language="de",
    )
    assert check(german, answer_de, FEED_TOKENS) == []


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


def test_the_page_mppt_row_names_the_model_and_does_not_require_a_card() -> None:
    """b46 is a documents question about the page's own product. The answer
    names GW10K-EHA-G20 and its 4 MPPTs. A card may be present; it is not
    what the row requires."""

    row = next(item for item in ROWS if item["id"] == "b46-en")
    prose = turn([text("The GW10K-EHA-G20 has 4 MPPTs.")])
    assert check(row, prose, FEED_TOKENS) == []
    with_card = turn(
        [
            text("The GW10K-EHA-G20 has 4 MPPTs."),
            {"type": "cards", "product_ids": [6528]},
        ]
    )
    assert check(row, with_card, FEED_TOKENS) == []
    german = next(item for item in ROWS if item["id"] == "b46-de")
    german_prose = turn([text("Der GW10K-EHA-G20 hat 4 MPPT.")], language="de")
    assert check(german, german_prose, FEED_TOKENS) == []
    unnamed = turn([text("This one has 4 MPPTs.")])
    assert any(
        "GW10K-EHA-G20" in failure for failure in check(row, unnamed, FEED_TOKENS)
    )
    vague = turn([text("Which model do you mean?")])
    failures = check(row, vague, FEED_TOKENS)
    assert any("4" in failure or "MPPT" in failure for failure in failures)


def test_the_datasheet_row_accepts_the_document_without_a_card() -> None:
    """b05 asks where the L260 datasheet is. The documents route shows the
    document. A product card is optional."""

    row = next(item for item in ROWS if item["id"] == "b05-en")
    hosted = turn(
        _document(
            "The datasheet for the L260-OMNI states a nominal capacity of 260 kWh."
        )
    )
    assert check(row, hosted, FEED_TOKENS) == []
    with_card = turn(
        [
            *_document("The L260-OMNI datasheet states 260 kWh nominal."),
            {"type": "cards", "product_ids": [2003]},
        ]
    )
    assert check(row, with_card, FEED_TOKENS) == []
    nameless = turn(_document("The datasheet is hosted below."))
    assert any("L260" in failure for failure in check(row, nameless, FEED_TOKENS))


def test_the_pairing_row_still_requires_an_inverter_card() -> None:
    """b10's route is pairing. Text that names a released inverter is not the card."""

    row = next(item for item in ROWS if item["id"] == "b10-en")
    prose = turn([text("The GW10K-EHA-G20 is released with the GW9.0-BAT-D-G20.")])
    assert any(
        "cards or compare" in failure for failure in check(row, prose, FEED_TOKENS)
    )
    shown = turn(
        [
            text("Released pairing."),
            {"type": "cards", "product_ids": [6528]},
        ]
    )
    assert check(row, shown, FEED_TOKENS) == []


def test_the_rfq_row_reads_the_guest_page_sentence() -> None:
    """1957 is rfq_only. A guest Genie card uses the PAGE line, the partner
    sign-in sentence, not the approved-account 'Quoted per project'."""

    row = next(item for item in ROWS if item["id"] == "b22-en")
    guest = turn(
        [
            text("The GW208.9-BAT-LCD-G10 is a commercial battery."),
            {
                "type": "cards",
                "product_ids": [1957],
                "prices": [
                    {
                        "product_id": 1957,
                        "text": "Net price after partner sign-in",
                        "reason": "login",
                    }
                ],
            },
        ]
    )
    assert check(row, guest, FEED_TOKENS) == []
    quoted = turn(
        [
            text("The GW208.9-BAT-LCD-G10 is quoted per project."),
            {
                "type": "cards",
                "product_ids": [1957],
                "prices": [{"product_id": 1957, "text": "Quoted per project"}],
            },
        ]
    )
    assert any("price line" in failure for failure in check(row, quoted, FEED_TOKENS))
    german = next(item for item in ROWS if item["id"] == "b22-de")
    guest_de = turn(
        [
            text("Der GW208.9-BAT-LCD-G10 ist ein Gewerbespeicher."),
            {
                "type": "cards",
                "product_ids": [1957],
                "prices": [
                    {"product_id": 1957, "text": "Nettopreis nach Partner-Anmeldung"}
                ],
            },
        ],
        language="de",
    )
    assert check(german, guest_de, FEED_TOKENS) == []


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
    # 100 rows: ceil(0.5*100) is the 50th value, ceil(0.95*100) the 95th.
    values = [float(n) for n in range(1, 101)]
    assert percentile(values, 0.5) == 50.0
    assert percentile(values, 0.95) == 95.0
    assert percentile([], 0.5) is None
    # n=25, p50: ceil(12.5) is the 13th value. round(12.5) is 12 (banker's)
    # and is not this rule — the same split as production attempt_2 p50.
    assert percentile([float(n) for n in range(1, 26)], 0.5) == 13.0


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


# Equivalent absence wording from the contract and from the 2026-10-19 baseline.
# compatibility.json line 511: HD-P3 with GW*-BAT-D-G2[01] is not_released.
_B09_ABSENCE = (
    "This pairing is not released.",
    "The pairing is not documented as released.",
    "There is no documented pairing.",
    "Our data holds no released pairing for this combination.",
    "The cited documents do not list this pair.",
    "Die Prüfung ergibt keine Freigabe.",
    "Die Kombination ist nicht freigegeben.",
    "Die Kombination ist nicht dokumentiert.",
    "Es gibt kein dokumentiertes Pairing.",
    "Ihre Kombination führen unsere Unterlagen nicht auf.",
    "Ein dokumentiertes Pairing für das genannte Gerät gibt es nicht.",
    "Damit kann ich die Kombination nicht freigeben.",
    "Ohne dokumentierte Freigabe empfehle ich sie nicht.",
    "Dieses Modell führt unsere Produktdatenbank nicht.",
    # Turn 232, 2026-10-19T17:38:55Z. "do not list this pairing" did not match.
    "Our documents do not list a pairing between the EcoFlow inverter you named "
    "and the GoodWe battery module shown here.",
    # Turn 233, 2026-10-19T17:39:20Z. The comma splits "kein dokumentiertes Pairing".
    "Für die genannte Kombination kann ich kein dokumentiertes, freigegebenes "
    "Pairing bestätigen. Die Kombination ist nicht als freigegeben hinterlegt.",
)


def test_b09_accepts_equivalent_absence_phrasings() -> None:
    for row_id in ("b09-en", "b09-de"):
        row = next(item for item in ROWS if item["id"] == row_id)
        for phrase in _B09_ABSENCE:
            failures = check(
                row,
                turn(
                    [
                        text(phrase),
                        {"type": "document", "ref": "compat.document.3612.0"},
                    ],
                    language=row["lang"],
                ),
                FEED_TOKENS,
            )
            assert not any(item.startswith("missing /") for item in failures), (
                row_id,
                phrase,
                failures,
            )


def test_b09_still_rejects_a_release_claim() -> None:
    english = next(item for item in ROWS if item["id"] == "b09-en")
    german = next(item for item in ROWS if item["id"] == "b09-de")
    english_failures = check(
        english,
        turn(
            [
                text("This pair is released and can be combined."),
                {"type": "document", "ref": "compat.document.3612.0"},
            ]
        ),
        FEED_TOKENS,
    )
    german_failures = check(
        german,
        turn(
            [
                text("Das Paar ist freigegeben und kann kombiniert werden."),
                {"type": "document", "ref": "compat.document.3612.0"},
            ],
            language="de",
        ),
        FEED_TOKENS,
    )
    assert any("must not match" in item for item in english_failures)
    assert any("must not match" in item for item in german_failures)
    # A positive release of this battery, after an absence sentence, is still
    # a release claim. The narrow "this pair is released" guard used to pass it.
    false_english = check(
        english,
        turn(
            [
                text(
                    "There is no documented pairing. However, the "
                    "GW9.0-BAT-D-G20 battery is released with the EcoFlow "
                    "OCEAN 2 HD-P3-15K."
                ),
                {"type": "document", "ref": "compat.document.3612.0"},
            ]
        ),
        FEED_TOKENS,
    )
    false_german = check(
        german,
        turn(
            [
                text(
                    "Es gibt kein dokumentiertes Pairing. Die Batterie "
                    "GW9.0-BAT-D-G20 ist jedoch mit dem EcoFlow OCEAN 2 "
                    "HD-P3-15K freigegeben."
                ),
                {"type": "document", "ref": "compat.document.3612.0"},
            ],
            language="de",
        ),
        FEED_TOKENS,
    )
    assert any("must not match" in item for item in false_english)
    assert any("must not match" in item for item in false_german)
    # The EcoFlow batteries are released. Saying so beside the absence is the
    # contract, and it is not a release of the asked GoodWe pair.
    named = check(
        english,
        turn(
            [
                text(
                    "There is no documented pairing. Those pairings are released "
                    "with the conditions in the document."
                ),
                {"type": "cards", "product_ids": [6481]},
            ]
        ),
        FEED_TOKENS,
    )
    assert not any(
        "must not match" in item or item.startswith("missing /") for item in named
    )
    # A general rule ("a battery without a released verdict") is not a release
    # of this pair. The verb-first guard used to match it.
    general = check(
        english,
        turn(
            [
                text(
                    "A pairing between the GoodWe battery module you named and "
                    "the EcoFlow inverter is not documented in our product data. "
                    "Pairings are released per inverter and battery, and a battery "
                    "without a released verdict is not recommended."
                ),
                {"type": "document", "ref": "compat.document.3612.0"},
            ]
        ),
        FEED_TOKENS,
    )
    assert not any(
        "must not match" in item or item.startswith("missing /") for item in general
    ), general


def test_b10_absence_with_the_battery_card_fails() -> None:
    """Local b10-de said there was no pairing and showed card 3612, the battery.

    The battery is released. Absence fails for that reason even when a card
    is shown. 3612 is not a partner, so the partner-card rule also fails.
    The message is not "no documented pairing" — that sentence is for a
    battery the ground does not release.
    """
    row = next(item for item in ROWS if item["id"] == "b10-de")
    failures = check(
        row,
        turn(
            [
                text("Für die Batterie ist kein dokumentiertes Pairing hinterlegt."),
                {"type": "cards", "product_ids": [3612]},
            ],
            language="de",
        ),
        FEED_TOKENS,
    )
    assert any("released battery" in item for item in failures)
    assert any("none of products" in item for item in failures)
    assert not any("unrelated cards" in item for item in failures)
    assert not any("no documented pairing, but" in item for item in failures)


def test_b10_a_no_pairing_sentence_about_the_released_battery_fails() -> None:
    """compatibility.json line 1546 releases this battery. Absence is not a pass."""
    german = next(item for item in ROWS if item["id"] == "b10-de")
    english = next(item for item in ROWS if item["id"] == "b10-en")
    german_failures = check(
        german,
        turn(
            [
                text(
                    "Für die Batterie GW9.0-BAT-D-G20 gibt es kein "
                    "dokumentiertes Pairing."
                )
            ],
            language="de",
        ),
        FEED_TOKENS,
    )
    english_failures = check(
        english,
        turn([text("There is no documented pairing for this battery.")]),
        FEED_TOKENS,
    )
    assert any("released battery" in item for item in german_failures)
    assert any("none of products" in item for item in german_failures)
    assert any("released battery" in item for item in english_failures)
    assert any("none of products" in item for item in english_failures)


def test_b10_a_no_pairing_sentence_fails_even_with_a_partner_card() -> None:
    """The released rule is unconditional: the card does not excuse absence.

    grade.py:532 fails a no-pairing sentence on a released row before the
    partner-card check runs, so a partner card cannot turn it into a pass.
    """
    row = next(item for item in ROWS if item["id"] == "b10-en")
    failures = check(
        row,
        turn(
            [
                text("There is no documented pairing for this battery."),
                {"type": "cards", "product_ids": [6528]},
                {"type": "document", "ref": "compat.document.3612.0"},
            ]
        ),
        FEED_TOKENS,
    )
    assert any("released battery" in item for item in failures)
    assert not any("none of products" in item for item in failures)


def test_b10_a_partner_card_passes() -> None:
    row = next(item for item in ROWS if item["id"] == "b10-en")
    failures = check(
        row,
        turn(
            [
                text("These inverters have a released pairing."),
                {"type": "cards", "product_ids": [6528]},
                {"type": "document", "ref": "compat.document.3612.0"},
            ]
        ),
        FEED_TOKENS,
    )
    assert not any("products" in item or "unrelated" in item for item in failures)


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


class _KeepAliveHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        body = json.dumps(
            {
                "conversation_id": "1",
                "stream": 'event: meta\ndata: {"language": "en"}\n\n'
                'event: done\ndata: {"ok": true}\n\n',
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class _CountingServer(ThreadingHTTPServer):
    def __init__(
        self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler]
    ) -> None:
        self.accepts = 0
        super().__init__(address, handler)

    def get_request(self) -> tuple[Any, Any]:
        connection, address = super().get_request()
        self.accepts += 1
        return connection, address


def test_ask_reuses_one_connection_and_retries_a_dead_socket() -> None:
    close_clients()
    server = _CountingServer(("127.0.0.1", 0), _KeepAliveHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    row = {"lang": "en", "question": "Is the EcoFlow OCEAN 2 single-phase?"}
    wp = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        first, first_error = ask(wp, row)
        second, second_error = ask(wp, row)
        assert first_error is None and second_error is None
        assert first.done and second.done
        assert server.accepts == 1
        pooled = next(iter(_clients.values()))
        assert pooled.sock is not None
        pooled.sock.close()
        third, third_error = ask(wp, row)
        assert third_error is None and third.done
        assert server.accepts == 2
    finally:
        close_clients()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
