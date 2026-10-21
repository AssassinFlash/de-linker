/**
 * Local guest and member walk for #473 (the German save link opens the German
 * account page).
 *
 * Guest: no login, save from the German configurator, read the POST's `url`
 * and the page's "Open saved solution" link, open it, record the wall.
 * Member: one logged-in context (a one-time login link, no mail), save in EN
 * and DE, open each answered link, record the account list.
 *
 * Cleanup is remove-item plus a cart read-back of remaining 0. No inquiry, no
 * registration, no login form, no mail.
 *
 * Instance: `just up fix473` + `just pull load fix473 …` + `just serve fix473`.
 * Run: node walk.mjs [login-url].
 */
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

const ORIGIN = 'http://127.0.0.1:9249';
const CASES = [
	{
		lang: 'en',
		cfg: '/solution-configurator/',
		cart: '/cart/',
		locale: 'en-GB',
		saved: 'Saved to your account',
	},
	{
		lang: 'de',
		cfg: '/de/loesungskonfigurator/',
		cart: '/de/loesungsentwurf/',
		locale: 'de-DE',
		saved: 'In Ihrem Konto gespeichert',
	},
];

const record = {
	ticket: 473,
	engine: 'local snapshot instance fix473',
	origin: ORIGIN,
	guest: [],
	member: [],
	mailSent: false,
	inquirySent: false,
	registered: false,
	startedAt: new Date().toISOString(),
	forbiddenPosts: [],
};

function writeRecord() {
	writeFileSync(join(here, 'record.json'), JSON.stringify(record, null, 2));
}

async function dismissConsent(page) {
	const accept = page.locator('[data-cky-tag="accept-button"]');
	try {
		await accept.waitFor({ state: 'visible', timeout: 3000 });
		await accept.evaluate((button) => button.click());
		await page
			.locator('.cky-consent-container')
			.waitFor({ state: 'hidden', timeout: 3000 });
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
					.evaluate(
						(el, how) =>
							el.scrollIntoView({ block: how, inline: 'nearest' }),
						block
					)
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
			left: (body.items || []).map((item) => ({
				id: item.id,
				quantity: item.quantity,
			})),
		};
	});
}

async function pageFacts(page) {
	return page.evaluate(() => ({
		url: location.href,
		lang: document.documentElement.lang,
		title: document.title,
		status:
			document
				.querySelector('.linker-actions__status')
				?.innerText?.replace(/\s+/g, ' ')
				.trim() || '',
		saveHref:
			document
				.querySelector('.linker-actions__status a')
				?.getAttribute('href') || '',
	}));
}

async function accountFacts(page) {
	return page.evaluate(() => {
		const main = document.querySelector('main');
		return {
			url: location.href,
			lang: document.documentElement.lang,
			title: document.title,
			hasPassword: !!document.querySelector('input[type="password"]'),
			hasRegisterForm: !!document.querySelector('form.register, #reg_email'),
			links: [...document.querySelectorAll('main a')]
				.map((node) => ({
					text: node.textContent.replace(/\s+/g, ' ').trim(),
					href: node.getAttribute('href'),
				}))
				.filter((link) =>
					/solution|loesung|lösung/i.test(
						`${link.text} ${link.href}`
					)
				)
				.slice(0, 12),
			text: (main?.innerText || '').replace(/\s+/g, ' ').slice(0, 900),
		};
	});
}

