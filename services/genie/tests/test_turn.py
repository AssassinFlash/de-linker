"""POST /assistant/turn streams SSE; /turn is the same route; votes land."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import SHELL
from fastapi.testclient import TestClient
from test_turn_abilities import clients, manifest

import linker_genie.app as app_module
from linker_genie.app import app
from linker_genie.facts import Fact, TurnFacts, collect, merge
from linker_genie.log import TurnLog
from linker_genie.route import NamedModel, Route
from linker_genie.schema import (
    ActionBlock,
    CardsBlock,
    DocumentBlock,
    Locale,
    TextBlock,
    TurnOutput,
    TurnRequest,
)
from linker_genie.understand import Prepared, nothing


@pytest.fixture(autouse=True)
def no_understanding() -> Iterator[None]:
    """The turn tests inject the generator; the understanding layer has its own
    tests (test_understand.py), so these never reach the Store API or Jev."""
    app.state.prepare = nothing
    yield
    del app.state.prepare


@pytest.fixture()
def log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TurnLog]:
    """A turn log in a temp dir, so tests never touch the real cache."""
    log = TurnLog(tmp_path / "turns.sqlite")
    monkeypatch.setattr(app_module, "_log", log)
    yield log
    log.close()


def _generate(request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
    facts = TurnFacts()
    facts.product_ids = {4107}
    facts.qualified_ids = {4107}
    facts.add(Fact(id="p4107.ac_power_kw", value="10", source="selection-facts"))
    return (
        TurnOutput(
            language=request.locale,
            blocks=[
                TextBlock(
                    text="This inverter is {fact:p4107.ac_power_kw} kW.",
                    refs=["4107"],
                ),
                CardsBlock(product_ids=[4107]),
            ],
        ),
        facts,
    )


def test_assistant_turn_streams_blocks(log: TurnLog) -> None:
    app.state.generate = _generate
    client = TestClient(app, headers=SHELL)
    response = client.post(
        "/assistant/turn",
        json={
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "10 kWp three-phase"}],
            "locale": "en",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert _meta(body)["accepts_previous_card_quantities"] is True
    assert "event: block" in body
    assert "event: done" in body
    assert "10 kW" in body


@pytest.mark.parametrize(
    ("case", "locale", "question"),
    [
        (
            "parameter",
            "de",
            "Welche AC-Nennleistung hat der SAJ HS2-8K-T2-X laut Datenblatt?",
        ),
        ("parameter", "de", "Wie hoch ist die AC-Nennleistung des SAJ HS2-8K-T2-X?"),
        ("parameter", "en", "What’s the rated AC output of the SAJ HS2-8K-T2-X?"),
        (
            "parameter",
            "en",
            "What is the AC rated power of the SAJ HS2-8K-T2-X according to the datasheet?",
        ),
        (
            "also-requests-pdf",
            "de",
            "Wie hoch ist die AC-Nennleistung des SAJ HS2-8K-T2-X? Bitte geben Sie mir auch das vollständige Datenblatt.",
        ),
        (
            "mixed-metric",
            "en",
            "What’s the rated AC output of the SAJ HS2-8K-T2-X and its maximum apparent power?",
        ),
        ("backup-only", "de", "Wie hoch ist die AC-Nennleistung des SAJ HS2-8K-T2-X?"),
    ],
)
def test_named_ac_rated_power_turn_cites_only_its_source_page(
    log: TurnLog,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    locale: Locale,
    question: str,
) -> None:
    on_grid = "AC Output [Backup]" if case == "backup-only" else "AC Output [On-grid]"
    # Turn 3 on e437a21ab: the EN projection has the rated-power row;
    # the DE projection supplied only the other AC figure the draft used.
    en = "0abea746ac33-p2-model-48c66ddb910103c5"
    de = "b00de688082b-p2-model-ad95898e2b017006"
    url = "https://de-linker.com/wp-content/uploads/2026/07/saj_hs2-10k-t2-x_datasheet.pdf"
    german = "https://de-linker.com/wp-content/uploads/2026/10/SAJ_HS2_6-10K-T2_Datasheet_DE.pdf"
    generic = "https://de-linker.com/wp-content/uploads/2026/09/saj_hs2_5_10k_t2_x_datasheet_en.pdf"
    product_id = 1184
    facts = merge(
        [
            collect(
                "linker/search-knowledge",
                {
                    "hits": [
                        {
                            "chunk_id": ref,
                            "product_ids": [product_id],
                            "evidence_product_id": product_id,
                            "document_id": f"doc-{ref}",
                            "document_revision": f"revision-{ref}",
                            "title": title,
                            "doc_url": pdf,
                            "doc_type": "datasheet",
                            "page": 2,
                            "text": text,
                            "figures": figures,
                        }
                        for ref, title, pdf, text, figures in [
                            (
                                de,
                                "SAJ HS2 Dreiphasige Komplettlösung",
                                german,
                                "| Modell | HS2-8K-T2-X |\n"
                                "| AC-Ausgang [Netzgekoppelt] |  |\n"
                                "| Max. Scheinleistung [VA] | [n14=8800 VA] |\n"
                                "| AC-Ausgang [Backup] |  |\n"
                                "| Max. Ausgangsleistung [VA] | [n27=8000 VA] |",
                                {f"{de}.n14": "8800 VA", f"{de}.n27": "8000 VA"},
                            ),
                            (
                                en,
                                "SAJ HS2 Three-Phase All-in-One Datasheet (EN)",
                                url,
                                "| MODEL | HS2-8K-T2-X |\n"
                                f"| {on_grid} |  |\n"
                                "| Rated AC Power [W] | [n10=8000 W] |\n"
                                "| Max. Apparent Power [VA] | [n11=8800 VA] |",
                                {f"{en}.n10": "8000 W", f"{en}.n11": "8800 VA"},
                            ),
                        ]
                    ]
                },
                "de",
            ),
            collect(
                "linker/get-product",
                {
                    "product_id": product_id,
                    "documents": [
                        {"url": "https://de-linker.com/other.pdf"},
                        {"url": generic, "title": "SAJ HS2 series datasheet (EN)"},
                    ],
                },
                "de",
            ),
        ]
    )
    route = Route(
        "documents",
        no_handoff=True,
        named_models=(NamedModel("HS2-8K-T2-X", (product_id,)),),
    )
    # The stored turn contains hydrated prose, not the raw model draft.
    # Reconstruct its fact placeholders and explicit blocks before hydration.
    draft = TurnOutput(
        language=locale,
        blocks=[
            TextBlock(
                text=(
                    f"Its rated AC output is {{fact:{en}.n10}} and its maximum apparent power is {{fact:{de}.n14}}."
                    if locale == "en"
                    else "Der SAJ HS2-8K-T2-X ist ein dreiphasiger Wechselrichter für Wohngebäude. "
                    "Laut Datenblatt im Abschnitt „HS2/AS2 Three Phase All-in-One Solution“ "
                    f"liegt die **AC-Nennleistung** im netzgekoppelten Betrieb bei {{fact:{en}.n10}}. "
                    "Die **maximale Scheinleistung** nennt das deutsche Datenblatt im Abschnitt "
                    f"„HS2 Dreiphasige Komplettlösung“ mit {{fact:{de}.n14}}."
                ),
                refs=[en, de, str(product_id)],
            ),
            CardsBlock(product_ids=[product_id]),
            DocumentBlock(ref=f"p{product_id}.document.1"),
        ],
    )
    if case == "backup-only":
        draft = TurnOutput(
            language="de",
            blocks=[
                TextBlock(
                    text="Die Unterlagen nennen keine AC-Nennleistung für den Netzbetrieb.",
                    refs=[en],
                )
            ],
        )
    raw = manifest(product_id)
    raw["documents"] = [
        {
            "document_id": f"doc-{ref}",
            "document_revision": f"revision-{ref}",
            "blob_sha256": "a" * 64,
            "url": pdf,
            "product_ids": [product_id],
        }
        for ref, pdf in [(en, url), (de, german), ("generic", generic)]
    ]
    monkeypatch.setattr(app.state, "prepare", lambda _: Prepared(route, facts))
    monkeypatch.setattr(
        app.state, "generate", lambda *_: (draft, TurnFacts()), raising=False
    )
    with clients(raw, {"product_id": product_id}) as (abilities, authority, _):
        monkeypatch.setattr(app.state, "publication", authority)
        monkeypatch.setattr(app_module, "ability_client", lambda: abilities)
        sse = _post("observed-rated-power", question, locale=locale)
    blocks = _blocks(sse)
    assert _meta(sse)["grounded"] and not _meta(sse)["fallback"]
    if case == "also-requests-pdf":
        assert any(block.get("url") == generic for block in blocks)
        return
    if case == "mixed-metric":
        assert "8000 W and its maximum apparent power is 8800 VA" in blocks[0]["text"]
        assert {en, de} <= {block.get("ref") for block in blocks}
        return
    if case == "backup-only":
        assert "keine AC-Nennleistung für den Netzbetrieb" in blocks[0]["text"]
        assert "8000 W" not in blocks[0]["text"]
        return
    assert [block["type"] for block in blocks] == ["text", "document"]
    assert blocks[0]["text"] == (
        "The rated AC power of the HS2-8K-T2-X is 8000 W in grid-connected operation."
        if locale == "en"
        else "Die AC-Nennleistung des HS2-8K-T2-X beträgt im Netzbetrieb 8000 W."
    )
    assert blocks[0]["refs"] == [en]
    assert blocks[1]["ref"] == en
    assert blocks[1]["url"] == f"{url}#page=2"
    assert blocks[1]["evidence_product_id"] == product_id


@pytest.mark.parametrize("unbound", [False, True])
def test_product_list_keeps_grounded_power_not_bare_model_numbers(
    log: TurnLog, monkeypatch: pytest.MonkeyPatch, unbound: bool
) -> None:
    ids = [6527, 6528]
    facts = collect(
        "linker/search-products",
        {
            "qualified": [
                {"product_id": 6527, "facts": {"ac_power_kw": 8}},
                {"product_id": 6528, "facts": {"ac_power_kw": 10}},
            ]
        },
        "en",
    )
    draft = TurnOutput(
        language="en",
        blocks=[
            TextBlock(
                text=(
                    "The two closest to the output you named are rated at "
                    "{fact:p6527.ac_power_kw} and {fact:p6528.ac_power_kw}."
                    + (" The price class is 93." if unbound else "")
                ),
                refs=[str(pid) for pid in ids],
            ),
            CardsBlock(product_ids=ids),
        ],
    )
    monkeypatch.setattr(
        app.state,
        "prepare",
        lambda _: Prepared(Route("products", show_products=True), facts),
    )
    monkeypatch.setattr(
        app.state, "generate", lambda *_: (draft, TurnFacts()), raising=False
    )
    raw = manifest(ids[0])
    raw["products"].extend(manifest(ids[1])["products"])
    with clients(raw) as (abilities, authority, _):
        monkeypatch.setattr(app.state, "publication", authority)
        monkeypatch.setattr(app_module, "ability_client", lambda: abilities)
        sse = _post(
            "observed-product-list-power",
            "Please prepare a product list with 2 hybrid inverters around 10 kW. I want to save the list to my account.",
        )
    blocks = _blocks(sse)
    assert not _meta(sse)["fallback"]
    assert "rated at 8 kW and 10 kW." in blocks[0]["text"]
    assert "93" not in blocks[0]["text"]
    assert blocks[1]["product_ids"] == ids


@pytest.mark.parametrize("model_count", [None, 1, 2])
def test_card_and_action_carry_the_requested_count(
    log: TurnLog, model_count: int | None
) -> None:
    def prepare(request: TurnRequest) -> Prepared:
        prepared = nothing(request)
        prepared.card_quantities = {4107: 2}
        return prepared

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        output, facts = _generate(request, retry)
        args = {"product_id": 4107}
        if model_count is not None:
            args["quantity"] = model_count
        output.blocks.append(ActionBlock(name="add_to_draft", args=args))
        facts.product_ids.add(4106)
        facts.qualified_ids.add(4106)
        output.blocks.append(
            ActionBlock(name="add_to_draft", args={"product_id": 4106, "quantity": 2})
        )
        output.blocks.append(
            ActionBlock(name="save_solution", args={"product_id": 4107, "quantity": 1})
        )
        return output, facts

    app.state.prepare = prepare
    app.state.generate = generate
    response = TestClient(app, headers=SHELL).post(
        "/assistant/turn",
        json={
            "conversation_id": "c1",
            "messages": [
                {
                    "role": "user",
                    "content": "Please prepare a product list with 2 SAJ H2-10K-T3 inverters. I want to save the list to my account.",
                }
            ],
        },
    )
    assert response.status_code == 200
    blocks = [
        json.loads(event.split("data: ", 1)[1])
        for event in response.text.split("\n\n")
        if event.startswith("event: block\n")
    ]
    assert next(block for block in blocks if block["type"] == "cards")[
        "quantities"
    ] == {"4107": 2}
    assert next(block for block in blocks if block.get("name") == "add_to_draft")[
        "args"
    ] == {"product_id": 4107, "quantity": 2}
    assert (
        next(
            block
            for block in blocks
            if block.get("name") == "add_to_draft"
            and block["args"]["product_id"] == 4106
        )["args"]["quantity"]
        == 1
    )
    assert (
        next(block for block in blocks if block.get("name") == "save_solution")["args"][
            "quantity"
        ]
        == 2
    )


@pytest.fixture()
def catalog_turn(vocabulary: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from test_nameplate import _abilities

    from linker_genie.understand import Understander

    understander = Understander(lambda: vocabulary, None)
    client = _abilities([])
    monkeypatch.setattr(app_module, "_client", client)
    app.state.prepare = lambda body: understander.prepare(body, client)


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        ("Show me a SAJ inverter.", 1),
        ("Please save that one.", 1),
        ("Please show me the SAJ H2-10K-T3 inverter.", 1),
        ("Please prepare 2 SAJ H2-10K-T3 inverters.", 2),
        ("I'd take 2 of the H2-10K-T3 for this project.", 2),
        ("I would like two units of the SAJ H2-10K-T3.", 2),
        ("Save 2 SAJ H2-10K-T3 or 3 SAJ H2-10K-T3.", 0),
        ("Save 2-3 SAJ H2-10K-T3.", 0),
        ("Save 2 to 3 SAJ H2-10K-T3.", 0),
        ("Bitte 2 bis 3 SAJ H2-10K-T3 speichern.", 0),
        ("Bitte SAJ H2-10K-T3, 4 Stück, speichern.", 4),
        ("Bitte zeigen Sie mir 3 Wechselrichter SAJ H2-10K-T3.", 3),
        ("Please show me 3 inverters SAJ H2-10K-T3.", 3),
        ("Bitte zeigen Sie mir 2 bis 3 Hybridwechselrichter SAJ H2-10K-T3.", 0),
        ("Please add SAJ H2-10K-T3, 2 to 3 units.", 0),
        ("Please add SAJ H2-10K-T3 x4.", 4),
        ("Save 12000 SAJ H2-10K-T3 inverters to my account.", 0),
    ],
)
def test_product_card_and_actions_use_the_current_request(
    log: TurnLog, catalog_turn: None, current: str, expected: int
) -> None:
    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        output, facts = _generate(request, retry)
        if request.locale == "de":
            output.blocks[0] = TextBlock(
                text="Dieser Wechselrichter hat {fact:p4107.ac_power_kw} kW.",
                refs=["4107"],
            )
        for name in ("add_to_draft", "save_solution"):
            output.blocks.append(
                ActionBlock(name=name, args={"product_id": 4107, "quantity": 4})
            )
        return output, facts

    app.state.generate = generate
    blocks = _blocks(
        _post(
            "c1",
            "We considered 4 SAJ H2-10K-T3 inverters.",
            current,
            locale="de" if current.startswith("Bitte") else "en",
        )
    )
    assert {
        block["name"]: block["args"] for block in blocks if block["type"] == "action"
    } == {
        "add_to_draft": {"product_id": 4107, "quantity": expected},
        "save_solution": {"product_id": 4107, "quantity": expected},
    }
    card = next(block for block in blocks if block["type"] == "cards")
    assert card["product_ids"] == [4107]
    assert card["quantities"] == {"4107": expected}


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("2 hybrid inverters", 2),
        ("2 or 3 hybrid inverters", 0),
        ("2 bis 3 Hybridwechselrichter", 0),
        ("2 Hybridwechselrichter", 2),
    ],
)
def test_customer_can_choose_either_inverter_at_the_requested_count(
    log: TurnLog, catalog_turn: None, description: str, expected: int
) -> None:
    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        ids = [6527, 6528]
        return TurnOutput(
            language="en",
            blocks=[
                TextBlock(text="Choose a hybrid inverter.", refs=[str(i) for i in ids]),
                CardsBlock(product_ids=ids),
            ],
        ), TurnFacts(product_ids=set(ids), qualified_ids=set(ids))

    app.state.generate = generate
    blocks = _blocks(
        _post(
            "choices",
            f"Please prepare a product list with {description} around 10 kW. I want to save the list to my account.",
        )
    )
    assert [b["type"] for b in blocks] == ["text", "cards"]
    assert blocks[1]["quantities"] == {"6527": expected, "6528": expected}


@pytest.mark.parametrize(
    ("language", "message", "previous", "expected"),
    [
        ("en", "2", {6527: 0}, {6527: 2}),
        ("de", "Zwei", {6528: 0}, {6528: 2}),
        ("en", "2 units", {6527: 0}, {6527: 2}),
        ("de", "2 Stück", {6528: 0}, {6528: 2}),
        ("en", "2 units", {6527: 0, 6528: 0}, {6527: 2, 6528: 2}),
        ("de", "2 Stück", {6527: 0, 6528: 0}, {6527: 2, 6528: 2}),
        ("en", "2 units", {6527: 0, 3582: 0}, {6527: 0, 3582: 0}),
        ("de", "2 davon", {6527: 0, 3582: 0}, {6527: 0, 3582: 0}),
        ("en", "2 of those", {6527: 1}, {6527: 2}),
        ("en", "Add 2 of those", {6527: 1}, {6527: 2}),
        ("en", "2 or 3 of those", {6527: 1}, {6527: 0}),
        ("de", "Zwei davon, bitte.", {6528: 1}, {6528: 2}),
        ("en", "Save that one.", {6527: 2, 6528: 2}, {6527: 2, 6528: 2}),
    ],
)
def test_follow_up_uses_the_options_actually_shown(
    log: TurnLog,
    catalog_turn: None,
    language: str,
    message: str,
    previous: dict[int, int],
    expected: dict[int, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app.state, "generate", _generate, raising=False)
    response = TestClient(app, headers=SHELL).post(
        "/assistant/turn",
        json={
            "conversation_id": "choices",
            "locale": language,
            "previous_card_quantities": previous,
            "messages": [
                {"role": "user", "content": "Inverters"},
                {"role": "assistant", "content": "Options"},
                {"role": "user", "content": message},
            ],
        },
    )
    assert response.status_code == 200
    blocks = _blocks(response.text)
    [card] = [b for b in blocks if b["type"] == "cards"]
    assert card["product_ids"] == list(expected)
    assert card["quantities"] == {str(pid): count for pid, count in expected.items()}
    assert not any(b["type"] == "parts" for b in blocks)
    if len(expected) > 1 and 0 in expected.values():
        assert blocks[0]["text"] == (
            "Welches Modell meinen Sie und wie viele Stück möchten Sie?"
            if language == "de"
            else "Which model do you mean, and how many units would you like?"
        )
    elif 0 in expected.values():
        assert blocks[0]["text"] == "How many units would you like?"
    elif language == "en":
        assert "solution draft" in blocks[0]["text"]
    else:
        assert "Lösungsentwurf" in blocks[0]["text"]


def test_explicitly_adding_an_earlier_parts_list_keeps_its_quantities(
    log: TurnLog, catalog_turn: None
) -> None:
    blocks = _blocks(
        _post("c1", "4x SAJ H2-10K-T3", "Please add these to my solution draft.")
    )
    parts = next(block for block in blocks if block["type"] == "parts")
    assert parts["add"]["items"] == [{"product_id": 4107, "quantity": 4}]


def test_turn_alias_is_the_same_handler(log: TurnLog) -> None:
    app.state.generate = _generate
    client = TestClient(app, headers=SHELL)
    response = client.post(
        "/turn",
        json={
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "hello"}],
            "locale": "de",
        },
    )
    assert response.status_code == 200
    assert "event: done" in response.text


def _meta(body: str) -> dict[str, Any]:
    for event in body.split("\n\n"):
        if "event: meta" in event:
            for line in event.splitlines():
                if line.startswith("data: "):
                    data: dict[str, Any] = json.loads(line[len("data: ") :])
                    return data
    raise AssertionError("no meta event in stream")


def test_meta_carries_the_logged_turn_id(log: TurnLog) -> None:
    app.state.generate = _generate
    client = TestClient(app, headers=SHELL)
    response = client.post(
        "/assistant/turn",
        json={
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    meta = _meta(response.text)
    assert isinstance(meta["turn_id"], int)
    assert meta["turn_id"] >= 1
    assert log.vote(meta["turn_id"], 1)


def _timings(body: str) -> dict[str, float]:
    timing = _meta(body)["timing"]
    assert isinstance(timing, dict)
    return timing


def test_meta_carries_the_turn_timing_record(log: TurnLog) -> None:
    """#336: a fake-fast turn still shows every phase it ran, non-negative, the
    phases nested inside the wall clock, and the completed record in the log."""
    app.state.generate = _generate
    body = (
        TestClient(app, headers=SHELL)
        .post(
            "/assistant/turn",
            json={
                "conversation_id": "c1",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        .text
    )
    timing = _timings(body)
    # The key set of one full model turn is stable (timing.py's vocabulary);
    # a skipped phase would be absent, not null.
    assert set(timing) == {
        "total",
        "first_event",
        "understand",
        "model",
        "model.attempt_1",
        "ground",
        "hydrate",
        "log",
    }
    assert all(
        isinstance(value, int | float) and value >= 0 for value in timing.values()
    )
    assert timing["total"] >= timing["model"]
    assert timing["model"] >= timing["model.attempt_1"]
    assert timing["total"] >= timing["understand"] + timing["model"]
    # The stream's `done` completes the row with the same phases and the final
    # wall clock (the wait the customer experienced; app._sse's finally).
    [(stored,)] = log._db.execute("SELECT timing FROM turns").fetchall()
    record = json.loads(stored)
    assert set(record) == set(timing)
    assert record["total"] >= timing["total"]


def test_the_inserted_row_has_no_total_until_the_stream_ends(
    log: TurnLog, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#336 review: the INSERT carries the phases only; `total` exists after the
    stream, so a turn whose stream never ran can never read as a fast turn."""
    inserted: dict[str, Any] = {}
    original = log.record

    def spy(**kwargs: Any) -> int:
        inserted.update(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(log, "record", spy)
    app.state.generate = _generate
    _post("c1", "hello")
    timing = inserted["timing"]
    assert isinstance(timing, dict)
    assert "total" not in timing
    assert timing["understand"] >= 0 and timing["model"] >= 0
    # And the stream that followed completed the same row.
    [(stored,)] = log._db.execute("SELECT timing FROM turns").fetchall()
    assert "total" in json.loads(stored)


def test_every_turn_closes_its_start_note(log: TurnLog) -> None:
    """#336: a start note is the only trace of a turn that never answered, so a
    served turn must leave none behind."""
    app.state.generate = _generate
    _post("c1", "hello")
    assert log._db.execute("SELECT COUNT(*) FROM turn_starts").fetchone() == (0,)


def test_a_turn_that_falls_back_times_the_template_and_both_attempts(
    log: TurnLog,
) -> None:
    """A phase the turn skipped is absent: grounding never ran (the model raised
    both times), while the retry, the fallback render and hydration are timed."""

    def broken(request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        raise ValueError("not a TurnOutput")

    app.state.generate = broken
    body = (
        TestClient(app, headers=SHELL)
        .post(
            "/assistant/turn",
            json={
                "conversation_id": "c1",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        .text
    )
    timing = _timings(body)
    assert {"model.attempt_1", "model.attempt_2", "template", "hydrate"} <= set(timing)
    assert "ground" not in timing
    # Both attempts together are the model's time (three-decimal rounding).
    assert timing["model"] == pytest.approx(
        timing["model.attempt_1"] + timing["model.attempt_2"], abs=0.001
    )


def test_a_person_turn_times_no_model(log: TurnLog) -> None:
    """A request for a person is answered in code (#243): no model, grounding,
    hydration or template phase exists to time — only the layer and the log."""
    from linker_genie.understand import Understander

    app.state.prepare = lambda body: Understander(None, None).prepare(body, None)  # type: ignore[arg-type]
    app.state.generate = _generate
    body = (
        TestClient(app, headers=SHELL)
        .post(
            "/assistant/turn",
            json={
                "conversation_id": "c1",
                "messages": [{"role": "user", "content": "Can I talk to a person?"}],
            },
        )
        .text
    )
    assert set(_timings(body)) == {"total", "first_event", "understand", "log"}


def test_vote_stores_a_thumbs_up_or_down(log: TurnLog) -> None:
    app.state.generate = _generate
    client = TestClient(app, headers=SHELL)
    body = client.post(
        "/assistant/turn",
        json={
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "hello"}],
        },
    ).text
    turn_id = _meta(body)["turn_id"]

    assert client.post(f"/turn/{turn_id}/vote", json={"vote": -1}).json() == {
        "ok": True
    }
    assert client.post(f"/assistant/turn/{turn_id}/vote", json={"vote": 1}).json() == {
        "ok": True
    }

    row = log._db.execute("SELECT vote FROM turns WHERE id = ?", (turn_id,)).fetchone()
    assert row == (1,)


def test_vote_on_an_unknown_turn_is_404(log: TurnLog) -> None:
    client = TestClient(app, headers=SHELL)
    assert client.post("/turn/999999/vote", json={"vote": 1}).status_code == 404


def test_a_vote_outside_the_scale_is_refused(log: TurnLog) -> None:
    client = TestClient(app, headers=SHELL)
    assert client.post("/turn/1/vote", json={"vote": 5}).status_code == 422


def test_an_internal_failure_is_logged_and_raised(log: TurnLog) -> None:
    def broken(request: TurnRequest, retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        raise KeyError("model backend exploded")

    app.state.generate = broken
    client = TestClient(app, headers=SHELL)
    with pytest.raises(KeyError):
        client.post(
            "/assistant/turn",
            json={
                "conversation_id": "c1",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    row = log._db.execute(
        "SELECT grounded, fallback, failures, timing FROM turns"
    ).fetchone()
    assert row is not None
    assert row[0] == 0 and row[1] == 1
    assert "internal" in row[2]
    # No stream ran: the record keeps its phases and has no total, so ops counts
    # it as incomplete rather than as a fast turn (#336).
    assert "total" not in json.loads(row[3])
    # The start note is closed: the failure has a row, so it is not an
    # unfinished turn (#336).
    assert log._db.execute("SELECT COUNT(*) FROM turn_starts").fetchone() == (0,)


def test_a_jev_failure_is_visible_in_the_stream_and_the_log(log: TurnLog) -> None:
    from linker_genie.route import Route
    from linker_genie.understand import Prepared

    def prepare(request: TurnRequest) -> Prepared:
        return Prepared(
            route=Route("model", reasons=("jev unavailable",)),
            log={
                "jev_error": "jev failed after 3 attempts: http 503",
                "route": "model",
            },
        )

    app.state.prepare = prepare
    app.state.generate = _generate
    response = TestClient(app, headers=SHELL).post(
        "/turn",
        json={
            "conversation_id": "c9",
            "messages": [{"role": "user", "content": "hi"}],
            "locale": "en",
        },
    )
    meta = json.loads(response.text.split("data: ", 1)[1].split("\n", 1)[0])
    assert meta["route"] == "model"
    assert meta["jev_error"] == "jev failed after 3 attempts: http 503"
    row = log._db.execute(
        "SELECT understanding FROM turns WHERE conversation_id = 'c9'"
    ).fetchone()
    assert json.loads(row[0])["jev_error"] == "jev failed after 3 attempts: http 503"


def test_an_old_log_gains_the_understanding_column(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "old.sqlite"
    old = sqlite3.connect(path)
    old.execute(
        "CREATE TABLE turns (id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL,"
        " created_at TEXT NOT NULL DEFAULT (datetime('now')), locale TEXT NOT NULL,"
        " grounded INTEGER NOT NULL, failures TEXT NOT NULL, fallback INTEGER NOT NULL,"
        " provider TEXT NOT NULL, model TEXT NOT NULL, tool_calls TEXT NOT NULL,"
        " output TEXT NOT NULL, vote INTEGER)"
    )
    old.commit()
    old.close()
    upgraded = TurnLog(path)
    upgraded.record("c", "en", True, (), False, "deepseek", "deepseek-flash", [], {})
    columns = [r[1] for r in upgraded._db.execute("PRAGMA table_info(turns)")]
    upgraded.close()
    # #258 adds the account flag after it; #336 the passive timing record after
    # that (NULL for the turns logged before it).
    assert columns[-4:] == ["understanding", "approved", "contact", "timing"]


def _blocks(body: str) -> list[dict[str, Any]]:
    return [
        json.loads(event.split("data: ", 1)[1])
        for event in body.split("\n\n")
        if event.startswith("event: block")
    ]


def _post(conversation: str, *customer: str, locale: str = "en") -> str:
    messages: list[dict[str, str]] = []
    for text in customer:
        if messages:
            messages.append({"role": "assistant", "content": "An answer."})
        messages.append({"role": "user", "content": text})
    response = TestClient(app, headers=SHELL).post(
        "/assistant/turn",
        json={"conversation_id": conversation, "messages": messages, "locale": locale},
    )
    assert response.status_code == 200
    return response.text


@pytest.mark.parametrize(
    ("message", "locale", "sentence"),
    [
        (
            "Can I talk to a person?",
            "en",
            "Someone from the Linker team can get in touch with you by email.",
        ),
        (
            "Ich möchte mit einem Mitarbeiter sprechen",
            "de",
            "Jemand aus dem Linker-Team kann sich per E-Mail bei Ihnen melden.",
        ),
    ],
)
def test_a_request_for_a_person_is_answered_without_the_model(
    log: TurnLog, message: str, locale: str, sentence: str
) -> None:
    from linker_genie.understand import Understander

    def no_model(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        raise AssertionError("the model must not run for a request for a person")

    app.state.prepare = lambda body: Understander(None, None).prepare(body, None)  # type: ignore[arg-type]
    app.state.generate = no_model
    body = _post("p1", message, locale=locale)
    assert _blocks(body) == [
        {"type": "text", "text": sentence, "refs": []},
        {"type": "contact", "reason": "asked"},
    ]
    row = log._db.execute("SELECT output, model, contact FROM turns").fetchone()
    assert json.loads(row[0])["blocks"][-1] == {"type": "contact", "reason": "asked"}
    # No model ran: model-routing audits read this field (review round 1 of #243).
    assert row[1] == "none"
    assert row[2] == "asked"


@pytest.mark.parametrize(
    ("message", "locale", "sentence"),
    [
        (
            "the S2 one",
            "en",
            "S2 is a suffix on more than one model. Which model do you mean?",
        ),
        (
            "die S2",
            "de",
            "S2 ist eine Endung mehrerer Modelle. Welches Modell meinen Sie?",
        ),
    ],
)
def test_a_suffix_only_question_is_answered_without_the_model(
    log: TurnLog, vocabulary: Any, message: str, locale: str, sentence: str
) -> None:
    """The sentence is the service's. find_products does not reach the model."""
    from linker_genie.jev import Reading
    from linker_genie.understand import Understander

    class Finder:
        def read(
            self, message: str, page: dict[str, Any], history: Any = ()
        ) -> Reading:
            del message, page, history
            return Reading("find_products", 0.99, 0.1, 0.05, 0.2, 2.6, 0.00003)

    def no_model(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        raise AssertionError("the model must not run for a suffix-only question")

    app.state.prepare = lambda body: Understander(lambda: vocabulary, Finder()).prepare(
        body,
        None,  # type: ignore[arg-type]
    )
    app.state.generate = no_model
    body = _post("sfx", message, locale=locale)
    assert _blocks(body) == [{"type": "text", "text": sentence, "refs": []}]
    assert _meta(body)["route"] == "clarify"
    row = log._db.execute("SELECT provider, model FROM turns").fetchone()
    assert row is not None and (row[0], row[1]) == ("service", "none")


def _frustrated(request: TurnRequest) -> Any:
    from linker_genie.jev import Reading
    from linker_genie.route import Route
    from linker_genie.understand import Prepared

    return Prepared(
        route=Route("model"), reading=Reading("other", 0.9, 0.1, 0.93, 0.1, 2.0, 0.0)
    )


def test_frustration_keeps_the_answer_and_adds_the_offer(log: TurnLog) -> None:
    app.state.prepare = _frustrated
    app.state.generate = _generate
    blocks = _blocks(_post("f1", "This is useless."))
    assert [b["type"] for b in blocks] == ["text", "cards", "contact"]
    assert blocks[-1]["reason"] == "dissatisfied"


def test_the_offer_never_comes_on_two_turns_in_a_row(log: TurnLog) -> None:
    app.state.prepare = _frustrated
    app.state.generate = _generate
    first = _blocks(_post("f2", "This is useless."))
    second = _blocks(_post("f2", "This is useless.", "Still useless!"))
    third = _blocks(_post("f2", "This is useless.", "Still useless!", "Nope."))
    assert [b["type"] for b in first][-1] == "contact"
    assert "contact" not in [b["type"] for b in second]
    assert [b["type"] for b in third][-1] == "contact"
    # Another conversation is not this one's history.
    assert _blocks(_post("f3", "This is useless."))[-1]["type"] == "contact"


def test_the_third_round_of_one_question_offers_once(log: TurnLog) -> None:
    app.state.generate = _generate
    question = "Which battery fits the SAJ H2-10K-T3?"
    rounds = [
        [b["type"] for b in _blocks(_post("r1", *([question] * n)))]
        for n in (1, 2, 3, 4, 5)
    ]
    assert ["contact" in shown for shown in rounds] == [
        False,
        False,
        True,
        False,
        False,
    ]


def test_the_log_keeps_the_offer_as_a_plain_field(tmp_path: Path) -> None:
    log = TurnLog(tmp_path / "turns.sqlite")
    common: dict[str, Any] = {
        "locale": "en",
        "grounded": True,
        "failures": (),
        "fallback": False,
        "provider": "deepseek",
        "model": "deepseek-flash",
        "tool_calls": [],
        "output": {},
    }
    log.record(conversation_id="c", contact=None, **common)
    log.record(conversation_id="c", contact="repeat", **common)
    log.record(conversation_id="d", contact="asked", **common)
    assert log.offers("c", 5) == [True, False]
    log.close()


def test_a_parts_turn_streams_its_card_and_no_model_writes(
    log: TurnLog, vocabulary: Any
) -> None:
    """#251: the service writes a parts turn; the card carries rows and the write."""
    from linker_genie import parts
    from linker_genie.route import Route
    from linker_genie.understand import Prepared

    source = parts.Source(
        "text",
        tuple(
            parts.parse_text(
                "2x SAJ H2-10K-T3\n3 x GoodWe GW10K-ETA-G20\n1 x SMA Sunny Boy 5.0"
            )
        ),
        since=0,
    )
    result = parts.build(source, [], vocabulary)

    def prepare(request: TurnRequest) -> Prepared:
        del request
        return Prepared(
            route=Route("parts", no_cards=True, no_handoff=True), parts_list=result
        )

    app.state.prepare = prepare
    client = TestClient(app, headers=SHELL)
    response = client.post(
        "/assistant/turn",
        json={
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "2x SAJ H2-10K-T3"}],
            "locale": "en",
        },
    )
    assert response.status_code == 200
    body = response.text
    meta = _meta(body)
    assert meta["route"] == "parts"
    assert meta["grounded"] and not meta["fallback"]
    assert '"type": "parts"' in body
    assert '"product_id": 4107' in body
    assert '"quantity": 2' in body
    assert "not in our product range" in body
    assert '"provider"' not in body
    # The turn log says the service wrote it (no model, no tool calls).
    row = log._db.execute("SELECT provider, model, tool_calls FROM turns").fetchone()
    assert row is not None and (row[0], row[1]) == ("service", "none")
    assert row[2] in ("[]", None)


def test_forget_purges_the_rows_a_file_parts_list_read(log: TurnLog) -> None:
    """#251: a list read from a file is the file's words; deleting the
    conversation takes its row texts, as it takes the reading (#236)."""
    log.record(
        conversation_id="c1",
        locale="en",
        grounded=True,
        failures=(),
        fallback=False,
        provider="service",
        model="none",
        tool_calls=[
            {
                "name": "linker/read-attachment",
                "arguments": {"id": "att1"},
                "ok": True,
                "result": {
                    "id": "att1",
                    "kind": "list",
                    "text": "SAJ H2-10K-T3\t2",
                },
            }
        ],
        output={
            "language": "en",
            "blocks": [
                {"type": "text", "text": "I checked your list.", "refs": []},
                {
                    "type": "parts",
                    "rows": [
                        {
                            "line": 1,
                            "text": "SAJ H2-10K-T3",
                            "quantity": 2,
                            "status": "matched",
                            "product_id": 4107,
                            "label": "H2-10K-T3",
                            "options": [],
                        }
                    ],
                    "ask_line": None,
                    "add": None,
                    "truncated": False,
                },
            ],
        },
        question="Attached: list.csv",
        understanding={"parts": {"kind": "table", "reading": "att1", "rows": 1}},
    )
    assert log.forget("c1") == 1
    row = log._db.execute("SELECT output, question FROM turns").fetchone()
    assert row is not None
    output = json.loads(row[0])
    block = next(b for b in output["blocks"] if b["type"] == "parts")
    assert block["rows"][0]["text"] == ""
    assert block["rows"][0]["purged"] is True
    # The customer's own message stays; it names the file, not its rows.
    assert row[1] == "Attached: list.csv"
