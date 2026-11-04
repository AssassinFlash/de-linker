/** Genie-family fix driver (2026-11-04 second round, corrected harness).
 *
 * What the first fix round got wrong, and what this driver does instead:
 *
 * 1. `copy-and-rating` recorded `turn succeeded` as a hard-coded pass, so a
 *    turn that ended in "Genie did not answer" still counted as success and
 *    its missing controls were reported as a documents-route UI gap. Every
 *    answer check here is gated on one real turn: proxy 2xx, a `turn_id` in
 *    the meta (the row's own gate for the thumbs — `VoteButtons` returns null
 *    without it), and assistant text the customer can read. A failed turn is
 *    recorded as a failed check carrying the app's own error text.
 * 2. `ordinary-draft-failure-owner-isolation` targeted the first
 *    `[data-genie-owned-recovery]` in the DOM. On a page carrying the home
 *    hero that is the *hero* instance's panel, so the dock composer stayed
 *    empty and the state was blamed for not restoring. All reads/writes here
 *    are scoped to `#linker-genie-mount`, and the restore is verified by
 *    reading the composer back and by a second reload.
 * 3. `cross-surface-entry-question-consumed` compared against the panel text
 *    before the hero's own conversation had painted. It now waits for the
 *    hero conversation's answer and counts the question there.
 */
import fs from "node:fs";
import {
	BASE, COMBOS, ROUTES, Recorder, answerControls, askTurn,
	check, consent, composer, dock, evidenceFile, goto, newPage, openDock,
	visible, watchRequests, chromium,
} from "./lib.mjs";

const Q = {
	en: {
		doc: "What usable capacity and power does the GoodWe Lynx Home F 10-16 battery have? Quote the datasheet numbers.",
		product: "SAJ eSolar AIO3",
		hero: "Which storage does Linker sell for a small home?",
	},
	de: {
		doc: "Welche Nutzkapazität und Leistung hat der GoodWe Lynx Home F 10-16? Nenne die Zahlen aus dem Datenblatt.",
		product: "SAJ eSolar AIO3",
		hero: "Welchen Speicher verkauft Linker für ein kleines Haus?",
	},
};
const restoreLabel = (lang) =>
	lang === "en" ? "Restore unsent draft" : "Bisherigen Entwurf wiederherstellen";

/** Turn check used by both routes: the answer exists as customer-visible text. */
function turnChecks(label, turn) {
	return [
		check(
			`${label}: real model turn answered (2xx + turn_id + answer text)`,
			turn.ok,
			turn.ok
				? `HTTP ${turn.httpStatus} · turn_id=${turn.turnId} · route=${turn.route ?? "n/a"} · ${turn.text.length} chars${turn.retried ? " · answered on the customer's own retry" : ""}`
				: `HTTP ${turn.httpStatus ?? "none"} · ${turn.error}`
		),
	];
}

/** One bounded retry, on the app's own "Try again" path.
 *
 * A 5xx here is the proxy reporting an upstream failure (the message the
 * customer sees is "Genie did not answer"), not the behaviour this row is
 * about. A real customer presses Try again, so the harness does the same —
 * once. The retry is named in the check detail, and a second failure stays a
 * failure. Nothing is retried on a 2xx answer. */
async function askWithRetry(page, question) {
	const first = await askTurn(page, question);
	if (first.ok || !(first.httpStatus >= 500)) return first;
	await page.waitForTimeout(10000);
	const retry = page.getByRole("button", { name: /^(Try again|Erneut versuchen)$/ }).first();
	if ((await retry.count()) > 0) {
		await retry.click().catch(() => {});
	} else {
		await composer(page).fill(question).catch(() => {});
		await dock(page).locator(".linker-genie-app__send").first().click().catch(() => {});
	}
	const second = await askTurn(page, question);
	return { ...second, retried: second.ok, firstAttempt: first.httpStatus };
}

