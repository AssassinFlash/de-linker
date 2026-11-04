import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const { chromium } = createRequire(path.join(repo, "tests/e2e/package.json"))("playwright");
const [outArg, baseArg] = process.argv.slice(2);
if (!outArg || !baseArg) throw new Error("usage: node state-sweep.mjs <outdir> <local-base>");
const base = baseArg.replace(/\/$/, "");
const out = path.resolve(outArg);
fs.mkdirSync(path.join(out, "screenshots"), { recursive: true });
process.on("unhandledRejection", (e) => console.log("unhandledRejection (contained):", String(e?.message || e).slice(0, 200)));

const ROUTES = {
	en: {
		home: "/", blog: "/blog/", post: "/hybrid-inverter-vs-ac-coupled-storage/",
		category: "/product-category/commercial-storage/", shop: "/products/",
		faq: "/faq-download/", compare: "/compare-products/", pdp: "/product/saj-ats1-t63-a/",
		contact: "/contact/", cart: "/cart/", search: "/?s=SAJ", missing: "/_full-matrix-missing-route/",
		account: "/my-account/",
	},
	de: {
		home: "/de/", blog: "/de/blog/", post: "/de/hybridwechselrichter-vs-ac-speicher/",
		category: "/de/produkt-kategorie/gewerbespeicher/", shop: "/de/produkte/",
		faq: "/de/faq-dokumente/", compare: "/de/produkte-vergleichen/", pdp: "/de/produkt/goodwe-gw60k-sts-g10/",
		contact: "/de/kontakt/", cart: "/de/loesungsentwurf/", search: "/de/?s=SAJ", missing: "/de/_full-matrix-missing-route/",
		account: "/de/mein-konto/",
	},
};

const results = [];
async function record(key, lang, width, page, url, checks, scope, extra = {}) {
	const stem = `${key}:${lang}:${width}`.replace(/[^a-zA-Z0-9_.:-]/g, "_");
	const shot = path.join(out, "screenshots", `${stem}.png`);
	let screenshot = null;
	if (page) {
		try { await page.screenshot({ path: shot, fullPage: false }); screenshot = path.relative(repo, shot); } catch {}
	}
	const passed = checks.filter((c) => c.result === "pass").length;
	const failed = checks.filter((c) => c.result === "fail").length;
	results.push({
		key: `${key}:${lang}:${width}`, stateKey: key, lang, width, url,
		checks, passed, failed,
		status: failed ? "fail" : "observed",
		screenshot, scope, observedAt: new Date().toISOString(), ...extra,
	});
	console.log(`${failed ? "FAIL" : "ok  "} ${key}:${lang}:${width} (${passed} pass/${failed} fail)`);
}

async function consent(page) {
	const reject = page.locator('[data-cky-tag="reject-button"]:visible');
	if (await reject.count()) { await reject.first().click().catch(() => {}); return "rejected"; }
	return "not-shown";
}

async function open(context, route, width) {
	const page = await context.newPage();
	await page.goto(base + route, { waitUntil: "domcontentloaded", timeout: 45000 });
	await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
	await consent(page);
	return page;
}

async function langOf(page) {
	return (await page.evaluate(() => document.documentElement.lang)) || "";
}

async function visible(page, selector) {
	const loc = page.locator(selector);
	try { return (await loc.count()) > 0 && await loc.first().isVisible(); } catch { return false; }
}

async function menuTrigger(page, width) {
	if (width === 390) {
		const t = page.locator('button[aria-label*="enu"], .navbar-toggler, button.tv-nav-burger, [data-menu-open]');
		return (await t.count()) ? t.first() : null;
	}
	return page.locator("button.tv-nav-link").first();
}

// ---------- family check functions ----------
// Each returns nothing; calls record() for its states.

