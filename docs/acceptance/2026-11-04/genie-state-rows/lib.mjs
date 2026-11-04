/** Shared runner for the 2026-11-04 genie/configurator state-row batch.
 *
 * Drives the isolated local instance `geniestates` (production snapshot
 * 20261104-1914, real engine + Genie services started by `just serve`) at
 * the four matrix combos (en/de × 1440/390). Real model turns are sent
 * through the browser's own WP proxy endpoints; failure states are injected
 * only at the network boundary (one-shot route abort) and are labelled as
 * such in each check's scope.
 */
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(
	"/Users/chesterjohn/Documents/de-linker/tests/e2e/package.json"
);
export const { chromium } = require("playwright");

export const BASE = process.env.GSTATES_BASE ?? "http://127.0.0.1:8916";
export const HERE = path.dirname(new URL(import.meta.url).pathname);
export const COMBOS = (
	process.env.GSTATES_ONLY
		? process.env.GSTATES_ONLY.split(",").map((s) => {
				const [lang, width] = s.split(":");
				return { lang, width: Number(width) };
			})
		: [
				{ lang: "en", width: 1440 },
				{ lang: "en", width: 390 },
				{ lang: "de", width: 1440 },
				{ lang: "de", width: 390 },
			]
);
export const ROUTES = {
	en: {
		home: "/", genie: "/genie/", cart: "/cart/",
		pdp: "/product/saj-ats1-t63-a/",
		entry: "/solution/residential-storage/",
		conf: "/solution-configurator/",
	},
	de: {
		home: "/de/", genie: "/de/genie/", cart: "/de/loesungsentwurf/",
		pdp: "/de/produkt/goodwe-gw60k-sts-g10/",
		entry: "/de/loesung/heimspeicher/",
		conf: "/de/loesungskonfigurator/",
	},
};

export async function newPage(browser, { lang, width }, extra = {}) {
	const context = await browser.newContext({
		viewport: { width, height: width === 390 ? 844 : 1000 },
		locale: lang === "de" ? "de-DE" : "en-US",
		// The 390 combos are the app's touch branch: without a mobile identity
		// and touch input, media-query touch paths stay unexercised.
		...(width === 390 ? { isMobile: true, hasTouch: true } : {}),
		...extra,
	});
	await context.addInitScript(() => {
		window.__gstatesConsole = [];
		for (const kind of ["error", "pageerror"]) {
			window.addEventListener("error", (e) =>
				window.__gstatesConsole.push(kind + ": " + String(e?.message || e).slice(0, 300))
			);
		}
	});
	const page = await context.newPage();
	page.on("crash", () => console.log("PAGE CRASH", JSON.stringify({ lang, width })));
	page.on("close", () => console.log("PAGE CLOSE", JSON.stringify({ lang, width })));
	const netfail = [];
	page.on("requestfailed", (r) => {
		if (!r.url().startsWith(BASE)) return;
		if (r.url().includes("admin-ajax")) return;
		netfail.push(r.method() + " " + r.url().replace(BASE, "") + " :: " + (r.failure()?.errorText ?? ""));
	});
	page.__netfail = netfail;
	return { context, page };
}

export async function consent(page) {
	const reject = page.locator('[data-cky-tag="reject-button"]:visible');
	if ((await reject.count()) > 0) {
		await reject.first().click().catch(() => {});
		await page.waitForTimeout(400);
		return "rejected";
	}
	return "not-shown";
}

export async function goto(page, route, { wait = 2500, ...opts } = {}) {
	await page.goto(BASE + route, { waitUntil: "domcontentloaded", timeout: 60000, ...opts });
	await page.waitForTimeout(wait);
}

export async function visible(page, selector, timeout = 8000) {
	try {
		await page.locator(selector).first().waitFor({ state: "visible", timeout });
		return true;
	} catch {
		return false;
	}
}

export async function textOf(page, selector, timeout = 8000) {
	try {
		return (await page.locator(selector).first().innerText({ timeout })).trim();
	} catch {
		return null;
	}
}

