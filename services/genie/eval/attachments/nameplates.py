"""Real nameplate photos and datasheet PDFs through Genie: issue #236's evaluation.

    uv run --locked python eval/attachments/nameplates.py --wp http://127.0.0.1:9121 \
        --service http://127.0.0.1:9124 \
        --uploads ~/de-linker-data/20261018-0541/uploads \
        --out ../../docs/acceptance/2026-10-18/236/eval

Two stages, nothing pinned or scripted:

1. **Reading** (`readings.json`): every photo of `photos/` and every label image of
   `--labels` (README.md names each source) is read the way the service reads it — `attachments.read`, deepseek-flash on
   the official API — and graded against the instance's products (`nameplate.identify`,
   the Store API of `--wp`). A row passes when the brand and the model read are the
   ones printed (letters and digits compared; `*` any, a leading `*` a suffix) and the
   grade is the expected one.
2. **Turns** (`turns.json`): each case is one POST of the running service's
   `/assistant/turn` (`--service`, the one `just serve` starts), in English and German:
   the photo or PDF in `attachments`, the shell's "Attached: <name>" line in the
   message. A turn passes when it is grounded and no fallback, in the asked language,
   the `attachment` event carries the expected grade (an exact plate shows its product
   as a card), the answer names the model printed or the datasheet's figure, a
   drawings PDF had pages rendered and read, and a follow-up turn — the earlier
   turn's `reading` sent back as the proxy sends it, no file — cites the reading.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from linker_genie import attachments
from linker_genie.agent import DEFAULT_BASE_URL, _env_with_credentials, model_name
from linker_genie.lexicon import normalize
from linker_genie.nameplate import identify
from linker_genie.schema import Upload
from linker_genie.storeapi import StoreVocabulary
from linker_genie.vision import Vision

if __package__:  # imported by the tests: the sibling module through the package
    from . import papers
else:  # run as a script (the documented use): its own folder is sys.path[0]
    import papers

HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE / "cases.json").read_text())
ATTACHED = {"en": "Attached: {}", "de": "Anhang: {}"}
# An amount of money, as a price list or delivery terms print one: the answer must
# never quote it from a file (review round 1 of PR #309, item 8).
MONEY = re.compile(
    r"(?:\d[\d.,]*\s*(?:€|eur\b|euro\b))|(?:(?:€|eur\b|euro\b)\s*\d[\d.,]*)",
    re.I,
)
LEAD = re.compile(r"\b\d+\s*(?:working\s+days?|werktage[n]?|wochentage[n]?)\b", re.I)
# The service's turn may read a PDF page by page before the agent runs; the shell
# itself waits 60 s (Proxy.php).
TIMEOUT = 90.0


def _same(read: str | None, expected: list[str | None]) -> bool:
    for option in expected:
        if option == "*":
            return True
        if option is None:
            if read is None:
                return True
            continue
        if read is None:
            continue
        if option.startswith("*"):
            if normalize(read).endswith(normalize(option[1:])):
                return True
        elif normalize(read) == normalize(option):
            return True
    return False


def _upload(path: Path, kind: str | None = None) -> Upload:
    kind = kind or (
        "application/pdf"
        if path.suffix == ".pdf"
        else "image/png"
        if path.suffix == ".png"
        else "image/jpeg"
    )
    return Upload.model_validate(
        {
            "name": path.name,
            "type": kind,
            "data": base64.b64encode(path.read_bytes()).decode(),
        }
    )


def _case_path(name: str, labels_root: Path) -> Path:
    """A case's image: `labels/…` from the extracted set, anything else from the repo."""
    if name.startswith("labels/"):
        return (labels_root / name[len("labels/") :]).resolve()
    return (HERE / "photos" / name).resolve()


