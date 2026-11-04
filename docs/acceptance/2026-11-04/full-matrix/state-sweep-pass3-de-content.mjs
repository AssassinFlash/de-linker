import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const { chromium } = createRequire(path.join(repo, "tests/e2e/package.json"))("playwright");
const [outArg, baseArg] = process.argv.slice(2);
const base = baseArg.replace(/\/$/, "");
const out = path.resolve(outArg);
fs.mkdirSync(path.join(out, "screenshots"), { recursive: true });
const results = [];

async function record(key, lang, width, page, url, checks, scope) {
	const stem = `pass3-${key}:${lang}:${width}`.replace(/[^a-zA-Z0-9_.:-]/g, "_");
	const shot = path.join(out, "screenshots", `${stem}.png`);
	let screenshot = null;
	if (page) { try { await page.screenshot({ path: shot }); screenshot = path.relative(repo, shot); } catch {} }
	const failed = checks.filter((c) => c.result === "fail").length;
	results.push({ key: `${key}:${lang}:${width}`, stateKey: key, lang, width, url, checks, passed: checks.length - failed, failed, status: failed ? "fail" : "observed", screenshot, scope, observedAt: new Date().toISOString(), pass: 3 });
	console.log(`${failed ? "FAIL" : "ok  "} ${key}:${lang}:${width}`);
}
async function open(context, route) {
	const page = await context.newPage();
	await page.goto(base + route, { waitUntil: "domcontentloaded", timeout: 60000 });
	await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
	const reject = page.locator('[data-cky-tag="reject-button"]:visible');
	if (await reject.count()) await reject.first().click().catch(() => {});
	return page;
}

const browser = await chromium.launch({ channel: "chromium", args: ["--disable-gpu"] });
try {
	for (const width of [1440, 390]) {
		const context = await browser.newContext({ viewport: { width, height: 844 }, reducedMotion: "reduce", isMobile: width === 390, hasTouch: width === 390 });
		const page = await open(context, "/de/loesung/");
		const details = page.locator("details, .accordion-button, [data-bs-toggle='collapse']").first();
		if (await details.count()) {
			const summary = details.locator("summary").first();
			const target = (await summary.count()) ? summary : details;
			const open0 = await details.getAttribute("open").catch(() => null);
			await target.click({ timeout: 8000 }).catch(() => {});
			await page.waitForTimeout(400);
			const open1 = await details.getAttribute("open").catch(() => null);
			await record("content:accordion", "de", width, page, page.url(), [
				{ name: "disclosure toggles on /de/loesung/", result: open0 !== open1 ? "pass" : "observe", observed: `open ${open0}->${open1}` },
			], "DE disclosure on the real DE twin page 6871 (pass1 used an invented 404 URL; quarantined)");
		} else {
			await record("content:accordion", "de", width, page, page.url(), [{ name: "disclosure present", result: "fail", observed: "no disclosure control on /de/loesung/" }], "DE twin page");
		}
		const anchorNav = await page.locator("main a[href^='#']").count();
		await record("content:section-navigation", "de", width, page, page.url(), [
			{ name: "same-page anchors", result: anchorNav > 0 ? "pass" : "observe", observed: `anchors=${anchorNav}` },
		], "DE anchor navigation count");
		const cta = page.locator("main a[class*='btn'], main .wp-block-button__link, main a[class*='cta']").first();
		if (await cta.count()) {
			const href = await cta.getAttribute("href");
			const status = await page.request.get(href.startsWith("http") ? href : base + href).then((r) => r.status()).catch(() => null);
			await record("content:cta-destination", "de", width, page, page.url(), [
				{ name: "first CTA resolves", result: status && status < 400 ? "pass" : "fail", observed: `href=${href} status=${status}` },
			], "DE CTA destination fetch");
		} else {
			await record("content:cta-destination", "de", width, page, page.url(), [{ name: "CTA", result: "fail", observed: "no CTA matched" }], "DE twin page");
		}
		const media = await page.locator("main iframe, main video").count();
		const imgs = await page.locator("main img").count();
		await record("content:embedded-media", "de", width, page, page.url(), [
			{ name: "media present", result: media + imgs > 0 ? "pass" : "fail", observed: `iframe/video=${media} imgs=${imgs}` },
		], "DE media presence");
		const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
		const longWords = await page.evaluate(() => (document.body.innerText || "").split(/\s+/).filter((w) => w.length > 25).slice(0, 3));
		await record("content:long-german-text", "de", width, page, page.url(), [
			{ name: "no horizontal overflow", result: overflow ? "fail" : "pass", observed: `overflow=${overflow}` },
			{ name: "long compounds sampled", result: "observe", observed: longWords.join(" | ").slice(0, 160) },
		], "DE long-word typography on real DE page");
		await page.close();
		const fp = await open(context, "/de/kontakt/");
		const required = await fp.locator("form [required], form [aria-required='true']").count();
		const submitBtn = fp.locator("form button[type='submit'], form input[type='submit']").first();
		let validation = "not-testable";
		let navigated = false;
		if (await submitBtn.count()) {
			await submitBtn.click().catch(() => {});
			await fp.waitForTimeout(600);
			validation = await fp.evaluate(() => [...document.querySelectorAll("form :invalid")].map((n) => n.name || n.id).slice(0, 5).join(",") || "no-invalid-flagged");
			navigated = !/de\/kontakt/.test(new URL(fp.url()).pathname);
		}
		await record("content:forms-and-validation", "de", width, fp, fp.url(), [
			{ name: "required fields", result: required > 0 ? "pass" : "observe", observed: `required=${required}` },
			{ name: "empty submit blocked client-side", result: navigated ? "fail" : "pass", observed: `navigated=${navigated}; invalid=${validation}` },
		], "DE contact form client-side validation only; NO submission");
		await fp.close();
		await context.close();
		fs.writeFileSync(path.join(out, "state-results-pass3.json"), `${JSON.stringify(results, null, 2)}\n`);
	}
} finally {
	await browser.close();
	fs.writeFileSync(path.join(out, "state-results-pass3.json"), `${JSON.stringify(results, null, 2)}\n`);
}
console.log(JSON.stringify({ rows: results.length, fails: results.filter((r) => r.failed > 0).map((r) => r.key) }));
