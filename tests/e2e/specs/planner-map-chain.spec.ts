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
import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

/** Drives a plain project through the full gate chain - site anchor, first
 * roof face, true-north coordinate reference - into a mounted, collecting
 * map workspace with the corner counter live. */
async function openDrawingWorkspace(page: Page) {
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

	// The outline-draw state: plain map clicks add corners (the collector
	// binds map.on('click'); the canvas must first be scrolled fully into
	// view - before that, clicks land in the clipped region and nothing
	// records). The role=status counter is the live evidence.
	await page.evaluate(() => {
		document
			.querySelector('.lp-map-surface')
			?.scrollIntoView({ block: 'center' });
	});
	// Let the scroll settle: a click during the settling misses the map.
	await page.waitForTimeout(800);
	const counter = page.locator('#lp-design [role="status"]');
	await expect(counter).toContainText('Recorded corners: 0');
	return { counter };
}

test('the map workspace mounts from a plain project through the full chain', async ({
	page,
}) => {
	const { counter } = await openDrawingWorkspace(page);
	const rect = (await page.locator('.maplibregl-canvas').boundingBox())!;
	const spots: Array<[number, number]> = [
		[rect.x + rect.width * 0.4, rect.y + rect.height * 0.4],
		[rect.x + rect.width * 0.6, rect.y + rect.height * 0.4],
		[rect.x + rect.width * 0.6, rect.y + rect.height * 0.6],
		[rect.x + rect.width * 0.4, rect.y + rect.height * 0.6],
	];
	for (const [i, [x, y]] of spots.entries()) {
		await page.mouse.click(x, y);
		await expect(counter).toContainText(`Recorded corners: ${i + 1}`, {
			timeout: 10_000,
		});
	}

	// The undo-redo state: Remove last corner drops the newest corner, and
	// re-clicking the same spot restores it - the removed point left the ring,
	// so it is no longer a duplicate. The remove-button click scrolls the
	// canvas out of the viewport (535px in the reference run), and clicks that
	// land on the panel instead of the canvas record nothing; the surface must
	// be scrolled back and settle before the canvas accepts clicks again.
	await page
		.locator('#lp-design button', { hasText: 'Remove last corner' })
		.click();
	await expect(counter).toContainText('Recorded corners: 3', {
		timeout: 10_000,
	});
	await page.evaluate(() => {
		document
			.querySelector('.lp-map-surface')
			?.scrollIntoView({ block: 'center' });
	});
	await page.waitForTimeout(800);
	const redo = (await page.locator('.maplibregl-canvas').boundingBox())!;
	await page.mouse.click(
		redo.x + redo.width * 0.4,
		redo.y + redo.height * 0.6
	);
	await expect(counter).toContainText('Recorded corners: 4', {
		timeout: 10_000,
	});

	// A closed ring stages the outline: the review panel offers the roof
	// properties (Add module array itself waits for a module specification,
	// the next state row).
	await page
		.locator('#lp-design button', { hasText: 'Close outline and review' })
		.click();
	await expect(
		page.locator('#lp-design a', { hasText: 'Roof properties' })
	).toBeVisible({ timeout: 30_000 });

	// The staged drawing keeps the drawing panel open, which gates the
	// design forms; parking it with Pause drawing closes the panel.
	await page
		.locator('#lp-design button', { hasText: 'Pause drawing' })
		.click();
	await page
		.locator('#lp-design button', { hasText: 'Add module specification' })
		.click({ timeout: 15_000 });

	// The module-specification state: the tier select is prefilled, and one
	// submit puts the reference module into the project - the gate Add
	// module array waits on (geometry.module_specs.length).
	const moduleForm = page.locator('#lp-design form');
	await moduleForm.locator('select').first().selectOption({ index: 0 });
	await moduleForm.locator('button[type="submit"]').click();
	await expect(
		page.locator('#lp-design button', { hasText: 'Add module array' })
	).toBeEnabled({ timeout: 30_000 });

	// The parked drawing went stale: the module specification changed the
	// project geometry after the outline was recorded, so the retained
	// drawing can no longer be applied to it (Resume stays disabled by
	// design). The stale notice says so and discarding frees the workspace.
	await expect(counter).toContainText('Drawing paused and retained');
	await expect(page.locator('#lp-design')).toContainText(
		'The project geometry has changed since this drawing began'
	);
	await page
		.locator('#lp-design button', { hasText: 'Discard drawing' })
		.click();
	const restart = page.locator('#lp-design button', {
		hasText: 'Start roof drawing',
	});
	await expect(restart.first()).toBeEnabled({ timeout: 15_000 });
	await restart.first().click();
	await page.evaluate(() => {
		document
			.querySelector('.lp-map-surface')
			?.scrollIntoView({ block: 'center' });
	});
	await page.waitForTimeout(800);
	await expect(counter).toContainText('Recorded corners: 0');
	const second = (await page.locator('.maplibregl-canvas').boundingBox())!;
	const secondSpots: Array<[number, number]> = [
		[second.x + second.width * 0.4, second.y + second.height * 0.4],
		[second.x + second.width * 0.6, second.y + second.height * 0.4],
		[second.x + second.width * 0.6, second.y + second.height * 0.6],
		[second.x + second.width * 0.4, second.y + second.height * 0.6],
	];
	for (const [i, [x, y]] of secondSpots.entries()) {
		await page.mouse.click(x, y);
		await expect(counter).toContainText(`Recorded corners: ${i + 1}`, {
			timeout: 10_000,
		});
	}
	await page
		.locator('#lp-design button', { hasText: 'Close outline and review' })
		.click();

	// The edit-vertices state: the staged outline switches the canvas to the
	// editor, and dragging an edge midpoint adds a corner (4 -> 5) without
	// leaving review. The staging click scrolls the page, so the surface is
	// scrolled back first; canvas-relative fractions still locate the drawn
	// corners because the map camera never moved.
	await page.evaluate(() => {
		document
			.querySelector('.lp-map-surface')
			?.scrollIntoView({ block: 'center' });
	});
	await page.waitForTimeout(800);
	const stagedBox = (await page.locator('.maplibregl-canvas').boundingBox())!;
	await page.mouse.move(
		stagedBox.x + stagedBox.width * 0.5,
		stagedBox.y + stagedBox.height * 0.4
	);
	await page.mouse.down();
	await page.mouse.move(
		stagedBox.x + stagedBox.width * 0.5,
		stagedBox.y + stagedBox.height * 0.35,
		{ steps: 8 }
	);
	await page.mouse.up();
	await expect(counter).toContainText('Recorded corners: 5', {
		timeout: 10_000,
	});

	// The validation-error state: every native required field is satisfied,
	// so the submission reaches the domain check, where pitch 90 breaks the
	// 0 <= pitch < 90 rule. The field-level alert names the field and keeps
	// every entry; the geometry check is never reached.
	const roofForm = page.locator('#lp-map-roof-properties');
	await expect(roofForm).toBeVisible({ timeout: 15_000 });
	await roofForm.locator('[name="name"]').fill('Map roof');
	await roofForm.locator('[name="pitch"]').fill('90');
	await roofForm.locator('[name="bearing"]').fill('180');
	await roofForm.locator('[name="height"]').fill('5');
	await roofForm
		.locator('[name="source"]')
		.fill('Aerial imagery measurement');
	await roofForm
		.locator('[name="calibration"]')
		.fill('Checked against the street alignment');
	await roofForm
		.locator('[name="rights"]')
		.fill('Customer-provided survey extract');
	await roofForm.locator('input[type="checkbox"]').check();
	await roofForm.locator('button[type="submit"]').click();
	await expect(
		roofForm.locator('[aria-invalid="true"][name="pitch"]')
	).toBeVisible();
	await expect(roofForm.locator('.lp-field-error')).toContainText(
		'missing or invalid'
	);

	// The save-return state: a corrected pitch passes the engine geometry
	// check, the roof enters the project draft, Save project stores it, and
	// the retained drawing retires - the boundary selector a returning
	// customer edits from now lists both roof boundaries.
	await roofForm.locator('[name="pitch"]').fill('30');
	await roofForm.locator('button[type="submit"]').click();
	await expect(counter).toContainText('Roof added to the project draft', {
		timeout: 60_000,
	});
	await page.getByRole('button', { name: 'Save project' }).click();
	await expect(page.locator('.lp-save-state')).toContainText('Saved', {
		timeout: 60_000,
	});
	// The boundary selector covers the selected roof; the roof list is the
	// project-wide consumer surface - the map-drawn roof now appears in it
	// next to the manual one, and its boundary is editable on the map.
	const boundaries = page.getByLabel('Boundary to edit');
	const roofList = page.getByLabel('Roof face');
	await expect(boundaries).toBeVisible({ timeout: 30_000 });
	await expect(roofList).toBeVisible();
	await expect(
		roofList.locator('option', { hasText: 'Main roof' })
	).toBeAttached();
	await expect(
		roofList.locator('option', { hasText: 'Map roof' })
	).toBeAttached();

	// The obstacles state: the feature selector drives the same collector for
	// a footprint on the saved map roof. The obstacle review adds height and
	// extrusion direction; the engine check admits it, Save project stores
	// it, and the editor's selection moves to the new obstacle - the
	// boundary selector then offers its footprint.
	await roofList.selectOption({ label: 'Map roof' });
	await page.getByLabel('Feature type').selectOption({ label: 'Obstacle' });
	await page.getByRole('button', { name: 'Draw a roof feature' }).click();
	await page.evaluate(() => {
		document
			.querySelector('.lp-map-surface')
			?.scrollIntoView({ block: 'center' });
	});
	await page.waitForTimeout(800);
	const obstacleBox = (await page
		.locator('.maplibregl-canvas')
		.boundingBox())!;
	const obstacleSpots: Array<[number, number]> = [
		[
			obstacleBox.x + obstacleBox.width * 0.45,
			obstacleBox.y + obstacleBox.height * 0.45,
		],
		[
			obstacleBox.x + obstacleBox.width * 0.55,
			obstacleBox.y + obstacleBox.height * 0.45,
		],
		[
			obstacleBox.x + obstacleBox.width * 0.55,
			obstacleBox.y + obstacleBox.height * 0.55,
		],
	];
	for (const [i, [x, y]] of obstacleSpots.entries()) {
		await page.mouse.click(x, y);
		await expect(counter).toContainText(`Recorded corners: ${i + 1}`, {
			timeout: 10_000,
		});
	}
	await page
		.locator('#lp-design button', { hasText: 'Close outline and review' })
		.click();
	const featureForm = page.locator('#lp-map-feature-properties');
	await expect(featureForm).toBeVisible({ timeout: 15_000 });
	await featureForm.locator('[name="name"]').fill('Chimney');
	await featureForm.locator('[name="height"]').fill('1.5');
	await featureForm
		.locator('[name="axis"]')
		.selectOption({ label: 'Vertically upward' });
	await featureForm.locator('input[type="checkbox"]').check();
	await featureForm.locator('button[type="submit"]').click();
	await expect(counter).toContainText('Feature added to the project draft', {
		timeout: 60_000,
	});
	await page.getByRole('button', { name: 'Save project' }).click();
	await expect(page.locator('.lp-save-state')).toContainText('Saved', {
		timeout: 60_000,
	});
	await expect(
		boundaries.locator('option', { hasText: 'Obstacle footprint' })
	).toBeAttached({ timeout: 30_000 });
});

