"""A nameplate photo, from the upload to the confirmation (#236).

Seams: `nameplate.identify` against the real product words of the live snapshot (the
grade is code's, from product data), and the understanding layer with the turn's
checks (`Understander.prepare`, `cycle.run`): what code fetches for a nameplate before
the model, what the card offers, and that an answer citing the photo passes and reads
well. deepseek-flash is scripted here; eval/attachments runs the real one.
"""

import base64
import io
import json
from collections.abc import Sequence
from typing import Any

import httpx
import pytest
from conftest import SHELL
from fastapi.testclient import TestClient
from PIL import Image

import linker_genie.app as app_module
from linker_genie.abilities import AbilityClient
from linker_genie.agent import _user_prompt
from linker_genie.app import app
from linker_genie.cycle import run
from linker_genie.facts import TurnFacts
from linker_genie.jev import Reading
from linker_genie.lexicon import Vocabulary
from linker_genie.log import TurnLog
from linker_genie.nameplate import identify
from linker_genie.schema import (
    AttachmentReading,
    CardsBlock,
    ReadingKind,
    TextBlock,
    TurnOutput,
    TurnRequest,
)
from linker_genie.understand import Understander
from linker_genie.vision import Instruction


def _reading(
    brand: str | None, model: str | None, kind: ReadingKind = "nameplate"
) -> AttachmentReading:
    return AttachmentReading(
        id="att1",
        name="plate.jpg",
        kind=kind,
        brand=brand,
        model=model,
    )


@pytest.mark.parametrize(
    ("brand", "model", "grade", "ids"),
    [
        # The model printed is one of ours, word for word.
        ("SAJ", "H2-10K-T3", "exact", (4107,)),
        ("GoodWe", "GW10K-ETA-G20", "exact", (3556,)),
        # Our series, not our model (we carry the H2 T3, not the T2).
        ("SAJ", "H2-10K-T2", "partial", ()),
        # A brand alone names no device.
        ("PYLONTECH", None, "unreadable", ()),
        # Our brand, a model we do not carry (the eval photos' devices).
        ("SAJ", "Sununo Plus 4K-M", "none", ()),
        ("GOODWE", "GW10K-ET", "none", ()),
        ("PYLONTECH", "US3000C", "none", ()),
        # Neither could be read.
        (None, None, "unreadable", ()),
    ],
)
def test_the_grade_is_decided_by_our_product_data(
    vocabulary: Vocabulary, brand: str, model: str, grade: str, ids: tuple[int, ...]
) -> None:
    found = identify(_reading(brand, model), vocabulary)
    assert found is not None
    assert found.grade == grade
    assert found.product_ids == ids


def test_a_document_is_no_nameplate(vocabulary: Vocabulary) -> None:
    assert identify(_reading("SAJ", "H2-10K-T3", kind="document"), vocabulary) is None


class NoJev:
    """Jev must not be asked: a nameplate turn's route is the nameplate's."""

    def read(
        self,
        message: str,
        page: dict[str, Any],
        history: Sequence[tuple[str, str]] = (),
    ) -> Reading:
        raise AssertionError("Jev was asked on a nameplate turn")


class See:
    def __init__(self, answer: dict[str, Any]) -> None:
        self.answer = answer
        self.calls = 0

    def __call__(self, jpeg: bytes, instruction: Instruction) -> dict[str, Any]:
        self.calls += 1
        return self.answer


def _photo() -> str:
    out = io.BytesIO()
    Image.new("RGB", (800, 600), (230, 230, 230)).save(out, "JPEG")
    return base64.b64encode(out.getvalue()).decode()


def _request(
    readings: list[dict[str, Any]] | None = None, photo: bool = True
) -> TurnRequest:
    return TurnRequest.model_validate(
        {
            "conversation_id": "c1",
            "messages": [{"role": "user", "content": "Attached: plate.jpg"}],
            "locale": "en",
            "attachments": (
                [{"name": "plate.jpg", "type": "image/jpeg", "data": _photo()}]
                if photo
                else []
            ),
            "readings": readings or [],
        }
    )


