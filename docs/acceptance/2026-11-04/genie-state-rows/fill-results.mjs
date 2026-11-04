/** Fill the RESULTS.md table tokens from the merged matrix + recount. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const states = JSON.parse(fs.readFileSync(path.join(repo, "docs/acceptance/2026-10-22/full-site/state-matrix.json"), "utf8"));
const FAMS = {
	genie: ["genie", "MERGE_NUM_genie", "MERGE_PEND_genie", "FIND_genie"],
	mkt: ["marketing-genie-entry", "MERGE_NUM_mkt", "MERGE_PEND_mkt", "FIND_mkt"],
	conf: ["configurator", "MERGE_NUM_conf", "MERGE_PEND_conf", "FIND_conf"],
	roof: ["roof", "MERGE_NUM_roof", "MERGE_PEND_roof", "FIND_roof"],
	pb: ["project-brief", "MERGE_NUM_pb", "MERGE_PEND_pb", "FIND_pb"],
};
let md = fs.readFileSync(path.join(here, "RESULTS.md"), "utf8");
const recount = JSON.parse(fs.readFileSync(path.join(here, "evidence/after-recount.json"), "utf8"));
const totals = { rows: 0, upgraded: 0, pending: 0, findings: 0 };
for (const [key, [fam, numTok, pendTok, findTok]] of Object.entries(FAMS)) {
	const rows = states.filter((r) => r.family === fam);
	const pv = rows.filter((r) => r.status === "partially-verified").length;
	const pending = rows.filter((r) => r.status === "pending").length;
	const findings = rows.filter((r) => (r.findings ?? []).some((f) => f.date === "2026-11-04" && String(f.source || "").includes("genie-state-rows"))).length;
	md = md.replace(numTok, String(pv)).replace(pendTok, String(pending)).replace(findTok, String(findings));
	totals.rows += rows.length; totals.upgraded += pv; totals.pending += pending; totals.findings += findings;
}
md = md.replace("MERGE_TOTAL_UPGRADED", String(totals.upgraded)).replace("MERGE_TOTAL_PENDING", String(totals.pending));
fs.writeFileSync(path.join(here, "RESULTS.md"), md);
console.log(JSON.stringify({ ...totals, recountUpdated: recount.updatedRows, matched: recount.matchedKeys }));
