import { expect, test } from '@playwright/test';
import { instance, wp } from '../lib/instance';

const pages = {
	en: { path: '/solution-configurator/' },
	de: { path: '/de/loesungskonfigurator/' },
} as const;

let inquiryPages: Record<string, string>;
test.beforeAll(() => {
	inquiryPages = JSON.parse(
		wp([
			'eval',
			String.raw`echo wp_json_encode(\Linker\Commerce\Planning\DraftTransfer::urls(true));`,
		])
	);
});

for (const [lang, routes] of Object.entries(pages)) {
	for (const width of [1440, 390]) {
		test(`${lang} ${width}: public configurator links open their promised task`, async ({
			page,
		}) => {
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			const entry = instance().url + routes.path;
			await page.goto(entry + '?view=equipment');
			const equipment = page.locator('details.sc-project-equipment');
			await expect(equipment).toHaveJSProperty('open', true);
			await expect(equipment.locator('select').first()).toBeVisible();
			await expect(
				equipment
					.locator('.sc-product-picker')
					.first()
					.locator('summary')
			).toBeVisible();
			await equipment
				.locator('.sc-product-picker')
				.first()
				.locator('summary')
				.click();
			const model = equipment.locator('.linker-product-card a').first();
			await expect(model).toBeVisible({ timeout: 45_000 });
			await expect(model).toHaveAttribute(
				'href',
				new RegExp(lang === 'de' ? '/de/produkt/' : '/product/')
			);
			expect(
				await model
					.locator('img')
					.evaluate((image: HTMLImageElement) =>
						image.decode().then(() => image.naturalWidth)
					)
			).toBeGreaterThan(0);
			expect(
				await page.evaluate(() => document.documentElement.scrollWidth)
			).toBeLessThanOrEqual(width);
			await page.goto(entry + '?view=project');
			await expect(
				page.locator('form [name=project_title]')
			).toBeVisible();
			await expect(
				page.locator('details.sc-project-equipment')
			).toHaveJSProperty('open', false);
			await page.goto(entry + '?compare=preliminary');
			await expect(
				page.locator('.sc-direction-comparison tbody tr')
			).toHaveCount(4);
			await page.goto(entry + '?scope=storage_addition');
			await expect(
				page.locator('.sc-direction-comparison tbody tr')
			).toHaveCount(2);
			await page.goto(entry + '?projects=1');
			await expect(page.locator('.sc-saved-projects')).toBeVisible();
			await expect(page.locator('[name=project_title]')).toHaveCount(0);
			const tiles: string[] = [];
			page.on('request', (request) => {
				if (
					/\/tiles\/|\/tile\/|\/MapServer\/tile\//i.test(
						request.url()
					)
				)
					tiles.push(request.url());
			});
			await page.goto(entry + '?step=roof');
			await expect(page.locator('form [name=country]')).toBeVisible();
			await expect(page.locator('[name=system_scope]')).toHaveCount(0);
			expect(tiles).toEqual([]);
			await page.goto(entry + '?view=inquiry');
			await expect(page).toHaveURL(inquiryPages[lang]!);
			await expect(
				page.locator('form.linker-inquiry-form')
			).toBeVisible();
			await expect(page.locator('html')).toHaveAttribute(
				'lang',
				new RegExp('^' + lang)
			);
		});
	}
}
