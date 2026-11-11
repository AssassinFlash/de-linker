/**
 * Dated national rule readings (docs/specs/548-workbench-application.md
 * "Dated national and operator rule readings").
 *
 * The site workspace's rule form is the only write surface for
 * `country_rule_inputs`: it offers the three evidence-backed bases, keeps a
 * rule whose country is not the project's visible but without a result, and
 * refuses an impossible date instead of dropping the entry. The saved revision
 * reads back through the gateway and the engine unchanged.
 *
 * Asserted here:
 * - the form does not exist before declared grid evidence (a reading needs a
 *   declared connection to be about);
 * - the three bases, the country mismatch notice, the EEG § 9(2) declarations,
 *   the invalid-date alert and the offered verified source date;
 * - the write contract on the engine's own planner route: `input_contract`
 *   required for these inputs, positive declared power, a real calendar date,
 *   one reading per revision, and an outside-version date stored as entered
 *   (it is a rule outcome, not a write error).
 *
 * Not asserted here: the rule *result* (`country_assessment.rule_review` →
 * `CountryRuleResult`) renders only inside the equipment qualification result,
 * which this spec does not drive. The run used to be blocked on this instance —
 * the manifest reported `ready.engineering: false` for every product, so
 * `/planning/runs/equipment` answered `409 product_evidence_changed` for a real
 * current inverter selection. That was a stale preparation receipt, not a code
 * defect: after the engineering receipt was re-acknowledged against the
 * engine's actually loaded source, the same call succeeds with `rule_review` in
 * its result (`docs/acceptance/2026-11-11/review-readiness-fix.md`). The
 * outcome contract stays covered at its own layer by
 * `services/engine/tests/planning/test_country_rules.py`.
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { plannerPost, type PlannerPrincipal } from '../lib/engine';
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

type Lang = 'en' | 'de';

/** Each language's own words, from the shipped linker-tools catalog. */
const WORDS = {
	en: {
		configurator: '/solution-configurator/',
		newProject: 'New project',
		createProject: 'Create project',
		saveProject: 'Save project',
		saved: 'Saved',
		country: 'Country',
		location: 'Address or location reference',
		latitude: 'Latitude',
		longitude: 'Longitude',
		gridHeading: 'Grid connection information',
		addGrid: 'Add grid connection information',
		dso: 'Responsible distribution system operator (DSO)',
		dsoUrl: 'DSO source URL',
		voltage: 'Voltage level at the grid connection point',
		tabTitle: 'Document title',
		tabUrl: 'Requirements source URL',
		tabEdition: 'Edition or version',
		ruleHeading: 'National rule inputs',
		basis: 'Rule scope and power basis',
		noRule: 'Do not assess a national rule',
		fr: 'France: generation-unit Pmax',
		nl: 'Netherlands: grid-feeding storage unit',
		de: 'Germany: EEG solar installed power',
		at: 'Austria: TOR Erzeuger Typ A maximum capacity',
		mismatch:
			"The selected rule does not match this project's country. No rule result will be added until they match.",
		frVoltage: 'Voltage at the grid connection point',
		deControl:
			'Is the smart meter or control equipment not yet installed, or is the first successful operator control test still pending?',
		deRemuneration: 'EEG remuneration for this installation',
		dePlugIn: 'Does the complete plug-in solar exception apply?',
		deSource: /German source text checked November 4, 2026/,
		dateLabel: 'Date for this rule reading (YYYY-MM-DD)',
		powerLabel: 'Declared power',
		useSource: 'Use the source checked on November 4, 2026',
		invalidDate:
			'Enter a valid date and positive numbers, or leave them empty. Your entries remain available for correction.',
	},
	de: {
		configurator: '/de/loesungskonfigurator/',
		newProject: 'Neues Projekt',
		createProject: 'Projekt anlegen',
		saveProject: 'Projekt speichern',
		saved: 'Gespeichert',
		country: 'Land',
		location: 'Adresse oder Standortbezeichnung',
		latitude: 'Breitengrad',
		longitude: 'Längengrad',
		gridHeading: 'Angaben zum Netzanschluss',
		addGrid: 'Angaben zum Netzanschluss ergänzen',
		dso: 'Zuständiger Verteilnetzbetreiber (VNB)',
		dsoUrl: 'Quellen-URL zum Netzbetreiber',
		voltage: 'Spannungsebene am Netzanschlusspunkt',
		tabTitle: 'Dokumenttitel',
		tabUrl: 'Quellen-URL der Anschlussbedingungen',
		tabEdition: 'Ausgabe oder Version',
		ruleHeading: 'Eingaben zu Landesregeln',
		basis: 'Regelungsbereich und Leistungsbezug',
		noRule: 'Keine Landesregel prüfen',
		fr: 'Frankreich: Pmax der Erzeugungseinheit',
		nl: 'Niederlande: netzeinspeisende Speichereinheit',
		de: 'Deutschland: installierte PV-Leistung nach EEG',
		at: 'Österreich: Maximalkapazität nach TOR Erzeuger Typ A',
		mismatch:
			'Die ausgewählte Regel passt nicht zum Land dieses Projekts. Ein Regelergebnis wird erst ergänzt, wenn beides übereinstimmt.',
		frVoltage: 'Spannung am Netzanschlusspunkt',
		deControl:
			'Fehlt noch das intelligente Messsystem oder die Steuerungseinrichtung, oder steht die erste erfolgreiche Ansteuerungsprüfung durch den Netzbetreiber noch aus?',
		deRemuneration: 'EEG-Vergütungsform dieser Anlage',
		dePlugIn:
			'Sind alle Voraussetzungen für die Steckersolar-Ausnahme erfüllt?',
		deSource: /Deutscher Quellentext geprüft am 4\. November 2026/,
		dateLabel: 'Datum dieser Regelbetrachtung (JJJJ-MM-TT)',
		powerLabel: 'Angegebene Leistung',
		useSource: 'Am 4. November 2026 geprüften Quellenstand verwenden',
		invalidDate:
			'Geben Sie ein gültiges Datum und positive Zahlen ein oder lassen Sie die Felder leer. Ihre Eingaben bleiben zur Korrektur erhalten.',
	},
} as const;

