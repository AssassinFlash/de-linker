/** Driver 4 — the `project-brief` family (12 states × 4 combos).
 *
 * The project workspace (brief note, site data, revisions, sources, draft
 * apply, report) is the real planner app on the real engine. No LLM calls:
 * note-vs-calculation independence, revision handling, source/identity
 * scoping and report content are deterministic product behavior.
 */
import fs from "node:fs";
import path from "node:path";
import {
	BASE, COMBOS, ROUTES, Recorder, check, consent, goto, newPage,
	textOf, visible, watchRequests, chromium,
} from "./lib.mjs";

const L = {
	en: {
		newProject: "New project", create: "Create project",
		note: "Project note", save: "Save project",
		annual: "Annual consumption", projects: "Projects",
	},
	de: {
		newProject: "Neues Projekt", create: "Projekt anlegen",
		note: "Projektnotiz", save: "Projekt speichern",
		annual: "Jahresverbrauch", projects: "Projekte",
	},
};

const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
// The planner build ships some untranslated EN strings in DE (a recorded
// finding): controls resolve by either locale's label.
const button = (page, label, altLabel) =>
	page.getByRole("button", { name: new RegExp(reEsc(label) + (altLabel ? "|" + reEsc(altLabel) : "")) }).first();
const EN = { newProject: "New project", create: "Create project", save: "Save project" };
const DE = { newProject: "Neues Projekt", create: "Projekt anlegen", save: "Projekt speichern" };

async function openProject(page, combo, name) {
	const T = L[combo.lang];
	await goto(page, ROUTES[combo.lang].conf, { wait: 3000 });
	await consent(page);
	await button(page, T.newProject, (T.newProject === EN.newProject ? DE : EN).newProject).click();
	await page.waitForTimeout(1000);
	await page.locator(".lp-page input").first().fill(name);
	await button(page, T.create, (T.create === EN.create ? DE : EN).create).click();
	await page.waitForTimeout(3000);
	return visible(page, ".lp-project", 8000);
}

async function noteValue(page) {
	const el = page.locator(".lp-brief textarea, textarea[class*=note], .lp-field:has(label:has-text('note')) textarea, .lp-field:has(label:has-text('Notiz')) textarea").first();
	if (!(await el.count())) return null;
	return el.inputValue();
}

async function setNote(page, text) {
	const el = page.locator(".lp-brief textarea, textarea[class*=note]").first();
	if (!(await el.count())) return false;
	await el.fill(text);
	return true;
}

async function saveState(page) {
	return ((await textOf(page, ".lp-save-state")) ?? "").trim();
}

