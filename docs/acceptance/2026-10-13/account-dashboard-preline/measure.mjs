/**
 * Measures the computed style of the shared dashboard vocabulary on the
 * Preline reference pages (file://, assets local) and on our account area
 * (http://127.0.0.1:8975, signed in), at the same 1440x900 viewport.
 *
 * Usage:
 *   node measure.mjs ref            -> writes measurements-ref.json
 *   node measure.mjs ours <user>    -> writes measurements-ours.json
 *
 * Each probe is [name, page, selector, props]. Selectors are CSS, or XPath
 * when prefixed with "xpath=". Props are getComputedStyle property names;
 * "rect" collects getBoundingClientRect. A probe that matches nothing records
 * null so a failed selector is visible in the output instead of silent.
 */
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';

const here = path.dirname(fileURLToPath(import.meta.url));
const worktree = path.resolve(here, '../../../..');
const { chromium } = createRequire(path.join(worktree, 'tests/e2e/package.json'))('playwright');

const mode = process.argv[2] ?? 'ref';
const refRoot = 'file:///Users/chesterjohn/Downloads/preline-pro-templates%20(1)/dashboards/';
const oursBase = 'http://127.0.0.1:8975';
const locale = process.env.CAPTURE_LOCALE ?? 'en';

const BOX = ['backgroundColor', 'borderColor', 'borderWidth', 'borderRadius', 'boxShadow', 'padding', 'margin', 'gap', 'rect'];
const TYPE = ['fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing', 'textTransform', 'color'];

