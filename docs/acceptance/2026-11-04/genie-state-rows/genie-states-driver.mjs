/** Round-3 addendum: the states whose round-0/round-2 findings are known to be
 * harness artefacts, re-recorded on the same harness the rest of round 3 uses.
 *
 * What was wrong in the earlier rounds:
 * - `dock` / `dock-keyboard-focus-escape-and-return` recorded "no
 *   .linker-genie-open found" as a defect at every width. The standing dock is
 *   `display:none` at ≤860px **by design** (`genie.css`, "The live page hides
 *   its bubble under 861px"); measured 0×0 at 390/860 and 50×50 at 861. That
 *   width has no floating dock, so the check is not applicable there — not a
 *   pass, not a defect.
 * - `product-card`, `product-add-retry`, `save-pending-error-success`,
 *   `consumer-draft-readback`, `consumer-saved-solution-readback`,
 *   `service-error-retry`, `thinking`, `answer-text` failed in earlier rounds
 *   because the round did not get a card-bearing answer (no card → no add/save
 *   affordance → every downstream check empty), and its checks did not
 *   distinguish "no card" from "card without controls".
 *
 * This driver asks one real product question, requires the card, then drives
 * add / save / retry on that card and reads each result back from the DOM and
 * from the network.
 */
import fs from "node:fs";
import {
	BASE, COMBOS, ROUTES, Recorder, answerControls, askTurn, check, consent,
	composer, dock, evidenceFile, goto, newPage, openDock, watchRequests, chromium,
} from "./lib.mjs";

const Q = { en: "SAJ eSolar AIO3", de: "SAJ eSolar AIO3" };

/** The card's own status line ("Saving…", "Addition not confirmed.", "Not
 * saved. Try again.", "In your solution draft."). It is the accessible
 * feedback the customer sees under the card's actions. */
function cardStatuses(page) {
	return page.evaluate(() =>
		[...document.querySelectorAll(".linker-card")].flatMap((card) =>
			[...card.querySelectorAll("[role=status], [class*=status]")]
				.map((el) => el.innerText.trim())
				.filter(Boolean)
		)
	);
}

