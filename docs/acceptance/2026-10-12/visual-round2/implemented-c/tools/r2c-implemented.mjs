/*
 * Measures the implemented round-2 proposals C1 and C2 (owner ruling
 * 2026-10-12) on a local instance:
 *
 *   C1  the product page hides the Genie app's closed title bar (it covered
 *       the sticky buy box's action row; the standing bubble stays);
 *   C2  under 860px an open Genie becomes a bottom conversation card instead
 *       of staying display:none with the whole dock tree.
 *
 * The style layer is plugins/linker-tools/src/genie/genie.css; this script
 * drives the instance's pages with the same browser, viewport and wait
 * protocol as the proposal round (fonts.ready, a scroll sweep, decoded
 * images), so the numbers line up with the trial's measurements. The
 * "before" phase runs against the pre-change checkout (git stash), the
 * "after" phase against the change itself.
 *
 *   node docs/acceptance/2026-10-12/visual-round2/implemented-c/tools/r2c-implemented.mjs before|after
 *
 * Screenshots and measurements.json land in
 * docs/acceptance/2026-10-12/visual-round2/implemented-c/.
 */
import {createRequire} from 'node:module';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../../../../../..');
const phase = process.argv[2];
if (phase !== 'before' && phase !== 'after') {
	throw new Error('usage: node docs/acceptance/2026-10-12/visual-round2/implemented-c/tools/r2c-implemented.mjs before|after');
}
const out = resolve(
	repo,
	'docs/acceptance/2026-10-12/visual-round2/implemented-c'
);
await mkdir(out, {recursive: true});

const BASE = 'http://127.0.0.1:8966';
const PDP = BASE + '/product/goodwe-gw60k-sts-g10/';
const SHOP = BASE + '/products/';

const {chromium} = createRequire(
	resolve(repo, 'plugins/linker-tools/package.json')
)('playwright');
const browser = await chromium.launch({channel: 'chromium'});

/** The proposal round's wait protocol: fonts, a scroll sweep, images. */
async function settle(page) {
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
}

/** Page-coordinate rect of the first match, rounded; null when absent. */
async function rect(page, sel) {
	return page.evaluate(
		(sel) => {
			const e = document.querySelector(sel);
			if (!e) return null;
			const r = e.getBoundingClientRect();
			return [
				Math.round(r.x),
				Math.round(r.y + scrollY),
				Math.round(r.width),
				Math.round(r.height),
			];
		},
		sel
	);
}

const report = {};
async function record(scene, data) {
	report[scene + '-' + phase] = data;
	console.log(scene, phase, JSON.stringify(data));
	let prior = {};
	try {
		prior = JSON.parse(await readFile(out + '/measurements.json', 'utf8'));
	} catch {
		// First phase of the run.
	}
	Object.assign(prior, report);
	await writeFile(out + '/measurements.json', JSON.stringify(prior, null, 1));
}

