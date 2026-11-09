/**
 * The staged project brief's consumer chain (state-matrix family
 * project-brief, previously deferred to CU): the installer entry stages the
 * note, the configurator reads it back verbatim, the customer can edit and
 * re-stage it, URL-carried sizing hints stay proposals until one explicit
 * confirmation, and the staged brief survives refresh and language switch.
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

const NOTE = '8 kWp roof with battery, Munich, south-facing';

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

/** Stages a brief from the installer entry and returns its id from the
 * configurator URL (the URL never carries customer text). */
async function stageBrief(page: Page, note: string): Promise<string> {
	await page.goto(instance().url + '/for-installer/');
	const field = page.locator('#lki-hero-query');
	await expect(field).toBeVisible();
	await field.fill(note);
	await field.press('Enter');
	await expect(page).toHaveURL(
		/solution-configurator\/\?.*brief=[a-f0-9]{32}/,
		{ timeout: 30_000 }
	);
	const url = new URL(page.url());
	return url.searchParams.get('brief')!;
}

test('the staged note reads back verbatim, stays out of sizing and re-stages', async ({
	page,
}) => {
	await stageBrief(page, NOTE);

	// Readback: the customer's own text arrives unedited, and the panel says
	// plainly that the note is not a calculation input.
	const note = page.getByRole('textbox', { name: 'Your project note' });
	await expect(note).toHaveValue(NOTE);
	await expect(page.locator('.lp-project-brief-start')).toContainText(
		'This note is not used in the calculation.'
	);

	// Editing and saving re-stages the note; the acknowledgement is a live
	// status, not a page reload.
	const edited = NOTE + ', EV charging from 2027';
	await note.fill(edited);
	await page.getByRole('button', { name: 'Save', exact: true }).click();
	await expect(
		page.locator('.lp-project-brief-start [role="status"]')
	).toContainText('Project note saved.');

	// The scope boundary: without URL hints there is nothing to confirm, so
	// the single confirmation gesture stays absent.
	await expect(
		page.getByRole('button', { name: 'Use these values' })
	).toHaveCount(0);
});

test('URL sizing hints stay proposals until the single confirmation', async ({
	page,
}) => {
	const briefId = await stageBrief(page, NOTE);
	await page.goto(
		instance().url +
			`/solution-configurator/?brief=${briefId}&plz=81671&annual_kwh=8000&pv_kwp=10&phase=3&backup=none`
	);

	// Every carried value shows as Carried over - proposals, not inputs.
	await expect(page.getByText('81671 (Carried over)')).toBeVisible();
	await expect(page.getByText('8000 kWh (Carried over)')).toBeVisible();
	await expect(page.getByText('10 kWp (Carried over)')).toBeVisible();
	await expect(page.getByText('Three-phase (Carried over)')).toBeVisible();
	await expect(page.getByText('Not needed (Carried over)')).toBeVisible();

	// One gesture turns all of them into confirmed inputs at once.
	await page.getByRole('button', { name: 'Use these values' }).click();
	await expect(page.getByText('81671 (Confirmed)')).toBeVisible();
	await expect(page.getByText('Three-phase (Confirmed)')).toBeVisible();
	await expect(
		page.getByRole('button', { name: 'Use these values' })
	).toHaveCount(0);
});

test('the staged brief survives refresh and the language switch', async ({
	page,
}) => {
	const briefId = await stageBrief(page, NOTE);
	const edited = NOTE + ', EV charging from 2027';
	await page.getByRole('textbox', { name: 'Your project note' }).fill(edited);
	await page.getByRole('button', { name: 'Save', exact: true }).click();
	await expect(
		page.locator('.lp-project-brief-start [role="status"]')
	).toContainText('Project note saved.');

	// A cold reload re-reads the staged source by its id: the edited note,
	// not the original entry text, comes back.
	await page.reload();
	await expect(
		page.getByRole('textbox', { name: 'Your project note' })
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

test('the note never sizes the project', async ({ page }) => {
	await stageBrief(
		page,
		'Please quote 99 kWp and 45000 kWh for our workshop in Munich'
	);

	// The note is the customer's own text; creating the project from it
	// leaves every sizing input at its default - the numbers in the note are
	// demands to answer, not inputs to consume.
	await page.getByRole('button', { name: 'Create project' }).click();
	await expect(page).toHaveURL(/project=/, { timeout: 60_000 });
	await page
		.getByRole('button', { name: 'Quick start: plan in one screen' })
		.click();
	await expect(page.getByLabel('PV array size')).toHaveValue('10');
	await expect(page.getByLabel('Annual electricity use')).toHaveValue('5000');
	await expect(page.getByLabel('Postcode or town')).toHaveValue('');
});

test('a failed note save keeps the text and retries on its own', async ({
	page,
}) => {
	await stageBrief(page, NOTE);
	const note = page.getByRole('textbox', { name: 'Your project note' });
	const edited = NOTE + ', EV charging from 2027';
	await note.fill(edited);

	// The staging endpoint fails: the panel says so, keeps the customer's
	// text untouched and never claims success.
	await page.route('**/rpc/sources/project-brief/stage', (route) =>
		route.abort()
	);
	await page.getByRole('button', { name: 'Save', exact: true }).click();
	await expect(
		page.locator('.lp-project-brief-start .lp-notice')
	).toContainText('The project note could not be carried over.');
	await expect(note).toHaveValue(edited);

	// The retry is note-only: the same gesture stages the kept text once the
	// endpoint answers again.
	await page.unroute('**/rpc/sources/project-brief/stage');
	await page.getByRole('button', { name: 'Save', exact: true }).click();
	await expect(
		page.locator('.lp-project-brief-start [role="status"]')
	).toContainText('Project note saved.');
});
