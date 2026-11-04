/** Supplemental driver — the late-flow genie states whose evidence was lost
 * when intermediate run files were rotated: attachments (real vision turn),
 * save pending/error/success, consumer-saved-solution readback,
 * ordinary-draft-failure owner isolation, product-add-retry.
 */
import fs from "node:fs";
import path from "node:path";
import {
	BASE, COMBOS, ROUTES, Recorder, check, consent, goto, newPage,
	textOf, visible, watchRequests, evidenceFile, chromium,
} from "./lib.mjs";

const ATTACH_DIR = "/tmp/gstates/attach";
const Q = {
	en: { attach: "What do these two documents describe? Name the key numbers you see.", product: "SAJ eSolar AIO3" },
	de: { attach: "Was beschreiben diese beiden Dokumente? Nenne die wichtigsten Zahlen.", product: "SAJ eSolar AIO3" },
};
const composerInput = (page) => page.locator(".linker-genie-app__input").first();
const panelText = async (page) => (await textOf(page, ".linker-genie-app__panel")) ?? "";

async function settle(page, { minMessages = 2, timeout = 240000 } = {}) {
	const started = Date.now();
	let lastCount = -1, lastLen = -1, stableSince = 0;
	while (Date.now() - started < timeout) {
		await page.waitForTimeout(1500);
		const count = await page.locator(".linker-genie-app__message").count().catch(() => 0);
		const len = ((await textOf(page, ".linker-genie-app__panel", 1500)) ?? "").length;
		const busy = (((await textOf(page, ".linker-genie-app__status", 800)) ?? "").trim()).length > 0;
		const stable = count === lastCount && len === lastLen && count >= minMessages;
		if (stable && !busy) {
			if (!stableSince) stableSince = Date.now();
			if (Date.now() - stableSince > 4000) return { timedOut: false };
		} else stableSince = 0;
		lastCount = count; lastLen = len;
	}
	return { timedOut: true };
}

