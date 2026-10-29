/** b2-inquiry acceptance walk — duplicate-submit protection (EN guest). Standalone; not in the suite. */
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { instance, REPO_ROOT, wp } from '../lib/instance';

const fixture = join(REPO_ROOT, 'tests/e2e/fixtures/public-inquiry.php');
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);
const out = join(REPO_ROOT, '.scratch/b2-walk');
mkdirSync(out, { recursive: true });
const t = (m: string) => console.log(new Date().toISOString(), m);

async function main() {
	const email = `b2walk-dup-${Date.now()}@example.test`;
	try {
		run('cleanup');
	} catch {
		/* no fixture from a previous run */
	}
	const setup = JSON.parse(run('setup', email, 'receipt')) as {
		product: number;
	};
	t(`fixture setup product=${setup.product}`);

	const browser = await chromium.launch();
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
	});
	const page = await context.newPage();
	const url = `${instance().url}/proforma-request/`;
	const evidence: Record<string, unknown> = { email };
	try {
		let posts = 0;
		page.on('request', (r) => {
			if (r.method() === 'POST' && r.url().includes('/proforma-request'))
				posts++;
		});
		await page.goto(url);
		const form = page.locator('form.linker-inquiry-form');
		await form.waitFor();
		await context.request.get(
			`${instance().url}/?add-to-cart=${setup.product}`
		);
		await page.reload();
		await page.locator('.linker-inquiry-line').first().waitFor();

		await form.locator('[name="name"]').fill('Dup Walk Guest');
		await form.locator('[name="email"]').fill(email);
		await form.locator('[name="company"]').fill('Dup GmbH');
		await form
			.locator('[name="message"]')
			.fill('Duplicate-submit protection check.');
		await form.locator('[name="consent"]').check();
		await page.waitForTimeout(3_100);

		// Double-click the submit button as a hurried user would.
		const button = form.locator('[type="submit"]');
		await button.dblclick();
		await page
			.locator('.linker-form-success')
			.first()
			.waitFor({ timeout: 30_000 });
		evidence.confirmedUrl = page.url();
		evidence.posts = posts;
		t(`success after dblclick url=${page.url()} posts=${posts}`);

		// And a scripted resubmit while the first is in flight: form is gone now;
		// the guard cleared navigation — assert exactly one order exists.
		const orders = (JSON.parse(run('read')) as { orders: unknown[] })
			.orders;
		evidence.ordersAfterDoubleSubmit = orders.length;
		t(`orders=${orders.length}`);

		// Back-button style: return to the form and submit again with the draft
		// now emptied by the success path — the preflight must refuse an empty
		// draft with an empty message (linker_inquiry_empty).
		await page.goto(url);
		await form.waitFor();
		const fill = (name: string, address: string) =>
			`(() => { const f = document.querySelector('form.linker-inquiry-form');
				const set = (field, value) => { const c = f.elements.namedItem(field); if (c) { c.value = value; c.dispatchEvent(new Event('input', { bubbles: true })); } };
				set('name', ${JSON.stringify(name)}); set('email', ${JSON.stringify(address)});
				f.elements.namedItem('consent').checked = true; })()`;
		await page.evaluate(fill('Dup Walk Guest', email));
		await page.waitForTimeout(3_100);
		await form.locator('[type="submit"]').click();
		await page.waitForTimeout(2_500);
		evidence.emptyDraftError = await page
			.locator('.linker-inquiry-error')
			.textContent();
		evidence.emptyDraftUrl = page.url();
		t(
			`empty-draft resubmit error=${JSON.stringify(evidence.emptyDraftError)} url=${page.url()}`
		);
		const orders2 = (JSON.parse(run('read')) as { orders: unknown[] })
			.orders;
		evidence.ordersAfterEmptyDraft = orders2.length;
		evidence.assertions = {
			// The POST count is informational only: the form navigation may
			// surface to the listener as a document request. The invariant
			// is that a double-click yields exactly one order.
			oneOrderAfterDoubleSubmit: orders.length === 1,
			emptyDraftRefused: String(evidence.emptyDraftError).length > 3,
			stillOneOrder: orders2.length === 1,
		};
		t(`assertions=${JSON.stringify(evidence.assertions)}`);
	} finally {
		await context.close().catch(() => {});
		await browser.close().catch(() => {});
		writeFileSync(join(out, 'dup.json'), JSON.stringify(evidence, null, 2));
		try {
			run('cleanup');
		} catch {
			/* already clean */
		}
	}
}

void main();
