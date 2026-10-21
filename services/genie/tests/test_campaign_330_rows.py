"""#431: per-question pass conditions for the twenty #330 rows.

`eval/regression/339-campaign-330.jsonl` has one row per regraded #330 defect
or parity case (the same ids as
`docs/research/2026-10-20-campaign-330/harness/fixtures/339/manifest.json`).
Each row carries the pass condition of its own question, at the deterministic
layer that decides it: the route and its search plan, the configurator
prefill, the tool-exhaustion fallback, the code-written parts answer or the
document post-processing. The test does not call the model and does not read
the row's registration as a pass.

A row whose fix merged runs green. A row without a merged fix has
``status: gap``: the same assertion runs but is marked xfail with the recorded
gap, so a green run never calls that row passed. An XPASS means a fix landed
and the row can leave the gap list.

docs/acceptance/2026-10-20/339/case-map.md is the index.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import test_prefill as prefill

from linker_genie import parts
from linker_genie.facts import Document, Fact, TurnFacts
from linker_genie.jev import Reading
from linker_genie.lexicon import Vocabulary
from linker_genie.prefill import stated_size_hint
from linker_genie.route import Route, Subject, plan
from linker_genie.schema import (
    CardsBlock,
    DocumentBlock,
    HandoffBlock,
    TextBlock,
    TurnMessage,
    TurnOutput,
)
from linker_genie.template import DEGRADED, fallback, seal

REPO = Path(__file__).resolve().parents[3]
SET = (
    Path(__file__).resolve().parents[1]
    / "eval"
    / "regression"
    / "339-campaign-330.jsonl"
)
CAMPAIGN = REPO / "docs" / "research" / "2026-10-20-campaign-330"
MANIFEST = CAMPAIGN / "harness" / "fixtures" / "339" / "manifest.json"
VERDICTS = CAMPAIGN / "verdicts.jsonl"
ROUND3 = CAMPAIGN / "round3-runs.jsonl"
CERTIFICATE = (
    CAMPAIGN / "harness" / "fixtures" / "certificate" / "esa-5-30kw-rated-output.txt"
)
CERTIFICATE_TITLE = "IEC 62109 certificate — ESA 5–30 kW ETA-G20"
CERTIFICATE_URL = (
    "https://de-linker.com/wp-content/uploads/2026/10/"
    "GW_ESA-5-30kW_Certificate_IEC-62109.pdf"
)
KINDS = frozenset(
    {"route", "prefill", "fallback", "document", "parts_question", "route_power"}
)
# The six rows the campaign left without a merged fix (issue #431): D12, the
# round-3 EZA read, D11 twice, D9 and D10. The set is the honesty guard: a row
# moves to "fixed" only by changing it here and in the fixture.
GAPS = frozenset({"A4-EN", "A8-DE", "C1-DE", "C1-EN", "G4-DE", "I1-DE"})


def _rows() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in SET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _manifest() -> dict[str, dict[str, Any]]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = payload["cases"]
    assert isinstance(cases, list)
    return {str(case["id"]): case for case in cases}


def _recorded_requests() -> dict[str, tuple[str, str]]:
    """The question text and language as the evidence files record them.

    ``cases.py`` is the current harness fixture; a row's own record is the
    archived run. G4-DE keeps the 2026-10-19 ``DLK-SAJ-`` wording there while
    the live fixture uses ``NEX-`` (round 3, not this row).
    """
    found: dict[str, tuple[str, str]] = {}
    for path in (VERDICTS, ROUND3):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            row_id = record.get("case") or record.get("id")
            request = record.get("request")
            lang = record.get("lang")
            if (
                isinstance(row_id, str)
                and isinstance(request, str)
                and isinstance(lang, str)
            ):
                found.setdefault(row_id, (request, lang))
    return found


def _reading(intent: str) -> Reading:
    return Reading(intent, 0.95, 0.1, 0.05, 0.2, 2.6, 0.0)  # type: ignore[arg-type]


def _subject(vocabulary: Vocabulary) -> Subject:
    return Subject(
        (),
        vocabulary.device_class,
        vocabulary.labels,
        vocabulary.phase,
        vocabulary.series_members,
        brand_of={key: set(value) for key, value in vocabulary.brand_of.items()},
        brand_names=dict(vocabulary.brand_names),
        names=dict(vocabulary.names),
        catalog_models=vocabulary.model_codes(),
    )


def _route(
    row: dict[str, Any], vocabulary: Vocabulary, reading: Reading | None
) -> Route:
    return plan(
        row["message"],
        vocabulary.match(row["message"]),
        reading,
        _subject(vocabulary),
        row["lang"],
    )


def _assert_calls(route: Route, expected: list[dict[str, Any]]) -> None:
    assert len(route.calls) == len(expected), [call.ability for call in route.calls]
    for call, wanted in zip(route.calls, expected, strict=True):
        assert call.ability == wanted["ability"]
        assert dict(call.arguments) == {
            key: value for key, value in wanted.items() if key != "ability"
        }


def _assert_notes(route: Route, expected: list[dict[str, Any]]) -> None:
    if not expected:
        assert route.named_models == ()
        return
    assert [note.code for note in route.named_models] == [
        wanted["code"] for wanted in expected
    ]
    for wanted in expected:
        note = next(note for note in route.named_models if note.code == wanted["code"])
        assert note.searched is wanted["searched"]
        assert list(note.product_ids) == wanted["product_ids"]
        if "unknown" in wanted:
            assert note.unknown is wanted["unknown"]
        if "written_brand" in wanted:
            assert note.written_brand == wanted["written_brand"]
        if "catalog_brand" in wanted:
            assert note.catalog_brand == wanted["catalog_brand"]


def _resolves(route: Route, wanted: dict[str, Any]) -> bool:
    """The real series is searched, noted as a product, or named in a fixed answer.

    A search for the invented code does not count, even though its text
    contains the series word: the campaign's D9 is exactly a search that kept
    the code and never the series. A hint alone does not count either; a later
    hint that merely says the series is absent must not close the gap.
    """
    needle = str(wanted["needle"]).casefold()
    for call in route.calls:
        series = str(call.arguments.get("series") or "").casefold()
        text = str(call.arguments.get("text") or "").casefold()
        if needle in series or text == needle:
            return True
    products = set(wanted.get("product_ids", []))
    if any(products & set(note.product_ids) for note in route.named_models):
        return True
    return (
        bool(wanted.get("allow_answer")) and needle in (route.answer or "").casefold()
    )


def _check_route(row: dict[str, Any], vocabulary: Vocabulary) -> None:
    expect = row["expect"]
    readings: list[tuple[str, Reading | None]] = [
        ("jev", _reading(row["intent"])),
        ("down", None),
    ]
    for label, reading in readings:
        route = _route(row, vocabulary, reading)
        if "route" in expect:
            assert route.name == expect["route"], label
        if "stock" in expect:
            assert route.stock is expect["stock"], label
        if "no_handoff" in expect:
            assert route.no_handoff is expect["no_handoff"], label
        if "calls" in expect:
            _assert_calls(route, expect["calls"])
        if "notes" in expect:
            _assert_notes(route, expect["notes"])
        for needle in expect.get("hint_contains", []):
            assert needle in route.hint, (label, needle)
        for needle in expect.get("calls_absent", []):
            for call in route.calls:
                blob = json.dumps(dict(call.arguments), ensure_ascii=False).casefold()
                assert needle.casefold() not in blob, (label, needle)
        for argument in expect.get("absent_arguments", []):
            assert all(argument not in call.arguments for call in route.calls), (
                label,
                argument,
            )
        if "resolves" in expect:
            assert _resolves(route, expect["resolves"]), label


def _check_prefill(row: dict[str, Any]) -> None:
    """Both paths send `stated_size_hint`, not the model's proposed object."""
    expect = row["expect"]
    assert stated_size_hint(row["message"]) == expect["prefill"]
    arguments, url = prefill._model_url(row["message"], row["lang"], expect["proposed"])
    assert arguments == expect["prefill"]
    query = prefill._query(url)
    assert query == {"pv_kwp": ["12"]}
    assert "phase" not in query
    assert "annual_kwh" not in query


