// Reference facts for the round-1 review items, live and t16 side by side.
//   node review-facts.mjs
import { createRequire } from 'node:module';
import path from 'node:path';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const browser = await chromium.launch({ channel: 'chromium' });

const PAGES = {
	't16-pdp': 'http://127.0.0.1:8924/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/',
	'live-pdp': 'https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/',
	't16-eta': 'http://127.0.0.1:8924/product/goodwe-esa-gw5k-eta-g20-5-kw-three-phase-power-module/',
	'live-eta': 'https://de-linker.com/product/goodwe-esa-gw5k-eta-g20-5-kw-three-phase-power-module/',
	't16-shop': 'http://127.0.0.1:8924/products/',
	'live-shop': 'https://de-linker.com/products/',
	't16-archive': 'http://127.0.0.1:8924/product-category/inverters/',
	'live-archive': 'https://de-linker.com/product-category/inverters/',
	't16-saj': 'http://127.0.0.1:8924/product/saj-ats1-t63-a/',
};

for (const [name, url] of Object.entries(PAGES)) {
	const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
	await page.goto(url + (url.includes('?') ? '' : '?cbq=' + Date.now()), { waitUntil: 'networkidle', timeout: 90000 }).catch(() => page.waitForTimeout(4000));
	await page.waitForTimeout(1000);
	const facts = await page.evaluate(() => {
		const cs = (sel, props) => {
			const el = document.querySelector(sel);
			if (!el) return 'none';
			const st = getComputedStyle(el);
			const r = el.getBoundingClientRect();
			const out = { rect: [Math.round(r.x), Math.round(r.y + window.scrollY), Math.round(r.width), Math.round(r.height)] };
			for (const p of props) out[p] = st.getPropertyValue(p);
			return out;
		};
		const all = (sel, props) => Array.from(document.querySelectorAll(sel)).slice(0, 6).map((el) => {
			const st = getComputedStyle(el);
			const r = el.getBoundingClientRect();
			const out = { rect: [Math.round(r.x), Math.round(r.y + window.scrollY), Math.round(r.width), Math.round(r.height)] };
			for (const p of props) out[p] = st.getPropertyValue(p);
			return out;
		});
		return {
			bodyBg: getComputedStyle(document.body).backgroundColor,
			docW: document.documentElement.scrollWidth,
			layout: cs('.pdp-layout', ['grid-template-columns', 'grid-template-areas', 'align-items', 'row-gap', 'column-gap']),
			gallery: cs('.pdp-gallery', ['grid-template-columns', 'grid-template-areas', 'gap', 'align-self']),
			mainWrap: cs('.pdp-gallery-main-wrap', ['background-color', 'border-radius', 'border-top-width', 'border-top-color', 'padding-top', 'width', 'height', 'align-self']),
			mainImg: cs('.pdp-gallery-main', ['background-color', 'border-radius', 'object-fit', 'width', 'height']),
			thumbs: cs('.pdp-thumbs', ['margin-top', 'padding-top', 'gap', 'height', 'align-self', 'grid-area']),
			thumbImgs: all('.pdp-thumb img', ['width', 'height', 'object-fit', 'border-radius']),
			thumbTiles: all('.pdp-thumb', ['padding-top', 'border-top-width', 'border-top-color', 'border-radius', 'background-color', 'width', 'height']),
			statIcon: all('.pdp-spec-list .pdp-app-stat-icon', ['display', 'width', 'height', 'color']),
			specRow: cs('.pdp-spec-list > div', ['display', 'grid-template-columns', 'gap', 'padding-top']),
			benefitP: all('.pdp-benefit p', ['font-size', 'color', 'line-height']),
			benefitLi: all('.pdp-benefit', ['background-color', 'padding-top', 'border-radius', 'width']),
			content: cs('.pdp-content', ['display', 'grid-template-columns', 'grid-template-areas', 'gap']),
			contentKids: Array.from(document.querySelectorAll('.pdp-content > *')).slice(0, 8).map((el) => {
				const st = getComputedStyle(el);
				return { cls: (el.getAttribute('class') || '').slice(0, 44), area: st.gridArea, h: Math.round(el.getBoundingClientRect().height) };
			}),
			tabs: all('.pdp-info-tabs [role="tab"]', ['background-color', 'color', 'font-size', 'font-weight', 'aria-selected']),
			tabList: cs('.pdp-info-tabs', ['display', 'gap', 'padding-top', 'background-color']),
			panel: cs('.pdp-info-panel', ['display', 'height']),
			panelKids: Array.from(document.querySelectorAll('.pdp-info-panel > *')).slice(0, 4).map((el) => ({ tag: el.tagName, cls: (el.getAttribute('class') || '').slice(0, 40), h: Math.round(el.getBoundingClientRect().height), open: el.open })),
			deckCounts: {
				tablists: document.querySelectorAll('[role="tablist"]').length,
				tabs: document.querySelectorAll('[role="tab"]').length,
				panels: document.querySelectorAll('.pdp-info-panel').length,
				discloses: document.querySelectorAll('.pdp-disclose').length,
				statrows: document.querySelectorAll('.pdp-stat-row').length,
			},
			downloadsBlock: cs('#downloads.pdp-block, #downloads', ['display', 'grid-template-columns', 'grid-template-areas', 'height']),
			downloadsKids: Array.from(document.querySelectorAll('#downloads > *')).slice(0, 6).map((el) => ({ tag: el.tagName, cls: (el.getAttribute('class') || '').slice(0, 30), area: getComputedStyle(el).gridArea, h: Math.round(el.getBoundingClientRect().height) })),
			docMetas: Array.from(document.querySelectorAll('.pdp-doc-meta')).slice(0, 6).map((el) => el.textContent.trim().slice(0, 40)),
			compareCheckboxes: document.querySelectorAll('.card-compare-checkbox').length,
			compareMarkup: (() => { const el = document.querySelector('.card-compare-checkbox'); return el ? el.outerHTML.slice(0, 300) : 'none'; })(),
			cardCompareAttr: document.querySelectorAll('[data-compare-article]').length,
			wbIntro: cs('.wb-intro', ['font-size', 'color']),
			wbIntroText: (document.querySelector('.wb-intro') || {}).textContent?.trim().slice(0, 120),
			cardCount: document.querySelectorAll('.sf-card').length,
			wpCustomCss: Array.from(document.querySelectorAll('style#wp-custom-css')).map((s) => s.textContent.length),
			protoAccent: (document.documentElement.outerHTML.match(/--proto-accent/g) || []).length,
			wide: Array.from(document.querySelectorAll('body *')).filter((el) => el.getBoundingClientRect().right > 1442 && el.getBoundingClientRect().width > 40).slice(0, 5).map((el) => `${el.tagName}.${(el.getAttribute('class') || '').slice(0, 40)} right=${Math.round(el.getBoundingClientRect().right)} w=${Math.round(el.getBoundingClientRect().width)}`),
		};
	});
	console.log('==== ' + name + ' ' + JSON.stringify({ docW: facts.docW, bodyBg: facts.bodyBg, cssLen: facts.wpCustomCss, protoAccent: facts.protoAccent, cardCount: facts.cardCount, compareCheckboxes: facts.compareCheckboxes, deckCounts: facts.deckCounts }));
	const keep = ['layout', 'gallery', 'mainWrap', 'mainImg', 'thumbs', 'thumbImgs', 'thumbTiles', 'statIcon', 'specRow', 'benefitP', 'content', 'contentKids', 'tabs', 'panel', 'panelKids', 'downloadsBlock', 'downloadsKids', 'docMetas', 'compareMarkup', 'wbIntroText', 'wide'];
	for (const k of keep) console.log('   ' + k + ': ' + JSON.stringify(facts[k]));
	await page.close();
}
await browser.close();
