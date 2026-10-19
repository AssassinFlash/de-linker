"""Apply the round-2 overturns to the stored 2026-10-19 graded rows.

Importing this module does not read the evidence directory. ``main`` reads
``final.jsonl``, drops the raw SSE, and writes ``verdicts.jsonl`` plus the
``cases.md`` index.

The six cases added after that run (A6, A7, I7, each EN and DE) are not in
the graded file and are not invented here.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import summary

CAMPAIGN = Path(__file__).resolve().parents[1]
POINTER = "~/de-linker-data/campaign-330/evidence/final.jsonl"
CERTIFICATE = Path(
    "~/de-linker-local/c330/wordpress/wp-content/uploads/2026/10/"
    "GW_ESA-5-30kW_Certificate_IEC-62109.pdf"
).expanduser()

# Eight stored passes the two-axis review overturned: six content defects,
# two parity failures. A parity row is not a pass and not a new product defect.
OVERTURNS: dict[str, dict[str, str]] = {
    "F3-DE": {
        "grade": "defect",
        "defect": "D8",
        "repro": "Ist der GoodWe H2-15K-T3 von euch? The answer denies the model and shows GoodWe ESA cards. SAJ H2-15K-T3 is id 2063; that card is absent.",
        "note": "F3-EN names SAJ id 2063. F3-DE denies the model and shows ESA cards 6512 and the rest.",
    },
    "G4-DE": {
        "grade": "defect",
        "defect": "D9",
        "repro": "The DE answer says the code is absent and so is the CHS2 series, then shows unrelated SAJ cards. G4-EN refuses the invented code and shows CHS2 ids 1959, 1960, 1961.",
        "note": "Series denial against cards the EN twin showed. The live fixture no longer uses a shop-prefixed invented code; this row keeps the 2026-10-19 wording.",
    },
    "I1-DE": {
        "grade": "defect",
        "defect": "D10",
        "repro": "Ich brauche einen 10-kWh-Wechselrichter. The answer is the fallback line Hier sind passende Produkte, with no kWh-to-kW correction.",
        "note": "Grounding blocked the digit 2 (failures: model text contains numbers). That block is not a unit correction. I1-EN corrected the storage figure.",
    },
    "C1-EN": {
        "grade": "defect",
        "defect": "D11",
        "repro": "The list ends Which of these are single-phase inverters? The turn is a parts card of 200 rows. The question is not answered.",
        "note": "An overlong list still has to land on the question that follows it. The missing intro line is not a pass.",
    },
    "C1-DE": {
        "grade": "defect",
        "defect": "D11",
        "repro": "The list ends Welche davon sind einphasige Wechselrichter? The turn is a parts card of 200 rows. The question is not answered.",
        "note": "Same miss as C1-EN.",
    },
    "A4-EN": {
        "grade": "defect",
        "defect": "D12",
        "repro": "what is the output of the GooodWe GW5K-ETA-G2O? The answer says the IEC certificate rates the output at 10 / 30 V and 11 / 30 V, 3L/N/PE.",
        "note": "Card 6512 is the right product. The certificate page states 3L/N/PE, 220/380, 230/400. The 10 and 11 are current-row indexes.",
    },
    "F1-DE": {
        "grade": "parity",
        "defect": "parity",
        "pair": "F1",
        "repro": "Is the SAJ GW10K-ETA-G20 in stock? EN is the D1 handoff. DE names GoodWe and shows cards 3556 and 1182.",
        "note": "DE answers the brand conflict. EN does not. Same question, different structure. Not a separate pass.",
    },
    "J5-DE": {
        "grade": "parity",
        "defect": "parity",
        "pair": "J5",
        "repro": "Smallest inverter of at least 30 kW. EN answers GW75K-ET-G10 after application=commercial. DE answers GW30K-ETA-G20 (6518).",
        "note": "DE is the correct product. Counting it as a pass hides the EN/DE split. Not a separate pass.",
    },
}

# Defect ids that the 2026-10-19 hand grade already had. Kept, not re-litigated.
KEPT_DEFECTS: dict[str, dict[str, str]] = {
    "A3-EN": {
        "defect": "D7",
        "note": "BD-8 is below lexicon.MIN_CODE 4. Only the Battery Base card. EF BD-8-S2 is id 3582.",
    },
    "F1-EN": {
        "defect": "D1",
        "note": "route=products. search-products text GW10K-ETA-G20 brand saj returns qualified []. Handoff, grounding rejects, fallback.",
    },
    "F4-DE": {
        "defect": "D5",
        "note": "EcoFlow GW5K-ETA-G20: says no EcoFlow product, misses that the model is GoodWe. F4-EN shows the GoodWe card.",
    },
    "G1-EN": {
        "defect": "D1",
        "note": "route=model, matches empty, no search call. Handoff fallback. The fake GW50K is not in the lexicon, so this is not the brand-AND search.",
    },
    "G1-DE": {
        "defect": "D1",
        "note": "route=model, jev unsure 0.70, no search call. Handoff sentence. Same shape as G1-EN.",
    },
    "G5-EN": {
        "defect": "D4",
        "note": "pydantic-ai Tool linker_search_knowledge exceeded max retries count of 1. Products fallback still emitted card 3608 and no DEGRADED sentence.",
    },
    "H4-EN": {
        "defect": "D2",
        "note": "route._search_input searched only the first of three models. The answer says the other two return no entry. H4-DE found all three.",
    },
    "I5-DE": {
        "defect": "D3",
        "note": "Jev sizing 0.77. The model called size-hint with phase=1. URL ?pv_kwp=12&phase=1. The customer did not say single-phase.",
    },
    "J5-EN": {
        "defect": "D6",
        "note": "Second search-products call is device_class inverters, application commercial, limit 12. That filter drops the home GW30K-ETA-G20. The model supplied application=commercial.",
    },
}

OBSERVATIONS: dict[str, str] = {
    "B1-EN": "Battery emoji read as a storage question; batteries plus a question.",
    "E6-EN": "Only single-phase EHA models listed. The ETA family is not mentioned.",
    "H5-EN": "GW8K-ETA-G20 missing from the cards, and the answer says so.",
    "H5-DE": "GW8K-ETA-G20 disclosed as not returned.",
    "K2-EN": "Empty sheet described as could not read. The sheet had no data rows.",
    "C5-EN": "The intro line is counted as a row that is not a product.",
    "K5-EN": "250 rows: 200 parsed, truncated true, first part disclosed. The 199 is that matched-count sentence.",
}

# One recorded check per row whose triage flag starts with "numbers to verify".
# cited-document means the answer names a document. This round did not re-read
# those PDF bytes. feed-field was checked against the 20261019-1409 snapshot.
# A4-EN is the one recorded fabrication.
NUMBER_CHECKS: dict[str, dict[str, str]] = {
    "A2-DE": {
        "status": "cited-document",
        "numbers": "10,12,9.999",
        "method": "The answer cites the user-manual model table and the datasheet series line. Those PDF bytes were not re-read.",
        "record": "Named models GW10K-ETA-G20, GW9.999K-ETA-G20, GW12K-ETA-G20. Feed has GW9.999K-ETA-G20 as id 6514. Not a fabrication record.",
    },
    "A4-DE": {
        "status": "feed-field",
        "numbers": "100,4.5,4.8,5",
        "method": "Feed product 2093 (BU3-5.0-TV2-PRO): nominal_kwh 5, usable_kwh 4.8. 100 Ah and the alternate 4.5 kWh are cited from the manual table. Manual PDF bytes were not re-read.",
        "record": "5 and 4.8 match the snapshot. 100 and 4.5 stay on the cited manual sentence.",
    },
    "A4-EN": {
        "status": "fabricated",
        "numbers": "11",
        "method": "pdftotext -f 2 -l 2 -layout on the local IEC 62109 certificate (ESA 5-30 kW). Feed product 6512 lists datasheet, manual and warranty, not this certificate. ac_power_kw is 5 and pv_input_kw is 10.",
        "record": "Certificate: Rated Output Volt. [Va.c.] : 3L/N/PE, 220/380, 230/400. Backup voltage is the same line. The answer says 10 / 30 V and 11 / 30 V. Rows 10 and 11 of the current table are 45.5 A at 380 V.",
    },
    "B4-DE": {
        "status": "cited-document",
        "numbers": "10000,11000,16500,60",
        "method": "The answer cites the HS2-10K-T2-X datasheet (W, VA, peak for 60 s). Feed product 1182 has empty figures and ac_power_kw 10. Datasheet PDF bytes were not re-read.",
        "record": "10000 W / 11000 VA / 16500 VA / 60 s are the cited datasheet sentence, not snapshot fields.",
    },
    "C3-EN": {
        "status": "cited-document",
        "numbers": "0.8,10000,11000,14.5,180,20000,242,3000,40,4000,45,50",
        "method": "The answer cites the SAJ H2 10-30K datasheet and user manual and shows card 4107. Feed figures for 4107 are empty. Those PDF bytes were not re-read.",
        "record": "The flagged set is the datasheet block in the answer (power, current, voltage window, altitude, temperatures, dimensions).",
    },
    "D1-EN": {
        "status": "cited-document",
        "numbers": "96.4,98.0,98.00",
        "method": "The answer cites the GW5K-ETA-G20 datasheet and user manual for max, European and battery-to-AC efficiency. Feed product 6512 has empty figures. Those PDF bytes were not re-read.",
        "record": "96.4 / 98.0 / 98.00 are the three efficiency sentences. No snapshot field holds them.",
    },
    "D4-DE": {
        "status": "feed-field",
        "numbers": "108",
        "method": "Feed kwh_range.max on the shown GW ESA cards, including GW10K-ETA-G20 id 3556.",
        "record": "The answer says storage 5-108 kWh. Snapshot kwh_range on 3556 is min 5, max 108.",
    },
    "D5-DE": {
        "status": "cited-document",
        "numbers": "97.6,98.0",
        "method": "The answer cites the HS2 datasheet efficiency row. Feed product 1182 has empty figures. Datasheet PDF bytes were not re-read.",
        "record": "98.0% max and 97.6% Euro are the cited datasheet sentence.",
    },
    "E2-DE": {
        "status": "cited-document",
        "numbers": "10000,11000",
        "method": "The answer cites the H2 datasheet and the manual table (page cited in the document block). Feed product 4107 has empty figures and ac_power_kw 10. PDF bytes were not re-read.",
        "record": "10000 W and 11000 VA are the cited rated-power sentence.",
    },
    "E3-EN": {
        "status": "cited-document",
        "numbers": "10000,11000,14.5,16.0",
        "method": "The answer cites the H2-10K-T3 datasheet section and the manual. Feed product 4107 has empty figures. PDF bytes were not re-read.",
        "record": "Rated power, apparent power and the two current figures are the cited datasheet sentences.",
    },
    "E5-EN": {
        "status": "cited-document",
        "numbers": "108,12,12.0,13.2,18,270,326,350,4,5.0,55,550",
        "method": "108 is feed kwh_range.max on GW5.1-BAT-D-G20 id 6519 (also nominal 5.12, usable 5). The module currents, voltages and temperatures are cited from the ESA datasheet p.3 and the manual pp.334-335. Those PDF bytes were not re-read.",
        "record": "5-108 kWh matches the snapshot range. The other flagged figures stay on the cited document blocks.",
    },
    "H1-DE": {
        "status": "feed-field",
        "numbers": "108",
        "method": "Feed kwh_range.max on compared GW10K-ETA-G20 id 3556.",
        "record": "The compare answer says 5-108 kWh. Snapshot max is 108.",
    },
    "H1-EN": {
        "status": "feed-field",
        "numbers": "108",
        "method": "Feed kwh_range.max on compared GW10K-ETA-G20 id 3556.",
        "record": "Same 5-108 kWh range as H1-DE.",
    },
    "I2-EN": {
        "status": "feed-field",
        "numbers": "108",
        "method": "Feed kwh_range.max on the shown GW battery modules (6520 and the ESA range).",
        "record": "The answer says modules combine up to 5-108 kWh. Snapshot max on those modules is 108.",
    },
    "I6-DE": {
        "status": "mixed",
        "numbers": "29.999,29900,29999",
        "method": "29.999 is feed ac_power_kw on CHS2-29.9K-T4-X id 1959. 29900 and 29999 are cited from the manual, the datasheet and the certificate. Those PDF bytes were not re-read. The card list missed id 1959, which is a separate flag.",
        "record": "29.999 kW matches the snapshot. 29900 VA and 29999 VA stay on the cited document sentences.",
    },
    "I6-EN": {
        "status": "cited-document",
        "numbers": "29900,29999",
        "method": "The answer cites the user-manual system table (29900 VA) and the datasheet (29999 VA) and shows card 1959. Feed ac_power_kw is 29.999, which triage did not flag. PDF bytes were not re-read.",
        "record": "29900 and 29999 are the two document sentences. The product AC figure in the snapshot is 29.999 kW.",
    },
    "J5-DE": {
        "status": "feed-field",
        "numbers": "2,29.999",
        "method": "29.999 is feed ac_power_kw on SAJ H2-30K-T3-DE id 1181, the model the answer names. The flagged 2 is the H2 token. The shown card is 6518 (GW30K-ETA-G20, ac 30), so triage did not see 1181.",
        "record": "29.999 kW matches id 1181. The digit 2 is the H2 in that model name. Not a voltage-style fabrication.",
    },
    "K5-EN": {
        "status": "parts-count",
        "numbers": "199",
        "method": "The parts block sentence says 199 of the parsed rows matched. The block is truncated.",
        "record": "199 is the matched-count sentence, not a catalogue figure.",
    },
}

_NONE: dict[str, str] = {
    "status": "no-unexplained-numbers",
    "numbers": "",
    "method": "triage",
    "record": "This row has no numbers-to-verify flag.",
}


def flagged_numbers(row: dict[str, Any]) -> bool:
    flags = row.get("flags") or []
    return any(
        isinstance(flag, str) and flag.startswith("numbers to verify") for flag in flags
    )


def verdict_of(row: dict[str, Any]) -> dict[str, Any]:
    """One stored turn, without the raw SSE, with the round-2 grade applied."""
    out = {key: value for key, value in row.items() if key != "stream"}
    case_id = str(row["case"])
    if case_id in OVERTURNS:
        over = OVERTURNS[case_id]
        out["grade"] = over["grade"]
        out["defect"] = over["defect"]
        out["grade_note"] = over["note"]
        out["repro"] = over["repro"]
        out["regrade"] = "round-2"
        if "pair" in over:
            out["pair"] = over["pair"]
    elif case_id in KEPT_DEFECTS:
        kept = KEPT_DEFECTS[case_id]
        out["grade"] = "defect"
        out["defect"] = kept["defect"]
        out["grade_note"] = kept["note"]
        out["regrade"] = None
    else:
        out["grade"] = row.get("grade")
        out["defect"] = None
        out["grade_note"] = OBSERVATIONS.get(case_id)
        out["regrade"] = None
    check = dict(NUMBER_CHECKS[case_id] if case_id in NUMBER_CHECKS else _NONE)
    if flagged_numbers(row) and case_id not in NUMBER_CHECKS:
        check = {
            "status": "missing",
            "numbers": "",
            "method": "none",
            "record": "A numbers flag has no recorded check.",
        }
    out["numbers_verification"] = check
    out["evidence"] = f"{POINTER}#{case_id}"
    if case_id.startswith("G4"):
        out["utterance_note"] = (
            "The request text is the 2026-10-19 turn. The live fixture uses an "
            "NEX- prefix. This row is the customer's wording, not a catalogue SKU."
        )
    return out


def certificate_voltage_line(path: Path | None = None) -> str | None:
    """The Rated Output Volt line, when pdftotext can read the local certificate."""
    pdf = CERTIFICATE if path is None else path
    if not pdf.is_file():
        return None
    done = subprocess.run(
        ["pdftotext", "-f", "2", "-l", "2", "-layout", str(pdf), "-"],
        check=False,
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        return None
    for line in done.stdout.splitlines():
        if "Rated Output Volt" in line and "Backup" not in line:
            return line.strip()
    return None


def attach_certificate(
    verdicts: list[dict[str, Any]], path: Path | None = None
) -> None:
    line = certificate_voltage_line(path)
    for verdict in verdicts:
        if verdict["case"] != "A4-EN":
            continue
        check = verdict["numbers_verification"]
        check["pdf_reread"] = line is not None
        if line is not None:
            check["pdf_line"] = line


def check_flag_coverage(rows: list[dict[str, Any]]) -> list[str]:
    flagged = {str(row["case"]) for row in rows if flagged_numbers(row)}
    problems: list[str] = []
    missing = flagged - set(NUMBER_CHECKS)
    extra = set(NUMBER_CHECKS) - flagged
    if missing:
        problems.append("flagged with no check: " + ", ".join(sorted(missing)))
    if extra:
        problems.append("check with no flag: " + ", ".join(sorted(extra)))
    return problems


def render_cases(verdicts: list[dict[str, Any]]) -> str:
    counts = {"pass": 0, "defect": 0, "parity": 0}
    for verdict in verdicts:
        grade = str(verdict.get("grade"))
        if grade in counts:
            counts[grade] += 1
    lines = [
        "# #330 逐例判定",
        "",
        "本文件是判定索引。完整请求、meta、blocks 和数字复核在同目录",
        "`verdicts.jsonl`（一行一例，不含原始 SSE）。`evidence` 指向本机",
        "`final.jsonl` 里该 case 的那一行。",
        "",
        f"已评分 {len(verdicts)} 例：pass {counts['pass']}，"
        f"defect {counts['defect']}，parity {counts['parity']}。",
        "装具里另有 6 例尚未开跑（A6-EN、A6-DE、A7-EN、A7-DE、I7-EN、I7-DE），",
        "不计入这 111 例。",
        "",
        summary.render(verdicts),
        "",
        "| case | class | lang | grade | defect | s | evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for verdict in verdicts:
        defect = verdict.get("defect") or ""
        lines.append(
            f"| {verdict['case']} | {verdict['class']} | {verdict['lang']} "
            f"| {verdict['grade']} | {defect} | {verdict.get('duration_s')} "
            f"| {verdict['evidence']} |"
        )
    lines.append("")
    return "\n".join(lines)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                rows.append(parsed)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--final",
        default="~/de-linker-data/campaign-330/evidence/final.jsonl",
    )
    parser.add_argument("--verdicts", default=str(CAMPAIGN / "verdicts.jsonl"))
    parser.add_argument("--cases", default=str(CAMPAIGN / "cases.md"))
    arguments = parser.parse_args(argv)
    source = Path(arguments.final).expanduser()
    rows = load_jsonl(source)
    problems = check_flag_coverage(rows)
    if problems:
        for problem in problems:
            print(problem)
        return 1
    verdicts = [verdict_of(row) for row in rows]
    attach_certificate(verdicts)
    out = Path(arguments.verdicts)
    with out.open("w", encoding="utf-8") as handle:
        for verdict in verdicts:
            handle.write(json.dumps(verdict, ensure_ascii=False) + "\n")
    Path(arguments.cases).write_text(render_cases(verdicts), encoding="utf-8")
    print(summary.render(verdicts))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