async function saveFromConfigurator(page, item, row) {
	await page.goto(ORIGIN + item.cfg, {
		waitUntil: 'domcontentloaded',
		timeout: 45000,
	});
	await dismissConsent(page);
	await quiet(page);
	await page.locator('#linker-plz').waitFor({
		state: 'visible',
		timeout: 30000,
	});
	await page.locator('#linker-plz').fill('80538');
	await page.locator('#linker-annual').fill('4500');
	await page.locator('#linker-kwp').fill('10');
	await page.locator('#linker-phase-3').check();
	await page.locator('#linker-backup').selectOption('none');

	const pending = page.waitForResponse(
		(response) =>
			response.url().includes('design/residential') &&
			response.request().method() === 'POST',
		{ timeout: 180000 }
	);
	await page
		.locator('#linker-inputs-section form button[type="submit"]')
		.click();
	const designResponse = await pending;
	row.designStatus = designResponse.status();
	const design = await designResponse.json().catch(() => ({}));
	row.lines = (design.selected?.lines || [])
		.filter((line) => line.product && line.product.id)
		.map((line) => ({
			id: line.product.id,
			model: line.product.model || '',
			quantity: line.quantity,
		}));

	const addButton = page.getByRole('button', {
		name: /Add all to solution draft|Alles zum Lösungsentwurf/i,
	});
	await addButton.waitFor({ state: 'visible', timeout: 45000 });
	await addButton.click();
	await page
		.getByText(
			/All products are in your solution draft|Alle Produkte sind in Ihrem Lösungsentwurf|Some products are not confirmed|nicht bestätigt/i
		)
		.first()
		.waitFor({ state: 'visible', timeout: 60000 });

	const saveWait = page.waitForResponse(
		(response) =>
			response.url().includes('linker/v1/solutions') &&
			response.request().method() === 'POST',
		{ timeout: 30000 }
	);
	await page
		.getByRole('button', { name: /Save solution|Lösung speichern/ })
		.click();
	const saveResponse = await saveWait;
	row.saveRequested = saveResponse.url();
	row.save = {
		status: saveResponse.status(),
		body: await saveResponse.json().catch(() => null),
	};
	await page
		.getByText(
			/Saved to your account|In Ihrem Konto gespeichert|could not be saved|konnte nicht gespeichert/i
		)
		.first()
		.waitFor({ state: 'visible', timeout: 15000 })
		.catch(() => {});
	row.saved = await pageFacts(page);
	row.shots = {
		save: await shoot(
			page,
			`${item.lang}-${row.kind}-save`,
			'.linker-actions__status',
			'center'
		),
	};

	row.accountRequested = row.saved.saveHref
		? new URL(row.saved.saveHref, ORIGIN).href
		: '';
	await page.goto(row.accountRequested, {
		waitUntil: 'domcontentloaded',
		timeout: 45000,
	});
	await dismissConsent(page);
	await quiet(page);
	row.account = await accountFacts(page);
	row.shots.account = await shoot(
		page,
		`${item.lang}-${row.kind}-account`,
		'main'
	);

	await page.goto(ORIGIN + item.cart, {
		waitUntil: 'domcontentloaded',
		timeout: 45000,
	});
	await dismissConsent(page);
	row.cleanup = await emptyDraft(page);
}

async function walkGuest(browser, item) {
	const row = { kind: 'guest', lang: item.lang, at: new Date().toISOString() };
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
		locale: item.locale,
		userAgent: 'de-linker-walk-473/1.0',
		reducedMotion: 'reduce',
	});
	const page = await context.newPage();
	page.on('request', (request) => {
		if (request.method() !== 'POST') {
			return;
		}
		const path = request.url().replace(ORIGIN, '').split('?')[0];
		row.posts = row.posts || [];
		row.posts.push(path);
		if (
			/\/checkout|proforma-request|proforma-anfrage|wp-login\.php|\/register|contact-form|admin-post\.php|wc\/store\/v1\/checkout/.test(
				request.url()
			)
		) {
			record.forbiddenPosts.push({ lang: item.lang, url: path });
		}
	});
	try {
		await saveFromConfigurator(page, item, row);
		row.guestCheck = await page.evaluate(async () => {
			const me = await fetch('/wp-json/wp/v2/users/me', {
				credentials: 'include',
			});
			return me.status;
		});
	} catch (failure) {
		row.error = String(failure && failure.message ? failure.message : failure);
	} finally {
		await context.close();
		record.guest.push(row);
		writeRecord();
	}
	return row;
}

async function walkMember(browser, loginUrl) {
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
		locale: 'de-DE',
		userAgent: 'de-linker-walk-473/1.0',
		reducedMotion: 'reduce',
	});
	const page = await context.newPage();
	await page.goto(loginUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
	const me = await page.evaluate(async () => {
		const response = await fetch('/wp-json/wp/v2/users/me', {
			credentials: 'include',
		});
		return response.status;
	});
	record.memberUser = me;
	for (const item of CASES) {
		const row = { kind: 'member', lang: item.lang, at: new Date().toISOString() };
		try {
			await saveFromConfigurator(page, item, row);
		} catch (failure) {
			row.error = String(
				failure && failure.message ? failure.message : failure
			);
		}
		record.member.push(row);
		writeRecord();
	}
	await context.close();
}

const browser = await chromium.launch();
try {
	for (const item of CASES) {
		await walkGuest(browser, item);
	}
	const loginUrl = process.argv[2];
	if (loginUrl) {
		await walkMember(browser, loginUrl);
	}
} finally {
	record.finishedAt = new Date().toISOString();
	writeRecord();
	await browser.close();
}
console.log(JSON.stringify(record, null, 2));