const REF = {
	'ref-overview': [
		`${refRoot}analytics-dashboard/index.html`,
		[
			['page.bg', 'body', ['backgroundColor']],
			['h1', 'xpath=//h1[contains(.,"Overview")]', TYPE],
			['sidebar.item', 'xpath=(//aside//a[contains(.,"Overview")] | //nav//a[contains(.,"Overview")])[1]', [...BOX, ...TYPE]],
			['tile', 'xpath=//*[@role="tab"][contains(.,"Users")]', BOX],
			['tile.label', 'xpath=//*[@role="tab"][contains(.,"Users")]//span[contains(@class,"text-muted-foreground-1") and contains(.,"Users")]', TYPE],
			['tile.number', 'xpath=//span[contains(@class,"xl:text-2xl") and contains(.,"54,382")]', TYPE],
			['card', 'xpath=//h2[contains(.,"Goal Conversions")]/ancestor::div[contains(@class,"bg-card")][1]', BOX],
			['card.heading', 'xpath=//h2[contains(.,"Goal Conversions")]', TYPE],
			['list.row', 'xpath=//*[contains(text(),"United States")][1]/ancestor::div[contains(@class,"grid") or contains(@class,"flex")][1]', BOX],
			['badge.beta', 'xpath=//*[contains(@class,"badge") or contains(@class,"inline-flex")][normalize-space(text())="Beta"][1]', [...BOX, ...TYPE]],
			['button.primary', 'xpath=//button[contains(.,"Add activity")] | //a[contains(.,"Add activity")]', [...BOX, ...TYPE]],
		],
	],
	'ref-inquiries': [
		`${refRoot}crm-dashboard/customers.html`,
		[
			['page.bg', 'body', ['backgroundColor']],
			['h1', 'xpath=//h2[contains(.,"All customers")]', TYPE],
			['table.card', 'xpath=//table[1]/ancestor::div[contains(@class,"border")][1]', BOX],
			['table.th', 'xpath=//table[1]//th[contains(.,"Name")]', [...BOX, ...TYPE]],
			['table.th-inner', 'xpath=//table[1]//th[contains(.,"Name")]//*[contains(text(),"Name")][1]', TYPE],
			['table.td', 'xpath=//table[1]//td[contains(.,"Amanda Harvey")]', [...BOX, ...TYPE]],
			['table.row', 'xpath=//table[1]//tr[contains(.,"Amanda Harvey")]', BOX],
			['chip', 'xpath=//a[contains(.,"Notion Ltd.")][1]', [...BOX, ...TYPE]],
			['button.primary', 'xpath=//button[contains(.,"New customer")] | //a[contains(.,"New customer")]', [...BOX, ...TYPE]],
			['toolbar.search', 'xpath=(//input[contains(@placeholder,"Search")])[1]', BOX],
		],
	],
	'ref-inquiry-detail': [
		`${refRoot}crm-dashboard/customer-details.html`,
		[
			['page.bg', 'body', ['backgroundColor']],
			['name', 'xpath=//h1[contains(.,"Amanda Harvey")]', TYPE],
			['tab.active', 'xpath=//*[@role="tab"][contains(.,"Details")]', [...BOX, ...TYPE]],
			['tablist', 'xpath=//*[@role="tablist"]', BOX],
			['section.h2', 'xpath=//p[contains(.,"General info")]', TYPE],
			['def.label', 'xpath=//dt[contains(.,"Gender")] | //*[contains(@class,"grid")]//span[contains(.,"Gender:")][1]', TYPE],
			['def.value', 'xpath=//*[contains(text(),"Female")][1]', TYPE],
			['def.row', 'xpath=//*[contains(text(),"Female")]/parent::*[1]', BOX],
			['action.button', 'xpath=//button[contains(.,"Add to list")][1]', [...BOX, ...TYPE]],
		],
	],
	'ref-documents': [
		`${refRoot}crm-dashboard/customer-details-invoices.html`,
		[
			['page.bg', 'body', ['backgroundColor']],
			['invoice.card', 'xpath=//span[contains(.,"Invoice for BlueVista")]/ancestor::div[contains(@class,"rounded-xl")][1]', BOX],
			['invoice.title', 'xpath=//span[contains(.,"Invoice for BlueVista")]', TYPE],
			['meta.label', 'xpath=//*[contains(text(),"Invoice date:")][1]', TYPE],
			['meta.value', 'xpath=//*[contains(text(),"April 5, 2025")][1]', TYPE],
			['total.amount', 'xpath=//*[contains(text(),"$1,000.00")][1]', TYPE],
			['badge.overdue', 'xpath=//*[contains(@class,"inline-flex")][contains(.,"Overdue")][1]', [...BOX, ...TYPE]],
			['badge.paid', 'xpath=//*[contains(@class,"inline-flex")][contains(.,"Paid")][1]', [...BOX, ...TYPE]],
			['button.ghost', 'xpath=//button[contains(.,"Resend")][1]', [...BOX, ...TYPE]],
			['link.view', 'xpath=//button[contains(.,"View details")][1] | //a[contains(.,"View details")][1]', TYPE],
		],
	],
	'ref-crm-index': [
		`${refRoot}crm-dashboard/index.html`,
		[
			['page.bg', 'body', ['backgroundColor']],
			['tile', 'xpath=//h2[contains(.,"Open deals")]/ancestor::div[contains(@class,"rounded-2xl")][1]', BOX],
			['tile.label', 'xpath=//h2[contains(.,"Open deals")]', TYPE],
			['tile.number', 'xpath=//h2[contains(.,"Open deals")]/following::div[contains(@class,"text-2xl")][1]', TYPE],
			['tiles.grid', 'xpath=//h2[contains(.,"Open deals")]/ancestor::div[contains(@class,"grid")][1]', ['gap', 'gridTemplateColumns', 'rect']],
			['h1', 'xpath=//h1[1]', TYPE],
		],
	],
	'ref-posts': [
		`${refRoot}cms-admin/posts.html`,
		[
			['page.bg', 'body', ['backgroundColor']],
			['table.th', 'xpath=(//table[1]//th)[1]', [...BOX, ...TYPE]],
			['table.th-inner', 'xpath=(//table[1]//th)[1]//span[1]', TYPE],
			['table.tr-head', 'xpath=//table[1]//thead//tr[1]', BOX],
			['table.td', 'xpath=(//table[1]//tbody//td)[1]', [...BOX, ...TYPE]],
			['table.tr', 'xpath=(//table[1]//tbody//tr)[1]', BOX],
		],
	],
	'ref-account-profile': [
		`${refRoot}admin-dashboard/account-profile.html`,
		[
			['page.bg', 'body', ['backgroundColor']],
			['sidebar', 'xpath=//aside[1]', BOX],
			['sidebar.item', 'xpath=(//aside//a | //aside//button)[contains(.,"Profile")][1]', [...BOX, ...TYPE]],
			['sidebar.item-active', 'xpath=(//aside//a | //aside//button)[contains(@class,"bg-sidebar-nav-active") or contains(@class,"active")][1]', [...BOX, ...TYPE]],
			['tab.active', 'xpath=//nav//a[contains(.,"Profile")][1]', BOX],
			['card', 'xpath=//h1[contains(.,"Profile")]/ancestor::div[contains(@class,"rounded-xl")][1]', BOX],
			['section.h2', 'xpath=//h2[contains(.,"Personal info")]', TYPE],
			['h1', 'xpath=//h1[contains(.,"Profile")]', TYPE],
			['section.desc', 'xpath=//p[contains(.,"Manage your name")]', TYPE],
			['form.label', 'xpath=//label[contains(.,"Name")][1]', TYPE],
			['form.input', 'xpath=//input[contains(@placeholder,"full name")][1]', BOX],
			['form.row', 'xpath=//input[contains(@placeholder,"full name")][1]/ancestor::div[contains(@class,"grid")][1]', BOX],
			['button.primary', 'xpath=(//button[contains(.,"Upload photo")])[1]', [...BOX, ...TYPE]],
			['button.danger-ghost', 'xpath=(//button[contains(.,"Delete")])[1]', [...BOX, ...TYPE]],
			['section.gap', 'xpath=//h2[contains(.,"Personal info")]/parent::*[1]', BOX],
		],
	],
};

