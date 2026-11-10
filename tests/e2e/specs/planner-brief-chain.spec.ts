/**
 * The staged project brief's consumer chain (state-matrix family
 * project-brief, previously deferred to CU): the installer entry stages the
 * note, the configurator reads it back verbatim, the customer can edit and
 * re-stage it, URL-carried sizing hints stay proposals until one explicit
 * confirmation, and the staged brief survives refresh and language switch.
 *
 * English and German: every word the chain reads is the page's own, from the
 * shipped German catalog (no new copy). The language-switch test stays
 * English-rooted - it exercises the switch itself.
 */
/**
 * External dependencies
 */
import { expect, test, type Page } from '@playwright/test';

/**
 * Internal dependencies
 */
import { seedConsentCookies } from '../lib/consent';
import { instance, wp } from '../lib/instance';

type Lang = 'en' | 'de';

const NOTE = '8 kWp roof with battery, Munich, south-facing';

/** The chain's own words, each language's page as it ships. */
const WORDS = {
	en: {
		entry: '/for-installer/',
		configurator: '/solution-configurator/',
		noteLabel: 'Your project note',
		notUsed: 'This note is not used in the calculation.',
		save: 'Save',
		saved: 'Project note saved.',
		carried: 'Carried over',
		confirmed: 'Confirmed',
		threePhase: 'Three-phase',
		notNeeded: 'Not needed',
		create: 'Create project',
		quickStart: 'Quick start: plan in one screen',
		pvSize: 'PV array size',
		annual: 'Annual electricity use',
		postcode: 'Postcode or town',
		carryFailed: 'The project note could not be carried over.',
		useValues: 'Use these values',
		newProject: 'New project',
		saveProject: 'Save project',
		savedState: 'Saved',
		useSaved: 'Use saved revision',
		keptOpen: 'Open changes have been kept alongside the saved revision.',
		projects: 'Projects',
	},
	de: {
		entry: '/de/fuer-installateur/',
		configurator: '/de/loesungskonfigurator/',
		noteLabel: 'Ihre Projektnotiz',
		notUsed: 'Diese Notiz fließt nicht in die Berechnung ein.',
		save: 'Speichern',
		saved: 'Projektnotiz gespeichert.',
		carried: 'Übernommen',
		confirmed: 'Bestätigt',
		threePhase: 'Dreiphasig',
		notNeeded: 'Nicht benötigt',
		create: 'Projekt anlegen',
		quickStart: 'Schnellstart: Planen auf einem Bildschirm',
		pvSize: 'Größe der PV-Anlage',
		annual: 'Jährlicher Stromverbrauch',
		postcode: 'Postleitzahl oder Ort',
		carryFailed: 'Die Projektnotiz konnte nicht übernommen werden.',
		useValues: 'Angaben übernehmen',
		newProject: 'Neues Projekt',
		saveProject: 'Projekt speichern',
		savedState: 'Gespeichert',
		useSaved: 'Gespeicherte Version verwenden',
		keptOpen:
			'Die offenen Änderungen und die gespeicherte Version sind erhalten geblieben.',
		projects: 'Projekte',
	},
} as const;

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

/** Stages a brief from the language's installer entry and returns its id from
 * the configurator URL (the URL never carries customer text). */
async function stageBrief(
	page: Page,
	lang: Lang,
	note: string
): Promise<string> {
	const words = WORDS[lang];
	await page.goto(instance().url + words.entry);
	const field = page.locator('#lki-hero-query');
	await expect(field).toBeVisible();
	await field.fill(note);
	await field.press('Enter');
	await expect(page).toHaveURL(
		new RegExp(`${words.configurator}\\?.*brief=[a-f0-9]{32}`),
		{ timeout: 30_000 }
	);
	const url = new URL(page.url());
	return url.searchParams.get('brief')!;
}

