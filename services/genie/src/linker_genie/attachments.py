"""The files a customer attaches: checked, read once, kept as text (#236).

docs/specs/13-genie.md "附件与铭牌". A turn carries its files apart from its messages
(`TurnRequest.attachments`). This module turns each into a `AttachmentReading`, the only thing
that outlives the turn:

- a photo is checked by its first bytes (JPEG, PNG or WebP, whatever the name or the
  declared type say), opened with a pixel ceiling, turned upright and re-encoded as a
  JPEG of about 1.69 megapixels without its metadata (no EXIF, no GPS), and read by
  deepseek-flash in one call of its own (`vision.py`, `PHOTO`): a nameplate's brand,
  model, product type and ratings as printed, or a document's text;
- a PDF is opened by PDFium, never run (no JavaScript, no forms): a page with a text
  layer is read as text; a page without one (a scan, a drawing) is rendered at the
  same 1.69 megapixels and read by deepseek-flash (`PAGE`), up to `MAX_RENDERED_PAGES`.

The official API takes no PDF (docs/research/2026-10-17-deepseek-flash-vision/ §4,
two 400s), so the conversion is here, on the VPS: PDFium reads and renders, no model
runs on the VPS (docs/specs/10-knowledge-index.md, scope of "不在 VPS 上解析").

The file is never stored: its bytes live in this request only. The reading goes back to
the proxy (an SSE `reading` event), which keeps it with the conversation and sends it
with every later turn (`TurnRequest.readings`), so a follow-up question needs no
re-upload and the image is never sent to the model twice. Its numbers reach an answer
only as facts (`attN.nK`, `figures.tag`), the way a document chunk's do.
"""

from __future__ import annotations

import base64
import binascii
import io
import logging
import math
import re
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Literal

from PIL import Image, ImageOps, UnidentifiedImageError

from linker_genie import facts
from linker_genie.facts import TurnFacts
from linker_genie.figures import tag
from linker_genie.page import PAGE_CHARS, PASSAGE_CHARS, Passage, render, select
from linker_genie.schema import (
    MAX_IMAGE_BYTES,
    MAX_PDF_BYTES,
    MAX_READING_CHARS,
    MAX_TURN_BYTES,
    AttachmentReading,
    Rating,
    ReadingKind,
    Upload,
)
from linker_genie.tools import READ_ATTACHMENT
from linker_genie.vision import See, VisionError

log = logging.getLogger(__name__)

NAME = READ_ATTACHMENT

# deepseek-flash scales every image to about the area of 1300 × 1300 pixels before it
# reads it (research §3.3, "roughly that of a 1300×1300 image"); sending that size
# keeps the detail it reads and nothing it throws away (research §9, item 2).
TARGET_PIXELS = 1300 * 1300
# JPEG quality of the re-encoded image: libjpeg's 75 is its default; a nameplate's small
# print reads better a step above it, and the measured photos of eval/attachments stay
# a few hundred kilobytes at 85.
JPEG_QUALITY = 85
# The largest image opened at all: fifty megapixels is above the largest phone camera
# sensors sold in Europe in 2026 (50 MP main cameras) and far below what a
# decompression bomb asks for; Pillow itself only refuses beyond 179 MP.
MAX_PIXELS = 50_000_000
# Pages of a PDF read: sixty hold the longest hosted manual a customer is likely to
# send whole (the SAJ H2 manual has 59 pages, snapshot 2026-10-18); beyond them the
# answer says which pages were not read.
MAX_PDF_PAGES = 60
# Pages without a text layer rendered and read by deepseek-flash, per file: each is
# one call of 2–5 s (research §3.4, eval/attachments); four run side by side and keep
# the turn inside the shell's 60 s.
MAX_RENDERED_PAGES = 4
# A page whose text layer has fewer characters than this is a scan or a drawing: a
# hosted datasheet page has well over a thousand, a wiring diagram's labels a few
# dozen (measured on eval/attachments' PDFs).
TEXT_PAGE_CHARS = 200
# Vision calls of one turn side by side: three files of which one is a PDF with four
# rendered pages.
WORKERS = 6

