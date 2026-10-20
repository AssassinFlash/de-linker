/**
 * #445 Genie ↔ Configurator integration matrix.
 *
 * Local only for anything that writes (Genie turns, carts, logins).
 * Production is GET + screenshot, never a turn and never add-to-cart.
 *
 *   node harness.mjs
 */
import { createRequire } from 'node:module';
import { execFile } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const exec = promisify(execFile);
const here = dirname(fileURLToPath(import.meta.url));
const worktree = join(here, '../../../..');
const shots = join(here, 'shots');
const WP = process.env.M445_WP || 'http://127.0.0.1:9231';
const LIVE = 'https://de-linker.com';

const { chromium } = createRequire(
	'/Users/chesterjohn/Documents/de-linker/tests/e2e/package.json'
)('playwright');

const PROMPTS = {
	en: 'Residential site with 10 kWp PV and 4500 kWh per year, three-phase, postcode 80538, backup needed.',
	de: 'Wohngebäude mit 10 kWp PV und 4500 kWh im Jahr, dreiphasig, PLZ 80538, Notstrom benötigt.',
};
const DRAFT_ASK = {
	en: 'What products are in my solution draft, and how many of each? What is the price of each?',
	de: 'Welche Produkte stehen in meinem Lösungsentwurf, und wie viele von jedem? Was kostet jedes?',
};
const PATHS = {
	en: { home: '/', cfg: '/solution-configurator/', cart: '/cart/' },
	de: {
		home: '/de/',
		cfg: '/de/loesungskonfigurator/',
		cart: '/de/loesungsentwurf/',
	},
};
const USERS = { approved: 'm445-approved', pending: 'm445-pending' };
const MONEY = /(?:€|EUR)\s*\d|\d[\d.,]*\s*(?:€|EUR)/;

mkdirSync(shots, { recursive: true });

const rows = [];

function row(fields) {
	rows.push(fields);
	const mark = fields.verdict === 'pass' ? 'PASS' : 'FAIL';
	console.log(
		`${mark} ${fields.link} ${fields.state} ${fields.lang} ${fields.viewport} ${fields.notes || ''}`
	);
}

async function shot(page, name) {
	const path = join(shots, name);
	await page.screenshot({ path, fullPage: false, animations: 'disabled' });
	return `shots/${name}`;
}

async function quiet(page) {
	await page.addStyleTag({
		content:
			'*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}',
	}).catch(() => {});
	const accept = page.locator('.cky-btn-accept').first();
	if (await accept.isVisible().catch(() => false)) {
		await accept.click({ timeout: 3000 }).catch(() => {});
	}
}

async function login(context, user) {
	const { stdout } = await exec('just', ['login', 'm445', `--user=${user}`], {
		cwd: worktree,
	});
	const url = stdout.trim().split('\n').filter((line) => line.startsWith('http')).pop();
	if (!url) {
		throw new Error(`no login url for ${user}`);
	}
	const page = await context.newPage();
	await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
	await page.close();
}

async function openGenie(page) {
	const dock = page.locator('.linker-genie-open').first();
	await dock.waitFor({ state: 'visible', timeout: 20000 });
	await dock.click();
	await page.locator('#linker-genie-input').waitFor({ state: 'visible', timeout: 20000 });
}

async function ask(page, prompt) {
	await openGenie(page);
	const input = page.locator('#linker-genie-input');
	await input.fill(prompt);
	const pending = page.waitForResponse(
		(response) =>
			response.url().includes('/genie/turn') &&
			response.request().method() === 'POST',
		{ timeout: 180000 }
	);
	await input.press('Enter');
	const response = await pending;
	const body = await response.text();
	await page
		.locator('.linker-genie-app__action, .linker-genie-app__error, .linker-genie-app__message')
		.last()
		.waitFor({ state: 'visible', timeout: 20000 })
		.catch(() => {});
	return { status: response.status(), body };
}

function actionUrl(sse) {
	const match = sse.match(/"name"\s*:\s*"open_configurator"[\s\S]{0,400}?"url"\s*:\s*"([^"]+)"/);
	if (match) {
		return match[1].replace(/\\\//g, '/');
	}
	const loose = sse.match(/solution-configurator\/\?[^"\\]+|loesungskonfigurator\/\?[^"\\]+/);
	return loose ? loose[0] : '';
}

