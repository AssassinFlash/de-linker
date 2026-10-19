"""Pure helpers in the battery. Nothing here posts, edits, or reads a live instance."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import grade
import run_battery


def test_ports_reads_one_instance_table(tmp_path: Path) -> None:
    table = tmp_path / "instances.toml"
    table.write_text(
        "[other]\nport = 1\ngenine_port = 2\n\n"
        "[c335]\nport = 9190\nengine_port = 9191\ngenie_port = 9192\n\n"
        "[next]\nport = 9\n",
        encoding="utf-8",
    )
    found = run_battery.ports("c335", table)
    assert found == {"port": 9190, "engine_port": 9191, "genie_port": 9192}


def test_ports_rejects_a_table_without_the_genie_port(tmp_path: Path) -> None:
    table = tmp_path / "instances.toml"
    table.write_text("[c335]\nport = 9190\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="no ports"):
        run_battery.ports("c335", table)


def test_address_gap_asks_only_for_the_postal_address() -> None:
    page = (
        "Linker Technology GmbH Steinfeldstraße 3 39179 Barleben "
        "HRB 33824 sales@de-linker.com"
    )
    assert run_battery.postal_codes(page) == ["39179"]
    assert (
        run_battery.address_gap(page, "Steinfeldstraße 3, 39179 Barleben, Deutschland")
        == []
    )
    assert run_battery.address_gap(page, "I could not answer this time.") == [
        "answer misses the postal address 39179"
    ]
    assert run_battery.address_gap("no address here", "39179") == [
        "page text has no postal address"
    ]


def test_mail_grade_checks_the_rendered_sentence_not_the_tool_link() -> None:
    email = "sales@de-linker.com"
    case = {
        "id": "T-mail",
        "expect_cards": False,
        "expect_handoff": True,
        "expect_numbers": False,
    }
    en = {
        "blocks": [
            {"type": "handoff", "summary": grade.HANDOFF_EN.format(email=email)}
        ],
        "answer": grade.HANDOFF_EN.format(email=email),
        "log": {"mailto": ""},
    }
    de = {
        "blocks": [
            {"type": "handoff", "summary": grade.HANDOFF_DE.format(email=email)}
        ],
        "answer": grade.HANDOFF_DE.format(email=email),
        "log": {"mailto": f"mailto:{email}"},
    }
    row = run_battery.grade_twin(case, en, de, None)
    assert row["mechanical"] == "pass"
    assert row["reasons"] == []
    assert row["customer_mailto_link"] is False
    assert "Handoff.tsx" in row["mailto_limitation"]
    assert row["tool_mailto"]["en"] == ""


def test_mppt_document_count_is_a_note_in_the_twin_record() -> None:
    case = {
        "id": "T-mppt",
        "expect_cards": False,
        "expect_handoff": False,
        "expect_numbers": True,
    }
    en = {
        "blocks": [
            {"type": "text", "text": "It has 3 trackers and 2 strings."},
            {"type": "document"},
            {"type": "document"},
            {"type": "document"},
        ],
        "answer": "It has 3 trackers and 2 strings.",
        "log": {},
    }
    de = {
        "blocks": [
            {
                "type": "text",
                "text": "Er hat 3 Tracker und 2 Strings, von 180 bis 900.",
            },
            {"type": "document"},
        ],
        "answer": "Er hat 3 Tracker und 2 Strings, von 180 bis 900.",
        "log": {},
    }
    row = run_battery.grade_twin(case, en, de, None)
    assert row["mechanical"] == "note"
    assert row["reasons"] == []
    assert any("document count en 3 de 1" in note for note in row["notes"])


def test_pair_numbers_are_graded() -> None:
    case = next(item for item in run_battery.TWINS if item["id"] == "T-pair")
    assert case["expect_numbers"] is True
    en = {
        "blocks": [
            {"type": "text", "text": "The set is 5, 10, 15, 20 and 25 kWh."},
            {"type": "cards", "product_ids": [1]},
        ],
        "answer": "The set is 5, 10, 15, 20 and 25 kWh.",
        "log": {},
    }
    de = {
        "blocks": [
            {"type": "text", "text": "Das Set hat 5 kWh."},
            {"type": "cards", "product_ids": [1]},
        ],
        "answer": "Das Set hat 5 kWh.",
        "log": {},
    }
    row = run_battery.grade_twin(case, en, de, None)
    assert row["mechanical"] == "note"
    assert row["reasons"] == []
    assert "10" in row["notes"][0]


def test_fallback_is_not_a_language_pass() -> None:
    reasons = run_battery.grade_language(
        "Wie viele MPPT-Tracker hat er?",
        "Zu Ihrer Frage habe ich Folgendes gefunden.",
        "en",
        {"fallback": True, "failures": ["model text contains numbers"]},
    )
    assert reasons == ["fallback is not a pass under gate 5"]
    row = run_battery.language_record(
        "L-switch-en",
        "Wie viele MPPT-Tracker hat er?",
        "Zu Ihrer Frage habe ich Folgendes gefunden.",
        "en",
        {"fallback": True},
    )
    assert row["mechanical"] == "defect"
    assert row["report_only"] is True
    assert row["fallback"] is True
    clean = run_battery.grade_language(
        "Wie viele MPPT-Tracker hat er?",
        "Er hat 3 Tracker und 2 Strings.",
        "en",
        {"fallback": False},
    )
    assert clean == []


def test_failed_translate_states_the_unmeasured_half() -> None:
    graded = run_battery.grade_translation(
        code=1,
        de_title_before="SAJ H2-10K-T3 (10 kW)",
        de_title_after="SAJ H2-10K-T3 (10 kW)",
        en_title="SAJ H2-10K-T3 C335DRIFT (10 kW)",
        marker="C335DRIFT",
    )
    assert graded["measured"] is False
    assert graded["mechanical"] == "defect"
    assert "#406" in graded["limitation"]
    assert "attribute numbers" in graded["limitation"]
    assert "prices" in graded["limitation"]


def test_successful_translate_grades_title_attributes_and_prices() -> None:
    en_product: dict[str, Any] = {
        "name": "SAJ H2-10K-T3 C335DRIFT (10 kW)",
        "sku": "DLK-SAJ-H210KT3",
        "attributes": [{"name": "MPPT", "terms": ["3"]}],
        "prices": {
            "currency_code": "EUR",
            "price": "168000",
            "regular_price": "168000",
        },
    }
    de_product: dict[str, Any] = {
        "name": "SAJ H2-10K-T3 C335DRIFT (10 kW)",
        "sku": "DLK-SAJ-H210KT3",
        "attributes": [{"name": "MPPT", "terms": ["3"]}],
        "prices": {
            "currency_code": "EUR",
            "price": "168000",
            "regular_price": "168000",
        },
    }
    graded = run_battery.grade_translation(
        code=0,
        de_title_before="SAJ H2-10K-T3 (10 kW)",
        de_title_after="SAJ H2-10K-T3 C335DRIFT (10 kW)",
        en_title="SAJ H2-10K-T3 C335DRIFT (10 kW)",
        marker="C335DRIFT",
        en_product=en_product,
        de_product=de_product,
    )
    assert graded["measured"] is True
    assert graded["mechanical"] == "pass"
    assert graded["limitation"] is None
    drifted = dict(de_product)
    drifted["prices"] = {"currency_code": "EUR", "price": "1"}
    failed = run_battery.grade_translation(
        code=0,
        de_title_before="before",
        de_title_after="SAJ H2-10K-T3 C335DRIFT (10 kW)",
        en_title="SAJ H2-10K-T3 C335DRIFT (10 kW)",
        marker="C335DRIFT",
        en_product=en_product,
        de_product=drifted,
    )
    assert failed["mechanical"] == "defect"
    assert any(reason.startswith("prices ") for reason in failed["reasons"])


def test_read_page_text_ignores_the_shell_title() -> None:
    raw = (
        '[{"name": "linker/read-page", "result": {'
        '"title": "SAJ H2-10K-T3 C335DRIFT (10 kW)", '
        '"text": "10 kW three-phase hybrid inverter"}}]'
    )
    assert "C335DRIFT" not in run_battery.read_page_text(raw)
    body = (
        '[{"name": "linker/read-page", "result": {'
        '"title": "old", "text": "C335DRIFT beacon at the end"}}]'
    )
    assert "C335DRIFT" in run_battery.read_page_text(body)
    assert (
        grade.drift_attribution(
            http_has_marker=True,
            tool_called=True,
            tool_has_marker="C335DRIFT" in run_battery.read_page_text(raw),
            answer_has_marker=False,
        )
        == "stale-cache"
    )
    assert (
        grade.drift_attribution(
            http_has_marker=True,
            tool_called=True,
            tool_has_marker=False,
            answer_has_marker=True,
        )
        == "title-fresh-body-stale"
    )


def test_restore_reads_the_snapshot_not_a_later_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = run_battery.snapshot_field(
        tmp_path, "title-original-4107.txt", "SAJ H2-10K-T3 (10 kW hybrid)"
    )
    remembered = "SAJ H2-10K-T3 C335DRIFT (10 kW hybrid)"
    seen: dict[str, object] = {}

    def fake_update(
        instance: str, post_id: int, field: str, value: str, directory: Path
    ) -> None:
        seen["instance"] = instance
        seen["post_id"] = post_id
        seen["field"] = field
        seen["value"] = value
        seen["directory"] = directory

    monkeypatch.setattr(run_battery, "wp_update", fake_update)
    run_battery.restore_snapshot("c335", 4107, "post_title", snapshot, tmp_path)
    assert seen["value"] == "SAJ H2-10K-T3 (10 kW hybrid)"
    assert seen["value"] != remembered
    assert seen["post_id"] == 4107
    assert seen["field"] == "post_title"


def test_exit_code_asserts_mail_growth_and_a_missed_restore() -> None:
    assert (
        run_battery.exit_code(
            mail_before=[], mail_after=[], drift_ran=False, restored=None
        )
        == 0
    )
    assert (
        run_battery.exit_code(
            mail_before=[], mail_after=["note.eml"], drift_ran=False, restored=None
        )
        == 1
    )
    assert (
        run_battery.exit_code(
            mail_before=[], mail_after=[], drift_ran=True, restored=False
        )
        == 1
    )
    assert (
        run_battery.exit_code(
            mail_before=[], mail_after=[], drift_ran=True, restored=True
        )
        == 0
    )


def test_discover_pairs_the_store_product_with_named_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_wp(_instance: str, _php: str) -> dict[str, Any]:
        return {
            "cart": {
                "id": 1,
                "en": "http://127.0.0.1:9190/cart/",
                "de": "http://127.0.0.1:9190/de/warenkorb/",
            },
            "imprint": {
                "id": 2,
                "en": "http://127.0.0.1:9190/imprint/",
                "de": "http://127.0.0.1:9190/de/impressum/",
            },
            "faq": {
                "id": 3,
                "en": "http://127.0.0.1:9190/faq-download/",
                "de": "",
            },
            "blog": {
                "id": 5,
                "en": "http://127.0.0.1:9190/post/",
                "de": "http://127.0.0.1:9190/de/post/",
            },
            "category": {
                "id": 6,
                "name": "Inverters",
                "en": "http://127.0.0.1:9190/c/",
                "de": "http://127.0.0.1:9190/de/c/",
                "de_name": "Wechselrichter",
            },
        }

    def fake_store(origin: str, lang: str) -> dict[str, Any]:
        return {
            "lang": lang,
            "id": 4107,
            "name": "SAJ H2-10K-T3 (10 kW)",
            "sku": "DLK",
            "permalink": f"{origin}/{lang}/product/",
            "prices": {"price": "100"},
            "attributes": [],
        }

    def fake_page(_origin: str, url: str) -> dict[str, Any]:
        return {
            "requested": url,
            "url": url,
            "status": 200,
            "error": None,
            "h1": "H",
            "prompts": [],
            "page": {"type": "other", "title": "T"},
            "context": {"type": "other", "url": url},
            "de_url": "http://127.0.0.1:9190/de/",
            "main": "39179 Barleben",
            "emails": [],
            "plz": ["39179"],
        }

    monkeypatch.setattr(run_battery, "wp_json", fake_wp)
    monkeypatch.setattr(run_battery, "store_product", fake_store)
    monkeypatch.setattr(run_battery, "load_page", fake_page)
    found = run_battery.discover("http://127.0.0.1:9190", "c335")
    assert found["surfaces"]["product"]["en"]["url"].endswith("/en/product/")
    assert found["surfaces"]["imprint"]["en"]["url"].endswith("/imprint/")
    assert found["surfaces"]["draft"]["en"]["url"].endswith("/cart/")
    assert found["surfaces"]["home"]["de"]["url"].endswith("/de/")
    assert found["attribute_reasons"] == []