const OURS = {
	'ours-overview': [
		`${oursBase}/my-account/`,
		[
			['page.bg', 'body', ['backgroundColor']],
			['content.bg', '.linker-account', ['backgroundColor']],
			['h1', '.linker-account-heading h1', TYPE],
			['sidebar', '.linker-account-sidebar', BOX],
			['sidebar.item', '.linker-account-nav-items a', [...BOX, ...TYPE]],
			['sidebar.item-active', '.linker-account-nav-items [aria-current="page"]', [...BOX, ...TYPE]],
			['sidebar.group-label', '.linker-account-nav-label', TYPE],
			['tile', '.linker-account-tile', BOX],
			['tile.number', '.linker-account-tile-count', TYPE],
			['tile.label', '.linker-account-tile-label', TYPE],
			['tiles.gap', '.linker-account-tiles', ['gap', 'rect']],
			['card', '.linker-account-panel', BOX],
			['card.heading', '.linker-account-panel-heading h2', TYPE],
			['card.head-row', '.linker-account-panel-heading', BOX],
			['row', '.linker-account-row', BOX],
			['badge', '.linker-account-row-status', [...BOX, ...TYPE]],
			['table.th', '.linker-account-table thead th', [...BOX, ...TYPE]],
			['table.td', '.linker-account-table tbody td', [...BOX, ...TYPE]],
			['sections.gap', '.linker-account-dashboard', ['gap']],
			['layout', '.linker-account-layout', ['gap', 'gridTemplateColumns']],
		],
	],
	'ours-inquiries': [
		`${oursBase}/my-account/inquiries/`,
		[
			['tabs', '.linker-account-tabs', BOX],
			['tab', '.linker-account-tabs a', [...BOX, ...TYPE]],
			['tab.active', '.linker-account-tabs [aria-current="page"]', [...BOX, ...TYPE]],
			['card', '.linker-account-card', BOX],
			['meta.label', '.linker-account-card-meta dt', TYPE],
			['meta.value', '.linker-account-card-meta dd', TYPE],
			['button.primary', '.linker-account-actions .linker-account-action', [...BOX, ...TYPE]],
			['products', '.linker-account-products', TYPE],
			['empty', '.linker-account-empty', [...BOX, ...TYPE]],
		],
	],
	'ours-documents': [
		`${oursBase}/my-account/documents/`,
		[
			['table.th', '.linker-account-table thead th', [...BOX, ...TYPE]],
			['table.td', '.linker-account-table tbody td', [...BOX, ...TYPE]],
		],
	],
	'ours-company': [
		`${oursBase}/my-account/company/billing/`,
		[
			['form.card', '.woocommerce-address-fields', BOX],
			['form.h2', '.linker-account-main form h2', TYPE],
			['form.label', '.form-row label', TYPE],
			['form.input', '.form-row .input-text', BOX],
			['form.row', '.form-row', ['margin', 'padding', 'rect']],
			['button.save', 'button[name="save_address"]', [...BOX, ...TYPE]],
			['contact.card', '.linker-contact-card', BOX],
		],
	],
	'ours-account-details': [
		`${oursBase}/my-account/edit-account/`,
		[
			['form.card', '.woocommerce-EditAccountForm', BOX],
			['form.label', '.form-row label', TYPE],
			['form.input', '.form-row .input-text', BOX],
			['button.save', 'button[name="save_account_details"]', [...BOX, ...TYPE]],
			['fieldset', 'fieldset', BOX],
			['legend', 'legend', TYPE],
		],
	],
	'ours-inquiry-detail': [
		`${oursBase}/my-account/inquiries/`,
		[
			['stagebar', '.linker-account-stagebar', BOX],
			['stage', '.linker-account-stagebar li', [...BOX, ...TYPE]],
			['stage.current', '.linker-account-stagebar [aria-current="step"]', [...BOX, ...TYPE]],
			['summary.card', '.linker-account-summary', BOX],
			['orderdetails.card', '.woocommerce-order-details', BOX],
			['shoptable.th', 'table.shop_table thead th', [...BOX, ...TYPE]],
			['shoptable.td', 'table.shop_table tbody td', [...BOX, ...TYPE]],
		],
		// measured after clicking into the first inquiry
		'click',
	],
};