async function readForm(page) {
	await page.locator('#linker-plz').waitFor({ state: 'visible', timeout: 20000 });
	return page.evaluate(() => {
		const value = (id) => document.getElementById(id)?.value ?? null;
		const phase = document.querySelector('input[name="phase"]:checked')?.value ?? null;
		return {
			htmlLang: document.documentElement.lang,
			appLang: document.querySelector('.linker-configurator')?.getAttribute('lang') || '',
			plz: value('linker-plz'),
			annual: value('linker-annual'),
			kwp: value('linker-kwp'),
			phase,
			backup: value('linker-backup'),
			steps: [...document.querySelectorAll('.linker-steps__item')].map((node) =>
				node.textContent.replace(/\s+/g, ' ').trim()
			),
			sections: ['linker-inputs-section', 'linker-solution-section', 'linker-report-section'].filter(
				(id) => document.getElementById(id)
			),
			title: document.querySelector('.linker-configurator__title')?.textContent?.trim() || '',
			mounted: Boolean(document.querySelector('[data-linker-app="configurator"]')),
		};
	});
}

function queryOf(url) {
	const parsed = new URL(url, WP);
	return Object.fromEntries(parsed.searchParams.entries());
}

function prefillOk(form, query, lang) {
	const notes = [];
	const annual = (form.annual || '').replace(',', '.');
	const kwp = (form.kwp || '').replace(',', '.');
	if (Number(kwp) !== Number(query.pv_kwp || '')) {
		notes.push(`pv_kwp field ${form.kwp || 'empty'} != ${query.pv_kwp}`);
	}
	if (Number(annual) !== Number(query.annual_kwh || '')) {
		notes.push(`annual field ${form.annual || 'empty'} != ${query.annual_kwh}`);
	}
	if (String(form.phase || '') !== String(query.phase || '')) {
		notes.push(`phase field ${form.phase || 'empty'} != ${query.phase}`);
	}
	if ((form.backup || '') !== (query.backup || '')) {
		notes.push(`backup field ${form.backup || 'empty'} != ${query.backup}`);
	}
	if ((form.plz || '') !== (query.plz || '')) {
		notes.push(`plz field ${form.plz || 'empty'} != ${query.plz}`);
	}
	const want = lang === 'de' ? 'de' : 'en';
	if (!String(form.htmlLang || '').toLowerCase().startsWith(want)) {
		notes.push(`html lang ${form.htmlLang} != ${want}`);
	}
	return notes;
}

async function sizeHintCell(browser, state, lang) {
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
		locale: lang === 'de' ? 'de-DE' : 'en-GB',
	});
	if (state !== 'guest') {
		await login(context, USERS[state]);
	}
	const page = await context.newPage();
	let href = '';
	let form = null;
	let sse = '';
	let error = '';
	try {
		await page.goto(WP + PATHS[lang].home, { waitUntil: 'domcontentloaded', timeout: 30000 });
		await quiet(page);
		const turn = await ask(page, PROMPTS[lang]);
		sse = turn.body;
		href = await page.locator('.linker-genie-app__action').first().getAttribute('href').catch(() => '');
		if (!href) {
			href = actionUrl(sse);
		}
		await page.locator('.linker-genie-app').first().scrollIntoViewIfNeeded().catch(() => {});
		const wide = await shot(page, `l1-${state}-${lang}-1440-genie.png`);
		await page.setViewportSize({ width: 390, height: 844 });
		await page.waitForTimeout(300);
		const narrow = await shot(page, `l1-${state}-${lang}-390-genie.png`);
		if (!href) {
			error = `no open_configurator link (turn ${turn.status})`;
		} else {
			await page.setViewportSize({ width: 1440, height: 900 });
			await page.goto(href, { waitUntil: 'domcontentloaded', timeout: 30000 });
			await quiet(page);
			form = await readForm(page);
			const query = queryOf(page.url());
			const problems = prefillOk(form, query, lang);
			const path = new URL(page.url()).pathname;
			const wantPath = PATHS[lang].cfg;
			if (path !== wantPath) {
				problems.push(`landed ${path} != ${wantPath}`);
			}
			await page.locator('#linker-kwp').scrollIntoViewIfNeeded();
			const cfgWide = await shot(page, `l1-${state}-${lang}-1440-configurator.png`);
			await page.setViewportSize({ width: 390, height: 844 });
			await page.waitForTimeout(200);
			const cfgNarrow = await shot(page, `l1-${state}-${lang}-390-configurator.png`);
			const verdict = problems.length ? 'fail' : 'pass';
			for (const [viewport, evidence] of [
				['1440', cfgWide],
				['390', cfgNarrow],
			]) {
				row({
					link: 'size-hint',
					state,
					lang,
					viewport,
					verdict,
					evidence,
					notes: problems.join('; ') || 'fields, language and units match the stated size',
					observed: { href, query, form, genieShot: viewport === '1440' ? wide : narrow },
				});
			}
			await context.close();
			return { href, form, sse };
		}
	} catch (failure) {
		error = error || String(failure.message || failure);
	}
	for (const viewport of ['1440', '390']) {
		row({
			link: 'size-hint',
			state,
			lang,
			viewport,
			verdict: 'fail',
			evidence: `shots/l1-${state}-${lang}-${viewport}-genie.png`,
			notes: error,
			observed: { href, sse: sse.slice(0, 500) },
		});
	}
	await context.close();
	return { href, form, sse, error };
}

