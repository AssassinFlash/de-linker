/*
 * Measures the two owner-approved round-2 account proposals (2026-10-12
 * ruling) on the t107 instance: B1 the account navigation as the header
 * card-language menu (with the current-page state restored at the markup
 * layer), B2 the inquiry list's row actions layered (View quiet, Request
 * again the primary).
 *
 * Same browser, viewport and wait protocol as the round's proposal trials
 * (/tmp/r2-trials.mjs on t105), so the numbers are directly comparable with
 * docs/acceptance/2026-10-12/visual-round2/proposals/measurements.json. Run
 * once before the change lands (phase "before") and once after (phase
 * "after"); each run writes its own PNGs and one measurements-<phase>.json.
 *
 * Each browser context needs its own one-time login, minted per run:
 *   just login t107 --user customer-3
 *   node tools/r2b-implemented.mjs <before|after> <out-dir> <login1> <login2> <login3>
 */
import {createRequire} from 'node:module';
import {mkdir, writeFile} from 'node:fs/promises';

const worktree = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-r2b';
const [phase, out, login1, login2, login3] = process.argv.slice(2);
if (!phase || !out || !login1 || !login2 || !login3) {
	throw new Error('usage: node r2b-implemented.mjs <before|after> <out-dir> <login1> <login2> <login3>');
}
await mkdir(out, {recursive: true});

const {chromium} = createRequire(worktree + '/plugins/linker-tools/package.json')('playwright');
const browser = await chromium.launch({channel: 'chromium'});
const BASE = 'http://127.0.0.1:8972';
const ACCT = BASE + '/my-account/inquiries/';

async function settle(page) {
	await page.waitForTimeout(1600);
	await page.evaluate(async () => {
		await document.fonts.ready;
		const step = () => new Promise((r) => setTimeout(r, 25));
		for (let t = 0; t < document.body.scrollHeight + 500; t += 600) {
			window.scrollTo(0, t);
			await step();
		}
		const vis = [...document.images].filter((i) => i.checkVisibility());
		await Promise.all(vis.map((i) => i.decode().catch(() => {})));
		window.scrollTo(0, 0);
	});
	await page.waitForTimeout(700);
}

const report = {phase};

// ---- B1: the account navigation card (inquiries, 1440 and 390) ----
// What the proposal's B1/B2 trials measured, plus the adopted navigation's
// own current-page state: the active item's classes, its aria-current and
// its computed background, and one hovered neighbour for the hover state.
const navMeasure = () => {
	const box = (el) => {
		if (!el) return null;
		const r = el.getBoundingClientRect();
		return [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)];
	};
	const nav = document.querySelector('.woocommerce-MyAccount-navigation');
	const list = nav?.querySelector('.list-group');
	const items = [...(nav?.querySelectorAll('.list-group-item') ?? [])];
	return {
		pageH: document.body.scrollHeight,
		nav: box(nav),
		listGroup: box(list),
		linkCount: items.length,
		linkTexts: items.map((a) => a.textContent.trim()),
		linkDisplays: [...new Set(items.map((a) => getComputedStyle(a).display))],
		linkHeights: items.map((a) => Math.round(a.getBoundingClientRect().height)),
		active: (() => {
			const a = items.find((el) => el.classList.contains('is-active'));
			if (!a) return null;
			return {
				text: a.textContent.trim(),
				className: a.className,
				ariaCurrent: a.getAttribute('aria-current'),
				background: getComputedStyle(a).backgroundColor,
				fontWeight: getComputedStyle(a).fontWeight,
			};
		})(),
	};
};

async function shotNav(viewport, login, name) {
	const ctx = await browser.newContext({viewport});
	const page = await ctx.newPage();
	await page.goto(login, {waitUntil: 'domcontentloaded'});
	await page.goto(ACCT + '?cbq=' + Date.now(), {waitUntil: 'domcontentloaded'});
	await settle(page);
	const measured = await page.evaluate(navMeasure);
	// The hover state is part of the adopted design: rest the pointer on the
	// item after the active one and read its computed background.
	const hoverIndex = measured.linkTexts.findIndex((t) => t === measured.active?.text) + 1;
	if (hoverIndex > 0 && hoverIndex < measured.linkCount) {
		await page.locator('.woocommerce-MyAccount-navigation .list-group-item').nth(hoverIndex).hover();
		await page.waitForTimeout(400);
		measured.hover = await page.evaluate(() => {
			const items = [...document.querySelectorAll('.woocommerce-MyAccount-navigation .list-group-item')];
			const a = items.find((el) => el.classList.contains('is-active'));
			const i = items.indexOf(a) + 1;
			const s = getComputedStyle(items[i]);
			return {text: items[i].textContent.trim(), background: s.backgroundColor};
		});
	}
	await page.screenshot({path: `${out}/${name}-${phase}.png`, fullPage: true});
	await ctx.close();
	return measured;
}

report['B1-1440'] = await shotNav({width: 1440, height: 900}, login1, 'B1_account-nav-1440');
console.log('B1-1440', JSON.stringify(report['B1-1440']));

report['B1-390'] = await shotNav({width: 390, height: 844}, login2, 'B2_account-nav-390');
console.log('B1-390', JSON.stringify(report['B1-390']));

// ---- B2: the inquiry row actions (inquiries, 1440) ----
// Every action link of the first row (View, Proforma invoice when the
// inquiry carries one, Request again), with the classes the row really
// prints and the computed layer the adoption prescribes.
{
	const ctx = await browser.newContext({viewport: {width: 1440, height: 900}});
	const page = await ctx.newPage();
	await page.goto(login3, {waitUntil: 'domcontentloaded'});
	await page.goto(ACCT + '?cbq=' + Date.now(), {waitUntil: 'domcontentloaded'});
	await settle(page);
	await page.evaluate(() => window.scrollTo(0, 180));
	await page.waitForTimeout(500);
	report['B2-1440'] = await page.evaluate(() => {
		const links = [...document.querySelectorAll('.woocommerce-orders-table__cell-order-actions a')];
		return {
			row1: links.slice(0, 3).map((a) => {
				const s = getComputedStyle(a);
				const r = a.getBoundingClientRect();
				return {
					text: a.textContent.trim(),
					className: a.className,
					background: s.backgroundColor,
					color: s.color,
					borderColor: s.borderTopColor,
					radius: s.borderRadius,
					fontSize: s.fontSize,
					w: Math.round(r.width),
					h: Math.round(r.height),
				};
			}),
			rows: document.querySelectorAll('.woocommerce-orders-table tbody tr').length,
		};
	});
	await page.screenshot({path: `${out}/B3_inquiry-actions-1440-${phase}.png`});
	await ctx.close();
	console.log('B2-1440', JSON.stringify(report['B2-1440']));
}

await writeFile(`${out}/measurements-${phase}.json`, JSON.stringify(report, null, 1));
console.log('measurements written:', phase);
await browser.close();