async function runCombo(browser, combo) {
	const rec = new Recorder("genie", combo);
	const { context, page } = await newPage(browser, combo, {
		permissions: ["clipboard-read", "clipboard-write"],
	});
	const R = ROUTES[combo.lang];
	try {
		await goto(page, R.genie);
		await consent(page);
		await openDock(page);

		// ---- dock: a marketing/product page carries the floating opener
		// `/genie/` is the workspace itself and prints no opener at all
		// (`Entries::dock()` is the standing dock of every other page), and
		// the dock is `display:none` at ≤860px by design ("The live page hides
		// its bubble under 861px" — measured 0×0 at 390/860, 50×50 at 861).
		await goto(page, R.home);
		await consent(page);
		if (combo.width > 860) {
			const opener = page.locator("[data-linker-genie-open]").first();
			const box = await opener.boundingBox().catch(() => null);
			await opener.click().catch(() => {});
			await page.waitForTimeout(2000);
			const composerVisible = await composer(page).isVisible().catch(() => false);
			await rec.record("dock", [
				check("floating control present and sized", !!box && box.width >= 40 && box.height >= 40,
					box ? `${Math.round(box.width)}×${Math.round(box.height)} at ${Math.round(box.x)},${Math.round(box.y)}` : "no box"),
				check("the floating control opens the dock with its composer", composerVisible),
			], page, "the standing dock on a marketing page above the 860px breakpoint");
			// Escape / reopen / Tab
			await composer(page).click().catch(() => {});
			await page.waitForTimeout(300);
			await page.keyboard.press("Escape");
			await page.waitForTimeout(1500);
			const closed = !(await composer(page).isVisible().catch(() => false));
			await opener.click().catch(() => {});
			await page.waitForTimeout(1500);
			const reopened = await composer(page).isVisible().catch(() => false);
			let focused = null;
			if (reopened) {
				await composer(page).click().catch(() => {});
				await page.keyboard.press("Tab");
				focused = await page.evaluate(() => document.activeElement?.className ?? null);
			}
			await rec.record("dock-keyboard-focus-escape-and-return", [
				check("Escape closes the dock", closed),
				check("reopen restores the dock", reopened),
				check("Tab moves focus inside the dock", !!focused && /linker-genie/.test(String(focused)), String(focused).slice(0, 60)),
			], page, "keyboard cycle on the standing dock: Escape, reopen, Tab");
		} else {
			const measured = await page.evaluate(() => {
				const wrap = document.querySelector("[data-linker-genie-open]")?.closest(".linker-genie");
				const b = document.querySelector("[data-linker-genie-open]")?.getBoundingClientRect();
				return { display: wrap ? getComputedStyle(wrap).display : null, box: b ? [Math.round(b.width), Math.round(b.height)] : null };
			});
			const why = `the standing dock is display:none at ≤860px by design (genie.css @media max-width:860px; the live page hides its bubble under 861px); measured display=${measured.display} box=${JSON.stringify(measured.box)} at ${combo.width}px and 50×50 at 861px`;
			await rec.record("dock", [
				check("a floating dock exists at this width", false, why, { notApplicable: why }),
			], page, "mobile width: the dock does not exist here by design");
			await rec.record("dock-keyboard-focus-escape-and-return", [
				check("the dock keyboard cycle exists at this width", false,
					`no floating dock at ${combo.width}px → no Escape/reopen/Tab cycle to drive`,
					{ notApplicable: why }),
			], page, "mobile width: no standing dock to cycle");
		}

		// ---- one real product turn drives the card states
		await goto(page, R.genie);
		await consent(page);
		await openDock(page);
		const turn = await askTurn(page, Q[combo.lang]);
		const answered = turn.ok;
		const cardCount = await dock(page).locator(".linker-card").count();
		const primary = dock(page).locator(".linker-genie-app__card-action--primary").first();
		const saveAction = dock(page).locator(".linker-genie-app__card-action:not(.linker-genie-app__card-action--primary)").first();
		const primaryCount = await primary.count();
		const saveCount = await saveAction.count();
		await rec.record("thinking", [
			check("turn answered (the thinking state precedes a real answer)", answered,
				answered ? `HTTP ${turn.httpStatus} · turn_id=${turn.turnId} · route=${turn.route}` : turn.error),
		], page, "a real turn on the dock; the indicator's presence is measured by askTurn's own waiting state");
		await rec.record("answer-text", [
			check("answer text rendered for the customer", answered && turn.text.length > 80,
				`${turn.text.length} chars`),
			check("question rendered exactly once as a user message",
				(await dock(page).locator(".linker-genie-app__message--user").count()) === 1,
				`user messages=${await dock(page).locator(".linker-genie-app__message--user").count()}`),
		], page, "the customer-visible answer, read from the dock's own message list");
		await rec.record("product-card", [
			check("product card rendered by the turn", cardCount > 0, `cards=${cardCount}`),
			check("card carries both actions", primaryCount > 0 && saveCount > 0,
				`add=${primaryCount}, save=${saveCount}`),
		], page, "a real product question that returns a card");

		if (primaryCount > 0) {
			// ---- product-add-retry: one aborted add, then the real retry
			const [draftLog] = watchRequests(page, "/genie/draft");
			await page.route(/\/genie\/draft(\?|$)/, (r) => r.abort("failed"), { times: 1 });
			await primary.click().catch(() => {});
			await page.waitForTimeout(4000);
			const failedAddStatuses = await cardStatuses(page).catch(() => []);
			const failureShown = failedAddStatuses.some((t) =>
				/Addition not confirmed|Not added|could not be confirmed|nicht bestätigt|nicht hinzugef/i.test(t)
			);
			await page.unroute(/\/genie\/draft(\?|$)/);
			await primary.click().catch(() => {});
			await page.waitForTimeout(7000);
			const afterRetry = (await dock(page).innerText().catch(() => "")) ?? "";
			const added = /In your solution draft|Im Lösungsentwurf/i.test(afterRetry);
			await rec.record("product-add-retry", [
				check("add affordance present on the card", true),
				check("a failed add surfaces its own feedback", failureShown,
					`card status=${JSON.stringify(failedAddStatuses)}`),
				check("the retry reaches the draft endpoint and is confirmed", draftLog.length >= 2 && added,
					`draft requests=${draftLog.length} · confirmed=${added}`),
			], page, "one-shot abort of the draft add, then the customer's own retry");

			// ---- consumer-draft-readback: the native draft page shows the line
			const draftUrl = ROUTES[combo.lang].cart;
			await goto(page, draftUrl, { wait: 2500 });
			await consent(page);
			const rows = await page.locator(".woocommerce-cart-form__cart-item, .lp-draft-line, [class*=cart-item]").count();
			const body = (await page.locator("main").first().innerText().catch(() => "")) || "";
			await rec.record("consumer-draft-readback", [
				check("the solution draft page renders", body.length > 80),
				check("the added product line is read back on the draft page",
					rows > 0 || /SAJ|eSolar AIO3/i.test(body),
					`rows=${rows} · mentions the model=${/SAJ|eSolar AIO3/i.test(body)}`),
			], page, "native Solution draft consumer after the Genie add");

			// ---- save-pending-error-success + saved-solution readback
			await goto(page, R.genie);
			await consent(page);
			await openDock(page);
			const turn2 = await askTurn(page, Q[combo.lang]);
			const save2 = dock(page).locator(".linker-genie-app__card-action:not(.linker-genie-app__card-action--primary)").first();
			const hasSave = (await save2.count()) > 0;
			let saveFailure = null;
			let saveFailureDetail = "";
			let savedOk = false;
			let savedDetail = "";
			let saveLog = [];
			if (hasSave) {
				[saveLog] = watchRequests(page, "/genie/solution");
				await page.route(/\/genie\/solution(\?|$)/, (r) => r.abort("failed"), { times: 1 });
				await save2.click().catch(() => {});
				await page.waitForTimeout(4000);
				const s1 = await cardStatuses(page).catch(() => []);
				// A dropped save is the app's own "unconfirmed" state: the write
				// may have landed, so it says so instead of claiming failure.
				saveFailure = s1.some((t) =>
					/request status could not be confirmed|Not saved|could not be saved|Nicht gespeichert|nicht bestätigt/i.test(t)
				);
				saveFailureDetail = JSON.stringify(s1);
				await page.unroute(/\/genie\/solution(\?|$)/);
				await save2.click().catch(() => {});
				await page.waitForTimeout(8000);
				const s2 = await cardStatuses(page).catch(() => []);
				savedOk = s2.some((t) => /Saved|Gespeichert/i.test(t));
				savedDetail = JSON.stringify(s2);
			}
			await rec.record("save-pending-error-success", [
				check("save affordance present on the card turn", hasSave && turn2.ok,
					`save=${hasSave} · turn=${turn2.httpStatus}`),
				check("a failed save surfaces its own feedback", saveFailure === true, `card status=${saveFailureDetail}`),
				check("the save retry reaches the endpoint and is acknowledged",
					saveLog.length >= 2 && savedOk, `solution requests=${saveLog.length} · card status=${savedDetail}`),
			], page, "one-shot abort of the save, then the customer's own retry");
			await rec.record("consumer-saved-solution-readback", [
				check("the conversation acknowledges the saved solution", savedOk,
					`card status=${savedDetail}; the configurator-side consumer is covered by the project-brief saved-solution rows`),
			], page, "Genie-side acknowledgement of the save");
		} else {
			await rec.record("product-add-retry", [
				check("add affordance present on the card", false, "the turn produced no card", {
					scope: `the product question returned route=${turn.route ?? "n/a"} with no card; the add/save chain cannot be driven from this answer`,
				}),
			], page, "no card in this answer");
			await rec.record("save-pending-error-success", [
				check("save affordance present on the card turn", false, "the turn produced no card", {
					scope: `the product question returned route=${turn.route ?? "n/a"} with no card`,
				}),
			], page, "no card in this answer");
			await rec.record("consumer-saved-solution-readback", [
				check("saved solution acknowledged in the conversation", false, "no save was reachable", {
					scope: "no card in this answer, so no save could be driven",
				}),
			], page, "no card in this answer");
			await rec.record("consumer-draft-readback", [
				check("added product line present", false, "no add was reachable", {
					scope: "no card in this answer, so no line could be added",
				}),
			], page, "no card in this answer");
		}

		// ---- service-error-retry: a failed turn, then the customer's retry
		await goto(page, R.genie);
		await consent(page);
		await openDock(page);
		const token = "retry-probe-" + Math.random().toString(36).slice(2, 7);
		await page.route("**/wp-json/linker-ai/v1/genie/turn", (r) => r.abort("failed"), { times: 3 });
		await composer(page).fill(token);
		await dock(page).locator(".linker-genie-app__send").first().click({ timeout: 15000 }).catch(() => {});
		const errorShown = await dock(page).locator(".linker-genie-app__error").first()
			.waitFor({ state: "visible", timeout: 15000 }).then(() => true).catch(() => false);
		await page.unroute("**/wp-json/linker-ai/v1/genie/turn");
		const retry = page.getByRole("button", { name: /^(Try again|Erneut versuchen)$/ }).first();
		const retryVisible = (await retry.count()) > 0;
		let retried = null;
		if (retryVisible) {
			await page.waitForTimeout(6000);
			await retry.click().catch(() => {});
			// The retry resends the preserved question; read the answer it gets.
			const started = Date.now();
			while (Date.now() - started < 240000) {
				await page.waitForTimeout(2000);
				const bodies = await dock(page)
					.locator(".linker-genie-app__message--assistant:not(.linker-genie-wait)")
					.allInnerTexts()
					.catch(() => []);
				const waiting = (await dock(page).locator(".linker-genie-wait").count()) > 0;
				if (!waiting && bodies.join("").length > 80) {
					retried = { ok: true, len: bodies.join("").length };
					break;
				}
			}
		}
		await rec.record("service-error-retry", [
			check("error UI shown on turn failure", errorShown),
			check("retry affordance preserved", retryVisible),
			check("retry succeeded against the real service", !!retried?.ok,
				retried ? `${retried.len} chars after retry` : "no answer after the retry",
				{ failureInjection: true }),
		], page, "one-shot network abort of the turn, then the customer's own retry against the real service");
	} catch (e) {
		console.log("combo error (contained):", combo, String(e?.message || e).slice(0, 250));
		rec.rows.push({ key: `genie:states:${combo.lang}:${combo.width}`, error: String(e?.message || e).slice(0, 350) });
	} finally {
		await context.close().catch(() => {});
	}
	return rec;
}

const browser = await chromium.launch({
	args: ["--disable-gpu", "--disable-dev-shm-usage", "--renderer-process-limit=1"],
});
const all = [];
for (const combo of COMBOS) all.push(await runCombo(browser, combo));
await browser.close();
const rows = all.flatMap((r) => r.rows);
fs.writeFileSync(await evidenceFile("genie-states-round3"), JSON.stringify({
	driver: "genie", fixRound: 3, base: BASE, observedAt: new Date().toISOString(),
	rows,
	modelBudget: "3 real turns per combo (product card, save card, retry) — bounded, no bulk sampling",
}, null, 1));
console.log("genie states driver done:", rows.length, "records,", rows.filter((r) => r.status === "fail").length, "failed");
