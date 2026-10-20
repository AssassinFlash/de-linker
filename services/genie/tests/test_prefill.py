"""Configurator prefill carries only what the customer stated (#365).

The German campaign sentence fell through to the model (Jev sizing 0.77),
and the model called size-hint with phase=1. The English sentence was routed
in code and the URL was pv_kwp only. Both paths now build that URL from
`stated_size_hint`.

The query string is not rebuilt here. `fixtures/size-hint-urls.json` is what
`SizeHint::execute` writes (home_url `https://de-linker.com`, `add_query_arg`
as `http_build_query` — the doubles in SizeHintTest). SizeHintTest asserts
the class still produces that file. This module only looks a URL up.

Registered for #339 (the campaign fixture ticket): the cases in this module
are the #365 prefill regressions — the campaign sentence, a negated backup,
a question that must not become phase or backup, the figures the first reader
dropped (year-word either side, kW peak, Drehstrom, spaced thousands), a
stated postcode, a value stated on an earlier user message, and the round-3
clauses: a later denial, a comma, a wh-statement, an indirect question,
mixed polarity, the year-word gap, and a leading-zero postcode. #339 should
fold these sentences into the campaign suite; until then they stay here.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from linker_genie.abilities import AbilityClient
from linker_genie.agent import (
    INPUT_DOCS,
    ToolBudget,
    _ability_runner,
    _page_runner,
    _user_prompt,
    instructions,
)
from linker_genie.conversation import customer_messages, last_customer_message
from linker_genie.jev import Reading
from linker_genie.lexicon import Vocabulary
from linker_genie.prefill import sizing_input, stated_size_hint
from linker_genie.route import (
    Route,
    Subject,
    plan,
)
from linker_genie.schema import TurnRequest
from linker_genie.understand import Prepared, Understander

# Produced by SizeHint.php. See the module docstring for the choice.
_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "size-hint-urls.json").read_text(
        encoding="utf-8"
    )
)

# Campaign #330 I5, evidence final.jsonl. The customer names PV size and a
# battery capacity, and no phase, yearly load, backup or postcode.
DE = "Meine PV-Anlage hat 12 kWp und ich möchte 15 kWh Batteriespeicher."
EN = "My PV is 12 kWp and I want 15 kWh of battery storage."
# What the model sent on I5-DE, plus the other fields a guess can fill.
# 15 kWh is battery capacity, not consumption per year.
UNSAFE = {
    "pv_kwp": 12,
    "phase": 1,
    "annual_load_kwh": 15,
    "backup": "needed",
    "plz": "80538",
}
# EcoFlow OCEAN 2 single-phase hybrid in the live snapshot (storeapi.json).
# The title gloss says single-phase / einphasig; the model code does not.
MODEL = "HD-P1-3K-S2"


def _reading(intent: str, confidence: float) -> Reading:
    return Reading(intent, confidence, 0.1, 0.05, 0.2, 2.6, 0.0)  # type: ignore[arg-type]


def _request(message: str, locale: str) -> TurnRequest:
    return TurnRequest.model_validate(
        {
            "conversation_id": "c-365",
            "locale": locale,
            "messages": [{"role": "user", "content": message}],
        }
    )


def _fixture_key(arguments: dict[str, Any]) -> str:
    """One key for a size-hint object, whether it came from JSON or the wire."""
    norm: dict[str, Any] = {}
    for key, value in arguments.items():
        if key in ("pv_kwp", "annual_load_kwh"):
            number = float(value)
            norm[key] = int(number) if number.is_integer() else number
        elif key == "phase":
            norm[key] = int(float(value))
        else:
            norm[key] = value
    return json.dumps(norm, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


_FIXTURE_URLS = {
    _fixture_key(case["input"]): case["configurator_url"] for case in _FIXTURE["cases"]
}


def _configurator_url(arguments: dict[str, Any]) -> str:
    """The URL SizeHint.php produced for this input. Not a second mapping."""
    key = _fixture_key(arguments)
    url = _FIXTURE_URLS.get(key)
    if not isinstance(url, str):
        raise AssertionError(
            f"no SizeHint.php fixture for {key}; regenerate "
            "services/genie/tests/fixtures/size-hint-urls.json"
        )
    return url


def _wire(request: httpx.Request) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, value in request.url.params.multi_items():
        if key.startswith("input[") and key.endswith("]") and "][" not in key:
            found[key[len("input[") : -1]] = value
    return found


class _Client:
    """Ability client whose size-hint answer is the URL SizeHint.php would build."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

        def handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            url = _configurator_url(_wire(request))
            return httpx.Response(
                200,
                json={
                    "result": {
                        "summary": "Open the Solution Configurator.",
                        "configurator_url": url,
                    }
                },
            )

        self.client = AbilityClient(
            "http://de-linker.test",
            transport=httpx.MockTransport(handle),
            sleep=lambda _seconds: None,
        )

    def close(self) -> None:
        self.client.close()


