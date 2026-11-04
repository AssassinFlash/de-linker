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

export function check(name, ok, detail = null, injected = false) {
	return { name, result: ok ? "pass" : "fail", detail, ...(injected ? { failureInjection: "one-shot network abort" } : {}) };
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