/*
 * C1, part 1: the product page's closed dock. Boot the app with the standing
 * bubble, stick the buy box, then measure the bar, the bubble and the three
 * action buttons (Compare, Ask Linker Advisor, Documents) with their occluder.
 */
{
	const ctx = await browser.newContext({viewport: {width: 1440, height: 900}});
	const page = await ctx.newPage();
	await page.goto(PDP + '?cbq=' + Date.now(), {waitUntil: 'domcontentloaded'});
	await page.waitForTimeout(2500);
	await settle(page);
	const rest = await page.evaluate(() => {
		const dock = document.querySelector('.linker-genie-open');
		const r = dock.getBoundingClientRect();
		return {
			bubble: [
				Math.round(r.x),
				Math.round(r.y + scrollY),
				Math.round(r.width),
				Math.round(r.height),
			],
			mountHidden: document.querySelector('[data-linker-genie-mount]').hidden,
			buyOnPage: !!document.querySelector('.pdp-buy-inner'),
		};
	});
	await page.locator('.linker-genie-open').click();
	await page
		.locator('.linker-genie-app__toggle')
		.waitFor({state: 'attached', timeout: 30000});
	await page.waitForTimeout(800);
	// Stick the buy box: its own page position minus the sticky top (84px).
	await page.evaluate(() => {
		const buy = document.querySelector('.pdp-buy-inner');
		window.scrollTo(
			0,
			Math.max(0, buy.getBoundingClientRect().top + scrollY - 84)
		);
	});
	await page.waitForTimeout(1200);
	const closed = await page.evaluate((rest) => {
		const r = (e) => {
			if (!e) return null;
			const b = e.getBoundingClientRect();
			return [
				Math.round(b.x),
				Math.round(b.y + scrollY),
				Math.round(b.width),
				Math.round(b.height),
			];
		};
		const bar = document.querySelector('.linker-genie-app__bar');
		const bubble = document.querySelector('.linker-genie-open');
		const buy = document.querySelector('.pdp-buy-inner');
		const buttons = [
			...document.querySelectorAll('.pdp-product-tools .pdp-tool'),
		];
		const overlap = (a, b) => {
			if (!a || !b) return 0;
			const w = Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]);
			const h = Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]);
			return Math.max(0, w) * Math.max(0, h);
		};
		const barRect = r(bar);
		const bubbleRect = r(bubble);
		const occluder = (btn) => {
			const b = btn.getBoundingClientRect();
			const hit = document.elementFromPoint(
				b.x + b.width / 2,
				b.y + b.height / 2
			);
			return hit && (btn === hit || btn.contains(hit))
				? null
				: hit
					? (hit.closest('.linker-genie, .linker-genie-app')?.className ??
						hit.tagName)
					: 'none';
		};
		return {
			rest,
			scrollY: Math.round(scrollY),
			ariaExpanded: bubble.getAttribute('aria-expanded'),
			barRect,
			barDisplay: bar ? getComputedStyle(bar).display : null,
			bubbleRect,
			buyRect: r(buy),
			buttons: buttons.map((btn) => {
				const rect = r(btn);
				return {
					label: btn.textContent.trim().split('\n')[0],
					rect,
					overlapBarPx2: Math.round(overlap(rect, barRect)),
					overlapBubblePx2: Math.round(overlap(rect, bubbleRect)),
					occludedBy: occluder(btn),
				};
			}),
		};
	}, rest);
	await page.screenshot({path: out + `/C1_pdp-dock-1440-${phase}.png`});
	await record('C1_pdp_closed', closed);

	// C1, part 2: the open conversation keeps the bar as the card's header.
	// The product page's own ask entry is the opener there (the closed bar,
	// whose Open button was the other opener, is the thing C1 hides).
	await page.locator('[data-pdp-ask]').first().click();
	await page
		.locator('.linker-genie-app__composer')
		.waitFor({state: 'visible', timeout: 30000});
	await page.waitForTimeout(1200);
	const opened = {
		barRect: await rect(page, '.linker-genie-app__bar'),
		barDisplay: await page.evaluate(
			"getComputedStyle(document.querySelector('.linker-genie-app__bar')).display"
		),
		panelRect: await rect(page, '.linker-genie-app__panel'),
	};
	await page.screenshot({path: out + `/C1_pdp-open-1440-${phase}.png`});
	await record('C1_pdp_open', opened);
	await ctx.close();
}

/*
 * C1, guard: away from the product page the closed bar stays.
 */
{
	const ctx = await browser.newContext({viewport: {width: 1440, height: 900}});
	const page = await ctx.newPage();
	await page.goto(SHOP + '?cbq=' + Date.now(), {waitUntil: 'domcontentloaded'});
	await page.waitForTimeout(2500);
	await settle(page);
	await page.locator('.linker-genie-open').click();
	await page
		.locator('.linker-genie-app__toggle')
		.waitFor({state: 'attached', timeout: 30000});
	await page.waitForTimeout(800);
	const bar = await rect(page, '.linker-genie-app__bar');
	const display = await page.evaluate(
		"getComputedStyle(document.querySelector('.linker-genie-app__bar')).display"
	);
	await page.screenshot({path: out + `/C1_shop-dock-1440-${phase}.png`});
	await record('C1_shop_closed', {barRect: bar, barDisplay: display});
	await ctx.close();
}

