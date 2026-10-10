"""Golden set: questions with the document pages that answer them, from the fact cards.

Source (`python -m index.eval.goldset`): the Model cards of the old repository's fact
cards (`knowledge/fact-cards/<brand>.md` at refs/landed/chain-tip, read with `git show`;
format: that directory's README.md). A card row is one fact with verbatim evidence,
`m<media ID> p.<physical page> "<quote>"`. A row becomes a question when its status is `evidenced`, its field has a question in
`fields.QUESTIONS`, and it cites a document of our media library that the inventory
holds (the media ID maps to the PDF's sha256). Two kinds:
- `text`: the gold evidence is the row's citations read from the text layer.
- `figure`: the field's evidence is a drawing (`fields.FIGURE_FIELDS`: clearance and
  dimension drawings, wiring and earthing diagrams, torque labels, pin-outs, layouts,
  compatibility matrices) and at least one citation is marked `(image)` - "read from
  the rendered page: a tick in a matrix, a label in a drawing ..." (fact-cards spec
  §2.2). Its gold evidence is those image citations: the answer is on the figure.
Rows of one model, field and kind merge into one question. Of all questions of a kind
whose first citation lands on the same document page, one is kept, so no single
datasheet page dominates. Each question is written in English and German.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

from index import inventory
from index.eval.fields import FIGURE_FIELDS, QUESTIONS
from index.paths import INVENTORY_PATH

OLD_REPO = Path("~/Documents/de-linker-project").expanduser()
OLD_REF = "refs/landed/chain-tip"
BRANDS = ("goodwe", "saj", "ecoflow", "pylontech")
GOLDEN_PATH = Path(__file__).with_name("golden.jsonl")

# `m5735 p.2 "Max. Input Power (kW) 150"`, optionally followed by ` (image)`. The
# quote marks are straight in most brand files and curly (“…”) in pylontech.md.
CITATION = re.compile(r'\b(m\d+) p\.(\d+) ["\u201c]([^"\u201d]*)["\u201d]( \(image\))?')
PARTNER = re.compile(r"partner:\s*([^;]+)")


@dataclass(frozen=True)
class Evidence:
    """One page that states the fact; `image` when the card read it off the rendered page."""

    doc_sha256: str
    page: int
    quote: str
    card_doc: str
    image: bool = False


@dataclass
class Question:
    """One golden question in one language."""

    id: str
    lang: str
    question: str
    brand: str
    model: str
    code: str
    kind: str
    answer: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class CardRow:
    brand: str
    model: str
    row_id: str
    field: str
    value: str
    unit: str
    scope: str
    evidence: str
    status: str


def read_card(repo: Path, ref: str, brand: str) -> str:
    """One brand file of the fact cards, as committed at `ref`."""
    return subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:knowledge/fact-cards/{brand}.md"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def card_rows(brand: str, text: str) -> Iterator[CardRow]:
    """The fact rows of every Model card in one brand file."""
    model = ""
    header: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            model = (
                title.split("·", 1)[1].strip() if title.startswith("Model card") else ""
            )
            header = []
            continue
        if not model or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not header:
            header = cells
            continue
        if set("".join(cells)) <= set("-: ") or header[:2] != ["ID", "Field"]:
            continue
        row = dict(zip(header, cells, strict=False))
        if row.get("ID") == "ID":
            continue
        yield CardRow(
            brand=brand,
            model=model,
            row_id=row.get("ID", ""),
            field=row.get("Field", ""),
            value=row.get("Value", ""),
            unit=row.get("Unit", ""),
            scope=row.get("Scope", ""),
            evidence=row.get("Evidence", ""),
            status=row.get("Status", ""),
        )


def field_code(row_id: str) -> str:
    """`EL-02b` -> `EL-02`; `EL-04 / EL-30` -> `EL-04`."""
    first = row_id.split("/")[0].strip()
    return re.sub(r"[a-z]$", "", first)


def evidence_of(row: CardRow, sha_by_media: Mapping[int, str]) -> list[Evidence]:
    """The row's citations of documents the inventory holds."""
    found = []
    for doc, page, quote, image in CITATION.findall(row.evidence):
        sha = sha_by_media.get(int(doc[1:]))
        if sha is not None:
            found.append(
                Evidence(
                    doc_sha256=sha,
                    page=int(page),
                    quote=quote,
                    card_doc=doc,
                    image=bool(image),
                )
            )
    return found


