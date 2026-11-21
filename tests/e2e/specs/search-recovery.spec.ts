/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from '../lib/instance';

for (const [locale, path, label, heading] of [
	['en', '/page/999/', 'Search the site', 'Search'],
	['de', '/de/seite/999/', 'Website durchsuchen', 'Suche'],
] as const) {
	test(`${locale}: retry an out-of-range search without retyping`, async ({
		page,
	}) => {
		const response = await page.goto(`${instance().url}${path}?s=SAJ`);
		expect(response?.status()).toBe(404);
		const downloads = page.locator('.lk-e4-card').filter({
			hasText:
				locale === 'en'
					? 'Open the document library'
					: 'Dokumentenbibliothek öffnen',
		});
		await downloads.click();
		await expect(
			page.getByRole('tab', { name: /Documents|Dokumente/i })
		).toHaveAttribute('aria-selected', 'true');
		await page.goBack();
		const search = page.getByRole('searchbox', { name: label });
		await expect(search).toHaveValue('SAJ');
		await search.press('Enter');
		await expect(page.locator('.journal-card').first()).toBeVisible();
		expect(new URL(page.url()).searchParams.get('s')).toBe('SAJ');

		const current = page.locator('#site-search');
		await current.fill('');
		await current.press('Enter');
		await expect(page.getByRole('heading', { level: 1 })).toHaveText(
			heading
		);
		await expect(page).toHaveTitle(new RegExp(heading));
	});
}
