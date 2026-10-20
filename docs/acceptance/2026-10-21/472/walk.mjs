/**
 * Production guest walk for #472 (add-all and save).
 *
 * Clicks the configurator: inputs → solution → design report → Add all →
 * Save. The add-all button is the Store API write. Cleanup is remove-item,
 * then a cart read-back of remaining 0. No inquiry, no registration, no
 * login, no mail.
 *
 * Reference: docs/research/2026-10-21-configurator-rooftop/matrix/production-draft.mjs
 */
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(
	'/Users/chesterjohn/Documents/de-linker/tests/e2e/package.json'
);
const { chromium } = require('playwright');

const here = dirname(fileURLToPath(import.meta.url));
const shotsDir = join(here, 'shots');
mkdirSync(shotsDir, { recursive: true });

const ORIGIN = 'https://de-linker.com';
const MONEY = /(?:€|EUR)\s*\d|\d[\d.,]*\s*(?:€|EUR)/;
const CASES = [
	{
		lang: 'en',
		cfg: '/solution-configurator/',
		cart: '/cart/',
		account: '/my-account/saved-solutions/',
		locale: 'en-GB',
		expectLang: 'en',
		added: 'All products are in your solution draft.',
		partial: 'Some products are not confirmed',
		saved: 'Saved to your account.',
		saveFailed: 'could not be saved',
		priceNote: 'Log in for prices',
		draftNote: 'without an account',
	},
	{
		lang: 'de',
		cfg: '/de/loesungskonfigurator/',
		cart: '/de/loesungsentwurf/',
		account: '/de/mein-konto/saved-solutions/',
		locale: 'de-DE',
		expectLang: 'de',
		added: 'Alle Produkte sind in Ihrem Lösungsentwurf.',
		partial: 'nicht bestätigt',
		saved: 'In Ihrem Konto gespeichert.',
		saveFailed: 'konnte nicht gespeichert',
		priceNote: 'Preise nach Anmeldung',
		draftNote: 'ohne Konto',
	},
];

const record = {
	ticket: 472,
	engine: 'production',
	origin: ORIGIN,
	guestOnly: true,
	mailSent: false,
	inquirySent: false,
	registered: false,
	loggedIn: false,
	startedAt: new Date().toISOString(),
	inputs: { plz: '80538', annual_kwh: 4500, pv_kwp: 10, phase: 3, backup: 'none' },
	forbiddenPosts: [],
	cases: [],
};

function writeRecord() {
	writeFileSync(join(here, 'record.json'), JSON.stringify(record, null, 2));
}

function moneyHits(text) {
	return (text || '').match(/(?:€|EUR)\s*[\d][\d.,]*|[\d][\d.,]*\s*(?:€|EUR)/g) || [];
}

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

async function quiet(page) {
	await page
		.addStyleTag({
			content:
				'*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}',
		})
		.catch(() => {});
}

async function shoot(page, fileBase, scrollSelector, block = 'start') {
	const taken = [];
	for (const vp of [
		{ width: 1440, height: 900, tag: '1440' },
		{ width: 390, height: 844, tag: '390' },
	]) {
		await page.setViewportSize({ width: vp.width, height: vp.height });
		if (scrollSelector) {
			const target = page.locator(scrollSelector).first();
			if (await target.count()) {
				await target
					.evaluate((el, how) => el.scrollIntoView({ block: how, inline: 'nearest' }), block)
					.catch(() => {});
			}
		}
		await page.waitForTimeout(350);
		const name = `${fileBase}-${vp.tag}.png`;
		await page.screenshot({ path: join(shotsDir, name), fullPage: false });
		taken.push(`shots/${name}`);
	}
	await page.setViewportSize({ width: 1440, height: 900 });
	return taken;
}

