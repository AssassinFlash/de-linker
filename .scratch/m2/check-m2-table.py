#!/usr/bin/env python3
"""Asserts the M2 copy batch's 43-row table against the fetched live dump.

For every row of docs/acceptance/2026-10-16/m2-copy/copy-review.md's
"定稿字符串对" table (43 rows: 41 count-1 content/meta pairs, and the two
"the Advisor zone" rows at 2 hits each), checks on the live dump that the
old string occurs exactly the expected number of times in the named field,
and that after the step applies, the old string is gone and the new one is
there. Run from the worktree:

    python3 .scratch/m2/check-m2-table.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rehearse  # noqa: E402  (its loader, dump, ids)

chrome = rehearse.chrome
dump = rehearse.dump

# row -> (post id, field, old, new, expected count). Field: "c" content,
# "d" _seopress_titles_desc. Transcribed from the review's table, A-E.
ROWS: list[tuple[int, int, str, str, str, int]] = [
    # A: the rename closeout.
    (5, 2748, "c", "<h3>Planner Sizing &amp; Compatibility Lists</h3>", "<h3>System Sizing &amp; Compatibility Lists</h3>", 1),
    (6, 2748, "c", 'aria-label="Planner sizing and compatibility lists"', 'aria-label="System sizing and compatibility lists"', 1),
    (7, 2748, "c", "<b>Planner Sizing and Compatibility Lists</b>", "<b>System Sizing and Compatibility Lists</b>", 1),
    (8, 2748, "c", '<h3 class="lk-sstage-h3">Planner Sizing and Compatibility Lists</h3>', '<h3 class="lk-sstage-h3">System Sizing and Compatibility Lists</h3>', 1),
    (9, 2748, "c", "<strong>Deliverable:</strong> Planner Sizing · Complete Parts List", "<strong>Deliverable:</strong> System Sizing · Complete Parts List", 1),
    (10, 6700, "c", "<h3>Planer-Auslegung &amp; Kompatibilitätslisten</h3>", "<h3>Systemauslegung &amp; Kompatibilitätslisten</h3>", 1),
    (11, 6700, "c", 'aria-label="Planer-Auslegung und Kompatibilitätslisten"', 'aria-label="Systemauslegung und Kompatibilitätslisten"', 1),
    (12, 6700, "c", "<b>Planer-Auslegung und Kompatibilitätslisten</b>", "<b>Systemauslegung und Kompatibilitätslisten</b>", 1),
    (13, 6700, "c", '<h3 class="lk-sstage-h3">Planer-Auslegung und Kompatibilitätslisten</h3>', '<h3 class="lk-sstage-h3">Systemauslegung und Kompatibilitätslisten</h3>', 1),
    (14, 6700, "c", "<strong>Ergebnis:</strong> Auslegung im Planer · Vollständige Stückliste", "<strong>Ergebnis:</strong> Systemauslegung · Vollständige Stückliste", 1),
    (15, 826, "c", "Site Detail maps usable roof space, module placement around obstructions, and physical dimensions before electrical sizing.", "The Roof detail step maps usable roof space, module placement around obstructions, and physical dimensions before electrical sizing.", 1),
    (16, 6871, "c", "Der Planer modelliert geeignete", "Der Lösungskonfigurator modelliert geeignete", 1),
    (17, 6871, "c", "<td>Speicherpakete, Planer-Werkzeuge und Partnerpreise</td>", "<td>Speicherpakete, Auslegungswerkzeuge und Partnerpreise</td>", 1),
    (18, 6863, "c", 'href="/de/produkte/" data-linker-assistant-open', 'href="/de/genie/" data-linker-assistant-open', 1),
    (19, 932, "c", 'href="/products/" data-linker-assistant-open', 'href="/genie/" data-linker-assistant-open', 1),
    # B: the review's additions.
    (20, 746, "c", "Design with Planner →", "Plan with the Solution Configurator →", 1),
    (21, 792, "c", "Model Project in Planner →", "Model the project in the Solution Configurator →", 1),
    (22, 746, "c", "<td>Storage packages, Planner tools, and Partner pricing</td>", "<td>Storage packages, sizing tools, and Partner pricing</td>", 1),
    (23, 1673, "c", "put to the Genie", "put to Genie", 1),
    (24, 1673, "c", "the Advisor button", "the Genie button", 1),
    (25, 1673, "c", "the Advisor zone", "the Genie zone", 2),
    (26, 1673, "c", "Advisor button zone", "Genie button zone", 1),
    (27, 6827, "c", "the Advisor button", "the Genie button", 1),
    (28, 6827, "c", "the Advisor zone", "the Genie zone", 2),
    (29, 6827, "c", "Advisor button zone", "Genie button zone", 1),
    # C: the cart ban, first two.
    (1, 13, "c", "<li>Quoted per site, not from the cart</li>", "<li>A project quote for each site</li>", 1),
    (2, 6913, "c", "<li>Angebot pro Standort, nicht aus dem Warenkorb</li>", "<li>Projektangebot pro Standort</li>", 1),
    (3, 1755, "d", "CRRC, Pylontech and GoodWe container BESS from 1.0 to 6.9 MWh, with datasheets on file, quoted per project, not from the cart.", "CRRC, Pylontech and GoodWe container BESS from 1.0 to 6.9 MWh, with datasheets on file, quoted per project.", 1),
    (4, 6917, "d", "Container-Batteriespeicher von CRRC, Pylontech und GoodWe mit 1,0 bis 6,9 MWh, mit hinterlegten Datenblättern, projektbezogen angeboten statt über den Warenkorb.", "Container-Batteriespeicher von CRRC, Pylontech und GoodWe mit 1,0 bis 6,9 MWh, mit hinterlegten Datenblättern, projektbezogen angeboten.", 1),
    # D: the cart ban, the remaining four.
    (30, 746, "c", "cannot simply be placed into an online shopping cart.", "are quoted per project.", 1),
    (31, 6871, "c", "lassen sich nicht einfach in einen Online-Warenkorb legen.", "werden projektbezogen angeboten.", 1),
    (32, 1673, "c", "(session, cart, and login cookies)", "(session, solution draft, and login cookies)", 1),
    (33, 6827, "c", "(Session-, Warenkorb- und Login-Cookies)", "(Session-, Lösungsentwurf- und Login-Cookies)", 1),
    (34, 1674, "c", "apply automatically in the cart", "apply automatically in the solution draft", 1),
    (35, 6825, "c", "werden im Warenkorb automatisch", "werden im Lösungsentwurf automatisch", 1),
    # E: the privacy sentences.
    (36, 1673, "c", "When you ask the Advisor a question", "When you ask Genie a question", 1),
    (37, 1673, "c", "not sent with Advisor messages", "not sent with your messages to Genie", 1),
    (38, 1673, "c", "Advisor conversations belonging to a signed-in account", "Conversations with Genie belonging to a signed-in account", 1),
    (39, 1673, "c", "from the Advisor's history", "from your Genie history", 1),
    (40, 6827, "c", "Wenn Sie dem Berater eine Frage stellen", "Wenn Sie Genie eine Frage stellen", 1),
    (41, 6827, "c", "nicht mit Berater-Nachrichten übermittelt", "nicht mit Ihren Nachrichten an Genie übermittelt", 1),
    (42, 6827, "c", "Berater-Konversationen, die zu einem angemeldeten Konto gehören", "Konversationen mit Genie, die zu einem angemeldeten Konto gehören", 1),
    (43, 6827, "c", "aus dem Verlauf des Beraters löschen", "aus Ihrem Genie-Verlauf löschen", 1),
]

STEP_OF: dict[int, str] = {
    2748: "services-support-en", 6700: "services-support-de",
    826: "for-installer-en", 6871: "solution-de", 6863: "faq-download-de",
    932: "faq-download-en", 746: "solution-en", 792: "commercial-storage-en",
    1673: "privacy-policy-en", 6827: "privacy-policy-de", 13: "home-en",
    6913: "home-de", 1755: "utility-storage-en", 6917: "utility-storage-de",
    1674: "terms-of-sale-en", 6825: "terms-of-sale-de",
}


def field_of(post_id: int, field: str) -> str:
    row = dump["posts"][str(post_id)]
    if field == "c":
        return row["post_content"]
    return dump["seo"].get(str(post_id), {}).get("desc", "")


def main() -> int:
    failures = 0
    for n, post_id, field, old, new, expected in ROWS:
        hay = field_of(post_id, field)
        count = hay.count(old)
        if count != expected:
            print(f"FAIL #{n} post {post_id}: count={count}, expected {expected}")
            failures += 1
        step = next(s for s in chrome.steps(rehearse.IDS) if s.key == STEP_OF[post_id])
        if field == "c":
            # After the step applies: old gone, new present.
            out = step.planned(field_of(post_id, "c"))
            if old in out:
                print(f"FAIL #{n} post {post_id}: old still present after apply")
                failures += 1
            if new not in out:
                print(f"FAIL #{n} post {post_id}: new missing after apply")
                failures += 1
        else:
            # A meta row: the step's seo_desc pair must be this row.
            if step.seo_desc != (old, new):
                print(f"FAIL #{n} post {post_id}: seo_desc pair mismatch")
                failures += 1
    # The zone rows also land in the rule channel with the right count.
    for post_id, step_key in ((1673, "privacy-policy-en"), (6827, "privacy-policy-de")):
        step = next(s for s in chrome.steps(rehearse.IDS) if s.key == step_key)
        if ("the Advisor zone", "the Genie zone") not in step.required_rules:
            print(f"FAIL the zone rule missing from {step_key}")
            failures += 1
    rows = len(ROWS)
    print(f"{rows} rows checked, {failures} failure(s)")
    assert rows == 43, f"the table should have 43 rows, has {rows}"
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
