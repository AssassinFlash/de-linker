import { expect, test } from '@playwright/test';
import { instance, wp } from '../lib/instance';
import {
	deleteOpenProject,
	plannerScreenshot,
	plannerWords,
	reopenProject,
} from '../lib/planner-entry';

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
		test(`${lang} ${width}: a partial project can choose a direction before and after reopening`, async ({
			page,
		}) => {
			const words = labels[lang];
			const fields = plannerWords[lang];
			const site = `Oslo ${Date.now()}`;
			const searches: string[] = [];
			page.on('request', (request) => {
				if (request.url().endsWith('/runs/find-equipment'))
					searches.push(request.url());
			});
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await page.goto(instance().url + words.path);
			const locationField = page.locator('input[name="location_label"]');
			await locationField.fill(site);
			await page
				.locator('[name="system_scope"]')
				.selectOption('storage_addition');
			await page
				.getByRole('combobox', { name: fields.purpose, exact: true })
				.selectOption('self');
			const energy = page.getByRole('region', {
				name: fields.energy,
				exact: true,
			});
			const grid = energy.getByRole('combobox', {
				name: fields.grid,
				exact: true,
			});
			const consumption = energy.getByRole('textbox', {
				name:
					lang === 'en'
						? 'Annual electricity use kWh'
						: 'Jährlicher Stromverbrauch kWh',
				exact: true,
			});
			await grid.selectOption('3');
			await consumption.fill('1.234,5');
			await expect(
				energy.getByRole('button', {
					name: fields.compare,
					exact: true,
				})
			).toBeDisabled();
			await locationField.press('Enter');
			await expect(consumption).toHaveValue('1.234,5');
			await consumption.fill('6400');
			await expect(
				energy.getByRole('button', {
					name: fields.compare,
					exact: true,
				})
			).toBeEnabled();
			await grid.selectOption('');
			for (const [index, scope] of [
				'storage_addition',
				'storage_only',
			].entries()) {
				await expect(
					energy.getByRole('button', {
						name: words.compare,
						exact: true,
					})
				).toBeEnabled();
				if (index === 0) await locationField.press('Enter');
				else
					await energy
						.getByRole('button', {
							name: words.compare,
							exact: true,
						})
						.click();
				const direction = words.directions[index === 0 ? 1 : 3];
				const card = page.getByRole('article').filter({
					has: page.getByRole('heading', {
						name: direction,
						exact: true,
					}),
				});
				await card
					.getByRole('button', { name: words.choose, exact: true })
					.click();
				await expect(
					page.locator('form.linker-inquiry-form')
				).toBeVisible();
				await expect(page.locator('.sc-draft-transfer')).toContainText(
					direction
				);
				await plannerScreenshot(
					page,
					`partial-${index === 0 ? 'new' : 'saved'}-${lang}-${width}`
				);
				const project = await reopenProject(page, lang, site);
				expect(project.inputs.brief).toMatchObject({
					system_scope: scope,
					site: { location_label: site },
					annual_load: { kwh: 6400 },
				});
				expect(project.inputs.equipment_setup.grid_phase).toBeNull();
			}
			expect(searches).toHaveLength(0);
			await deleteOpenProject(page, lang, site);
		});
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
			await expect(
				page.getByRole('status').getByRole('heading', {
					name:
						lang === 'en'
							? 'Inquiry received'
							: 'Anfrage eingegangen',
					exact: true,
				})
			).toBeVisible({ timeout: 60_000 });
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
				note: `${direction}\r\n\r\n${words.message}`,
			});
		});
	}
}
