// Paired live|t112 full-page screenshots for the fresh-diff debt audit
// (2026-10-12). Same browser, same machine, identical viewport and wait
// protocol for both sides: fonts.ready + image decode + lazy-scroll walk +
// networkidle, no fixed sleeps. Read-only GET only.
//
//   node capture.mjs <out-dir> [filter-substring]
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-r2debt';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');

const out = process.argv[2];
const filter = process.argv[3] || '';
fs.mkdirSync(out, { recursive: true });

const LIVE = 'https://de-linker.com';
const T = 'http://127.0.0.1:8978';

// name -> { live, t112, width }
const PAIRS = [
	// 1. Homepage EN/DE x 1440/390
	{ name: 'home-en-1440', live: `${LIVE}/`, t112: `${T}/`, width: 1440 },
	{ name: 'home-en-390', live: `${LIVE}/`, t112: `${T}/`, width: 390 },
	{ name: 'home-de-1440', live: `${LIVE}/de/`, t112: `${T}/de/`, width: 1440 },
	{ name: 'home-de-390', live: `${LIVE}/de/`, t112: `${T}/de/`, width: 390 },
	// 2. Cart + checkout (guest, browse only) EN x 1440/390
	{ name: 'cart-en-1440', live: `${LIVE}/cart/`, t112: `${T}/cart/`, width: 1440 },
	{ name: 'cart-en-390', live: `${LIVE}/cart/`, t112: `${T}/cart/`, width: 390 },
	{ name: 'checkout-en-1440', live: `${LIVE}/proforma-request/`, t112: `${T}/proforma-request/`, width: 1440 },
	{ name: 'checkout-en-390', live: `${LIVE}/proforma-request/`, t112: `${T}/proforma-request/`, width: 390 },
	// 3. my-account logged out EN x 1440/390
	{ name: 'account-en-1440', live: `${LIVE}/my-account/`, t112: `${T}/my-account/`, width: 1440 },
	{ name: 'account-en-390', live: `${LIVE}/my-account/`, t112: `${T}/my-account/`, width: 390 },
	// 4. Static/marketing pages EN x 1440
	{ name: 'about-en-1440', live: `${LIVE}/about/`, t112: `${T}/about/`, width: 1440 },
	{ name: 'contact-en-1440', live: `${LIVE}/contact/`, t112: `${T}/contact/`, width: 1440 },
	{ name: 'installers-en-1440', live: `${LIVE}/for-installer/`, t112: `${T}/for-installer/`, width: 1440 },
	{ name: 'epc-en-1440', live: `${LIVE}/for-epc/`, t112: `${T}/for-epc/`, width: 1440 },
	{ name: 'services-en-1440', live: `${LIVE}/services-support/`, t112: `${T}/services-support/`, width: 1440 },
	{ name: 'faqdl-en-1440', live: `${LIVE}/faq-download/`, t112: `${T}/faq-download/`, width: 1440 },
	{ name: 'solution-en-1440', live: `${LIVE}/solution/`, t112: `${T}/solution/`, width: 1440 },
	// 5. Blog listing + single post EN x 1440
	{ name: 'bloglist-en-1440', live: `${LIVE}/blog/`, t112: `${T}/blog/`, width: 1440 },
	{ name: 'blogpost-en-1440', live: `${LIVE}/hybrid-inverter-vs-ac-coupled-storage/`, t112: `${T}/hybrid-inverter-vs-ac-coupled-storage/`, width: 1440 },
	// 6. Search results (PV) x 1440
	{ name: 'search-pv-en-1440', live: `${LIVE}/?s=PV`, t112: `${T}/?s=PV`, width: 1440 },
	// 7. 404 x 1440
	{ name: 'notfound-en-1440', live: `${LIVE}/audit-404-20261012/`, t112: `${T}/audit-404-20261012/`, width: 1440 },
	// 8. Compare x 1440
	{ name: 'compare-en-1440', live: `${LIVE}/compare-products/`, t112: `${T}/compare-products/`, width: 1440 },
	// 9. Known-debt spot checks (390 PDP purchase bar, shop family headers + search chips)
	{ name: 'pdp-en-390', live: `${LIVE}/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/`, t112: `${T}/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/`, width: 390 },
	{ name: 'products-en-1440', live: `${LIVE}/products/`, t112: `${T}/products/`, width: 1440 },
];