def _key_digest(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


def build(rows: Sequence[CardRow], sha_by_media: Mapping[int, str]) -> list[Question]:
    """Questions in English and German, one per (model, field, partner, kind) and first page."""
    merged: dict[
        tuple[str, str, str, str], tuple[CardRow, list[Evidence], list[str]]
    ] = {}
    for row in rows:
        code = field_code(row.row_id)
        if row.status != "evidenced" or code not in QUESTIONS:
            continue
        partner = ""
        if code == "CP-01":
            match = PARTNER.search(row.scope)
            if not match:
                continue
            partner = match.group(1).strip()
        cited = evidence_of(row, sha_by_media)
        if code in FIGURE_FIELDS and any(item.image for item in cited):
            kind, evidence = "figure", [item for item in cited if item.image]
        else:
            kind, evidence = "text", [item for item in cited if not item.image]
        if not evidence:
            continue
        key = (row.model, code, partner, kind)
        answer = " ".join(
            part for part in (row.value, row.unit) if part and part != "—"
        )
        if key not in merged:
            merged[key] = (row, [], [])
        _, gold, answers = merged[key]
        gold.extend(item for item in evidence if item not in gold)
        answers.append(answer)
    # One question per kind and first gold page: the one whose key hashes lowest.
    by_page: dict[tuple[str, str, int], tuple[str, tuple[str, str, str, str]]] = {}
    for key, (_, gold, _) in merged.items():
        page = (key[3], gold[0].doc_sha256, gold[0].page)
        digest = _key_digest(*key)
        if page not in by_page or digest < by_page[page][0]:
            by_page[page] = (digest, key)
    questions: list[Question] = []
    for digest, key in sorted(by_page.values()):
        row, gold, answers = merged[key]
        model, code, partner, kind = key
        for lang, template in zip(("en", "de"), QUESTIONS[code], strict=True):
            questions.append(
                Question(
                    id=f"{digest[:10]}-{lang}",
                    lang=lang,
                    question=template.format(model=model, partner=partner),
                    brand=row.brand,
                    model=model,
                    code=code,
                    kind=kind,
                    answer="; ".join(dict.fromkeys(answers)),
                    evidence=gold,
                )
            )
    return questions


def write(questions: Sequence[Question], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for question in questions:
            handle.write(json.dumps(asdict(question), ensure_ascii=False) + "\n")


def load(path: Path = GOLDEN_PATH) -> list[Question]:
    """The committed golden set."""
    questions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        row["evidence"] = [Evidence(**item) for item in row["evidence"]]
        questions.append(Question(**row))
    return questions


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the golden set from the fact cards."
    )
    parser.add_argument("--repo", type=Path, default=OLD_REPO)
    parser.add_argument("--ref", default=OLD_REF)
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--out", type=Path, default=GOLDEN_PATH)
    args = parser.parse_args(argv)
    sha_by_media = {
        media_id: document.sha256
        for document in inventory.load(args.inventory)
        for media_id in document.media_ids
    }
    rows = [
        row
        for brand in BRANDS
        for row in card_rows(brand, read_card(args.repo, args.ref, brand))
    ]
    questions = build(rows, sha_by_media)
    write(questions, args.out)
    commit = subprocess.run(
        ["git", "-C", str(args.repo), "rev-parse", args.ref],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    print(
        f"{len(rows)} card rows at {commit[:12]} -> {len(questions)} questions -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
