/**
 * A commercial project reaches its report PDF and Woo draft.
 *
 * Production walk 2026-11-11 §B: a commercial customer filled the one-screen
 * quick start, got the sized 690-combination answer and the provisional bill of
 * materials, and then read HTTP 422 from the report step with no PDF. The screen
 * had adopted the chosen equipment combination as the project's candidate and
 * still named a separate equipment run in the report request; the report's own
 * contract reads an adopted candidate as the project's single equipment source,
 * so the extra run contradicted it.
 *
 * Exercise the same adopted-candidate contract through the configurator:
 * fresh project, commercial inputs, real comparison, PDF and product transfer.
 */
import { expect, test, type Page } from '@playwright/test';
import { seedConsentCookies } from '../lib/consent';
import { instance, wp } from '../lib/instance';

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

async function reviewCommercialProject(page: Page) {
	await page.setViewportSize({ width: 1440, height: 900 });

	// The public size-hint link carries a declared PV rating, not a calculation.
	await page.goto(instance().url + '/solution-configurator/?pv_kwp=100', {
		waitUntil: 'networkidle',
	});
	const form = page.getByRole('form', { name: 'New project' });
	const title = `E2E commercial ${Date.now()}`;
	await expect(page.getByText('100 kWp', { exact: true })).toBeVisible();
	await expect(
		page.getByLabel('Use these values for the new project')
	).toBeChecked();
	await form.getByText('Site details', { exact: true }).click();
	await form.getByLabel('Project name (optional)').fill(title);
	await form
		.getByRole('combobox', { name: 'Country', exact: true })
		.selectOption('DE');
	await form.getByLabel('Town or site').fill('80331 München');
	await form.getByLabel('Planned system').selectOption('new_pv_storage');
	await form.getByLabel('Main purpose').selectOption('peak');
	await form.getByLabel('Site use').selectOption('commercial');
	await expect(
		page.getByText('Solar installation and roof layout', { exact: true })
	).toBeVisible();
	await page.getByLabel('Annual electricity use').fill('250000');
	await page
		.getByRole('combobox', { name: 'Grid connection', exact: true })
		.selectOption('3');
	await page.getByLabel('Target grid import limit').fill('70');
	await page.getByRole('button', { name: 'Compare systems' }).click();
	const option = page
		.getByRole('button', { name: 'Use this configuration', exact: true })
		.first();
	await expect(option).toBeVisible({ timeout: 120_000 });
	await option.click();
	await expect(
		page
			.getByRole('navigation', { name: 'Project navigation' })
			.getByRole('button', { name: /Review & inquire/ })
	).toHaveAttribute('aria-current', 'step');
	return title;
}

test('a commercial customer sends the selected system and quantities directly from review', async ({
	page,
}) => {
	test.setTimeout(420_000);
	expect(instance().url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
	const title = await reviewCommercialProject(page);
	const products = page.getByRole('table', {
		name: 'Products included in your inquiry',
	});
	await expect(products).toBeVisible({ timeout: 180_000 });
	const expected = await products.locator('tbody tr').evaluateAll((rows) =>
		rows.map((row) => ({
			name: row.querySelectorAll('td')[0]!.textContent!.trim(),
			quantity: Number(row.querySelectorAll('td')[1]!.textContent),
		}))
	);
	expect(expected.length).toBeGreaterThan(0);
	const email = `e2e-commercial-${Date.now()}@example.test`;
	const form = page.locator('form.linker-inquiry-form');
	await form.locator('[name="name"]').fill('E2E Commercial Guest');
	await form.locator('[name="email"]').fill(email);
	await form
		.locator('[name="message"]')
		.fill('Please quote this system for our Munich site.');
	await form.locator('[name="consent"]').check();
	await page.waitForTimeout(3100);
	await form.getByRole('button', { name: 'Send inquiry' }).click();
	await expect(page.locator('.linker-form-success')).toBeVisible({
		timeout: 60_000,
	});
	const result = JSON.parse(
		wp([
			'eval',
			`
		$orders = wc_get_orders(array('billing_email' => '${email}', 'limit' => 2));
		if (count($orders) !== 1) { throw new RuntimeException('Expected one inquiry'); }
		$order = $orders[0];
		$stored = Linker\\Commerce\\Planning\\Context::stored($order);
		echo wp_json_encode(array('status' => $order->get_status(), 'customer' => $order->get_customer_id(), 'title' => reset($stored)['reference']['title'], 'lines' => array_values(array_map(static fn($item) => array('name' => $item->get_name(), 'quantity' => $item->get_quantity()), $order->get_items()))));
	`,
		])
	);
	expect(result).toMatchObject({
		status: 'inquiry-received',
		customer: 0,
		title,
	});
	expect(result.lines).toHaveLength(expected.length);
	expect(result.lines).toEqual(expect.arrayContaining(expected));
});

test('a commercial customer downloads the project PDF and transfers the selected system to a solution draft', async ({
	page,
}) => {
	test.setTimeout(420_000);
	await reviewCommercialProject(page);
	await expect(
		page.getByRole('button', { name: 'Download PDF', exact: true })
	).toBeVisible({ timeout: 180_000 });

	// The PDF the customer downloads: bytes, page count, and a 200.
	const asset = page.waitForResponse('**/rpc/assets/content');
	const download = page.waitForEvent('download', { timeout: 120_000 });
	await page.getByRole('button', { name: 'Download PDF' }).click();
	expect((await asset).status()).toBe(200);
	const file = await download;
	const path = await file.path();
	expect(path, 'the browser saved the report').toBeTruthy();

	const { readFileSync } = await import('node:fs');
	const bytes = readFileSync(path!);
	expect(bytes.subarray(0, 5).toString('latin1'), 'a PDF header').toBe(
		'%PDF-'
	);
	expect(bytes.length).toBeGreaterThan(2000);
	// Pages are declared in the page tree; counting them proves the document is
	// a finished report rather than an empty container.
	const pages = (bytes.toString('latin1').match(/\/Type\s*\/Page[^s]/g) ?? [])
		.length;
	expect(pages, 'the report has pages').toBeGreaterThan(0);
	expect(file.suggestedFilename()).toMatch(
		/^linker-planning-[a-f0-9]{32}-r\d+-en\.pdf$/
	);

	await page
		.getByRole('button', {
			name: 'Add selected products to solution draft',
		})
		.click();
	const preview = page.getByRole('table').filter({
		has: page.getByRole('columnheader', { name: 'New quantity' }),
	});
	await expect(preview.getByRole('row').nth(1)).toBeVisible();
	const rows = await preview.locator('tbody tr').evaluateAll((lines) =>
		lines.map((line) => {
			const cells = line.querySelectorAll('td');
			return {
				name: cells[0]!.textContent!.trim(),
				quantity: Number(cells[2]!.textContent),
			};
		})
	);
	expect(rows.length).toBeGreaterThan(0);
	await page.getByRole('button', { name: 'Confirm changes' }).click();
	await page.getByRole('link', { name: 'View solution draft' }).click();
	for (const item of rows) {
		const row = page
			.locator('.cart_item:visible')
			.filter({ hasText: item.name });
		await expect(row).toBeVisible();
		await expect(row.locator('input.qty')).toHaveValue(
			String(item.quantity)
		);
	}
});
