/**
 * Native image calibration: a drawing is scaled with two points and a known
 * length, checked against an independent second span, traced, saved and read
 * back from the server — in both page languages and both viewports the owner
 * required (docs/specs/548-interactive-design.md, "import/calibration").
 *
 * The scale arithmetic is asserted against the pixels this test clicks, so a
 * green run means the recorded m/pixel follows from the marks, not that a form
 * accepted a click.
 */
/**
 * External dependencies
 */
import { join } from 'node:path';

import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { seedConsentCookies } from '../lib/consent';
import { instance, REPO_ROOT } from '../lib/instance';

test.setTimeout(240_000);

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

type Lang = 'en' | 'de';

const WORDS = {
	en: {
		configurator: '/solution-configurator/',
		newProject: 'New project',
		create: 'Create project',
		overview: 'Project overview',
		sections: 'Project sections',
		calibrate: 'Calibrate a roof image',
		stepImage: 'Image and roof',
		stepScale: 'Scale',
		stepOutline: 'Outline',
		continue: 'Continue',
		drawingType: 'Drawing type',
		plan: 'Horizontal plan or site plan',
		faceName: 'Roof face name',
		scaleSpan: 'Scale span (0 of 2)',
		checkSpan: 'Check span (0 of 2)',
		outline: 'Roof outline (0 points)',
		scaleLength: 'Real length of the scale span',
		bearing: 'Down-slope bearing as drawn',
		checkLength: 'Real length of the check span',
		recordedScale: 'Recorded scale',
		status: 'Measurement status',
		usable: 'Usable uniform scale',
		referenceOnly: 'Reference only',
		reference: 'Measurement or drawing reference',
		rights: 'Permission or licence basis',
		export: 'Permission to export geometry',
		retention:
			'I have permission to use this drawing, derive the roof outline from it and keep the calibration with the project.',
		add: 'Add roof to current design',
		area: 'Roof-plane area',
		outlinePoints: 'Outline points',
		sourceProperties: 'Source properties',
		saveProject: 'Save project',
		savedState: 'Saved',
		deleteProject: 'Delete project',
	},
	de: {
		configurator: '/de/loesungskonfigurator/',
		newProject: 'Neues Projekt',
		create: 'Projekt anlegen',
		overview: 'Projektübersicht',
		sections: 'Projektbereiche',
		calibrate: 'Dachbild kalibrieren',
		stepImage: 'Bild und Dach',
		stepScale: 'Maßstab',
		stepOutline: 'Umriss',
		continue: 'Weiter',
		drawingType: 'Art der Zeichnung',
		plan: 'Horizontaler Grundriss oder Lageplan',
		faceName: 'Name der Dachfläche',
		scaleSpan: 'Maßstabstrecke (0 von 2)',
		checkSpan: 'Prüfstrecke (0 von 2)',
		outline: 'Dachumriss (0 Punkte)',
		scaleLength: 'Tatsächliche Länge der Maßstabstrecke',
		bearing: 'Gefällerichtung laut Zeichnung',
		checkLength: 'Tatsächliche Länge der Prüfstrecke',
		recordedScale: 'Gespeicherter Maßstab',
		status: 'Status der Messung',
		usable: 'Nutzbarer einheitlicher Maßstab',
		referenceOnly: 'Nur als Referenz',
		reference: 'Aufmaß- oder Zeichnungsreferenz',
		rights: 'Berechtigungs- oder Lizenzgrundlage',
		export: 'Berechtigung zum Export der Geometrie',
		retention:
			'Ich habe die Berechtigung, diese Zeichnung zu verwenden, daraus den Dachumriss abzuleiten und die Kalibrierung mit dem Projekt aufzubewahren.',
		add: 'Dachfläche in den Entwurf übernehmen',
		area: 'Fläche in der Dachebene',
		outlinePoints: 'Umrisspunkte',
		sourceProperties: 'Quelleneigenschaften',
		saveProject: 'Projekt speichern',
		savedState: 'Gespeichert',
		deleteProject: 'Projekt löschen',
	},
} as const;

/** German number fields take a decimal comma. */
function num(lang: Lang, value: string): string {
	return 'de' === lang ? value.replace('.', ',') : value;
}

/** The repository's own 1200 x 800 fixture plan; 600 px is declared as 12 m. */
const DRAWING = join(REPO_ROOT, 'tests/e2e/fixtures/roof-plan-calibration.png');

