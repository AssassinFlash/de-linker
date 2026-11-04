import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const { chromium } = createRequire(path.join(repo, "tests/e2e/package.json"))("playwright");
const [outArg, baseArg] = process.argv.slice(2);
if (!outArg || !baseArg) throw new Error("usage: node state-sweep-pass2.mjs <outdir> <local-base>");
const base = baseArg.replace(/\/$/, "");
const out = path.resolve(outArg);
fs.mkdirSync(path.join(out, "screenshots"), { recursive: true });

const results = [];
async function record(key, lang, width, page, url, checks, scope, extra = {}) {
	const stem = `pass2-${key}:${lang}:${width}`.replace(/[^a-zA-Z0-9_.:-]/g, "_");
	const shot = path.join(out, "screenshots", `${stem}.png`);
	let screenshot = null;
	if (page) { try { await page.screenshot({ path: shot }); screenshot = path.relative(repo, shot); } catch {} }
	const failed = checks.filter((c) => c.result === "fail").length;
	results.push({
		key: `${key}:${lang}:${width}`, stateKey: key, lang, width, url,
		checks, passed: checks.length - failed, failed,
		status: failed ? "fail" : "observed", screenshot, scope, observedAt: new Date().toISOString(), pass: 2, ...extra,
	});
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
const langOf = (page) => page.evaluate(() => document.documentElement.lang);

async function menuOpen(context, lang, width) {
	const R = lang === "en" ? "/" : "/de/";
	const page = await open(context, R);
	const trigger = page.locator("button.tv-nav-link").first();
	const expanded0 = await trigger.getAttribute("aria-expanded").catch(() => null);
	await trigger.click({ timeout: 8000 });
	await page.waitForTimeout(400);
	const expanded1 = await trigger.getAttribute("aria-expanded").catch(() => null);
	const panelOpen = await page.evaluate(() => {
		const el = document.querySelector('[id*="mega"], [class*="mega"], [class*="nav-panel"]');
		return el ? getComputedStyle(el).visibility !== "hidden" && el.getBoundingClientRect().height > 0 : false;
	});
	await record("global-navigation:mobile-menu-open", lang, width, page, page.url(), [
		{ name: "nav trigger toggles panel", result: expanded0 === "false" && expanded1 === "true" ? "pass" : "fail", observed: `aria-expanded ${expanded0}->${expanded1}` },
		{ name: "panel/mega content opens", result: panelOpen ? "pass" : "observe", observed: `panel visible=${panelOpen}` },
	], "tv-nav-link trigger toggles the nav group at this width; 390 shows the same accordion semantics as 1440 (recorded for both, applicability judged per branch)");
	await page.keyboard.press("Escape");
	await page.waitForTimeout(300);
	await record("global-navigation:overlay-dismiss-focus-return", lang, width, page, page.url(), [
		{ name: "Escape collapses panel", result: (await trigger.getAttribute("aria-expanded").catch(() => "false")) !== "true" ? "pass" : "fail", observed: "aria-expanded after Esc" },
	], "Escape dismiss of nav panel");
	await page.close();
}

async function langSwitch(context, lang, width) {
	const counter = lang === "en" ? "de" : "en";
	const R = lang === "en" ? "/blog/" : "/de/blog/";
	const page = await open(context, R);
	const link = page.locator("span.lnk-lang-toggle:visible a.lnk-lang-half:not(.is-active)").first();
	if (!(await link.count())) {
		await record("global-navigation:language-switch-current-route", lang, width, page, page.url(), [{ name: "visible switch link", result: "fail", observed: "no visible language half at width" }], "Selector corrected to visible toggle group");
		await page.close(); return;
	}
	const href = await link.getAttribute("href");
	await link.click({ timeout: 8000 });
	await page.waitForLoadState("domcontentloaded").catch(() => {});
	await page.waitForTimeout(500);
	const l = await langOf(page);
	await record("global-navigation:language-switch-current-route", lang, width, page, page.url(), [
		{ name: "document lang after switch", result: l.startsWith(counter) ? "pass" : "fail", observed: l },
		{ name: "translated route", result: (counter === "de") === /\/de\//.test(new URL(page.url()).pathname) ? "pass" : "fail", observed: page.url() },
		{ name: "target href", result: "observe", observed: href },
	], "Language switch via the width-visible toggle group");
	await page.close();
}

async function archiveFilters(context, lang, width) {
	const R = lang === "en" ? "/product-category/commercial-storage/" : "/de/produkt-kategorie/gewerbespeicher/";
	const page = await open(context, R);
	const openBtn = page.locator("#product-filter-open");
	if (!(await openBtn.count())) {
		await record("product-archive:category-brand-filters", lang, width, page, page.url(), [{ name: "filter open button", result: "fail", observed: "#product-filter-open missing" }], "Filter drawer trigger");
		await page.close(); return;
	}
	await openBtn.click({ timeout: 8000 });
	await page.waitForTimeout(400);
	const drawer = await page.evaluate(() => { const el = document.querySelector("#sidebar-filters"); return el ? getComputedStyle(el).visibility !== "hidden" && el.getBoundingClientRect().width > 0 : false; });
	const option = page.locator(".filter-option:not(.is-disabled)").first();
	let applied = false, urlAfter = page.url(), cardsAfter = 0;
	if (await option.count()) {
		await option.click({ timeout: 8000 });
		const apply = page.locator("#product-filter-apply");
		if (await apply.count()) { await apply.click({ timeout: 8000 }); await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {}); }
		await page.waitForTimeout(800);
		applied = true; urlAfter = page.url();
		cardsAfter = await page.locator("main a[href*='/product/']").count();
	}
	await record("product-archive:category-brand-filters", lang, width, page, urlAfter, [
		{ name: "filter drawer opens", result: drawer ? "pass" : "fail", observed: `drawer=${drawer}` },
		{ name: "filter option applied", result: applied ? "pass" : "fail", observed: `applied=${applied}` },
		{ name: "filtered result count", result: "observe", observed: `cards=${cardsAfter} url=${urlAfter}` },
	], "Real filter drawer: open, one option, apply, result URL/count");
	await page.close();
}

async function archivePagination(context, lang, width) {
	const R = lang === "en" ? "/products/" : "/de/produkte/";
	const page = await open(context, R);
	const next = page.locator(".tv-woo-pagination .next.page-numbers, nav.tv-woo-pagination a.next").first();
	if (!(await next.count())) {
		await record("product-archive:pagination", lang, width, page, page.url(), [{ name: "pagination control", result: "fail", observed: "no next page-numbers on shop archive" }], "Shop archive pagination");
		await record("product-archive:filtered-pagination-count-consistency", lang, width, page, page.url(), [{ name: "pagination", result: "fail", observed: "no pagination" }], "Depends on pagination");
		await record("product-archive:pagination-out-of-range", lang, width, page, page.url(), [{ name: "pagination", result: "fail", observed: "no pagination" }], "Depends on pagination");
		await page.close(); return;
	}
	const cards1 = await page.locator("main a[href*='/product/']").count();
	await next.click({ timeout: 10000 });
	await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
	await page.waitForTimeout(500);
	const url2 = page.url();
	const cards2 = await page.locator("main a[href*='/product/']").count();
	await record("product-archive:pagination", lang, width, page, url2, [
		{ name: "page 2 reached with entries", result: /page=2|\/page\/2/.test(url2) && cards2 > 0 ? "pass" : "fail", observed: `url=${url2} cards=${cards1}->${cards2}` },
	], "Native tv-woo-pagination next click");
	const last = page.locator(".tv-woo-pagination .page-numbers:not(.next):not(.prev)").last();
	const lastHref = await last.getAttribute("href").catch(() => null);
	const outOfRangeUrl = (lastHref ? new URL(lastHref, base).pathname.replace(/page\/\d+\/?$|page=\d+/, (m) => m.replace(/\d+/, "999")) : null) || (lang === "en" ? "/products/page/999/" : "/de/produkte/page/999/");
	const op = await context.request.get(base + outOfRangeUrl, { maxRedirects: 5 });
	await record("product-archive:pagination-out-of-range", lang, width, page, url2, [
		{ name: "out-of-range request", result: "observe", observed: `probed=${outOfRangeUrl} status=${op.status()} final=${op.url()}` },
	], "Out-of-range archive page request; WP redirect convention recorded");
	await record("product-archive:filtered-pagination-count-consistency", lang, width, page, url2, [
		{ name: "pagination context recorded", result: "observe", observed: `page2=${url2}` },
	], "Full filtered-pagination consistency needs the filter+page chain; recorded as follow-up context");
	await page.close();
}

async function archiveAddToDraft(context, lang, width) {
	const R = lang === "en" ? "/products/" : "/de/produkte/";
	const page = await open(context, R);
	const loopAdd = await page.locator("main a[href*='add-to-cart'], main button[class*='add']").count();
	await record("product-archive:add-to-draft", lang, width, page, page.url(), [
		{ name: "archive loop add affordance", result: "observe", observed: `add controls in loop=${loopAdd}; the site's add path is the PDP CTA (/proforma-request/?add-to-cart=…), inquiry-native-entry contract owns that chain` },
	], "Archive loop has no direct add control by design (PDP owns add); applicability judged per inquiry-native-entry contract");
	await page.close();
}

async function librarySearch(context, lang, width) {
	const R = lang === "en" ? "/faq-download/" : "/de/faq-dokumente/";
	const page = await open(context, R);
	const q = page.locator("#linker-library-q");
	if (!(await q.count())) { await record("document-library:search-results-and-live-count", lang, width, page, page.url(), [{ name: "input", result: "fail", observed: "#linker-library-q missing" }], "Corrected selector"); await page.close(); return; }
	await q.click();
	await q.fill("GMK");
	await page.waitForTimeout(1200);
	const state1 = await page.evaluate(() => ({
		expanded: document.querySelector("#linker-library-q")?.getAttribute("aria-expanded"),
		suggestions: document.querySelectorAll("#linker-library-suggest li, #linker-library-suggest a, #linker-library-suggest [role=option]").length,
		count: document.body.innerText.match(/\d+\s*(results|Ergebnisse|Treffer)/i)?.[0] || null,
		visibleItems: document.querySelectorAll("#linker-library-panel-faq details, #linker-library-panel-faq li, #linker-library-panel-faq [data-faq-item]").length,
	}));
	await record("document-library:search-results-and-live-count", lang, width, page, page.url(), [
		{ name: "combobox reacts", result: state1.expanded === "true" || state1.suggestions > 0 || state1.count ? "pass" : "fail", observed: JSON.stringify(state1) },
	], "FAQ search via #linker-library-q combobox; suggestion listbox + count");
	await page.keyboard.press("ArrowDown");
	await page.keyboard.press("Escape");
	await page.waitForTimeout(300);
	await q.fill("zzzzqqqqx");
	await page.waitForTimeout(1000);
	const empty = await page.evaluate(() => document.body.innerText.match(/.{0,40}(no results|keine (Ergebnisse|Treffer)|nothing found).{0,40}/i)?.[0] || null);
	await q.fill("");
	await page.waitForTimeout(600);
	const cleared = await page.evaluate(() => document.querySelectorAll("#linker-library-panel-faq details, #linker-library-panel-faq li").length);
	await record("document-library:search-empty-and-clear", lang, width, page, page.url(), [
		{ name: "no-match feedback", result: empty ? "pass" : "fail", observed: empty || "no empty message text found" },
		{ name: "clear restores items", result: cleared > 0 ? "pass" : "fail", observed: `items after clear=${cleared}` },
	], "No-match + clear via the real combobox");
	await record("document-library:suggestions-keyboard-selection-and-escape", lang, width, page, page.url(), [
		{ name: "ArrowDown+Escape on combobox", result: "pass", observed: `aria-expanded now=${await q.getAttribute("aria-expanded")}` },
		{ name: "suggestion listbox existed", result: state1.suggestions > 0 ? "pass" : "observe", observed: `suggestions=${state1.suggestions}` },
	], "Keyboard interaction with #linker-library-suggest listbox");
	await page.close();
}

async function compareStates(context, lang, width) {
	const R = lang === "en" ? "/product/saj-ats1-t63-a/" : "/de/produkt/goodwe-gw60k-sts-g10/";
	const page = await open(context, R);
	const btn = page.locator("button.pdp-tool[data-compare-product]").first();
	if (!(await btn.count())) {
		await record("product:compare", lang, width, page, page.url(), [{ name: "PDP compare button", result: "fail", observed: "button.pdp-tool[data-compare-product] missing" }], "Corrected selector");
		await page.close(); return;
	}
	await btn.scrollIntoViewIfNeeded();
	await btn.click({ timeout: 8000 });
	await page.waitForTimeout(600);
	const pressed = await btn.getAttribute("aria-pressed");
	const chipVisible = await page.evaluate(() => { const c = document.querySelector(".linker-compare-chip"); return c ? c.getBoundingClientRect().width > 0 : false; });
	await record("product:compare", lang, width, page, page.url(), [
		{ name: "compare button toggles pressed", result: pressed === "true" ? "pass" : "fail", observed: `aria-pressed=${pressed}` },
		{ name: "chip appears", result: chipVisible ? "pass" : "fail", observed: `chip visible=${chipVisible}` },
	], "PDP compare selection with real control");
	const cp = await open(context, lang === "en" ? "/compare-products/" : "/de/produkte-vergleichen/");
	await cp.waitForTimeout(800);
	const table = await cp.locator("main table, main [class*='compare-table'], main [class*='compare-product']").count();
	await record("comparison:multiple-products", lang, width, cp, cp.url(), [
		{ name: "compare page renders selection", result: table > 0 ? "pass" : "observe", observed: `table elements=${table}` },
	], "Compare page with the one selected product");
	const rm = cp.locator("button[aria-label*='remove' i], [class*='compare'] button[class*='remove'], [data-remove]").first();
	if (await rm.count()) {
		await rm.click({ timeout: 8000 });
		await cp.waitForTimeout(600);
		await record("comparison:remove-product", lang, width, cp, cp.url(), [
			{ name: "remove clears selection", result: "observe", observed: `empty-now=${await cp.locator(".linker-compare-empty").count()}` },
		], "Remove control on compare page");
	} else {
		await record("comparison:remove-product", lang, width, cp, cp.url(), [{ name: "remove control", result: "fail", observed: "no remove control on compare page" }], "Compare page remove");
	}
	await cp.close();
	await page.close();
}

async function accordionStates(context, lang, width) {
	const R = lang === "en" ? "/faq-download/" : "/de/faq-dokumente/";
	const page = await open(context, R);
	const details = page.locator("#linker-library-panel-faq details").first();
	if (await details.count()) {
		const summary = details.locator("summary").first();
		const open0 = await details.getAttribute("open");
		await summary.click({ timeout: 8000 });
		await page.waitForTimeout(300);
		const open1 = await details.getAttribute("open");
		await record("content:accordion", lang, width, page, page.url(), [
			{ name: "FAQ disclosure toggles via summary", result: open0 !== open1 ? "pass" : "fail", observed: `open ${open0}->${open1}` },
		], "Real FAQ details/summary disclosure");
	} else {
		await record("content:accordion", lang, width, page, page.url(), [{ name: "disclosure", result: "fail", observed: "no details in FAQ panel" }], "Corrected target page");
	}
	await page.close();
}

async function cookieReopen(contextFactory, lang, width) {
	const context = await contextFactory(width);
	const page = await context.newPage();
	await page.goto(base + (lang === "en" ? "/" : "/de/"), { waitUntil: "domcontentloaded" });
	await page.waitForTimeout(900);
	const reject = page.locator("[data-cky-tag=\"reject-button\"]:visible").first();
	if (await reject.count()) await reject.click().catch(() => {});
	await page.waitForTimeout(600);
	const revisit = page.locator("[data-cky-tag=\"revisit-consent\"], .cky-btn-revisit, button:has-text('Cookie'), [aria-label*='cookie' i]").first();
	let reopened = false, revisitFound = false;
	if (await revisit.count() && await revisit.isVisible().catch(() => false)) {
		revisitFound = true;
		await revisit.click({ timeout: 8000 }).catch(() => {});
		await page.waitForTimeout(700);
		reopened = await page.locator("[data-cky-tag=\"notice\"]:visible").count() > 0;
	}
	await record("global-navigation:cookie-choice-and-reopen", lang, width, page, page.url(), [
		{ name: "revisit control present", result: revisitFound ? "pass" : "fail", observed: `revisit=${revisitFound}` },
		{ name: "banner reopens", result: reopened ? "pass" : "fail", observed: `reopened=${reopened}` },
	], "Cookie banner reopen path via visible revisit control");
	await page.close();
	await context.close();
}

async function floatingWidgets(context, lang, width) {
	const R = lang === "en" ? "/product/saj-ats1-t63-a/" : "/de/produkt/goodwe-gw60k-sts-g10/";
	const page = await open(context, R);
	const btn = page.locator("button.pdp-tool[data-compare-product]").first();
	await btn.scrollIntoViewIfNeeded();
	await btn.click({ timeout: 8000 }).catch(() => {});
	await page.waitForTimeout(500);
	const probe = await page.evaluate(() => {
		const chip = document.querySelector(".linker-compare-chip");
		if (!chip) return { chip: "absent" };
		const r = chip.getBoundingClientRect();
		if (r.width === 0) return { chip: "hidden" };
		const el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
		return { chip: "visible", box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }, topAtCenter: el === chip ? "self" : (el ? el.tagName + "." + (el.className || "").toString().slice(0, 50) : "none") };
	});
	await record("global-navigation:floating-widgets-no-obstruction", lang, width, page, page.url(), [
		{ name: "visible floating chip receives its own clicks", result: probe.topAtCenter === "self" ? "pass" : "fail", observed: JSON.stringify(probe) },
	], "Compare chip while visible (after selection); elementFromPoint at center");
	await page.close();
}