/** German number fields take a decimal comma (the field's own hint). */
function num(lang: Lang, value: string): string {
	return 'de' === lang ? value.replace('.', ',') : value;
}

/** The section that owns one heading; the editor nests its forms this way. */
function section(page: Page, heading: string | RegExp): Locator {
	return page
		.getByRole('heading', {
			name: heading,
			exact: typeof heading === 'string',
		})
		.locator('xpath=ancestor::section[1]');
}

/** The rule form's controls: basis first, then the date and power fields. */
function ruleForm(page: Page, heading: string): Locator {
	return section(page, heading);
}

/**
 * Opens the configurator on a fresh project and returns its id. The editor
 * keeps polling while it is open, so navigation settles on the DOM plus the
 * first editor control rather than on network idleness.
 */
async function openProject(page: Page, lang: Lang, title: string) {
	const words = WORDS[lang];
	await page.goto(instance().url + words.configurator, {
		waitUntil: 'domcontentloaded',
	});
	await page.getByRole('button', { name: words.newProject }).first().click();
	await page.locator('input[maxlength="256"]').first().fill(title);
	await page.getByRole('button', { name: words.createProject }).click();
	await expect(page).toHaveURL(/project=/, { timeout: 60_000 });
	return new URL(page.url()).searchParams.get('project') ?? '';
}

