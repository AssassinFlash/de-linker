/** Summarize the batch: coverage before/after, remaining pending, findings. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const matrixPath = path.join(repo, "docs/acceptance/2026-10-22/full-site/state-matrix.json");
const states = JSON.parse(fs.readFileSync(matrixPath, "utf8"));
const FAMILIES = ["genie", "marketing-genie-entry", "configurator", "roof", "project-brief"];

const before = { pending: 0, "partially-verified": 0, pass: 0, passed: 0, "not-applicable": 0 };
const after = { ...before };
const famBefore = {};
const famAfter = {};
const pendingKeys = [];
for (const row of states) {
	if (!FAMILIES.includes(row.family)) continue;
	famBefore[row.family] ??= { ...before };
	famAfter[row.family] ??= { ...before };
}
for (const row of states) {
	if (!FAMILIES.includes(row.family)) continue;
	// "before" = status was set by the first pass; we cannot reconstruct it here,
	// so before counts come from the pass-1 RESULTS (308 rows: 276 pending/32 pv).
	famAfter[row.family][row.status] = (famAfter[row.family][row.status] ?? 0) + 1;
	after[row.status] = (after[row.status] ?? 0) + 1;
	if (row.status === "pending") pendingKeys.push(row.key);
}
const totalRows = FAMILIES.reduce((a, f) => a + Object.values(famAfter[f] ?? {}).reduce((x, y) => x + y, 0), 0);
console.log(JSON.stringify({ totalRows, after, famAfter, pending: pendingKeys.length, pendingKeys: pendingKeys.slice(0, 400) }, null, 1));
