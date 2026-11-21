import { expect, test, type Locator, type Page } from '@playwright/test';
import { roofEntry, removeSiteProject } from '../lib/configurator-site';
import { seedConsentCookies } from '../lib/consent';

test.beforeEach(async ({ context, page }) => {
	await seedConsentCookies(context);
	page.setDefaultTimeout(20_000);
});

const words = {
	en: {
		home: '/',

		open: 'Open aerial map',

		module: 'PV module',
		pitch: 'Pitch (°)',
		azimuth: 'Azimuth (°)',
		height: 'Relative roof height (m)',
		rows: 'Rows',
		columns: 'Columns',
		gap: 'Module gap (m)',
		placed: 'placed modules',
	},
	de: {
		home: '/de/',

		open: 'Luftbildkarte öffnen',

		module: 'PV-Modul',
		pitch: 'Dachneigung (°)',
		azimuth: 'Azimut (°)',
		height: 'Relative Dachhöhe (m)',
		rows: 'Reihen',
		columns: 'Spalten',
		gap: 'Modulabstand (m)',
		placed: 'platzierte Module',
	},
};

const address = 'Museumstraat 1, 1071 XX Amsterdam';
const roofCorners = [
	[-35, 15],
	[55, -110],
	[108, -72],
	[18, 53],
] as const;

function response(page: Page, path: string) {
	return page.waitForResponse(
		(reply) =>
			reply.request().method() === 'POST' &&
			new URL(reply.url()).pathname.endsWith('/' + path)
	);
}

async function centre(map: Locator) {
	await map.scrollIntoViewIfNeeded();
	const bounds = await map.boundingBox();
	if (!bounds) throw new Error('Map canvas has no visible bounds');
	return { x: bounds.width / 2, y: bounds.height / 2 };
}