def _abilities(seen: list[httpx.Request]) -> AbilityClient:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        text = request.url.params.get("input[text]") or ""
        qualified = (
            [{"product_id": 4107, "title": "SAJ H2-10K-T3", "facts": {}}]
            if "H2-10K-T3" in text or "H2" in str(request.url)
            else []
        )
        return httpx.Response(200, json={"qualified": qualified, "excluded": {}})

    return AbilityClient(
        "http://site.test", transport=httpx.MockTransport(handle), sleep=lambda s: None
    )


SAJ_PLATE = {
    "kind": "nameplate",
    "brand": "SAJ",
    "model": "H2-10K-T3",
    "product_type": "Hybrid inverter",
    "ratings": [{"label": "Max. PV input voltage", "value": "1000 V"}],
    "text": "",
}


def test_an_exact_nameplate_fetches_its_product_and_offers_it_for_confirmation(
    vocabulary: Vocabulary,
) -> None:
    seen: list[httpx.Request] = []
    see = See(SAJ_PLATE)
    understander = Understander(lambda: vocabulary, NoJev(), see=see)
    prepared = understander.prepare(_request(), _abilities(seen))
    assert see.calls == 1
    assert prepared.route.name == "nameplate"
    assert prepared.route.show_products
    [call] = prepared.route.calls
    assert call.ability == "linker/search-products"
    assert call.arguments["text"] == "H2-10K-T3"
    assert prepared.log["attachments"] == [
        {"id": "att1", "kind": "nameplate", "failed": None, "match": "exact"}
    ]
    [card] = prepared.cards
    assert card["match"] == "exact"
    assert card["products"] == [{"product_id": 4107, "label": "H2-10K-T3"}]
    assert (card["brand"], card["model"]) == ("SAJ", "H2-10K-T3")
    # The reading goes back to the proxy; its figure is a fact of the turn.
    [reading] = prepared.readings
    assert reading.model == "H2-10K-T3"
    assert any(f.startswith("att1.n") for f in prepared.facts.facts)
    prompt = _user_prompt(_request(), None, prepared)
    assert "Files the customer attached" in prompt
    assert "confirm that this is their device" in prompt


def test_an_unreadable_nameplate_fetches_nothing_and_shows_no_cards(
    vocabulary: Vocabulary,
) -> None:
    see = See({"kind": "nameplate", "brand": None, "model": None, "ratings": []})
    understander = Understander(lambda: vocabulary, NoJev(), see=see)
    prepared = understander.prepare(_request(), _abilities([]))
    assert prepared.route.name == "nameplate"
    assert prepared.route.calls == ()
    assert prepared.route.no_cards
    assert prepared.cards[0]["match"] == "unreadable"
    assert prepared.cards[0]["products"] == []


def test_a_model_we_do_not_carry_offers_the_brand_without_forcing_cards(
    vocabulary: Vocabulary,
) -> None:
    see = See({**SAJ_PLATE, "model": "Sununo Plus 4K-M", "product_type": "Inverter"})
    understander = Understander(lambda: vocabulary, NoJev(), see=see)
    prepared = understander.prepare(_request(), _abilities([]))
    assert prepared.cards[0]["match"] == "none"
    assert not prepared.route.show_products
    [call] = prepared.route.calls
    assert call.arguments["brand"] == "saj"
    assert "text" not in call.arguments


def test_an_answer_citing_the_photo_is_grounded_and_hydrated(
    vocabulary: Vocabulary,
) -> None:
    understander = Understander(lambda: vocabulary, NoJev(), see=See(SAJ_PLATE))
    request = _request()
    prepared = understander.prepare(request, _abilities([]))
    figure = next(
        f for f, fact in prepared.facts.facts.items() if fact.value == "1000 V"
    )

    def generate(_r: TurnRequest, _retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text="Your nameplate reads SAJ H2-10K-T3 with a maximum PV "
                        f"input of {{fact:{figure}}}. Is this your device?",
                        refs=["att1", "4107"],
                    ),
                    CardsBlock(product_ids=[4107]),
                ],
            ),
            TurnFacts(),
        )

    result = run(request, generate, prepared.route, prepared.facts)
    assert result.grounded, result.failures
    block = result.output.blocks[0]
    assert isinstance(block, TextBlock)
    assert "maximum PV input of 1000 V." in block.text


