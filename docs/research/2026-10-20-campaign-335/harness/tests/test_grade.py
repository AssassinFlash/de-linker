"""The #335 bars, locked before the live battery grades a turn."""

from __future__ import annotations

from typing import Any

from grade import (
    HANDOFF_DE,
    HANDOFF_EN,
    answer_language_reasons,
    banned_words,
    drift_attribution,
    du_pronouns,
    handoff_reasons,
    language_of,
    money_in,
    price_reasons,
    prompt_reasons,
    standalone_numbers,
    title_with_marker,
    twin_notes,
    twin_reasons,
)


def test_banned_words_cover_the_ticket_list() -> None:
    text = (
        "Add it to the basket and open the catalogue article. "
        "Legen Sie es in den Warenkorb und öffnen Sie den Katalog-Artikel."
    )
    found = set(banned_words(text))
    assert "basket" in found
    assert "catalogue" in found
    assert "article" in found
    assert "warenkorb" in found
    assert "katalog" in found
    assert "artikel" in found
    assert banned_words("catalog") == ["catalog"]
    assert banned_words("cart") == ["cart"]
    assert banned_words("Einkaufswagen") == ["einkaufswagen"]
    assert banned_words("a product category") == []


def test_du_form_does_not_eat_direkt_or_dichtung() -> None:
    assert du_pronouns("Direkt an die Dichtung.") == []
    assert du_pronouns("Du kannst das dir merken.") == ["du", "dir"]
    assert du_pronouns("Prüfen Sie Ihre Angaben.") == []


def test_numbers_ignore_model_codes_and_accept_a_german_comma() -> None:
    assert standalone_numbers("The H2-10K-T3 has 2 MPPTs and 10 kW.") == ["2", "10"]
    assert standalone_numbers("2 MPPT und 10,5 kW") == ["2", "10.5"]


def test_language_vote_follows_closed_class_words() -> None:
    assert language_of("Which batteries pair with this inverter?") == "en"
    assert language_of("Welche Batterien passen zu diesem Wechselrichter?") == "de"
    assert language_of("H2-10K-T3") == "neutral"
    assert language_of("Welche battery passt for a house?") == "mixed"
    assert language_of("Nettopreis nach Partner-Anmeldung") == "de"


def test_twin_card_set_and_handoff_sentence() -> None:
    email = "sales@de-linker.com"
    en: list[dict[str, Any]] = [
        {"type": "text", "text": "These batteries pair with this inverter."},
        {"type": "cards", "product_ids": [3, 1]},
    ]
    de: list[dict[str, Any]] = [
        {"type": "text", "text": "Diese Batterien passen zu diesem Wechselrichter."},
        {"type": "cards", "product_ids": [1, 3]},
    ]
    assert (
        twin_reasons(
            en, de, expect_cards=True, expect_handoff=False, expect_numbers=False
        )
        == []
    )
    mismatched: list[dict[str, Any]] = [
        {"type": "text", "text": "Diese Batterie passt."},
        {"type": "cards", "product_ids": [1]},
    ]
    reasons = twin_reasons(
        en, mismatched, expect_cards=True, expect_handoff=False, expect_numbers=False
    )
    assert any(reason.startswith("card set") for reason in reasons)
    en_h: list[dict[str, Any]] = [
        {"type": "handoff", "summary": HANDOFF_EN.format(email=email)}
    ]
    de_h: list[dict[str, Any]] = [
        {"type": "handoff", "summary": HANDOFF_DE.format(email=email)}
    ]
    assert (
        twin_reasons(
            en_h, de_h, expect_cards=False, expect_handoff=True, expect_numbers=False
        )
        == []
    )
    paraphrased = [{"type": "handoff", "summary": f"Schreiben Sie an {email}."}]
    assert handoff_reasons(en_h[0]["summary"], paraphrased[0]["summary"])


def test_document_count_and_extra_figures_are_notes() -> None:
    en: list[dict[str, Any]] = [
        {"type": "text", "text": "It has 3 trackers and 2 strings."},
        {"type": "document"},
        {"type": "document"},
        {"type": "document"},
    ]
    de: list[dict[str, Any]] = [
        {"type": "text", "text": "Er hat 3 Tracker und 2 Strings, von 180 bis 900."},
        {"type": "document"},
    ]
    assert (
        twin_reasons(
            en, de, expect_cards=False, expect_handoff=False, expect_numbers=True
        )
        == []
    )
    notes = twin_notes(en, de, expect_numbers=True)
    assert any(note.startswith("document count en 3 de 1") for note in notes)
    assert any("180" in note and "900" in note for note in notes)
    assert any("shared figures match" for note in notes)


