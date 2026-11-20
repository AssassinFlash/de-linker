import { expect, test } from '@playwright/test';
import { instance } from '../lib/instance';

test('the same guest comparison keeps entered details across reload and language change', async ({
	page,
}) => {
	page.setDefaultTimeout(15_000);
	const { url } = instance();
	await page.goto(url + '/');
	const entry = page.locator('[data-linker-planner-entry="home-hero"] a');
	await entry.click();
	await page
		.getByRole('button', { name: 'Enter project details', exact: true })
		.click();
	await page.locator('input[name="location_label"]').fill('Utrecht');
	await page.locator('input[name="annual_load_kwh"]').fill('6412');
	await page
		.getByRole('button', { name: 'Compare options', exact: true })
		.click();
	const facts = page.locator('.sc-preliminary-layout .sc-project-facts');
	await expect(facts).toContainText('Utrecht');
	await expect(facts).toContainText('6412 kWh');
	await page.reload();
	await expect(facts).toContainText('Utrecht');
	await expect(facts).toContainText('6412 kWh');
	await page
		.locator('header')
		.getByRole('link', { name: 'DE', exact: true })
		.click();
	await expect(page).toHaveURL(/\/de\/.+#sc-preliminary-options$/);
	await expect(
		page.getByRole('heading', { name: 'Projektbeschreibung', exact: true })
	).toBeVisible();
	await expect(facts).toContainText('Utrecht');
	await expect(facts).toContainText('6412 kWh');
	expect(page.url()).not.toMatch(/Utrecht|6412/);
	await page.goto(url + '/');
	await entry.click();
	await expect(
		page.getByRole('table', { name: 'Compare system options' })
	).toBeVisible();
	await expect(facts).toHaveCount(0);
	const linked = new URL(page.url());
	linked.searchParams.set('annual_kwh', '8927');
	await page.goto(linked.href);
	await expect(facts).toContainText('8927 kWh');
	await expect(facts).not.toContainText('Utrecht');
});
