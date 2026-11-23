import { expect, type Page } from '@playwright/test';
import { instance } from './instance';

export type SiteLanguage = 'en' | 'de';
const entry = {
	en: {
		home: '/',
		configurator: '/solution-configurator/',
		plan: 'Use a roof plan or measurements',
		deleteProject: 'Delete project',
	},
	de: {
		home: '/de/',
		configurator: '/de/loesungskonfigurator/',
		plan: 'Dachplan oder Aufmaß verwenden',
		deleteProject: 'Projekt löschen',
	},
} as const;

export async function roofEntry(page: Page, lang: SiteLanguage) {
	const text = entry[lang];
	await page.goto(instance().url + text.home, {
		waitUntil: 'domcontentloaded',
	});
	await page.locator('a.showcase-roof').click();
	const workspace = page.locator('[data-linker-planner]');
	return workspace
		.locator('form')
		.filter({ has: page.locator('[name="location_label"]') });
}

export async function startSolarProject(
	page: Page,
	lang: SiteLanguage,
	title: string
) {
	const text = entry[lang];
	const form = await roofEntry(page, lang);
	const workspace = page.locator('[data-linker-planner]');
	await form.locator('[name="country"]').selectOption('DE');
	await form.locator('[name="location_label"]').fill(title);
	await form.getByRole('button', { name: text.plan, exact: true }).click();
	await expect(page).toHaveURL(/project=[a-f0-9]{32}#sc-roof-plan$/, {
		timeout: 60000,
	});
	return workspace;
}

export async function removeSiteProject(
	page: Page,
	lang: SiteLanguage,
	title: string
) {
	await page.goto(instance().url + entry[lang].configurator + '?projects=1', {
		waitUntil: 'domcontentloaded',
	});
	const row = page.getByRole('listitem').filter({
		has: page.getByRole('heading', {
			name: title,
			exact: true,
		}),
	});
	await row
		.getByRole('button', {
			name: new RegExp(
				lang === 'en' ? '^Delete project ' : '^Projekt .* löschen$'
			),
		})
		.click();
	await row
		.getByRole('button', {
			name: entry[lang].deleteProject,
			exact: true,
		})
		.click();
	await expect(row).toHaveCount(0);
}
