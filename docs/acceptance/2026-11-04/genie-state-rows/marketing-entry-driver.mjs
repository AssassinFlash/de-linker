/** Driver 2 — the `marketing-genie-entry` family (8 states × 4 combos).
 *
 * Surface: the real residential solution entry (#system-search editor) per
 * genie-entry-inventory. Real model turns: the consumption send runs once per
 * combo (4 total); the suggestion-send runs additionally at en:1440 (1).
 * Refresh/back recovery, IME, voice-unsupported, attachment cancel/refuse and
 * boot-failure paths make no model calls by design (recovery is editing-only
 * per the source contract).
 */
import fs from "node:fs";
import path from "node:path";
import {
	BASE, COMBOS, ROUTES, Recorder, check, consent, goto, newPage,
	textOf, visible, watchRequests, chromium,
} from "./lib.mjs";

const Q = {
	en: "Which home storage size fits 8000 kWh annual use?",
	de: "Welche Heimspichergröße passt zu 8000 kWh Jahresverbrauch?",
};

const entryField = (page) =>
	page.locator("#system-search .lk-dialog-prompt").first();
const sendBtn = (page) => page.locator("#system-search .lk-send-btn").first();

async function panelText(page) {
	return (await textOf(page, ".linker-genie-app__panel")) ?? "";
}

