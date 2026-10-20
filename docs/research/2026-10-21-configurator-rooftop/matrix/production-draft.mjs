/**
 * Production guest draft probe for #445. Store API writes, then a Genie turn
 * on the cart page, then the lines are removed. No mail, no account, no inquiry.
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(
	'/Users/chesterjohn/Documents/de-linker/tests/e2e/package.json'
);
const { chromium } = require('playwright');

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, 'shots');
const ORIGIN = 'https://de-linker.com';
const IDS = [3556, 3611];

const cases = [
	{
		id: 'guest-en',
		lang: 'en',
		cart: '/cart/',
		question:
			'What products are in my solution draft, and how many of each? What is the price of each?',
	},
	{
		id: 'guest-de',
		lang: 'de',
		cart: '/de/loesungsentwurf/',
		question:
			'Welche Produkte stehen in meinem Lösungsentwurf, und wie viele von jedem? Was kostet jedes?',
	},
];

async function dismissConsent(page) {
	const accept = page.locator('[data-cky-tag="accept-button"]');
	try {
		await accept.waitFor({ state: 'visible', timeout: 5000 });
		await accept.evaluate((button) => button.click());
		await page.locator('.cky-consent-container').waitFor({ state: 'hidden', timeout: 5000 });
	} catch {
		// Already chosen, or this page has no banner.
	}
}

async function cartState(page) {
	return page.evaluate(async (ids) => {
		const read = await fetch('/wp-json/wc/store/v1/cart', { credentials: 'include' });
		const body = await read.json();
		const items = (body.items || []).map((item) => ({
			id: item.id,
			name: item.name,
			quantity: item.quantity,
			sku: item.sku || '',
		}));
		return {
			status: read.status,
			items,
			wanted: ids.map((id) => ({
				id,
				quantity: items.filter((item) => item.id === id).reduce((sum, item) => sum + item.quantity, 0),
			})),
		};
	}, IDS);
}

async function addWanted(page) {
	return page.evaluate(async (ids) => {
		const base = '/wp-json/wc/store/v1';
		const read = await fetch(`${base}/cart`, { credentials: 'include' });
		let nonce = read.headers.get('Nonce') || '';
		const before = await read.json();
		const have = new Map();
		for (const item of before.items || []) {
			have.set(item.id, (have.get(item.id) || 0) + item.quantity);
		}
		const writes = [];
		for (const id of ids) {
			const already = have.get(id) || 0;
			if (already >= 1) {
				writes.push({ id, skipped: true, already });
				continue;
			}
			const response = await fetch(`${base}/cart/add-item`, {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json', Nonce: nonce },
				body: JSON.stringify({ id, quantity: 1 }),
			});
			nonce = response.headers.get('Nonce') || nonce;
			writes.push({ id, status: response.status });
		}
		const after = await fetch(`${base}/cart`, { credentials: 'include' });
		const cart = await after.json();
		return {
			writes,
			items: (cart.items || []).map((item) => ({
				id: item.id,
				name: item.name,
				quantity: item.quantity,
				sku: item.sku || '',
			})),
		};
	}, IDS);
}

async function emptyDraft(page) {
	return page.evaluate(async () => {
		const base = '/wp-json/wc/store/v1';
		const read = await fetch(`${base}/cart`, { credentials: 'include' });
		let nonce = read.headers.get('Nonce') || '';
		const cart = await read.json();
		const removed = [];
		for (const item of cart.items || []) {
			const response = await fetch(`${base}/cart/remove-item`, {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json', Nonce: nonce },
				body: JSON.stringify({ key: item.key }),
			});
			nonce = response.headers.get('Nonce') || nonce;
			removed.push(response.status);
		}
		const after = await fetch(`${base}/cart`, { credentials: 'include' });
		const body = await after.json();
		return { removed, remaining: (body.items || []).length };
	});
}

function judge(answer) {
	const text = answer || '';
	const money = /(?:€|EUR)\s*\d|\d[\d.,]*\s*(?:€|EUR)/.test(text);
	const statesOne = /(?:^|[^\d])1(?:[^\d]|$)/.test(text) && /quantit|Stück|Menge|how many|wie viele/i.test(text);
	const denies = /does not print a quantity|not stated|führt der Entwurf nicht|keine Menge|nicht angegeben|Stückzahlen führt/i.test(text);
	return { money, statesOne, denies, chars: text.length };
}

const rows = [];
const browser = await chromium.launch({ headless: true });
try {
	for (const item of cases) {
		const context = await browser.newContext({
			viewport: { width: 1440, height: 900 },
			userAgent: 'de-linker-matrix-445/1.0',
		});
		const page = await context.newPage();
		const row = { engine: 'prod', state: 'guest', lang: item.lang, at: new Date().toISOString() };
		try {
			await page.goto(ORIGIN + item.cart, { waitUntil: 'domcontentloaded', timeout: 45000 });
			await dismissConsent(page);
			row.before = await cartState(page);
			row.add = await addWanted(page);
			await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
			await dismissConsent(page);
			row.afterReload = await cartState(page);
			const wide = `prod-draft-${item.id}-1440.png`;
			await page.screenshot({ path: join(shots, wide), fullPage: false });
			await page.setViewportSize({ width: 390, height: 844 });
			const narrow = `prod-draft-${item.id}-390.png`;
			await page.screenshot({ path: join(shots, narrow), fullPage: false });
			await page.setViewportSize({ width: 1440, height: 900 });
			row.cartShots = [`shots/${wide}`, `shots/${narrow}`];

			const dock = page.locator('.linker-genie-open').first();
			await dock.waitFor({ state: 'visible', timeout: 20000 });
			await dock.click();
			const input = page.locator('#linker-genie-input');
			await input.waitFor({ state: 'visible', timeout: 20000 });
			await input.fill(item.question);
			const pending = page.waitForResponse(
				(response) => response.url().includes('/genie/turn') && response.request().method() === 'POST',
				{ timeout: 180000 }
			);
			await input.press('Enter');
			const response = await pending;
			const body = await response.text();
			row.turnStatus = response.status();
			let stream = body;
			try {
				const parsed = JSON.parse(body);
				if (typeof parsed.stream === 'string') {
					stream = parsed.stream;
					row.conversationId = parsed.conversation_id ?? null;
				}
			} catch {
				// Non-JSON is kept as the raw answer text below.
			}
			const texts = [...stream.matchAll(/"text"\s*:\s*"((?:\\.|[^"\\])*)"/g)].map((match) =>
				JSON.parse(`"${match[1]}"`)
			);
			row.answer = texts.join('\n');
			row.judge = judge(row.answer);
			await page
				.locator('.linker-genie-app__message, .linker-genie-app__error')
				.last()
				.waitFor({ state: 'visible', timeout: 20000 })
				.catch(() => {});
			await page.waitForTimeout(1500);
			const genieWide = `prod-draft-${item.id}-genie-1440.png`;
			await page.screenshot({ path: join(shots, genieWide), fullPage: false });
			await page.setViewportSize({ width: 390, height: 844 });
			const genieNarrow = `prod-draft-${item.id}-genie-390.png`;
			await page.screenshot({ path: join(shots, genieNarrow), fullPage: false });
			row.genieShots = [`shots/${genieWide}`, `shots/${genieNarrow}`];
			row.panel = await page.locator('.linker-genie-app').innerText().catch(() => '');
		} catch (failure) {
			row.error = String(failure && failure.message ? failure.message : failure);
			const failShot = `prod-draft-${item.id}-error.png`;
			await page.screenshot({ path: join(shots, failShot), fullPage: false }).catch(() => {});
			row.errorShot = `shots/${failShot}`;
		} finally {
			row.emptied = await emptyDraft(page).catch((failure) => ({
				error: String(failure && failure.message ? failure.message : failure),
			}));
			await context.close();
		}
		rows.push(row);
		console.log(item.id, row.turnStatus || row.error, row.judge || '', 'remaining', row.emptied && row.emptied.remaining);
	}
} finally {
	await browser.close();
}

writeFileSync(join(here, 'production-draft.json'), JSON.stringify(rows, null, 2));
console.log('wrote', rows.length);