class _Jev:
    def __init__(self, confidence: float) -> None:
        self.confidence = confidence

    def read(
        self,
        message: str,
        page: dict[str, Any],
        history: Sequence[tuple[str, str]] = (),
    ) -> Reading:
        del message, page, history
        return _reading("sizing", self.confidence)


def _query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


def _code_url(
    vocabulary: Vocabulary, message: str, locale: str, confidence: float
) -> tuple[dict[str, Any], str]:
    box = _Client()
    try:
        prepared = Understander(lambda: vocabulary, _Jev(confidence)).prepare(
            _request(message, locale), box.client
        )
    finally:
        box.close()
    assert prepared.route.name == "sizing"
    (call,) = prepared.route.calls
    assert call.ability == "linker/size-hint"
    url = prepared.facts.facts["size.configurator_url"].value
    assert isinstance(url, str)
    return dict(call.arguments), url


def _model_url(
    message: str,
    locale: str,
    proposed: dict[str, Any],
    earlier: Sequence[str] = (),
) -> tuple[dict[str, Any], str]:
    spoken: str | tuple[str, ...] = (*earlier, message) if earlier else message
    box = _Client()
    try:
        runner = _ability_runner(
            box.client, ToolBudget(), "linker/size-hint", None, locale, spoken
        )
        payload = runner(proposed)
    finally:
        box.close()
    sent = box.requests[0]
    assert sent.url.path.endswith("/linker/size-hint/run")
    arguments = stated_size_hint(spoken)
    url = payload["configurator_url"]
    assert _wire(sent).keys() == arguments.keys()
    return arguments, url


@pytest.mark.parametrize(("locale", "message"), [("de", DE), ("en", EN)])
def test_the_unsafe_sentence_prefills_pv_only_on_both_paths(
    vocabulary: Vocabulary, locale: str, message: str
) -> None:
    code_arguments, code_url = _code_url(vocabulary, message, locale, 1.0)
    model_arguments, model_url = _model_url(message, locale, UNSAFE)

    assert code_arguments == model_arguments == {"pv_kwp": 12.0}
    assert _query(code_url) == _query(model_url) == {"pv_kwp": ["12"]}
    for url in (code_url, model_url):
        assert "phase" not in _query(url)
        assert "annual_kwh" not in _query(url)
        assert "backup" not in _query(url)
        assert "plz" not in _query(url)


def test_low_confidence_stays_on_the_model_and_the_url_still_omits_phase(
    vocabulary: Vocabulary,
) -> None:
    """I5-DE: Jev 0.77 stayed below 0.8. The fix does not move that threshold."""
    box = _Client()
    try:
        prepared = Understander(lambda: vocabulary, _Jev(0.77)).prepare(
            _request(DE, "de"), box.client
        )
    finally:
        box.close()
    assert prepared.route.name == "model"
    assert prepared.route.calls == ()
    assert box.requests == []
    _arguments, url = _model_url(DE, "de", UNSAFE)
    assert _query(url) == {"pv_kwp": ["12"]}


