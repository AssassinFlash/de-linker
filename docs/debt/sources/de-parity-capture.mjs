// DE parity capture for t110 (2026-10-13).
// Same protocol as docs/debt/sources/capture-resume.mjs: one Chromium launch,
// independent anonymous contexts, viewport 1440x900 / 390x844, cbq cache-bust,
// animation killed, fonts.ready, lazy-scroll, image settle, full-page PNG.
// Does not follow a redirect into another language and call that a pair:
// the final URL and html lang are recorded with the DOM counts.
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-r2debt';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');

const countsOnly = process.argv.includes('--counts-only');
const out = process.argv[2];
const filter = (process.argv[3] || '').replace(/^--/, '');
const resume = process.argv.includes('--resume');
fs.mkdirSync(out, { recursive: true });

const LIVE = 'https://de-linker.com';
const T = 'http://127.0.0.1:8975';

// 14 page types x DE x 1440/390. URLs are the live hreflang targets from the
// 2026-10-12 EN protocol (docs/debt/sources/capture-resume.mjs), not guessed.
const PAIRS = [
	{ name: 'home-de-1440', live: `${LIVE}/de/`, local: `${T}/de/`, width: 1440 },
	{ name: 'home-de-390', live: `${LIVE}/de/`, local: `${T}/de/`, width: 390 },
	{ name: 'cart-de-1440', live: `${LIVE}/de/warenkorb/`, local: `${T}/de/warenkorb/`, width: 1440 },
	{ name: 'cart-de-390', live: `${LIVE}/de/warenkorb/`, local: `${T}/de/warenkorb/`, width: 390 },
	{ name: 'checkout-de-1440', live: `${LIVE}/de/proforma-anfrage/`, local: `${T}/de/proforma-anfrage/`, width: 1440 },
	{ name: 'checkout-de-390', live: `${LIVE}/de/proforma-anfrage/`, local: `${T}/de/proforma-anfrage/`, width: 390 },
	{ name: 'account-de-1440', live: `${LIVE}/de/mein-konto/`, local: `${T}/de/mein-konto/`, width: 1440 },
	{ name: 'account-de-390', live: `${LIVE}/de/mein-konto/`, local: `${T}/de/mein-konto/`, width: 390 },
	{ name: 'about-de-1440', live: `${LIVE}/de/ueber-uns/`, local: `${T}/de/ueber-uns/`, width: 1440 },
	{ name: 'about-de-390', live: `${LIVE}/de/ueber-uns/`, local: `${T}/de/ueber-uns/`, width: 390 },
	{ name: 'contact-de-1440', live: `${LIVE}/de/kontakt/`, local: `${T}/de/kontakt/`, width: 1440 },
	{ name: 'contact-de-390', live: `${LIVE}/de/kontakt/`, local: `${T}/de/kontakt/`, width: 390 },
	{ name: 'installers-de-1440', live: `${LIVE}/de/fuer-installateur/`, local: `${T}/de/fuer-installateur/`, width: 1440 },
	{ name: 'installers-de-390', live: `${LIVE}/de/fuer-installateur/`, local: `${T}/de/fuer-installateur/`, width: 390 },
	{ name: 'services-de-1440', live: `${LIVE}/de/service-support/`, local: `${T}/de/service-support/`, width: 1440 },
	{ name: 'services-de-390', live: `${LIVE}/de/service-support/`, local: `${T}/de/service-support/`, width: 390 },
	{ name: 'bloglist-de-1440', live: `${LIVE}/de/blog/`, local: `${T}/de/blog/`, width: 1440 },
	{ name: 'bloglist-de-390', live: `${LIVE}/de/blog/`, local: `${T}/de/blog/`, width: 390 },
	{ name: 'blogarchive-de-1440', live: `${LIVE}/de/category/system-design/`, local: `${T}/de/category/system-design/`, width: 1440 },
	{ name: 'blogarchive-de-390', live: `${LIVE}/de/category/system-design/`, local: `${T}/de/category/system-design/`, width: 390 },
	{ name: 'blogpost-de-1440', live: `${LIVE}/de/hybridwechselrichter-vs-ac-speicher/`, local: `${T}/de/hybridwechselrichter-vs-ac-speicher/`, width: 1440 },
	{ name: 'blogpost-de-390', live: `${LIVE}/de/hybridwechselrichter-vs-ac-speicher/`, local: `${T}/de/hybridwechselrichter-vs-ac-speicher/`, width: 390 },
	{ name: 'search-de-1440', live: `${LIVE}/de/?s=PV`, local: `${T}/de/?s=PV`, width: 1440 },
	{ name: 'search-de-390', live: `${LIVE}/de/?s=PV`, local: `${T}/de/?s=PV`, width: 390 },
	{ name: 'notfound-de-1440', live: `${LIVE}/de/audit-404-20261012/`, local: `${T}/de/audit-404-20261012/`, width: 1440 },
	{ name: 'notfound-de-390', live: `${LIVE}/de/audit-404-20261012/`, local: `${T}/de/audit-404-20261012/`, width: 390 },
	{ name: 'compare-de-1440', live: `${LIVE}/de/compare-products/`, local: `${T}/de/compare-products/`, width: 1440 },
	{ name: 'compare-de-390', live: `${LIVE}/de/compare-products/`, local: `${T}/de/compare-products/`, width: 390 },
];