for (const lang of ['en', 'de'] as const) {
	const words = WORDS[lang];

	test(`${lang}: the staged note reads back verbatim, stays out of sizing and re-stages`, async ({
		page,
	}) => {
		await stageBrief(page, lang, NOTE);

		// Readback: the customer's own text arrives unedited, and the panel
		// says plainly that the note is not a calculation input.
		const note = page.getByRole('textbox', { name: words.noteLabel });
		await expect(note).toHaveValue(NOTE);
		await expect(page.locator('.lp-project-brief-start')).toContainText(
			words.notUsed
		);

		// Editing and saving re-stages the note; the acknowledgement is a
		// live status, not a page reload.
		const edited = NOTE + ', EV charging from 2027';
		await note.fill(edited);
		await page
			.getByRole('button', { name: words.save, exact: true })
			.click();
		await expect(
			page.locator('.lp-project-brief-start [role="status"]')
		).toContainText(words.saved);

		// The scope boundary: without URL hints there is nothing to confirm,
		// so the single confirmation gesture stays absent.
		await expect(
			page.getByRole('button', { name: words.useValues })
		).toHaveCount(0);
	});

	test(`${lang}: URL sizing hints stay proposals until the single confirmation`, async ({
		page,
	}) => {
		const briefId = await stageBrief(page, lang, NOTE);
		await page.goto(
			instance().url +
				`${words.configurator}?brief=${briefId}&plz=81671&annual_kwh=8000&pv_kwp=10&phase=3&backup=none`
		);

		// Every carried value shows as carried over - proposals, not inputs.
		await expect(page.getByText(`81671 (${words.carried})`)).toBeVisible();
		await expect(
			page.getByText(`8000 kWh (${words.carried})`)
		).toBeVisible();
		await expect(page.getByText(`10 kWp (${words.carried})`)).toBeVisible();
		await expect(
			page.getByText(`${words.threePhase} (${words.carried})`)
		).toBeVisible();
		await expect(
			page.getByText(`${words.notNeeded} (${words.carried})`)
		).toBeVisible();

		// One gesture turns all of them into confirmed inputs at once.
		await page.getByRole('button', { name: words.useValues }).click();
		await expect(
			page.getByText(`81671 (${words.confirmed})`)
		).toBeVisible();
		await expect(
			page.getByText(`${words.threePhase} (${words.confirmed})`)
		).toBeVisible();
		await expect(
			page.getByRole('button', { name: words.useValues })
		).toHaveCount(0);
	});

	test(`${lang}: the note never sizes the project`, async ({ page }) => {
		await stageBrief(
			page,
			lang,
			'Please quote 99 kWp and 45000 kWh for our workshop in Munich'
		);

		// The note is the customer's own text; creating the project from it
		// leaves every sizing input at its default - the numbers in the note
		// are demands to answer, not inputs to consume.
		await page.getByRole('button', { name: words.create }).click();
		await expect(page).toHaveURL(/project=/, { timeout: 60_000 });
		await page.getByRole('button', { name: words.quickStart }).click();
		await expect(page.getByLabel(words.pvSize)).toHaveValue('10');
		await expect(page.getByLabel(words.annual)).toHaveValue('5000');
		await expect(page.getByLabel(words.postcode)).toHaveValue('');
	});

	test(`${lang}: a failed note save keeps the text and retries on its own`, async ({
		page,
	}) => {
		await stageBrief(page, lang, NOTE);
		const note = page.getByRole('textbox', { name: words.noteLabel });
		const edited = NOTE + ', EV charging from 2027';
		await note.fill(edited);

		// The staging endpoint fails: the panel says so, keeps the
		// customer's text untouched and never claims success.
		await page.route('**/rpc/sources/project-brief/stage', (route) =>
			route.abort()
		);
		await page
			.getByRole('button', { name: words.save, exact: true })
			.click();
		await expect(
			page.locator('.lp-project-brief-start .lp-notice')
		).toContainText(words.carryFailed);
		await expect(note).toHaveValue(edited);

		// The retry is note-only: the same gesture stages the kept text once
		// the endpoint answers again.
		await page.unroute('**/rpc/sources/project-brief/stage');
		await page
			.getByRole('button', { name: words.save, exact: true })
			.click();
		await expect(
			page.locator('.lp-project-brief-start [role="status"]')
		).toContainText(words.saved);
	});

	test(`${lang}: two projects keep revisions apart and a concurrent save conflicts visibly`, async ({
		context,
	}) => {
		const create = async (title: string) => {
			const p = await context.newPage();
			await p.goto(instance().url + words.configurator);
			await p
				.getByRole('button', { name: words.newProject })
				.first()
				.click();
			await p.locator('input[maxlength="256"]').first().fill(title);
			await p.getByRole('button', { name: words.create }).click();
			await expect(p).toHaveURL(/project=/, { timeout: 60_000 });
			return p;
		};

		// Two projects coexist for one customer session.
		const first = await create('Revision conflict e2e');
		const second = await create('Second project in parallel');
		await expect(second.locator('body')).toContainText('Second project');
		await second.close();

		// The same project opened in a second tab saves a new revision
		// first.
		const other = await context.newPage();
		await other.goto(first.url());
		const address = other.locator('#lp-site input').nth(0);
		await address.fill('Triftstrasse 15');
		await other.getByRole('button', { name: words.saveProject }).click();
		await expect(other.locator('.lp-save-state')).toContainText(
			words.savedState,
			{ timeout: 30_000 }
		);

		// The stale tab edits the same field and saves into a conflict: the
		// revision it knew is gone, its change is kept alongside it.
		const stale = first.locator('#lp-site input').nth(0);
		await stale.fill('Triftstrasse 25');
		await first.getByRole('button', { name: words.saveProject }).click();
		await expect(
			first.getByText(words.keptOpen, { exact: true })
		).toBeVisible({ timeout: 30_000 });

		// Returning to the saved revision is one explicit gesture.
		await first.getByRole('button', { name: words.useSaved }).click();
		await expect(
			first.getByText(words.keptOpen, { exact: true })
		).toBeHidden({ timeout: 30_000 });
		await expect(stale).toHaveValue('Triftstrasse 15');
		await other.close();
	});

	test(`${lang}: a guest project transfers to the account that signs in`, async ({
		page,
	}) => {
		// An approved account exists to receive the guest's project.
		const stamp = `${Date.now()}`.slice(-9);
		const login = `e2e-brief-claim-${stamp}`;
		const password = 'e2e-Account-2026!';
		const userId = wp([
			'user',
			'create',
			login,
			`${login}@example.test`,
			'--role=customer',
			`--user_pass=${password}`,
			'--porcelain',
		]).trim();
		if (!/^\d+$/.test(userId)) {
			throw new Error(`user create failed: ${userId}`);
		}
		wp([
			'user',
			'meta',
			'update',
			userId,
			'linker_approval_status',
			'approved',
		]);

		// The guest plans a project of their own.
		await page.goto(instance().url + words.configurator);
		await page
			.getByRole('button', { name: words.newProject })
			.first()
			.click();
		await page
			.locator('input[maxlength="256"]')
			.first()
			.fill('Guest to claim');
		await page.getByRole('button', { name: words.create }).click();
		await expect(page).toHaveURL(/project=/, { timeout: 60_000 });
		const projectUrl = page.url();

		// The identity switch: signing in inside the same browser session
		// hands every guest project to that account (session claim, spec
		// 548).
		await page.goto(instance().url + '/my-account/');
		await page.fill('#username', login);
		await page.fill('#password', password);
		await page.locator('button[name="login"]').focus();
		await page.keyboard.press('Enter');
		await page.waitForLoadState('load');
		await expect(page.locator('a[href*="action=logout"]')).not.toHaveCount(
			0,
			{ timeout: 30_000 }
		);

		// The claimed project stays reachable under the account, and the
		// projects screen lists it there.
		await page.goto(projectUrl);
		await expect(page.locator('.lp-project-bar')).toContainText(
			'Guest to claim',
			{ timeout: 60_000 }
		);
		await page
			.locator('.lp-project-bar button', { hasText: words.projects })
			.click();
		await expect(page.locator('body')).toContainText('Guest to claim', {
			timeout: 30_000,
		});
	});
}