def test_an_earlier_reading_answers_a_follow_up_without_the_file(
    vocabulary: Vocabulary,
) -> None:
    """The proxy sends the conversation's readings back; no file rides again."""
    stored = {
        "id": "att1",
        "name": "plate.jpg",
        "kind": "nameplate",
        "brand": "SAJ",
        "model": "H2-10K-T3",
        "ratings": [{"label": "Max. PV input voltage", "value": "1000 V"}],
        "text": "Brand: SAJ\nModel: H2-10K-T3\nMax. PV input voltage: 1000 V",
    }

    class Other:
        def read(
            self, message: str, page: dict[str, Any], history: Any = ()
        ) -> Reading:
            return Reading("other", 0.9, 0.0, 0.0, 0.0, 1.0, 0.0)

    see = See(SAJ_PLATE)
    understander = Understander(lambda: vocabulary, Other(), see=see)
    prepared = understander.prepare(_request([stored], photo=False), _abilities([]))
    assert see.calls == 0
    assert prepared.readings == [] and prepared.cards == []
    assert prepared.route.name != "nameplate"
    assert "att1.n1" in prepared.facts.facts
    assert "1000 V" in prepared.facts.facts["att1.n1"].value


def test_the_stream_carries_the_card_and_the_reading(
    vocabulary: Vocabulary, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = TurnLog(tmp_path / "turns.sqlite")
    monkeypatch.setattr(app_module, "_log", log)
    understander = Understander(lambda: vocabulary, NoJev(), see=See(SAJ_PLATE))
    seen: list[httpx.Request] = []
    app.state.prepare = lambda body: understander.prepare(body, _abilities(seen))

    def generate(_r: TurnRequest, _retry: str | None) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text="Is this your SAJ H2-10K-T3?", refs=["att1", "4107"]
                    ),
                    CardsBlock(product_ids=[4107]),
                ],
            ),
            TurnFacts(),
        )

    app.state.generate = generate
    app.state.commerce = lambda ids: (TurnFacts(), [])
    try:
        response = TestClient(app, headers=SHELL).post(
            "/assistant/turn", json=_request().model_dump()
        )
    finally:
        del app.state.prepare, app.state.generate, app.state.commerce
    assert response.status_code == 200
    events = [
        (chunk.split("\n")[0][len("event: ") :], json.loads(chunk.split("\n")[1][6:]))
        for chunk in response.text.strip().split("\n\n")
    ]
    names = [name for name, _ in events]
    assert names[:3] == ["meta", "attachment", "reading"]
    assert events[1][1]["match"] == "exact"
    assert events[2][1]["model"] == "H2-10K-T3"
    # The bytes of the photo never leave the request: not in the stream, not in the log.
    assert _photo()[:40] not in response.text
    [turn] = log._db.execute("SELECT tool_calls, understanding FROM turns").fetchall()
    assert "linker/read-attachment" in turn[0]
    assert "base64" not in turn[0]
    assert '"match": "exact"' in turn[1]
    log.close()


# --- review round 1 of PR #309 -------------------------------------------------


@pytest.mark.parametrize(
    ("brand", "kept"),
    [
        ("SAJ", "SAJ"),
        ("GOODWE", "GOODWE"),
        ("Pylontech", "Pylontech"),
        # Guessed for the R5 label that prints no maker, thinking off (thinking.md).
        ("INVS", None),
        ("SOLIS", None),
        ("HVS", None),
    ],
)
def test_a_brand_counts_only_when_it_is_one_of_ours(
    vocabulary: Vocabulary, brand: str, kept: str | None
) -> None:
    see = See({**SAJ_PLATE, "brand": brand, "model": "R5-6K-S2-15"})
    understander = Understander(lambda: vocabulary, NoJev(), see=see)
    prepared = understander.prepare(_request(), _abilities([]))
    [reading] = prepared.readings
    assert reading.brand == kept
    assert (f"Brand: {brand}" in reading.text) is (kept is not None)
    assert prepared.cards[0]["brand"] == kept