def _check_fallback(row: dict[str, Any], vocabulary: Vocabulary) -> None:
    expect = row["expect"]
    facts = TurnFacts()
    facts.product_ids = set(expect["facts_product_ids"])
    route = _route(row, vocabulary, _reading(row["intent"]))
    output = fallback(facts, row["lang"], route, exhausted=expect["exhausted"])
    assert expect["degraded"] is True
    assert [type(block) for block in output.blocks] == [HandoffBlock]
    handoff = output.blocks[0]
    assert isinstance(handoff, HandoffBlock)
    assert handoff.summary == DEGRADED[row["lang"]]
    cards = [
        product_id
        for block in output.blocks
        if isinstance(block, CardsBlock)
        for product_id in block.product_ids
    ]
    assert cards == expect["cards"] == []


def _sealed_text(
    row: dict[str, Any], answer: str, facts: TurnFacts, route: Route
) -> str:
    chunk = row["expect"]["chunk"]
    output = TurnOutput(
        language=row["lang"],
        blocks=[
            TextBlock(text=answer, refs=["6512", chunk]),
            CardsBlock(product_ids=[6512]),
            DocumentBlock(ref=chunk),
        ],
    )
    sealed = seal(output, facts, route, row["message"], None)
    return " ".join(
        block.text for block in sealed.blocks if isinstance(block, TextBlock)
    )


