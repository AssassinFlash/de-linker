"""A customer's files (#236): checked, read once, kept as text, cited as facts.

Seams: `attachments.read` (what a file becomes: the image deepseek-flash is shown, the
reading), `attachments.record` with `facts.collect` (what an answer may cite, the same
facts the quality check rebuilds from the turn log), and `vision.Vision` (the one call
to the official API, its failures explicit).
"""

import base64
import io
import json
import logging
from pathlib import Path
from typing import Any

import httpx
import pytest
from PIL import Image

from linker_genie import attachments
from linker_genie.attachments import MAX_RENDERED_PAGES, PAGE, PHOTO, TARGET_PIXELS
from linker_genie.facts import collect
from linker_genie.quality.citations import verify
from linker_genie.quality.turns import LoggedTurn
from linker_genie.schema import (
    MAX_IMAGE_BYTES,
    AttachmentReading,
    Upload,
)
from linker_genie.vision import Instruction, Vision, VisionError

PROBE_PDF = (
    Path(__file__).resolve().parents[3]
    / "docs/research/2026-10-17-deepseek-flash-vision/raw/datasheet-probe.pdf"
)
NAMEPLATE = {
    "kind": "nameplate",
    "brand": "SAJ",
    "model": "H2-10K-T3",
    "product_type": "Hybrid inverter",
    "ratings": [
        {"label": "Max. PV input voltage", "value": "1000 V"},
        {"label": "Rated AC power", "value": "10 kW"},
    ],
    "text": "",
}


class See:
    """deepseek-flash, scripted: what it is shown and what it answers."""

    def __init__(self, answer: dict[str, Any] | None = None, error: str | None = None):
        self.answer = answer if answer is not None else NAMEPLATE
        self.error = error
        self.shown: list[tuple[bytes, Instruction]] = []

    def __call__(self, jpeg: bytes, instruction: Instruction) -> dict[str, Any]:
        self.shown.append((jpeg, instruction))
        if self.error:
            raise VisionError(self.error)
        if instruction == PAGE:
            return {"text": f"Drawing label {len(self.shown)}: 230 V"}
        return self.answer


def _upload(raw: bytes, kind: str, name: str = "file") -> Upload:
    return Upload(name=name, type=kind, data=base64.b64encode(raw).decode())  # type: ignore[arg-type]


def _photo(width: int = 4000, height: int = 3000, gps: bool = True) -> bytes:
    """A camera photo: large, with EXIF that names a place."""
    image = Image.new("RGB", (width, height), (200, 200, 200))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # Make
    if gps:
        exif[0x8825] = {1: "N", 2: (52.0, 31.0, 12.0), 3: "E", 4: (13.0, 24.0, 36.0)}
    out = io.BytesIO()
    image.save(out, "JPEG", exif=exif)
    return out.getvalue()


def _image_pdf(pages: int) -> bytes:
    """A PDF of scanned pages: images only, no text layer."""
    images = [Image.new("RGB", (1240, 1754), (255, 255, 255)) for _ in range(pages)]
    out = io.BytesIO()
    images[0].save(out, "PDF", save_all=True, append_images=images[1:], resolution=150)
    return out.getvalue()


def test_a_photo_is_shown_upright_small_and_without_its_metadata() -> None:
    see = See()
    [reading] = attachments.read([_upload(_photo(), "image/jpeg", "plate.jpg")], 0, see)
    [(jpeg, instruction)] = see.shown
    assert instruction == PHOTO
    with Image.open(io.BytesIO(jpeg)) as shown:
        assert shown.format == "JPEG"
        assert shown.width * shown.height <= TARGET_PIXELS
        # 4:3 kept: 1501 × 1126 or so.
        assert abs(shown.width / shown.height - 4 / 3) < 0.01
        assert not shown.getexif()
        assert "exif" not in shown.info
    assert reading.id == "att1"
    assert reading.kind == "nameplate"
    assert (reading.brand, reading.model) == ("SAJ", "H2-10K-T3")
    assert "Max. PV input voltage: 1000 V" in reading.text