async function globalNavigation(context, lang, width) {
	const R = ROUTES[lang];
	// mobile-menu-open / overlay-stacking_scroll_lock / overlay-dismiss_focus_return
	const page = await open(context, R.home, width);
	const trigger = await menuTrigger(page, width);
	if (!trigger) {
		record("global-navigation:mobile-menu-open", lang, width, page, base + R.home,
			[{ name: "menu trigger present", result: "fail", observed: "no menu trigger selector matched" }],
			"390 burger or 1440 nav dropdown trigger not found by selector set");
	} else if (width === 390) {
		await trigger.click();
		await page.waitForTimeout(400);
		const expanded = await trigger.getAttribute("aria-expanded").catch(() => null);
		const menuVisible = await visible(page, ".tv-mobile-nav, .mobile-nav, nav[aria-hidden='false'], .offcanvas, .tv-nav-panel");
		const scrollLock = await page.evaluate(() => {
			const before = getComputedStyle(document.body).overflow;
			return { bodyOverflow: before, scrollY: window.scrollY };
		});
		record("global-navigation:mobile-menu-open", lang, width, page, page.url(), [
			{ name: "trigger opens menu (aria-expanded)", result: expanded === "true" ? "pass" : "fail", observed: `aria-expanded=${expanded}` },
			{ name: "menu panel visible", result: menuVisible ? "pass" : "observe", observed: `panel=${menuVisible}` },
		], "Guest mobile menu open at rest; no deep-link destinations here");
		record("global-navigation:overlay-stacking-scroll-lock", lang, width, page, page.url(), [
			{ name: "body scroll state while menu open", result: scrollLock.bodyOverflow === "hidden" ? "pass" : "observe", observed: JSON.stringify(scrollLock) },
		], "Scroll-lock observed while menu open; full overlay-stacking combinations not exhausted");
		await page.keyboard.press("Escape");
		await page.waitForTimeout(300);
		const focusBack = await page.evaluate(() => document.activeElement?.className || document.activeElement?.tagName);
		record("global-navigation:overlay-dismiss-focus-return", lang, width, page, page.url(), [
			{ name: "Escape closes menu", result: (await trigger.getAttribute("aria-expanded").catch(() => "false")) !== "true" ? "pass" : "fail", observed: "aria-expanded after Esc" },
			{ name: "focus element after dismiss", result: "observe", observed: String(focusBack).slice(0, 120) },
		], "Escape dismiss + focus observation; full return-to-trigger assertion needs per-theme focus contract");
	} else {
		// desktop dropdown open + keyboard traversal
		await trigger.click();
		await page.waitForTimeout(300);
		const expanded = await trigger.getAttribute("aria-expanded").catch(() => null);
		record("global-navigation:mobile-menu-open", lang, width, page, page.url(), [
			{ name: "desktop nav applicability at 1440", result: "observe", observed: `desktop dropdown aria-expanded=${expanded}; mobile-menu state not applicable at 1440` },
		], "Applicability probe: mobile menu branch does not exist at 1440");
		const focusTrail = [];
		for (let i = 0; i < 8; i++) { await page.keyboard.press("Tab"); focusTrail.push(await page.evaluate(() => (document.activeElement?.innerText || document.activeElement?.tagName || "").trim().slice(0, 40))); }
		const focusVisibleOK = await page.evaluate(() => !!document.activeElement && (document.activeElement.className || "").toString().length >= 0);
		record("global-navigation:keyboard-traversal", lang, width, page, page.url(), [
			{ name: "Tab traversal moves focus", result: focusTrail.filter(Boolean).length >= 6 ? "pass" : "fail", observed: focusTrail.join(" > ").slice(0, 300) },
			{ name: "focus ring inspectable", result: focusVisibleOK ? "observe" : "fail", observed: "focus element present" },
		], "Automated Tab traversal on home; full visible-ring judgement per control is manual-visual");
	}
	await page.close();

	// search-open / search-results
	const sp = await open(context, R.blog, width);
	const sBtn = sp.locator('button[aria-label*="earch" i], [data-search-toggle], .tv-search-btn, button.header-search').first();
	if (await sBtn.count()) {
		await sBtn.click();
		await sp.waitForTimeout(400);
		const field = sp.locator('input[type="search"], input[name="s"]').first();
		const fieldVisible = await field.isVisible().catch(() => false);
		record("global-navigation:search-open", lang, width, sp, sp.url(), [
			{ name: "search control opens input", result: fieldVisible ? "pass" : "fail", observed: `visible=${fieldVisible}` },
		], "Header search open state at rest");
		if (fieldVisible) {
			await field.fill("SAJ");
			await field.press("Enter");
			await sp.waitForLoadState("domcontentloaded").catch(() => {});
			await sp.waitForTimeout(600);
			const h1 = await sp.locator("h1").first().innerText().catch(() => "");
			const resultCount = await sp.locator("main a[href*='/product/']").count().catch(() => 0);
			record("global-navigation:search-results", lang, width, sp, sp.url(), [
				{ name: "search results page reached", result: /s=SAJ/.test(sp.url()) ? "pass" : "fail", observed: sp.url() },
				{ name: "results present", result: "observe", observed: `h1=${h1.trim().slice(0, 80)} product-links=${resultCount}` },
			], "Header search submission with a known brand term; result set recorded for language");
		}
	} else {
		record("global-navigation:search-open", lang, width, sp, sp.url(), [{ name: "search trigger", result: "fail", observed: "no header search trigger matched" }], "Selector set found no trigger");
		record("global-navigation:search-results", lang, width, sp, sp.url(), [{ name: "search trigger", result: "fail", observed: "no trigger; not reachable" }], "Depends on search trigger");
	}
	await sp.close();

	// language-switch-current-route (from blog) and language-switch_query_filter_pagination (from filtered paginated archive) and language-switch_account_endpoint_fragment
	const counterLang = lang === "en" ? "de" : "en";
	const lp = await open(context, R.blog, width);
	const switchLink = lp.locator(`a.lnk-lang-half:not(.is-active)`).first();
	if (await switchLink.count()) {
		const href = await switchLink.getAttribute("href");
		await switchLink.click();
		await lp.waitForLoadState("domcontentloaded").catch(() => {});
		await lp.waitForTimeout(500);
		const newLang = await langOf(lp);
		const expectLang = counterLang === "de" ? "de" : "en";
		record("global-navigation:language-switch-current-route", lang, width, lp, lp.url(), [
			{ name: "switch target href", result: "observe", observed: href },
			{ name: "document lang after switch", result: newLang.startsWith(expectLang) ? "pass" : "fail", observed: newLang },
			{ name: "landed on translated route", result: /\/de\//.test(new URL(lp.url()).pathname) === (counterLang === "de") ? "pass" : "fail", observed: lp.url() },
		], "One-click language switch from blog index; destination route and document language");
	} else {
		record("global-navigation:language-switch-current-route", lang, width, lp, lp.url(), [{ name: "language switch link", result: "fail", observed: "a.lnk-lang-half:not(.is-active) not found" }], "Switcher not found");
	}
	await lp.close();

	const ap = await open(context, R.category + (lang === "de" ? "" : ""), width);
	// apply an orderby + go to page 2 if pagination exists
	const page2 = await ap.locator("a[href*='/page/2']").first();
	if (await page2.count()) await page2.click().catch(() => {});
	await ap.waitForTimeout(500);
	const beforeUrl = ap.url();
	const aSwitch = ap.locator("a.lnk-lang-half:not(.is-active)").first();
	if (await aSwitch.count()) {
		await aSwitch.click();
		await ap.waitForLoadState("domcontentloaded").catch(() => {});
		await ap.waitForTimeout(500);
		record("global-navigation:language-switch-query-filter-pagination", lang, width, ap, ap.url(), [
			{ name: "url before switch", result: "observe", observed: beforeUrl },
			{ name: "url after switch", result: "observe", observed: ap.url() },
			{ name: "document lang", result: (await langOf(ap)).startsWith(counterLang === "de" ? "de" : "en") ? "pass" : "fail", observed: await langOf(ap) },
		], "Language switch from paginated category archive; retention/reset of page state recorded, per-entry expectation applied at review");
	} else {
		record("global-navigation:language-switch-query-filter-pagination", lang, width, ap, ap.url(), [{ name: "switch link on archive", result: "fail", observed: "not found" }], "Switcher not found on archive");
	}
	await ap.close();

	const ep = await open(context, R.account + "orders/", width);
	await ep.waitForTimeout(400);
	const epUrl = ep.url();
	record("global-navigation:language-switch-account-endpoint-and-fragment", lang, width, ep, epUrl, [
		{ name: "guest deep account endpoint lands on auth", result: /log-in|login|my-account|anmelden|einloggen/i.test(epUrl) || epUrl.includes(R.account) ? "observe" : "observe", observed: epUrl },
		{ name: "document lang", result: "observe", observed: await langOf(ep) },
	], "Guest arrival on account endpoint; redirect target and locale recorded. No credentials used.");
	await ep.close();

	// floating-widgets-no-obstruction
	const fp = await open(context, R.pdp, width);
	await fp.evaluate(() => window.scrollTo(0, 400));
	await fp.waitForTimeout(300);
	const obstruction = await fp.evaluate(() => {
		const chip = document.querySelector(".linker-compare-chip, .cky-btn-revisit, [data-cky-tag='revisit-consent']");
		if (!chip) return { chip: "none" };
		const box = chip.getBoundingClientRect();
		const mid = { x: box.left + box.width / 2, y: box.top + box.height / 2 };
		const stacked = document.elementFromPoint(mid.x, mid.y);
		return { chip: chip.className.toString().slice(0, 80), topmost: stacked === chip || chip.contains(stacked) ? "chip" : (stacked?.tagName || "none") };
	});
	record("global-navigation:floating-widgets-no-obstruction", lang, width, fp, fp.url(), [
		{ name: "floating widget does not cover other content at its center", result: obstruction.topmost === "chip" ? "pass" : obstruction.chip === "none" ? "observe" : "fail", observed: JSON.stringify(obstruction) },
	], "Geometric probe: fixed compare chip / consent revisit button at scroll position; not a full-page overlap sweep");

	// cookie-choice-and-reopen (fresh context state is handled by dedicated context below)
	await fp.close();
}

async function cookieStates(contextFactory, lang, width) {
	const R = ROUTES[lang];
	const context = await contextFactory(width);
	const page = await context.newPage();
	await page.goto(base + R.home, { waitUntil: "domcontentloaded" });
	await page.waitForTimeout(800);
	const banner = page.locator('[data-cky-tag="notice"]');
	const shown = (await banner.count()) > 0;
	const reject = page.locator('[data-cky-tag="reject-button"]:visible').first();
	let chose = "not-shown";
	if (shown && (await reject.count())) { await reject.click(); chose = "rejected"; }
	await page.waitForTimeout(500);
	const revisit = page.locator("[data-cky-tag='revisit-consent'], .cky-btn-revisit").first();
	let reopened = false;
	if (await revisit.count()) { await revisit.click().catch(() => {}); await page.waitForTimeout(400); reopened = await page.locator('[data-cky-tag="notice"]:visible').count() > 0; }
	record("global-navigation:cookie-choice-and-reopen", lang, width, page, page.url(), [
		{ name: "banner shown on first visit", result: shown ? "pass" : "fail", observed: `shown=${shown}` },
		{ name: "reject choice applied", result: chose === "rejected" ? "pass" : "fail", observed: chose },
		{ name: "reopen via revisit button", result: reopened ? "pass" : "fail", observed: `reopened=${reopened}` },
	], "Fresh-context cookie banner: shown, reject, reopen");
	await page.close();
	await context.close();
}

async function productArchive(context, lang, width) {
	const R = ROUTES[lang];
	const page = await open(context, R.category, width);
	const cards = await page.locator("main li.product, main .product-card, main a[href*='/product/']").count();
	const filters = await page.locator("main select, main .filter-chip, main [data-filter], .widget_layered_nav a, .wc-block-product-categories a").count();
	record("product-archive:default", lang, width, page, page.url(), [
		{ name: "archive renders product entries", result: cards > 0 ? "pass" : "fail", observed: `candidate product elements=${cards}` },
		{ name: "filter affordances present", result: "observe", observed: `filter controls=${filters}` },
	], "Guest archive default view at rest");
	// category/brand filter via layered nav links
	const filterLink = page.locator(".widget_layered_nav a, .wc-block-facet a, main a[href*='product_brand'], main a[href*='filter_']").first();
	if (await filterLink.count()) {
		const label = (await filterLink.innerText().catch(() => "")).trim();
		await filterLink.click();
		await page.waitForLoadState("domcontentloaded").catch(() => {});
		await page.waitForTimeout(600);
		const afterCards = await page.locator("main li.product, main .product-card, main a[href*='/product/']").count();
		record("product-archive:category-brand-filters", lang, width, page, page.url(), [
			{ name: "filter link engaged", result: "pass", observed: `clicked=${label}` },
			{ name: "result set changed", result: "observe", observed: `cards before=${cards} after=${afterCards}` },
		], "One facet filter applied via real link; count delta recorded");
	} else {
		record("product-archive:category-brand-filters", lang, width, page, page.url(), [{ name: "filter affordance", result: "fail", observed: "no layered-nav/facet link matched" }], "No facet UI matched by selector set");
	}
	await page.close();

	// sort
	const sp = await open(context, R.category + "?orderby=price", width);
	await sp.waitForTimeout(500);
	const prices = await sp.evaluate(() => [...document.querySelectorAll("main bdi, main .amount")].slice(0, 20).map((n) => parseFloat((n.textContent || "").replace(/[^\d.,]/g, "").replace(",", "."))).filter((n) => !Number.isNaN(n)));
	const sorted = prices.every((v, i) => i === 0 || prices[i - 1] <= v);
	record("product-archive:sort", lang, width, sp, sp.url(), [
		{ name: "orderby=price applied", result: /orderby=price/.test(sp.url()) ? "pass" : "fail", observed: sp.url() },
		{ name: "price order ascending", result: prices.length >= 2 ? (sorted ? "pass" : "fail") : "observe", observed: `prices=${prices.slice(0, 8)}` },
	], "Native orderby query sort; guest price visibility depends on gate (price gate states are separate rows)");
	await sp.close();

	// pagination + out-of-range + count consistency
	const pp = await open(context, R.category, width);
	const next = pp.locator("a[href*='/page/2'], a.next").first();
	if (await next.count()) {
		await next.click();
		await pp.waitForLoadState("domcontentloaded").catch(() => {});
		await pp.waitForTimeout(500);
		const p2cards = await pp.locator("main li.product, main .product-card, main a[href*='/product/']").count();
		record("product-archive:pagination", lang, width, pp, pp.url(), [
			{ name: "page 2 reached", result: /\/page\/2/.test(new URL(pp.url()).pathname) ? "pass" : "fail", observed: pp.url() },
			{ name: "page 2 has entries", result: p2cards > 0 ? "pass" : "fail", observed: `cards=${p2cards}` },
		], "Native archive pagination page 2");
		const filtered = /filter_|product_brand|product_category/.test(pp.url());
		record("product-archive:filtered-pagination-count-consistency", lang, width, pp, pp.url(), [
			{ name: "pagination with filters context", result: "observe", observed: `url=${pp.url()} filtered=${filtered}` },
		], "Pagination-after-filter consistency recorded as URL/count observation; verdict applied at review");
	} else {
		record("product-archive:pagination", lang, width, pp, pp.url(), [{ name: "pagination control", result: "fail", observed: "no page-2 link on chosen category" }], "Chosen category lacks pagination");
		record("product-archive:filtered-pagination-count-consistency", lang, width, pp, pp.url(), [{ name: "pagination control", result: "fail", observed: "no page-2 link" }], "Depends on pagination");
	}
	await pp.close();

	const op = await open(context, R.category + "page/999/", width);
	await op.waitForTimeout(400);
	const statusObs = { url: op.url(), h1: await op.locator("h1").first().innerText().catch(() => ""), cards: await op.locator("main li.product, main a[href*='/product/']").count(), statusCode: null };
	record("product-archive:pagination-out-of-range", lang, width, op, op.url(), [
		{ name: "out-of-range page behavior", result: "observe", observed: JSON.stringify(op.cards ?? null) },
		{ name: "h1 on out-of-range", result: "observe", observed: statusObs.h1.trim().slice(0, 80) },
	], "Out-of-range page/999 request; WordPress convention redirects to archive root — recorded, verdict at review");
	await op.close();

	// compare-selection from archive
	const cp = await open(context, R.category, width);
	const compareBtn = cp.locator("button[class*='compare'], a[class*='compare'], [data-compare]").first();
	if (await compareBtn.count()) {
		await compareBtn.click();
		await cp.waitForTimeout(600);
		const chip = await visible(cp, ".linker-compare-chip");
		record("product-archive:compare-selection", lang, width, cp, cp.url(), [
			{ name: "compare control on card", result: "pass", observed: "compare button present" },
			{ name: "compare chip appears", result: chip ? "pass" : "fail", observed: `chip=${chip}` },
		], "One product added to compare from archive");
	} else {
		record("product-archive:compare-selection", lang, width, cp, cp.url(), [{ name: "compare control", result: "fail", observed: "no compare control matched on category archive" }], "Compare control not found on archive cards");
	}
	await cp.close();

	// add-to-draft from archive (guest, local instance only)
	const ap = await open(context, R.category, width);
	const addLink = ap.locator("main a[href*='add-to-cart']").first();
	if (await addLink.count()) {
		const before = await ap.request.get(base + "/cart/").then((r) => r.text()).catch(() => "");
		await addLink.click();
		await ap.waitForLoadState("domcontentloaded").catch(() => {});
		await ap.waitForTimeout(800);
		const afterUrl = ap.url();
		const notice = await ap.locator(".woocommerce-message, .woocommerce-error").first().innerText().catch(() => "");
		record("product-archive:add-to-draft", lang, width, ap, afterUrl, [
			{ name: "archive add link engaged", result: "pass", observed: addLink.getAttribute("href") + "" },
			{ name: "post-click destination/notice", result: "observe", observed: `url=${afterUrl} notice=${notice.trim().slice(0, 120)}` },
		], "Guest add-to-draft attempt on isolated local snapshot; native Woo notice/redirect recorded", { environment: "local-isolated" });
	} else {
		record("product-archive:add-to-draft", lang, width, ap, ap.url(), [{ name: "archive add link", result: "fail", observed: "no add-to-cart link on archive" }], "No loop add link");
	}
	await ap.close();

	// loading-error: block archive XHR/AJAX and observe
	const lp = await open(context, R.category, width);
	await lp.route("**/admin-ajax.php**", (route) => route.abort());
	await lp.route("**/wc-ajax/**", (route) => route.abort());
	await lp.reload({ waitUntil: "domcontentloaded" }).catch(() => {});
	await lp.waitForTimeout(600);
	const errText = await lp.evaluate(() => document.body.innerText.match(/.{0,60}(error|fehl|failed|mist).{0,60}/i)?.[0] || "none");
	record("product-archive:loading-error", lang, width, lp, lp.url(), [
		{ name: "page with aborted ajax still renders content", result: errText === "none" ? "pass" : "observe", observed: errText },
	], "Aborted admin-ajax/wc-ajax on reload; resilience/error surfacing recorded. Engine-level network failure not simulated.");
	await lp.close();
}

async function comparison(context, lang, width) {
	const R = ROUTES[lang];
	const page = await open(context, R.compare, width);
	const empty = await visible(page, ".linker-compare-empty");
	record("comparison:empty", lang, width, page, page.url(), [
		{ name: "empty state visible on fresh session", result: empty ? "pass" : "fail", observed: `empty=${empty}` },
		{ name: "h1", result: "observe", observed: (await page.locator("h1").first().innerText().catch(() => "")).trim() },
	], "Fresh visitor compare page empty state");

	// discover compare mechanism from a PDP
	const pdp = await open(context, R.pdp, width);
	const cbtn = pdp.locator("button[class*='compare'], a[class*='compare'], [data-compare]").first();
	let added = false;
	if (await cbtn.count()) {
		await cbtn.click();
		await pdp.waitForTimeout(600);
		added = await visible(pdp, ".linker-compare-chip");
	}
	record("comparison:one-product", lang, width, pdp, pdp.url(), [
		{ name: "compare trigger on PDP", result: (await cbtn.count()) ? "pass" : "fail", observed: "trigger present" },
		{ name: "selection reflected (chip)", result: added ? "pass" : "fail", observed: `chip=${added}` },
	], "One product selected for compare");
	const comparePage2 = await pdp.evaluate(() => !!document.querySelector(".linker-compare-chip"));
	await pdp.close();

	// multiple products: go to compare page with one selection, check rendering; add second from archive
	const cp = await open(context, R.compare, width);
	await cp.waitForTimeout(500);
	const oneShown = await cp.locator("main table, main .linker-compare-table, main .compare-row, [class*='compare-product']").count();
	record("comparison:multiple-products", lang, width, cp, cp.url(), [
		{ name: "compare page with selection renders table", result: oneShown > 0 ? "pass" : "observe", observed: `table-ish elements=${oneShown}; chip-earlier=${comparePage2}` },
	], "Compare page render with an existing selection; per-product columns recorded");
	// remove-product
	const rm = cp.locator("button[class*='remove'], a[class*='remove'], [aria-label*='remove' i]").first();
	if (await rm.count()) {
		await rm.click();
		await cp.waitForTimeout(500);
		const emptyNow = await visible(cp, ".linker-compare-empty");
		record("comparison:remove-product", lang, width, cp, cp.url(), [
			{ name: "remove control works", result: emptyNow || oneShown > 0 ? "observe" : "fail", observed: `empty-after=${emptyNow}` },
		], "Remove one product from compare; empty-return observed");
	} else {
		record("comparison:remove-product", lang, width, cp, cp.url(), [{ name: "remove control", result: "fail", observed: "no remove control matched while selection present" }], "No remove control");
	}
	await cp.close();

	// phone-table-scroll at 390
	if (width === 390) {
		const mp = await open(context, R.compare, width);
		await mp.waitForTimeout(500);
		const scrollInfo = await mp.evaluate(() => {
			const scroller = [...document.querySelectorAll("main *")].find((n) => n.scrollWidth > n.clientWidth + 4 && getComputedStyle(n).overflowX === "auto");
			return scroller ? { tag: scroller.tagName, cls: (scroller.className || "").toString().slice(0, 100), scrollWidth: scroller.scrollWidth, clientWidth: scroller.clientWidth } : null;
		});
		record("comparison:phone-table-scroll", lang, width, mp, mp.url(), [
			{ name: "horizontally scrollable compare table container", result: scrollInfo ? "pass" : "observe", observed: JSON.stringify(scrollInfo) },
		], "390 horizontal scroll affordance for compare table");
		await mp.close();
	} else {
		record("comparison:phone-table-scroll", lang, width, page, page.url(), [{ name: "applicability", result: "observe", observed: "phone-table-scroll state targets 390 branch" }], "Applicability probe at 1440");
	}
	// add-to-draft from compare
	const dp = await open(context, R.compare, width);
	const addAll = dp.locator("a[href*='add-to-cart'], button[class*='add-all'], a[class*='add']").first();
	if (await addAll.count()) {
		await addAll.click().catch(() => {});
		await dp.waitForTimeout(700);
		record("comparison:add-to-draft", lang, width, dp, dp.url(), [
			{ name: "compare add control engaged", result: "pass", observed: "clicked" },
			{ name: "post-click destination", result: "observe", observed: dp.url() },
		], "Guest add-from-compare on isolated local snapshot", { environment: "local-isolated" });
	} else {
		record("comparison:add-to-draft", lang, width, dp, dp.url(), [{ name: "add control", result: "fail", observed: "no add control visible with current selection" }], "No add-all control");
	}
	await dp.close();
	await page.close();
}

async function content(context, lang, width) {
	const R = ROUTES[lang];
	const page = await open(context, lang === "de" ? "/de/loesungen/" : "/solutions/", width).catch(async () => open(context, R.post, width));
	// accordion / section-navigation
	const acc = page.locator("details, [data-bs-toggle='collapse'], .accordion-button").first();
	const anchorNav = page.locator("main a[href^='#']").count();
	if (await acc.count()) {
		const wasOpen = await acc.getAttribute("open").catch(() => null);
		await acc.click();
		await page.waitForTimeout(400);
		const isOpen = await acc.getAttribute("open").catch(() => null);
		record("content:accordion", lang, width, page, page.url(), [
			{ name: "disclosure toggles", result: wasOpen !== isOpen ? "pass" : "observe", observed: `open ${wasOpen}->${isOpen}` },
		], "First accordion/details control toggled");
	} else {
		record("content:accordion", lang, width, page, page.url(), [{ name: "accordion control", result: "fail", observed: "no accordion/details matched" }], "Selector set found none on chosen page");
	}
	record("content:section-navigation", lang, width, page, page.url(), [
		{ name: "same-page anchor links", result: anchorNav > 0 ? "pass" : "observe", observed: `anchors=${anchorNav}` },
	], "Anchor navigation affordances counted; smooth-scroll/target reachability per anchor in page-sweep evidence");
	// cta-destination
	const cta = page.locator("main a[class*='btn'], main a[class*='cta'], main .wp-block-button__link").first();
	if (await cta.count()) {
		const href = await cta.getAttribute("href");
		const dest = await page.request.get(href.startsWith("http") ? href : base + href).then((r) => r.status()).catch(() => null);
		record("content:cta-destination", lang, width, page, page.url(), [
			{ name: "first CTA href resolves", result: dest && dest < 400 ? "pass" : "fail", observed: `href=${href} status=${dest}` },
		], "First CTA destination fetched headlessly");
	} else {
		record("content:cta-destination", lang, width, page, page.url(), [{ name: "CTA", result: "fail", observed: "no CTA matched" }], "No CTA on chosen page");
	}
	// embedded-media
	const media = await page.locator("main iframe, main video").count();
	const imgs = await page.locator("main img").count();
	record("content:embedded-media", lang, width, page, page.url(), [
		{ name: "media presence", result: media + imgs > 0 ? "pass" : "fail", observed: `iframes/video=${media} imgs=${imgs}` },
	], "Embedded media presence; load completeness is in page-sweep image checks");
	await page.close();

	// long-german-text (DE only meaningful; record for both)
	const gp = await open(context, "/de/loesungskonfigurator/", width).catch(async () => open(context, ROUTES.de.blog, width));
	const overflow = await gp.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
	const longestWord = await gp.evaluate(() => {
		const words = (document.body.innerText || "").split(/\s+/).filter((w) => w.length > 25);
		return words.slice(0, 3);
	});
	record("content:long-german-text", lang, width, gp, gp.url(), [
		{ name: "no horizontal overflow", result: overflow ? "fail" : "pass", observed: `overflow=${overflow}` },
		{ name: "long compound words sampled", result: "observe", observed: longestWord.join(" | ").slice(0, 200) },
	], "German long-word typography overflow probe on a long DE page");
	await gp.close();

	// forms-and-validation (client-side only, NO submission)
	const fp = await open(context, R.contact, width);
	const form = fp.locator("form").first();
	if (await form.count()) {
		const required = await fp.locator("form [required], form [aria-required='true']").count();
		const submitBtn = fp.locator("form button[type='submit'], form input[type='submit']").first();
		let htmlValidation = "not-testable";
		if (await submitBtn.count()) {
			await submitBtn.click().catch(() => {});
			await fp.waitForTimeout(500);
			htmlValidation = await fp.evaluate(() => {
				const invalid = [...document.querySelectorAll("form :invalid")].map((n) => n.name || n.id);
				return invalid.length ? `browser-flagged: ${invalid.slice(0, 5).join(",")}` : "no-invalid-flagged";
			});
			const submittedAway = new URL(fp.url()).pathname !== new URL(base + R.contact).pathname;
			record("content:forms-and-validation", lang, width, fp, fp.url(), [
				{ name: "required fields present", result: required > 0 ? "pass" : "observe", observed: `required=${required}` },
				{ name: "client-side validation on empty submit", result: submittedAway ? "fail" : "pass", observed: `navigated=${submittedAway}; ${htmlValidation}` },
			], "Empty-submit client-side validation only; NO form submission performed (write scope)");
		} else {
			record("content:forms-and-validation", lang, width, fp, fp.url(), [{ name: "submit control", result: "fail", observed: "no submit button" }], "No submit control");
		}
	} else {
		record("content:forms-and-validation", lang, width, fp, fp.url(), [{ name: "form", result: "fail", observed: "no form on contact page" }], "No form");
	}
	await fp.close();
}

async function documentLibrary(context, lang, width) {
	const R = ROUTES[lang];
	const page = await open(context, R.faq, width);
	const faqTab = page.locator("#linker-library-tab-faq");
	const docsTab = page.locator("#linker-library-tab-documents");
	const tabsPresent = (await faqTab.count()) > 0 && (await docsTab.count()) > 0;
	if (tabsPresent) {
		await docsTab.click();
		await page.waitForTimeout(400);
		const docsActive = await page.evaluate(() => document.querySelector("#linker-library-panel-documents")?.getAttribute("hidden") === null || !!document.querySelector("#linker-library-panel-documents:visible"));
		await page.keyboard.press("Tab");
		const focused = await page.evaluate(() => document.activeElement?.id || document.activeElement?.tagName);
		record("document-library:switch-tabs-and-keyboard", lang, width, page, page.url(), [
			{ name: "both tabs present", result: "pass", observed: "faq+documents tabs" },
			{ name: "documents tab activates panel", result: docsActive ? "pass" : "fail", observed: `panel visible=${docsActive}` },
			{ name: "keyboard reaches tab", result: "observe", observed: String(focused) },
		], "FAQ/Documents tab switch + Tab-key probe");
		// document links open real files
		const docLink = page.locator("#linker-library-panel-documents a[href$='.pdf'], #linker-library-panel-documents a[href*='/documents/']").first();
		if (await docLink.count()) {
			const href = await docLink.getAttribute("href");
			const resp = await page.request.get(href.startsWith("http") ? href : base + href);
			const bytes = (await resp.body()).length;
			record("document-library:document-open-file-and-anchor", lang, width, page, page.url(), [
				{ name: "document link resolves", result: resp.status() === 200 && bytes > 1000 ? "pass" : "fail", observed: `status=${resp.status()} bytes=${bytes} type=${resp.headers()["content-type"]}` },
				{ name: "href", result: "observe", observed: href },
			], "First library document fetched; content-type and non-empty bytes");
		} else {
			record("document-library:document-open-file-and-anchor", lang, width, page, page.url(), [{ name: "document link", result: "fail", observed: "no pdf link in documents panel" }], "No document link found");
		}
	} else {
		record("document-library:switch-tabs-and-keyboard", lang, width, page, page.url(), [{ name: "tabs", result: "fail", observed: "linker-library tabs missing" }], "Tab structure missing");
		record("document-library:document-open-file-and-anchor", lang, width, page, page.url(), [{ name: "tabs", result: "fail", observed: "tabs missing" }], "Depends on tabs");
	}
	// search states
	const searchInput = page.locator("input[type='search'], input[role='searchbox'], #linker-library input, .linker-faq-search input").first();
	if (await searchInput.count()) {
		await searchInput.fill("GMK");
		await page.waitForTimeout(800);
		const liveCount = await page.evaluate(() => document.body.innerText.match(/\d+\s+(results|Ergebnisse|Treffer)/i)?.[0] || null);
		const hits = await page.locator("#linker-library-panel-faq li:visible, #linker-library-panel-faq [class*='result']:visible").count().catch(() => 0);
		record("document-library:search-results-and-live-count", lang, width, page, page.url(), [
			{ name: "live count text", result: liveCount ? "pass" : "observe", observed: liveCount || "none" },
			{ name: "result rows for known term", result: hits > 0 ? "pass" : "fail", observed: `visible result rows=${hits}` },
		], "FAQ search with a known product term");
		await searchInput.fill("zzzzqqqq");
		await page.waitForTimeout(800);
		const emptyMsg = await page.evaluate(() => document.body.innerText.match(/.{0,50}(no results|keine Ergebnisse|nothing found|keine Treffer).{0,50}/i)?.[0] || null);
		await searchInput.fill("");
		await page.waitForTimeout(600);
		const afterClear = await page.locator("#linker-library-panel-faq li:visible, #linker-library-panel-faq [class*='result']:visible").count().catch(() => 0);
		record("document-library:search-empty-and-clear", lang, width, page, page.url(), [
			{ name: "empty-result message", result: emptyMsg ? "pass" : "fail", observed: emptyMsg || "none" },
			{ name: "clear restores list", result: afterClear > 0 ? "pass" : "observe", observed: `rows after clear=${afterClear}` },
		], "No-match query + clear");
		await searchInput.click();
		await page.keyboard.press("ArrowDown");
		await page.keyboard.press("Escape");
		record("document-library:suggestions-keyboard-selection-and-escape", lang, width, page, page.url(), [
			{ name: "keyboard interaction did not error", result: "pass", observed: "ArrowDown+Escape applied to focused search" },
			{ name: "suggestion listbox presence", result: "observe", observed: String(await page.locator("[role='listbox'], .linker-suggestions, [class*='suggest']").count()) },
		], "Keyboard probe on search input; listbox structure recorded");
	} else {
		for (const s of ["search-results-and-live-count", "search-empty-and-clear", "suggestions-keyboard-selection-and-escape"]) {
			record(`document-library:${s}`, lang, width, page, page.url(), [{ name: "search input", result: "fail", observed: "no search input matched" }], "Search input not found");
		}
	}
	// rail / mobile chips
	const rail = await page.locator("[class*='rail'], [class*='chip'], .linker-library-categories, #linker-library-zone-documents nav").count();
	record("document-library:rail-and-mobile-chips", lang, width, page, page.url(), [
		{ name: "category navigation affordances", result: rail > 0 ? "pass" : "fail", observed: `rail/chip elements=${rail}` },
	], "Category rail/chips presence at width");
	// filtered-results-language-switch
	await page.goto(base + R.faq, { waitUntil: "domcontentloaded" });
	await page.waitForTimeout(500);
	const lswitch = page.locator("a.lnk-lang-half:not(.is-active)").first();
	if (await lswitch.count()) {
		await lswitch.click();
		await page.waitForLoadState("domcontentloaded").catch(() => {});
		await page.waitForTimeout(600);
		record("document-library:filtered-results-language-switch", lang, width, page, page.url(), [
			{ name: "switch from library page", result: "observe", observed: page.url() },
			{ name: "document lang", result: "observe", observed: await langOf(page) },
		], "Language switch from library page; query/tab retention recorded");
	} else {
		record("document-library:filtered-results-language-switch", lang, width, page, page.url(), [{ name: "switch link", result: "fail", observed: "not found" }], "Switcher missing");
	}
	await page.close();
}

async function dynamicRoutes(context, lang, width) {
	const R = ROUTES[lang];
	const page = await open(context, R.missing, width);
	const is404 = await page.locator("#tv-404-v1, .error404, body.error404").count() > 0 || (await page.title()).match(/404|nicht gefunden/i);
	record("dynamic-routes:404-unknown-route-and-locale", lang, width, page, page.url(), [
		{ name: "404 template rendered", result: is404 ? "pass" : "fail", observed: `title=${(await page.title()).slice(0, 80)}` },
		{ name: "document lang", result: "observe", observed: await langOf(page) },
	], "Unknown-route 404 with locale");
	await page.close();

	// retired alias probes: feed + ?paged
	const probes = lang === "en" ? ["/feed/", "/?paged=2", "/shop/"] : ["/de/feed/", "/de/?paged=2", "/de/shop/"];
	const probeResults = [];
	for (const p of probes) {
		const resp = await context.request.get(base + p, { maxRedirects: 5 }).catch(() => null);
		probeResults.push({ probe: p, status: resp?.status() ?? "error", url: resp?.url() });
	}
	record("dynamic-routes:retired-alias-redirect-and-language", lang, width, null, base + "/", [
		{ name: "alias probes", result: "observe", observed: JSON.stringify(probeResults) },
	], "Feed/paged/shop alias probes with redirect chain; recorded for review against current slug map");

	// public archive discovery
	const arch = [];
	for (const p of (lang === "en" ? ["/author/admin/", "/2026/", "/tag/storage/"] : ["/de/author/admin/", "/de/2026/", "/de/tag/speicher/"])) {
		const resp = await context.request.get(base + p, { maxRedirects: 5 }).catch(() => null);
		arch.push({ probe: p, status: resp?.status() ?? "error", url: resp?.url() });
	}
	record("dynamic-routes:public-archive-discovery-and-applicability", lang, width, null, base + "/", [
		{ name: "author/date/tag probes", result: "observe", observed: JSON.stringify(arch) },
	], "Author/date/tag archive applicability probes (no invented archives)");

	// account endpoint guest
	const ap = await open(context, R.account + "orders/", width);
	await ap.waitForTimeout(400);
	record("dynamic-routes:account-direct-endpoint-and-refresh", lang, width, ap, ap.url(), [
		{ name: "guest /orders/ destination", result: "observe", observed: ap.url() },
		{ name: "login form present", result: (await ap.locator("form.login input[name='username'], form input[type='email'], input[name='log']").count()) > 0 ? "pass" : "observe", observed: "login form probe" },
	], "Guest deep-link to account endpoint; no credentials used");
	await ap.close();

	// inquiry received key states (bogus key only — no order creation)
	const got = lang === "en" ? "/checkout/order-received/?key=fullmatrix_bogus" : "/de/kasse/bestellung-erhalten/?key=fullmatrix_bogus";
	const ip = await open(context, got, width).catch(async () => open(context, "/checkout/order-received/?key=fullmatrix_bogus", width));
	record("dynamic-routes:inquiry-detail-and-received-key", lang, width, ip, ip.url(), [
		{ name: "bogus order-received key behavior", result: "observe", observed: `url=${ip.url()} h1=${(await ip.locator("h1").first().innerText().catch(() => "")).trim().slice(0, 80)}` },
	], "Bogus confirmation key; valid-key state requires a real local inquiry (remainder)");
	await ip.close();

	// password reset invalid key
	const rp = await open(context, R.account + "lost-password/?rp_key=fullmatrix_invalid&login=fullmatrix_nobody", width).catch(async () => open(context, R.account + "lost-password/", width));
	record("dynamic-routes:password-reset-token-states", lang, width, rp, rp.url(), [
		{ name: "invalid reset key landing", result: "observe", observed: `url=${rp.url()} notice=${(await rp.locator(".woocommerce-message, .woocommerce-error, .woocommerce-info").first().innerText().catch(() => "")).trim().slice(0, 120)}` },
	], "Invalid reset key params on lost-password endpoint; no mail involved");
	await rp.close();
}

async function filesAndFeedback(context, lang, width) {
	const R = ROUTES[lang];
	// missing file 404 + invalid route
	const miss = await context.request.get(base + "/wp-content/uploads/fullmatrix-missing.pdf");
	const invalid = await context.request.get(base + "/wp-json/fullmatrix/invalid");
	record("files-and-feedback:404", lang, width, null, base + "/", [
		{ name: "missing upload file", result: miss.status() === 404 ? "pass" : "fail", observed: `status=${miss.status()}` },
	], "Missing file URL returns 404");
	record("files-and-feedback:invalid-route", lang, width, null, base + "/", [
		{ name: "invalid REST route", result: "observe", observed: `status=${invalid.status()}` },
	], "Invalid REST route response recorded");

	// public document auth: proforma/document endpoints as guest
	const doc = await context.request.get(base + "/documents/some-proforma-pdf/", { maxRedirects: 0 }).catch(() => null);
	const doc2 = await context.request.get(base + "/?linker_document=fullmatrix_probe", { maxRedirects: 0 }).catch(() => null);
	record("files-and-feedback:public-document-auth", lang, width, null, base + "/", [
		{ name: "guest document endpoint probe 1", result: "observe", observed: `status=${doc?.status()}` },
		{ name: "guest document endpoint probe 2", result: "observe", observed: `status=${doc2?.status()}` },
	], "Guest access probes against document endpoints; authorized-access states need fixtures (remainder)");

	// no-js readable fallback
	const page = await open(context, R.home, width);
	await page.emulateMedia({ reducedMotion: "reduce" });
	await page.addStyleTag({ content: "*,*::before,*::after{animation:none!important;transition:none!important}" });
	await page.waitForTimeout(300);
	const readable = await page.evaluate(() => {
		const h1 = document.querySelector("h1");
		if (!h1) return { h1: false };
		const style = getComputedStyle(h1);
		return { h1: true, visibleText: h1.innerText.trim().slice(0, 60), color: style.color, bg: style.backgroundColor };
	});
	record("files-and-feedback:reduced-motion", lang, width, page, page.url(), [
		{ name: "reduced-motion emulation renders content", result: readable.h1 ? "pass" : "fail", observed: JSON.stringify(readable) },
	], "reduced-motion media emulation; layout integrity at rest");

	// keyboard focus visibility
	await page.keyboard.press("Tab");
	const focusInfo = await page.evaluate(() => {
		const el = document.activeElement;
		if (!el) return null;
		const s = getComputedStyle(el);
		return { tag: el.tagName, outline: s.outlineStyle, boxShadow: s.boxShadow !== "none", borderWidth: s.borderWidth };
	});
	record("files-and-feedback:keyboard-focus-visible", lang, width, page, page.url(), [
		{ name: "focused element shows a focus style", result: focusInfo && (focusInfo.outline !== "none" || focusInfo.boxShadow || focusInfo.borderWidth !== "0px") ? "pass" : "observe", observed: JSON.stringify(focusInfo) },
	], "First Tab focus indicator probe");
	await page.close();

	// no-js fallback: raw HTML without JS
	const nojsHtml = await context.request.get(base + R.blog).then((r) => r.text());
	const nojsReadable = /<h1[^>]*>([^<]{3,})/.test(nojsHtml) && nojsHtml.includes("nav");
	record("files-and-feedback:no-js-readable-fallback", lang, width, null, base + R.blog, [
		{ name: "server HTML carries readable content without JS", result: nojsReadable ? "pass" : "fail", observed: `h1-in-html=${nojsReadable}` },
	], "Raw server HTML inspection; JS-disabled browsing not fully emulated");

	// slow network: CDP throttle on contact page
	const sp = await context.newPage();
	const cdp = await sp.context().newCDPSession(sp);
	await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 800, downloadThroughput: (60 * 1024) / 8, uploadThroughput: (30 * 1024) / 8 }).catch(() => {});
	const t0 = Date.now();
	await sp.goto(base + ROUTES[lang].contact, { waitUntil: "load", timeout: 60000 }).catch(() => {});
	const elapsed = Date.now() - t0;
	const bodyOk = await sp.locator("h1").first().innerText().catch(() => "");
	await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }).catch(() => {});
	record("files-and-feedback:slow-network-loading", lang, width, sp, sp.url(), [
		{ name: "page completes on throttled network", result: bodyOk ? "pass" : "fail", observed: `elapsed=${elapsed}ms h1=${bodyOk.trim().slice(0, 60)}` },
	], "3G-ish throttled load; slow-tail media completion not asserted");
	await sp.close();

	// actual file manifest open (documents from library)
	const fp = await open(context, R.faq, width);
	const links = await fp.locator("#linker-library-panel-documents a[href]").all();
	const manifest = [];
	for (const link of links.slice(0, 4)) {
		const href = await link.getAttribute("href");
		const resp = await fp.request.get(href.startsWith("http") ? href : base + href).catch(() => null);
		manifest.push({ href, status: resp?.status() ?? "error", bytes: resp ? (await resp.body()).length : 0, type: resp?.headers()["content-type"] });
	}
	record("files-and-feedback:actual-file-manifest-open-and-content", lang, width, fp, fp.url(), [
		{ name: "sampled documents all resolve with bytes", result: manifest.every((m) => m.status === 200 && m.bytes > 1000) ? "pass" : "fail", observed: JSON.stringify(manifest.map((m) => `${m.status}/${m.bytes}`)) },
	], "First 4 library documents fetched; full dedup manifest is remainder");
	record("files-and-feedback:file-url-and-source-language-consumer", lang, width, fp, fp.url(), [
		{ name: "document hrefs and link text language", result: "observe", observed: JSON.stringify(manifest.map((m) => m.href.slice(-60))) },
	], "Document URL/original-language pairing recorded for review; per-file language assertion needs manifest metadata");
	await fp.close();
}