test('the staged brief survives refresh and the language switch (English root)', async ({
	page,
}) => {
	const briefId = await stageBrief(page, 'en', NOTE);
	const edited = NOTE + ', EV charging from 2027';
	await page.getByRole('textbox', { name: WORDS.en.noteLabel }).fill(edited);
	await page
		.getByRole('button', { name: WORDS.en.save, exact: true })
		.click();
	await expect(
		page.locator('.lp-project-brief-start [role="status"]')
	).toContainText(WORDS.en.saved);

	// A cold reload re-reads the staged source by its id: the edited note,
	// not the original entry text, comes back.
	await page.reload();
	await expect(
		page.getByRole('textbox', { name: WORDS.en.noteLabel })
	).toHaveValue(edited);

	// The language switch carries the same brief id to the German
	// configurator; customer text and the entry link follow.
	await page.getByRole('link', { name: 'DE', exact: true }).click();
	await expect(page).toHaveURL(
		/de\/loesungskonfigurator\/\?.*brief=[a-f0-9]{32}/,
		{ timeout: 30_000 }
	);
	const germanNote = page.locator('.lp-project-brief-start textarea');
	await expect(germanNote).toHaveValue(edited);
	await expect(
		page.locator('.lp-project-brief-start a', {
			hasText: 'Zurück zur Eingabe',
		})
	).toHaveAttribute('href', /\/de\/fuer-installateur\/$/);
});