for (const lang of ['en', 'de'] as const) {
	const words = WORDS[lang];

	test(`${lang}: the national rule form gates on grid evidence and saves one dated reading`, async ({
		page,
	}) => {
		test.setTimeout(180_000);
		const project = await openProject(
			page,
			lang,
			`Country rules e2e ${lang} ${Date.now()}`
		);

		const brief = page.locator('#lp-site');
		await brief.getByLabel(words.country).selectOption('DE');
		await brief.getByLabel(words.location).fill('Triftstrasse 5');
		await brief.getByLabel(words.latitude).fill(num(lang, '48.1689'));
		await brief.getByLabel(words.longitude).fill(num(lang, '11.5844'));

		// A rule reading without declared grid evidence has no project scope at
		// all, so the form does not exist until that evidence is entered.
		await expect(
			page.getByRole('heading', { name: words.ruleHeading, exact: true })
		).toHaveCount(0);

		await page.getByRole('button', { name: words.addGrid }).click();
		const grid = section(page, words.gridHeading);
		await grid.getByLabel(words.dso).fill('Netz Oranienburg');
		await grid
			.getByLabel(words.dsoUrl)
			.fill('https://www.netz-oranienburg.de/tab');
		await grid.getByLabel(words.voltage).selectOption('low');
		await grid.getByLabel(words.tabTitle).fill('TAB Niederspannung');
		await grid
			.getByLabel(words.tabUrl)
			.fill('https://www.netz-oranienburg.de/tab.pdf');
		await grid.getByLabel(words.tabEdition).fill('2026-01');

		const rule = ruleForm(page, words.ruleHeading);
		await expect(rule).toBeVisible();
		const basis = rule.locator('select').first();
		expect(await basis.locator('option').allInnerTexts()).toEqual([
			words.noRule,
			words.fr,
			words.nl,
			words.de,
			words.at,
		]);

		// A French reading on a German project stays visible as a project
		// declaration, but the engine adds no result for it.
		await basis.selectOption('fr_generation_pmax');
		await expect(rule.getByRole('status')).toHaveText(words.mismatch);
		await expect(rule.getByLabel(words.frVoltage)).toBeVisible();
		expect(await rule.locator('select').count()).toBe(2);

		await basis.selectOption('de_pv_installed');
		await expect(rule.getByRole('status')).toHaveCount(0);
		// The basis selector plus the three EEG § 9(2) declarations.
		expect(await rule.locator('select').count()).toBe(4);
		await expect(rule).toContainText(words.deControl);
		await expect(rule).toContainText(words.deRemuneration);
		await expect(rule).toContainText(words.dePlugIn);
		await expect(rule).toContainText(words.deSource);
		await expect(rule.getByLabel(words.frVoltage)).toHaveCount(0);

		// An impossible date is reported, and the entry stays for correction.
		const date = rule.getByLabel(words.dateLabel);
		await date.fill('2026-13-40');
		await expect(rule.getByRole('alert')).toHaveText(words.invalidDate);

		// The editor offers the basis's most recently verified source date.
		await rule.getByRole('button', { name: words.useSource }).click();
		await expect(date).toHaveValue('2026-11-04');
		await expect(rule.getByRole('alert')).toHaveCount(0);
		await rule.locator('input').nth(1).fill(num(lang, '120'));

		await page.getByRole('button', { name: words.saveProject }).click();
		await expect(page.locator('.lp-save-state')).toContainText(
			words.saved,
			{
				timeout: 90_000,
			}
		);

		// The saved revision reads back through the gateway and the engine: the
		// form is rebuilt from `country_rule_inputs`, not from local state.
		await page.goto(
			`${instance().url}${words.configurator}?project=${project}#lp-site`,
			{ waitUntil: 'domcontentloaded' }
		);
		const reopened = ruleForm(page, words.ruleHeading);
		await expect(reopened).toBeVisible({ timeout: 60_000 });
		await expect(reopened.locator('select').first()).toHaveValue(
			'de_pv_installed'
		);
		await expect(reopened.getByLabel(words.dateLabel)).toHaveValue(
			'2026-11-04'
		);
		await expect(reopened.locator('input').nth(1)).toHaveValue(
			num(lang, '120')
		);

		// A different basis starts from empty declarations and, on this German
		// project, is again a non-matching rule.
		await reopened
			.locator('select')
			.first()
			.selectOption('nl_storage_max_active');
		await expect(reopened.getByRole('status')).toHaveText(words.mismatch);
		await expect(reopened.getByLabel(words.dateLabel)).toHaveValue('');
	});
}

/**
 * The write contract the browser and the gateway share, asserted on the
 * engine's own planner route with the envelope the gateway sets. Refusals are
 * part of the contract, so each one keeps its status and its named code.
 */