/** Copy + thumbs on the answer that the last turn just produced. */
async function copyVoteChecks(page, label, turn) {
	const { votes, copy } = answerControls(page);
	let voteCount = 0;
	for (let i = 0; i < 12 && voteCount < 2; i++) {
		voteCount = await votes.count();
		if (voteCount < 2) await page.waitForTimeout(1000);
	}
	const copyCount = await copy.count();
	let clipboard = "";
	if (copyCount) {
		await copy.first().click().catch(() => {});
		await page.waitForTimeout(700);
		clipboard = await page
			.evaluate(() => navigator.clipboard.readText().catch(() => ""))
			.catch(() => "");
	}
	const norm = (s) =>
		s
			// The clipboard carries the answer's markdown source (`### Title`,
			// `**bold**`); the message element shows it rendered. Compare the two
			// on the same footing by dropping the syntax markers first.
			.replace(/^#{1,6}\s+/gm, "")
			.replace(/\*\*|__/g, "")
			.replace(/\s+/g, " ")
			.trim();
	const clip = norm(clipboard);
	const messageText = norm(turn.answer || turn.text);
	// The copied text is the answer's own prose. On a products turn the message
	// element also renders cards, so the clipboard is a verbatim part of the
	// message rather than its whole text — the assertion is that containment.
	const probe = clip.slice(0, 60);
	const clipMatches = clip.length > 30 && probe.length > 30 && messageText.includes(probe);

	// The vote POST is the customer-visible effect: the thumb must stay pressed.
	const [voteLog, stopVotes] = watchRequests(page, "/vote");
	let votePressed = false;
	let voteStatus = null;
	const onVoteResponse = (r) => {
		if (r.url().includes("/vote")) voteStatus = r.status();
	};
	page.on("response", onVoteResponse);
	const helpful = votes.first();
	if (voteCount) {
		await helpful.click().catch(() => {});
		await page.waitForTimeout(1200);
		votePressed = (await helpful.getAttribute("aria-pressed").catch(() => null)) === "true";
	}
	page.off("response", onVoteResponse);
	stopVotes();

	return [
		...turnChecks(label, turn),
		check(`${label}: copy + both thumbs rendered on the answer`, copyCount > 0 && voteCount >= 2,
			`copy buttons=${copyCount}, thumbs=${voteCount}`),
		check(`${label}: copy puts the answer on the clipboard`, clipMatches,
			`clipboard ${clipboard.length} chars · ${JSON.stringify(clip.slice(0, 40))} · contained in the answer=${clipMatches}`),
		check(`${label}: thumbs post the vote and stay pressed`, votePressed && /^2\d\d$/.test(String(voteStatus)),
			`POST ${voteLog.length} · HTTP ${voteStatus}`),
	];
}

async function runCombo(browser, combo) {
	const rec = new Recorder("genie", combo);
	const { context, page } = await newPage(browser, combo, {
		permissions: ["clipboard-read", "clipboard-write"],
	});
	const R = ROUTES[combo.lang];
	const T = { restore: restoreLabel(combo.lang) };
	try {
		await goto(page, R.genie);
		await consent(page);
		await openDock(page);

		// ---- copy/vote on two routable answers, each on its own real turn
		try {
			const docTurn = await askWithRetry(page, Q[combo.lang].doc);
			const docChecks = await copyVoteChecks(page, "documents-routed (datasheet question)", docTurn);
			const prodTurn = await askWithRetry(page, Q[combo.lang].product);
			const prodChecks = await copyVoteChecks(page, "product-routed (bare model query)", prodTurn);
			await rec.record("copy-and-rating", [...docChecks, ...prodChecks], page,
				`copy + vote checked on each route's own answer; the thumb controls only exist on an answered turn (VoteButtons needs the meta turn_id), so a failed turn is recorded as a failed turn, never as a missing control or a route gap (route=${docTurn.route ?? "n/a"}/${prodTurn.route ?? "n/a"})`);
		} catch (e) {
			console.log("copy-and-rating phase error:", String(e?.message || e).slice(0, 200));
			rec.rows.push({ key: `genie:copy-and-rating:${combo.lang}:${combo.width}`, error: String(e?.message || e).slice(0, 300) });
		}

		// ---- ordinary draft failure + explicit recovery, dock-scoped
		// The dock is the surface this state is about, and /genie/ mounts the
		// dock alone. The home page also mounts the hero cinematic, which this
		// host cannot keep alive next to a reload cycle.
		try {
			await goto(page, R.genie);
			await consent(page);
			await openDock(page);
			const draft = "owner-isolation-probe " + Math.random().toString(36).slice(2, 8);
			await page.route("**/wp-json/linker-ai/v1/genie/turn", (r) => r.abort("failed"), { times: 3 });
			await composer(page).fill(draft);
			await dock(page).locator(".linker-genie-app__send").first().click({ timeout: 15000 }).catch(() => {});
			const errorShown = await visible(page, "#linker-genie-mount .linker-genie-app__error", 12000);
			const preserved = ((await composer(page).inputValue().catch(() => "")) ?? "").includes(draft.slice(0, 12));
			await page.unroute("**/wp-json/linker-ai/v1/genie/turn");

			await page.reload({ waitUntil: "domcontentloaded" });
			await page.waitForTimeout(3000);
			await consent(page);
			await openDock(page);
			const panel = page.locator("#linker-genie-mount [data-genie-owned-recovery]").first();
			const panelVisible = await panel
				.waitFor({ state: "visible", timeout: 20000 })
				.then(() => true)
				.catch(() => false);
			const panelText = panelVisible ? ((await panel.innerText()) ?? "") : "";
			let restored = false;
			if (panelVisible) {
				await panel.locator("button").first().click().catch(() => {});
				for (let i = 0; i < 40; i++) {
					await page.waitForTimeout(500);
					const value = await composer(page).inputValue().catch(() => "");
					if (value.includes(draft.slice(0, 12))) {
						restored = true;
						break;
					}
				}
			}
			// A restored draft must survive the surface going away again: reload
			// and read the composer (or the panel that offers it) once more.
			let persisted = false;
			if (restored) {
				await page.reload({ waitUntil: "domcontentloaded" });
				await page.waitForTimeout(3000);
				await consent(page);
				await openDock(page);
				const value = await composer(page).inputValue().catch(() => "");
				const panelAgain = page.locator("#linker-genie-mount [data-genie-owned-recovery]").first();
				const offeredAgain =
					(await panelAgain.count()) > 0 &&
					((await panelAgain.innerText().catch(() => "")) ?? "").includes(draft.slice(0, 12));
				persisted = value.includes(draft.slice(0, 12)) || offeredAgain;
			}

			// Ownership: a second guest on the same page must not be offered it.
			// A second guest on a lighter surface: the dock page carries no hero
			// instance, and the ownership question is the guest's own scope, not
			// the page. (Two hero-bearing contexts at once exhausts this host.)
			const { context: ctx2, page: page2 } = await newPage(browser, combo);
			await goto(page2, R.genie);
			await consent(page2);
			await openDock(page2);
			const foreignPanel = await page2.locator("#linker-genie-mount [data-genie-owned-recovery]").count();
			const foreignValue = (await composer(page2).inputValue().catch(() => "")) ?? "";
			await ctx2.close();

			await rec.record("ordinary-draft-failure-owner-isolation", [
				check("failed send shows the app's error UI", errorShown),
				check("draft text preserved in the composer after the failure", preserved),
				check("owned-recovery panel offered after reload", panelVisible, panelText.replace(/\n+/g, " · ").slice(0, 80)),
				check("panel shows the draft owner's text", panelText.includes(draft.slice(0, 12))),
				check("Restore unsent draft puts the text back in the composer", restored),
				check("restored draft persists across a further reload", persisted),
				check("a different guest is offered no recovery and no text", foreignPanel === 0 && !foreignValue.includes("owner-isolation-probe"),
					`panels=${foreignPanel} value=${JSON.stringify(foreignValue.slice(0, 30))}`),
			], page, "failure injected ×3 at the network boundary on /genie/ (the dock's own page); every read is scoped to #linker-genie-mount, and the home page's hero instance is checked separately by the hero rows");
		} catch (e) {
			console.log("draft-failure phase error:", String(e?.message || e).slice(0, 200));
			rec.rows.push({ key: `genie:ordinary-draft-failure-owner-isolation:${combo.lang}:${combo.width}`, error: String(e?.message || e).slice(0, 300) });
		}

		// ---- home hero + cross-surface, measured on the hero's own conversation
		if (combo.lang === "en" && combo.width === 1440) {
			await goto(page, R.home);
			await consent(page);
			const heroReady = await visible(page, '.hero-cinematic[data-linker-genie-hero="ready"]', 20000);
			const heroInput = page.locator(".hero-prompt").first();
			const heroSurface = page.locator(".linker-genie-hero__surface").first();
			let typed = heroReady && (await heroInput.count()) > 0;
			let answerText = "";
			let turns = 0;
			let occurrences = 0;
			if (typed) {
				const [turnLog, stop] = watchRequests(page, "/genie/turn");
				await heroInput.fill(Q.en.hero);
				await page.keyboard.press("Enter");
				const started = Date.now();
				while (Date.now() - started < 240000) {
					await page.waitForTimeout(2000);
					const bodies = await heroSurface
						.locator(".linker-genie-app__message--assistant:not(.linker-genie-wait)")
						.allInnerTexts()
						.catch(() => []);
					const waiting = (await heroSurface.locator(".linker-genie-wait").count()) > 0;
					const joined = bodies.join("\n");
					if (!waiting && joined.length > 80) {
						answerText = joined;
						break;
					}
				}
				stop();
				turns = turnLog.filter((t) => t.startsWith("POST")).length;
				// The question is consumed when it stands as exactly one user
				// message. Counting it in the answer text would count the model
				// quoting it back, which is not what the state means.
				const userMessages = await heroSurface
					.locator(".linker-genie-app__message--user")
					.allInnerTexts()
					.catch(() => []);
				const question = Q.en.hero.trim();
				occurrences = userMessages.filter((m) => m.replace(/\s+/g, " ").trim() === question.replace(/\s+/g, " ")).length;
				// The hero conversation may already hold earlier turns from this
				// session; the state is that *this* question became a message once.
				const asked = occurrences >= 1;
				await rec.record("cross-surface-entry-question-consumed", [
					check("question became a message in the hero conversation", asked),
					check("question appears exactly once in the conversation", occurrences === 1, `occurrences=${occurrences}`),
					check("exactly one turn request fired", turns === 1, `turns=${turns}`),
					check("the hero conversation shows the answer", answerText.length > 80, `${answerText.length} chars`),
				], page, "home hero → in-place conversation, read on the hero's own instance");
				await rec.record("home-hero", [
					check("hero reaches its ready state", heroReady),
					check("hero input accepts text", typed),
					check("hero conversation answers the question", answerText.length > 80, `${answerText.length} chars`),
				], page, "home hero entry surface; the un-interacted pixel-gate area untouched");
			}
		}
	} catch (e) {
		console.log("combo error (contained):", combo, String(e?.message || e).slice(0, 250));
		rec.rows.push({ key: `genie:fixdriver:${combo.lang}:${combo.width}`, error: String(e?.message || e).slice(0, 350) });
	} finally {
		await context.close().catch(() => {});
	}
	return rec;
}

// This host is under memory pressure (free pages in the low hundreds of MB,
// swap mostly used), and Chromium gets reclaimed mid-run when several pages
// and a hero cinematic are alive at once. One browser, one argument set, and
// a fresh page per phase keep the run inside that budget.
const browser = await chromium.launch({
	args: ["--disable-gpu", "--disable-dev-shm-usage", "--renderer-process-limit=1"],
});
const all = [];
for (const combo of COMBOS) all.push(await runCombo(browser, combo));
await browser.close();
const rows = all.flatMap((r) => r.rows);
fs.writeFileSync(await evidenceFile("genie-family-fix"), JSON.stringify({
	driver: "genie", fixRound: 3, base: BASE, observedAt: new Date().toISOString(),
	rows,
	modelBudget: "2 real turns per combo (documents + product) + 1 hero turn at en:1440; failed turns recorded verbatim, never counted as success",
}, null, 1));
console.log("genie fix driver done:", rows.length, "records,", rows.filter((r) => r.status === "fail").length, "failed");