def readings(wp: str, labels_root: Path) -> list[dict[str, Any]]:
    env = _env_with_credentials()
    key = env.get("GENIE_API_KEY") or env.get("DEEPSEEK_API_KEY") or ""
    base = env.get("GENIE_BASE_URL") or env.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL
    see = Vision(key, base, model_name())
    vocabulary = StoreVocabulary(wp).get()
    rows = []
    for case in CASES["photos"]:
        path = _case_path(case["file"], labels_root)
        started = time.monotonic()
        [reading] = attachments.read([_upload(path)], 0, see)
        seconds = round(time.monotonic() - started, 2)
        found = identify(reading, vocabulary)
        grade = found.grade if found else None
        grades = case["grade"] if isinstance(case["grade"], list) else [case["grade"]]
        failures = []
        if reading.failed:
            failures.append(f"failed: {reading.failed}")
        if not _same(reading.brand, case["brand"]):
            failures.append(f"brand {reading.brand!r}")
        if not _same(reading.model, case["model"]):
            failures.append(f"model {reading.model!r}")
        # The grade is what the customer is offered; it is judged on its own.
        graded = grade in grades and not (
            case.get("product")
            and (not found or case["product"] not in found.product_ids)
        )
        if not graded:
            failures.append(f"grade {grade}")
        rows.append(
            {
                "file": case["file"].rsplit("/", 1)[-1],
                "synthetic": bool(case.get("synthetic")),
                "seconds": seconds,
                "kind": reading.kind,
                "brand": reading.brand,
                "model": reading.model,
                "product_type": reading.product_type,
                "ratings": len(reading.ratings),
                "grade": grade,
                "grade_pass": graded,
                "pass": not failures,
                "failures": failures,
            }
        )
        print(
            rows[-1]["file"], "PASS" if not failures else f"FAIL {failures}", flush=True
        )
    see.close()
    return rows


def _events(stream: str) -> list[tuple[str, Any]]:
    out = []
    for chunk in stream.strip().split("\n\n"):
        name = re.search(r"^event: (.+)$", chunk, re.M)
        data = re.search(r"^data: (.+)$", chunk, re.M)
        if name and data:
            out.append((name.group(1), json.loads(data.group(1))))
    return out


def _turn(
    client: httpx.Client,
    service: str,
    locale: str,
    message: str,
    uploads: list[Upload],
    readings_sent: list[dict[str, Any]],
) -> tuple[list[tuple[str, Any]], float]:
    body = {
        "conversation_id": f"eval-236-{time.time_ns()}",
        "messages": [{"role": "user", "content": message}],
        "locale": locale,
        "page_context": {"type": "home", "url": "/"},
        "attachments": [u.model_dump() for u in uploads],
        "readings": readings_sent,
    }
    started = time.monotonic()
    response = client.post(f"{service.rstrip('/')}/assistant/turn", json=body)
    response.raise_for_status()
    return _events(response.text), round(time.monotonic() - started, 2)