test('the engine keeps one dated rule reading per revision and refuses an unscoped one', async () => {
	test.setTimeout(120_000);
	const principal: PlannerPrincipal = {
		kind: 'guest',
		subject: `countrye2e:${Date.now()}`,
	};
	const brief = {
		schema_version: 1,
		project_use: 'commercial',
		system_scope: 'new_pv_storage',
		site: {
			country_code: 'DE',
			location_label: 'Triftstrasse 5',
			latitude: 48.1689,
			longitude: 11.5844,
			coordinate_basis: 'user_entered',
			timezone: null,
		},
		annual_load: {
			kwh: 10000,
			basis: 'user_estimate',
			source_note: 'Customer estimate',
		},
		project_note: '',
	};
	const grid = {
		schema_version: 1,
		dso_name: 'Netz Oranienburg',
		dso_source_url: 'https://www.netz-oranienburg.de/tab',
		voltage_level: 'low',
		tab: {
			title: 'TAB Niederspannung',
			source_url: 'https://www.netz-oranienburg.de/tab.pdf',
			edition: '2026-01',
			date: null,
		},
	};
	const rule = (changes: Record<string, unknown> = {}) => ({
		schema_version: 1,
		basis: 'de_pv_installed',
		rule_date: '2020-01-01',
		power_kw: 120,
		connection_voltage_kv: null,
		de_before_control_test: true,
		de_remuneration: null,
		de_plug_in_exception: null,
		fr_enedis_full_self_consumption: null,
		...changes,
	});
	const create = (key: string, inputs: Record<string, unknown>) =>
		plannerPost<Record<string, unknown>>(
			'projects/create',
			{
				schema_version: 1,
				key,
				title: 'Country rules contract',
				input_contract: 'project_engineering_v10',
				inputs,
			},
			principal
		);

	// A reading is a declaration about a declared grid connection; without one
	// the project has no scope for it (GridConnection/CountryRuleInputs).
	const unscoped = await create('unscoped', {
		brief,
		country_rule_inputs: rule(),
	});
	expect(unscoped.status).toBe(422);
	expect(unscoped.body).toMatchObject({
		error: {
			code: 'invalid_input',
			fields: [{ path: ['body', 'inputs'], kind: 'value_error' }],
		},
	});

	// These inputs belong to the `project_engineering_v10` complete writer; an
	// older writer would drop them, so the engine refuses the write outright.
	const noContract = await plannerPost<Record<string, unknown>>(
		'projects/create',
		{
			schema_version: 1,
			key: 'no-contract',
			title: 'Country rules contract',
			inputs: {
				brief,
				grid_connection: grid,
				country_rule_inputs: rule(),
			},
		},
		principal
	);
	expect(noContract.status).toBe(422);
	expect(noContract.body).toMatchObject({
		error: { code: 'project_input_contract_required' },
	});

	// Declared power is a positive quantity, not a placeholder zero.
	const zero = await create('zero-power', {
		brief,
		grid_connection: grid,
		country_rule_inputs: rule({ power_kw: 0 }),
	});
	expect(zero.status).toBe(422);
	expect(zero.body).toMatchObject({
		error: {
			code: 'invalid_input',
			fields: [
				{ path: ['body', 'inputs', 'power_kw'], kind: 'greater_than' },
			],
		},
	});

	// A date that is not a calendar date is refused; it is never stored as text.
	const badDate = await create('bad-date', {
		brief,
		grid_connection: grid,
		country_rule_inputs: rule({ rule_date: '2020-13-01' }),
	});
	expect(badDate.status).toBe(422);
	expect(badDate.body).toMatchObject({
		error: {
			code: 'invalid_input',
			fields: [
				{ path: ['body', 'inputs', 'rule_date'], kind: 'value_error' },
			],
		},
	});

	// A date outside the documented version is a *rule outcome*, not a write
	// error: the declaration is stored as entered and evaluated later.
	const created = await create('outside-version', {
		brief,
		grid_connection: grid,
		country_rule_inputs: rule(),
	});
	expect(created.status).toBe(200);
	const projectId = String(created.body.id);
	expect(created.body.inputs).toMatchObject({
		country_rule_inputs: rule(),
	});

	const read = await plannerPost<Record<string, unknown>>(
		'projects/read',
		{ schema_version: 1, project_id: projectId },
		principal
	);
	expect(read.status).toBe(200);
	expect(read.body).toMatchObject({
		revision: 1,
		inputs: { country_rule_inputs: rule() },
	});

	// One reading per revision: a revise replaces it instead of accumulating.
	const revised = await plannerPost<Record<string, unknown>>(
		'projects/revise',
		{
			schema_version: 1,
			key: 'revise-to-nl',
			project_id: projectId,
			expected_revision: 1,
			input_contract: 'project_engineering_v10',
			inputs: {
				brief,
				grid_connection: grid,
				country_rule_inputs: rule({
					basis: 'nl_storage_max_active',
					rule_date: '2026-11-04',
				}),
			},
		},
		principal
	);
	expect(revised.status).toBe(200);
	expect(revised.body).toMatchObject({
		revision: 2,
		inputs: {
			country_rule_inputs: rule({
				basis: 'nl_storage_max_active',
				rule_date: '2026-11-04',
			}),
		},
	});

	const removed = await plannerPost<Record<string, unknown>>(
		'projects/delete',
		{
			schema_version: 1,
			key: 'cleanup',
			project_id: projectId,
			expected_revision: 2,
		},
		principal
	);
	expect(removed.status).toBe(200);
});
