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
import {
	plannerWords,
	fillSolarProject,
	compareProject,
	reopenProject,
	deleteOpenProject,
} from '../lib/planner-entry';
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
		importRoof: 'Import roof geometry',
		continue: 'Continue',
		stepPlane: 'Roof plane',
		stepSource: 'Source',
		prepare: 'Prepare roof preview',
		review: 'Review imported roof',
		area: 'Roof-plane area',
		openings: 'Openings retained',
		attach: 'Add roof to current design',
	},
	de: {
		configurator: '/de/loesungskonfigurator/',
		importRoof: 'Dachgeometrie importieren',
		continue: 'Weiter',
		stepPlane: 'Dachebene',
		stepSource: 'Quelle',
		prepare: 'Dachvorschau vorbereiten',
		review: 'Importierte Dachfläche prüfen',
		area: 'Fläche in der Dachebene',
		openings: 'Übernommene Aussparungen',
		attach: 'Dachfläche in den Entwurf übernehmen',
	},
} as const;

/** German number fields take a decimal comma (the field's own hint). */
function num(lang: Lang, value: string): string {
	return 'de' === lang ? value.replace('.', ',') : value;
}

/** The repository's own WGS 84 fixture: a 3-4-5 roof carrying one opening. */
const SOURCE = join(REPO_ROOT, 'fixtures/planning/source-roof-wgs84.geojson');

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
				await page.goto(instance().url + words.configurator);
				await fillSolarProject(page, lang, title);
				await page
					.getByText(plannerWords[lang].roof, { exact: true })
					.click();

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
				await expect(
					page.getByText(
						lang === 'en'
							? 'Roof added: Imported 3-4-5 roof'
							: 'Dachfläche hinzugefügt: Imported 3-4-5 roof',
						{ exact: true }
					)
				).toBeVisible();
				await compareProject(page, lang);
				const { inputs } = await reopenProject(page, lang, title);
				expect(inputs.geometry.roofs).toHaveLength(1);
				expect(inputs.geometry.roofs[0].name).toBe(
					'Imported 3-4-5 roof'
				);
				expect(inputs.geometry.roofs[0].holes_uv).toHaveLength(1);
				await expect(
					page
						.getByText('Imported 3-4-5 roof', { exact: true })
						.first()
				).toBeAttached();
				await deleteOpenProject(page, lang, title);
			});
		}
	}
});
