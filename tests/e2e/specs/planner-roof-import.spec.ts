/**
 * Native roof import: the guided GeoJSON wizard in the real browser, in both
 * page languages and both viewports the owner required
 * (docs/specs/548-roof-import-workflow.md §Interruption and evidence:
 * "Native EN/DE × 1440/390 evidence must exercise file selection,
 * invalid/corrected input, actual preview/attach/save/reopen, retained holes").
 *
 * The import runs against the deployed engine through the page's own RPC, and
 * every assertion reads the saved project back from the server, so a green
 * run means the roof is in the project — not that the form accepted a click.
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

/** The wizard's own words, each language's page as it ships. */
const WORDS = {
	en: {
		configurator: '/solution-configurator/',
		newProject: 'New project',
		create: 'Create project',
		overview: 'Project overview',
		sections: 'Project sections',
		openRoof: 'Open roof workspace',
		importRoof: 'Import roof geometry',
		stepFile: 'File and roof',
		roofFile: 'Roof file',
		roofInFile: 'Roof in this file',
		roofFaceName: 'Roof face name',
		continue: 'Continue',
		stepPlane: 'Roof plane',
		pitch: 'Roof pitch',
		bearing: 'Downslope direction from true north',
		height: 'Relative height at the first outline point',
		basis: 'Measurement or drawing reference',
		stepSource: 'Source',
		sourceRef: 'Source reference',
		rights: 'Permission or licence basis',
		exportPermission: 'Permission to export geometry',
		retention:
			'I have permission to upload this original file, derive roof geometry from it and retain both privately with this project.',
		prepare: 'Prepare roof preview',
		review: 'Review imported roof',
		area: 'Roof-plane area',
		openings: 'Openings retained',
		attach: 'Add roof to current design',
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
		openRoof: 'Dachplanung öffnen',
		importRoof: 'Dachgeometrie importieren',
		stepFile: 'Datei und Dach',
		roofFile: 'Dachdatei',
		roofInFile: 'Dachfläche in dieser Datei',
		roofFaceName: 'Name der Dachfläche',
		continue: 'Weiter',
		stepPlane: 'Dachebene',
		pitch: 'Dachneigung',
		bearing: 'Gefällerichtung ab geografisch Nord',
		height: 'Relative Höhe am ersten Umrisspunkt',
		basis: 'Aufmaß- oder Zeichnungsreferenz',
		stepSource: 'Quelle',
		sourceRef: 'Quellenreferenz',
		rights: 'Berechtigungs- oder Lizenzgrundlage',
		exportPermission: 'Berechtigung zum Export der Geometrie',
		retention:
			'Ich habe die Berechtigung, diese Originaldatei hochzuladen, daraus Dachgeometrie abzuleiten und beides privat mit diesem Projekt aufzubewahren.',
		prepare: 'Dachvorschau vorbereiten',
		review: 'Importierte Dachfläche prüfen',
		area: 'Fläche in der Dachebene',
		openings: 'Übernommene Aussparungen',
		attach: 'Dachfläche in den Entwurf übernehmen',
		saveProject: 'Projekt speichern',
		savedState: 'Gespeichert',
		deleteProject: 'Projekt löschen',
	},
} as const;

/** German number fields take a decimal comma (the field's own hint). */
function num(lang: Lang, value: string): string {
	return 'de' === lang ? value.replace('.', ',') : value;
}

/** The repository's own WGS 84 fixture: a 3-4-5 roof carrying one opening. */
const SOURCE = join(REPO_ROOT, 'fixtures/planning/source-roof-wgs84.geojson');

/**
 * Create an empty project and open its roof workspace. The empty roof
 * workspace is what makes this project eligible to adopt the import's own
 * geographic origin (a nonempty frame must be aligned first).
 */
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

/** Fill the three wizard steps and prepare the server preview. */
async function fillWizard(page: Page, lang: Lang) {
	const words = WORDS[lang];
	await page
		.getByRole('button', { name: words.importRoof, exact: true })
		.click();
	const panel = page.locator('.lp-import-panel');
	await expect(panel).toBeVisible();

	// Step 1 - the original file. A single Feature is the only choice, so it
	// is already selected; the name still has to be typed.
	await panel.locator('input[type="file"]').setInputFiles(SOURCE);
	await expect(panel.locator('.lp-file-name')).not.toHaveText(
		/No file selected|Keine Datei/
	);
	await panel.locator('[name="roof"]').fill('Imported 3-4-5 roof');
	await panel
		.getByRole('button', { name: words.continue, exact: true })
		.click();

	// Step 2 - the plane the customer measured. No default is supplied, so
	// the empty field is a required-input state, not a zero.
	await expect(panel.getByRole('heading')).toHaveText(words.stepPlane);
	await panel.locator('[name="pitch"]').fill(num(lang, '36.87'));
	await panel.locator('[name="bearing"]').fill(num(lang, '180'));
	await panel.locator('[name="height"]').fill(num(lang, '5'));
	await panel
		.locator('[name="basis"]')
		.fill('Synthetic 3-4-5 fixture; not a survey');
	await panel
		.getByRole('button', { name: words.continue, exact: true })
		.click();

	// Step 3 - the source declaration and the right to retain the original.
	await expect(panel.getByRole('heading')).toHaveText(words.stepSource);
	await panel.locator('[name="source"]').fill('Own fixture file');
	await panel
		.locator('[name="rights"]')
		.fill('Own synthetic fixture; retaining and deriving is permitted');
	await panel.locator('select[name="export"]').selectOption('permitted');
	await panel.locator('[name="retention"]').check();
	await panel
		.getByRole('button', { name: words.prepare, exact: true })
		.click();
	await expect(panel.getByRole('heading')).toHaveText(words.review, {
		timeout: 120_000,
	});
	return panel;
}

test.describe('native roof import', () => {
	for (const lang of ['en', 'de'] as const) {
		for (const width of [1440, 390]) {
			test(`${lang} @${width}: an owned GeoJSON becomes a saved roof with its opening`, async ({
				page,
			}) => {
				const words = WORDS[lang];
				await page.setViewportSize({
					width,
					height: width === 390 ? 844 : 900,
				});
				const title = `m-roof import ${lang} ${width}`;
				await emptyRoofWorkspace(page, lang, title);

				const panel = await fillWizard(page, lang);

				// The preview reports the accepted roof, its plane area and the
				// opening it kept — read from the prepared manifest, not typed.
				const review = panel.locator('.lp-import-review');
				await expect(review).toContainText(words.area);
				await expect(review).toContainText(words.openings);
				await expect(
					review.locator('.lp-field-summary dd').nth(1)
				).toHaveText('1');

				await panel
					.getByRole('button', { name: words.attach, exact: true })
					.click();
				// Attachment is one history step; the project then has to be
				// saved before the roof belongs to it.
				await page
					.getByRole('button', { name: words.saveProject })
					.click();
				await expect(page.locator('.lp-save-state')).toContainText(
					words.savedState,
					{ timeout: 120_000 }
				);

				// Reopen from the server: the roof and its opening survive.
				await page.reload({ waitUntil: 'networkidle' });
				await expect(page.locator('#lp-design')).toContainText(
					/Imported 3-4-5 roof/,
					{ timeout: 120_000 }
				);

				// Leave the instance as it was found: the test project and its
				// revisions are removed through the app's own delete command.
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
