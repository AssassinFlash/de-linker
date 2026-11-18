/** The planner's first rendered frame must already speak the page language. */
import { expect, test } from '@playwright/test';
import { instance } from '../lib/instance';

test.setTimeout(180_000);

test('de: the initial project form is German while the catalog load is delayed', async ({
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

	const firstForm = page.evaluate(
		() =>
			new Promise<string | null>((resolve) => {
				const root = document.querySelector('[data-linker-planner]')!;
				const observer = new MutationObserver(() => {
					const form = root.querySelector('form[aria-label]');
					if (form) {
						observer.disconnect();
						resolve(form.getAttribute('aria-label'));
					}
				});
				observer.observe(root, { childList: true, subtree: true });
			})
	);
	release();
	expect(await firstForm).toBe('Neues Projekt');
	const form = page.getByRole('form', { name: 'Neues Projekt', exact: true });
	await expect(form.getByLabel('Geplantes System')).toBeVisible({
		timeout: 120_000,
	});
	await expect(
		form.getByRole('heading', { name: 'Was planen Sie?' })
	).toBeVisible();
	await form.getByLabel('Geplantes System').selectOption('new_pv_storage');
	await expect(
		page.getByRole('button', { name: 'Systeme vergleichen' })
	).toBeVisible();
	await form.getByText('Standortdetails', { exact: true }).click();
	await expect(form.getByLabel('Projektname (optional)')).toBeVisible();
	await expect(
		page.getByRole('button', { name: 'Gespeicherte Projekte' })
	).toBeVisible();
	await expect(
		page.getByRole('navigation', { name: 'Projektnavigation' })
	).toBeVisible();
	await expect(form).not.toContainText(/Project name|Compare systems/);
});
