/*
 * Measures the two owner-approved round-2 catalog proposals (A1 shop/category
 * container width, A2 sticky category filter rail; owner ruling 2026-10-12)
 * on the t106 instance around their implementation in
 * plugins/linker-commerce/content/windpress/catalogue.css.
 *
 * Same browser (chromium), viewports, URL and wait protocol as the proposal
 * round (docs/acceptance/2026-10-12/visual-round2/proposals/README.md), so
 * the numbers line up with that round's measurements.json: fonts.ready, a
 * stepwise scroll through the whole page, every visible image decoded, then
 * the measurement (and the A2 one after scrolling to y=2000).
 *
 * The variant argument only names the output files: run it with "before"
 * while the served CSS is still the pre-change state, and again with "after"
 * once the change is in and `just windpress-compile t106` has recompiled.
 *
 *   node tools/r2a-implemented.mjs <before|after> <out-dir>
 */
import {createRequire} from 'node:module';
import {mkdir, writeFile} from 'node:fs/promises';

const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-r2a';
const [variant, out] = process.argv.slice(2);
if (!variant || !out) throw new Error('usage: node r2a-implemented.mjs <before|after> <out-dir>');
await mkdir(out, {recursive: true});

const {chromium} = createRequire(repo + '/plugins/linker-tools/package.json')('playwright');
const browser = await chromium.launch({channel: 'chromium'});
const SHOP = 'http://127.0.0.1:8963/products/';
const CAT = 'http://127.0.0.1:8963/product-category/home-storage/';

async function open(url, width, height) {
	const ctx = await browser.newContext({viewport: {width, height}});
	const page = await ctx.newPage();
	await page.goto(url + '?cbq=' + Date.now(), {waitUntil: 'domcontentloaded'});
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
	});
	return {ctx, page};
}

// The A1 numbers: container, grid, first card, its identity column, page
// height. Boxes are [x, y-in-page, width, height] as in the proposal round.
const a1 = () => {
	const rb = (e) => {
		const r = e.getBoundingClientRect();
		return [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)];
	};
	const root = document.querySelector('#tv-woo-b2b-catalog.sf-catalog');
	const container = root.querySelector('.container');
	const grid = root.querySelector('.catalog-grid');
	const card0 = grid.querySelector('.sf-card');
	const identity0 = card0.querySelector('.card-identity');
	return {
		pageH: document.body.scrollHeight,
		sfContainer: getComputedStyle(root).getPropertyValue('--sf-container').trim(),
		container: rb(container),
		containerMaxWidth: getComputedStyle(container).maxWidth,
		grid: rb(grid),
		gridCols: getComputedStyle(grid).gridTemplateColumns,
		card0: rb(card0),
		identity0: rb(identity0),
	};
};

const report = {};

// A1 on the shop page, 1440: the proposal round's own measurement set.
{
	const {ctx, page} = await open(SHOP, 1440, 900);
	report['A1-shop-1440'] = await page.evaluate(a1);
	await page.evaluate(() => window.scrollTo(0, 0));
	await page.waitForTimeout(400);
	await page.screenshot({path: `${out}/A1_catalog-container-1440-${variant}.png`, fullPage: true});
	await ctx.close();
}

// A1 on the category page, 1440: the rule reads the same on both page types.
{
	const {ctx, page} = await open(CAT, 1440, 900);
	report['A1-category-1440'] = await page.evaluate(a1);
	await page.evaluate(() => window.scrollTo(0, 0));
	await page.waitForTimeout(400);
	await page.screenshot({path: `${out}/A1_category-container-1440-${variant}.png`});
	await ctx.close();
}

// A1 guard, 1200: the min-width:1360px rule must not reach below it.
{
	const {ctx, page} = await open(SHOP, 1200, 900);
	report['A1-guard1200'] = await page.evaluate(a1);
	await ctx.close();
}

// A2 on the category page, 1440, at scroll y=2000: the rail pinned at 104.
{
	const {ctx, page} = await open(CAT, 1440, 900);
	await page.evaluate(() => window.scrollTo(0, 2000));
	await page.waitForTimeout(400);
	report['A2-category-1440-y2000'] = await page.evaluate(() => {
		const rail = document.querySelector('.sidebar-filters');
		const r = rail.getBoundingClientRect();
		const cs = getComputedStyle(rail);
		return {
			scrollY: Math.round(scrollY),
			railViewportRect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
			position: cs.position,
			top: cs.top,
			maxHeight: cs.maxHeight,
			overflowY: cs.overflowY,
		};
	});
	await page.screenshot({path: `${out}/A2_catalog-rail-1440-${variant}.png`});
	await ctx.close();
}

// A2 guard, 860: below the min-width:861px rule the mobile drawer owns the
// rail; nothing about the implemented rule may show here.
{
	const {ctx, page} = await open(CAT, 860, 900);
	await page.evaluate(() => window.scrollTo(0, 600));
	await page.waitForTimeout(400);
	report['A2-guard860-y600'] = await page.evaluate(() => {
		const rail = document.querySelector('.sidebar-filters');
		const r = rail.getBoundingClientRect();
		const cs = getComputedStyle(rail);
		return {
			scrollY: Math.round(scrollY),
			railViewportRect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
			position: cs.position,
			visibility: cs.visibility,
			maxHeight: cs.maxHeight,
			overflowY: cs.overflowY,
		};
	});
	await ctx.close();
}

await writeFile(`${out}/measurements-implemented-${variant}.json`, JSON.stringify(report, null, 1));
console.log(variant, JSON.stringify(report));
await browser.close();