export class Recorder {
	constructor(driver, combo) {
		this.driver = driver;
		this.combo = combo;
		this.rows = [];
		this.shots = 0;
	}
	async record(state, checks, page, scope, extra = {}) {
		const key = `${this.driver}:${state}:${this.combo.lang}:${this.combo.width}`;
		const stem = key.replace(/[^a-zA-Z0-9_.:-]/g, "_");
		let screenshot = null;
		if (page) {
			const shot = path.join(HERE, "screenshots", `${stem}.png`);
			try {
				await page.screenshot({ path: shot });
				screenshot = `docs/acceptance/2026-11-04/genie-state-rows/screenshots/${stem}.png`;
				this.shots++;
			} catch {}
		}
		const failed = checks.filter((c) => c.result === "fail");
		const passed = checks.filter((c) => c.result === "pass");
		this.rows.push({
			key, driver: this.driver, state,
			lang: this.combo.lang, width: this.combo.width,
			url: page ? page.url().replace(BASE, "") : null,
			observedAt: new Date().toISOString(),
			checks, passed: passed.length, failed: failed.length,
			status: failed.length ? "fail" : "observed",
			screenshot, scope, ...extra,
		});
		console.log(
			`${failed.length ? "FAIL" : "ok  "} ${key} (${passed.length} pass/${failed.length} fail)`
		);
	}
	async flush(file) {
		const out = path.join(HERE, "evidence", file);
		fs.writeFileSync(out, JSON.stringify({ driver: this.driver, base: BASE, observedAt: new Date().toISOString(), rows: this.rows }, null, 1));
		console.log(`wrote ${out} (${this.rows.length} rows, ${this.shots} shots)`);
	}
}

/**
 * One recorded check.
 *
 * A check is a pass or a fail. The only third result is a *declared* scope
 * limit, which the caller must name explicitly — `{ scope: "<why this half is
 * not exercisable>" }` — so a harness that cannot reach a state can never be
 * mistaken for a product that works. `{ notApplicable: "<why this state does
 * not exist here>" }` records a state the product does not have at this
 * width/capability; it is not a pass and not a failure. Nothing is
 * reclassified by state name.
 */
export function check(name, ok, detail = null, opts = {}) {
	const options = opts === true ? { failureInjection: true } : opts ?? {};
	const scope = !ok && typeof options.scope === "string" ? options.scope : null;
	const notApplicable =
		!ok && typeof options.notApplicable === "string" ? options.notApplicable : null;
	return {
		name,
		result: ok ? "pass" : notApplicable ? "not-applicable" : scope ? "scope" : "fail",
		detail,
		...(scope ? { scopeReason: scope } : {}),
		...(notApplicable ? { notApplicableReason: notApplicable } : {}),
		...(options.failureInjection ? { failureInjection: "one-shot network abort" } : {}),
	};
}

export async function localeOf(page) {
	return page.evaluate(() => document.documentElement.lang || null);
}

export function evidenceFile(base) {
	const only = process.env.GSTATES_ONLY ? "-" + process.env.GSTATES_ONLY.replace(/[:]/g, "-") : "";
	return path.join(HERE, "evidence", `${base}${only}.json`);
}

/** Watch genie proxy requests; returns [tally, stop]. */
export function watchRequests(page, pattern) {
	const seen = [];
	const on = (r) => {
		if (r.url().includes(pattern)) seen.push(r.method() + " " + r.url().replace(BASE, "").slice(0, 120));
	};
	page.on("request", on);
	return [
		seen,
		() => page.off("request", on),
	];
}

// --- real-turn harness -------------------------------------------------------
// The genie app renders two instances on pages that carry the home hero
// (`#linker-genie-mount` dock, `.linker-genie-hero__surface` hero). Every
// read/write below is scoped to one instance: the dock on `/genie/`, the dock
// in the dock combos, and the hero only where the hero itself is the state.

export const dock = (page) => page.locator("#linker-genie-mount").first();
export const composer = (page) => dock(page).locator(".linker-genie-app__input").first();
export const sendButton = (page) => dock(page).locator(".linker-genie-app__send").first();

/** Answers of this instance, excluding the "thinking" placeholder. */
export function assistantBodies(page) {
	return dock(page)
		.locator(".linker-genie-app__message--assistant:not(.linker-genie-wait)")
		.allInnerTexts()
		.catch(() => []);
}

export function appErrors(page) {
	return dock(page).locator(".linker-genie-app__error").allInnerTexts().catch(() => []);
}

/** Open the dock from a marketing page (peek card closed first). */
export async function openDock(page) {
	const peekClose = page.locator("[data-linker-genie-peek-close]").first();
	if (await peekClose.count()) {
		await peekClose.click().catch(() => {});
		await page.waitForTimeout(500);
	}
	const open = page.locator("[data-linker-genie-open], .linker-genie-open").first();
	if (await open.count()) {
		await open.click().catch(() => {});
	}
	await composer(page)
		.waitFor({ state: "visible", timeout: 25000 })
		.catch(() => {});
	// The send button is disabled while the native draft context is not ready.
	for (let i = 0; i < 40; i++) {
		if (!(await sendButton(page).isDisabled().catch(() => true))) break;
		await page.waitForTimeout(500);
	}
}