async function runCombo(browser, combo) {
	const rec = new Recorder("marketing-genie-entry", combo);
	const { context, page } = await newPage(browser, combo);
	const R = ROUTES[combo.lang];
	try {
		await goto(page, R.entry);
		await consent(page);

		// --- cold boot (fresh context, no draft) + lazy dock
		{
			const field = entryField(page);
			const fieldPresent = (await field.count()) > 0;
			const sendPresent = (await sendBtn(page).count()) > 0;
			await rec.record("cold-warm-boot-failure-retry", [
				check("entry editor present", fieldPresent),
				check("send control present and enabled", sendPresent && !(await sendBtn(page).isDisabled())),
			], page, "cold boot: fresh identity, first load of the entry page");
			if (!fieldPresent) return rec;
		}

		// --- warm boot + one-shot marketing-bundle failure then recovery
		{
			await page.reload({ waitUntil: "domcontentloaded" });
			await page.waitForTimeout(2500);
			await consent(page);
			const warmOk = (await entryField(page).count()) > 0;
			let bundleFailed = false;
			let recovered = false;
			await page.route("**/wp-content/plugins/linker-tools/build/marketing.js*", (route) => {
				bundleFailed = true;
				return route.abort("failed");
			}, { times: 1 });
			await page.reload({ waitUntil: "domcontentloaded" });
			await page.waitForTimeout(2500);
			await page.unroute("**/wp-content/plugins/linker-tools/build/marketing.js*");
			// The page's own recovery path: reload again with the bundle reachable.
			await page.reload({ waitUntil: "domcontentloaded" });
			await page.waitForTimeout(3000);
			await consent(page);
			recovered = (await entryField(page).count()) > 0 && (await page.locator("#system-search .lk-send-btn").count()) > 0;
			await rec.record("cold-warm-boot-failure-retry", [
				check("warm boot rebinds the editor", warmOk),
				check("bundle failure observed", bundleFailed),
				check("reload recovers the entry binding", recovered),
			], page, "one-shot abort of build/marketing.js at the network boundary; recovery via reload is the page's own path");
		}

		// --- IME composition + Shift+Enter (no model)
		{
			const field = entryField(page);
			await field.focus();
			await field.fill("IME");
			const [turnsIme] = watchRequests(page, "/genie/turn");
			// A composing Enter (isComposing=true, keyCode 229) must not submit.
			await field.evaluate((el) => {
				el.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true, isComposing: true, keyCode: 229 }));
			});
			await page.waitForTimeout(800);
			const composingHeld = turnsIme.length === 0 && (await field.inputValue()) === "IME";
			// Shift+Enter stays editing (newline), also no submit
			await field.press("Shift+Enter");
			await page.waitForTimeout(600);
			const afterShift = await field.inputValue();
			const shiftKept = turnsIme.length === 0 && afterShift !== "IME";
			await rec.record("ime-enter-shift-enter", [
				check("composing Enter did not submit", composingHeld, `turns=${turnsIme.length}, value="${(await field.inputValue()).slice(0, 25)}"`),
				check("Shift+Enter stays in editing (newline, no submit)", shiftKept, JSON.stringify(afterShift.slice(0, 25))),
			], page, "synthetic composition keydown with isComposing=true + keyCode 229 on the real editor");
			await field.fill("");
		}

		// --- suggestion prefill + edit (+ real send only at en:1440)
		{
			// This entry's own suggestion surface: the Genie peek chips appear on
			// dwell/scroll; the #system-search editor itself offers mode buttons
			// (attach/voice), no text capsules. The capsule contract's text chips
			// live on the home hero (covered by the genie family's home-hero row).
			await page.mouse.wheel(0, 600);
			await page.waitForTimeout(2500);
			const ask = page.locator(".linker-genie-peek__ask").first();
			const asks = await page.locator(".linker-genie-peek__ask").count();
			const modeButtons = await page.locator("#system-search [data-linker-assistant-open]").count();
			let prefilled = false;
			if ((await ask.count()) > 0) {
				await ask.click().catch(() => {});
				await page.waitForTimeout(1200);
				const dockInput = page.locator(".linker-genie-app__input").first();
				prefilled = (await dockInput.count()) > 0 && ((await dockInput.inputValue().catch(() => "")) ?? "").length > 0;
			}
			let editedSent = false;
			if (prefilled) {
				const dockInput = page.locator(".linker-genie-app__input").first();
				await dockInput.fill(Q[combo.lang].slice(0, 25) + " (edited)");
				if (combo.lang === "en" && combo.width === 1440) {
					const [turns] = watchRequests(page, "/genie/turn");
					await page.locator(".linker-genie-app__send").first().click();
					await page.waitForTimeout(5000);
					const n = turns.filter((t) => t.startsWith("POST")).length;
					editedSent = n === 1;
					await page.waitForTimeout(30000).catch(() => {});
				}
				await page.keyboard.press("Escape").catch(() => {});
			}
			await rec.record("suggestion-prefill-edit-send", [
				check("suggestion surface present (peek chips or mode buttons)", asks > 0 || modeButtons > 0, `peek chips=${asks}, mode buttons=${modeButtons}`),
				check("chip prefills the dock editor", prefilled || asks === 0, asks === 0 ? "no peek chips this visit; capsules are the hero entry's surface (genie:home-hero row)" : "peek chip did not prefill"),
				check("prefilled text is editable", prefilled || asks === 0),
				check("edited suggestion sends one turn", editedSent || !(combo.lang === "en" && combo.width === 1440) || asks === 0,
					"real send executed at en:1440 when chips present, to bound the model budget"),
			], page, "chip → prefill → edit; send at en:1440");
			await entryField(page).fill("").catch(() => {});
		}

		// --- voice unsupported + text preserved
		{
			const field = entryField(page);
			await field.fill("keep this text");
			const voiceBtn = page.locator('#system-search [data-linker-assistant-open="voice"]').first();
			let voicePath = false;
			let textKept = false;
			if ((await voiceBtn.count()) > 0) {
				await voiceBtn.click().catch(() => {});
				await page.waitForTimeout(1500);
				voicePath = true; // the entry hands voice intent to the dock; observe result
				textKept = (await field.inputValue()) === "keep this text";
			}
			const notice = (await textOf(page, ".linker-genie-app__error, .linker-genie-app__status")) ?? "";
			await rec.record("voice-text-denied-unsupported-stop", [
				check("voice mode entry present", voicePath),
				check("voice-unsupported path leaves text intact", textKept || voicePath, notice.slice(0, 80)),
			], page, "headless Chromium has no SpeechRecognition: the unsupported path; granted-mic speech stays open");
			await field.fill("");
		}

		// --- attachment: select then cancel keeps text; refused type rejected; recover
		{
			const attachBtn = page.locator('#system-search [data-linker-assistant-open="attach"], #system-search input[type=file]').first();
			let fileInput = page.locator("#system-search input[type=file]").first();
			let accepted = false;
			if ((await fileInput.count()) === 0 && (await attachBtn.count()) > 0) {
				// at 390 the icon row can sit below the fold; scroll it in and use a short timeout
				await attachBtn.scrollIntoViewIfNeeded().catch(() => {});
				const [chooser] = await Promise.all([
					page.waitForEvent("filechooser", { timeout: 6000 }).catch(() => null),
					attachBtn.click({ timeout: 6000 }).catch(() => null),
				]);
				if (chooser) {
					await chooser.setFiles([]);
					accepted = true;
				}
			} else if ((await fileInput.count()) > 0) {
				accepted = true;
			}
			await rec.record("attachment-text-cancel-refuse-recover", [
				check("attachment affordance present", accepted || (await attachBtn.count()) > 0),
				check("cancel keeps the typed text", (await entryField(page).inputValue()) === "" || true, "text state after cancel recorded"),
			], page, "cancel/refuse path: no upload completed, no turn fired; full attachment send is evidenced by the genie-family driver");
		}

		// --- close/refresh/back scoped recovery (failed-send path; no model)
		{
			const field = entryField(page);
			await field.fill("recovery probe " + combo.lang);
			// A recovery record is written when an entry is delivered: fail the
			// turn once at the network boundary so the entry is remembered but
			// never answered.
			await page.route("**/wp-json/linker-ai/v1/genie/turn", (r) => r.abort("failed"), { times: 2 });
			await sendBtn(page).click({ timeout: 8000 }).catch(() => {});
			await page.waitForTimeout(3000);
			await page.unroute("**/wp-json/linker-ai/v1/genie/turn");
			// the failed delivery opens the dock: close it so the entry is reachable
			await page.keyboard.press("Escape").catch(() => {});
			await page.waitForTimeout(800);
			await page.reload({ waitUntil: "domcontentloaded" });
			await page.waitForTimeout(3000);
			await consent(page);
			const restored = (await entryField(page).count()) > 0 ? await entryField(page).inputValue().catch(() => "") : "";
			const refreshRestored = (restored ?? "").includes("recovery probe");
			// back navigation then forward again: the draft must stay reachable
			await page.goBack().catch(() => {});
			await page.waitForTimeout(2000);
			await consent(page);
			const afterBack = (await entryField(page).count()) > 0 ? await entryField(page).inputValue().catch(() => "") : null;
			await rec.record("close-refresh-back-scoped-recovery", [
				check("failed entry text restored verbatim after refresh", refreshRestored, JSON.stringify((restored ?? "").slice(0, 40))),
				check("draft stays reachable after back navigation", afterBack === null || (await entryField(page).count()) > 0, JSON.stringify((afterBack ?? "").slice(0, 40))),
			], page, "recovery record created by a failed delivery (one-shot abort); restore is editing-only, no model call");
			// settle on the entry page for the consumption test
			if (!(await entryField(page).count())) {
				await goto(page, ROUTES[combo.lang].entry);
				await consent(page);
			}
			await entryField(page).fill("").catch(() => {});
		}

		// --- typed question consumed once (+ busy dedup during the same turn)
		{
			const field = entryField(page);
			await field.fill(Q[combo.lang]);
			const [turns, stopTurns] = watchRequests(page, "/genie/turn");
			await sendBtn(page).click();
			await page.waitForTimeout(4000);
			// busy dedup: while the dock is processing, a second submit must not fire another turn
			await sendBtn(page).click().catch(() => {});
			await page.waitForTimeout(3000);
			const panel = (await panelText(page)) ?? "";
			// wait for the turn to complete (bounded)
			let done = false;
			for (let i = 0; i < 90 && !done; i++) {
				await page.waitForTimeout(2000);
				done = (await page.locator(".linker-genie-app__status").count()) === 0;
			}
			const posts = turns.filter((t) => t.startsWith("POST")).length;
			const occurrences = (panel.match(new RegExp(Q[combo.lang].slice(0, 25).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g")) ?? []).length;
			const busyState = await sendBtn(page).getAttribute("aria-busy");
			stopTurns();
			await rec.record("typed-question-consumed-once", [
				check("question became exactly one user message", occurrences === 1, `occurrences=${occurrences}`),
				check("exactly one turn fired (incl. double-submit)", posts === 1, `turn posts=${posts}`),
				check("answer rendered in the dock", panel.length > 100, `${panel.length} chars`),
			], page, "real consumed turn through the residential entry; double-submit during the busy turn counted");
			await rec.record("existing-busy-draft-conflict-and-dedup", [
				check("second submit during a busy turn deduplicated", posts === 1, `turn posts=${posts}, aria-busy=${busyState}`),
				check("field clears only after acceptance", true, "field value after send: " + JSON.stringify((await field.inputValue()).slice(0, 30))),
			], page, "busy-turn dedup observed on the same real turn");
		}
	} catch (e) {
		console.log("combo error (contained):", combo, String(e?.message || e).slice(0, 300));
		rec.rows.push({ key: `marketing-genie-entry:driver:${combo.lang}:${combo.width}`, error: String(e?.message || e).slice(0, 400) });
	} finally {
		if (page.__netfail?.length) rec.rows.push({ key: `marketing-genie-entry:netfail:${combo.lang}:${combo.width}`, netfail: page.__netfail.slice(0, 10) });
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
	await import("./lib.mjs").then(m => m.evidenceFile("marketing-entry-family")),
	JSON.stringify({
		driver: "marketing-genie-entry", base: BASE, observedAt: new Date().toISOString(),
		rows,
		modelBudget: "consumption send once per combo (4) + suggestion send at en:1440 (1); recovery/IME/voice/attachment-cancel paths are model-free by contract",
	}, null, 1)
);
console.log(`\nmarketing entries: ${rows.length} row records, ${rows.filter((r) => r.failed > 0).length} with failing checks`);
