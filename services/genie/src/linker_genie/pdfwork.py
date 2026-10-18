"""A customer's PDF, opened by PDFium in a process of its own (#236).

PDFium is not thread-safe (pypdfium2's documentation: "PDFium is not thread-safe …
it is not allowed to call pdfium functions simultaneously across different threads"),
and the service's turn runs in the threadpool of a sync FastAPI route, so two turns
with PDFs at once would call it from two threads. Each PDF is therefore opened in a
new Python process (`convert`): the parent sends the file's bytes on stdin and reads
one JSON object back on stdout. A subprocess per file, not a long-lived pool: a
crash, a hang or a runaway allocation in PDFium ends that one process, the turn gets
an explicit refusal for that file (`pdf_timeout`, `pdf_failed`), and the next PDF
starts in a fresh process with nothing left over (docs/specs/13-genie.md "附件与铭牌").

The child, `python -I -m linker_genie.pdfwork`, never runs a PDF's scripts or forms
(PDFium's text and render calls only). A page with a text layer is read as text, row
by row (`rows`: a datasheet's columns come back as "| label [unit] | value |" rows,
so a figure keeps the unit its row names); a page without one (a scan, a drawing) is
rendered at about 1.69 megapixels for deepseek-flash (`imaging.encode`).
"""

from __future__ import annotations

import base64
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

# The child: the interpreter that runs the service, isolated (-I: no user site, no
# PYTHON* variables, not the working directory on sys.path).
COMMAND = (sys.executable, "-I", "-m", "linker_genie.pdfwork")
# Wall-clock seconds for one PDF, start of the process to its answer. Measured on
# all 384 PDFs of the live snapshot's uploads up to the 16 MiB cap (2026-10-18,
# docs/acceptance/2026-10-18/236/pdfwork.md): median 0.1 s, slowest 1.22 s. Fifteen
# seconds is about twelve times the slowest, room for the VPS's one slower CPU; with
# four rendered pages read side by side in about 15 s more (attachments.PAGE_TOKENS)
# the turn stays inside the shell's 60 s (Proxy.php).
SECONDS = 15.0
# Address space the child may take on Linux (the VPS), where RLIMIT_AS is enforced:
# the largest peak resident memory on the same PDFs was 495 MiB (pdfwork.md); two GiB
# is about four times that and half the VPS's 3.9 GB, so a hostile file that asks
# PDFium for more fails that file, never the service. Not set on macOS, which does
# not enforce it.
MEMORY_BYTES = 2 * 1024**3
# Segments of one text row: PDFium returns a datasheet's cells as separate text
# rectangles; their vertical centres differ by under one point within a row and by
# about ten points between rows (the hosted H2 and HS2 datasheets, 2026-10-18), so a
# three-point band joins a row and never two.
ROW_POINTS = 3.0
# The child's exit status when PDFium cannot open the file (damaged, or locked with
# a password): the file is refused as unreadable, not as a crash.
UNREADABLE = 3


class PdfRefused(ValueError):
    """The PDF was not read; the message is the reason code."""


@dataclass
class Converted:
    """What the child read: text pages, rendered pages, what it left out."""

    pages: int
    texts: dict[int, str] = field(default_factory=dict)
    renders: list[tuple[int, bytes]] = field(default_factory=list)
    unread: list[int] = field(default_factory=list)
    # The first page past the page cap, when the file has more.
    beyond: int | None = None


