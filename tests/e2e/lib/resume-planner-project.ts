import { expect, type Page } from '@playwright/test';
import { instance } from './instance';

/** Return as the installer to the saved project and its optional design chapters. */
export async function resumePlannerProject(
	page: Page,
	language: 'en' | 'de',
	title: string
) {
	const de = language === 'de';
	await page.goto(instance().url + (de ? '/de/' : '/'));
	await page.locator('[data-linker-planner-entry="home-hero"] a').click();
	const workspace = page.locator('[data-linker-planner]');
	await workspace
		.getByRole('button', {
			name: de ? 'Projekte' : 'Projects',
			exact: true,
		})
		.click();
	const saved = workspace
		.getByRole('listitem')
		.filter({
			has: page.getByRole('heading', { name: title, exact: true }),
		});
	await saved
		.getByRole('button', {
			name: de ? 'Projekt öffnen' : 'Open project',
			exact: true,
		})
		.click();
	const nav = workspace.getByRole('navigation', {
		name: de ? 'Projektnavigation' : 'Project navigation',
	});
	await expect(nav).toBeVisible();
	return nav;
}