def test_the_route_log_and_the_wire_are_one_size_hint(
    vocabulary: Vocabulary,
) -> None:
    """plan() derives the size-hint dict once. The log and the wire hold it."""
    earlier = "12 kWp, dreiphasig"
    later = "und die Speichergröße?"
    request = TurnRequest.model_validate(
        {
            "conversation_id": "c-365",
            "locale": "de",
            "messages": [
                {"role": "user", "content": earlier},
                {"role": "assistant", "content": "Der Konfigurator legt das aus."},
                {"role": "user", "content": later},
            ],
        }
    )
    box = _Client()
    try:
        prepared = Understander(lambda: vocabulary, _Jev(1.0)).prepare(
            request, box.client
        )
    finally:
        box.close()
    logged = prepared.log["calls"][0]["arguments"]
    sent = prepared.results[0]["arguments"]
    assert logged is sent
    assert logged == {"pv_kwp": 12.0, "phase": 3}
    url = prepared.facts.facts["size.configurator_url"].value
    assert _query(str(url)) == {"pv_kwp": ["12"], "phase": ["3"]}


@pytest.mark.parametrize(
    ("message", "phase"),
    [
        ("12 kWp, single-phase, and 15 kWh of battery storage", "1"),
        ("12 kWp, dreiphasig, und 15 kWh Batteriespeicher", "3"),
    ],
)
def test_a_stated_phase_stays_in_the_url(message: str, phase: str) -> None:
    route = plan(message, [], _reading("sizing", 1.0), Subject((), {}, {}), "en")
    assert route.calls[0].arguments["phase"] == int(phase)
    _arguments, url = _model_url(message, "en", {"pv_kwp": 12, "phase": 1})
    assert _query(url) == {"pv_kwp": ["12"], "phase": [phase]}


def test_the_model_cannot_replace_a_stated_phase() -> None:
    message = "three-phase home, 12 kWp, 15 kWh of battery storage"
    _arguments, url = _model_url(message, "en", {"pv_kwp": 99, "phase": 1})
    assert _query(url) == {"pv_kwp": ["12"], "phase": ["3"]}


def test_an_empty_model_call_still_carries_the_stated_pv_size() -> None:
    _arguments, url = _model_url(DE, "de", {})
    assert _query(url) == {"pv_kwp": ["12"]}


# b19 (baseline): no figure, phase, backup or postcode. b43 is a scripted
# remit sentence, not an empty size-hint. The ability client raises unless
# the empty object is HTTP 200. The code route's object stays that same
# dict: lang is not added (#365, #393).
_EMPTY_SIZING = (
    "How big a battery do I need for my home?",
    "Wie groß muss ein Speicher für mein Einfamilienhaus sein?",
)


@pytest.mark.parametrize("message", _EMPTY_SIZING)
def test_an_empty_size_hint_is_accepted_on_the_model_route_and_the_code_route_is_unchanged(
    vocabulary: Vocabulary, message: str
) -> None:
    code_arguments, code_url = _code_url(vocabulary, message, "en", 1.0)
    model_arguments, model_url = _model_url(message, "en", {})

    assert code_arguments == model_arguments == {}
    assert code_url == model_url == "https://de-linker.com/solution-configurator/"
    assert "lang" not in _query(code_url)
    assert "lang" not in _query(model_url)


def test_a_single_phase_catalogue_product_does_not_prefill_phase(
    vocabulary: Vocabulary,
) -> None:
    """pa_phase of HD-P1-3K-S2 is 1. The customer did not say a phase."""
    rows = [
        (product_id, vocabulary.phase[product_id], vocabulary.names[product_id])
        for product_id, name in vocabulary.names.items()
        if MODEL in name and product_id in vocabulary.phase
    ]
    assert rows
    assert {phase for _product_id, phase, _name in rows} == {1}
    messages = (
        f"My PV is 12 kWp and I want the EcoFlow OCEAN 2 {MODEL}.",
        f"Meine PV-Anlage hat 12 kWp und ich möchte den EcoFlow OCEAN 2 {MODEL}.",
    )
    for locale, message in zip(("en", "de"), messages, strict=True):
        assert "phase" not in message.lower()
        assert "phasig" not in message.lower()
        arguments, url = _model_url(message, locale, {"pv_kwp": 12, "phase": 1})
        assert arguments == {"pv_kwp": 12.0}
        assert _query(url) == {"pv_kwp": ["12"]}