def test_without_the_product_words_no_brand_is_known() -> None:
    from linker_genie.nameplate import with_known_brand

    reading = AttachmentReading(
        id="att1",
        name="p.jpg",
        kind="nameplate",
        brand="SAJ",
        model="H2-10K-T3",
        text="Brand: SAJ\nModel: H2-10K-T3",
    )
    blind = with_known_brand(reading, None)
    assert blind.brand is None
    assert blind.text == "Model: H2-10K-T3"


class OtherIntent:
    """Jev on a follow-up without a file: a question, nothing more."""

    def read(self, message: str, page: dict[str, Any], history: Any = ()) -> Reading:
        return Reading("other", 0.9, 0.0, 0.0, 0.0, 1.0, 0.0)


def _turn_through_the_app(
    vocabulary: Vocabulary,
    log: TurnLog,
    monkeypatch: pytest.MonkeyPatch,
    request: TurnRequest,
) -> None:
    monkeypatch.setattr(app_module, "_log", log)
    jev = NoJev() if request.attachments else OtherIntent()
    understander = Understander(lambda: vocabulary, jev, see=See(SAJ_PLATE))
    app.state.prepare = lambda body: understander.prepare(body, _abilities([]))
    app.state.generate = lambda _r, _retry: (
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="Is this your SAJ H2-10K-T3?", refs=["att1"])],
        ),
        TurnFacts(),
    )
    app.state.commerce = lambda ids: (TurnFacts(), [])
    try:
        response = TestClient(app, headers=SHELL).post(
            "/assistant/turn", json=request.model_dump()
        )
    finally:
        del app.state.prepare, app.state.generate, app.state.commerce
    assert response.status_code == 200, response.text


