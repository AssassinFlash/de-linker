/*
 * Measures the four owner-approved PDP proposals (2026-10-11 ruling) on the
 * t16 instance after they were implemented in
 * plugins/linker-commerce/content/windpress/pdp.css.
 *
 * Same browser, viewport, URL and wait protocol as the proposal round's
 * /tmp/t16-proposals.mjs, so the "after" numbers are directly comparable to
 * that round's measurements.json. The "before" variant injects the four
 * properties' pre-implementation values (the CSS as the trial's "before" state
 * had it) so this run measures its own baseline instead of trusting the
 * recorded one.
 *
 *   node tools/pdp-proposals-implemented.mjs <out-dir>
 */
import {createRequire} from 'node:module';
import {mkdir, writeFile} from 'node:fs/promises';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const out = process.argv[2];
if (!out) throw new Error('usage: node pdp-proposals-implemented.mjs <out-dir>');
await mkdir(out, {recursive: true});

const {chromium} = createRequire(repo + '/plugins/linker-tools/package.json')('playwright');
const browser = await chromium.launch({channel: 'chromium'});
const PDP = 'http://127.0.0.1:8924/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/';

// The pre-implementation values of exactly the four accepted proposals.
const before = `@media (min-width:1200px){
  #tv-storefront-pdp .pdp-stats-layout{grid-template-columns:minmax(0,0.95fr) minmax(0,1.05fr);gap:40px}
  #tv-storefront-pdp .pdp-stats-summary{display:block}
  #tv-storefront-pdp .pdp-pairings{grid-template-columns:repeat(4,280px)}
  #tv-storefront-pdp .pdp-faqs{display:block}
  #tv-storefront-pdp .pdp-faqs > .pdp-section-title{grid-column:auto}
}
@media (max-width:480px){
  body:has(#tv-storefront-pdp) #tv-storefront-pdp .pdp-spec-list{grid-template-columns:repeat(4,minmax(0,1fr))}
}`;

const shots = [
	['P1_technical', 1440, '#stats'],
	['P2_pairings', 1440, '.pdp-pairings'],
	['P3_faq', 1440, '.pdp-faqs'],
	['P4_specstrip', 390, '.pdp-spec-list'],
	// Guards for the proposals' stated footprint: nothing changes below the
	// 1200px breakpoint, and the 480px rule does not reach 481px.
	['GUARD_1100', 1100, '#stats'],
	['GUARD_481', 481, '.pdp-spec-list'],
];

const report = {};
for (const [name, width, sel] of shots) {
	for (const variant of ['before', 'after']) {
		const ctx = await browser.newContext({viewport: {width, height: width === 390 ? 844 : 900}});
		const page = await ctx.newPage();
		await page.goto(PDP + '?cbq=' + Date.now(), {waitUntil: 'domcontentloaded'});
		// "before" = the pre-implementation state, "after" = the served CSS as is.
		if (variant === 'before') await page.addStyleTag({content: before});
		await page.waitForTimeout(2500);
		await page.evaluate(async () => {
			await document.fonts.ready;
			const step = () => new Promise((r) => setTimeout(r, 40));
			for (let t = 0; t < document.body.scrollHeight + 800; t += 700) {
				window.scrollTo(0, t);
				await step();
			}
			const vis = [...document.images].filter((i) => i.checkVisibility());
			await Promise.all(vis.map((i) => i.decode().catch(() => {})));
			window.scrollTo(0, 0);
		});
		await page.waitForTimeout(1200);
		report[name + '-' + width + '-' + variant] = await page.evaluate((sel) => {
			const box = (e) => {
				const r = e.getBoundingClientRect();
				return [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)];
			};
			const cs = (e) => getComputedStyle(e);
			const el = document.querySelector(sel);
			const out = {target: box(el), pageH: document.body.scrollHeight};
			if (sel === '#stats') {
				const l = document.querySelector('.pdp-stats-layout');
				const d = document.querySelector('.pdp-info-deck');
				const s = document.querySelector('.pdp-stats-summary');
				const r0 = document.querySelector('.pdp-stat-row dd');
				out.layout = box(l);
				out.layoutColumns = cs(l).gridTemplateColumns;
				out.deck = box(d);
				out.summary = s ? box(s) : null;
				out.summaryDisplay = s ? cs(s).display : null;
				out.summaryColumns = s ? cs(s).gridTemplateColumns : null;
				out.valueBox = r0 ? box(r0) : null;
			}
			if (sel === '.pdp-pairings') {
				const c = [...document.querySelectorAll('.pdp-pairing')];
				out.cards = c.length;
				out.columns = cs(el).gridTemplateColumns;
				out.firstTwo = c.slice(0, 2).map(box);
				out.lastRow = c.slice(-4).map(box);
			}
			if (sel === '.pdp-faqs') {
				const rows = [...document.querySelectorAll('.pdp-faqs .pdp-disclose')];
				out.rows = rows.length;
				out.columns = cs(el).gridTemplateColumns;
				out.row0 = rows[0] ? box(rows[0]) : null;
				out.row1 = rows[1] ? box(rows[1]) : null;
			}
			if (sel === '.pdp-spec-list') {
				const cells = [...document.querySelectorAll('.pdp-spec-list > div')];
				out.cells = cells.length;
				out.columns = cs(el).gridTemplateColumns;
				out.cell0 = cells[0] ? box(cells[0]) : null;
				out.cellLast = cells[cells.length - 1] ? box(cells[cells.length - 1]) : null;
			}
			return out;
		}, sel);
		await ctx.close();
		console.log(name, width, variant, JSON.stringify(report[name + '-' + width + '-' + variant]));
	}
}
await writeFile(out + '/measurements-implemented.json', JSON.stringify(report, null, 1));
await browser.close();
