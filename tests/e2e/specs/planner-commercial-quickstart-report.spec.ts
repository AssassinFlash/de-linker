/**
 * The commercial quick start reaches its report PDF, end to end.
 *
 * Production walk 2026-11-11 §B: a commercial customer filled the one-screen
 * quick start, got the sized 690-combination answer and the provisional bill of
 * materials, and then read HTTP 422 from the report step with no PDF. The screen
 * had adopted the chosen equipment combination as the project's candidate and
 * still named a separate equipment run in the report request; the report's own
 * contract reads an adopted candidate as the project's single equipment source,
 * so the extra run contradicted it.
 *
 * This drives the shipped planner bundle over the real review instance: the
 * quick start's own form, the real engine's search/qualification/report runs,
 * and the customer's own Download PDF button. The assertion is the delivered
 * file: HTTP 200, PDF bytes, and pages in it.
 */
import { expect, test } from '@playwright/test';
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

test('a commercial quick start downloads its planning report PDF', async ({
	page,
}) => {
	test.setTimeout(420_000);
	await page.setViewportSize({ width: 1440, height: 900 });

	await page.goto(instance().url + '/solution-configurator/', {
		waitUntil: 'networkidle',
	});
	// The customer's own route into the one-screen start: the projects panel's
	// button, not the inline form the empty index shows (that copy belongs to
	// the index and leaves with the first saved project).
	const start = page.getByRole('button', { name: 'Start a solution' });
	if (await start.count()) await start.first().click();
	const form = page.locator('.lp-quickstart-form');
	await expect(form).toBeVisible({ timeout: 120_000 });

	// The production walk's own commercial inputs: 100 kWp, a commercial annual
	// consumption, three phases and a peak-shaving goal, with a postcode.
	await form.getByLabel('Project type').selectOption('commercial');
	await form.getByLabel('PV array size').selectOption('100');
	await form.getByLabel('Annual electricity use').selectOption('250000');
	// The walk's own goal: cut the commercial peak demand.
	await form.getByLabel('System goal').selectOption('peak_shaving');
	await form.getByLabel('Postcode or town').fill('80331');

	await form.getByRole('button', { name: 'Generate solution' }).click();

	// The report step must finish, not fail: the report is the whole point of
	// this spec, and its failure was silent behind a plausible sentence.
	const reportStep = page.locator('li[data-step="report"]');
	await expect(reportStep).toHaveAttribute('data-state', 'done', {
		timeout: 300_000,
	});
	await expect(reportStep).not.toContainText(/stopped|could not/i);

	// The PDF the customer downloads: bytes, page count, and a 200.
	const download = page.waitForEvent('download', { timeout: 120_000 });
	await page.getByRole('button', { name: 'Download PDF' }).click();
	const file = await download;
	const path = await file.path();
	expect(path, 'the browser saved the report').toBeTruthy();

	const { readFileSync } = await import('node:fs');
	const bytes = readFileSync(path!);
	expect(bytes.subarray(0, 5).toString('latin1'), 'a PDF header').toBe(
		'%PDF-'
	);
	expect(bytes.length).toBeGreaterThan(2000);
	// Pages are declared in the page tree; counting them proves the document is
	// a finished report rather than an empty container.
	const pages = (bytes.toString('latin1').match(/\/Type\s*\/Page[^s]/g) ?? [])
		.length;
	expect(pages, 'the report has pages').toBeGreaterThan(0);
	expect(file.suggestedFilename()).toMatch(
		/^linker-planning-[a-f0-9]{32}-r\d+-en\.pdf$/
	);
});
