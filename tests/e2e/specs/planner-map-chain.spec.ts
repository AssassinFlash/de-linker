/**
 * The roof-drawing map workspace mounts through a fully drivable chain
 * (state-matrix rows initial-map .. validation-error, previously deferred to
 * CU as "map canvas chain"): a project with a site anchor and a first roof
 * face whose coordinate reference is true north unlocks Start roof drawing,
 * and the maplibre canvas mounts. This spec pins that chain - the entry row
 * for the drawing states that follow.
 */
/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

test('the map workspace mounts from a plain project through the full chain', async ({
	page,
}) => {
	await page.goto(instance().url + '/solution-configurator/', {
		waitUntil: 'networkidle',
	});

	// 1. New project: the title is the only field keeping Create disabled.
	await page.getByRole('button', { name: 'New project' }).first().click();
	await page.locator('input[maxlength="256"]').first().fill('Map chain e2e');
	await page.getByRole('button', { name: 'Create project' }).click();
	await expect(page).toHaveURL(/project=/, { timeout: 60_000 });

	// 2. The site anchor: country, address and coordinates.
	const site = page.locator('#lp-site');
	await site.locator('select').first().selectOption('DE');
	await site.locator('input').nth(0).fill('Triftstrasse 5');
	await site.locator('input').nth(1).fill('48.1689');
	await site.locator('input').nth(2).fill('11.5844');

	// 3. Into the roof workspace: open the overview section first - the
	// empty-state button renders collapsed (zero size) until then.
	await page.getByRole('link', { name: 'Project overview' }).click();
	const roofEntry = page.locator('.lp-overview-empty .lp-button');
	await roofEntry.waitFor({ state: 'attached' });
	await page.evaluate(
		(el) => (el as HTMLElement).click(),
		await roofEntry.elementHandle()
	);
	await expect(page).toHaveURL(/#lp-design/, { timeout: 15_000 });

	// 4. The first roof face: every field including the rights note, which is
	// the one required field a quick pass misses.
	await page
		.locator('#lp-design button', { hasText: 'Add roof face' })
		.click();
	const faceForm = page.locator('#lp-design form');
	await faceForm.locator('[name="name"]').fill('Main roof');
	await faceForm.locator('[name="width"]').fill('10');
	await faceForm.locator('[name="length"]').fill('6');
	await faceForm.locator('[name="pitch"]').fill('30');
	await faceForm.locator('[name="bearing"]').fill('180');
	await faceForm.locator('[name="source"]').fill('Owner measurement');
	await faceForm
		.locator('[name="rights_note"]')
		.fill('Owner-provided tape measurement');
	await faceForm.locator('[name="rights"]').check();
	await faceForm.locator('button[type="submit"]').click();

	// 5. Coordinate references: true north with the anchor coordinates and a
	// source - drawingBridge requires both halves.
	await page
		.locator('#lp-design button', {
			hasText: 'Coordinate references',
		})
		.click();
	const coordForm = page.locator('#lp-design form');
	await coordForm.locator('select[name="north"]').selectOption('true_north');
	await coordForm.locator('[name="latitude"]').fill('48.1689');
	await coordForm.locator('[name="longitude"]').fill('11.5844');
	const northSource = coordForm.locator('select[name="north_source"]');
	if ((await northSource.locator('option').count()) > 1) {
		await northSource.selectOption({ index: 1 });
	}
	const anchorSource = coordForm.locator('select[name="anchor_source"]');
	if ((await anchorSource.locator('option').count()) > 1) {
		await anchorSource.selectOption({ index: 1 });
	}
	await coordForm.locator('button[type="submit"]').click();

	// 6-7. The Map tab's Start roof drawing gate opens and the canvas mounts.
	await page.locator('#lp-design button', { hasText: /^Map$/ }).click();
	const start = page
		.locator('#lp-design button', { hasText: 'Start roof drawing' })
		.first();
	await expect(start, 'the geographic gate opens').toBeEnabled({
		timeout: 30_000,
	});
	await start.click();

	await expect(
		page.locator('.maplibregl-canvas'),
		'the maplibre canvas mounts'
	).toBeVisible({ timeout: 60_000 });
	await expect(page.locator('[aria-label="Project map"]')).toBeVisible();
});