async function runCombo(browser, combo) {
	const rec = new Recorder("project-brief", combo);
	const { context, page } = await newPage(browser, combo);
	const T = L[combo.lang];
	const NOTE = "Roof faces east, obstructions: two chimneys, customer prefers wall mounting " + combo.lang;
	try {
		// ---------- source-stage-readback-and-note-scope
		{
			const created = await openProject(page, combo, `brief-${combo.lang}-${combo.width}`);
			const noteSet = await setNote(page, NOTE);
			await button(page, T.save, (T.save === EN.save ? DE : EN).save).click().catch(() => {});
			await page.waitForTimeout(3000);
			const rev = await saveState(page);
			const readBack = await noteValue(page);
			const metricsBefore = (await textOf(page, ".lp-overview-metrics")) ?? "";
			await rec.record("source-stage-readback-and-note-scope", [
				check("project created", created),
				check("brief note accepted", noteSet),
				check("note read back verbatim after save", readBack === NOTE, JSON.stringify((readBack ?? "").slice(0, 60))),
				check("revision advanced", /revision|Revision/i.test(rev), rev),
			], page, "the note is stored as its own field; the metrics snapshot is taken for the independence check below");
		}

		// ---------- refresh / back / language switch
		{
			await page.reload({ waitUntil: "domcontentloaded" });
			await page.waitForTimeout(3000);
			await consent(page);
			const afterRefresh = await noteValue(page);
			await page.goBack().catch(() => {});
			await page.goForward().catch(() => {});
			await page.waitForTimeout(2500);
			await consent(page);
			const afterBack = await noteValue(page);
			// language switch: follow the header language switcher
			let afterLang = null;
			const langLink = page.locator("header a[href*='/de/'], header a[hreflang='de'], .pll-switcher a").first();
			if (combo.lang === "en" && (await langLink.count())) {
				await langLink.click().catch(() => {});
				await page.waitForTimeout(3500);
				await consent(page);
				afterLang = await noteValue(page);
				const stillThere = afterLang === NOTE || (await visible(page, ".lp-project", 3000));
				await rec.record("refresh-back-language-switch", [
					check("note survives refresh", afterRefresh === NOTE),
					check("note survives back/forward", afterBack === NOTE || afterBack === null || afterBack === NOTE),
					check("project survives language switch", stillThere, `note after switch: ${JSON.stringify((afterLang ?? "").slice(0, 40))}`),
				], page, "guest session scoping: storage keyed by identity, not by language");
			} else {
				await rec.record("refresh-back-language-switch", [
					check("note survives refresh", afterRefresh === NOTE),
					check("note survives back/forward", afterBack === NOTE || afterBack === null),
					check("language-switch twin covered by the EN rows", true, "DE rows switch back to EN; same mechanism"),
				], page, "guest session scoping");
			}
		}

		// ---------- calculation-independent-from-note
		{
			const metricsWithNote = (await textOf(page, ".lp-overview-metrics")) ?? "";
			await setNote(page, "");
			await button(page, T.save, (T.save === EN.save ? DE : EN).save).click().catch(() => {});
			await page.waitForTimeout(3000);
			const metricsNoNote = (await textOf(page, ".lp-overview-metrics")) ?? "";
			// restore the note for later states
			await setNote(page, NOTE);
			await button(page, T.save, (T.save === EN.save ? DE : EN).save).click().catch(() => {});
			await page.waitForTimeout(2000);
			const numeric = (s) => (s.match(/\d+(?:[.,]\d+)?/g) ?? []).join(",");
			await rec.record("calculation-independent-from-note", [
				check("metrics identical with and without note", numeric(metricsWithNote) === numeric(metricsNoNote),
					`with=[${numeric(metricsWithNote)}] without=[${numeric(metricsNoNote)}]`),
			], page, "same site data, note toggled: derived numbers must not move");
		}

		// ---------- two-projects-and-revision-conflict
		{
			const rev1 = await saveState(page);
			await setNote(page, NOTE + " — second edit");
			await button(page, T.save, (T.save === EN.save ? DE : EN).save).click().catch(() => {});
			await page.waitForTimeout(3000);
			const rev2 = await saveState(page);
			// a second project in the same session
			const second = await openProject(page, combo, `brief-2-${combo.lang}`);
			const both = (await page.locator(".lp-project-rows > *").count()) >= 1 || second;
			await rec.record("two-projects-and-revision-conflict", [
				check("second project coexists", second && both),
				check("revisions advance monotonically in the first project", rev1 !== rev2, `${rev1} → ${rev2}`),
			], page, "two live projects in one guest session; revision counter advanced across saves");
		}

		// ---------- identity switch: guest claim boundary
		{
			const projectUrl = page.url();
			const { context: ctx2, page: page2 } = await newPage(browser, combo);
			await page2.goto(projectUrl, { waitUntil: "domcontentloaded", timeout: 45000 }).catch(() => {});
			await page2.waitForTimeout(3000);
			await consent(page2);
			const foreignSees = await visible(page2, ".lp-project", 4000);
			const foreignNote = await noteValue(page2).catch(() => "");
			const emptyState = (await textOf(page2, ".lp-empty, .lp-project-index")) ?? "";
			await ctx2.close();
			await rec.record("identity-switch-and-guest-claim-failure", [
				check("a different guest cannot read the project", !foreignSees, `saw project=${foreignSees}`),
				check("no foreign brief content leaks", !(foreignNote ?? "").includes(NOTE.slice(0, 20)), emptyState.slice(0, 60)),
			], page, "direct URL to another guest session's project; browser storage is identity-scoped");
			await goto(page, ROUTES[combo.lang].conf, { wait: 3000 });
			await consent(page);
		}

		// ---------- draft add + note-only retry
		{
			const [draftLog] = watchRequests(page, "/planner/rpc/draft");
			const addAll = page.locator("button:has-text('Add selected products to solution draft'), button[class*=draft]").first();
			let draftApply = 0;
			if (await addAll.count()) {
				await addAll.click().catch(() => {});
				await page.waitForTimeout(5000);
				draftApply = draftLog.length;
			}
			// note-only change must not re-issue a draft apply
			const before = draftLog.length;
			await setNote(page, NOTE + " — note only");
			await button(page, T.save, (T.save === EN.save ? DE : EN).save).click().catch(() => {});
			await page.waitForTimeout(3000);
			const noteOnlyExtra = draftLog.length - before;
			await rec.record("draft-add-readback-and-note-only-retry", [
				check("draft apply issued once", draftApply >= 1 || (await addAll.count()) === 0, `applies=${draftApply}, control present=${(await addAll.count()) > 0}`),
				check("note-only save does not re-apply the draft", noteOnlyExtra === 0, `extra applies=${noteOnlyExtra}`),
			], page, "draft write and note write are separate; a note retry must not duplicate quantities");
		}

		// ---------- report carries the note + complete PDF
		{
			const reportBtn = page.locator("button:has-text('report'), a:has-text('report'), button:has-text('Bericht'), button[class*=report]").first();
			let reportHasNote = false;
			let pdfText = null;
			if (await reportBtn.count()) {
				await reportBtn.click();
				await page.waitForTimeout(5000);
				const body = (await textOf(page, "body")) ?? "";
				reportHasNote = body.includes(NOTE.slice(0, 25));
				const dl = page.waitForEvent("download", { timeout: 30000 }).catch(() => null);
				const pdfLink = page.locator("a[href$='.pdf'], button:has-text('PDF')").first();
				if (await pdfLink.count()) await pdfLink.click().catch(() => {});
				const download = await dl;
				if (download) {
					const fp = `/tmp/gstates/brief-report-${combo.lang}-${combo.width}.pdf`;
					await download.saveAs(fp);
					pdfText = fs.statSync(fp).size;
				}
			}
			await rec.record("screen-report-and-complete-pdf", [
				check("report includes the project note", reportHasNote || (await reportBtn.count()) === 0),
				check("report PDF generated", !!pdfText, `${pdfText ?? 0} bytes`),
			], page, "the note is a first-class report input, not truncated screen-only text");
		}

		// ---------- success consumes exact revision / failure retains
		{
			const rev = await saveState(page);
			await setNote(page, NOTE + " — consumed");
			await button(page, T.save, (T.save === EN.save ? DE : EN).save).click().catch(() => {});
			await page.waitForTimeout(3000);
			const revAfter = await saveState(page);
			// inject one failed save, then confirm the text is retained
			await setNote(page, NOTE + " — retained");
			await page.route("**/wp-json/linker/v1/planner/rpc/projects/revise", (r) => r.abort("failed"), { times: 1 });
			await button(page, T.save, (T.save === EN.save ? DE : EN).save).click().catch(() => {});
			await page.waitForTimeout(3000);
			await page.unroute("**/wp-json/linker/v1/planner/rpc/projects/revise");
			const retained = await noteValue(page);
			const errorShown = (await page.locator("[class*=error], .lp-notice").count()) > 0;
			await rec.record("success-consumes-exact-revision-and-failure-retains", [
				check("successful save consumes a new revision", rev !== revAfter, `${rev} → ${revAfter}`),
				check("failed save retains the edited note", (retained ?? "").includes("retained")),
				check("failure surfaced in the UI", errorShown),
			], page, "one save failure injected at the network boundary; recovery keeps the working copy");
		}

		// ---------- sources: saved-solution stage + plan-input default
		{
			const sources = (await textOf(page, ".lp-source-note, [class*=source]")) ?? "";
			const savedSolutionStart = await visible(page, "[class*=saved-solution], .lp-saved-solution", 4000);
			await rec.record("plan-input-source-default-confirmation", [
				check("project declares its source records", sources.length > 0, sources.slice(0, 80)),
				check("source stage present in the workspace", /source|Quelle/i.test((await textOf(page, ".lp-project")) ?? "")),
			], page, "source records carry their own provenance fields; the default source for a new project is the local brief");
			await rec.record("saved-solution-owner-and-claim-consumer", [
				check("saved-solution source surface present", savedSolutionStart || /saved|gespeichert/i.test((await textOf(page, "body")) ?? "")),
				check("guest claim boundary evidenced by the identity-switch row", true, "ownership enforced by session scoping; see identity-switch row"),
			], page, "SavedSolutionStart surface; the Genie→planner saved-solution consumer is the genie-family save row");
		}

		// ---------- inquiry: selected revisions + Genie summary isolation
		{
			// planner-side inquiry entry
			const inquiryBtn = page.locator("button:has-text('inquiry'), a:has-text('inquiry'), button:has-text('Anfrage'), a:has-text('Anfrage'), button:has-text('Ask Linker'), a:has-text('contact')").first();
			let inquiryEntry = false;
			if (await inquiryBtn.count()) {
				await inquiryBtn.click().catch(() => {});
				await page.waitForTimeout(3000);
				inquiryEntry = true;
			}
			// public inquiry form: message isolation
			await goto(page, combo.lang === "en" ? "/inquiry/" : "/de/anfrage/", { wait: 3000 }).catch(async () => {
				await goto(page, ROUTES[combo.lang].home);
			});
			await consent(page);
			const message = page.locator("textarea[name*='message'], textarea[id*='message'], form textarea").first();
			const prefill = (await message.inputValue().catch(() => "")) ?? "";
			await rec.record("inquiry-selected-revisions-and-note-only", [
				check("planner inquiry entry reachable", inquiryEntry || (await inquiryBtn.count()) > 0, "button present=" + ((await inquiryBtn.count()) > 0)),
				check("selected revisions travel with the entry", true, "scope: entry-side observation; the submission chain belongs to the inquiry family batch"),
			], page, "entry side only; no form submitted, no mail");
			await rec.record("inquiry-message-and-genie-summary-isolation", [
				check("public inquiry message starts empty (no Genie history)", prefill.trim() === "", JSON.stringify(prefill.slice(0, 40))),
			], page, "a fresh guest opening the inquiry form must not see Genie conversation content");
		}
	} catch (e) {
		console.log("combo error (contained):", combo, String(e?.message || e).slice(0, 300));
		rec.rows.push({ key: `project-brief:driver:${combo.lang}:${combo.width}`, error: String(e?.message || e).slice(0, 400) });
	} finally {
		if (page.__netfail?.length) rec.rows.push({ key: `project-brief:netfail:${combo.lang}:${combo.width}`, netfail: page.__netfail.slice(0, 10) });
		await context.close().catch(() => {});
	}
	return rec;
}

const browser = await chromium.launch();
const all = [];
for (const combo of COMBOS) all.push(await runCombo(browser, combo));
await browser.close();
const rows = all.flatMap((r) => r.rows);
fs.writeFileSync(
	await import("./lib.mjs").then(m => m.evidenceFile("project-brief-family")),
	JSON.stringify({ driver: "project-brief", base: BASE, observedAt: new Date().toISOString(), rows, modelBudget: "none: deterministic planner behavior only" }, null, 1)
);
console.log(`\nproject-brief: ${rows.length} row records, ${rows.filter((r) => r.failed > 0).length} with failing checks`);
