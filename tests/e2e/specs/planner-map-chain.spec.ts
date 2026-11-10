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

type Lang = 'en' | 'de';

/** The chain's own words, each language's page as it ships. */
const WORDS = {
	en: {
		configurator: '/solution-configurator/',
		newProject: 'New project',
		create: 'Create project',
		overview: 'Project overview',
		sections: 'Project sections',
		addRoofFace: 'Add roof face',
		coordRefs: 'Coordinate references',
		mapTab: /^Map$/,
		startDrawing: 'Start roof drawing',
		corners: 'Recorded corners: ',
		removeLast: 'Remove last corner',
		closeOutline: 'Close outline and review',
		roofProps: 'Roof properties',
		pauseDrawing: 'Pause drawing',
		addModuleSpec: 'Add module specification',
		addModuleArray: 'Add module array',
		pausedRetained: 'Drawing paused and retained',
		geometryChanged:
			'The project geometry has changed since this drawing began',
		discard: 'Discard drawing',
		saveProject: 'Save project',
		savedState: 'Saved',
		boundary: 'Boundary to edit',
		roofFace: 'Roof face',
		featureType: 'Feature type',
		obstacle: 'Obstacle',
		obstacleFootprint: 'Obstacle footprint',
		drawFeature: 'Draw a roof feature',
		roofAdded: 'Roof added to the project draft',
		featureAdded: 'Feature added to the project draft',
		axis: 'Vertically upward',
		loadStreet: 'Load street map',
		hideStreet: 'Hide street map',
		mapNotDisplayed: 'could not be fully displayed',
		retryMap: 'Retry loading map',
		designView: 'Design view',
		planBtn: 'Plan',
		viewMap: 'Map',
		roofDesign: 'Roof design',
		projectMap: 'Project map',
		fieldInvalid: 'missing or invalid',
	},
	de: {
		configurator: '/de/loesungskonfigurator/',
		newProject: 'Neues Projekt',
		create: 'Projekt anlegen',
		overview: 'Projektübersicht',
		sections: 'Projektbereiche',
		addRoofFace: 'Dachfläche hinzufügen',
		coordRefs: 'Koordinatenbezüge',
		mapTab: /^Karte$/,
		startDrawing: 'Zeichnung beginnen',
		corners: 'Erfasste Eckpunkte: ',
		removeLast: 'Letzten Eckpunkt entfernen',
		closeOutline: 'Umriss schließen und prüfen',
		roofProps: 'Dacheigenschaften',
		pauseDrawing: 'Zeichnung pausieren',
		addModuleSpec: 'Modulspezifikation hinzufügen',
		addModuleArray: 'Modulfeld hinzufügen',
		pausedRetained: 'Zeichnung pausiert und',
		geometryChanged:
			'Die Projektgeometrie wurde seit Beginn dieser Zeichnung geändert',
		discard: 'Zeichnung verwerfen',
		saveProject: 'Projekt speichern',
		savedState: 'Gespeichert',
		boundary: 'Zu bearbeitender Umriss',
		roofFace: 'Dachfläche',
		featureType: 'Objekttyp',
		obstacle: 'Hindernis',
		obstacleFootprint: 'Grundriss des Hindernisses',
		drawFeature: 'Objekt auf der Dachfläche zeichnen',
		roofAdded: 'Die Dachfläche wurde dem Projektentwurf hinzugefügt',
		featureAdded: 'Das Objekt wurde dem Projektentwurf hinzugefügt',
		axis: 'Senkrecht nach oben',
		loadStreet: 'Straßenkarte laden',
		hideStreet: 'Straßenkarte ausblenden',
		mapNotDisplayed: 'konnte nicht vollständig angezeigt werden',
		retryMap: 'Karte erneut laden',
		designView: 'Planungsansicht',
		planBtn: 'Draufsicht',
		viewMap: 'Karte',
		roofDesign: 'Dachplanung',
		projectMap: 'Projektkarte',
		fieldInvalid: 'ungültig',
	},
} as const;

/** German number fields take a decimal comma (the field's own hint). */
function num(lang: Lang, value: string): string {
	return 'de' === lang ? value.replace('.', ',') : value;
}

/** Drives a plain project through the full gate chain - site anchor, first
 * roof face, true-north coordinate reference - into a mounted, collecting
 * map workspace with the corner counter live. */