async function deepLinkCell(browser, state, lang, href) {
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
		locale: lang === 'de' ? 'de-DE' : 'en-GB',
	});
	if (state !== 'guest') {
		await login(context, USERS[state]);
	}
	const page = await context.newPage();
	if (!href) {
		for (const viewport of ['1440', '390']) {
			row({
				link: 'open_configurator',
				state,
				lang,
				viewport,
				verdict: 'fail',
				evidence: '',
				notes: 'Genie produced no open_configurator URL to follow',
				observed: {},
			});
		}
		await context.close();
		return;
	}
	try {
		await page.goto(href, { waitUntil: 'domcontentloaded', timeout: 30000 });
		await quiet(page);
		const form = await readForm(page);
		const path = new URL(page.url()).pathname;
		const problems = [];
		if (path !== PATHS[lang].cfg) {
			problems.push(`landed ${path} != ${PATHS[lang].cfg}`);
		}
		if (!form.mounted) {
			problems.push('configurator did not mount');
		}
		if (form.steps.length !== 3) {
			problems.push(`step rail has ${form.steps.length} items: ${form.steps.join(' | ')}`);
		}
		if (!form.sections.includes('linker-inputs-section') || !form.sections.includes('linker-solution-section')) {
			problems.push(`sections ${form.sections.join(',')}`);
		}
		const want = lang === 'de' ? 'de' : 'en';
		if (!String(form.htmlLang).toLowerCase().startsWith(want)) {
			problems.push(`html lang ${form.htmlLang}`);
		}
		await page.locator('.linker-steps').scrollIntoViewIfNeeded().catch(() => {});
		const wide = await shot(page, `l2-${state}-${lang}-1440.png`);
		await page.setViewportSize({ width: 390, height: 844 });
		await page.waitForTimeout(200);
		const narrow = await shot(page, `l2-${state}-${lang}-390.png`);
		const verdict = problems.length ? 'fail' : 'pass';
		row({
			link: 'open_configurator',
			state,
			lang,
			viewport: '1440',
			verdict,
			evidence: wide,
			notes: problems.join('; ') || `three-step rail: ${form.steps.join(' / ')}`,
			observed: { url: page.url(), form },
		});
		row({
			link: 'open_configurator',
			state,
			lang,
			viewport: '390',
			verdict,
			evidence: narrow,
			notes: problems.join('; ') || `three-step rail: ${form.steps.join(' / ')}`,
			observed: { url: page.url(), form },
		});
	} catch (failure) {
		for (const viewport of ['1440', '390']) {
			row({
				link: 'open_configurator',
				state,
				lang,
				viewport,
				verdict: 'fail',
				evidence: '',
				notes: String(failure.message || failure),
				observed: { href },
			});
		}
	}
	await context.close();
}

async function emptyDraft(page) {
	return page.evaluate(async () => {
		const base = '/wp-json/wc/store/v1';
		const read = await fetch(`${base}/cart`, { credentials: 'include' });
		let nonce = read.headers.get('Nonce') || '';
		const cart = await read.json();
		const removed = [];
		for (const item of cart.items || []) {
			const res = await fetch(`${base}/cart/remove-item`, {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json', Nonce: nonce },
				body: JSON.stringify({ key: item.key }),
			});
			nonce = res.headers.get('Nonce') || nonce;
			removed.push(res.status);
		}
		const after = await fetch(`${base}/cart`, {
			credentials: 'include',
			headers: { Nonce: nonce },
		});
		const body = await after.json();
		return { removed, remaining: (body.items || []).length };
	});
}

