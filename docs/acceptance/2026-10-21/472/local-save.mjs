/**
 * Local guest save-URL check for #472. Session only. No login, no mail.
 * Compares the account URL a German configurator page gets from
 * POST linker/v1/solutions with the English page on the same instance.
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
const ORIGIN = process.env.LOCAL_ORIGIN || 'http://127.0.0.1:9153';
const pages = [
	{ lang: 'de', path: '/de/loesungskonfigurator/' },
	{ lang: 'en', path: '/solution-configurator/' },
];

const browser = await chromium.launch({ headless: true });
const rows = [];
try {
	for (const item of pages) {
		const context = await browser.newContext({
			viewport: { width: 1440, height: 900 },
			locale: item.lang === 'de' ? 'de-DE' : 'en-GB',
			userAgent: 'de-linker-walk-472-local/1.0',
		});
		const page = await context.newPage();
		const row = { origin: ORIGIN, lang: item.lang, at: new Date().toISOString() };
		try {
			await page.goto(ORIGIN + item.path, { waitUntil: 'domcontentloaded', timeout: 30000 });
			const accept = page.locator('[data-cky-tag="accept-button"]');
			await accept.waitFor({ state: 'visible', timeout: 3000 }).catch(() => {});
			if (await accept.count()) {
				await accept.evaluate((button) => button.click()).catch(() => {});
			}
			const mount = page.locator('[data-linker-app="configurator"]');
			await mount.waitFor({ state: 'attached', timeout: 15000 });
			const nonce = await mount.getAttribute('data-rest-nonce');
			const rest = await mount.getAttribute('data-rest-url');
			row.pageLang = await page.evaluate(() => document.documentElement.lang);
			row.bundle = await page.locator('script[src*="configurator.js"]').first().getAttribute('src');
			row.save = await page.evaluate(
				async ({ restUrl, token }) => {
					const products = await fetch(
						`${restUrl}wc/store/v1/products?per_page=1`,
						{ credentials: 'include' }
					);
					const list = await products.json();
					const id = list[0] && list[0].id;
					const response = await fetch(`${restUrl}linker/v1/solutions`, {
						method: 'POST',
						credentials: 'include',
						headers: {
							'Content-Type': 'application/json',
							'X-WP-Nonce': token,
						},
						body: JSON.stringify({
							kind: 'residential',
							title: '472 local language check',
							input: { plz: '80538' },
							lines: [{ product_id: id, quantity: 1 }],
						}),
					});
					return {
						productId: id,
						status: response.status,
						body: await response.json().catch(() => null),
					};
				},
				{ restUrl: rest, token: nonce }
			);
			if (row.save.body && row.save.body.url) {
				await page.goto(row.save.body.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
				row.opened = await page.evaluate(() => ({
					url: location.href,
					lang: document.documentElement.lang,
					title: document.title,
					hasPassword: !!document.querySelector('input[type="password"]'),
				}));
			}
		} catch (failure) {
			row.error = String(failure && failure.message ? failure.message : failure);
		} finally {
			await context.close();
		}
		rows.push(row);
		console.log(item.lang, row.save && row.save.status, row.save && row.save.body, row.opened || row.error);
	}
} finally {
	await browser.close();
}
writeFileSync(join(here, 'local-save.json'), JSON.stringify(rows, null, 2));
