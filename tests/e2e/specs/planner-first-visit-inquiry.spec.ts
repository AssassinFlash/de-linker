import { expect, test, type Page } from '@playwright/test';
import {
	applyTurnstileProfile,
	instance,
	instanceName,
	wp,
} from '../lib/instance';

let restoreProtection: (() => void) | undefined;
test.beforeAll(() => {
	expect(instance().url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
	restoreProtection = applyTurnstileProfile(instanceName(), 'optional');
});
test.afterAll(() => {
	restoreProtection?.();
});
test.beforeEach(({ page }) => {
	page.setDefaultTimeout(15_000);
});

async function screenshot(page: Page, name: string) {
	await page.evaluate(() => document.fonts.ready.then(() => undefined));
	const path = test.info().outputPath(name + '.png');
	await page.screenshot({ path, animations: 'disabled' });
	await test.info().attach(name, { path, contentType: 'image/png' });
}

const labels = {
	en: {
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
			await page.goto(url + (lang === 'de' ? '/de/' : '/'));
			await page
				.locator('[data-linker-planner-entry="home-hero"] a')
				.click();
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
			await screenshot(page, `preliminary-solutions-${lang}-${width}`);
			await card
				.getByRole('button', { name: words.choose, exact: true })
				.click();
			const form = page.locator('form.linker-inquiry-form');
			await expect(form).toBeVisible({ timeout: 90_000 });
			const binding = await form
				.locator('[name="linker_preliminary_project"]')
				.inputValue();
			const direction = await page
				.locator('.sc-draft-transfer p')
				.filter({ hasText: chosen })
				.innerText();
			expect(direction).toContain(chosen);
			await screenshot(page, `review-and-inquire-${lang}-${width}`);
			const email = `e2e-preliminary-${Date.now()}@example.test`;
			await form.locator('[name="name"]').fill('E2E First Guest');
			await form.locator('[name="email"]').fill(email);
			await form.locator('textarea:visible').fill(words.message);
			await form.locator('[name="consent"]').check();
			await form
				.getByRole('button', { name: words.send, exact: true })
				.click();
			await expect(
				page.getByRole('status').getByRole('heading', {
					name:
						lang === 'en'
							? 'Inquiry received'
							: 'Anfrage eingegangen',
					exact: true,
				})
			).toBeVisible({ timeout: 60_000 });
			await screenshot(page, `inquiry-received-${lang}-${width}`);
			const result = JSON.parse(
				wp([
					'eval',
					`
    $orders = wc_get_orders(array('billing_email' => '${email}', 'limit' => 2));
    if (count($orders) !== 1) {throw new RuntimeException('Expected one inquiry');}
    $order = $orders[0];
    echo wp_json_encode(array('number'=>$order->get_order_number(),'locale'=>Linker\\Commerce\\Inquiry\\OrderLocale::of($order),'customer'=>$order->get_customer_id(),'status'=>$order->get_status(),'items'=>count($order->get_items()),'note'=>$order->get_customer_note(),'project'=>$order->get_meta('_linker_preliminary_project')));
   `,
				])
			);
			expect(result).toEqual({
				number: expect.any(String),
				locale: lang === 'de' ? 'de_DE_formal' : 'en_US',
				customer: 0,
				status: 'inquiry-received',
				items: 0,
				project: binding,
				note: expect.stringContaining(direction),
			});
			expect(result.note).toContain(words.message);
			const overviewNumber = page
				.locator('.woocommerce-order-overview__order strong')
				.getByText(result.number, { exact: true });
			const heldNumber = page
				.getByRole('status')
				.getByText(new RegExp(`#${result.number}\\b`));
			await expect(
				overviewNumber.or(heldNumber).filter({ visible: true }).first()
			).toBeVisible();
		});
	}
}

test('keeps the selection and inquiry edits while changing language and returning to the comparison', async ({
	page,
}) => {
	const { url } = instance();
	const direction = 1;
	const changedDirection = 3;
	const note = 'I would like to discuss storage.';
	const form = page.locator('form.linker-inquiry-form');
	const compare = (name: string, action: string) =>
		page
			.getByRole('article')
			.filter({
				has: page.getByRole('heading', { name, exact: true }),
			})
			.getByRole('button', { name: action, exact: true });

	await page.goto(url + '/');
	await page
		.getByRole('link', {
			name: 'Open the Solution Configurator',
			exact: true,
		})
		.click();
	await compare(labels.en.directions[direction], labels.en.choose).click();
	await expect(form).toBeVisible();
	await form.locator('textarea:visible').fill(note);
	const projectReference = form.locator(
		'[name="linker_preliminary_project"]'
	);
	const selected = await projectReference.inputValue();
	await page
		.locator('header')
		.getByRole('link', { name: 'DE', exact: true })
		.click();
	await expect(page).toHaveURL(
		/\/de\/loesungskonfigurator\/.*#sc-preliminary-review$/
	);
	await expect(
		form.getByRole('button', { name: labels.de.send, exact: true })
	).toBeVisible();
	await expect(form.locator('textarea:visible')).toHaveValue(note);
	await expect(projectReference).toHaveValue(selected);

	await page
		.getByRole('button', { name: 'Variante ändern', exact: true })
		.click();
	await compare(
		labels.de.directions[changedDirection],
		labels.de.choose
	).click();
	await expect(form.locator('textarea:visible')).toHaveValue(note);
	const [id, revision] = selected.split(':');
	await expect(projectReference).toHaveValue(`${id}:${Number(revision) + 1}`);
});