def test_both_prompts_state_the_five_field_conversation_contract() -> None:
    english = instructions("en")
    german = instructions("de")
    assert "empty object" in english
    assert "conversation" in english
    assert "leaves out every field they did not state" in english
    assert "leeren Objekt" in german
    assert "Gespräch" in german
    assert "lässt jedes nicht genannte Feld weg" in german
    for field in ("pv_kwp", "annual_load_kwh", "phase", "backup", "plz"):
        assert field in english
        assert field in german
    doc = INPUT_DOCS["linker/size-hint"]
    assert "empty object" in doc
    assert "conversation" in doc
    for field in ("pv_kwp", "annual_load_kwh", "phase", "backup", "plz"):
        assert field in doc
    assert "drops every other field" not in doc
    assert "including plz" not in doc


# #339 registration: the sentences below are the round-2 regressions. A negated
# backup is the stated value "none" (SizeHint.php's enum), never "needed".
@pytest.mark.parametrize(
    "message",
    [
        "ohne Notstrom",
        "kein Notstrom nötig",
        "no backup needed",
        "kein Ersatzstrom",
        "backup is not required",
        "Notstrom ist nicht nötig",
        "do not need backup",
        "don't need backup",
    ],
)
def test_a_negated_backup_is_none_and_never_needed(message: str) -> None:
    assert sizing_input(message) == {"backup": "none"}


@pytest.mark.parametrize(
    "message",
    [
        "not single-phase",
        "nicht einphasig",
        "kein Drehstrom",
        "not three-phase",
    ],
)
def test_a_negated_phase_does_not_become_that_phase(message: str) -> None:
    assert "phase" not in sizing_input(message)
    assert "backup" not in sizing_input(message)


@pytest.mark.parametrize(
    "message",
    [
        "Ist einphasig möglich?",
        "can it do backup?",
        "unterstützt das Drehstrom?",
        "can it do backup",
        "Ist einphasig möglich",
    ],
)
def test_a_question_does_not_prefill_phase_or_backup(message: str) -> None:
    found = sizing_input(message)
    assert "phase" not in found
    assert "backup" not in found


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("annual consumption 6000 kWh", {"annual_load_kwh": 6000.0}),
        ("consumption per year 6000 kWh", {"annual_load_kwh": 6000.0}),
        ("yearly consumption 6000 kWh", {"annual_load_kwh": 6000.0}),
        ("6000 kWh Jahresverbrauch", {"annual_load_kwh": 6000.0}),
        ("12 kW peak", {"pv_kwp": 12.0}),
        ("12 kWp", {"pv_kwp": 12.0}),
        ("12 Kilowatt Peak", {"pv_kwp": 12.0}),
        ("400 V Drehstrom", {"phase": 3}),
        ("12 000 kWh pro Jahr", {"annual_load_kwh": 12000.0}),
        ("12.000 kWh pro Jahr", {"annual_load_kwh": 12000.0}),
        ("12,000 kWh per year", {"annual_load_kwh": 12000.0}),
        ("Wechselstrom", {"phase": 1}),
        ("einphasig", {"phase": 1}),
        ("1-phasig", {"phase": 1}),
        ("3-phasig", {"phase": 3}),
        ("Drehstrom", {"phase": 3}),
        ("three-phase", {"phase": 3}),
        ("PLZ 80538", {"plz": "80538"}),
        ("Postleitzahl 80538", {"plz": "80538"}),
        ("postcode 80538", {"plz": "80538"}),
        ("ZIP 80538", {"plz": "80538"}),
        ("80538 PLZ", {"plz": "80538"}),
        ("PLZ 01067", {"plz": "01067"}),
        ("01067 PLZ", {"plz": "01067"}),
        ("Jahresstromverbrauch 6000 kWh", {"annual_load_kwh": 6000.0}),
        ("Stromverbrauch 6000 kWh", {"annual_load_kwh": 6000.0}),
        ("annual consumption of about 6000 kWh", {"annual_load_kwh": 6000.0}),
        ("6000 kWh p.a.", {"annual_load_kwh": 6000.0}),
        ("Unser Jahresverbrauch liegt bei 6000 kWh", {"annual_load_kwh": 6000.0}),
        ("Our annual consumption is 6000 kWh", {"annual_load_kwh": 6000.0}),
        ("Jahresverbrauch beträgt 6000 kWh", {"annual_load_kwh": 6000.0}),
        ("yearly consumption are 6000 kWh", {"annual_load_kwh": 6000.0}),
        ("6000 kWh, jährlich", {"annual_load_kwh": 6000.0}),
    ],
)
def test_stated_figures_the_first_reader_dropped(
    message: str, expected: dict[str, object]
) -> None:
    assert sizing_input(message) == expected