def test_ids_continue_after_the_conversations_readings() -> None:
    readings = attachments.read(
        [
            _upload(_photo(400, 300), "image/jpeg"),
            _upload(_photo(400, 300), "image/jpeg"),
        ],
        3,
        See(),
    )
    assert [r.id for r in readings] == ["att4", "att5"]


@pytest.mark.parametrize(
    ("raw", "declared", "reason"),
    [
        (b"\x89PNG\r\n\x1a\n" + b"0" * 64, "image/jpeg", "type"),
        (b"MZ\x90\x00 an executable", "image/jpeg", "type"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", "image/png", "type"),
        (b"%PDF-1.7 but declared as a photo", "image/webp", "type"),
        (b"\xff\xd8\xff" + b"0" * (MAX_IMAGE_BYTES), "image/jpeg", "too_large"),
        (b"\xff\xd8\xff not really a jpeg", "image/jpeg", "unreadable_image"),
    ],
)
def test_a_file_that_is_not_what_it_says_is_refused_and_never_shown(
    raw: bytes, declared: str, reason: str, caplog: pytest.LogCaptureFixture
) -> None:
    see = See()
    with caplog.at_level(logging.WARNING, logger="linker_genie.attachments"):
        [reading] = attachments.read([_upload(raw, declared)], 0, see)
    assert reading.failed == reason
    assert see.shown == []
    assert reason in caplog.text


def test_data_that_is_not_base64_is_refused() -> None:
    upload = Upload(name="x.jpg", type="image/jpeg", data="not base64 !!")
    [reading] = attachments.read([upload], 0, See())
    assert reading.failed == "not_base64"


def test_a_decompression_bomb_is_refused_before_it_is_decoded() -> None:
    out = io.BytesIO()
    Image.new("1", (10_000, 6_000)).save(out, "PNG")  # 60 MP, a few kilobytes
    see = See()
    [reading] = attachments.read([_upload(out.getvalue(), "image/png")], 0, see)
    assert reading.failed == "too_many_pixels"
    assert see.shown == []


def test_a_pdf_with_a_text_layer_is_read_without_the_model() -> None:
    see = See()
    raw = PROBE_PDF.read_bytes()
    [reading] = attachments.read([_upload(raw, "application/pdf", "ds.pdf")], 0, see)
    # The probe page has three lines of text: below the text-page threshold, so it is
    # rendered too; its text layer is kept with what deepseek-flash read.
    assert reading.kind == "document"
    assert reading.pages == 1
    assert reading.pages_read == 1
    assert "--- page 1 ---" in reading.text


def test_scanned_pages_are_rendered_up_to_the_cap_and_the_rest_named() -> None:
    see = See()
    raw = _image_pdf(MAX_RENDERED_PAGES + 2)
    [reading] = attachments.read([_upload(raw, "application/pdf", "scan.pdf")], 0, see)
    assert len(see.shown) == MAX_RENDERED_PAGES
    assert all(instruction == PAGE for _, instruction in see.shown)
    for jpeg, _ in see.shown:
        with Image.open(io.BytesIO(jpeg)) as page:
            assert page.width * page.height <= TARGET_PIXELS
            assert page.width * page.height > TARGET_PIXELS * 0.9
    assert reading.pages == MAX_RENDERED_PAGES + 2
    assert reading.pages_read == MAX_RENDERED_PAGES
    assert "--- pages not read: 5, 6 ---" in reading.text


def test_a_broken_pdf_is_refused() -> None:
    [reading] = attachments.read(
        [_upload(b"%PDF-1.4\n broken", "application/pdf")], 0, See()
    )
    assert reading.failed == "unreadable_pdf"


def test_a_file_deepseek_flash_could_not_read_is_named_failed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    see = See(error="HTTP 400: unsupported image")
    with caplog.at_level(logging.ERROR, logger="linker_genie.attachments"):
        [reading] = attachments.read([_upload(_photo(400, 300), "image/jpeg")], 0, see)
    assert reading.failed == "unread"
    assert "HTTP 400: unsupported image" in caplog.text


def test_without_a_key_nothing_is_read_and_the_cause_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR, logger="linker_genie.attachments"):
        [reading] = attachments.read([_upload(_photo(400, 300), "image/jpeg")], 0, None)
    assert reading.failed == "no_reader"
    assert "no deepseek-flash key" in caplog.text