const NO_ANIM = '*, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; caret-color: transparent !important; }';

const COUNTS = `(() => {
	const q = (s) => document.querySelectorAll(s).length;
	return {
		url: location.href,
		lang: document.documentElement.lang,
		scrollWidth: document.documentElement.scrollWidth,
		scrollHeight: document.body.scrollHeight,
		a: q('a'), img: q('img'), form: q('form'), button: q('button'),
		h1: q('h1'), h2: q('h2'), h3: q('h3'),
		header: q('header'), footer: q('footer'), nav: q('nav'),
		li: q('li'), table: q('table'), input: q('input'), iframe: q('iframe'),
		wooNotices: q('.woocommerce-notices-wrapper, .woocommerce-message, .woocommerce-error, .woocommerce-info'),
		products: q('li.product, .products .product'),
		wpBlock: q('[class*="wp-block-"]'),
		lcCanvas: q('[class*="lc-"], [data-lc]'),
		formsCls: q('.wpcf7-form, form[class*="contact"], form[class*="inquiry"], form[class*="quote"]'),
	};
})()`;

const browser = await chromium.launch({ channel: 'chromium' });

async function shoot(url, file, width) {
	const context = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 } });
	const page = await context.newPage();
	const target = url.includes('?') ? `${url}&cbq=${Date.now()}` : `${url}?cbq=${Date.now()}`;
	await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 120_000 });
	await page.waitForLoadState('load', { timeout: 60_000 }).catch(() => {});
	await page.waitForLoadState('networkidle', { timeout: 20_000 }).catch(() => {});
	await page.addStyleTag({ content: NO_ANIM });
	// Fonts settled.
	await page.evaluate(async () => { await document.fonts.ready; });
	// Lazy images: walk the page so every lazy loader fires, then back to top.
	await page.evaluate(async () => {
		await new Promise((resolve) => {
			let y = 0;
			const step = () => {
				window.scrollTo(0, y);
				y += 600;
				if (y < document.body.scrollHeight + 600) requestAnimationFrame(step);
				else resolve();
			};
			step();
		});
		window.scrollTo(0, 0);
	});
	await page.waitForLoadState('networkidle', { timeout: 20_000 }).catch(() => {});
	// Every image decoded (or failed).
	await page.evaluate(async () => {
		await Promise.all(Array.from(document.images).map((img) => new Promise((res) => {
			if (img.complete && img.naturalWidth > 0) { img.decode().then(() => res(), () => res()); return; }
			const done = () => { img.decode().then(() => res(), () => res()); };
			img.addEventListener('load', done, { once: true });
			img.addEventListener('error', () => res(), { once: true });
		})));
	});
	await page.evaluate(async () => { await document.fonts.ready; });
	await page.screenshot({ path: file, fullPage: true, animations: 'disabled' });
	const counts = await page.evaluate(COUNTS);
	await context.close();
	return counts;
}

const summary = {};
for (const spec of PAIRS) {
	if (filter && !spec.name.includes(filter)) continue;
	const base = spec.name;
	const liveCounts = await shoot(spec.live, path.join(out, `${base}-live.png`), spec.width);
	const tCounts = await shoot(spec.t112, path.join(out, `${base}-t112.png`), spec.width);
	summary[base] = { live: liveCounts, t112: tCounts };
	fs.writeFileSync(path.join(out, 'dom-counts.json'), JSON.stringify(summary, null, 1));
	console.log(base, 'live', liveCounts.scrollHeight, 't112', tCounts.scrollHeight,
		'| a', liveCounts.a, '/', tCounts.a, '| img', liveCounts.img, '/', tCounts.img,
		'| h2', liveCounts.h2, '/', tCounts.h2, '| form', liveCounts.form, '/', tCounts.form);
}
await browser.close();
console.log('done');
