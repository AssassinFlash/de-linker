import { expect, test, type Locator, type Page } from '@playwright/test';
import { instance } from '../lib/instance';

const words = {
	en: {
		home: '/',
		roof: 'Start with your roof',
		open: 'Open aerial map',
		show: 'Show aerial map',
		finish: 'Finish outline',
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
		roof: 'Dach planen',
		open: 'Luftbildkarte öffnen',
		show: 'Luftbildkarte anzeigen',
		finish: 'Umriss abschließen',
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
		}) => {
			const text = words[lang];
			await page.setViewportSize({
				width,
				height: width === 390 ? 844 : 900,
			});
			await page.goto(instance().url + text.home);
			const homeForm = page
				.getByRole('form')
				.filter({
					has: page.locator(
						'[name="roof_imagery_consent"], [name="location_label"]'
					),
				});
			await homeForm.locator('[name="country"]').selectOption('NL');
			await homeForm.locator('[name="location_label"]').fill(address);
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
			await editor
				.getByRole('combobox', { name: text.module, exact: true })
				.selectOption({
					label: 'Trina Solar TSM-460NEG9R.28 · 460 Wp',
				});
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
			const saved = await receipt.json();
			await page.reload();
			expect(saved).toMatchObject({
				id,
				inputs: {
					geometry: {
						roofs: [
							expect.objectContaining({ id: expect.any(String) }),
						],
						arrays: [
							expect.objectContaining({ rows: 2, columns: 2 }),
						],
					},
				},
			});
			expect(saved.inputs.geometry.arrays[0].roof_id).toBe(
				saved.inputs.geometry.roofs[0].id
			);
			await expect(editor).toContainText('4 ' + text.placed);
			await page.screenshot({
				path: test.info().outputPath('reopened-layout.png'),
			});
		});
	}
}