async function cartRead(page) {
	return page.evaluate(async () => {
		const response = await fetch('/wp-json/wc/store/v1/cart', { credentials: 'include' });
		const body = await response.json();
		const items = (body.items || []).map((item) => ({
			id: item.id,
			name: item.name,
			sku: item.sku || '',
			quantity: item.quantity,
			pricesNull: item.prices == null,
			price: item.prices ? String(item.prices.price) : null,
			regularPrice: item.prices ? String(item.prices.regular_price) : null,
			salePrice: item.prices ? String(item.prices.sale_price) : null,
			currency: item.prices ? item.prices.currency_code : null,
			rawPrice: item.prices && item.prices.raw_prices ? String(item.prices.raw_prices.price) : null,
			lineTotal: item.totals && item.totals.line_total != null ? String(item.totals.line_total) : null,
		}));
		const totals = body.totals || {};
		return {
			status: response.status,
			items,
			totalsPresent: Object.keys(totals),
			totalPrice: totals.total_price != null ? String(totals.total_price) : null,
			totalItems: totals.total_items != null ? String(totals.total_items) : null,
		};
	});
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
			removed.push({ id: item.id, status: response.status });
		}
		const after = await fetch(`${base}/cart`, { credentials: 'include' });
		const body = await after.json();
		return {
			removed,
			remaining: (body.items || []).length,
			left: (body.items || []).map((item) => ({ id: item.id, quantity: item.quantity })),
		};
	});
}

function compareLines(wanted, items) {
	const problems = [];
	const got = new Map();
	for (const item of items) {
		got.set(item.id, (got.get(item.id) || 0) + item.quantity);
	}
	for (const line of wanted) {
		const quantity = got.get(line.id) || 0;
		if (quantity !== line.quantity) {
			problems.push(`${line.model || line.id}: want ${line.quantity}, cart ${quantity}`);
		}
	}
	const ids = new Set(wanted.map((line) => line.id));
	for (const item of items) {
		if (!ids.has(item.id)) {
			problems.push(`extra cart line ${item.id} ${item.name} × ${item.quantity}`);
		}
	}
	return problems;
}

async function pageFacts(page) {
	return page.evaluate(() => ({
		url: location.href,
		lang: document.documentElement.lang,
		title: document.title,
		rail: document.querySelector('.linker-steps')?.innerText?.replace(/\s+/g, ' ').trim() || '',
		mounted: !!document.querySelector('[data-linker-app="configurator"]'),
		reportIds: [...document.querySelectorAll('#linker-report-section section')].map((node) =>
			node.getAttribute('aria-labelledby')
		),
		reportTitles: [...document.querySelectorAll('#linker-report-section h4')].map((node) =>
			node.textContent.trim()
		),
		status: document.querySelector('.linker-actions__status')?.innerText?.replace(/\s+/g, ' ').trim() || '',
		saveHref: document.querySelector('.linker-actions__status a')?.getAttribute('href') || '',
	}));
}