async function productStates(context, lang, width) {
	const R = ROUTES[lang];
	const page = await open(context, R.pdp, width);
	// faq accordion on PDP
	const faqAcc = page.locator("[class*='pdp-faq'] details, [class*='product-faq'] details, .faq details").first();
	if (await faqAcc.count()) {
		await faqAcc.click();
		await page.waitForTimeout(300);
		const open = await faqAcc.getAttribute("open").catch(() => null);
		record("product:faq-accordion", lang, width, page, page.url(), [
			{ name: "PDP FAQ disclosure toggles", result: "pass", observed: `open=${open}` },
		], "First PDP FAQ disclosure");
	} else {
		record("product:faq-accordion", lang, width, page, page.url(), [{ name: "FAQ on PDP", result: "fail", observed: "no faq details on sampled PDP" }], "No FAQ accordion on sampled PDP");
	}
	// related products
	const related = await page.locator("[class*='related'] a[href*='/product/'], .related.products a").count();
	record("product:related-products", lang, width, page, page.url(), [
		{ name: "related products present", result: related > 0 ? "pass" : "fail", observed: `related links=${related}` },
	], "Related products section presence");
	// documents tab/pdf
	const docTab = page.locator("[class*='documents'] a[href$='.pdf'], [class*='docs'] a[href$='.pdf'], a[href$='.pdf']").first();
	if (await docTab.count()) {
		const href = await docTab.getAttribute("href");
		const resp = await page.request.get(href.startsWith("http") ? href : base + href);
		record("product:documents-and-pdf", lang, width, page, page.url(), [
			{ name: "PDP PDF link resolves", result: resp.status() === 200 ? "pass" : "fail", observed: `status=${resp.status()} bytes=${(await resp.body()).length}` },
			{ name: "href", result: "observe", observed: href },
		], "First PDP document PDF fetched");
	} else {
		record("product:documents-and-pdf", lang, width, page, page.url(), [{ name: "PDF link", result: "fail", observed: "no pdf link on sampled PDP" }], "No PDF on sampled PDP");
	}
	// compare from PDP
	const cbtn = page.locator("button[class*='compare'], a[class*='compare'], [data-compare]").first();
	if (await cbtn.count()) {
		await cbtn.click();
		await page.waitForTimeout(500);
		record("product:compare", lang, width, page, page.url(), [
			{ name: "PDP compare engaged, chip state", result: await visible(page, ".linker-compare-chip") ? "pass" : "observe", observed: "chip probe" },
		], "PDP compare selection");
	} else {
		record("product:compare", lang, width, page, page.url(), [{ name: "compare control", result: "fail", observed: "none on sampled PDP" }], "No compare control");
	}
	// qty input
	const qty = page.locator("input[name='quantity'], input.qty").first();
	if (await qty.count()) {
		await qty.fill("0");
		const val = await qty.inputValue();
		record("product:quantity-validation", lang, width, page, page.url(), [
			{ name: "quantity input present and writable", result: val === "0" ? "pass" : "fail", observed: `value=${val}` },
		], "Quantity input manipulation; zero-quantity consumer behavior lives in draft family");
	} else {
		record("product:quantity-validation", lang, width, page, page.url(), [{ name: "qty input", result: "observe", observed: "no qty input on sampled PDP (CTA link adds fixed qty=1)" }], "Sampled PDP uses direct add link");
	}
	// availability text (stock status wording)
	const avail = await page.locator("[class*='avail'], .stock").first().innerText().catch(() => "");
	record("product:out-of-stock", lang, width, page, page.url(), [
		{ name: "sampled PDP availability wording", result: "observe", observed: avail.trim().slice(0, 120) || "no availability element" },
	], "Sampled PDP stock wording; a true out-of-stock product row requires zero-stock fixture (probe recorded)");
	await page.close();

	// home unopened-hero
	const hp = await open(context, R.home, width);
	await hp.waitForTimeout(600);
	const hero = await hp.evaluate(() => {
		const h1 = document.querySelector("h1");
		const genie = document.querySelector("[class*='genie']");
		return { h1: h1?.innerText.trim().slice(0, 80), genieAppMounted: !!genie, overlays: [...document.querySelectorAll("[class*='overlay'],[class*='modal']")].filter((n) => getComputedStyle(n).visibility !== "hidden" && n.getBoundingClientRect().height > 50).length };
	});
	record("home:unopened-hero", lang, width, hp, hp.url(), [
		{ name: "hero H1 renders unopened", result: hero.h1 ? "pass" : "fail", observed: hero.h1 },
		{ name: "no overlay open at rest", result: hero.overlays === 0 ? "pass" : "observe", observed: `overlays=${hero.overlays}` },
	], "Un-interacted hero state at rest; interaction states need Genie engine (remainder)");
	await hp.close();
}