const NO_ANIM = '*, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; caret-color: transparent !important; }';

const COUNTS = `(() => {
	const q = (s) => document.querySelectorAll(s).length;
	const header = document.querySelector('header');
	return {
		url: location.href,
		lang: document.documentElement.lang,
		title: document.title,
		scrollWidth: document.documentElement.scrollWidth,
		scrollHeight: document.body.scrollHeight,
		a: q('a'), img: q('img'), form: q('form'), button: q('button'),
		h1: q('h1'), h2: q('h2'), h3: q('h3'),
		header: q('header'), footer: q('footer'), nav: q('nav'),
		headerText: header ? header.innerText.replace(/\\s+/g, ' ').trim().slice(0, 240) : '',
		langSwitch: q('[data-linker-language-choice], .lnk-lang-half, .pll-switcher'),
		shell: /no posts matched|Keine Beiträge gefunden|Nichts gefunden/i.test(document.body.innerText),
	};
})()`;

// The Mac system proxy (127.0.0.1:1082) is what Chromium picks up; a bare
// launch failed with ERR_TUNNEL_CONNECTION_FAILED on 2026-10-13. curl through
// the same proxy returned 200, so the proxy is named explicitly and localhost
// is left out of it.
const browser = await chromium.launch({
	channel: 'chromium',
	proxy: { server: 'http://127.0.0.1:1082', bypass: '127.0.0.1,localhost' },
});
console.log('browser', browser.version());

async function shoot(url, file, width) {
	const context = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 } });
	const page = await context.newPage();
	const target = url.includes('?') ? `${url}&cbq=${Date.now()}` : `${url}?cbq=${Date.now()}`;
	const response = await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 120_000 });
	await page.waitForLoadState('load', { timeout: 60_000 }).catch(() => {});
	await page.waitForLoadState('networkidle', { timeout: 20_000 }).catch(() => {});
	await page.addStyleTag({ content: NO_ANIM });
	await page.evaluate(async () => { await document.fonts.ready; });
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
	await page.evaluate(async () => {
		const budget = new Promise((res) => setTimeout(res, 15000));
		const settled = Promise.all(Array.from(document.images).map((img) => new Promise((res) => {
			if (img.complete) { img.decode().then(() => res(), () => res()); return; }
			const done = () => { img.decode().then(() => res(), () => res()); };
			img.addEventListener('load', done, { once: true });
			img.addEventListener('error', () => res(), { once: true });
		})));
		await Promise.race([settled, budget]);
	});
	await page.evaluate(async () => { await document.fonts.ready; });
	await page.evaluate(() => document.documentElement.style.setProperty('overflow-y', 'scroll'));
	if (!countsOnly) {
		await page.screenshot({ path: file, fullPage: true, animations: 'disabled' });
	}
	const counts = await page.evaluate(COUNTS);
	counts.status = response ? response.status() : null;
	await context.close();
	return counts;
}

const countsPath = path.join(out, 'dom-counts.json');
const summary = fs.existsSync(countsPath) ? JSON.parse(fs.readFileSync(countsPath, 'utf8')) : {};
for (const spec of PAIRS) {
	if (filter && filter !== 'resume' && !spec.name.includes(filter)) continue;
	if (resume && fs.existsSync(path.join(out, `${spec.name}-live.png`)) && fs.existsSync(path.join(out, `${spec.name}-t110.png`))) {
		console.log(spec.name, 'skip-existing');
		continue;
	}
	const liveCounts = await shoot(spec.live, path.join(out, `${spec.name}-live.png`), spec.width);
	const localCounts = await shoot(spec.local, path.join(out, `${spec.name}-t110.png`), spec.width);
	summary[spec.name] = { live: liveCounts, t110: localCounts };
	fs.writeFileSync(path.join(out, 'dom-counts.json'), JSON.stringify(summary, null, 1));
	console.log(spec.name,
		'live', liveCounts.status, liveCounts.lang, liveCounts.scrollHeight,
		't110', localCounts.status, localCounts.lang, localCounts.scrollHeight,
		'url', localCounts.url.replace(/cbq=\d+/, 'cbq'));
}
await browser.close();
console.log('done', Object.keys(summary).length);
