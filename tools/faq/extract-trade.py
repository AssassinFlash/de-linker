#!/usr/bin/env python3
"""Extract the 16 trade Q&As out of the FAQ page's templates at a revision.

`plugins/linker-commerce/data/faq-trade.json` is the frozen copy of the B2B
trade rules the page carries ("Before you order"), and this script is its
provenance: ticket #176 moved those questions and answers out of the two
LiveCanvas templates (`content/livecanvas/faq_page.html` and its German twin)
and into a data file, because the rail, the mobile chip row, the card headings
and the rows all have to read one source — and the counts around them used to
be handwritten.

The templates no longer hold the rules (that is the point of the move), so the
script reads them out of a revision: it runs `git show <rev>:<path>` for both
files, parses the `<section class="linker-trade-category">` blocks, and writes
the `{en, de}` pairs. Run it after touching the extractor to prove the shipped
data file is what this code produces:

    python3 tools/faq/extract-trade.py --rev 08997063 \
        --out plugins/linker-commerce/data/faq-trade.json

`--rev 08997063` is the commit the extraction was made from: the last commit
whose templates still carried the rules (the parent of #176's own change).
Output that differs from the committed file means one of the two sides moved,
which is exactly what a reviewer needs to see.

The file's `_why`/`_rule`/`_source` prose is written here, not parsed; the
categories and their questions come from the templates.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = {
    "en": "plugins/linker-commerce/content/livecanvas/faq_page.html",
    "de": "plugins/linker-commerce/content/livecanvas/de/faq_page.html",
}

WHY = (
    "The trade rules of /faq-download/ ('Before you order'): the 16 B2B questions the page "
    "carries, frozen. Content moved verbatim out of the LiveCanvas templates on 2026-10-15 "
    "(#176) so the rail, the mobile chip row, the card headings and the answers read one "
    "source; de-linker has no lab and the register states what the documents state."
)
RULE = (
    "Verbatim copy of the page's own questions and answers; wording is approved content and "
    "is not edited here. Answers may carry inline links to the contact page."
)


def template_at(rev: str, path: str) -> str:
    """One template's source at a revision, through git."""
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{rev}:{path}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"extract-trade: git show {rev}:{path} failed:\n{proc.stderr.strip()}")
    return proc.stdout


def blocks(text: str) -> list[tuple[str, list[dict[str, str]]]]:
    """The trade categories of a template: (name, [{question, answer}, …])."""
    out: list[tuple[str, list[dict[str, str]]]] = []
    for category in re.findall(
        r'<section class="linker-trade-category"[^>]*>(.*?)</section>', text, re.S
    ):
        name = re.search(r"<h3[^>]*>(.*?)</h3>", category, re.S)
        if name is None:
            sys.exit("extract-trade: a category has no <h3>")
        qas = []
        for details in re.findall(
            r'<details class="linker-trade-question[^"]*"[^>]*>(.*?)</details>',
            category,
            re.S,
        ):
            question = re.search(r"<summary[^>]*>(.*?)</summary>", details, re.S)
            answer = re.search(r"<div[^>]*>(.*?)</div>", details, re.S)
            if question is None or answer is None:
                sys.exit("extract-trade: a question has no <summary> or <div>")
            qas.append(
                {
                    "question": html.unescape(question.group(1).strip()),
                    "answer": html.unescape(
                        re.sub(r"^<p>|</p>$", "", answer.group(1).strip()).strip()
                    ),
                }
            )
        out.append((html.unescape(name.group(1).strip()), qas))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--rev",
        default="08997063",
        help="Revision whose templates carry the rules (default: the extraction's own commit)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "plugins/linker-commerce/data/faq-trade.json",
        help="Where to write the data file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the output differs from the file on disk instead of writing it",
    )
    args = parser.parse_args()

    parsed = {
        lang: blocks(template_at(args.rev, path)) for lang, path in TEMPLATES.items()
    }
    if len(parsed["en"]) != len(parsed["de"]):
        sys.exit(
            "extract-trade: the two templates state a different number of categories"
        )

    categories: list[dict[str, Any]] = []
    # The two languages must line up: a mismatch is a refusal, not a silent
    # pairing of one language's question with another's. Indexed rather than
    # zipped, so the pairing is spelled out and the script keeps running on the
    # python3 the tools/ scripts are documented with.
    for index, (name_en, qas_en) in enumerate(parsed["en"]):
        name_de, qas_de = parsed["de"][index]
        if len(qas_en) != len(qas_de):
            sys.exit(
                f"extract-trade: '{name_en}' has {len(qas_en)} EN and {len(qas_de)} DE questions"
            )
        categories.append(
            {
                "name": {"en": name_en, "de": name_de},
                "qas": [
                    {
                        "question": {
                            "en": qa_en["question"],
                            "de": qas_de[qa_index]["question"],
                        },
                        "answer": {
                            "en": qa_en["answer"],
                            "de": qas_de[qa_index]["answer"],
                        },
                    }
                    for qa_index, qa_en in enumerate(qas_en)
                ],
            }
        )

    data = {
        "_why": WHY,
        "_rule": RULE,
        "_source": (
            "plugins/linker-commerce/content/livecanvas/faq_page.html and de/faq_page.html at "
            f"{args.rev} (#176 extraction, tools/faq/extract-trade.py --rev {args.rev})."
        ),
        "categories": categories,
    }
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.is_file() else ""
        if current != text:
            sys.exit(
                f"extract-trade: {args.out} differs from the extraction at {args.rev}"
            )
        print(f"extract-trade: {args.out} matches the extraction at {args.rev}")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    total = sum(len(category["qas"]) for category in categories)
    print(f"{len(categories)} categories, {total} qas -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
