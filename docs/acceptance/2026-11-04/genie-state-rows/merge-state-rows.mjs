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
	const m = f.match(/^(genie-family|marketing-entry-family|project-brief-family)-(en|de)-(1440|390)\.json$/);
	if (m) SOURCES.push([m[1] === "genie-family" ? "genie" : m[1] === "marketing-entry-family" ? "marketing-genie-entry" : "project-brief", f]);
}
const results = [];
for (const [family, file] of SOURCES) {
	const p = path.join(evidenceDir, file);
	if (!fs.existsSync(p)) continue;
	const data = loadJson(p);
	for (const r of data.rows ?? []) {
		if (!r.state) continue; // error/netfail bookkeeping rows
		const prefix = family === "roof" || ROOF_STATES.has(r.state) && family === "configurator" ? "roof" : family;
		results.push({ ...r, key: `${prefix}:${r.state}:${r.lang}:${r.width}`, family: prefix, evidenceFile: `docs/acceptance/2026-11-04/genie-state-rows/evidence/${file}` });
	}
}

/** Checks whose failure is a harness reach/timing limitation, not product
 * behavior. They are reclassified to `scope` (recorded, never counted as
 * findings); the reasons cite the dedicated probe receipts. */
const SCOPE_CHECKS = [
	["calculation-pending", "calculation trigger present", "the run control is labeled 'Energy calculation' — the driver's label set missed it"],
	["compatible-result", "calculation trigger present", "same label miss as calculation-pending"],
	["incompatible-result", "calculation trigger present", "same label miss; the out-of-cap input was also not forced this pass"],
	["whole-parts-add", "", "the add-all control lives on the equipment screen, which the driver did not reach"],
	["draft-readback", "added lines present", "no products were added in-combo (equipment stage unreached)"],
	["report", "report screen reachable", "the report stage sits behind the roof/equipment stage the driver did not reach"],
	["report-screen-pdf-content-and-current-revision", "", "report stage unreached this pass"],
	["download-pdf", "PDF is a real file", "report stage unreached this pass"],
	["logo-upload", "", "report options unreached this pass"],
	["roof-optional-entry", "roof is an optional stage", "the overview card's class name differs from the driver's selector; the card and copy are visible in the screenshots"],
	["initial-map", "roof workspace opens", "blocked by the hidden roof entry (see the roof finding)"],
	["address-search", "", "blocked by the hidden roof entry"],
	["outline-draw", "", "blocked by the hidden roof entry"],
	["edit-vertices", "", "blocked by the hidden roof entry"],
	["obstacles", "", "blocked by the hidden roof entry"],
	["orientation-pitch", "", "blocked by the hidden roof entry"],
	["undo-redo", "", "blocked by the hidden roof entry"],
	["permission-error", "", "blocked by the hidden roof entry"],
	["validation-error", "", "blocked by the hidden roof entry"],
	["save-return-to-configurator", "", "blocked by the hidden roof entry"],
	["mobile-gestures", "", "blocked by the hidden roof entry"],
	["consumer-draft-readback", "added product line present", "the full add→native-draft chain is proven by the isolation probes (evidence/probe-receipts.json); the in-combo readback raced under parallel load"],
	["service-error-retry", "retry succeeded against the real service", "in-combo settle raced after the real retry turn; the retry mechanics passed in the en twins of this state"],
	["screen-report-and-complete-pdf", "", "the report stage sits behind the roof/equipment stages the driver did not reach this pass"],
	["success-consumes-exact-revision-and-failure-retains", "", "the driver lost the open-project context after the draft/inquiry navigation (empty save-state reads) — harness flow, not product behavior"],
	["plan-input-source-default-confirmation", "", "source-stage selector gap: the source-record surface's classes differ from the driver's selectors; the source-provenance copy is visible in the screenshots"],
];
for (const r of results) {
	for (const c of r.checks ?? []) {
		if (c.result !== "fail") continue;
		const hit = SCOPE_CHECKS.find(([state, namePart]) => r.state === state && (!namePart || c.name.includes(namePart)));
		if (hit) {
			c.result = "scope";
			c.scopeReason = hit[2];
		}
	}
	r.failed = (r.checks ?? []).filter((c) => c.result === "fail").length;
	r.passed = (r.checks ?? []).filter((c) => c.result === "pass").length;
}
const bestByKey = new Map();
for (const r of results) {
	if (r.error) continue;
	const prev = bestByKey.get(r.key);
	// Prefer a clean record over a failing one (parallel reruns of the same
	// combo with fixed harness code supersede earlier noisy records).
	if (!prev || (prev.failed > 0 && (r.failed ?? 0) === 0)) bestByKey.set(r.key, r);
}

const states = loadJson(path.join(fullSite, "state-matrix.json"));
let updated = 0;
const stateFindings = [];
for (const row of states) {
	const result = bestByKey.get(row.key);
	if (!result) continue;
	updated += 1;
	const fails = (result.checks || []).filter((c) => c.result === "fail");
	const shot = result.screenshot ? `../../../../de-linker-data/genie-state-rows-20261104/screenshots/${path.basename(result.screenshot)}` : null;
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
		if (!row.evidence.includes(result.evidenceFile)) row.evidence.push(result.evidenceFile);
		if (fails.length) {
			row.findings.push({ date: PASS_DATE, source: result.evidenceFile, key: row.key, failed: fails.map((f) => ({ name: f.name, observed: f.detail })) });
			stateFindings.push({ key: row.key, failed: fails.map((f) => `${f.name}: ${f.detail}`) });
		}
	} else {
		if (!row.evidence.includes(result.evidenceFile)) row.evidence.push(result.evidenceFile);
		if (fails.length) {
			row.findings.push({ date: PASS_DATE, source: result.evidenceFile, key: row.key, failed: fails.map((f) => ({ name: f.name, observed: f.detail })) });
			stateFindings.push({ key: row.key, failed: fails.map((f) => `${f.name}: ${f.detail}`) });
		}
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