def test_a_reading_is_logged_once_and_purged_with_its_conversation(
    vocabulary: Vocabulary, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from linker_genie.quality.turns import TurnSource

    path = tmp_path / "turns.sqlite"
    log = TurnLog(path)
    first = _request()
    _turn_through_the_app(vocabulary, log, monkeypatch, first)
    [(stored,)] = log._db.execute("SELECT tool_calls FROM turns").fetchall()
    [full] = [c for c in json.loads(stored) if c["name"] == "linker/read-attachment"]
    reading = {
        k: v for k, v in full["result"].items() if k not in ("figures", "decimal")
    }
    reading["text"] = "Brand: SAJ\nModel: H2-10K-T3\nMax. PV input voltage: 1000 V"
    # The follow-up carries the reading back (the proxy's), and no file.
    _turn_through_the_app(
        vocabulary, log, monkeypatch, _request([reading], photo=False)
    )
    rows = log._db.execute("SELECT id, tool_calls FROM turns ORDER BY id").fetchall()
    second = [
        c for c in json.loads(rows[1][1]) if c["name"] == "linker/read-attachment"
    ]
    assert second == [
        {
            "name": "linker/read-attachment",
            "arguments": {"id": "att1"},
            "ok": True,
            "result": {"id": "att1", "earlier": True},
        }
    ]
    # The quality check still reads what the follow-up could cite.
    [judged] = TurnSource(path).by_ids([rows[1][0]])
    [resolved] = [c for c in judged.tool_calls if c["name"] == "linker/read-attachment"]
    assert "1000 V" in resolved["result"]["text"]

    # The customer deletes the conversation: the proxy calls forget.
    response = TestClient(app, headers=SHELL).post("/assistant/conversation/c1/forget")
    assert response.json() == {"purged": 1}
    [(after,)] = log._db.execute(
        "SELECT tool_calls FROM turns WHERE id = ?", (rows[0][0],)
    ).fetchall()
    [purged] = [c for c in json.loads(after) if c["name"] == "linker/read-attachment"]
    assert purged["result"] == {
        "id": "att1",
        "kind": "nameplate",
        "pages": None,
        "pages_read": None,
        "failed": None,
        "purged": True,
    }
    assert "1000 V" not in after and "H2-10K-T3" not in after
    log.close()


def test_the_service_answers_only_its_shell(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    from linker_genie.schema import MAX_REQUEST_BYTES

    client = TestClient(app)
    body = _request().model_dump()
    with caplog.at_level(logging.WARNING, logger="linker_genie.gate"):
        assert client.post("/assistant/turn", json=body).status_code == 401
        assert (
            client.post(
                "/assistant/turn", json=body, headers={"X-Linker-Service-Token": "no"}
            ).status_code
            == 401
        )
        assert client.post("/turn/1/vote", json={"vote": 1}).status_code == 401
        assert client.post("/assistant/conversation/c1/forget").status_code == 401
    assert "without the service token" in caplog.text
    # /health stays open for the site's daily check.
    assert client.get("/health").status_code == 200
    # A body past the cap is refused before it is parsed, declared or streamed.
    big = b"x" * (MAX_REQUEST_BYTES + 1)
    shell = TestClient(app, headers=SHELL)
    declared = shell.post(
        "/assistant/turn", content=big, headers={"content-type": "application/json"}
    )
    assert declared.status_code == 413

    def chunks() -> Any:
        for start in range(0, len(big), 1 << 20):
            yield big[start : start + (1 << 20)]

    streamed = shell.post(
        "/assistant/turn",
        content=chunks(),
        headers={"content-type": "application/json"},
    )
    assert streamed.status_code == 413
    # Without the token configured the endpoints are closed, loudly.
    monkeypatch.delenv("GENIE_SERVICE_TOKEN")
    with caplog.at_level(logging.ERROR, logger="linker_genie.gate"):
        assert shell.post("/assistant/turn", json=body).status_code == 503
    assert "GENIE_SERVICE_TOKEN is not set" in caplog.text


def test_forget_takes_a_failed_derived_calls_error_with_it(tmp_path: Any) -> None:
    """A failed search's error carries its arguments: the reading's words.

    `understand._run` records "linker/search-products: <error>" in
    `call_failures`, and the error quotes the arguments made from the nameplate.
    `forget` removes that entry with the reading (review round 1 of PR #309).
    """
    from linker_genie.log import TurnLog

    log = TurnLog(tmp_path / "turns.sqlite")
    turn_id = log.record(
        conversation_id="c1",
        locale="en",
        grounded=True,
        failures=(),
        fallback=False,
        provider="p",
        model="m",
        tool_calls=[
            {
                "name": "linker/read-attachment",
                "arguments": {"id": "att1"},
                "ok": True,
                "result": {
                    "id": "att1",
                    "kind": "nameplate",
                    "text": "Model: H2-10K-T3",
                },
            },
            {
                "name": "linker/search-products",
                "arguments": {"text": "H2-10K-T3"},
                "ok": True,
                "result": {},
                "from_reading": "att1",
            },
        ],
        output={},
        understanding={
            "call_failures": [
                "linker/search-products: H2-10K-T3 unavailable",
                "linker/get-product: stock unreadable",
                {
                    "text": "linker/search-products: H2-10K-T3 still named",
                    "kind": "ability",
                },
                {"text": "linker/get-product: kept as a note"},
            ]
        },
    )
    assert turn_id > 0

    assert log.forget("c1") == 1
    (calls, understanding) = log._db.execute(
        "SELECT tool_calls, understanding FROM turns WHERE id = ?", (turn_id,)
    ).fetchone()
    assert "H2-10K-T3" not in calls
    assert "H2-10K-T3" not in understanding
    assert "stock unreadable" in understanding
    assert "kept as a note" in understanding
    log.close()