async function traceRoof(page: Page, map: Locator, touch: boolean) {
	await map.scrollIntoViewIfNeeded();
	const bounds = await map.boundingBox();
	if (!bounds) throw new Error('Map canvas has no visible bounds');
	const points = [...roofCorners, roofCorners[0]].map(([dx, dy]) => ({
		x: bounds.x + bounds.width / 2 + dx,
		y: bounds.y + bounds.height / 2 + dy,
	}));
	const first = points[0]!;
	if (touch) {
		const cdp = await page.context().newCDPSession(page);
		await cdp.send('Input.dispatchTouchEvent', {
			type: 'touchStart',
			touchPoints: [first],
		});
		for (const point of points.slice(1)) {
			await cdp.send('Input.dispatchTouchEvent', {
				type: 'touchMove',
				touchPoints: [point],
			});
		}
		await cdp.send('Input.dispatchTouchEvent', {
			type: 'touchEnd',
			touchPoints: [],
		});
		await cdp.detach();
		return;
	}
	await page.mouse.move(first.x, first.y);
	await page.mouse.down();
	for (const point of points.slice(1))
		await page.mouse.move(point.x, point.y, { steps: 5 });
	await page.mouse.up();
}

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${lang} ${width}: locate a building from home and reopen its roof layout`, async ({
			page,
			browser,
		}) => {
			const text = words[lang];
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			const requestedTiles: string[] = [];
			page.on('request', (r) => {
				if (new URL(r.url()).hostname === 'service.pdok.nl')
					requestedTiles.push(r.url());
			});
			const homeForm = await roofEntry(page, lang);
			await homeForm.locator('[name="country"]').selectOption('NL');
			const offer = page.waitForRequest(
				(r) =>
					r.method() === 'POST' &&
					new URL(r.url()).pathname.endsWith('/places/lookup') &&
					r.postDataJSON()?.country === 'NL'
			);
			await homeForm.locator('[name="location_label"]').fill(address);
			const sourceRead = await page.request.fetch(await offer);
			expect(sourceRead.ok()).toBe(true);
			const { imagery } = await sourceRead.json();
			await expect(
				homeForm.locator('[name="roof_imagery_consent"]')
			).toBeVisible();
			expect(requestedTiles).toEqual([]);
			await homeForm.locator('[name="roof_imagery_consent"]').check();
			const image = page.waitForResponse(
				(r) =>
					new URL(r.url()).hostname === 'service.pdok.nl' &&
					r.ok() &&
					/^image\//.test(r.headers()['content-type'] ?? '')
			);
			await homeForm
				.getByRole('button', { name: text.open, exact: true })
				.click();
			await expect(page).toHaveURL(/project=[^&#]+#sc-roof/);
			const id = new URL(page.url()).searchParams.get('project');
			const map = page.locator('.maplibregl-canvas');
			await image;
			const show =
				lang === 'en' ? 'Show aerial map' : 'Luftbildkarte anzeigen';
			const hide =
				lang === 'en' ? 'Hide aerial map' : 'Luftbildkarte ausblenden';
			const view = page.locator('[data-map-status]');
			await expect(
				view.getByRole('link', {
					name:
						lang === 'en'
							? 'Map attribution'
							: 'Quellenangaben zur Karte',
				})
			).toBeVisible();
			await expect(view).toContainText(
				imagery.credit + ' — ' + imagery.licence
			);
			await expect(
				view.getByRole('link', {
					name:
						lang === 'en'
							? 'Map attribution'
							: 'Quellenangaben zur Karte',
				})
			).toHaveAttribute('href', imagery.licence_url);
			await view.getByRole('button', { name: hide, exact: true }).click();
			const hidden = view.getByRole('button', {
				name: show,
				exact: true,
			});
			await expect(hidden).toHaveAttribute('aria-pressed', 'false');
			const afterWithdrawal = requestedTiles.length;
			// Changing the map area with the aerial layer off must stay local.
			await view
				.getByRole('button', {
					name: lang === 'en' ? 'Zoom in' : 'Vergrößern',
					exact: true,
				})
				.click();
			await expect(view).toHaveAttribute('data-map-status', 'ready');
			expect(requestedTiles.length).toBe(afterWithdrawal);
			await hidden.click();
			await expect(
				view.getByRole('button', { name: hide, exact: true })
			).toHaveAttribute('aria-pressed', 'true');
			await expect(
				page.getByRole('button', {
					name: /Add corner at map centre|Eckpunkt.*Kartenmitte/i,
				})
			).toBeEnabled({ timeout: 35000 });
			await page.getByLabel(text.pitch, { exact: true }).fill('10');
			await page.getByLabel(text.azimuth, { exact: true }).fill('180');
			await page.getByLabel(text.height, { exact: true }).fill('5');
			const mid = await centre(map);
			const savedRoof = response(page, 'projects/revise');
			await traceRoof(page, map, width === 390);
			expect((await savedRoof).ok()).toBe(true);

			const editor = page.locator('.sc-solar');
			for (const [field, value] of Object.entries({
				panel_length_mm: '1800',
				panel_width_mm: '1100',
				panel_thickness_mm: '30',
				panel_power_w: '430',
			}))
				await editor.locator('input[name="' + field + '"]').fill(value);
			await editor.getByLabel(text.rows, { exact: true }).fill('2');
			await editor.getByLabel(text.columns, { exact: true }).fill('2');
			await editor.getByLabel(text.gap, { exact: true }).fill('0.02');
			const savedLayout = page.waitForResponse(
				(reply) =>
					new URL(reply.url()).pathname.endsWith(
						'/projects/revise'
					) &&
					reply.request().postDataJSON()?.inputs?.geometry?.arrays
						?.length === 1
			);
			await map.click({ position: { x: mid.x + 25, y: mid.y - 8 } });
			const receipt = await savedLayout;
			expect(receipt.ok()).toBe(true);
			const saved = receipt.request().postDataJSON();
			const geometry = saved.inputs.geometry;
			expect(saved.project_id).toBe(id);
			expect(geometry.roofs).toHaveLength(1);
			expect(geometry.module_specs).toMatchObject([
				{
					model: 'PV 430 Wp · 1800 × 1100 mm',
					stc_power_w: 430,
					gamma_pdc_per_c: null,
				},
			]);
			expect(geometry.module_specs[0].source.woo).toBeUndefined();
			expect(geometry.arrays).toMatchObject([
				{ rows: 2, columns: 2, roof_id: geometry.roofs[0].id },
			]);
			expect(
				geometry.sources.find(
					(source: { id: string }) =>
						source.id === geometry.roofs[0].source_id
				)
			).toMatchObject({
				rights_basis: 'referenced_licence',
				reference_url: 'https://creativecommons.org/licenses/by/4.0/',
			});
			const counter = '4 ' + text.placed;
			await expect(editor).toContainText(counter);
			const title = await page
				.locator('.sc-project-heading h1')
				.innerText();
			await page.reload({ waitUntil: 'domcontentloaded' });
			await expect(editor).toContainText(counter);
			const clean = await browser.newContext({
				viewport: page.viewportSize(),
				storageState: await page.context().storageState(),
			});
			try {
				const reopened = await clean.newPage();
				await reopened.goto(page.url(), {
					waitUntil: 'domcontentloaded',
				});
				await expect(reopened.locator('.sc-solar-total')).toContainText(
					counter
				);
				const cookieChoice = reopened.locator(
					'[data-cky-tag="reject-button"]:visible'
				);
				if (await cookieChoice.isVisible()) await cookieChoice.click();
				const show = reopened.getByRole('button', {
					name:
						lang === 'en'
							? 'Show aerial map'
							: 'Luftbildkarte anzeigen',
				});
				await show.click();
				await expect(
					reopened.getByRole('button', {
						name:
							lang === 'en'
								? 'Hide aerial map'
								: 'Luftbildkarte ausblenden',
					})
				).toBeEnabled();
				await reopened
					.getByRole('button', {
						name:
							lang === 'en' ? 'Draw roof' : 'Dachfläche zeichnen',
						exact: true,
					})
					.click();
				await expect(
					reopened.getByRole('button', {
						name: /Add corner at map centre|Eckpunkt.*Kartenmitte/i,
					})
				).toBeEnabled({ timeout: 35000 });
				const aerial = reopened.locator('[data-map-status]');
				await aerial.scrollIntoViewIfNeeded();
				await aerial.screenshot({
					path: test.info().outputPath('reopened-layout.png'),
				});
			} finally {
				await clean.close();
			}
			await removeSiteProject(page, lang, title);
		});
	}
}

test('a Berlin street address opens the disclosed state aerial layer', async ({
	page,
}) => {
	const form = await roofEntry(page, 'de');
	await form.locator('[name="country"]').selectOption('DE');
	await form
		.locator('[name="location_label"]')
		.fill('Platz der Republik 1, 11011 Berlin');
	const permission = form.getByRole('checkbox', {
		name: /Luftbilder.*Berlin/i,
	});
	await permission.check();
	await form
		.getByRole('button', { name: 'Luftbildkarte öffnen', exact: true })
		.click();
	await expect(page).toHaveURL(/#sc-roof$/);
	await expect(
		page.getByRole('button', {
			name: 'Eckpunkt in der Kartenmitte hinzufügen',
		})
	).toBeEnabled({ timeout: 60000 });
	await expect(page.locator('[data-map-status]')).toContainText('Berlin');
	await removeSiteProject(
		page,
		'de',
		await page.locator('.sc-project-heading h1').innerText()
	);
});

test('a site without an aerial layer can continue with a measured roof', async ({
	page,
}) => {
	const form = await roofEntry(page, 'en');
	await form.locator('[name="country"]').selectOption('BA');
	await form
		.locator('[name="location_label"]')
		.fill('Obala Kulina bana 1, 71000 Sarajevo');
	await form
		.getByRole('button', { name: 'Open aerial map', exact: true })
		.click();
	await expect(page).toHaveURL(/#sc-roof$/);
	await page
		.getByRole('button', { name: 'Enter roof measurements', exact: true })
		.click();
	await expect(page.getByLabel('Width (m)', { exact: true })).toBeVisible();
	await removeSiteProject(
		page,
		'en',
		await page.locator('.sc-project-heading h1').innerText()
	);
});
