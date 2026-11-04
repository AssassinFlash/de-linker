/** Reset the rows re-recorded by the corrected harness (2026-11-04, round 3).
 *
 * These rows carried findings produced by a harness whose own assertions were
 * wrong, so the findings are not evidence about the product:
 *
 * - **roof (44)**: the first driver looked for the roof entry inside the site
 *   workspace, where the overview is hidden, and never entered the design
 *   workspace. The entry is the rail link `a[href="#lp-design"]` (and the
 *   overview button); the workspace opens, builds faces, obstacles and saved
 *   revisions. Round 3 records the real states.
 * - **genie copy-and-rating (4)**: the DE failures were turns that did not
 *   answer ("Genie did not answer" — `Proxy` 5xx), recorded as a pass by a
 *   hard-coded check, and the missing thumb controls (which only render on an
 *   answered turn, `VoteButtons` needs the meta `turn_id`) were reported as a
 *   documents-route gap.
 * - **genie ordinary-draft-failure-owner-isolation (4)**: the driver clicked
 *   the first `[data-genie-owned-recovery]` in the DOM, which on a home page
 *   is the hero instance's panel, and then read the dock composer. Restore
 *   works; the read was on the other instance.
 * - **genie cross-surface-entry-question-consumed en:1440 / home-hero en:1440**:
 *   the pending rows of the same batch, re-recorded by the same fixed driver.
 *
 * Statuses return to `pending` and this batch's findings and receipts on
 * exactly these rows are removed, so the merge derives each row's status from
 * the round-3 evidence alone. Every other row keeps its evidence untouched.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const matrixPath = path.join(repo, "docs/acceptance/2026-10-22/full-site/state-matrix.json");
const states = JSON.parse(fs.readFileSync(matrixPath, "utf8"));

const GENIE_STATES = new Set([
	"copy-and-rating",
	"ordinary-draft-failure-owner-isolation",
	"cross-surface-entry-question-consumed",
	"home-hero",
]);

const RESET = (row) =>
	row.family === "roof" ||
	(row.family === "genie" && GENIE_STATES.has(row.state));

let reset = 0;
for (const row of states) {
	if (!RESET(row)) continue;
	reset += 1;
	row.status = "pending";
	delete row.engine_pass_evidence;
	row.findings = (row.findings ?? []).filter(
		(f) => !(typeof f === "object" && f.date === "2026-11-04" && String(f.source ?? "").includes("genie-state-rows"))
	);
	row.evidence = (row.evidence ?? []).filter((e) => !String(e).includes("genie-state-rows"));
}
fs.writeFileSync(matrixPath, `${JSON.stringify(states, null, 2)}\n`);
console.log(JSON.stringify({ resetRows: reset }));