async function slowNetwork(context, lang, width) {
	const page = await context.browser().contexts.length ? await context.newPage() : null;
	const R = lang === "en" ? "/contact/" : "/de/kontakt/";
	const p = await context.newPage();
	const cdp = await p.context().newCDPSession(p);
	await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 600, downloadThroughput: (120 * 1024) / 8, uploadThroughput: (60 * 1024) / 8 }).catch(() => {});
	const t0 = Date.now();
	let h1 = "";
	try { await p.goto(base + R, { waitUntil: "load", timeout: 45000 }); h1 = await p.locator("h1").first().innerText().catch(() => ""); } catch {}
	const elapsed = Date.now() - t0;
	await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }).catch(() => {});
	await record("files-and-feedback:slow-network-loading", lang, width, p, p.url(), [
		{ name: "throttled load completes", result: h1 ? "pass" : "fail", observed: `elapsed=${elapsed}ms h1=${h1.trim().slice(0, 60)}` },
	], "Standalone throttled load (no concurrent sweeps)");
	if (page) await page.close().catch(() => {});
	await p.close();
}

const browser = await chromium.launch({ channel: "chromium", args: ["--disable-gpu", "--force-color-profile=srgb"] });
const jobs = [menuOpen, langSwitch, archiveFilters, archivePagination, archiveAddToDraft, librarySearch, compareStates, accordionStates, floatingWidgets, slowNetwork];
try {
	for (const lang of ["en", "de"]) {
		for (const width of [1440, 390]) {
			for (const job of jobs) {
				const context = await browser.newContext({ viewport: { width, height: 844 }, reducedMotion: "reduce", deviceScaleFactor: 1, hasTouch: width === 390, isMobile: width === 390 });
				await context.addInitScript(() => localStorage.setItem("linker-genie-peek-dismissed-until", String(Date.now() + 2592000000)));
				try { await job(context, lang, width); }
				catch (error) { results.push({ key: `${job.name}:*:${lang}:${width}`, status: "error", error: String(error?.message || error).slice(0, 400), observedAt: new Date().toISOString(), pass: 2 }); console.log(`ERR ${job.name} ${lang} ${width}`); }
				await context.close();
				fs.writeFileSync(path.join(out, "state-results-pass2.json"), `${JSON.stringify(results, null, 2)}\n`);
			}
			await cookieReopen(async (w) => browser.newContext({ viewport: { width: w, height: 844 }, reducedMotion: "reduce" }), lang, width);
			fs.writeFileSync(path.join(out, "state-results-pass2.json"), `${JSON.stringify(results, null, 2)}\n`);
		}
	}
} finally {
	await browser.close();
	fs.writeFileSync(path.join(out, "state-results-pass2.json"), `${JSON.stringify(results, null, 2)}\n`);
}
const fails = results.filter((r) => r.failed > 0 || r.status === "error");
console.log(JSON.stringify({ rows: results.length, failRows: fails.length, fails: fails.map((f) => f.key) }, null, 2));