PHOTO = (
    "A customer of a distributor of solar inverters and batteries sent this photo. "
    "Say what it shows and transcribe it exactly as printed. Answer only with a JSON "
    'object: {"kind": "nameplate"|"document"|"photo", "brand": string|null, '
    '"model": string|null, "product_type": string|null, '
    '"ratings": [{"label": string, "value": string}], "text": string}. '
    'kind "nameplate": the rating label of a device (inverter, battery, charger, '
    "meter), also when it is partly unreadable: brand, model and product_type as "
    "printed, and every rating with its label and value, units included. "
    'kind "document": a page, a datasheet, a list or a drawing: all printed text in '
    '"text", line by line, a table row as "label: value". '
    'kind "photo": anything else: one sentence in "text" saying what it shows, and a '
    "brand or model printed on it in brand and model. "
    "Never correct, complete or guess anything; write null for what you cannot read. "
    "Leave out serial numbers, addresses, e-mail addresses and phone numbers."
)
PAGE = (
    "This is one page of a PDF a customer sent to a distributor of solar inverters "
    "and batteries: a scanned page or a drawing. Transcribe every word and figure "
    'printed on it exactly, line by line; write a table row as "label: value"; for '
    "a drawing, list its labels and what they point to. Never correct, complete or "
    "guess; leave out what you cannot read. Answer only with a JSON object: "
    '{"text": string}.'
)

_Type = Literal["jpeg", "png", "webp", "pdf"]
_DECLARED: dict[str, _Type] = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
}


class Refused(ValueError):
    """A file this service does not read; the message is the reason code."""


@dataclass
class _Job:
    """One image deepseek-flash reads: a photo, or a PDF page without text."""

    index: int
    page: int | None
    jpeg: bytes
    answer: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class _File:
    upload: Upload
    id: str
    kind: _Type | None = None
    failed: str | None = None
    pages: int | None = None
    # A PDF's text pages by page number, and its pages left unread.
    texts: dict[int, str] = field(default_factory=dict)
    unread: list[int] = field(default_factory=list)


def read(
    uploads: Sequence[Upload], start: int, see: See | None
) -> list[AttachmentReading]:
    """Read this turn's files; ids continue after the conversation's `start` readings.

    A file that cannot be read becomes a reading with `failed`, never an exception:
    the turn goes on and the answer says what could not be read. Each failure is
    logged with its cause.
    """
    files = [_File(upload, f"att{start + n + 1}") for n, upload in enumerate(uploads)]
    total = 0
    jobs: list[_Job] = []
    for index, item in enumerate(files):
        try:
            raw = _decode(item.upload)
            total += len(raw)
            if total > MAX_TURN_BYTES:
                raise Refused("turn_too_large")
            item.kind = _sniff(raw, item.upload.type)
            if item.kind == "pdf":
                jobs.extend(_pdf(item, index, raw))
            else:
                jobs.append(_Job(index, None, _jpeg(raw)))
        except Refused as error:
            item.failed = str(error)
            log.warning("genie attachment %s refused: %s", item.id, error)
    if jobs and see is None:
        for job in jobs:
            job.error = "no_reader"
        log.error("genie attachments: no deepseek-flash key is configured")
    elif jobs:
        assert see is not None
        reader = see

        def one(job: _Job) -> None:
            try:
                job.answer = reader(job.jpeg, PHOTO if job.page is None else PAGE)
            except VisionError as error:
                job.error = "unread"
                log.error("genie attachment page %s not read: %s", job.page, error)

        with ThreadPoolExecutor(max_workers=min(WORKERS, len(jobs))) as pool:
            list(pool.map(one, jobs))
    return [
        _reading(item, [j for j in jobs if j.index == n])
        for n, item in enumerate(files)
    ]