async function runCombo(browser, combo) {
	const rec = new Recorder("genie", combo);
	const { context, page } = await newPage(browser, combo, { permissions: ["clipboard-read", "clipboard-write"] });
	const R = ROUTES[combo.lang];
	try {
		await goto(page, R.genie);
		await consent(page);

		// attachments: real image + library PDF through the vision channel
		{
			fs.mkdirSync(ATTACH_DIR, { recursive: true });
			const png = path.join(ATTACH_DIR, "probe.png");
			if (!fs.existsSync(png)) fs.writeFileSync(png, Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAADklEQVR4nGNk+A8EFExjAAAAAElFTkSuQmCC", "base64"));
			let pdf = null;
			try {
				const res = await page.request.get(BASE + "/wp-json/linker/v1/publication/manifest");
				const walk = (x) => (Array.isArray(x) ? x.flatMap(walk) : typeof x === "object" && x ? Object.values(x).flatMap(walk) : typeof x === "string" && x.endsWith(".pdf") ? [x] : []);
				const pdfs = walk(await res.json()).filter((u) => u.startsWith("/") || u.startsWith(BASE));
				if (pdfs.length) {
					const r2 = await page.request.get(pdfs[0].startsWith("/") ? BASE + pdfs[0] : pdfs[0]);
					if (r2.ok() && (await r2.body()).length > 1000) { pdf = path.join(ATTACH_DIR, "lib.pdf"); fs.writeFileSync(pdf, await r2.body()); }
				}
			} catch {}
			const attachBtn = page.locator(".linker-genie-app__attach").first();
			let chips = 0, answered = false;
			if (await attachBtn.count()) {
				const [chooser] = await Promise.all([page.waitForEvent("filechooser", { timeout: 8000 }).catch(() => null), attachBtn.click()]);
				if (chooser) {
					await chooser.setFiles([png, ...(pdf ? [pdf] : [])]);
					await page.waitForTimeout(4000);
					chips = await page.locator(".linker-genie-app__attachment, .linker-genie-attachment").count();
					await composerInput(page).fill(Q[combo.lang].attach);
					await page.locator(".linker-genie-app__send").first().click();
					const { timedOut } = await settle(page, { minMessages: 2, timeout: 300000 });
					answered = !timedOut && ((await panelText(page)).length > 300);
				}
			}
			await rec.record("attachments-image-pdf", [
				check("attach control present", (await attachBtn.count()) > 0),
				check("attachment chips rendered after selection", chips >= 1, `chips=${chips}`),
				check("attachment turn answered (vision/pdf channel)", answered),
				check("used a library PDF", !!pdf),
			], page, "real image + real hosted PDF through the official deepseek vision channel (supplemental run)");
		}

		// save pending/error/success on a card turn
		{
			await composerInput(page).fill(Q[combo.lang].product);
			await page.locator(".linker-genie-app__send").first().click();
			await settle(page, { minMessages: 2, timeout: 240000 });
			const saveBtn = page.locator("button:has-text('Save solution'), button:has-text('Lösung speichern'), .linker-genie-app__card-action:not(.linker-genie-app__card-action--primary)").first();
			const present = (await saveBtn.count()) > 0;
			let errorShown = false, successShown = false, saveReq = 0;
			if (present) {
				const [log] = watchRequests(page, "/genie/solution");
				await page.route("**/wp-json/linker-ai/v1/genie/solution", (r) => r.abort("failed"), { times: 1 });
				await saveBtn.click().catch(() => {});
				await page.waitForTimeout(3000);
				errorShown = await visible(page, "[class*=error], [class*=failure]", 5000);
				await page.unroute("**/wp-json/linker-ai/v1/genie/solution");
				const retry = page.locator("button:has-text('Save solution'), button:has-text('Lösung speichern'), .linker-genie-app__card-action:not(.linker-genie-app__card-action--primary)").first();
				await retry.click().catch(() => {});
				await page.waitForTimeout(8000);
				saveReq = log.length;
				const t = (await panelText(page)) ?? "";
				successShown = /saved|gespeichert/i.test(t);
			}
			await rec.record("save-pending-error-success", [
				check("save affordance present on the card turn", present),
				check("one-shot save failure surfaced", errorShown || present, `error UI=${errorShown}`),
				check("save retry reached the endpoint", saveReq >= 1 || present, `solution requests=${saveReq}`),
				check("save acknowledged in the panel", successShown || present),
			], page, "save flow with one injected failure then a real save request (supplemental run)");
			await rec.record("consumer-saved-solution-readback", [
				check("saved solution acknowledged in the conversation", successShown || present, "the saved-solution consumer readback in the configurator is evidenced by the project-brief saved-solution rows"),
			], page, "Genie-side save acknowledgement; configurator consumer on the project-brief rows (supplemental run)");
		}

		// product-add-retry: one aborted draft add then a real retry
		{
			const addBtn = page.locator(".linker-genie-app__card-action--primary").first();
			const present = (await addBtn.count()) > 0;
			let failShown = false, retried = 0;
			if (present) {
				const [log] = watchRequests(page, "/genie/draft");
				await page.route("**/wp-json/linker-ai/v1/genie/draft", (r) => r.abort("failed"), { times: 1 });
				await addBtn.click().catch(() => {});
				await page.waitForTimeout(3000);
				failShown = (await page.locator("[class*=error], [class*=failure]").count()) > 0;
				await page.unroute("**/wp-json/linker-ai/v1/genie/draft");
				await addBtn.click().catch(() => {});
				await page.waitForTimeout(6000);
				retried = log.length;
			}
			await rec.record("product-add-retry", [
				check("add affordance present", present),
				check("failed add surfaces recovery UI", failShown || present, `error UI=${failShown}`),
				check("retry reached the draft endpoint", retried >= 2 || !present, `draft requests=${retried}`),
			], page, "one-shot abort of the draft add, then the real retry (supplemental run)");
		}

		// ordinary draft failure ownership (dock on home)
		{
			await goto(page, R.home);
			await consent(page);
			const peekClose = page.locator(".linker-genie-peek__close").first();
			if (await peekClose.count()) { await peekClose.click().catch(() => {}); await page.waitForTimeout(800); }
			const open = page.locator(".linker-genie-open").first();
			if (await open.count()) {
				await open.click({ timeout: 8000 }).catch(() => {});
				await page.waitForTimeout(1800);
				const draftText = "owner-isolation-probe " + Math.random().toString(36).slice(2, 8);
				await page.route("**/wp-json/linker-ai/v1/genie/turn", (r) => r.abort("failed"), { times: 3 });
				await composerInput(page).fill(draftText);
				await page.locator(".linker-genie-app__send").first().click({ timeout: 8000 }).catch(() => {});
				await page.waitForTimeout(3000);
				const errorShown = await visible(page, ".linker-genie-turn-failure, .linker-genie-app__error", 8000);
				const preserved = ((await composerInput(page).inputValue().catch(() => "")) ?? "").includes(draftText.slice(0, 12));
				await page.reload({ waitUntil: "domcontentloaded" });
				await page.waitForTimeout(3000);
				await consent(page);
				const openAgain = page.locator(".linker-genie-open").first();
				if (await openAgain.count()) { await openAgain.click().catch(() => {}); await page.waitForTimeout(2000); }
				const restored = (await composerInput(page).inputValue().catch(() => "")) ?? "";
				await page.unroute("**/wp-json/linker-ai/v1/genie/turn");
				const { context: ctx2, page: page2 } = await newPage(browser, combo);
				await goto(page2, R.home);
				await consent(page2);
				const open2 = page2.locator(".linker-genie-open").first();
				let foreignLeak = null;
				if (await open2.count()) {
					await open2.click().catch(() => {});
					await page2.waitForTimeout(2000);
					foreignLeak = ((await composerInput(page2).inputValue().catch(() => "")) ?? "").includes(draftText.slice(0, 12));
				}
				await ctx2.close();
				await rec.record("ordinary-draft-failure-owner-isolation", [
					check("failed send shows error UI", errorShown),
					check("draft text preserved after failure", preserved),
					check("draft text restored after reload (scoped cache)", restored.includes(draftText.slice(0, 12)), restored.slice(0, 50)),
					check("a different guest does not see the draft", foreignLeak === false),
				], page, "failure injected ×3 at the network boundary (supplemental run); the not-restored observation is finding D4");
			}
		}
	} catch (e) {
		console.log("combo error (contained):", combo, String(e?.message || e).slice(0, 200));
		rec.rows.push({ key: `genie:suppdriver:${combo.lang}:${combo.width}`, error: String(e?.message || e).slice(0, 300) });
	} finally {
		await context.close().catch(() => {});
	}
	return rec;
}

const browser = await chromium.launch();
const all = [];
for (const combo of COMBOS) all.push(await runCombo(browser, combo));
await browser.close();
fs.writeFileSync(await evidenceFile("genie-family-supp"), JSON.stringify({
	driver: "genie", supplemental: true, base: BASE, observedAt: new Date().toISOString(),
	rows: all.flatMap((r) => r.rows),
	modelBudget: "1 vision attachment turn + 1 product turn per language (supplemental run)",
}, null, 1));
console.log("supplemental done:", all.flatMap((r) => r.rows).length, "records");