def convert(
    raw: bytes, max_pages: int, max_rendered: int, text_chars: int
) -> Converted:
    """The PDF read in its own process, or `PdfRefused` saying why it was not."""
    try:
        done = subprocess.run(
            [*COMMAND, str(max_pages), str(max_rendered), str(text_chars)],
            input=raw,
            capture_output=True,
            timeout=SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        # subprocess.run has killed the child before raising.
        log.error("genie pdf: not read within %.0f s; the worker was stopped", SECONDS)
        raise PdfRefused("pdf_timeout") from error
    if done.returncode == UNREADABLE:
        raise PdfRefused("unreadable_pdf")
    if done.returncode != 0:
        log.error(
            "genie pdf: the worker ended with status %s: %s",
            done.returncode,
            done.stderr.decode("utf-8", "replace")[-500:],
        )
        raise PdfRefused("pdf_failed")
    try:
        answer = json.loads(done.stdout)
        return Converted(
            pages=int(answer["pages"]),
            texts={int(k): str(v) for k, v in answer["texts"].items()},
            renders=[
                (int(item["page"]), base64.b64decode(item["jpeg"]))
                for item in answer["renders"]
            ],
            unread=[int(n) for n in answer["unread"]],
            beyond=answer["beyond"],
        )
    except (ValueError, KeyError, TypeError) as error:
        log.error("genie pdf: the worker's answer is unreadable: %s", error)
        raise PdfRefused("pdf_failed") from error


def rows(textpage: Any) -> str:
    """A page's text layer as rows: each line's cells left to right, " | " between.

    A line of one cell is written as it is; a line of several is "| a | b |", the
    table form `figures.tag` reads a row's unit from ("Max. DC Voltage [V] | 1000").
    """
    segments: list[tuple[float, float, str]] = []
    for index in range(textpage.count_rects()):
        left, bottom, right, top = textpage.get_rect(index)
        text = " ".join(textpage.get_text_bounded(left, bottom, right, top).split())
        if text:
            segments.append(((bottom + top) / 2, left, text))
    lines: list[tuple[float, list[tuple[float, str]]]] = []
    for middle, left, text in sorted(segments, key=lambda s: (-s[0], s[1])):
        if lines and abs(lines[-1][0] - middle) < ROW_POINTS:
            lines[-1][1].append((left, text))
        else:
            lines.append((middle, [(left, text)]))
    out = []
    for _, cells in lines:
        texts = [text for _, text in sorted(cells)]
        out.append(texts[0] if len(texts) == 1 else "| " + " | ".join(texts) + " |")
    return "\n".join(out)


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+\n", "\n", re.sub(r"\n{3,}", "\n\n", text)).strip()


def _read(raw: bytes, max_pages: int, max_rendered: int, text_chars: int) -> int:
    """The child's work: read `raw`, write the JSON answer; return the exit status."""
    import math

    import pypdfium2 as pdfium

    from linker_genie.imaging import TARGET_PIXELS, encode

    try:
        document = pdfium.PdfDocument(raw)
    except pdfium.PdfiumError:
        return UNREADABLE
    answer: dict[str, Any] = {"texts": {}, "renders": [], "unread": [], "beyond": None}
    try:
        answer["pages"] = len(document)
        for number in range(1, len(document) + 1):
            if number > max_pages:
                # The rest is named as one range, however long the file is.
                answer["beyond"] = number
                break
            page = document[number - 1]
            try:
                textpage = page.get_textpage()
                try:
                    text = _clean(rows(textpage))
                finally:
                    textpage.close()
                if len(text) >= text_chars:
                    answer["texts"][number] = text
                    continue
                if len(answer["renders"]) >= max_rendered:
                    answer["unread"].append(number)
                    continue
                width, height = page.get_size()
                scale = math.sqrt(TARGET_PIXELS / max(1.0, width * height))
                jpeg = encode(page.render(scale=scale).to_pil())
                answer["renders"].append(
                    {"page": number, "jpeg": base64.b64encode(jpeg).decode("ascii")}
                )
                if text:
                    answer["texts"][number] = text
            finally:
                page.close()
    finally:
        document.close()
    sys.stdout.write(json.dumps(answer))
    return 0


def main() -> int:
    if sys.platform.startswith("linux"):
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
    max_pages, max_rendered, text_chars = (int(value) for value in sys.argv[1:4])
    return _read(sys.stdin.buffer.read(), max_pages, max_rendered, text_chars)


if __name__ == "__main__":
    sys.exit(main())