async function openDrawingWorkspace(page: Page, lang: Lang) {
	const words = WORDS[lang];
	await page.goto(instance().url + words.configurator, {
		waitUntil: 'networkidle',
	});

	// 1. New project: the title is the only field keeping Create disabled.
	await page.getByRole('button', { name: words.newProject }).first().click();
	await page.locator('input[maxlength="256"]').first().fill('Map chain e2e');
	await page.getByRole('button', { name: words.create }).click();
	await expect(page).toHaveURL(/project=/, { timeout: 60_000 });
	// The section navigation only answers once the app has hydrated - a
	// click on the overview link before that is swallowed (observed on the
	// German page). The save-state status is the hydrated app chrome.
	await expect(page.locator('.lp-save-state')).toBeVisible({
		timeout: 30_000,
	});

	// 2. The site anchor: country, address and coordinates.
	const site = page.locator('#lp-site');
	await site.locator('select').first().selectOption('DE');
	await site.locator('input').nth(0).fill('Triftstrasse 5');
	await site.locator('input').nth(1).fill(num(lang, '48.1689'));
	await site.locator('input').nth(2).fill(num(lang, '11.5844'));

	// 3. Into the roof workspace: open the overview section first - the
	// empty-state button renders collapsed (zero size) until then. Desktop
	// exposes section links; the phone viewport is a Project sections
	// combobox (both live in the DOM, one per viewport).
	const overviewLink = page.getByRole('link', { name: words.overview });
	if (await overviewLink.isVisible()) await overviewLink.click();
	else
		await page
			.getByRole('combobox', { name: words.sections })
			.selectOption('overview');
	const roofEntry = page.locator('.lp-overview-empty .lp-button');
	// A plain click waits for the button to be visible and stable - an
	// evaluate-click can land before hydration binds the handler (observed
	// on the German page, whose catalog loads make hydration slower).
	await roofEntry.click();
	await expect(page).toHaveURL(/#lp-design/, { timeout: 15_000 });

	// 4. The first roof face: every field including the rights note, which is
	// the one required field a quick pass misses.
	// Exact role name: on the German page a substring also matches the
	// empty-state's "Erste Dachfläche hinzufügen".
	await page
		.locator('#lp-design button.lp-button', { hasText: words.addRoofFace })
		.first()
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
			hasText: words.coordRefs,
		})
		.click();
	const coordForm = page.locator('#lp-design form');
	await coordForm.locator('select[name="north"]').selectOption('true_north');
	await coordForm.locator('[name="latitude"]').fill(num(lang, '48.1689'));
	await coordForm.locator('[name="longitude"]').fill(num(lang, '11.5844'));
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
	await page.locator('#lp-design button', { hasText: words.mapTab }).click();
	const start = page
		.locator('#lp-design button', { hasText: words.startDrawing })
		.first();
	await expect(start, 'the geographic gate opens').toBeEnabled({
		timeout: 30_000,
	});
	await start.click();

	await expect(
		page.locator('.maplibregl-canvas'),
		'the maplibre canvas mounts'
	).toBeVisible({ timeout: 60_000 });
	await expect(
		page.locator(`[aria-label="${words.projectMap}"]`)
	).toBeVisible();

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
	await expect(counter).toContainText(`${words.corners}0`);
	return { counter };
}