/*
 * C2: under 860px the catalogue's Ask Genie chip boots the app; measure the
 * resting tree, the card after the click, and the conversation after the
 * app's own Open.
 */
{
	const ctx = await browser.newContext({viewport: {width: 390, height: 844}});
	const page = await ctx.newPage();
	await page.goto(SHOP + '?cbq=' + Date.now(), {waitUntil: 'domcontentloaded'});
	await page.waitForTimeout(2500);
	await settle(page);
	const resting = await page.evaluate(() => {
		const dock = document.querySelector('.linker-genie');
		const bubble = document.querySelector('.linker-genie-open');
		const b = bubble.getBoundingClientRect();
		return {
			dockDisplay: getComputedStyle(dock).display,
			bubbleRect: [
				Math.round(b.x),
				Math.round(b.y + scrollY),
				Math.round(b.width),
				Math.round(b.height),
			],
		};
	});
	// The catalogue carries two Ask Genie chips at this width: the search
	// toolbar's (hidden under 861px) and the mobile tool row's — click the
	// one the visitor can actually see.
	const chip = page.locator('.linker-genie-chip:visible').first();
	await chip.scrollIntoViewIfNeeded();
	await chip.click();
	await page
		.locator('.linker-genie-app__toggle')
		.waitFor({state: 'attached', timeout: 30000});
	await page.waitForTimeout(800);
	const opened = await page.evaluate((resting) => {
		const r = (e) => {
			if (!e) return null;
			const b = e.getBoundingClientRect();
			return [
				Math.round(b.x),
				Math.round(b.y + scrollY),
				Math.round(b.width),
				Math.round(b.height),
			];
		};
		const dock = document.querySelector('.linker-genie');
		const bubble = document.querySelector('.linker-genie-open');
		const panel = document.querySelector('.linker-genie-panel');
		const app = document.querySelector('.linker-genie-app');
		const cs = getComputedStyle(app);
		const pr = r(panel);
		return {
			resting,
			viewport: [innerWidth, innerHeight],
			chipAria: document
				.querySelector('.linker-genie-chip')
				.getAttribute('aria-expanded'),
			bubbleAria: bubble.getAttribute('aria-expanded'),
			dockDisplay: getComputedStyle(dock).display,
			dockPosition: getComputedStyle(dock).position,
			bubbleDisplay: getComputedStyle(bubble).display,
			bubbleRect: r(bubble),
			panelRect: pr,
			panelInViewport:
				!!pr &&
				pr[0] >= 0 &&
				pr[1] >= 0 &&
				pr[0] + pr[2] <= innerWidth &&
				pr[1] + pr[3] <= innerHeight,
			appRect: r(app),
			appMaxHeight: cs.maxHeight,
			appOverflow: cs.overflow,
			appRadius: cs.borderRadius,
			appBackground: cs.backgroundColor,
		};
	}, resting);
	await page.screenshot({path: out + `/C2_genie-mobile-390-${phase}.png`});
	await record('C2_shop_open', opened);

	// The app's own Open expands the conversation inside the card. Before the
	// change the whole tree is display:none, so the Open button cannot even
	// be clicked: that unreachable state is the before measurement itself.
	const toggle = page.locator('.linker-genie-app__toggle');
	if (await toggle.isVisible()) {
		await toggle.click();
		await page
			.locator('.linker-genie-app__composer')
			.waitFor({state: 'visible', timeout: 30000});
		await page.waitForTimeout(1200);
		const expanded = await page.evaluate(() => {
			const r = (e) => {
				if (!e) return null;
				const b = e.getBoundingClientRect();
				return [
					Math.round(b.x),
					Math.round(b.y + scrollY),
					Math.round(b.width),
					Math.round(b.height),
				];
			};
			const app = document.querySelector('.linker-genie-app');
			const panel = document.querySelector('.linker-genie-app__panel');
			const composer = document.querySelector('.linker-genie-app__composer');
			const ar = r(app);
			const pr = r(panel);
			const inside =
				!!ar &&
				!!pr &&
				pr[0] >= ar[0] &&
				pr[1] >= ar[1] &&
				pr[0] + pr[2] <= ar[0] + ar[2] + 1 &&
				pr[1] + pr[3] <= ar[1] + ar[3] + 1;
			return {
				appRect: ar,
				panelRect: pr,
				insideCard: inside,
				composerVisible: !!composer && composer.getBoundingClientRect().height > 0,
				maxHeightCapPx: Math.round(0.72 * innerHeight),
				respectsCap: !!ar && ar[3] <= Math.ceil(0.72 * innerHeight),
			};
		});
		await page.screenshot({path: out + `/C2_genie-mobile-open-390-${phase}.png`});
		await record('C2_shop_expand', expanded);
	} else {
		await page.screenshot({path: out + `/C2_genie-mobile-open-390-${phase}.png`});
		await record('C2_shop_expand', {
			toggleVisible: false,
			note: 'the Open button sits in the display:none dock tree: the conversation is unreachable — the defect C2 fixes',
		});
	}
	await ctx.close();
}

await browser.close();
