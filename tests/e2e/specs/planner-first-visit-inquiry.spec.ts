import { expect, test } from '@playwright/test';
import { instance, wp } from '../lib/instance';
import { plannerScreenshot } from '../lib/planner-entry';

const labels = {
	en: {
		path: '/solution-configurator/',
		compare: 'Compare preliminary options',
		directions: [
			'Solar and storage',
			'Storage for existing PV',
			'Solar',
			'Storage',
		],
		choose: 'Choose this option',
		send: 'Send inquiry',
		message: 'Please discuss this preliminary solution with me.',
	},
	de: {
		path: '/de/loesungskonfigurator/',
		compare: 'Erste Anlagenvarianten vergleichen',
		directions: [
			'Photovoltaik und Speicher',
			'Speicher für eine bestehende PV-Anlage',
			'Photovoltaik',
			'Speicher',
		],
		choose: 'Diese Variante wählen',
		send: 'Anfrage senden',
		message: 'Bitte besprechen Sie diesen ersten Lösungsvorschlag mit mir.',
	},
} as const;

for (const lang of ['en', 'de'] as const) {
	for (const width of [390, 1440]) {
		test(`${lang} ${width}: a first guest requests a preliminary solution with no project data`, async ({
			page,
			context,
		}) => {
			test.setTimeout(240_000);
			const { url } = instance();
			expect(url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
			const words = labels[lang];
			expect(await context.cookies()).toEqual([]);
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await page.goto(url + words.path);
			await page
				.getByRole('button', { name: words.compare, exact: true })
				.click({ timeout: 15_000 });
			for (const name of words.directions)
				await expect(
					page
						.getByRole('article')
						.getByRole('heading', { name, exact: true })
				).toBeVisible();
			const chosen = words.directions[1];
			const card = page.getByRole('article').filter({
				has: page.getByRole('heading', {
					name: chosen,
					exact: true,
				}),
			});
			await plannerScreenshot(
				page,
				`preliminary-solutions-${lang}-${width}`
			);
			await card
				.getByRole('button', { name: words.choose, exact: true })
				.click();
			const form = page.locator('form.linker-inquiry-form');
			await expect(form).toBeVisible({ timeout: 90_000 });
			const direction = await page
				.locator('.sc-draft-transfer p')
				.filter({ hasText: chosen })
				.innerText();
			expect(direction).toContain(chosen);
			await plannerScreenshot(
				page,
				`review-and-inquire-${lang}-${width}`
			);
			const email = `e2e-preliminary-${Date.now()}@example.test`;
			await form.locator('[name="name"]').fill('E2E First Guest');
			await form.locator('[name="email"]').fill(email);
			await form.locator('textarea:visible').fill(words.message);
			await form.locator('[name="consent"]').check();
			await page.waitForTimeout(3100);
			await form
				.getByRole('button', { name: words.send, exact: true })
				.click();
			await expect(page.locator('.linker-form-success')).toBeVisible({
				timeout: 60_000,
			});
			await plannerScreenshot(page, `inquiry-received-${lang}-${width}`);
			const result = JSON.parse(
				wp([
					'eval',
					`
    $orders = wc_get_orders(array('billing_email' => '${email}', 'limit' => 2));
    if (count($orders) !== 1) {throw new RuntimeException('Expected one inquiry');}
    $order = $orders[0];
    echo wp_json_encode(array('customer'=>$order->get_customer_id(),'status'=>$order->get_status(),'items'=>count($order->get_items()),'note'=>$order->get_customer_note()));
   `,
				])
			);
			expect(result).toEqual({
				customer: 0,
				status: 'inquiry-received',
				items: 0,
				note: `${direction}\n\n${words.message}`,
			});
		});
	}
}