def turns(service: str, uploads_root: Path) -> list[dict[str, Any]]:
    rows = []
    kept: dict[tuple[str, str], list[dict[str, Any]]] = {}
    with httpx.Client(timeout=TIMEOUT) as client:
        for case in CASES["turns"]:
            for locale in ("en", "de"):
                if (
                    case.get("locale")
                    and case["locale"] != locale
                    and not case.get("question_de")
                ):
                    continue
                uploads: list[Upload] = []
                if "file" in case:
                    # Named as a phone names it: the eval's file names say what the
                    # photo shows, and the model must not read the answer there.
                    photo = _upload(
                        (HERE / "photos" / case["file"]).resolve(), case.get("type")
                    )
                    uploads = [photo.model_copy(update={"name": "IMG_4711.jpg"})]
                elif "pdf" in case:
                    uploads = [_upload(uploads_root / case["pdf"])]
                elif "generated" in case:
                    # A supplier's paper written for the evaluation (papers.py): no
                    # real price list is shipped, and the file is a customer's.
                    data = getattr(papers, case["generated"])(locale)
                    name = (
                        "Preisliste.pdf"
                        if locale == "de"
                        else "Price list.pdf"
                    )
                    if case["generated"] == "delivery_terms":
                        name = (
                            "Lieferbedingungen.pdf"
                            if locale == "de"
                            else "Delivery terms.pdf"
                        )
                    uploads = [
                        Upload.model_validate(
                            {
                                "name": name,
                                "type": "application/pdf",
                                "data": base64.b64encode(data).decode(),
                            }
                        )
                    ]
                question = case.get("question_de" if locale == "de" else "question")
                if locale == "de" and not question:
                    question = case.get("question")
                lines = [question] if question else []
                lines += [ATTACHED[locale].format(u.name) for u in uploads]
                sent = kept.get((case["after"], locale), []) if "after" in case else []
                events, seconds = _turn(
                    client, service, locale, "\n".join(lines), uploads, sent
                )
                meta: dict[str, Any] = next((p for n, p in events if n == "meta"), {})
                cards = [p for n, p in events if n == "attachment"]
                read = [p for n, p in events if n == "reading"]
                blocks = [p for n, p in events if n == "block"]
                kept[(case["id"], locale)] = read
                text = " ".join(
                    b.get("text", "") for b in blocks if b.get("type") == "text"
                )
                refs = {
                    r
                    for b in blocks
                    if b.get("type") == "text"
                    for r in b.get("refs", [])
                }
                shown = [
                    pid
                    for b in blocks
                    if b.get("type") == "cards"
                    for pid in b["product_ids"]
                ]
                failures = []
                if meta.get("fallback") or not meta.get("grounded"):
                    failures.append(
                        "fallback: " + "; ".join(meta.get("failures") or [])
                    )
                if meta.get("language") != locale:
                    failures.append(f"language {meta.get('language')}")
                if "grade" in case:
                    grades = (
                        case["grade"]
                        if isinstance(case["grade"], list)
                        else [case["grade"]]
                    )
                    if not cards or cards[0].get("match") not in grades:
                        failures.append(
                            f"grade {cards[0].get('match') if cards else None}"
                        )
                for pid in case.get("cards", []):
                    if pid not in shown:
                        failures.append(f"no card {pid}")
                if case.get("mentions") and normalize(
                    case["mentions"]
                ) not in normalize(text):
                    failures.append(f"does not name {case['mentions']}")
                if case.get("answer") and case["answer"] not in text.replace(
                    ".", ""
                ).replace(" ", ""):
                    failures.append(f"no {case['answer']} in the answer")
                if case.get("rendered") and not (
                    cards and (cards[0].get("pages_read") or 0) > 0
                ):
                    failures.append("no page read")
                if case.get("cites_reading") and not any(
                    r.startswith("att") for r in refs
                ):
                    failures.append("the reading is not cited")
                if case.get("no_money") and (amount := MONEY.search(text)):
                    failures.append(f"states an amount from the file: {amount.group(0)}")
                if case.get("no_lead_time") and (lead := LEAD.search(text)):
                    failures.append(f"states a lead time from the file: {lead.group(0)}")
                if case.get("handoff") and not any(
                    b.get("type") == "contact" for b in blocks
                ):
                    failures.append("no handoff block")
                rows.append(
                    {
                        "id": case["id"],
                        "locale": locale,
                        "seconds": seconds,
                        "route": meta.get("route"),
                        "attachment": cards,
                        "answer": text,
                        "refs": sorted(refs),
                        "cards": shown,
                        "pass": not failures,
                        "failures": failures,
                    }
                )
                print(
                    case["id"],
                    locale,
                    seconds,
                    "PASS" if not failures else f"FAIL {failures}",
                    flush=True,
                )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--wp", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--uploads", type=Path, required=True)
    parser.add_argument(
        "--labels",
        type=Path,
        default=Path("~/de-linker-data/eval/attachments").expanduser(),
        help="the folder the extracted label images live in (not in the repository)",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--stage", choices=("all", "readings", "turns"), default="all")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.stage in ("all", "readings"):
        rows = readings(args.wp, args.labels.expanduser())
        (args.out / "readings.json").write_text(
            json.dumps(rows, indent=1, ensure_ascii=False) + "\n"
        )
        print(
            f"readings: {sum(r['pass'] for r in rows)}/{len(rows)} read as printed, "
            f"{sum(r['grade_pass'] for r in rows)}/{len(rows)} graded right"
        )
    if args.stage in ("all", "turns"):
        rows = turns(args.service, args.uploads.expanduser())
        (args.out / "turns.json").write_text(
            json.dumps(rows, indent=1, ensure_ascii=False) + "\n"
        )
        print(f"turns: {sum(r['pass'] for r in rows)}/{len(rows)}")


if __name__ == "__main__":
    main()