test('external map requests wait for the street-map opt-in and recover from tile failure', async ({
	page,
}) => {
	// The address-search row of the privacy gate: no tile, glyph, geolocation
	// or address-search request leaves the browser until the visitor selects
	// the disclosed Load street map action (spec 548).
	const external: string[] = [];
	await page.route('**/*', (route) => {
		const url = route.request().url();
		if (!url.includes('127.0.0.1') && !url.startsWith('data:'))
			external.push(url);
		void route.continue();
	});
	const { counter } = await openDrawingWorkspace(page);
	const rect = (await page.locator('.maplibregl-canvas').boundingBox())!;
	await page.mouse.click(
		rect.x + rect.width * 0.4,
		rect.y + rect.height * 0.4
	);
	await expect(counter).toContainText('Recorded corners: 1', {
		timeout: 10_000,
	});
	await page.mouse.click(
		rect.x + rect.width * 0.6,
		rect.y + rect.height * 0.4
	);
	await expect(counter).toContainText('Recorded corners: 2', {
		timeout: 10_000,
	});
	expect(
		external,
		'no external request before the street-map opt-in'
	).toEqual([]);

	// The single opt-in: the street style and its tiles then flow.
	await page.getByRole('button', { name: 'Load street map' }).click();
	await expect
		.poll(() => external.length, { timeout: 30_000 })
		.toBeGreaterThan(0);

	// The permission-error row: denied street tiles surface the failure
	// notice without touching the recorded geometry, and retrying after the
	// denial is lifted recovers the map.
	await page.route('**tiles.openfreemap.org/**', (route) => route.abort());
	await page.getByRole('button', { name: 'Hide street map' }).click();
	await page.getByRole('button', { name: 'Load street map' }).click();
	const notice = page
		.locator('.lp-map-view')
		.getByText('could not be fully displayed');
	await expect(notice).toBeVisible({ timeout: 30_000 });
	await expect(counter).toContainText('Recorded corners: 2');
	await page.unroute('**tiles.openfreemap.org/**');
	await page.getByRole('button', { name: 'Retry loading map' }).click();
	await expect(notice).toBeHidden({ timeout: 30_000 });
	await expect(page.locator('.maplibregl-canvas')).toBeVisible();
});