def _certificate_facts(row: dict[str, Any]) -> TurnFacts:
    expect = row["expect"]
    chunk = expect["chunk"]
    facts = TurnFacts()
    facts.product_ids = {6512}
    facts.qualified_ids = {6512}
    facts.chunk_ids.add(chunk)
    facts.add(
        Fact(id=chunk, value=f"{CERTIFICATE_TITLE} · p. 2", source="search-knowledge")
    )
    facts.add(Fact(id=f"{chunk}.text", value=expect["p2"], source="search-knowledge"))
    facts.documents[chunk] = Document(
        url=CERTIFICATE_URL, title=CERTIFICATE_TITLE, page=2
    )
    return facts


def _check_document(row: dict[str, Any]) -> None:
    """A voltage figure must come from the certificate line, not a row index."""
    facts = _certificate_facts(row)
    route = Route("documents", show_products=True, no_handoff=True)
    text = _sealed_text(row, row["expect"]["answer"], facts, route)
    for phrase in row["expect"]["blocked"]:
        assert phrase not in text, phrase


def _document_row() -> dict[str, Any]:
    return next(row for row in _rows() if row["id"] == "A4-EN")


def test_the_certificate_condition_has_its_source_and_fixed_answer() -> None:
    """The gap row's controls: the certificate says it, and the fix keeps it."""
    row = _document_row()
    expect = row["expect"]
    line = CERTIFICATE.read_text(encoding="utf-8")
    for needle in expect["certificate"]:
        assert needle in line, needle
    facts = _certificate_facts(row)
    route = Route("documents", show_products=True, no_handoff=True)
    fixed = _sealed_text(row, expect["fixed_answer"], facts, route)
    for needle in expect["certificate"]:
        assert needle in fixed, needle


def _check_parts_question(row: dict[str, Any], vocabulary: Vocabulary) -> None:
    messages = [TurnMessage(role="user", content=row["message"])]
    source = parts.find(messages, [], [], vocabulary)
    if source is None:
        # No parts count: the turn must carry the trailing question instead.
        route = _route(row, vocabulary, _reading("find_products"))
        blob = " ".join(
            (
                json.dumps(
                    [dict(call.arguments) for call in route.calls], ensure_ascii=False
                ),
                route.hint,
                route.answer or "",
            )
        ).casefold()
        words = [word.casefold() for word in row["expect"]["phase_words"]]
        assert "phase" in blob or any(word in blob for word in words), blob
        return
    result = parts.build(source, messages, vocabulary)
    output, _ = parts.answer(result, row["lang"])
    text = " ".join(
        block.text for block in output.blocks if isinstance(block, TextBlock)
    )
    words = [word.casefold() for word in row["expect"]["phase_words"]]
    assert any(word in text.casefold() for word in words), text


