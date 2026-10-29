/** One-off probe: replicate the invalid-email submit and capture navigation. */
import { chromium } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { instance, wp } from '../lib/instance';

const fixture = join(process.cwd(), 'fixtures/public-inquiry.php');
const run = (...args: string[]) =>
	wp(['eval-file', fixture, ...args], 'b2inquiry').trim();

void (async () => {
	const email = `probe-${Date.now()}@example.test`;
	try {
		run('cleanup');
	} catch {
		/* no fixture yet */
	}
	const setup = JSON.parse(run('setup', email, 'receipt'));
	const browser = await chromium.launch();
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
	});
	const page = await context.newPage();
	page.on('request', (r) => {
		if (r.method() === 'POST') console.log('POST', r.url());
	});
	page.on('framenavigated', (f) => console.log('NAV', f.url()));
	await page.goto(`${instance().url}/proforma-request/`);
	await context.request.get(
		`${instance().url}/?add-to-cart=${setup.product}`
	);
	await page.reload();
	const form = page.locator('form.linker-inquiry-form');
	await form.locator('[name="name"]').fill('Probe Guest');
	await form.locator('[name="email"]').fill('not-an-email');
	await form.locator('[name="company"]').fill('Probe GmbH');
	await form.locator('[name="message"]').fill('probe message');
	await form.locator('[name="consent"]').check();
	await page.waitForTimeout(3_100);
	page.on('console', (m) => console.log('CONSOLE', m.text()));
	page.on('pageerror', (e) => console.log('PAGEERROR', String(e)));
	await page.evaluate(() => {
		const f = document.querySelector(
			'form.linker-inquiry-form'
		) as HTMLFormElement | null;
		console.log('FORM', !!f, f?.noValidate, f?.action);
		f?.addEventListener('submit', () => console.log('SUBMIT-EVENT'), {
			capture: true,
		});
		if (f) {
			f.noValidate = true;
			f.requestSubmit();
			console.log('REQUESTSUBMIT-CALLED');
		}
	});
	await page.waitForTimeout(4_000);
	const error = await page
		.locator('.linker-inquiry-error')
		.textContent()
		.catch(() => 'LOCATOR_ERROR');
	console.log('ERROR_PARAGRAPH:', JSON.stringify(error));
	console.log('URL:', page.url());
	await page.screenshot({
		path: join(process.cwd(), '../../artifacts/probe-invalid-email.png'),
		fullPage: true,
	});
	await browser.close();
	run('cleanup');
})();
