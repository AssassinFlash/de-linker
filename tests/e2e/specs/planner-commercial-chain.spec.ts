/**
 * The commercial sizing chain on the deployed planner, end to end.
 *
 * The engine sizes commercial storage only when it receives a 15-minute load
 * profile and the peak to hold (`services/engine` `commercial.py` `design()`);
 * without both it answers indicative ranges by design. The production walk
 * found the workspace never carried either input, so a customer could only
 * ever reach the indicative answer. This spec drives the real review stack —
 * real WordPress, the real engine on its own port, the shipped planner bundle
 * — and asserts the sized answer the customer now gets.
 *
 * 1440 and 390: the panel's own inputs and the sized table must both stay
 * usable at the phone width the site is judged on.
 */
import { expect, test, type Page } from '@playwright/test';
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

test.beforeEach(async ({ context }) => {
	await seedConsentCookies(context);
});

/** One month of a plausible commercial load, one value per line. */
function loadProfile(days = 30): string {
	const lines: string[] = [];
	for (let day = 0; day < days; day += 1) {
		for (let quarter = 0; quarter < 96; quarter += 1) {
			const hour = (quarter * 15) / 60;
			lines.push(
				String(hour >= 7 && hour < 18 ? 95 + (quarter % 8) * 3 : 18),
			);
		}
	}
	return lines.join('\n');
}

/** A saved commercial project, created through the interface and read back. */
async function commercialProject(page: Page, title: string): Promise<string> {
	await page.goto(instance().url + '/solution-configurator/?energy_view=equipment', {
		waitUntil: 'networkidle',
	});
	await page.getByRole('button', { name: /^New project$/i }).first().click();
	await page.locator('input[maxlength="256"]').first().fill(title);
	await page.getByRole('button', { name: /^Create project$/i }).click();
	await expect(page).toHaveURL(/project=/, { timeout: 60_000 });
	const id = new URL(page.url()).searchParams.get('project') ?? '';
	expect(id).toMatch(/^[a-f0-9]{32}$/);

	// The site's use is what offers the commercial sizing panel; it lives in
	// the brief's own section, not the project-location section beside it.
	await page
		.locator('#lp-brief-use select')
		.first()
		.selectOption('commercial');
	// The annual consumption is the brief's declared load.
	const annual = page.locator('#lp-brief-use input[inputmode="decimal"]');
	if (await annual.count()) await annual.first().fill('380000');
	// The postcode travels in the location label, which is where the panel
	// reads it from. In `#lp-site` the first input is the address; the two
	// decimal fields beside it are the coordinates.
	await page
		.locator('#lp-site input')
		.nth(0)
		.fill('80331 München');
	// The brief's coordinate fields report a format error while empty, which
	// keeps the project unsaveable, so they are filled the way a customer
	// locating the site would.
	const coordinates = page.locator('#lp-site input[inputmode="decimal"]');
	await coordinates.nth(0).fill('48.14');
	await coordinates.nth(1).fill('11.58');
	// The brief edits stay in the open draft until the project is saved, and
	// the commercial panel's gate reads the saved brief.
	await page.getByRole('button', { name: /^Save project$/i }).click();
	await expect(page.locator('.lp-save-state')).toContainText(/^Saved/i, {
		timeout: 120_000,
	});
	// The commercial panel lives in the equipment workspace, which the
	// project's own navigation opens.
	await page
		.locator('.lp-project-aside nav a', { hasText: /^Equipment$/ })
		.first()
		.click();
	await expect(page.locator('#lp-commercial-title')).toBeVisible({
		timeout: 120_000,
	});
	return id;
}

test('a commercial project with a load profile and a target peak is sized from both', async ({
	page,
}) => {
	await page.setViewportSize({ width: 1440, height: 900 });
	const profile = loadProfile(30);
	await commercialProject(page, 'K-line commercial sized');

	const panel = page.locator('#lp-commercial-title');
	await expect(panel).toBeVisible({ timeout: 120_000 });
	const section = panel.locator('xpath=ancestor::section[1]');
	await expect(section.locator('input[inputmode="numeric"]').first()).toHaveValue(
		'80331',
	);

	const numbers = section.locator('input[inputmode="decimal"]');
	await numbers.nth(0).fill('150'); // grid connection capacity, kVA
	await numbers.nth(1).fill('380000'); // annual consumption, kWh
	await numbers.nth(2).fill('119'); // peak from the bill, kW
	await numbers.nth(3).fill('70'); // target peak, kW

	await section.locator('input[type="file"]').setInputFiles({
		name: 'load.csv',
		mimeType: 'text/csv',
		buffer: Buffer.from(profile, 'utf8'),
	});
	await expect(section).toContainText(/intervals read from the file/i, {
		timeout: 30_000,
	});

	await section.getByRole('button', { name: /Size the storage/i }).click();

	// A sized answer carries systems; the indicative answer never does. This is
	// the exact distinction the production walk could not reach.
	await expect(section).toContainText(/Sized storage/i, { timeout: 150_000 });
	await expect(section).toContainText(/Usable energy/i);
	await expect(section).toContainText(/Peak in the profile/i);
	await expect(section).not.toContainText(/Indicative ranges/i);
	const rows = section.locator('table tbody tr');
	await expect(rows.first()).toBeVisible();
	expect(await rows.count()).toBeGreaterThan(0);
});

test('the panel stays usable at the phone width the site is judged on', async ({
	page,
}) => {
	await page.setViewportSize({ width: 390, height: 844 });
	const profile = loadProfile(7);
	await commercialProject(page, 'K-line commercial 390');

	const panel = page.locator('#lp-commercial-title');
	await expect(panel).toBeVisible({ timeout: 120_000 });
	const section = panel.locator('xpath=ancestor::section[1]');
	await expect(section.locator('input[inputmode="numeric"]').first()).toBeVisible();
	const box = await panel.boundingBox();
	expect(box!.width).toBeLessThanOrEqual(390);

	const numbers = section.locator('input[inputmode="decimal"]');
	await numbers.nth(0).fill('150');
	await numbers.nth(1).fill('380000');
	await numbers.nth(2).fill('119');
	await numbers.nth(3).fill('70');
	await section.locator('input[type="file"]').setInputFiles({
		name: 'load.csv',
		mimeType: 'text/csv',
		buffer: Buffer.from(profile, 'utf8'),
	});
	await expect(section).toContainText(/intervals read from the file/i, {
		timeout: 30_000,
	});
	await section.getByRole('button', { name: /Size the storage/i }).click();
	await expect(section).toContainText(/Sized storage/i, { timeout: 150_000 });
});
