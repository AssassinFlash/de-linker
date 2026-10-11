// Round-2 facts: pairing card internals, thumb sources, plan-check, docs grid,
// and a scan for the page whose live deck counts are 13 tabs / 3 tablists /
// 13 discloses / 32 statrows. Usage: node r2-facts.mjs
import { createRequire } from 'node:module';
import path from 'node:path';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const browser = await chromium.launch({ channel: 'chromium' });

const detail = async (url, label) => {
	const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
	await page.goto(url + '?cbq=' + Date.now(), { waitUntil: 'networkidle', timeout: 90000 }).catch(() => page.waitForTimeout(4000));
	await page.evaluate(async () => { await new Promise((r) => { let t = 0; const s = () => { window.scrollTo(0, t); t += 700; if (t < document.body.scrollHeight + 700) setTimeout(s, 40); else r(); }; s(); }); });
	await page.waitForTimeout(900);
	const out = await page.evaluate(() => {
		const box = (sel) => { const el = document.querySelector(sel); if (!el) return 'none'; const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return { w: +r.width.toFixed(1), h: +r.height.toFixed(1), x: Math.round(r.x), y: Math.round(r.y + scrollY), display: s.display, pad: s.padding, mar: s.margin, bg: s.backgroundColor, fs: s.fontSize, lh: s.lineHeight, radius: s.borderTopLeftRadius, gap: s.gap, rowGap: s.rowGap, colGap: s.columnGap }; };
		const img = (sel) => { const el = document.querySelector(sel); if (!el) return 'none'; const r = el.getBoundingClientRect(); return { w: +r.width.toFixed(1), h: +r.height.toFixed(1), src: (el.currentSrc || el.src || '').split('/').pop(), nat: [el.naturalWidth, el.naturalHeight], fit: getComputedStyle(el).objectFit, radius: getComputedStyle(el).borderTopLeftRadius, bg: getComputedStyle(el).backgroundColor }; };
		return {
			pairCard: box('.pdp-pairing'), pairImg: img('.pdp-pairing img'), pairImgBox: box('.pdp-pairing img'),
			chip: box('.pdp-pairing-chips .pdp-doc-meta'), chipText: (document.querySelector('.pdp-pairing-chips .pdp-doc-meta') || {}).textContent,
			pairName: box('.pdp-pairing-name'), pairSku: box('.pdp-pairing-sku'), pairCopy: box('.pdp-pairing-copy'),
			thumb0: img('.pdp-thumb img'), thumb1: img('.pdp-thumb:nth-child(2) img'),
			thumb0Box: box('.pdp-thumb img'),
			planCheck: box('.pdp-project-check'), planSummary: box('.pdp-project-check summary'), planH2: box('.pdp-project-check summary h2'),
			docsBlock: box('#downloads.pdp-block'), docsH2: box('#downloads .pdp-section-title'), docCard: box('.pdp-doc'), docIcon: box('.pdp-doc-icon'), docGrow: box('.pdp-doc .grow'), docMeta: box('.pdp-doc-meta'),
			card: box('.sf-card'), cardMedia: box('.sf-card-media'), cardIdentity: box('.card-identity'), cardFacts: box('.card-facts'), cardArticle: box('.card-exact-article'), cardPrice: box('.sf-card-price'), cardAvail: box('.sf-card-availability'), cardActions: box('.sf-card-actions'), cardTitle: box('.sf-card-title'), cardBrand: box('.sf-card-brand'), cardSku: box('.sf-card-sku'),
			metaLang: Array.from(document.querySelectorAll('.pdp-doc-meta')).slice(0, 14).map((e) => e.textContent.trim().slice(-16)),
		};
	});
	console.log('==== ' + label + ' ' + JSON.stringify(out.pairCard) + ' ' + JSON.stringify(out.pairImgBox) + ' ' + JSON.stringify(out.chip));
	console.log('   pairName ' + JSON.stringify(out.pairName) + ' pairSku ' + JSON.stringify(out.pairSku));
	console.log('   thumb0 ' + JSON.stringify(out.thumb0) + '\n   thumb1 ' + JSON.stringify(out.thumb1));
	console.log('   planCheck ' + JSON.stringify(out.planCheck) + '\n   planSummary ' + JSON.stringify(out.planSummary) + '\n   planH2 ' + JSON.stringify(out.planH2));
	console.log('   docsBlock ' + JSON.stringify(out.docsBlock) + '\n   docsH2 ' + JSON.stringify(out.docsH2) + '\n   docCard ' + JSON.stringify(out.docCard) + '\n   docIcon ' + JSON.stringify(out.docIcon) + '\n   docGrow ' + JSON.stringify(out.docGrow) + '\n   docMeta ' + JSON.stringify(out.docMeta));
	console.log('   card ' + JSON.stringify(out.card) + '\n   cardMedia ' + JSON.stringify(out.cardMedia) + '\n   cardIdentity ' + JSON.stringify(out.cardIdentity) + '\n   cardFacts ' + JSON.stringify(out.cardFacts) + '\n   cardArticle ' + JSON.stringify(out.cardArticle) + '\n   cardPrice ' + JSON.stringify(out.cardPrice) + '\n   cardAvail ' + JSON.stringify(out.cardAvail) + '\n   cardActions ' + JSON.stringify(out.cardActions) + '\n   cardTitle ' + JSON.stringify(out.cardTitle) + ' cardBrand ' + JSON.stringify(out.cardBrand) + ' cardSku ' + JSON.stringify(out.cardSku));
	console.log('   metaLang ' + JSON.stringify(out.metaLang));
	await page.close();
};

await detail('https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/', 'LIVE-pdp');
await detail('http://127.0.0.1:8924/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/', 'T16-pdp');
await detail('https://de-linker.com/products/', 'LIVE-shop');
await detail('http://127.0.0.1:8924/products/', 'T16-shop');

// scan candidate products for the 13/3/13/32 deck shape
const candidates = [
	'goodwe-gw112-6-bat-ac-g10', 'goodwe-gw61-4-bat-ac-g10', 'goodwe-gw208-9-bat-lc-g10',
	'goodwe-esa-gw125-261-esa-lcn-g10', 'saj-b2-10-0-hv1', 'saj-chs2-50k-t6-x',
	'goodwe-gw100k-et-g10', 'goodwe-etr-125-kw-ci-three-phase-hybrid-inverter-1000v',
	'pylontech-optim-us-l260-omni', 'saj-emanager-c1-pro', 'goodwe-gw261-2-bat-lcd-g10',
	'goodwe-lynx-home-f-pcu-base-master-bms', 'chint-dtsu666',
];
for (const slug of candidates) {
	const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
	await page.goto('https://de-linker.com/product/' + slug + '/?cbq=' + Date.now(), { waitUntil: 'networkidle', timeout: 90000 }).catch(() => {});
	await page.evaluate(async () => { await new Promise((r) => { let t = 0; const s = () => { window.scrollTo(0, t); t += 900; if (t < document.body.scrollHeight + 900) setTimeout(s, 30); else r(); }; s(); }); });
	await page.waitForTimeout(500);
	const c = await page.evaluate(() => ({ tablists: document.querySelectorAll('[role="tablist"]').length, tabs: document.querySelectorAll('[role="tab"]').length, discloses: document.querySelectorAll('.pdp-disclose').length, statrows: document.querySelectorAll('.pdp-stat-row').length }));
	console.log('SCAN ' + slug + ' ' + JSON.stringify(c));
	await page.close();
}
await browser.close();