async function fillAndDesign(page) {
	await page.locator('#linker-plz').waitFor({ state: 'visible', timeout: 20000 });
	const emptied = await emptyDraft(page);
	await page.locator('#linker-plz').fill('80538');
	await page.locator('#linker-annual').fill('4500');
	await page.locator('#linker-kwp').fill('10');
	await page.locator('#linker-phase-3').check();
	// Spec 14 acceptance case is residential three-phase 10 kWp. Selecting
	// backup without a load and hours returns no candidate, so it is not used.
	await page.locator('#linker-backup').selectOption('none');
	const pending = page.waitForResponse(
		(response) => response.url().includes('design/residential') && response.request().method() === 'POST',
		{ timeout: 180000 }
	);
	await page.locator('form button[type="submit"]').click();
	const response = await pending;
	const design = await response.json().catch(() => ({}));
	await page.locator('#linker-solution-section').scrollIntoViewIfNeeded();
	const added = page.getByRole('button', { name: /Add all to solution draft|Alles zum Lösungsentwurf/i });
	await added.waitFor({ state: 'visible', timeout: 45000 });
	await added.click();
	await page
		.getByText(/All products are in your solution draft|Alle Produkte sind in Ihrem Lösungsentwurf|Some products are not confirmed/i)
		.first()
		.waitFor({ state: 'visible', timeout: 45000 });
	return { design, emptied };
}

async function draftCell(browser, state, lang) {
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
		locale: lang === 'de' ? 'de-DE' : 'en-GB',
	});
	if (state !== 'guest') {
		await login(context, USERS[state]);
	}
	const page = await context.newPage();
	try {
		await page.goto(WP + PATHS[lang].cfg, { waitUntil: 'domcontentloaded', timeout: 30000 });
		await quiet(page);
		const filled = await fillAndDesign(page);
		const design = filled.design;
		const lines = (design.selected?.lines || [])
			.filter((line) => line.product?.id)
			.map((line) => ({
				id: line.product.id,
				sku: line.product.sku,
				model: line.product.model,
				quantity: line.quantity,
			}));
		await page.locator('.linker-actions__status').scrollIntoViewIfNeeded().catch(() => {});
		const solutionShot = await shot(page, `l3-${state}-${lang}-solution.png`);
		await page.goto(WP + PATHS[lang].cart, { waitUntil: 'domcontentloaded', timeout: 30000 });
		await quiet(page);
		const cart = await page.evaluate(() => {
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
				lines: rows.map((item) => ({
					name: (item.querySelector('.product-name, .wc-block-components-product-name')?.innerText || '')
						.replace(/\s+/g, ' ')
						.trim(),
					qty: item.querySelector('input.qty, .wc-block-components-quantity-selector__input')?.value || '',
				})),
				amounts: [...document.querySelectorAll('.woocommerce-Price-amount, .wc-block-formatted-money-amount')]
					.filter(shown)
					.map((node) => node.innerText.replace(/\s+/g, ' ').trim()),
				text: (document.querySelector('main')?.innerText || '').slice(0, 2000),
			};
		});
		const turn = await ask(page, DRAFT_ASK[lang]);
		const panel = await page.locator('.linker-genie-app').first().innerText().catch(() => '');
		const cardPrices = await page
			.locator('.linker-card__price, .linker-card__price--net, .linker-card__price--note')
			.allInnerTexts()
			.catch(() => []);
		const spoken = `${panel}\n${turn.body}`;
		const moneyInAnswer = MONEY.test(panel) || cardPrices.some((text) => MONEY.test(text));
		const moneyOnCart = cart.amounts.some((text) => MONEY.test(text)) || MONEY.test(cart.text);
		const problems = [];
		if (design.status && design.status !== 'solution') {
			problems.push(`design status ${design.status}`);
		}
		if (filled.emptied.remaining !== 0) {
			problems.push(`draft was not empty before add-all (remaining ${filled.emptied.remaining})`);
		}
		if (!lines.length) {
			problems.push('design returned no product lines');
		}
		for (const line of lines) {
			const model = line.model || '';
			if (!spoken.includes(model)) {
				problems.push(`Genie did not name ${model}`);
			}
			const want = Number(line.quantity);
			const at = spoken.indexOf(model);
			const around =
				at < 0
					? ''
					: `${spoken.slice(Math.max(0, at - 70), at)} ${spoken.slice(at + model.length, at + model.length + 70)}`;
			const nearby = [...around.matchAll(/(?:^|[^\d])(\d{1,4})(?:[^\d]|$)/g)].map((match) => Number(match[1]));
			const wordForOne = /(?:^|[^A-Za-zÄÖÜäöü])(?:one|ein|eine)(?![A-Za-zÄÖÜäöü])/i.test(around);
			if (!nearby.includes(want) && !(want === 1 && wordForOne)) {
				problems.push(`quantity for ${model} not stated as ${want} (nearby ${nearby.join(',') || 'none'})`);
			}
			const cartLine = cart.lines.find((item) => item.name.includes(model));
			if (!cartLine) {
				problems.push(`draft page has no line for ${model}`);
			} else if (Number(cartLine.qty) !== want) {
				problems.push(`draft quantity for ${model} is ${cartLine.qty || 'empty'} != ${want}`);
			}
		}
		if (state === 'approved') {
			if (!moneyOnCart && !moneyInAnswer) {
				problems.push('approved account saw no price on the draft or in Genie');
			}
		} else if (moneyInAnswer || moneyOnCart) {
			problems.push(`price leak for ${state}`);
		}
		await page.locator('.linker-genie-app').first().scrollIntoViewIfNeeded().catch(() => {});
		const wide = await shot(page, `l3-${state}-${lang}-1440.png`);
		await page.setViewportSize({ width: 390, height: 844 });
		await page.waitForTimeout(200);
		const narrow = await shot(page, `l3-${state}-${lang}-390.png`);
		const verdict = problems.length ? 'fail' : 'pass';
		const notes =
			problems.join('; ') || 'draft lines match; Genie named products and quantities; price gate held';
		for (const [viewport, evidence] of [
			['1440', wide],
			['390', narrow],
		]) {
			row({
				link: 'draft',
				state,
				lang,
				viewport,
				verdict,
				evidence,
				notes,
				observed: {
					lines,
					cartLines: cart.lines,
					emptied: filled.emptied,
					designStatus: design.status,
					moneyInAnswer,
					moneyOnCart,
					cardPrices,
					cartAmounts: cart.amounts.slice(0, 8),
					panel: panel.slice(0, 1200),
					solutionShot,
				},
			});
		}
	} catch (failure) {
		const evidence = await shot(page, `l3-${state}-${lang}-error.png`).catch(() => '');
		for (const viewport of ['1440', '390']) {
			row({
				link: 'draft',
				state,
				lang,
				viewport,
				verdict: 'fail',
				evidence,
				notes: String(failure.message || failure),
				observed: {},
			});
		}
	}
	await context.close();
}

