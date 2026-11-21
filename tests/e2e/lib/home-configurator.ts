import { expect, type Page } from '@playwright/test';

type Language = 'en' | 'de';

export async function launchHomepageConfigurator(
	page: Page,
	language: Language
) {
	await page
		.locator('#configurator-showcase')
		.getByRole('link', {
			name:
				language === 'en'
					? 'Launch Configurator'
					: 'Konfigurator starten',
			exact: true,
		})
		.click();
	return page.locator('[data-linker-planner]').getByRole('form', {
		name:
			language === 'en'
				? 'Compare project options'
				: 'Projektoptionen vergleichen',
		exact: true,
	});
}

export async function compareSavedFromHome(
	page: Page,
	language: Language,
	projectId: string
) {
	const shortcut = page.locator(
		'#configurator-showcase a[href$="?projects=1"]'
	);
	if (await shortcut.isVisible()) {
		await shortcut.click();
	} else {
		await page.locator('[data-linker-planner-entry="home-hero"] a').click();
		await page
			.locator('[data-linker-planner]')
			.getByRole('button', {
				name: language === 'en' ? 'Projects' : 'Projekte',
				exact: true,
			})
			.click();
	}
	const row = page
		.getByRole('listitem')
		.filter({ has: page.locator('[id="sc-project-' + projectId + '"]') });
	await row
		.getByRole('link', {
			name:
				language === 'en' ? 'Compare options' : 'Optionen vergleichen',
			exact: true,
		})
		.click();
	await expect(page).toHaveURL(new RegExp('[?&]project=' + projectId));
}
