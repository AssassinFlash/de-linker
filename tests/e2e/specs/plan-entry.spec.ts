/** Installer Plan carries the customer's own words to the native Woo inquiry. */
import { expect, test } from '@playwright/test';
import { seedConsentCookies } from '../lib/consent';
import { instance, wp } from '../lib/instance';

const PAGES = {
	en: {
		page: '/for-installer/',
		planner: '/solution-configurator/',
		note: '10 kWp roof with a battery for self-consumption',
		noteLabel: 'Your project note',
		direction: 'Solar and storage',
		choose: 'Choose this option',
		send: 'Send inquiry',
		received: 'Inquiry received',
	},
	de: {
		page: '/de/fuer-installateur/',
		planner: '/de/loesungskonfigurator/',
		note: '10 kWp Dachanlage mit Speicher für den Eigenverbrauch',
		noteLabel: 'Ihre Projektnotiz',
		direction: 'Photovoltaik und Speicher',
		choose: 'Diese Variante wählen',
		send: 'Anfrage senden',
		received: 'Anfrage eingegangen',
	},
} as const;

for (const [locale, spec] of Object.entries(PAGES)) {
	test(`${locale}: Installer Plan sends the reviewed project note with the current draft`, async ({
		page,
		context,
	}) => {
		const { url } = instance();
		await seedConsentCookies(context);
		await page.setViewportSize({
			width: 1440,
			height: 900,
		});
		const products: number[] = [];
		if (locale === 'en') {
			await page.goto(url + '/product/saj-bu2-5-0-hv1/');
			const add = page.locator('a[href*="add-to-cart="]:visible').first();
			const href = await add.getAttribute('href');
			products.push(
				Number(new URL(href!, url).searchParams.get('add-to-cart'))
			);
			await add.click();
			await page.goto(url + '/cart/');
			await expect(page.locator('.cart_item')).toHaveCount(1);
		}
		await page.goto(url + spec.page);
		const field = page.locator('#lki-hero-query');
		await field.fill(spec.note);
		await field.press('Enter');
		await expect(page).toHaveURL(
			new RegExp(`${spec.planner}\\?.*brief=[a-f0-9]{32}`)
		);
		const note = page.getByRole('textbox', { name: spec.noteLabel });
		await expect(note).toHaveValue(spec.note, { timeout: 60_000 });
		const card = page.getByRole('article').filter({
			has: page.getByRole('heading', {
				name: spec.direction,
				exact: true,
			}),
		});
		for (const width of [390, 1440]) {
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await expect(note).toBeVisible();
			await expect(
				card.getByRole('button', { name: spec.choose })
			).toBeVisible();
		}
		await card.getByRole('button', { name: spec.choose }).click();
		const form = page.locator('form.linker-inquiry-form');
		await expect(
			form.locator('.linker-inquiry-project-note')
		).toContainText(spec.note);
		await expect(
			form.locator('[name="linker_include_project_notes"]')
		).toBeChecked();
		const width = locale === 'en' ? 1440 : 390;
		await page.setViewportSize({
			width,
			height: width === 390 ? 844 : 900,
		});
		await expect(form.locator('textarea:visible')).toHaveValue('');
		const email = `e2e-installer-${Date.now()}@example.test`;
		await form.locator('[name="name"]').fill('E2E Installer');
		await form.locator('[name="email"]').fill(email);
		await form.locator('[name="consent"]').check();
		await page.waitForTimeout(3100);
		await form.getByRole('button', { name: spec.send }).click();
		await expect(
			page
				.getByRole('status')
				.getByRole('heading', { name: spec.received })
		).toBeVisible({ timeout: 60_000 });
		const order = JSON.parse(
			wp([
				'eval',
				`
				$orders = wc_get_orders(array('billing_email' => '${email}', 'limit' => 2));
				if (count($orders) !== 1) { throw new RuntimeException('Expected one inquiry'); }
				$order = $orders[0];
				$lines = array_values(array_map(static fn($item) => array($item->get_product_id(), $item->get_quantity()), $order->get_items()));
				echo wp_json_encode(array('notes' => array_column(\\Linker\\Commerce\\Planning\\Context::stored_notes($order), 'text'), 'message' => $order->get_customer_note(), 'lines' => $lines, 'status' => $order->get_status()));
			`,
			])
		);
		expect(order.notes).toEqual([spec.note]);
		expect(order.message).toContain(spec.direction);
		expect(order.message).not.toContain(spec.note);
		expect(order.lines).toEqual(products.map((id) => [id, 1]));
		expect(order.status).toBe('inquiry-received');
	});
}