// Additional pages and explicit workspace dimensions: every capture is a viewport,
// not a stretched full-page image. No fixture or page content is written.
REF['ref-account-notifications'] = [ `${refRoot}admin-dashboard/account-notifications.html`, [
	['h1', 'h1', TYPE], ['control', 'button', BOX],
] ];
OURS['ours-saved-solutions'] = [ `${oursBase}/my-account/saved-solutions/`, [
	['card', '.linker-account-solution, .linker-account-empty', BOX],
	['button.primary', '.linker-account-action', [...BOX, ...TYPE]],
] ];
for (const [name, spec] of Object.entries(REF)) {
	spec[1].push(['workspace', '#content', BOX], ['content', '#content > div', BOX],
		['sidebar', '#hs-pro-sidebar', BOX],
		['navigation.toggle', '[data-hs-overlay="#hs-pro-sidebar"]', BOX]);
}
for (const spec of Object.values(OURS)) {
	spec[1].push(['workspace', '#container-content-account', BOX], ['content', '.linker-account-main', BOX],
		['h1', '.linker-account-heading h1', [...TYPE, 'rect']],
		['sidebar', '.linker-account-sidebar', BOX],
		['navigation.toggle', '.linker-account-menu-toggle', BOX],
		['tiles.grid', '.linker-account-tiles', ['gridTemplateColumns', 'gap', 'rect']],
		['table.card', '.linker-account-table-card', BOX],
		['table.row', '.linker-account-table tbody tr', BOX],
		['table.th', '.linker-account-table thead th', [...BOX, ...TYPE]],
		['table.td', '.linker-account-table tbody td', [...BOX, ...TYPE]],
		['badge', '.linker-account-row-status', [...BOX, ...TYPE]],
		['bottom.nav', '.linker-account-bottom-nav', BOX],
		['bottom.target', '.linker-account-bottom-nav a', BOX],
		['shortcuts.grid', '.linker-account-shortcuts ul', ['gridTemplateColumns', 'gap', 'rect']],
		['shortcuts.target', '.linker-account-shortcuts a', BOX],
		['form.input', '.form-row .input-text', BOX],
		['action.target', '.linker-account-action, button[name="save_address"], button[name="save_account_details"]', BOX]);
}
REF['ref-crm-index'][1].push(['page.title', 'h2', TYPE]);
REF['ref-overview'][1].push(['sidebar.item', 'nav a', BOX]);
if (locale === 'de') {
	for (const spec of Object.values(OURS)) spec[0] = spec[0].replace('/my-account/', '/de/mein-konto/');
}
const specs = mode === 'ref' ? REF : OURS;
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

if (mode !== 'ref') {
	const user = process.argv[3] ?? 'e2e-en-1791887434348';
	const login = execFileSync('just', ['login', 't110', `--user=${user}`], {
		cwd: worktree,
		encoding: 'utf8',
	}).trim().split('\n').pop();
	await page.goto(login, { waitUntil: 'domcontentloaded' });
	await page.waitForURL(/my-account|\/$/);
}

const out = {};
for (const [width, height] of [[1440, 900], [390, 844], [430, 932]]) {
await page.setViewportSize({ width, height });
for (const [name, [url, probes, action]] of Object.entries(specs)) {
	const pageName = `${name}-${width}`;
	await page.goto(url, { waitUntil: mode === 'ref' ? 'networkidle' : 'load' });
	await page.evaluate(async () => { await document.fonts.ready; });
	if (action === 'click') {
		const detail = page.locator('a[href*="/inquiry/"], a[href*="/anfrage/"]').first();
		if ((await detail.count()) > 0) {
			await detail.click();
			await page.waitForLoadState('domcontentloaded');
		}
	}
	out[pageName] = { url: page.url(), probes: {} };
	for (const [name, selector, props] of probes) {
		out[pageName].probes[name] = await page.evaluate(
			({ selector, props }) => {
				const el = selector.startsWith('xpath=')
					? document.evaluate(selector.slice(6), document, null, XPathResult.FIRST_ORDERED_NODE_TYPE).singleNodeValue
					: document.querySelector(selector);
				if (!el) return null;
				const cs = getComputedStyle(el);
				const rec = {};
				for (const p of props) {
					rec[p] = p === 'rect'
						? (({ x, y, width, height }) => ({ x, y, width, height }))(el.getBoundingClientRect())
						: cs.getPropertyValue(p.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase()));
				}
				return rec;
			},
			{ selector, props }
		);
	}
	out[pageName].viewport = { width, height };
	out[pageName].overflow = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
	const prefix = process.env.CAPTURE_PREFIX ?? (mode === 'ref' ? 'ref' : 'ours');
	await page.screenshot({ path: path.join(here, `${name.replace(/^(ref|ours)/, prefix)}-${width}.png`) });
	console.log(pageName, 'done', JSON.stringify(out[pageName].overflow));
}
}

const file = path.join(here, `measurements-${process.env.CAPTURE_PREFIX ?? (mode === 'ref' ? 'ref' : 'ours')}.json`);
fs.writeFileSync(file, JSON.stringify(out, null, '\t'));
console.log('wrote', file);
await browser.close();
