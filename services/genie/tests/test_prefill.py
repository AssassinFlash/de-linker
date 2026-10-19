"""Configurator prefill carries only what the customer stated (#365).

The German campaign sentence fell through to the model (Jev sizing 0.77),
and the model called size-hint with phase=1. The English sentence was routed
in code and the URL was pv_kwp only. Both paths now build that URL from
`stated_size_hint`, and the query below is what SizeHint.php writes from the
object the service actually sends (plugins/linker-commerce includes/Abilities/SizeHint.php).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import pytest

from linker_genie.abilities import AbilityClient
from linker_genie.agent import INPUT_DOCS, ToolBudget, _ability_runner, instructions
from linker_genie.jev import Reading
from linker_genie.lexicon import Vocabulary
from linker_genie.route import Call, Route, Subject, plan, stated_size_hint
from linker_genie.schema import TurnRequest
from linker_genie.understand import Prepared, Understander, _run_calls

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
_BACKUP = {"none", "needed", "needed_accessory_ok"}


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


def _php_number(raw: str) -> str | None:
    """PHP `(string)(float)` for a positive size-hint number: `12`, not `12.0`."""
    try:
        number = float(raw)
    except ValueError:
        return None
    if number <= 0:
        return None
    text = format(number, "f").rstrip("0").rstrip(".")
    return text or "0"


def _configurator_url(arguments: dict[str, str]) -> str:
    """The query SizeHint::execute writes from the input it was given."""
    query: dict[str, str] = {}
    if "pv_kwp" in arguments:
        pv = _php_number(arguments["pv_kwp"])
        if pv is not None:
            query["pv_kwp"] = pv
    if "annual_load_kwh" in arguments:
        annual = _php_number(arguments["annual_load_kwh"])
        if annual is not None:
            query["annual_kwh"] = annual
    if "phase" in arguments:
        try:
            phase = int(float(arguments["phase"]))
        except ValueError:
            phase = 0
        if phase in (1, 3):
            query["phase"] = str(phase)
    backup = arguments.get("backup")
    if backup in _BACKUP:
        query["backup"] = backup
    plz = arguments.get("plz", "")
    if re.fullmatch(r"[0-9]{5}", plz):
        query["plz"] = plz
    url = "https://de-linker.test/solution-configurator/"
    if query:
        url += "?" + urlencode(query)
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
    message: str, locale: str, proposed: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    box = _Client()
    try:
        runner = _ability_runner(
            box.client, ToolBudget(), "linker/size-hint", None, locale, message
        )
        payload = runner(proposed)
    finally:
        box.close()
    sent = box.requests[0]
    assert sent.url.path.endswith("/linker/size-hint/run")
    arguments = stated_size_hint(message)
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


def test_a_dirty_code_call_is_stripped_before_size_hint_runs() -> None:
    box = _Client()
    prepared = Prepared(
        route=Route(
            "sizing",
            (Call("linker/size-hint", dict(UNSAFE)),),
            action="open_configurator",
        )
    )
    try:
        _run_calls(prepared, _request(DE, "de"), box.client)
    finally:
        box.close()
    assert prepared.results[0]["arguments"] == {"pv_kwp": 12.0}
    url = prepared.facts.facts["size.configurator_url"].value
    assert _query(str(url)) == {"pv_kwp": ["12"]}
    assert "phase" not in _wire(box.requests[0])


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


def test_both_prompts_tell_the_model_to_leave_unstated_fields_out() -> None:
    english = instructions("en")
    german = instructions("de")
    assert "leaves out every field they did not state" in english
    assert "lässt jedes nicht genannte Feld weg" in german
    doc = INPUT_DOCS["linker/size-hint"]
    assert "empty object" in doc
    assert "drops every other field" in doc
