/** Merge the genie-state-rows evidence into the state matrix (pass-1 schema).
 *
 * Rules (same as the full-matrix merge): pending rows with valid evidence
 * become partially-verified and carry the receipt; failing checks become
 * findings with observed values; stronger statuses are never downgraded and
 * existing evidence is never cleared. Roof-state records produced by the
 * configurator driver are re-keyed to the roof family.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const fullSite = path.join(repo, "docs/acceptance/2026-10-22/full-site");
const PASS_DATE = "2026-11-04";
const ROOF_STATES = new Set(["initial-map", "address-search", "outline-draw", "edit-vertices", "obstacles", "orientation-pitch", "undo-redo", "permission-error", "validation-error", "save-return-to-configurator", "mobile-gestures"]);

const SOURCES = [
	["genie", "genie-family.json"],
	["genie", "genie-family-supp.json"],
	["genie", "genie-family-fix.json"],
	["genie", "genie-states-round3.json"],
	["marketing-genie-entry", "marketing-entry-family.json"],
	["configurator", "configurator-family.json"],
	["roof", "roof-family.json"],
	["project-brief", "project-brief-family.json"],
	["project-brief", "project-brief-family-run2.json"],
];
function loadJson(p) { return JSON.parse(fs.readFileSync(p, "utf8")); }
function saveJson(p, v) { fs.writeFileSync(p, `${JSON.stringify(v, null, 2)}\n`); }

const evidenceDir = path.join(here, "evidence");
// combo-scoped shards from parallel runs are folded in with the same family
for (const f of fs.readdirSync(evidenceDir)) {
	const m = f.match(
		/^(genie-family|marketing-entry-family|project-brief-family|roof-family|genie-states-round3)(-fix)?-(en|de)-(1440|390)\.json$/
	);
	if (m)
		SOURCES.push([
			m[1] === "genie-family" || m[1] === "genie-states-round3"
				? "genie"
				: m[1] === "marketing-entry-family"
					? "marketing-genie-entry"
					: m[1] === "roof-family"
						? "roof"
						: "project-brief",
			f,
		]);
}
const results = [];
for (const [family, file] of SOURCES) {
	const p = path.join(evidenceDir, file);
	if (!fs.existsSync(p)) continue;
	const data = loadJson(p);
	for (const r of data.rows ?? []) {
		if (!r.state) continue; // error/netfail bookkeeping rows
		const prefix = family === "roof" || ROOF_STATES.has(r.state) && family === "configurator" ? "roof" : family;
		results.push({
			...r,
			key: `${prefix}:${r.state}:${r.lang}:${r.width}`,
			family: prefix,
			// The driver's own harness round, so a newer round supersedes an
			// older one for the same row (see bestByKey).
			fixRound: data.fixRound ?? 0,
			evidenceFile: `docs/acceptance/2026-11-04/genie-state-rows/evidence/${file}`,
		});
	}
}

/** Only an explicitly declared scope limit may be recorded as `scope`.
 *
 * The drivers mark such a half themselves (`check(name, false, detail,
 * { scope: "why this half is not exercisable" })`), so a failing check can
 * never be reclassified by a state-name lookup in the merge. Everything else
 * that failed stays a failure and becomes a finding. */
for (const r of results) {
	r.failed = (r.checks ?? []).filter((c) => c.result === "fail").length;
	r.passed = (r.checks ?? []).filter((c) => c.result === "pass").length;
	r.scoped = (r.checks ?? []).filter((c) => c.result === "scope").length;
	r.notApplicable = (r.checks ?? []).filter((c) => c.result === "not-applicable").length;
}
const bestByKey = new Map();
for (const r of results) {
	if (r.error) continue;
	const prev = bestByKey.get(r.key);
	// A newer harness round supersedes an older one for the same key; within
	// one round a clean record supersedes a failing rerun. A failing record of
	// the newest round is kept as the failing record — it is the evidence.
	const newer = !prev || (r.fixRound ?? 0) > (prev.fixRound ?? 0);
	const sameRound = prev && (r.fixRound ?? 0) === (prev.fixRound ?? 0);
	if (newer || (sameRound && prev.failed > 0 && (r.failed ?? 0) === 0)) bestByKey.set(r.key, r);
}

const states = loadJson(path.join(fullSite, "state-matrix.json"));
let updated = 0;
const stateFindings = [];
for (const row of states) {
	const result = bestByKey.get(row.key);
	if (!result) continue;
	updated += 1;
	const fails = (result.checks || []).filter((c) => c.result === "fail");
	// Round-3 captures are committed next to this record and referenced
	// repo-relative. The earlier rounds' captures were never committed (36 MB of
	// PNGs); their file exists by basename in the owner's data directory, which
	// RESULTS.md names. A basename keeps a machine-specific absolute path out of
	// the committed matrix.
	const committed = result.screenshot && fs.existsSync(path.join(repo, result.screenshot));
	const shot = result.screenshot
		? committed
			? result.screenshot
			: path.basename(result.screenshot)
		: null;
	const entry = {
		date: PASS_DATE,
		source: result.evidenceFile,
		scope: result.scope,
		checks: result.checks,
		screenshot: shot,
		model_channel: result.scope?.includes("deepseek") ? "deepseek-flash official via the local genie service (real turn)" : "no model call (deterministic UI/engine behavior)",
	};
	if (row.status === "pending") {
		row.status = "partially-verified";
		row.engine_pass_evidence = entry;
	} else if (row.status !== "not-applicable") {
		// A stronger status is never downgraded; the newest round's receipt
		// replaces the older one for this row.
		row.engine_pass_evidence = entry;
	}
	if (!row.evidence.includes(result.evidenceFile)) row.evidence.push(result.evidenceFile);
	// This batch owns the findings it produced on a row. A superseded harness
	// round's finding is not evidence about the product any more, so every
	// finding this batch wrote on the row is dropped before the current
	// round's are added — re-runs are idempotent, and an old round's
	// observation cannot outlive the round that replaced it. Findings from
	// other batches (dated differently, or from another source tree) are kept.
	row.findings = (row.findings ?? []).filter(
		(f) =>
			!(
				typeof f === "object" &&
				f.date === PASS_DATE &&
				String(f.source ?? "").includes("genie-state-rows")
			)
	);
	if (fails.length) {
		row.findings.push({ date: PASS_DATE, source: result.evidenceFile, key: row.key, failed: fails.map((f) => ({ name: f.name, observed: f.detail })) });
		stateFindings.push({ key: row.key, failed: fails.map((f) => `${f.name}: ${f.detail}`) });
	}
}
saveJson(path.join(fullSite, "state-matrix.json"), states);

const after = {};
for (const row of states) after[row.status] = (after[row.status] || 0) + 1;
const famCount = {};
for (const f of ["genie", "marketing-genie-entry", "configurator", "roof", "project-brief"]) {
	famCount[f] = states.filter((r) => r.family === f).reduce((a, r) => { a[r.status] = (a[r.status] || 0) + 1; return a; }, {});
}
saveJson(path.join(evidenceDir, "after-recount.json"), { after, familyStatuses: famCount, updatedRows: updated, matchedKeys: bestByKey.size });
console.log(JSON.stringify({ updated, matched: bestByKey.size, after, stateFindings: stateFindings.length }, null, 1));