async function emptyRoofWorkspace(page: Page, lang: Lang, title: string) {
	const words = WORDS[lang];
	await page.goto(instance().url + words.configurator, {
		waitUntil: 'networkidle',
	});
	await page.getByRole('button', { name: words.newProject }).first().click();
	await page.locator('input[maxlength="256"]').first().fill(title);
	await page.getByRole('button', { name: words.create }).click();
	await expect(page).toHaveURL(/project=/, { timeout: 60_000 });
	await expect(page.locator('.lp-save-state')).toBeVisible({
		timeout: 30_000,
	});
	const overviewLink = page.getByRole('link', { name: words.overview });
	if (await overviewLink.isVisible()) await overviewLink.click();
	else
		await page
			.getByRole('combobox', { name: words.sections })
			.selectOption('overview');
	await page.locator('.lp-overview-empty .lp-button').click();
	await expect(page).toHaveURL(/#lp-design/, { timeout: 15_000 });
}

/**
 * A click at an image pixel. The surface uses `xMidYMid meet`, so the
 * letterboxing is removed before the pixel is named; the click is dispatched to
 * the SVG element itself, which keeps it clear of sticky bars at 390 px and of
 * the longer German layout.
 */
async function mark(page: Page, x: number, y: number) {
	const surface = page.locator('.lp-plan-svg');
	await surface.scrollIntoViewIfNeeded();
	const box = await surface.boundingBox();
	if (!box) throw new Error('calibration surface has no box');
	const viewBox = (await surface.getAttribute('viewBox'))!
		.split(' ')
		.map(Number);
	const [width, height] = [viewBox[2]!, viewBox[3]!];
	const scale = Math.min(box.width / width, box.height / height);
	await surface.click({
		position: {
			x: (box.width - width * scale) / 2 + x * scale,
			y: (box.height - height * scale) / 2 + y * scale,
		},
	});
}

test.describe('native image calibration', () => {
	for (const lang of ['en', 'de'] as const) {
		for (const width of [1440, 390]) {
			test(`${lang} @${width}: two points scale the drawing, a second span checks it, the roof is saved and read back`, async ({
				page,
			}) => {
				const words = WORDS[lang];
				await page.setViewportSize({
					width,
					height: width === 390 ? 844 : 900,
				});
				const title = `m-image calibration ${lang} ${width}`;
				await emptyRoofWorkspace(page, lang, title);

				await page
					.getByRole('button', { name: words.calibrate, exact: true })
					.click();
				const panel = page.locator('.lp-import-panel');
				await expect(panel).toBeVisible();
				await expect(panel.getByRole('heading')).toHaveText(
					words.stepImage
				);

				// Step 1 — the browser decodes the image and reports its own pixels.
				await panel
					.locator('input[type="file"]')
					.setInputFiles(DRAWING);
				await expect(panel).toContainText('1200');
				await panel
					.getByRole('combobox', { name: words.drawingType })
					.selectOption('horizontal_plan');
				await panel
					.locator('[name="roof"]')
					.fill('Calibrated drawing roof');
				await panel
					.getByRole('button', { name: words.continue, exact: true })
					.click();

				// Step 2 — the scale span (600 px declared as 12 m) and an
				// independent 480 px span declared as 9.6 m at the same scale.
				await expect(panel.getByRole('heading')).toHaveText(
					words.stepScale
				);
				await panel
					.getByRole('button', { name: words.scaleSpan, exact: true })
					.click();
				await mark(page, 100, 700);
				await mark(page, 700, 700);
				await panel.locator('[name="length"]').fill(num(lang, '12'));
				await panel
					.getByRole('button', { name: words.checkSpan, exact: true })
					.click();
				await mark(page, 100, 100);
				await mark(page, 580, 100);
				// The drawing's page-down faces south, so the roof's down-slope
				// bearing is 180 and the traced page-down edge becomes V.
				await panel.locator('[name="bearing"]').fill(num(lang, '180'));
				await panel
					.locator('[name="check_length"]')
					.fill(num(lang, '9.6'));
				await expect(panel).toContainText(words.recordedScale);
				await expect(panel).toContainText('0.02');
				await expect(panel).toContainText(words.usable);
				await panel
					.getByRole('button', { name: words.continue, exact: true })
					.click();

				// Step 3 — trace the outline on the same calibrated image.
				await expect(panel.getByRole('heading')).toHaveText(
					words.stepOutline
				);
				await panel
					.getByRole('button', { name: words.outline, exact: true })
					.click();
				await mark(page, 100, 100);
				await mark(page, 700, 100);
				await mark(page, 700, 700);
				await mark(page, 100, 700);
				await panel
					.locator('[name="note"]')
					.fill('Synthetic calibration fixture; not a survey');
				await panel
					.locator('[name="rights"]')
					.fill(
						'Own synthetic fixture; deriving and retaining is permitted'
					);
				await panel
					.locator('select[name="export"]')
					.selectOption('permitted');
				await panel
					.locator('[name="precision"]')
					.fill(num(lang, '0.05'));
				await panel.locator('[name="retention"]').check();
				// 600 x 600 px at 0.02 m/px is a 144 m2 roof-plane outline.
				await expect(panel.locator('.lp-import-review')).toContainText(
					words.area
				);
				await expect(panel.locator('.lp-import-review')).toContainText(
					'144'
				);
				await panel
					.getByRole('button', { name: words.add, exact: true })
					.click();
				await page
					.getByRole('button', { name: words.saveProject })
					.click();
				await expect(page.locator('.lp-save-state')).toContainText(
					words.savedState,
					{ timeout: 120_000 }
				);

				// Reopen from the server: the drawing-derived roof and the source
				// declarations it was measured from survive the round trip.
				await page.reload({ waitUntil: 'networkidle' });
				await expect(page.locator('#lp-design')).toContainText(
					'Calibrated drawing roof',
					{ timeout: 120_000 }
				);
				// The roof carries the calibrated source: select it, then open
				// that source's properties and read the stored calibration back.
				await page
					.locator('.lp-object-tree')
					.getByRole('button', {
						name: 'Calibrated drawing roof',
						exact: true,
					})
					.click();
				await page
					.getByRole('button', {
						name: words.sourceProperties,
						exact: true,
					})
					.click();
				const properties = page.locator('.lp-geometry-form');
				await expect(properties).toContainText(
					'Synthetic calibration fixture; not a survey',
					{ timeout: 15_000 }
				);
				await expect(
					properties.locator('[name="precision"]')
				).toHaveValue(num(lang, '0.05'));

				// Leave the instance as it was found.
				await page.goto(instance().url + words.configurator, {
					waitUntil: 'networkidle',
				});
				const row = page.locator('.lp-project-entry', {
					hasText: title,
				});
				await row.locator('.lp-project-delete').click();
				await page
					.getByRole('button', {
						name: words.deleteProject,
						exact: true,
					})
					.click();
				await expect(row).toHaveCount(0, { timeout: 60_000 });
			});
		}
	}
});