for (const lang of ['en', 'de'] as const) {
	const words = WORDS[lang];
	test(`${lang}: the map workspace mounts from a plain project through the full chain`, async ({
		page,
	}) => {
		const { counter } = await openDrawingWorkspace(page, lang);
		const rect = (await page.locator('.maplibregl-canvas').boundingBox())!;
		const spots: Array<[number, number]> = [
			[rect.x + rect.width * 0.4, rect.y + rect.height * 0.4],
			[rect.x + rect.width * 0.6, rect.y + rect.height * 0.4],
			[rect.x + rect.width * 0.6, rect.y + rect.height * 0.6],
			[rect.x + rect.width * 0.4, rect.y + rect.height * 0.6],
		];
		for (const [i, [x, y]] of spots.entries()) {
			await page.mouse.click(x, y);
			await expect(counter).toContainText(`${words.corners}${i + 1}`, {
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
			.locator('#lp-design button', { hasText: words.removeLast })
			.click();
		await expect(counter).toContainText(`${words.corners}3`, {
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
		await expect(counter).toContainText(`${words.corners}4`, {
			timeout: 10_000,
		});

		// A closed ring stages the outline: the review panel offers the roof
		// properties (Add module array itself waits for a module specification,
		// the next state row).
		await page
			.locator('#lp-design button', { hasText: words.closeOutline })
			.click();
		await expect(
			page.locator('#lp-design a', { hasText: words.roofProps })
		).toBeVisible({ timeout: 30_000 });

		// The staged drawing keeps the drawing panel open, which gates the
		// design forms; parking it with Pause drawing closes the panel.
		await page
			.locator('#lp-design button', { hasText: words.pauseDrawing })
			.click();
		await page
			.locator('#lp-design button', { hasText: words.addModuleSpec })
			.click({ timeout: 15_000 });

		// The module-specification state: the tier select is prefilled, and one
		// submit puts the reference module into the project - the gate Add
		// module array waits on (geometry.module_specs.length).
		const moduleForm = page.locator('#lp-design form');
		await moduleForm.locator('select').first().selectOption({ index: 0 });
		await moduleForm.locator('button[type="submit"]').click();
		await expect(
			page.locator('#lp-design button', { hasText: words.addModuleArray })
		).toBeEnabled({ timeout: 30_000 });

		// The parked drawing went stale: the module specification changed the
		// project geometry after the outline was recorded, so the retained
		// drawing can no longer be applied to it (Resume stays disabled by
		// design). The stale notice says so and discarding frees the workspace.
		await expect(counter).toContainText(words.pausedRetained);
		await expect(page.locator('#lp-design')).toContainText(
			words.geometryChanged
		);
		await page
			.locator('#lp-design button', { hasText: words.discard })
			.click();
		const restart = page.locator('#lp-design button', {
			hasText: words.startDrawing,
		});
		await expect(restart.first()).toBeEnabled({ timeout: 15_000 });
		await restart.first().click();
		await page.evaluate(() => {
			document
				.querySelector('.lp-map-surface')
				?.scrollIntoView({ block: 'center' });
		});
		await page.waitForTimeout(800);
		await expect(counter).toContainText(`${words.corners}0`);
		const second = (await page
			.locator('.maplibregl-canvas')
			.boundingBox())!;
		const secondSpots: Array<[number, number]> = [
			[second.x + second.width * 0.4, second.y + second.height * 0.4],
			[second.x + second.width * 0.6, second.y + second.height * 0.4],
			[second.x + second.width * 0.6, second.y + second.height * 0.6],
			[second.x + second.width * 0.4, second.y + second.height * 0.6],
		];
		for (const [i, [x, y]] of secondSpots.entries()) {
			await page.mouse.click(x, y);
			await expect(counter).toContainText(`${words.corners}${i + 1}`, {
				timeout: 10_000,
			});
		}
		await page
			.locator('#lp-design button', { hasText: words.closeOutline })
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
		const stagedBox = (await page
			.locator('.maplibregl-canvas')
			.boundingBox())!;
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
		await expect(counter).toContainText(`${words.corners}5`, {
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
			words.fieldInvalid
		);

		// The save-return state: a corrected pitch passes the engine geometry
		// check, the roof enters the project draft, Save project stores it, and
		// the retained drawing retires - the boundary selector a returning
		// customer edits from now lists both roof boundaries.
		await roofForm.locator('[name="pitch"]').fill('30');
		await roofForm.locator('button[type="submit"]').click();
		await expect(counter).toContainText(words.roofAdded, {
			timeout: 60_000,
		});
		await page.getByRole('button', { name: words.saveProject }).click();
		await expect(page.locator('.lp-save-state')).toContainText(
			words.savedState,
			{
				timeout: 60_000,
			}
		);
		// The boundary selector covers the selected roof; the roof list is the
		// project-wide consumer surface - the map-drawn roof now appears in it
		// next to the manual one, and its boundary is editable on the map.
		const boundaries = page.getByLabel(words.boundary);
		// Role-scoped: on the German page the plain label also matches the plan
		// SVG's and a section's aria-labels.
		const roofList = page.getByRole('combobox', { name: words.roofFace });
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
		await page
			.getByLabel(words.featureType)
			.selectOption({ label: words.obstacle });
		await page.getByRole('button', { name: words.drawFeature }).click();
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
			await expect(counter).toContainText(`${words.corners}${i + 1}`, {
				timeout: 10_000,
			});
		}
		await page
			.locator('#lp-design button', { hasText: words.closeOutline })
			.click();
		const featureForm = page.locator('#lp-map-feature-properties');
		await expect(featureForm).toBeVisible({ timeout: 15_000 });
		await featureForm.locator('[name="name"]').fill('Chimney');
		await featureForm.locator('[name="height"]').fill(num(lang, '1.5'));
		await featureForm
			.locator('[name="axis"]')
			.selectOption({ label: words.axis });
		await featureForm.locator('input[type="checkbox"]').check();
		await featureForm.locator('button[type="submit"]').click();
		await expect(counter).toContainText(words.featureAdded, {
			timeout: 60_000,
		});
		await page.getByRole('button', { name: words.saveProject }).click();
		await expect(page.locator('.lp-save-state')).toContainText(
			words.savedState,
			{
				timeout: 60_000,
			}
		);
		await expect(
			boundaries.locator('option', { hasText: words.obstacleFootprint })
		).toBeAttached({ timeout: 30_000 });
	});

	test(`${lang}: external map requests wait for the street-map opt-in and recover from tile failure`, async ({
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
		const { counter } = await openDrawingWorkspace(page, lang);
		const rect = (await page.locator('.maplibregl-canvas').boundingBox())!;
		await page.mouse.click(
			rect.x + rect.width * 0.4,
			rect.y + rect.height * 0.4
		);
		await expect(counter).toContainText(`${words.corners}1`, {
			timeout: 10_000,
		});
		await page.mouse.click(
			rect.x + rect.width * 0.6,
			rect.y + rect.height * 0.4
		);
		await expect(counter).toContainText(`${words.corners}2`, {
			timeout: 10_000,
		});
		expect(
			external,
			'no external request before the street-map opt-in'
		).toEqual([]);

		// The single opt-in: the street style and its tiles then flow.
		await page.getByRole('button', { name: words.loadStreet }).click();
		await expect
			.poll(() => external.length, { timeout: 30_000 })
			.toBeGreaterThan(0);

		// The permission-error row: denied street tiles surface the failure
		// notice without touching the recorded geometry, and retrying after the
		// denial is lifted recovers the map.
		await page.route('**tiles.openfreemap.org/**', (route) =>
			route.abort()
		);
		await page.getByRole('button', { name: words.hideStreet }).click();
		await page.getByRole('button', { name: words.loadStreet }).click();
		const notice = page
			.locator('.lp-map-view')
			.getByText(words.mapNotDisplayed);
		await expect(notice).toBeVisible({ timeout: 30_000 });
		await expect(counter).toContainText(`${words.corners}2`);
		await page.unroute('**tiles.openfreemap.org/**');
		await page.getByRole('button', { name: words.retryMap }).click();
		await expect(notice).toBeHidden({ timeout: 30_000 });
		await expect(page.locator('.maplibregl-canvas')).toBeVisible();
	});

	test(`${lang}: the design view triad carries the geometry across plan, map and 3D`, async ({
		page,
	}) => {
		const { counter } = await openDrawingWorkspace(page, lang);
		// The view switch stays locked while a drawing is open; discarding the
		// empty drawing frees the triad.
		await page
			.locator('#lp-design button', { hasText: words.discard })
			.click();
		const views = page.getByRole('group', { name: words.designView });
		const third = views.getByRole('button', { name: '3D', exact: true });
		await expect(third).toBeEnabled({ timeout: 15_000 });

		// The orientation-pitch state: the 3D view presents the pitched roof
		// faces (the manual face carries pitch 30 / bearing 180) from the same
		// project geometry the map collected on.
		await third.click();
		await expect(
			page.getByRole('img', { name: words.roofDesign })
		).toBeVisible({
			timeout: 60_000,
		});

		// Plan and map keep serving the same geometry.
		await views.getByRole('button', { name: words.planBtn }).click();
		await expect(page.locator('#lp-design .lp-plan-svg')).toBeVisible({
			timeout: 30_000,
		});
		await views.getByRole('button', { name: words.viewMap }).click();
		await expect(page.locator('.maplibregl-canvas')).toBeVisible({
			timeout: 30_000,
		});
	});

	test.describe(`phone viewport ${lang}`, () => {
		test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

		test(`${lang}: touch taps collect corners and one-finger drags scroll the page`, async ({
			page,
		}) => {
			const { counter } = await openDrawingWorkspace(page, lang);
			const rect = (await page
				.locator('.maplibregl-canvas')
				.boundingBox())!;
			const cdp = await page.context().newCDPSession(page);

			// A touch tap records a corner through the same collector.
			const tap = {
				x: rect.x + rect.width * 0.4,
				y: rect.y + rect.height * 0.4,
			};
			await cdp.send('Input.dispatchTouchEvent', {
				type: 'touchStart',
				touchPoints: [tap],
			});
			await cdp.send('Input.dispatchTouchEvent', {
				type: 'touchEnd',
				touchPoints: [],
			});
			await expect(counter).toContainText(`${words.corners}1`, {
				timeout: 10_000,
			});

			// Cooperative gestures: one finger drags the page, not the map - the
			// corner count stays put while the page scrolls.
			const drag = {
				x: rect.x + rect.width * 0.6,
				y: rect.y + rect.height * 0.6,
			};
			const before = await page.evaluate(() => window.scrollY);
			await cdp.send('Input.dispatchTouchEvent', {
				type: 'touchStart',
				touchPoints: [drag],
			});
			for (let step = 1; step <= 6; step++) {
				await cdp.send('Input.dispatchTouchEvent', {
					type: 'touchMove',
					touchPoints: [{ x: drag.x, y: drag.y - step * 20 }],
				});
			}
			await cdp.send('Input.dispatchTouchEvent', {
				type: 'touchEnd',
				touchPoints: [],
			});
			await page.waitForTimeout(400);
			const after = await page.evaluate(() => window.scrollY);
			expect(after, 'the page scrolled under the map').not.toBe(before);
			await expect(counter).toContainText(`${words.corners}1`);
		});
	});
}