def test_a_readings_figures_are_facts_the_quality_check_rebuilds() -> None:
    [reading] = attachments.read([_upload(_photo(400, 300), "image/jpeg")], 0, See())
    payload, gathered = attachments.record(reading)
    assert gathered.facts["att1"].value == "file"
    figures = {fid: fact.value for fid, fact in gathered.facts.items() if ".n" in fid}
    assert "1000 V" in figures.values() and "10 kW" in figures.values()
    assert "[n" in payload["text"]
    # The turn log keeps the call; the quality check rebuilds the same facts.
    [call] = gathered.tool_calls
    rebuilt = collect(call["name"], call["result"])
    assert set(rebuilt.facts) == set(gathered.facts)
    figure = next(fid for fid, value in figures.items() if value == "1000 V")
    turn = LoggedTurn(
        id=1,
        created_at="2026-10-18T00:00:00",
        conversation_id="c",
        locale="en",
        question="what does my nameplate say?",
        output={
            "language": "en",
            "blocks": [
                {"type": "text", "text": "The label reads 1000 V.", "refs": ["att1"]}
            ],
        },
        tool_calls=gathered.tool_calls,
        fallback=False,
        page={},
    )
    assert verify(turn) == []
    assert figure.startswith("att1.n")


def test_a_long_reading_shows_the_model_the_passages_of_the_question() -> None:
    body = "\n".join(
        f"Filler line {n} about nothing in particular." for n in range(600)
    )
    text = "--- page 1 ---\n" + body + "\n--- page 9 ---\nExport limit setting: 0 W"
    reading = AttachmentReading(
        id="att1", name="manual.pdf", kind="document", text=text
    )
    payload, _ = attachments.record(reading)
    view = attachments.model_view(payload, "How do I set the export limit?")
    assert "Export limit setting" in view["text"]
    assert len(view["text"]) <= 12_000
    assert view["complete"] is False
    assert "figures" not in view


def _vision(handler: Any, sleeps: list[float] | None = None) -> Vision:
    return Vision(
        "key",
        "https://api.deepseek.test",
        "deepseek-flash",
        transport=httpx.MockTransport(handler),
        sleep=(sleeps.append if sleeps is not None else lambda _s: None),
    )


def test_vision_sends_one_image_url_block_for_json() -> None:
    seen: list[dict[str, Any]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        assert request.url == "https://api.deepseek.test/chat/completions"
        assert request.headers["authorization"] == "Bearer key"
        content = json.dumps({"kind": "photo", "text": "a roof"})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": content}}]}
        )

    answer = _vision(handle)(b"\xff\xd8\xffjpeg", Instruction("read it"))
    assert answer == {"kind": "photo", "text": "a roof"}
    [body] = seen
    assert body["model"] == "deepseek-flash"
    assert body["response_format"] == {"type": "json_object"}
    assert body["thinking"] == {"type": "disabled"}
    [message] = body["messages"]
    assert message["role"] == "user"
    assert message["content"][0] == {"type": "text", "text": "read it"}
    assert message["content"][1]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )


def test_a_400_is_raised_at_once_with_the_apis_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls: list[int] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(
            400, json={"error": {"message": "unsupported file", "type": "invalid"}}
        )

    with caplog.at_level(logging.ERROR, logger="linker_genie.vision"):
        with pytest.raises(VisionError, match="HTTP 400: unsupported file"):
            _vision(handle)(b"jpeg", Instruction("read it"))
    assert calls == [1]
    assert "refused the image" in caplog.text