def _decode(upload: Upload) -> bytes:
    try:
        raw = base64.b64decode(upload.data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise Refused("not_base64") from error
    limit = MAX_PDF_BYTES if upload.type == "application/pdf" else MAX_IMAGE_BYTES
    if not raw:
        raise Refused("empty")
    if len(raw) > limit:
        raise Refused("too_large")
    return raw


def _sniff(raw: bytes, declared: str) -> _Type:
    """The file's type by its first bytes; it must be the type it was sent as."""
    found: _Type | None = None
    if raw.startswith(b"\xff\xd8\xff"):
        found = "jpeg"
    elif raw.startswith(b"\x89PNG\r\n\x1a\n"):
        found = "png"
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        found = "webp"
    elif raw.startswith(b"%PDF-"):
        found = "pdf"
    if found is None or _DECLARED.get(declared) != found:
        raise Refused("type")
    return found


def _jpeg(raw: bytes) -> bytes:
    """The photo upright, at about TARGET_PIXELS, as a JPEG without metadata."""
    try:
        with Image.open(io.BytesIO(raw)) as opened:
            width, height = opened.size
            if width * height > MAX_PIXELS:
                raise Refused("too_many_pixels")
            opened.load()
            image = ImageOps.exif_transpose(opened) or opened
            return _encode(image)
    except Refused:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as error:
        raise Refused("unreadable_image") from error


def _encode(image: Image.Image) -> bytes:
    rgb = image.convert("RGB")
    pixels = rgb.width * rgb.height
    if pixels > TARGET_PIXELS:
        scale = math.sqrt(TARGET_PIXELS / pixels)
        rgb = rgb.resize(
            (
                max(1, math.floor(rgb.width * scale)),
                max(1, math.floor(rgb.height * scale)),
            ),
            Image.Resampling.LANCZOS,
        )
    out = io.BytesIO()
    # No `exif=`, no `icc_profile=`: what the camera wrote (GPS among it) stays behind.
    rgb.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue()


def _pdf(item: _File, index: int, raw: bytes) -> list[_Job]:
    """The text of a PDF's text pages, and a job for each page that has none."""
    import pypdfium2 as pdfium

    try:
        document = pdfium.PdfDocument(raw)
    except pdfium.PdfiumError as error:
        # A damaged file or one locked with a password.
        raise Refused("unreadable_pdf") from error
    jobs: list[_Job] = []
    try:
        item.pages = len(document)
        for number in range(1, item.pages + 1):
            if number > MAX_PDF_PAGES:
                item.unread.append(number)
                continue
            page = document[number - 1]
            try:
                textpage = page.get_textpage()
                try:
                    text = _clean(textpage.get_text_bounded())
                finally:
                    textpage.close()
                if len(text) >= TEXT_PAGE_CHARS:
                    item.texts[number] = text
                    continue
                if len(jobs) >= MAX_RENDERED_PAGES:
                    item.unread.append(number)
                    continue
                width, height = page.get_size()
                scale = math.sqrt(TARGET_PIXELS / max(1.0, width * height))
                image = page.render(scale=scale).to_pil()
                jobs.append(_Job(index, number, _encode(image)))
                if text:
                    item.texts[number] = text
            finally:
                page.close()
    finally:
        document.close()
    return jobs


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+\n", "\n", re.sub(r"\n{3,}", "\n\n", text)).strip()


def _reading(item: _File, jobs: list[_Job]) -> AttachmentReading:
    name = item.upload.name
    if item.failed:
        return AttachmentReading(
            id=item.id, name=name, kind="document", failed=item.failed
        )
    if item.kind == "pdf":
        return _pdf_reading(item, jobs)
    job = jobs[0]
    if job.answer is None:
        return AttachmentReading(
            id=item.id, name=name, kind="photo", failed=job.error or "unread"
        )
    return _photo_reading(item.id, name, job.answer)


def _photo_reading(
    reading_id: str, name: str, answer: dict[str, Any]
) -> AttachmentReading:
    said = answer.get("kind")
    kind: ReadingKind = (
        "nameplate"
        if said == "nameplate"
        else "document"
        if said == "document"
        else "photo"
    )
    ratings = []
    for row in answer.get("ratings") or []:
        if isinstance(row, dict):
            label, value = _text(row.get("label")), _text(row.get("value"))
            if label and value:
                ratings.append(Rating(label=label[:200], value=value[:200]))
    reading = AttachmentReading(
        id=reading_id,
        name=name,
        kind=kind,
        brand=_short(answer.get("brand")),
        model=_short(answer.get("model")),
        product_type=_short(answer.get("product_type")),
        ratings=ratings[:60],
    )
    lines = [
        f"{label}: {value}"
        for label, value in (
            ("Brand", reading.brand),
            ("Model", reading.model),
            ("Product type", reading.product_type),
        )
        if value
    ]
    lines.extend(f"{rating.label}: {rating.value}" for rating in reading.ratings)
    extra = _text(answer.get("text"))
    if extra:
        lines.append(extra)
    return reading.model_copy(update={"text": "\n".join(lines)[:MAX_READING_CHARS]})


def _pdf_reading(item: _File, jobs: list[_Job]) -> AttachmentReading:
    pages: dict[int, str] = dict(item.texts)
    failed_pages = []
    for job in jobs:
        assert job.page is not None
        seen = _text((job.answer or {}).get("text"))
        if seen:
            pages[job.page] = (pages.get(job.page, "") + "\n" + seen).strip()
        elif job.answer is None:
            failed_pages.append(job.page)
    parts = [f"--- page {number} ---\n{pages[number]}" for number in sorted(pages)]
    unread = sorted([*item.unread, *failed_pages])
    if unread:
        parts.append(
            "--- pages not read: " + ", ".join(str(n) for n in unread) + " ---"
        )
    text = "\n".join(parts)[:MAX_READING_CHARS]
    return AttachmentReading(
        id=item.id,
        name=item.upload.name,
        kind="document",
        text=text,
        pages=item.pages,
        pages_read=len(pages),
        failed=None if pages else "unread",
    )


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _short(value: Any) -> str | None:
    text = _text(value)
    if not text or text.lower() in ("null", "none", "unknown", "n/a"):
        return None
    return text[:200]


def record(reading: AttachmentReading) -> tuple[dict[str, Any], TurnFacts]:
    """The reading as a tool result: its text tagged, its figures as facts.

    The one way a turn sees a reading, this turn's or an earlier one's: the facts are
    `attN` (the file), `attN.text` and `attN.nK` (each figure, as `figures.tag` writes
    it); the turn log keeps the call, so the quality check rebuilds the same facts
    (`facts.collect`).
    """
    tagged = tag(reading.id, reading.text)
    payload: dict[str, Any] = {
        **reading.model_dump(exclude={"text"}),
        "text": tagged.text,
        "figures": tagged.figures,
    }
    gathered = facts.collect(NAME, payload)
    gathered.tool_calls.append(
        {"name": NAME, "arguments": {"id": reading.id}, "ok": True, "result": payload}
    )
    return payload, gathered


def model_view(payload: dict[str, Any], question: str) -> dict[str, Any]:
    """The reading as the model reads it: no figure table; a long text cut to the
    passages nearest the question, as a long page is (`page.select`)."""
    view = {key: value for key, value in payload.items() if key != "figures"}
    text = str(payload.get("text") or "")
    if len(text) > PAGE_CHARS:
        view["text"] = render(select(_passages(text), question))
        view["complete"] = False
    return {key: value for key, value in view.items() if value not in (None, [], "")}


def _passages(text: str) -> list[Passage]:
    """A reading's text cut at its page marks, then into runs of lines of at most
    `PASSAGE_CHARS`, as a long page is cut (page.py)."""
    found: list[Passage] = []
    heading = ""
    run: list[str] = []

    def close() -> None:
        if run:
            found.append(Passage(heading, "\n".join(run)))
            run.clear()

    for line in text.split("\n"):
        if line.startswith("--- page ") or line.startswith("--- pages not read"):
            close()
            heading = line.strip("- ")
            found.append(Passage(heading, heading, is_heading=True))
            continue
        if not line.strip():
            continue
        if run and sum(len(item) + 1 for item in run) + len(line) > PASSAGE_CHARS:
            close()
        run.append(line)
    close()
    return found
