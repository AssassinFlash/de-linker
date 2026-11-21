import { join } from 'node:path';

import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { seedConsentCookies } from '../lib/consent';
import { REPO_ROOT } from '../lib/instance';
import {
	startSolarProject,
	removeSiteProject,
	type SiteLanguage as Lang,
} from '../lib/configurator-site';

test.setTimeout(240_000);

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

/** The wizard's own words, each language's page as it ships. */
const WORDS = {
	en: {
		useLayout: 'Use this layout',
		importRoof: 'Import roof geometry',
		roofFile: 'Roof file',
		stepPlane: 'Roof plane',
		continue: 'Continue',
		stepSource: 'Source',
		prepare: 'Prepare roof preview',
		review: 'Review imported roof',
		area: 'Roof-plane area',
		openings: 'Openings retained',
		attach: 'Add roof to current design',
		saved: 'The roof import is included in the saved project.',
	},
	de: {
		useLayout: 'Belegung übernehmen',
		importRoof: 'Dachgeometrie importieren',
		roofFile: 'Dachdatei',
		stepPlane: 'Dachebene',
		continue: 'Weiter',
		stepSource: 'Quelle',
		prepare: 'Dachvorschau vorbereiten',
		review: 'Importierte Dachfläche prüfen',
		area: 'Fläche in der Dachebene',
		openings: 'Übernommene Aussparungen',
		attach: 'Dachfläche in den Entwurf übernehmen',
		saved: 'Der Dachimport ist im gespeicherten Projekt enthalten.',
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
	const panel = page.locator('[data-linker-planner]');
	const form = panel
		.locator('form')
		.filter({ has: page.getByLabel(words.roofFile, { exact: true }) });
	await expect(panel).toBeVisible();

	await form
		.getByLabel(words.roofFile, { exact: true })
		.setInputFiles(SOURCE);
	await expect(
		form.getByText('source-roof-wgs84.geojson', { exact: true })
	).toBeVisible();
	await form.locator('[name="roof"]').fill('Imported 3-4-5 roof');
	await form
		.getByRole('button', { name: words.continue, exact: true })
		.click();

	// Step 2 - the plane the customer measured. No default is supplied, so
	// the empty field is a required-input state, not a zero.
	await expect(
		panel.getByRole('heading', { name: words.stepPlane, exact: true })
	).toBeVisible();
	await form.locator('[name="pitch"]').fill('91');
	await form.locator('[name="bearing"]').fill(num(lang, '180'));
	await form.locator('[name="height"]').fill(num(lang, '5'));
	await form
		.locator('[name="basis"]')
		.fill('Synthetic 3-4-5 fixture; not a survey');
	await form
		.getByRole('button', { name: words.continue, exact: true })
		.click();

	await expect(form.locator('[name="pitch"]')).toHaveAttribute(
		'aria-invalid',
		'true'
	);
	await form.locator('[name="pitch"]').fill(num(lang, '36.87'));
	await form
		.getByRole('button', { name: words.continue, exact: true })
		.click();

	// Step 3 - the source declaration and the right to retain the original.
	await expect(
		panel.getByRole('heading', { name: words.stepSource, exact: true })
	).toBeVisible();
	await form.locator('[name="source"]').fill('Own fixture file');
	await form
		.locator('[name="rights"]')
		.fill('Own synthetic fixture; retaining and deriving is permitted');
	await panel.locator('select[name="export"]').selectOption('permitted');
	await form.locator('[name="retention"]').check();
	await panel
		.getByRole('button', { name: words.prepare, exact: true })
		.click();
	await expect(
		panel.getByRole('heading', { name: words.review, exact: true })
	).toBeVisible({
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
				await startSolarProject(page, lang, title);

				const panel = await fillWizard(page, lang);

				await expect(
					panel.getByText(words.area, { exact: true })
				).toBeVisible();
				await expect(
					panel
						.getByText(words.openings, { exact: true })
						.locator('..')
						.locator('dd')
				).toHaveText('1');
				const revised = page.waitForResponse(
					(r) =>
						new URL(r.url()).pathname.endsWith(
							'/projects/revise'
						) &&
						r.request().postDataJSON()?.inputs?.geometry?.roofs
							?.length === 1
				);
				await panel
					.getByRole('button', { name: words.attach, exact: true })
					.click();
				expect((await revised).ok()).toBe(true);
				await expect(
					panel.getByText(words.saved, { exact: true })
				).toBeVisible();

				const reopened = await page.context().newPage();
				await reopened.setViewportSize({
					width,
					height: width === 390 ? 844 : 900,
				});
				const read = reopened.waitForRequest(
					(r) =>
						new URL(r.url()).pathname.endsWith('/projects/read') &&
						r.method() === 'POST'
				);
				await reopened.goto(page.url(), {
					waitUntil: 'domcontentloaded',
				});
				const response = await reopened.request.fetch(await read);
				expect(response.ok()).toBe(true);
				const saved = await response.json();
				expect(saved.title).toBe(title);
				expect(saved.inputs.geometry.roofs).toHaveLength(1);
				expect(saved.inputs.geometry.roofs[0].holes_uv).toHaveLength(1);
				await reopened
					.getByRole('button', { name: words.useLayout, exact: true })
					.click();
				const outline = reopened.locator(
					'.sc-roof-preview path[fill-rule="evenodd"]'
				);
				await expect(outline).toBeVisible();
				expect(
					(await outline.getAttribute('d'))?.match(/M/g)
				).toHaveLength(2);
				await outline.scrollIntoViewIfNeeded();
				await reopened.screenshot({
					path: test.info().outputPath('saved-roof.png'),
					animations: 'disabled',
				});

				await reopened.close();
				await removeSiteProject(page, lang, title);
			});
		}
	}
});