def _check_route_power(row: dict[str, Any], vocabulary: Vocabulary) -> None:
    """The unit-corrected reading reaches the search or the answer."""
    expect = row["expect"]
    route = _route(row, vocabulary, _reading(row["intent"]))
    assert route.name == expect["route"]
    powers = {
        call.arguments.get("ac_power_min")
        for call in route.calls
        if call.ability == "linker/search-products"
    } | {
        call.arguments.get("ac_power_max")
        for call in route.calls
        if call.ability == "linker/search-products"
    }
    filtered = expect["power_kw"] in powers
    blob = f"{route.hint} {route.answer or ''}"
    corrected = all(
        re.search(rf"\b{re.escape(word)}\b", blob) for word in expect["unit_words"]
    )
    assert filtered or corrected


def _check(row: dict[str, Any], vocabulary: Vocabulary) -> None:
    kind = row["kind"]
    if kind == "route":
        _check_route(row, vocabulary)
    elif kind == "prefill":
        _check_prefill(row)
    elif kind == "fallback":
        _check_fallback(row, vocabulary)
    elif kind == "document":
        _check_document(row)
    elif kind == "parts_question":
        _check_parts_question(row, vocabulary)
    elif kind == "route_power":
        _check_route_power(row, vocabulary)
    else:
        raise AssertionError(kind)


def test_the_fixture_covers_the_campaign_manifest() -> None:
    """Every manifest id has a row; this is the precondition, not the pass."""
    manifest = _manifest()
    rows = {row["id"]: row for row in _rows()}
    assert set(rows) == set(manifest)
    for cid, case in manifest.items():
        assert rows[cid]["issue"] == case["issue"], cid
        assert rows[cid]["campaign"] == case["campaign"], cid
        assert rows[cid]["defect"] == case["defect"], cid
        assert rows[cid]["grade"] == case["grade"], cid
        assert rows[cid]["evidence"] == case["evidence"], cid


def test_the_questions_are_verbatim_from_the_evidence() -> None:
    """EN and DE are the evidence files' own request strings, not retyped."""
    recorded = _recorded_requests()
    for row in _rows():
        request, lang = recorded[row["id"]]
        assert row["message"] == request, row["id"]
        assert row["lang"] == lang, row["id"]


def test_every_row_carries_a_condition_and_the_gaps_are_listed() -> None:
    """A row is a condition, not a registration; a gap is marked as one."""
    rows = _rows()
    assert len(rows) == 20
    assert {row["id"] for row in rows if row["status"] == "gap"} == GAPS
    for row in rows:
        assert row["kind"] in KINDS, row["id"]
        assert row["lang"] == ("de" if row["id"].endswith("-DE") else "en"), row["id"]
        assert row["expect"], row["id"]
        assert str(row["pass"]).strip(), row["id"]
        assert row["status"] in {"fixed", "gap"}, row["id"]
        if row["status"] == "gap":
            assert str(row["gap"]).strip(), row["id"]
        else:
            assert "gap" not in row, row["id"]


@pytest.mark.parametrize("row", _rows(), ids=[row["id"] for row in _rows()])
def test_330_row(
    row: dict[str, Any], vocabulary: Vocabulary, request: pytest.FixtureRequest
) -> None:
    """The row's own pass condition; a gap is xfail, never green."""
    if row["status"] == "gap":
        request.node.add_marker(
            pytest.mark.xfail(reason=f"#431 gap: {row['gap']}", strict=False)
        )
    else:
        assert row["status"] == "fixed", row["id"]
    _check(row, vocabulary)
