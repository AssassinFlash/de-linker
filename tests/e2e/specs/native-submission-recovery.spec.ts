import { test, expect } from '@playwright/test';
import { join } from 'node:path';
import {
	applyTurnstileProfile,
	instance,
	REPO_ROOT,
	wp,
} from '../lib/instance';
import { seedConsentCookies } from '../lib/consent';
import { waitForTurnstile } from '../lib/turnstile';

const fixture = join(REPO_ROOT, 'tests/e2e/fixtures/public-inquiry.php');
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);

for (const scenario of [
	{ locale: 'en', width: 1440, route: '/contact/', outcome: 'fail' },
	{ locale: 'de', width: 390, route: '/de/kontakt/', outcome: 'spent' },
] as const) {
	test(`${scenario.locale} ${scenario.width}: a refused verification keeps the contact message editable`, async ({
		context,
		page,
	}) => {
		const site = instance();
		const restore = applyTurnstileProfile(site.name, scenario.outcome);
		const email = `native-contact-${Date.now()}@example.test`;
		const message =
			scenario.locale === 'de'
				? 'Ich möchte einen Speicher anfragen.'
				: 'Please contact me about a battery.';
		try {
			run('setup', email);
			await seedConsentCookies(context);
			await page.setViewportSize({
				width: scenario.width,
				height: scenario.width === 390 ? 844 : 900,
			});
			await page.goto(site.url + scenario.route);
			const form = page.locator('form.linker-contact-form');
			await form.locator('[name=name]').fill('Alex Example');
			await form.locator('[name=email]').fill(email);
			await form.locator('textarea[name=message]').fill(message);
			await form.locator('[name=consent]').check();
			await waitForTurnstile(form);
			await Promise.all([
				page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
				form.locator('[type=submit]').first().click(),
			]);
			await expect(form.locator('[name=email]')).toHaveValue(email);
			await expect(form.locator('textarea[name=message]')).toHaveValue(
				message
			);
			await expect(form.locator('[name=consent]')).toBeChecked();
			expect(JSON.parse(run('read')).orders).toHaveLength(0);
			await expect(page.locator('.linker-contact-receipt')).toHaveCount(
				0
			);
		} finally {
			try {
				run('cleanup');
			} finally {
				restore();
			}
		}
	});
}