def test_a_spaced_thousands_group_is_never_read_as_zero() -> None:
    found = sizing_input("12 000 kWh pro Jahr")
    assert found["annual_load_kwh"] == 12000.0
    assert found["annual_load_kwh"] != 0


@pytest.mark.parametrize(
    "message",
    ["0 kWh pro Jahr", "100001 kWh per year", "0 kWp", "1001 kWp", "000 kWh pro Jahr"],
)
def test_an_implausible_size_is_dropped(message: str) -> None:
    found = sizing_input(message)
    assert "annual_load_kwh" not in found
    assert "pv_kwp" not in found


def test_drehstrom_and_three_phase_are_the_same_phase() -> None:
    assert (
        sizing_input("Drehstrom")["phase"] == sizing_input("three-phase")["phase"] == 3
    )


def test_a_question_keeps_a_stated_figure_and_drops_the_asked_phase() -> None:
    """A sizing question still carries the kWp the customer gave."""
    assert sizing_input("What size battery for 8 kWp, three-phase?") == {"pv_kwp": 8.0}


def test_an_earlier_statement_survives_the_next_sizing_question(
    vocabulary: Vocabulary,
) -> None:
    earlier = "12 kWp, dreiphasig"
    later = "und die Speichergröße?"
    request = TurnRequest.model_validate(
        {
            "conversation_id": "c-365",
            "locale": "de",
            "messages": [
                {"role": "user", "content": earlier},
                {"role": "assistant", "content": "Der Konfigurator legt das aus."},
                {"role": "user", "content": later},
            ],
        }
    )
    box = _Client()
    try:
        prepared = Understander(lambda: vocabulary, _Jev(1.0)).prepare(
            request, box.client
        )
    finally:
        box.close()
    assert prepared.route.name == "sizing"
    assert prepared.route.calls[0].arguments == {"pv_kwp": 12.0, "phase": 3}
    assert prepared.results[0]["arguments"] == {"pv_kwp": 12.0, "phase": 3}
    url = prepared.facts.facts["size.configurator_url"].value
    assert _query(str(url)) == {"pv_kwp": ["12"], "phase": ["3"]}

    arguments, model_url = _model_url(later, "de", {"phase": 1}, earlier=(earlier,))
    assert arguments == {"pv_kwp": 12.0, "phase": 3}
    assert _query(model_url) == {"pv_kwp": ["12"], "phase": ["3"]}


def test_a_later_user_message_overrides_only_the_field_it_states() -> None:
    found = stated_size_hint(
        ["einphasig, 5 kWp, mit Notstrom", "doch dreiphasig, PLZ 80538"]
    )
    assert found == {"pv_kwp": 5.0, "phase": 3, "backup": "needed", "plz": "80538"}
    assert stated_size_hint(["mit Notstrom", "ohne Notstrom"])["backup"] == "none"


def test_a_later_question_does_not_wipe_an_earlier_statement() -> None:
    found = stated_size_hint(
        [
            "12 kWp, dreiphasig, mit Notstrom",
            "Ist einphasig möglich?",
            "can it do backup?",
        ]
    )
    assert found == {"pv_kwp": 12.0, "phase": 3, "backup": "needed"}


def test_a_stated_postcode_reaches_the_url() -> None:
    message = "PLZ 80538, 12 kWp, dreiphasig"
    assert sizing_input(message) == {"plz": "80538", "pv_kwp": 12.0, "phase": 3}
    _arguments, url = _model_url(message, "de", {})
    assert _query(url) == {"plz": ["80538"], "pv_kwp": ["12"], "phase": ["3"]}