async function productionSmoke(browser) {
	const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const page = await context.newPage();
	const records = [];
	const pages = [
		['size-hint-url', `${LIVE}/solution-configurator/?pv_kwp=10&annual_kwh=4500&phase=3&backup=needed&plz=80538`],
		['cfg-de', `${LIVE}/de/loesungskonfigurator/?pv_kwp=10&annual_kwh=4500&phase=3&plz=80538`],
		['cart-en', `${LIVE}/cart/`],
		['cart-de', `${LIVE}/de/loesungsentwurf/`],
	];
	for (const [id, url] of pages) {
		await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
		await quiet(page);
		const form = id.startsWith('cart') ? null : await readForm(page).catch(() => null);
		await page.setViewportSize({ width: 1440, height: 900 });
		const wide = await shot(page, `prod-${id}-1440.png`);
		await page.setViewportSize({ width: 390, height: 844 });
		const narrow = await shot(page, `prod-${id}-390.png`);
		records.push({ id, url: page.url(), form, shots: [wide, narrow] });
		console.log(`PROD ${id} ${page.url()} lang=${form?.htmlLang || ''} kwp=${form?.kwp || ''}`);
	}
	await context.close();
	writeFileSync(join(here, 'production-smoke.json'), JSON.stringify(records, null, 2));
}

async function main() {
	const only = process.env.M445_ONLY || '';
	const browser = await chromium.launch({ headless: true });
	if (only !== 'draft') {
		const links = {};
		for (const state of ['guest', 'approved']) {
			for (const lang of ['en', 'de']) {
				links[`${state}-${lang}`] = await sizeHintCell(browser, state, lang);
			}
		}
		for (const state of ['guest', 'approved']) {
			for (const lang of ['en', 'de']) {
				await deepLinkCell(browser, state, lang, links[`${state}-${lang}`]?.href);
			}
		}
	}
	if (only !== 'links') {
		for (const state of ['guest', 'pending', 'approved']) {
			for (const lang of ['en', 'de']) {
				await draftCell(browser, state, lang);
			}
		}
	}
	if (!only) {
		await productionSmoke(browser);
	}
	await browser.close();
	let stored = rows;
	if (only === 'draft') {
		const { readFileSync } = await import('node:fs');
		const previous = JSON.parse(readFileSync(join(here, 'rows.json'), 'utf8'));
		stored = previous.filter((item) => item.link !== 'draft').concat(rows);
	}
	writeFileSync(join(here, 'rows.json'), JSON.stringify(stored, null, 2));
	const pass = stored.filter((item) => item.verdict === 'pass').length;
	console.log(`rows ${stored.length} pass ${pass} fail ${stored.length - pass}`);
}

main().catch((error) => {
	console.error(error);
	writeFileSync(join(here, 'rows-partial.json'), JSON.stringify(rows, null, 2));
	process.exit(1);
});