def test_omitted_kwh_steps_are_graded_as_a_note() -> None:
    en = [{"type": "text", "text": "The set is 5, 10, 15, 20 and 25 kWh."}]
    de = [{"type": "text", "text": "Das Set hat 5 kWh."}]
    assert (
        twin_reasons(
            en, de, expect_cards=False, expect_handoff=False, expect_numbers=True
        )
        == []
    )
    notes = twin_notes(en, de, expect_numbers=True)
    assert len(notes) == 1
    assert "5,10,15,20,25" in notes[0]
    assert notes[0].endswith("shared figures match and one side adds figures")


def test_disjoint_figures_stay_a_defect() -> None:
    en = [{"type": "text", "text": "It has 3 trackers."}]
    de = [{"type": "text", "text": "Er hat 4 Tracker."}]
    reasons = twin_reasons(
        en, de, expect_cards=False, expect_handoff=False, expect_numbers=True
    )
    assert any(reason.startswith("numbers en 3 de 4") for reason in reasons)
    assert twin_notes(en, de, expect_numbers=True) == []


def test_guest_price_line_rejects_a_sum_and_the_other_language() -> None:
    assert (
        price_reasons(
            [
                {
                    "product_id": 1,
                    "text": "Net price after partner sign-in",
                    "reason": "login",
                }
            ],
            "en",
            guest=True,
        )
        == []
    )
    german = price_reasons(
        [
            {
                "product_id": 1,
                "text": "Net price after partner sign-in",
                "reason": "login",
            }
        ],
        "de",
        guest=True,
    )
    assert german
    leaked = price_reasons(
        [{"product_id": 1, "text": "1.680,00 €", "reason": "login"}],
        "de",
        guest=True,
    )
    assert any("sum" in reason for reason in leaked)
    assert money_in("€1,680.00")


def test_prompts_name_the_page_and_keep_sie_form() -> None:
    assert (
        prompt_reasons(
            [
                "What pairs with the SAJ H2-10K-T3?",
                "Show the documents for the SAJ H2-10K-T3",
            ],
            "en",
            must_name="SAJ H2-10K-T3",
        )
        == []
    )
    german = prompt_reasons(
        ["Legen Sie es in den Warenkorb", "Was passt zum SAJ H2-10K-T3?"],
        "de",
        must_name="SAJ H2-10K-T3",
    )
    assert any("banned" in reason for reason in german)
    assert prompt_reasons(["Check my draft"], "en", minimum=2)


def test_drift_attribution_names_the_layer() -> None:
    assert (
        drift_attribution(
            http_has_marker=True,
            tool_called=True,
            tool_has_marker=False,
            answer_has_marker=False,
        )
        == "stale-cache"
    )
    assert (
        drift_attribution(
            http_has_marker=True,
            tool_called=True,
            tool_has_marker=False,
            answer_has_marker=True,
        )
        == "title-fresh-body-stale"
    )
    assert (
        drift_attribution(
            http_has_marker=True,
            tool_called=True,
            tool_has_marker=True,
            answer_has_marker=False,
        )
        == "model-ignored-fresh-page"
    )
    assert (
        drift_attribution(
            http_has_marker=True,
            tool_called=True,
            tool_has_marker=True,
            answer_has_marker=True,
        )
        == "fresh"
    )
    assert (
        drift_attribution(
            http_has_marker=False,
            tool_called=False,
            tool_has_marker=False,
            answer_has_marker=False,
        )
        == "edit-not-rendered"
    )
    assert (
        drift_attribution(
            http_has_marker=True,
            tool_called=False,
            tool_has_marker=False,
            answer_has_marker=True,
        )
        == "answered-from-prompt-title"
    )


def test_title_marker_stays_in_the_short_name() -> None:
    titled = title_with_marker("SAJ H2-10K-T3 (10 kW hybrid)", "C335DRIFT")
    assert titled == "SAJ H2-10K-T3 C335DRIFT (10 kW hybrid)"
    assert title_with_marker("Bare title", "C335DRIFT") == "Bare title C335DRIFT"


def test_answer_language_follows_a_clear_question_and_the_page_when_mixed() -> None:
    assert answer_language_reasons(
        "How many MPPT trackers does it have?",
        "Dieser Wechselrichter hat zwei Tracker.",
        "de",
    ) == ["answer de, want en"]
    assert (
        answer_language_reasons(
            "Welche battery für das house?",
            "Which battery fits a house?",
            "en",
        )
        == []
    )
    assert (
        answer_language_reasons("H2-10K-T3", "Der Wechselrichter ist dieser.", "de")
        == []
    )
