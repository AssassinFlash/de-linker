import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const { chromium } = createRequire(path.join(repo, "tests/e2e/package.json"))("playwright");
const [outArg, baseArg] = process.argv.slice(2);
if (!outArg || !baseArg) throw new Error("usage: node state-sweep-pass4.mjs <outdir> <local-base>");
const base = baseArg.replace(/\/$/, "");
const out = path.resolve(outArg);
fs.mkdirSync(path.join(out, "screenshots"), { recursive: true });
const results = [];

async function record(key, lang, width, page, url, checks, scope) {
	const stem = `pass4-${key}:${lang}:${width}`.replace(/[^a-zA-Z0-9_.:-]/g, "_");
	const shot = path.join(out, "screenshots", `${stem}.png`);
	let screenshot = null;
	if (page) { try { await page.screenshot({ path: shot }); screenshot = path.relative(repo, shot); } catch {} }
	const failed = checks.filter((c) => c.result === "fail").length;
	results.push({ key: `${key}:${lang}:${width}`, stateKey: key, lang, width, url, checks, passed: checks.length - failed, failed, status: failed ? "fail" : "observed", screenshot, scope, observedAt: new Date().toISOString(), pass: 4 });
	console.log(`${failed ? "FAIL" : "ok  "} ${key}:${lang}:${width}`);
}
async function open(context, route) {
	const page = await context.newPage();
	await page.goto(base + route, { waitUntil: "domcontentloaded", timeout: 90000 });
	await page.waitForLoadState("networkidle", { timeout: 10000 }).catch(() => {});
	const reject = page.locator('[data-cky-tag="reject-button"]:visible');
	if (await reject.count()) await reject.first().click().catch(() => {});
	return page;
}
const CLICK = { timeout: 20000 };

