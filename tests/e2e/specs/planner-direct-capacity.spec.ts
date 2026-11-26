import { expect, test } from '@playwright/test';
import { removeSiteProject } from '../lib/configurator-site';
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`direct PV entry updates the equipment preview in ${lang} at ${width}px`, async ({
			page,
			context,
			baseURL,
		}, info) => {
			const origin = baseURL ?? instance().url;
			const de = lang === 'de';
			const path = de
				? '/de/loesungskonfigurator/'
				: '/solution-configurator/';
			const label = (en: string, german: string) => (de ? german : en);
			const button = (en: string, german: string) =>
				page.getByRole('button', {
					name: label(en, german),
					exact: true,
				});
			const shot = async (name: string) => {
				await page.evaluate(() =>
					document.fonts.ready.then(() => undefined)
				);
				await page.screenshot({
					path: info.outputPath(name + '.png'),
					animations: 'disabled',
				});
			};
			const title = `Capacity ${lang} ${width} ${Date.now()}`;
			let created = false;
			page.on('response', (response) => {
				if (response.url().includes('projects/create') && response.ok())
					created = true;
			});
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await seedConsentCookies(context, origin);
			try {
				await page.goto(origin + path, {
					waitUntil: 'domcontentloaded',
				});
				await page.locator('[name="project_name"]').fill(title);
				await page
					.locator('[name="project_country"]')
					.selectOption('IT');
				await page.locator('[name="annual_load_kwh"]').fill('7200');
				await page
					.locator('[name="annual_load_basis"]')
					.selectOption('user_estimate');
				await page
					.locator('[name="site_pv_kw"]')
					.fill(label('11.09', '11,09'));
				await expect(
					page.locator('[name="project_start"]')
				).toHaveValue('known');
				await page.locator('[name="grid_phase"]').selectOption('3');
				await page
					.locator('[name="project_purpose"]')
					.selectOption('self');
				await button(
					'Enter project details',
					'Projektdaten eingeben'
				).click();
				await page.locator('[name="location_label"]').fill('Torino');
				await button('Compare systems', 'Systeme vergleichen').click();
				const cards = page.locator('.sc-comparison > .sc-package');
				await expect(cards.first()).toBeVisible({ timeout: 90_000 });
				const widths = await cards.evaluateAll((items) =>
					items.map((card) => ({
						width: card.clientWidth,
						content: card.scrollWidth,
						label: card.querySelector('.sc-package-capacity strong')
							?.textContent,
					}))
				);
				expect(widths.every((card) => card.content <= card.width)).toBe(
					true
				);
				await cards.first().scrollIntoViewIfNeeded();
				await shot('01-options');
				const roof = button('Roof & PV', 'Dach & PV');
				if (!(await roof.isVisible()))
					await button(
						'Fine-tune (optional)',
						'Verfeinern (optional)'
					).click();
				await roof.click();
				await expect(page).toHaveURL(/#sc-solar$/);
				const capacity = page.locator('.sc-solar-inputs input').first();
				await expect(capacity).toHaveValue(/^11[.,]09$/);
				const sidebar = page
					.locator('aside dt')
					.filter({ hasText: label('Solar capacity', 'PV-Leistung') })
					.locator('+ dd');
				await expect(sidebar).toHaveText(/11[.,]09\s*kWp/);
				await capacity.scrollIntoViewIfNeeded();
				await shot('02-solar');
				await capacity.fill('13.7');
				await expect(sidebar).toHaveText(/13[.,]7\s*kWp/);
				await button(
					'Continue with energy use',
					'Weiter zum Energiebedarf'
				).click();
				await button('Compare systems', 'Systeme vergleichen').click();
				const preview = page.locator('.sc-system-overview');
				await expect(
					preview.getByRole('heading', {
						name: label('Equipment preview', 'Geräteübersicht'),
					})
				).toBeVisible({ timeout: 90_000 });
				await expect(
					preview.locator('.sc-system-diagram')
				).toContainText(/13[.,]7\s*kWp/);
				await preview
					.locator('.sc-system-diagram')
					.scrollIntoViewIfNeeded();
				await shot('03-preview');
				await preview
					.locator('.sc-selection-evidence > summary')
					.click();
				const check = preview
					.locator('.sc-check-list li')
					.filter({
						has: page.getByText(
							label('PV input power', 'PV-Eingangsleistung'),
							{ exact: true }
						),
					})
					.first();
				await expect(check).toContainText(/13[.,]7\s*kWp/);
				await expect(preview).not.toContainText(/11[.,]09\s*kWp/);
				await check.scrollIntoViewIfNeeded();
				await shot('04-pv-input');
				await info.attach('capacity', {
					body: JSON.stringify({
						project: new URL(page.url()).searchParams.get(
							'project'
						),
						widths,
						preview: await preview
							.locator('.sc-system-diagram')
							.innerText(),
						check: await check.innerText(),
					}),
					contentType: 'application/json',
				});
			} finally {
				if (created) await removeSiteProject(page, lang, title, origin);
			}
		});
	}
}
