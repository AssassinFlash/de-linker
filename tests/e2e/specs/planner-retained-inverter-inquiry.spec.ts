import { expect, test } from '@playwright/test';
import { instance, wp } from '../lib/instance';

const local = /^http:\/\/127\.0\.0\.1:\d+$/;

test('a first guest sends a retained-inverter inquiry directly from review', async ({
	page,
	context,
}) => {
	test.setTimeout(240_000);
	const { url } = instance();
	expect(url).toMatch(local);
	const tag = Date.now();
	const email = `e2e-retained-${tag}@example.test`;
	const title = `E2E retained inverter ${tag}`;
	const workspace = page.locator('[data-linker-planner]');
	expect(await context.cookies()).toEqual([]);
	await page.goto(`${url}/solution-configurator/`);
	const reject = page.getByRole('button', {
		name: 'Reject all',
		exact: true,
	});
	if (await reject.isVisible()) await reject.click();
	page.setDefaultTimeout(15_000);
	const project = page.getByRole('form', { name: 'New project' });
	await project.getByText('Site details', { exact: true }).click();
	await project.getByLabel('Project name (optional)').fill(title);
	await project.locator('select[name=country]').selectOption('DE');
	await project.getByLabel('Town or site').fill('Berlin');
	await project
		.locator('select[name=system_scope]')
		.selectOption('storage_addition');
	await project.getByLabel('Site use').selectOption('residential');
	await project
		.locator('select[name=project_purpose]')
		.selectOption('backup');
	await project.getByLabel('There is an existing system').check();
	await project.getByLabel('Existing system name').fill('Workshop inverter');
	await project.getByLabel('Existing inverter power (kW)').fill('7.5');
	await project.getByLabel('Keep the existing inverter').check();
	await workspace.getByLabel('Grid connection').selectOption('3');
	await workspace.getByLabel('Backup load').fill('3');
	await workspace.getByLabel('Required duration').fill('2');
	await workspace.getByRole('button', { name: 'Compare systems' }).click();
	await expect(
		workspace.getByRole('heading', { name: 'Keep the existing inverter' })
	).toBeVisible({ timeout: 90_000 });
	await workspace
		.getByRole('button', { name: 'Review the proposal' })
		.click();
	const form = workspace.locator('form.linker-inquiry-form');
	await expect(form).toBeVisible({ timeout: 120_000 });
	await expect(
		workspace.getByRole('table', {
			name: 'Products included in your inquiry',
		})
	).toHaveCount(0);
	await expect(
		workspace.getByRole('heading', { name: title, exact: true })
	).toBeVisible();
	const cart = await context.request.get(`${url}/wp-json/wc/store/v1/cart`);
	expect(cart.ok()).toBe(true);
	expect((await cart.json()).items).toEqual([]);
	await form.locator('[name="name"]').fill('E2E Report Guest');
	await form.locator('[name="email"]').fill(email);
	await form
		.locator('[name="message"]')
		.fill(
			'Please quote backup storage for our existing workshop inverter.'
		);
	await form.locator('[name="consent"]').check();
	// PublicGuard requires three seconds on a rendered form.
	await page.waitForTimeout(3100);
	await form.getByRole('button', { name: 'Send inquiry' }).click();
	await expect(page.locator('.linker-form-success')).toBeVisible({
		timeout: 60_000,
	});
	const order = JSON.parse(
		wp([
			'eval',
			`
		$orders = wc_get_orders(array('billing_email' => '${email}', 'limit' => 2));
		if (count($orders) !== 1) { throw new RuntimeException('Expected one inquiry'); }
		$order = $orders[0];
		$stored = Linker\\Commerce\\Planning\\Context::stored($order);
		$reference = count($stored) === 1 ? reset($stored)['reference'] : null;
		echo wp_json_encode(array('id' => $order->get_id(), 'customer' => $order->get_customer_id(), 'status' => $order->get_status(), 'items' => count($order->get_items()), 'reference' => $reference));
	`,
		])
	);
	expect(order).toMatchObject({
		customer: 0,
		status: 'inquiry-received',
		items: 0,
		reference: {
			title,
			report_only: true,
			items: [],
		},
	});
	const download = page.getByRole('link', {
		name: 'Download PDF',
		exact: true,
	});
	await expect(download).toBeVisible();
	const href = await download.getAttribute('href');
	expect(href).toContain(
		`/inquiries/${order.id}/planning-report/${order.reference.handoff_id}`
	);
	const pdf = await context.request.get(new URL(href!, url).href);
	expect(pdf.ok()).toBe(true);
	expect(pdf.headers()['content-type']).toContain('application/pdf');
	expect((await pdf.body()).subarray(0, 5).toString()).toBe('%PDF-');
});