def test_a_later_denial_clears_the_earlier_value() -> None:
    short = stated_size_hint(["12 kWp, dreiphasig", "kein Drehstrom"])
    assert short == {"pv_kwp": 12.0}
    assert "phase" not in short
    sentence = stated_size_hint(["12 kWp, Drehstrom", "Ich habe keinen Drehstrom"])
    assert sentence == {"pv_kwp": 12.0}
    assert "phase" not in sentence
    assert stated_size_hint(["mit Notstrom", "kein Notstrom"]) == {"backup": "none"}
    assert stated_size_hint(["12 kWp, mit Notstrom", "Ich habe keinen Notstrom"]) == {
        "pv_kwp": 12.0,
        "backup": "none",
    }


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Ich habe Drehstrom, ist das möglich?", {"phase": 3}),
        ("I have three-phase, is that supported?", {"phase": 3}),
        ("Was ich brauche: 12 kWp, Drehstrom", {"pv_kwp": 12.0, "phase": 3}),
        ("What I need is three-phase", {"phase": 3}),
        ("Wie gesagt, der Anschluss ist dreiphasig", {"phase": 3}),
        ("Mein Haus ist dreiphasig, kann es auch Notstrom?", {"phase": 3}),
        ("ohne Netz und mit Notstrom", {"backup": "needed"}),
    ],
)
def test_a_declarative_clause_keeps_its_value(
    message: str, expected: dict[str, object]
) -> None:
    assert sizing_input(message) == expected


@pytest.mark.parametrize(
    "message",
    [
        "ob Notstrom möglich ist",
        "whether backup is possible",
        "if backup is possible",
        "geht das mit Drehstrom",
        "und kann es Notstrom",
        "nicht nur Notstrom, sondern auch Eigenverbrauch",
        "kein Problem ich brauche Notstrom",
    ],
)
def test_a_question_or_a_mixed_polarity_does_not_fill_phase_or_backup(
    message: str,
) -> None:
    found = sizing_input(message)
    assert "phase" not in found
    assert "backup" not in found


def test_a_negation_across_long_compounds_still_denies_phase() -> None:
    """Three words, longer than a 48-character slice, still govern the keyword."""
    gap = "innerhalb bestehenden Sonderhaushaltsanschlussvertrags"
    message = f"nicht {gap} Drehstrom"
    keyword = message.rindex("Drehstrom")
    assert keyword - message.index("nicht") > 48
    assert "phase" not in sizing_input(message)


def test_customer_words_are_read_through_one_list() -> None:
    """The page read, the file cut and the prefill all use the customer list.

    Assistant text that states a phase, a backup and a postcode is not a source.
    The page tool and a long attachment are cut to the last user message.
    """
    last = "ZZSTORAGEQUESTION"
    request = TurnRequest.model_validate(
        {
            "conversation_id": "c-365",
            "locale": "de",
            "messages": [
                {"role": "user", "content": "earlier 12 kWp"},
                {
                    "role": "assistant",
                    "content": "dreiphasig, mit Notstrom, PLZ 01067",
                },
                {"role": "user", "content": last},
            ],
        }
    )
    assert customer_messages(request) == ["earlier 12 kWp", last]
    assert last_customer_message(request) == last
    assert stated_size_hint(customer_messages(request)) == {"pv_kwp": 12.0}
    empty = TurnRequest.model_validate(
        {"conversation_id": "c-365", "locale": "en", "messages": []}
    )
    assert last_customer_message(empty) == ""
    assert customer_messages(empty) == []

    seen: dict[str, str] = {}

    def reader(_page: object, question: str, _logged_in: bool) -> dict[str, Any]:
        seen["question"] = question
        return {"text": "page body", "title": "Page"}

    runner = _page_runner(reader, ToolBudget(), request)
    assert runner(None)["text"] == "page body"
    assert seen["question"] == last

    lead = "opening passage. " * 120
    filler = ("neutral filler sentence. " * 40 + "\n") * 16
    decoy = "ASSISTANTONLYTOKEN sits in this passage. " * 20
    hit = "ZZSTORAGEQUESTION markerphrase sits in this passage. " * 20
    text = "\n".join((lead, filler, decoy, hit))
    assert len(text) > 12_000
    prepared = Prepared(
        route=Route("model"),
        attachments=[{"id": "r1", "text": text}],
    )
    prompt = _user_prompt(request, None, prepared)
    assert "markerphrase" in prompt
    assert "ASSISTANTONLYTOKEN" not in prompt