async function walk(browser, item) {
	const row = {
		lang: item.lang,
		at: new Date().toISOString(),
		posts: [],
		shots: {},
	};
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
		locale: item.locale,
		userAgent: 'de-linker-walk-472/1.0',
		reducedMotion: 'reduce',
	});
	const page = await context.newPage();
	await page.route('**/*', async (route) => {
		const request = route.request();
		const url = request.url();
		if (request.method() === 'POST') {
			const path = url.replace(ORIGIN, '').split('?')[0];
			row.posts.push(path);
			const forbidden =
				/\/checkout|proforma-request|proforma-anfrage|wp-login\.php|\/register|contact-form|admin-post\.php|wc\/store\/v1\/checkout/.test(
					url
				);
			if (forbidden) {
				record.forbiddenPosts.push({ lang: item.lang, url: path });
				await route.abort();
				return;
			}
		}
		await route.continue();
	});
	try {
		await page.goto(ORIGIN + item.cfg, { waitUntil: 'domcontentloaded', timeout: 45000 });
		await dismissConsent(page);
		await quiet(page);
		row.guest = await page.evaluate(async () => {
			const me = await fetch('/wp-json/wp/v2/users/me', { credentials: 'include' });
			const names = document.cookie
				.split(';')
				.map((part) => part.split('=')[0].trim())
				.filter(Boolean);
			return { usersMe: me.status, cookieNames: names };
		});
		if (row.guest.usersMe === 200) {
			row.abort = 'session is authenticated; no writes';
			return row;
		}
		const script = await page.locator('script[src*="configurator.js"]').first().getAttribute('src');
		row.bundle = script;
		if (script && !record.bundleSha256) {
			const absolute = new URL(script, ORIGIN).href;
			const response = await fetch(absolute);
			const bytes = Buffer.from(await response.arrayBuffer());
			record.bundleSha256 = createHash('sha256').update(bytes).digest('hex');
			record.bundleBytes = bytes.length;
			record.bundleUrl = absolute.split('?')[0];
		}
		await page.locator('#linker-plz').waitFor({ state: 'visible', timeout: 30000 });
		row.before = await cartRead(page);
		await page.locator('#linker-plz').fill('80538');
		await page.locator('#linker-annual').fill('4500');
		await page.locator('#linker-kwp').fill('10');
		await page.locator('#linker-phase-3').check();
		await page.locator('#linker-backup').selectOption('none');
		row.inputs = await pageFacts(page);
		row.shots.inputs = await shoot(page, `${item.lang}-inputs`, '#linker-inputs-section');

		const pending = page.waitForResponse(
			(response) =>
				response.url().includes('design/residential') && response.request().method() === 'POST',
			{ timeout: 180000 }
		);
		await page.locator('#linker-inputs-section form button[type="submit"]').click();
		const designResponse = await pending;
		row.designStatus = designResponse.status();
		const design = await designResponse.json().catch(() => ({}));
		row.design = {
			status: design.status || null,
			selected: design.selected
				? {
						inverter: design.selected.inverter?.model || null,
						battery: design.selected.battery?.model || null,
						release: design.selected.battery?.release?.verdict || null,
					}
				: null,
			lines: (design.selected?.lines || [])
				.filter((line) => line.product && line.product.id)
				.map((line) => ({
					id: line.product.id,
					sku: line.product.sku || '',
					model: line.product.model || '',
					role: line.role || '',
					quantity: line.quantity,
				})),
			installerLines: (design.selected?.lines || []).filter((line) => !line.product).length,
		};
		const addButton = page.getByRole('button', {
			name: /Add all to solution draft|Alles zum Lösungsentwurf/i,
		});
		await addButton.waitFor({ state: 'visible', timeout: 45000 });
		row.solution = await pageFacts(page);
		row.shots.solution = await shoot(page, `${item.lang}-solution`, '#linker-solution-section');
		await page.locator('#linker-report-section').waitFor({ state: 'visible', timeout: 20000 });
		row.report = await pageFacts(page);
		row.reportText = await page
			.locator('#linker-report-section')
			.innerText()
			.then((text) => text.replace(/\s+/g, ' ').slice(0, 1500))
			.catch(() => '');
		row.shots.report = await shoot(page, `${item.lang}-report`, '#linker-report-section');

		await addButton.click();
		const confirmation = page.getByText(
			/All products are in your solution draft|Alle Produkte sind in Ihrem Lösungsentwurf|Some products are not confirmed|nicht bestätigt/i
		);
		await confirmation.first().waitFor({ state: 'visible', timeout: 60000 });
		row.added = await pageFacts(page);
		row.afterAdd = await cartRead(page);
		row.lineDiff = compareLines(row.design.lines, row.afterAdd.items);
		row.shots.added = await shoot(page, `${item.lang}-added`, '.linker-actions__status', 'center');

		const saveWait = page.waitForResponse(
			(response) =>
				response.url().includes('linker/v1/solutions') && response.request().method() === 'POST',
			{ timeout: 30000 }
		);
		await page.getByRole('button', { name: /Save solution|Lösung speichern/ }).click();
		const saveResponse = await saveWait;
		row.save = {
			status: saveResponse.status(),
			body: await saveResponse.json().catch(() => null),
		};
		await page
			.getByText(/Saved to your account|In Ihrem Konto gespeichert|could not be saved|konnte nicht gespeichert/i)
			.first()
			.waitFor({ state: 'visible', timeout: 15000 })
			.catch(() => {});
		row.saved = await pageFacts(page);
		row.cookieNamesAfterSave = await page.evaluate(() =>
			document.cookie
				.split(';')
				.map((part) => part.split('=')[0].trim())
				.filter(Boolean)
		);
		row.shots.save = await shoot(page, `${item.lang}-save`, '.linker-actions__status', 'center');

		const accountUrl = row.saved.saveHref
			? new URL(row.saved.saveHref, ORIGIN).href
			: ORIGIN + item.account;
		row.accountRequested = accountUrl;
		await page.goto(accountUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
		await dismissConsent(page);
		row.account = await page.evaluate(() => ({
			url: location.href,
			lang: document.documentElement.lang,
			title: document.title,
			hasPassword: !!document.querySelector('input[type="password"]'),
			hasRegisterForm: !!document.querySelector('form.register, #reg_email'),
			text: (document.querySelector('main')?.innerText || '').replace(/\s+/g, ' ').slice(0, 800),
		}));
		row.shots.account = await shoot(page, `${item.lang}-account`, 'main');

		await page.goto(ORIGIN + item.cart, { waitUntil: 'domcontentloaded', timeout: 45000 });
		await dismissConsent(page);
		await quiet(page);
		row.draft = await page.evaluate(() => {
			const shown = (node) => {
				const style = getComputedStyle(node);
				return style.display !== 'none' && style.visibility !== 'hidden';
			};
			const rows = [
				...document.querySelectorAll(
					'tr.cart_item, .woocommerce-cart-form__cart-item, .wc-block-cart-items__row'
				),
			];
			return {
				url: location.href,
				lang: document.documentElement.lang,
				title: document.title,
				lines: rows.map((item) => ({
					name: (item.querySelector('.product-name, .wc-block-components-product-name')?.innerText || '')
						.replace(/\s+/g, ' ')
						.trim(),
					qty: item.querySelector('input.qty, .wc-block-components-quantity-selector__input')?.value || '',
				})),
				amounts: [...document.querySelectorAll('.woocommerce-Price-amount, .wc-block-formatted-money-amount')]
					.filter(shown)
					.map((node) => node.innerText.replace(/\s+/g, ' ').trim()),
				text: (document.querySelector('main')?.innerText || '').replace(/\s+/g, ' ').slice(0, 1800),
			};
		});
		row.draftCart = await cartRead(page);
		row.draftDiff = compareLines(row.design.lines, row.draftCart.items);
		row.shots.draft = await shoot(page, `${item.lang}-draft`, '.woocommerce-cart-form, .wc-block-cart, main');
	} catch (failure) {
		row.error = String(failure && failure.message ? failure.message : failure);
		const failName = `${item.lang}-error-1440.png`;
		await page.screenshot({ path: join(shotsDir, failName), fullPage: false }).catch(() => {});
		row.errorShot = `shots/${failName}`;
	} finally {
		row.emptied = await emptyDraft(page).catch((failure) => ({
			error: String(failure && failure.message ? failure.message : failure),
		}));
		if (row.emptied && row.emptied.remaining > 0) {
			row.emptiedRetry = await emptyDraft(page).catch((failure) => ({
				error: String(failure && failure.message ? failure.message : failure),
			}));
		}
		await page.goto(ORIGIN + item.cart, { waitUntil: 'domcontentloaded', timeout: 45000 }).catch(() => {});
		row.emptiedRead = await cartRead(page).catch((failure) => ({
			error: String(failure && failure.message ? failure.message : failure),
		}));
		const emptyShot = `${item.lang}-emptied-1440.png`;
		await page.screenshot({ path: join(shotsDir, emptyShot), fullPage: false }).catch(() => {});
		row.emptiedShot = `shots/${emptyShot}`;
		await context.close();
	}
	return row;
}

const browser = await chromium.launch({ headless: true });
try {
	for (const item of CASES) {
		console.log('walk', item.lang);
		const row = await walk(browser, item);
		record.cases.push(row);
		record.updatedAt = new Date().toISOString();
		writeRecord();
		console.log(
			item.lang,
			row.error || row.design?.status,
			'lines',
			(row.design && row.design.lines && row.design.lines.length) || 0,
			'diff',
			row.lineDiff || [],
			'save',
			row.save && row.save.status,
			'remaining',
			row.emptied && row.emptied.remaining
		);
	}
} finally {
	await browser.close();
	record.finishedAt = new Date().toISOString();
	writeRecord();
}
console.log('wrote', record.cases.length);