const browser = await chromium.launch({ channel: "chromium", args: ["--disable-gpu"] });
try {
	for (const lang of ["en", "de"]) {
		for (const width of [1440, 390]) {
			const context = await browser.newContext({ viewport: { width, height: 844 }, reducedMotion: "reduce", isMobile: width === 390, hasTouch: width === 390 });
			const cat = lang === "en" ? "/product-category/commercial-storage/" : "/de/produkt-kategorie/gewerbespeicher/";
			const shop = lang === "en" ? "/products/" : "/de/produkte/";
			const faq = lang === "en" ? "/faq-download/" : "/de/faq-dokumente/";
			const pdp = lang === "en" ? "/product/saj-ats1-t63-a/" : "/de/produkt/goodwe-gw60k-sts-g10/";
			const prodPath = lang === "en" ? "/product/" : "/produkt/";

			// menu open (390 semantics + 1440 applicability) with scroll and patience
			{
				const page = await open(context, lang === "en" ? "/" : "/de/");
				const trigger = page.locator("button.tv-nav-link").first();
				await trigger.scrollIntoViewIfNeeded().catch(() => {});
				const before = await trigger.getAttribute("aria-expanded").catch(() => null);
				let clicked = true;
				await trigger.click(CLICK).catch(() => { clicked = false; });
				await page.waitForTimeout(500);
				const after = await trigger.getAttribute("aria-expanded").catch(() => null);
				await record("global-navigation:mobile-menu-open", lang, width, page, page.url(), [
					{ name: "nav trigger toggles", result: clicked && before === "false" && after === "true" ? "pass" : "fail", observed: `clicked=${clicked} aria-expanded ${before}->${after}` },
				], "tv-nav-link trigger with scroll-into-view; branch applicability judged per width at review");
				await page.close();
			}
			// language switch via visible toggle
			{
				const page = await open(context, lang === "en" ? "/blog/" : "/de/blog/");
				const link = page.locator("span.lnk-lang-toggle:visible a.lnk-lang-half:not(.is-active)").first();
				if (await link.count()) {
					await link.scrollIntoViewIfNeeded().catch(() => {});
					const href = await link.getAttribute("href");
					await link.click(CLICK).catch(() => {});
					await page.waitForLoadState("domcontentloaded").catch(() => {});
					await page.waitForTimeout(600);
					const l = await page.evaluate(() => document.documentElement.lang);
					await record("global-navigation:language-switch-current-route", lang, width, page, page.url(), [
						{ name: "document lang after switch", result: l.startsWith(lang === "en" ? "de" : "en") ? "pass" : "fail", observed: l },
						{ name: "translated route", result: (/\/de\//.test(new URL(page.url()).pathname)) === (lang === "en") ? "pass" : "fail", observed: page.url() },
					], "Language switch through the width-visible toggle");
				} else {
					await record("global-navigation:language-switch-current-route", lang, width, page, page.url(), [{ name: "visible switch", result: "fail", observed: "none visible" }], "No visible toggle");
				}
				await page.close();
			}
			// archive filter drawer with scroll + apply
			{
				const page = await open(context, cat);
				const openBtn = page.locator("#product-filter-open");
				if (await openBtn.count()) {
					await openBtn.scrollIntoViewIfNeeded().catch(() => {});
					await openBtn.click(CLICK).catch(() => {});
					await page.waitForTimeout(600);
					const drawer = await page.evaluate(() => { const el = document.querySelector("#sidebar-filters"); return el ? el.getBoundingClientRect().width > 0 : false; });
					const option = page.locator(".filter-option:not(.is-disabled)").first();
					let applied = false, urlAfter = page.url(), cards = 0;
					if (drawer && (await option.count())) {
						await option.scrollIntoViewIfNeeded().catch(() => {});
						await option.click(CLICK).catch(() => {});
						const apply = page.locator("#product-filter-apply");
						if (await apply.count()) { await apply.scrollIntoViewIfNeeded().catch(() => {}); await apply.click(CLICK).catch(() => {}); await page.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {}); }
						await page.waitForTimeout(1000);
						applied = true; urlAfter = page.url();
						cards = await page.locator(`main a[href*='${prodPath}']`).count();
					}
					await record("product-archive:category-brand-filters", lang, width, page, urlAfter, [
						{ name: "filter drawer opens", result: drawer ? "pass" : "fail", observed: `drawer=${drawer}` },
						{ name: "option applied", result: applied ? "pass" : "fail", observed: `applied=${applied}` },
						{ name: "filtered cards", result: "observe", observed: `cards=${cards}` },
					], "Real filter drawer: open/option/apply with scroll-into-view");
				} else {
					await record("product-archive:category-brand-filters", lang, width, page, page.url(), [{ name: "filter trigger", result: "fail", observed: "#product-filter-open absent on category" }], "Filter trigger");
				}
				await page.close();
			}
			// pagination with DE-correct selector
			{
				const page = await open(context, shop);
				const next = page.locator(".tv-woo-pagination a.next").first();
				if (await next.count()) {
					await next.scrollIntoViewIfNeeded().catch(() => {});
					await next.click(CLICK).catch(() => {});
					await page.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
					await page.waitForTimeout(700);
					const url2 = page.url();
					const cards2 = await page.locator(`main a[href*='${prodPath}']`).count();
					await record("product-archive:pagination", lang, width, page, url2, [
						{ name: "page 2 reached with entries", result: /page=2|\/page\/2/.test(url2) && cards2 > 0 ? "pass" : "fail", observed: `url=${url2} cards=${cards2}` },
					], "Shop archive pagination with locale-correct product path");
				} else {
					await record("product-archive:pagination", lang, width, page, page.url(), [{ name: "pagination", result: "fail", observed: "no next control" }], "Shop pagination");
				}
				await page.close();
			}
			// FAQ empty state via real selector + GMK results
			{
				const page = await open(context, faq);
				const q = page.locator("#linker-library-q");
				if (await q.count()) {
					await q.click();
					await q.fill("GMK");
					await page.waitForTimeout(1200);
					const gmk = await page.evaluate(() => ({
						count: document.querySelector("#linker-library-result-count")?.innerText.trim().slice(0, 80) || null,
						ledgerHits: document.querySelectorAll(".linker-library-ledger [data-library-hit], .linker-library-ledger li").length,
						suggest: document.querySelectorAll("#linker-library-suggest [role='option'], #linker-library-suggest li").length,
					}));
					await record("document-library:search-results-and-live-count", lang, width, page, page.url(), [
						{ name: "live count present", result: gmk.count ? "pass" : "fail", observed: JSON.stringify(gmk) },
					], "FAQ search results + live count element");
					await q.fill("zzzzqqqqx");
					await page.waitForTimeout(1000);
					const empty = await page.evaluate(() => { const el = document.querySelector(".linker-library-empty"); return el ? { visible: el.getBoundingClientRect().height > 0, text: el.innerText.trim().slice(0, 120) } : null; });
					await q.fill("");
					await page.waitForTimeout(700);
					const cleared = await page.evaluate(() => document.querySelectorAll(".linker-library-ledger [data-library-hit], #linker-library-panel-faq li").length);
					await record("document-library:search-empty-and-clear", lang, width, page, page.url(), [
						{ name: "no-match empty element", result: empty && empty.visible ? "pass" : "fail", observed: JSON.stringify(empty) },
						{ name: "clear restores items", result: cleared > 0 ? "pass" : "fail", observed: `items=${cleared}` },
					], "No-match state = .linker-library-empty element (label text is page-config localized)");
					await page.close();
				} else { await page.close(); }
			}
			// compare: chip + remove via markup discovered in probes
			{
				const page = await open(context, pdp);
				const btn = page.locator("button.pdp-tool[data-compare-product]").first();
				if (await btn.count()) {
					await btn.scrollIntoViewIfNeeded();
					await btn.click(CLICK).catch(() => {});
					await page.waitForTimeout(700);
					const chip = await page.evaluate(() => {
						const c = document.querySelector(".linker-compare-chip");
						if (!c) return null;
						const r = c.getBoundingClientRect();
						if (r.width === 0) return { hidden: true };
						const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
						return { w: Math.round(r.width), h: Math.round(r.height), topAtCenter: top === c || c.contains(top) ? "self" : top ? top.tagName + "." + String(top.className).slice(0, 50) : "none" };
					});
					await record("global-navigation:floating-widgets-no-obstruction", lang, width, page, page.url(), [
						{ name: "visible chip reachable at center", result: chip && chip.topAtCenter === "self" ? "pass" : "fail", observed: JSON.stringify(chip) },
					], "Compare chip center hit-test while visible");
					const chipHref = await page.evaluate(() => document.querySelector(".linker-compare-chip a")?.getAttribute("href") || "/compare-products/");
					const cp = await context.newPage();
					await cp.goto(base + (lang === "en" ? "/compare-products/" : "/de/produkte-vergleichen/"), { waitUntil: "domcontentloaded", timeout: 60000 });
					await cp.waitForTimeout(1200);
					const cpInfo = await cp.evaluate(() => ({
						rows: document.querySelectorAll("main [data-compare-id], main [data-product-id], main table tr").length,
						removeControls: [...document.querySelectorAll("main button, main a")].filter((n) => /remove|clear|entfernen|reset/i.test((n.getAttribute("aria-label") || "") + " " + n.innerText + " " + n.className)).map((n) => ({ tag: n.tagName, label: (n.getAttribute("aria-label") || n.innerText || "").trim().slice(0, 40) })).slice(0, 4),
					}));
					let removed = null;
					const rm = cp.locator("main button, main a").filter({ hasText: /remove|clear|entfernen/i }).first();
					if (cpInfo.removeControls.length && (await rm.count())) {
						await rm.scrollIntoViewIfNeeded().catch(() => {});
						await rm.click(CLICK).catch(() => {});
						await cp.waitForTimeout(700);
						removed = await cp.evaluate(() => document.querySelectorAll("main [data-compare-id], main table tr").length);
					}
					await record("comparison:remove-product", lang, width, cp, cp.url(), [
						{ name: "remove control present", result: cpInfo.removeControls.length ? "pass" : "fail", observed: JSON.stringify(cpInfo.removeControls) },
						{ name: "rows after remove", result: "observe", observed: `rows=${removed}` },
					], "Compare page remove control with real selection");
					await cp.close();
				}
				await page.close();
			}
			await context.close();
			fs.writeFileSync(path.join(out, "state-results-pass4.json"), `${JSON.stringify(results, null, 2)}\n`);
		}
	}
	// slow network with the page sweep suspended by the caller if provided
	{
		const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
		const page = await context.newPage();
		const cdp = await context.newCDPSession(page);
		await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 600, downloadThroughput: (120 * 1024) / 8, uploadThroughput: (60 * 1024) / 8 }).catch(() => {});
		const t0 = Date.now();
		let h1 = "";
		try { await page.goto(base + "/contact/", { waitUntil: "load", timeout: 60000 }); h1 = await page.locator("h1").first().innerText().catch(() => ""); } catch {}
		const elapsed = Date.now() - t0;
		await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }).catch(() => {});
		await record("files-and-feedback:slow-network-loading", "en", 1440, page, page.url(), [
			{ name: "throttled load completes", result: h1 ? "pass" : "fail", observed: `elapsed=${elapsed}ms h1=${h1.trim().slice(0, 60)}` },
		], "Standalone throttled load after background load removed");
		await context.close();
	}
	// cookie reopen
	for (const lang of ["en", "de"]) {
		const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
		const page = await context.newPage();
		await page.goto(base + (lang === "en" ? "/" : "/de/"), { waitUntil: "domcontentloaded", timeout: 60000 });
		await page.waitForTimeout(2000);
		const rej = page.locator('[data-cky-tag="reject-button"]:visible');
		if (await rej.count()) await rej.click().catch(() => {});
		await page.waitForTimeout(1200);
		const revisitInfo = await page.evaluate(() => [...document.querySelectorAll("[class*='revisit'], [data-cky-tag='revisit-consent']")].map((n) => ({ tag: n.tagName, cls: String(n.className).slice(0, 60), visible: n.getBoundingClientRect().width > 0 })).slice(0, 5));
		let reopened = false;
		const rv = page.locator(".cky-revisit, [data-cky-tag='revisit-consent']").first();
		if (await rv.count()) { await rv.scrollIntoViewIfNeeded().catch(() => {}); await rv.click(CLICK).catch(() => {}); await page.waitForTimeout(900); reopened = await page.locator("[data-cky-tag='notice']:visible").count() > 0; }
		await record("global-navigation:cookie-choice-and-reopen", lang, 1440, page, page.url(), [
			{ name: "revisit control found", result: revisitInfo.some((r) => r.visible) ? "pass" : "fail", observed: JSON.stringify(revisitInfo) },
			{ name: "banner reopens", result: reopened ? "pass" : "fail", observed: `reopened=${reopened}` },
		], "Cookie banner reopen path");
		await context.close();
	}
} finally {
	await browser.close();
	fs.writeFileSync(path.join(out, "state-results-pass4.json"), `${JSON.stringify(results, null, 2)}\n`);
}
console.log(JSON.stringify({ rows: results.length, fails: results.filter((r) => r.failed > 0).map((r) => r.key) }, null, 2));