/**
 * Send one real turn and read the answer the way a customer sees it.
 *
 * Success requires all three: the proxy answered 2xx, the meta carried a
 * `turn_id` (the control row's own gate for vote buttons), and the assistant
 * message carries text. A turn that errors is reported as a failed check with
 * the app's own error text — never as a route/UI defect and never as success.
 */
export async function askTurn(page, question, { timeout = 300000 } = {}) {
	const input = composer(page);
	await input.waitFor({ state: "visible", timeout: 20000 });
	await input.fill(question);
	for (let i = 0; i < 40; i++) {
		if (!(await sendButton(page).isDisabled().catch(() => true))) break;
		await page.waitForTimeout(500);
	}
	let response = null;
	const onResponse = async (r) => {
		if (!r.url().includes("/genie/turn") || r.request().method() !== "POST") return;
		if (response) return;
		let body = "";
		try {
			body = await r.text();
		} catch {
			body = "";
		}
		// The proxy answers `{ conversation_id, stream }`; the meta event with
		// `turn_id`/`route` lives inside the SSE string.
		let stream = body;
		try {
			const parsed = JSON.parse(body);
			if (parsed && typeof parsed.stream === "string") stream = parsed.stream;
		} catch {}
		const meta = stream.match(/turn_id\\?"?\s*:\s*(\d+)/);
		const route = stream.match(/route\\?"?\s*:\s*\\?"([^"\\]+)/);
		const intent = stream.match(/intent\\?"?\s*:\s*\\?"([^"\\]+)/);
		response = {
			status: r.status(),
			turnId: meta ? Number(meta[1]) : null,
			route: route ? route[1] : null,
			intent: intent ? intent[1] : null,
			bodyHead: stream.slice(0, 240),
		};
	};
	page.on("response", onResponse);
	await sendButton(page).click({ timeout: 15000 }).catch(() => {});
	const started = Date.now();
	let last = "";
	let stableSince = 0;
	let result = null;
	while (Date.now() - started < timeout) {
		await page.waitForTimeout(1500);
		const bodies = await assistantBodies(page);
		const errors = await appErrors(page);
		const waiting = (await dock(page).locator(".linker-genie-wait").count()) > 0;
		const joined = bodies.join("\n");
		if (errors.length && !waiting) {
			result = { ok: false, error: errors.join(" | ").slice(0, 200) };
			break;
		}
		if (!waiting && joined && joined === last) {
			if (!stableSince) stableSince = Date.now();
			if (Date.now() - stableSince > 3500) {
				result = { ok: true, text: joined, bodies };
				break;
			}
		} else {
			stableSince = 0;
		}
		last = joined;
	}
	page.off("response", onResponse);
	const answerText = result?.text ?? last;
	// The answer this turn produced is the last assistant message, not the
	// whole thread: earlier answers stay in the panel.
	const thisAnswer = (result?.bodies ?? []).slice(-1)[0] ?? "";
	const httpOk = !!response && response.status >= 200 && response.status < 300;
	const answered = !!result?.ok && httpOk && !!response?.turnId && answerText.length > 80;
	let reason = null;
	if (!answered) {
		reason =
			result?.error ??
			(!response
				? "no turn request observed"
				: !httpOk
					? `turn request failed (HTTP ${response.status})`
					: !response.turnId
						? `no turn_id in the answer meta (HTTP ${response.status})`
						: `no customer-visible answer text (HTTP ${response.status})`);
	}
	return {
		ok: answered,
		httpStatus: response?.status ?? null,
		turnId: response?.turnId ?? null,
		route: response?.route ?? null,
		intent: response?.intent ?? null,
		/* The whole thread, and the one message this turn added. */
		text: answerText,
		answer: thisAnswer,
		error: answered ? null : String(reason),
	};
}

/** The two thumb buttons and the copy button of the last answer.
 * `CopyReply` and `VoteButtons` share the `__vote` class, so the thumbs are
 * selected by their own accessible names, not by the shared class. */
export function answerControls(page) {
	const actions = dock(page).locator(".linker-genie-answer-actions").last();
	return {
		actions,
		votes: actions.locator(
			'[aria-label="Helpful"], [aria-label="Not helpful"], [aria-label="Hilfreich"], [aria-label="Nicht hilfreich"]'
		),
		copy: actions.locator('[aria-label="Copy response"], [aria-label="Antwort kopieren"]'),
	};
}

