/** The planner's first rendered frame must already speak the page language. */
import { expect, test } from '@playwright/test';
import { instance } from '../lib/instance';

test.setTimeout(180_000);

test('de: the first New project dialog is German while the catalog load is delayed', async ({
	page,
}) => {
	expect(instance().url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
	// Hold the full translation catalog back until the unmounted shell state
	// has been observed; the loader promise is bounded, but nothing else in
	// this test may rely on that bound.
	let release!: () => void;
	const gate = new Promise<void>((resolve) => {
		release = resolve;
	});
	await page.route('**/linker-tools-de_DE_formal-*.json*', async (route) => {
		await gate;
		await route.continue();
	});
	await page.goto(`${instance().url}/de/loesungskonfigurator/`);

	// The footer loader has run and the module has executed, yet the React
	// workspace must not mount with an untranslated form while the catalog is
	// still in flight: the server-rendered German status is all there is.
	await page.waitForFunction(
		() =>
			typeof (window as { linkerToolsCatalog?: unknown })
				.linkerToolsCatalog !== 'undefined'
	);
	await expect(
		page.locator('[data-linker-planner] [role="status"]')
	).toHaveText(/Ihr Arbeitsbereich wird geöffnet/);
	await expect(page.locator('[data-linker-planner] button')).toHaveCount(0);
	await expect(page.locator('[data-linker-planner]')).not.toContainText(
		'New project'
	);

	release();
	// The shell button itself is inline-translated; the dialog strings come
	// from the now-loaded full catalog, and the first dialog render must
	// already be German — not an English frame that translates afterwards.
	await expect(
		page.getByRole('button', { name: 'Neues Projekt' })
	).toBeVisible({ timeout: 120_000 });
	await page.getByRole('button', { name: 'Neues Projekt' }).click();
	const dialog = page.locator('.lp-new-project');
	await expect(dialog).toBeVisible();
	await expect(dialog).toContainText('Projektname');
	const actions = dialog.locator('.lp-inline-actions button');
	await expect(actions.filter({ hasText: 'Projekt anlegen' })).toBeVisible();
	await expect(actions.filter({ hasText: 'Abbrechen' })).toBeVisible();
	await expect(dialog).not.toContainText('Create project');
	await expect(dialog).not.toContainText('Cancel');
});
