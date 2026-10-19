"""One test per triage branch, plus the sizing URL parser and the fixture scan."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cases
import run_battery
from run_battery import build_parser, configurator_prefill, triage

FEED: dict[str, Any] = {
    "products": [
        {
            "id": 1,
            "model": "H2-10K-T3",
            "figures": {},
            "ac_power_kw": 10,
            "pv_input_kw": 20,
            "usable_kwh": None,
            "nominal_kwh": None,
            "phase": 3,
            "series": "H2",
        },
        {
            "id": 9,
            "model": "CHS2-75K-T8-X",
            "figures": {},
            "ac_power_kw": None,
            "pv_input_kw": None,
            "usable_kwh": None,
            "nominal_kwh": None,
            "phase": 3,
            "series": "CHS2",
        },
    ]
}


def _case(
    request: str = "Is the H2-10K-T3 in stock?",
    lang: str = "en",
    expect: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": "T",
        "class": "units",
        "lang": lang,
        "request": request,
        "expect": {} if expect is None else expect,
    }


def _meta(language: str = "en", **extra: Any) -> dict[str, Any]:
    meta: dict[str, Any] = {"language": language, "turn_id": 1, "fallback": False}
    meta.update(extra)
    return meta


def _cut(
    case: dict[str, Any],
    blocks: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
    http: int | None = 200,
    error: str | None = None,
) -> dict[str, Any]:
    return triage(
        case,
        meta if meta is not None else _meta(str(case["lang"])),
        blocks,
        FEED,
        1.0,
        http,
        error,
    )


def _flags(result: dict[str, Any]) -> str:
    return " | ".join(result["flags"])


def test_error_is_triage_error() -> None:
    result = _cut(_case(), [], meta=None, http=None, error="timed out")
    assert result["verdict"] == "TRIAGE_ERROR"
    assert result["flags"] == ["timed out"]


def test_http_not_200_is_triage_defect() -> None:
    result = _cut(_case(), [], meta=None, http=500)
    assert result["verdict"] == "TRIAGE_DEFECT"
    assert result["flags"] == ["http 500"]


def test_language_mismatch() -> None:
    result = _cut(_case(), [{"type": "text", "text": "In stock?"}], meta=_meta("de"))
    assert "language 'de' != 'en'" in _flags(result)


def test_fallback() -> None:
    result = _cut(
        _case(),
        [{"type": "text", "text": "Here are matching products?"}],
        meta=_meta(fallback=True, failures=["model text contains numbers"]),
    )
    assert "fallback turn" in _flags(result)


def test_min_chars() -> None:
    result = _cut(
        _case(request="hi", expect={"min_chars": 10}),
        [{"type": "text", "text": "What do you need?"}],
    )
    assert "case shorter than designed" in _flags(result)


def test_missing_expect_ids() -> None:
    result = _cut(
        _case(expect={"expect_ids": [1]}),
        [{"type": "text", "text": "Which one?"}],
    )
    assert "missing expected product 1" in _flags(result)


def test_any_ids_miss() -> None:
    result = _cut(
        _case(expect={"any_ids": [1, 2]}),
        [{"type": "text", "text": "Which one?"}],
    )
    assert "no expected product among [1, 2]" in _flags(result)


def test_forbidden_ids() -> None:
    result = _cut(
        _case(expect={"forbidden_ids": [1]}),
        [{"type": "text", "text": "This one?"}, {"type": "cards", "product_ids": [1]}],
    )
    assert "forbidden product 1 shown" in _flags(result)


def test_empty_answer() -> None:
    result = _cut(_case(), [])
    assert "empty answer" in _flags(result)


def test_no_next_step() -> None:
    result = _cut(
        _case(), [{"type": "text", "text": "The unit is listed in the catalogue."}]
    )
    assert "no next step" in _flags(result)


def test_no_products_violated() -> None:
    result = _cut(
        _case(expect={"no_products": True}),
        [{"type": "text", "text": "Here?"}, {"type": "cards", "product_ids": [1]}],
    )
    assert "products shown for small talk: [1]" in _flags(result)


def test_fake_model_shown() -> None:
    result = _cut(
        _case(expect={"fake": "CHS2-75K-T8-X"}),
        [
            {"type": "text", "text": "Quoted?"},
            {"type": "cards", "product_ids": [9]},
        ],
    )
    assert "fake model CHS2-75K-T8-X shown" in _flags(result)


def test_fake_model_absent_from_the_feed_is_still_flagged() -> None:
    """The fake string is not a catalogue row. Answer text and compare count."""
    absent = {"products": [FEED["products"][0]]}
    case = _case(expect={"fake": "GW50K-ETA-G20"})
    quoted = triage(
        case,
        _meta(),
        [{"type": "text", "text": "The GW50K-ETA-G20 is in stock?"}],
        absent,
        1.0,
        200,
        None,
    )
    assert "fake model GW50K-ETA-G20 shown in the answer" in _flags(quoted)
    compared = triage(
        case,
        _meta(),
        [
            {"type": "text", "text": "Nearest real models?"},
            {"type": "compare", "values": {"model": "GW50K-ETA-G20"}},
        ],
        absent,
        1.0,
        200,
        None,
    )
    assert "fake model GW50K-ETA-G20 shown in compare" in _flags(compared)
    assert "shown in the answer" not in _flags(compared)
    nearest = triage(
        case,
        _meta(),
        [
            {"type": "text", "text": "The H2-10K-T3 is the nearest real model?"},
            {"type": "cards", "product_ids": [1]},
        ],
        absent,
        1.0,
        200,
        None,
    )
    assert "fake model" not in _flags(nearest)


def test_sizing_action_missing() -> None:
    result = _cut(
        _case(expect={"sizing": {"pv_kwp": 8.0}}),
        [{"type": "text", "text": "Open the configurator?"}],
    )
    assert "sizing case without open_configurator action" in _flags(result)


def test_url_prefill_match_passes() -> None:
    """I3 shape: the action carries a URL, not flat pv_kwp / annual_load_kwh."""
    case = _case(
        request="I have 8 kWp on the roof and use 4000 kWh a year, three-phase.",
        expect={"sizing": {"pv_kwp": 8.0, "annual_load_kwh": 4000.0, "phase": 3}},
    )
    blocks: list[dict[str, Any]] = [
        {"type": "text", "text": "Open it below?"},
        {
            "type": "action",
            "name": "open_configurator",
            "args": {
                "url": "http://127.0.0.1:9162/solution-configurator/"
                "?pv_kwp=8&annual_kwh=4000&phase=3"
            },
        },
    ]
    result = _cut(case, blocks)
    assert result["verdict"] == "TRIAGE_PASS"
    assert result["flags"] == []


def test_url_value_mismatch() -> None:
    case = _case(
        request="I have 8 kWp.",
        expect={"sizing": {"pv_kwp": 8.0}},
    )
    blocks: list[dict[str, Any]] = [
        {"type": "text", "text": "Open it?"},
        {
            "type": "action",
            "name": "open_configurator",
            "args": {"url": "http://127.0.0.1/solution-configurator/?pv_kwp=9"},
        },
    ]
    result = _cut(case, blocks)
    assert "prefill pv_kwp=9.0, want 8.0" in _flags(result)


def test_no_annual_fires_when_annual_kwh_present() -> None:
    case = _case(
        request="My PV is 12 kWp and I want 15 kWh of battery storage.",
        expect={"sizing": {"pv_kwp": 12.0, "no_annual": True}},
    )
    blocks: list[dict[str, Any]] = [
        {"type": "text", "text": "Open it?"},
        {
            "type": "action",
            "name": "open_configurator",
            "args": {
                "url": "http://127.0.0.1/solution-configurator/?pv_kwp=12&annual_kwh=4000"
            },
        },
    ]
    result = _cut(case, blocks)
    text = _flags(result)
    assert "storage kWh bled into annual_load_kwh" in text
    assert "was not asked for" not in text


def test_no_annual_quiet_when_absent() -> None:
    case = _case(
        request="My PV is 12 kWp and I want 15 kWh of battery storage.",
        expect={"sizing": {"pv_kwp": 12.0, "no_annual": True}},
    )
    blocks: list[dict[str, Any]] = [
        {"type": "text", "text": "Open it?"},
        {
            "type": "action",
            "name": "open_configurator",
            "args": {"url": "http://127.0.0.1/solution-configurator/?pv_kwp=12"},
        },
    ]
    result = _cut(case, blocks)
    assert result["verdict"] == "TRIAGE_PASS"


def test_extra_phase_flagged_and_pv_present() -> None:
    """I5-DE shape: pv_kwp is on the URL; phase=1 was not asked."""
    case = _case(
        request="Meine PV-Anlage hat 12 kWp und ich möchte 15 kWh Batteriespeicher.",
        lang="de",
        expect={"sizing": {"pv_kwp": 12.0, "no_annual": True}},
    )
    blocks: list[dict[str, Any]] = [
        {"type": "text", "text": "Starten Sie ihn?"},
        {
            "type": "action",
            "name": "open_configurator",
            "args": {
                "url": "http://127.0.0.1/solution-configurator/?pv_kwp=12&phase=1"
            },
        },
    ]
    result = _cut(case, blocks)
    text = _flags(result)
    assert "prefill phase=1 was not asked for" in text
    assert "pv_kwp=None" not in text
    assert "bled" not in text


def test_flat_key_fills_only_when_the_url_omits_it() -> None:
    url_wins = configurator_prefill(
        {"url": "http://h/?pv_kwp=8", "pv_kwp": 99, "phase": 3}
    )
    assert url_wins["pv_kwp"] == 8.0
    assert url_wins["phase"] == 3
    flat = configurator_prefill({"pv_kwp": 8, "annual_kwh": 4000})
    assert flat["pv_kwp"] == 8
    assert flat["annual_load_kwh"] == 4000


def test_parts_block_missing() -> None:
    result = _cut(
        _case(expect={"parts_rows": 3}),
        [{"type": "text", "text": "I checked the list?"}],
    )
    assert "no parts block for a list file" in _flags(result)


def test_parts_row_count() -> None:
    result = _cut(
        _case(expect={"parts_rows": 3}),
        [{"type": "text", "text": "Checked?"}, {"type": "parts", "rows": [{}]}],
    )
    assert "1 rows, want 3" in _flags(result)


def test_truncation_missing() -> None:
    result = _cut(
        _case(expect={"parts_truncated": True}),
        [
            {"type": "text", "text": "Checked?"},
            {"type": "parts", "rows": [], "truncated": False},
        ],
    )
    assert "no truncation flag" in _flags(result)


def test_unexplained_numbers() -> None:
    result = _cut(
        _case(),
        [{"type": "text", "text": "The warranty runs 12 years?"}],
    )
    assert "numbers to verify: 12" in _flags(result)


def test_de_answer_looks_english() -> None:
    result = _cut(
        _case(lang="de", request="Ist der H2-10K-T3 auf Lager?"),
        [{"type": "text", "text": "The inverter is in stock for you?"}],
    )
    assert "answer looks English on a DE turn" in _flags(result)


def test_en_answer_looks_german() -> None:
    result = _cut(
        _case(),
        [{"type": "text", "text": "Der Wechselrichter ist auf Lager?"}],
    )
    assert "answer looks German on an EN turn" in _flags(result)


def test_clean_pass() -> None:
    result = _cut(
        _case(),
        [{"type": "text", "text": "Yes. The H2-10K-T3 is in stock. Add it?"}],
    )
    assert result == {
        "verdict": "TRIAGE_PASS",
        "flags": [],
        "duration_s": 1.0,
    }


def test_workers_default_is_one() -> None:
    parsed = build_parser().parse_args([])
    assert parsed.workers == 1


def test_battery_size_and_no_shop_prefixed_fake() -> None:
    assert len(cases.CASES) == 111
    assert len(cases.PARTS_CASES) == 8
    token = "DLK" + "-"
    root = Path(run_battery.__file__).resolve().parent
    for case in [*cases.CASES, *cases.PARTS_CASES]:
        assert token not in case["request"]
        assert token not in case["id"]
    for path in root.rglob("*.py"):
        if any(part in {".venv", "__pycache__"} for part in path.parts):
            continue
        assert token not in path.read_text(encoding="utf-8"), path.name
    g4 = [case for case in cases.CASES if case["id"] == "G4-EN"]
    assert g4[0]["request"].startswith("Can you quote 20 pieces of NEX-")