def test_a_5xx_is_tried_once_more() -> None:
    answers = iter(
        [
            httpx.Response(503, text="busy"),
            httpx.Response(
                200, json={"choices": [{"message": {"content": '{"text": "ok"}'}}]}
            ),
        ]
    )
    sleeps: list[float] = []
    answer = _vision(lambda request: next(answers), sleeps)(
        b"jpeg", Instruction("read it")
    )
    assert answer == {"text": "ok"}
    assert sleeps == [0.25]


def test_an_answer_that_is_not_json_is_an_error() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "hm"}}]})

    with pytest.raises(VisionError, match="unreadable answer"):
        _vision(handle)(b"jpeg", Instruction("read it"))


def test_the_proxy_checks_the_same_limits_as_the_service() -> None:
    """The shell's proxy refuses first (Attachments.php), the service again here."""
    import re

    from linker_genie import schema

    tools = Path(__file__).resolve().parents[3] / "plugins/linker-tools/includes/Genie"
    proxy = (tools / "Attachments.php").read_text()
    thread = (tools / "Thread.php").read_text()

    def constant(source: str, name: str) -> int:
        found = re.search(rf"const {name}\s*=\s*(\d+);", source)
        assert found, name
        return int(found.group(1))

    assert constant(proxy, "MAX_FILES") == schema.MAX_FILES
    assert constant(proxy, "MAX_IMAGE_BYTES") == schema.MAX_IMAGE_BYTES
    assert constant(proxy, "MAX_PDF_BYTES") == schema.MAX_PDF_BYTES
    assert constant(proxy, "MAX_TURN_BYTES") == schema.MAX_TURN_BYTES
    assert constant(proxy, "NAME_LENGTH") == schema.NAME_LENGTH
    assert constant(thread, "READINGS_LIMIT") == schema.MAX_READINGS


def test_a_page_is_read_as_plain_text_capped_and_a_cut_page_says_so() -> None:
    seen: list[dict[str, Any]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": "Line 1\nLine 2"},
                        "finish_reason": "length",
                    }
                ]
            },
        )

    answer = _vision(handle)(b"jpeg", PAGE)
    assert answer == {"text": "Line 1\nLine 2", "truncated": True}
    [body] = seen
    assert "response_format" not in body
    assert body["max_tokens"] == PAGE.max_tokens

    class Cut(See):
        def __call__(self, jpeg: bytes, instruction: Instruction) -> dict[str, Any]:
            self.shown.append((jpeg, instruction))
            return {"text": "Wiring: L1 L2 L3", "truncated": True}

    [reading] = attachments.read(
        [_upload(_image_pdf(1), "application/pdf", "scan.pdf")], 0, Cut()
    )
    assert "Wiring: L1 L2 L3\n[the rest of this page was not read]" in reading.text


def test_a_ratings_glued_figures_are_spaced_so_they_can_be_cited() -> None:
    see = See(
        {
            **NAMEPLATE,
            "ratings": [
                {"label": "Vmax PV", "value": "1000Vd.c."},
                {"label": "MPPT range", "value": "200...850Vd.c."},
                {"label": "Grid", "value": "3L/N/PE~400/380Va.c."},
            ],
        }
    )
    [reading] = attachments.read([_upload(_photo(400, 300), "image/jpeg")], 0, see)
    # The rating keeps what the label prints; the text spaces it for the tags.
    assert reading.ratings[0].value == "1000Vd.c."
    _payload, gathered = attachments.record(reading)
    values = {f.value for fid, f in gathered.facts.items() if ".n" in fid}
    assert {"1000 Vdc", "200", "850 Vdc"} <= values


def test_a_long_pdf_names_the_pages_past_the_cap_as_one_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(attachments, "MAX_PDF_PAGES", 2)
    monkeypatch.setattr(attachments, "MAX_RENDERED_PAGES", 2)
    see = See()
    [reading] = attachments.read(
        [_upload(_image_pdf(5), "application/pdf", "manual.pdf")], 0, see
    )
    assert len(see.shown) == 2
    assert reading.pages == 5
    assert "--- pages not read: 3–5 ---" in reading.text
