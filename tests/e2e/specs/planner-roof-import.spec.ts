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
		home: '/',
		configurator: '/solution-configurator/',
		details: 'Enter project details',
		newProject: 'New project',
		solar: 'Continue with solar',
		roofChoice: 'Place modules on the roof',
		openRoof: 'Open roof layout',
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
		deleteProject: 'Delete project',
	},
	de: {
		home: '/de/',
		configurator: '/de/loesungskonfigurator/',
		details: 'Projektdaten eingeben',
		newProject: 'Neues Projekt',
		solar: 'Weiter zur PV-Anlage',
		roofChoice: 'Module auf dem Dach platzieren',
		openRoof: 'Dachbelegung öffnen',
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
		deleteProject: 'Projekt löschen',
	},
} as const;

/** German number fields take a decimal comma (the field's own hint). */
function num(lang: Lang, value: string): string {
	return 'de' === lang ? value.replace('.', ',') : value;
}

/** The repository's own WGS 84 fixture: a 3-4-5 roof carrying one opening. */
const SOURCE = join(REPO_ROOT, 'fixtures/planning/source-roof-wgs84.geojson');

async function emptyRoofWorkspace(page: Page, lang: Lang, title: string) {
	const words = WORDS[lang];
	await page.goto(instance().url + words.home);
	await page.locator('[data-linker-planner-entry="home-hero"] a').click();
	const workspace = page.locator('[data-linker-planner]');
	await workspace
		.getByRole('button', { name: words.details, exact: true })
		.click();
	const project = workspace.getByRole('form', {
		name: words.newProject,
		exact: true,
	});
	await project.locator('[name="project_title"]').fill(title);
	await project.locator('[name="country"]').selectOption('DE');
	await project
		.locator('[name="system_scope"]')
		.selectOption('new_pv_storage');
	await project
		.getByRole('button', { name: words.solar, exact: true })
		.click();
	await expect(page).toHaveURL(/[?&]project=[a-f0-9]{32}/, {
		timeout: 60_000,
	});
	await workspace
		.getByRole('button', { name: words.roofChoice, exact: true })
		.click();
	await workspace
		.getByRole('button', { name: words.openRoof, exact: true })
		.click();
}

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
				await emptyRoofWorkspace(page, lang, title);

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

				const read = page.waitForResponse((r) =>
					new URL(r.url()).pathname.endsWith('/projects/read')
				);
				await page.reload();
				const saved = await (await read).json();
				expect(saved.title).toBe(title);
				expect(saved.inputs.geometry.roofs).toHaveLength(1);
				expect(saved.inputs.geometry.roofs[0].holes_uv).toHaveLength(1);
				const outline = panel.locator(
					'.sc-roof-preview path[fill-rule="evenodd"]'
				);
				await expect(outline).toBeVisible();
				expect(
					(await outline.getAttribute('d'))?.match(/M/g)
				).toHaveLength(2);
				await outline.scrollIntoViewIfNeeded();
				await page.screenshot({
					path: test.info().outputPath('saved-roof.png'),
					animations: 'disabled',
				});

				await page.goto(
					instance().url + words.configurator + '?projects=1'
				);
				const row = page
					.getByRole('listitem')
					.filter({
						has: page.getByRole('heading', {
							name: title,
							exact: true,
						}),
					});
				await row
					.getByRole('button', {
						name: new RegExp(
							lang === 'en'
								? '^Delete project '
								: '^Projekt .* löschen$'
						),
					})
					.click();
				await row
					.getByRole('button', {
						name: words.deleteProject,
						exact: true,
					})
					.click();
				await expect(row).toHaveCount(0);
			});
		}
	}
});