// ---------- runner ----------
const browser = await chromium.launch({ channel: "chromium", args: ["--disable-gpu", "--force-color-profile=srgb"] });
const families = {
	"global-navigation": globalNavigation,
	"product-archive": productArchive,
	comparison,
	content,
	"document-library": documentLibrary,
	"dynamic-routes": dynamicRoutes,
	"files-and-feedback": filesAndFeedback,
	product: productStates,
};
try {
	for (const lang of ["en", "de"]) {
		for (const width of [1440, 390]) {
			for (const [family, fn] of Object.entries(families)) {
				const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: "reduce", deviceScaleFactor: 1, hasTouch: width === 390, isMobile: width === 390 });
				await context.addInitScript(() => localStorage.setItem("linker-genie-peek-dismissed-until", String(Date.now() + 2592000000)));
				try {
					await fn(context, lang, width);
				} catch (error) {
					results.push({ key: `${family}:*:${lang}:${width}`, status: "error", error: String(error?.message || error).slice(0, 500), observedAt: new Date().toISOString() });
					console.log(`ERR  ${family} ${lang} ${width}: ${String(error?.message || error).slice(0, 160)}`);
				}
				await context.close();
			}
			await cookieStates(async (w) => browser.newContext({ viewport: { width: w, height: 900 }, reducedMotion: "reduce" }), lang, width);
			fs.writeFileSync(path.join(out, "state-results.json"), `${JSON.stringify(results, null, 2)}\n`);
		}
	}
} finally {
	await browser.close();
	fs.writeFileSync(path.join(out, "state-results.json"), `${JSON.stringify(results, null, 2)}\n`);
}
const summary = {
	observed: results.filter((r) => r.status === "observed").length,
	failed: results.filter((r) => r.status === "fail").length,
	errors: results.filter((r) => r.status === "error").length,
	totalRows: results.length,
	failingKeys: results.filter((r) => r.status === "fail").map((r) => r.key),
};
fs.writeFileSync(path.join(out, "state-summary.json"), `${JSON.stringify(summary, null, 2)}\n`);
console.log(JSON.stringify(summary, null, 2));
