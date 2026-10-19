/** Basic mode on the real CMP, Consent API, Site Kit and WooCommerce. */
import { writeFileSync, unlinkSync, existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { instance, instanceName, wp } from '../lib/instance';

const target = instance(instanceName());
const keys = [
	'googlesitekit_active_modules',
	'googlesitekit_analytics-4_settings',
] as const;
const saved = new Map<string, string>();
const measurementId = 'G-TEST201123';
const fixturePath = join(
	target.dir,
	'wordpress/wp-content/mu-plugins/linker-consent-fixture.php'
);
const google =
	/https:\/\/[^/]*(?:googletagmanager\.com|google-analytics\.com|doubleclick\.net)\//;
const fixtureMark =
	'Local-only fixture: Site Kit normally suppresses all tags in local environments.';

function fixtureSource(): string {
	return `<?php
// ${fixtureMark}
add_filter('googlesitekit_allowed_tag_environment_types', function ($types) {
 if (wp_get_environment_type() === 'local' && (get_option('googlesitekit_analytics-4_settings', [])['measurementID'] ?? '') === 'G-TEST201123') { $types[] = 'local'; }
 return $types;
});
`;
}

/** A crashed run leaves this file and used to abort the next one. */
function clearOwnedFixture(): void {
	if (!existsSync(fixturePath)) return;
	const body = readFileSync(fixturePath, 'utf8');
	if (!body.includes(fixtureMark)) {
		throw new Error(
			`Refusing to replace an mu-plugin that is not the consent fixture: ${fixturePath}`
		);
	}
	unlinkSync(fixturePath);
}

test.use({ bypassCSP: true });

test.beforeAll(() => {
	clearOwnedFixture();
	writeFileSync(fixturePath, fixtureSource());
	for (const key of keys) {
		saved.set(
			key,
			wp(['eval', `echo wp_json_encode(get_option('${key}', null));`])
		);
	}
	const active = JSON.parse(saved.get(keys[0])!) || [];
	wp([
		'option',
		'update',
		keys[0],
		JSON.stringify([...new Set([...active, 'analytics-4'])]),
		'--format=json',
	]);
	const analytics = JSON.parse(saved.get(keys[1])!);
	wp([
		'option',
		'update',
		keys[1],
		JSON.stringify({
			...analytics,
			accountID: '1234',
			propertyID: '1234',
			webDataStreamID: '1234',
			measurementID: measurementId,
			googleTagID: measurementId,
			useSnippet: true,
			trackingDisabled: [],
		}),
		'--format=json',
	]);
});

test.afterAll(() => {
	clearOwnedFixture();
	for (const [key, value] of saved) {
		if (value === 'null') wp(['option', 'delete', key]);
		else wp(['option', 'update', key, value, '--format=json']);
	}
});

async function observe(page: Page): Promise<string[]> {
	const requests: string[] = [];
	page.on('request', (request) => {
		if (google.test(request.url())) requests.push(request.url());
	});
	// The real gtag library runs; measurement transmissions are intercepted.
	// No local fixture data enters the production Analytics property.
	await page.route(google, async (route) => {
		if (route.request().url().includes('/gtag/js')) await route.continue();
		else await route.fulfill({ status: 204, body: '' });
	});
	return requests;
}

async function trackingCookies(page: Page): Promise<string[]> {
	return (await page.context().cookies())
		.filter((cookie) => /^(_ga(?:_|$)|sbjs_)/.test(cookie.name))
		.map((cookie) => cookie.name);
}

for (const lang of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${lang} ${width}: first visit and rejection never measure`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 960 });
			const requests = await observe(page);
			await page.goto(`${target.url}${lang === 'de' ? '/de/' : '/'}`);
			await expect(page.locator('.cky-consent-container')).toBeVisible();
			await expect(
				page.locator('[data-cky-tag="accept-button"]')
			).toHaveText(lang === 'de' ? 'Alle akzeptieren' : 'Accept all');
			await page.waitForTimeout(900);
			expect(requests).toEqual([]);
			expect(await trackingCookies(page)).toEqual([]);
			await page.locator('[data-cky-tag="reject-button"]').click();
			await page.reload();
			await page.waitForTimeout(900);
			expect(requests).toEqual([]);
			expect(await trackingCookies(page)).toEqual([]);
		});
	}
}

for (const purpose of ['statistics', 'marketing', 'both'] as const) {
	test(`independent purposes: ${purpose}`, async ({ page }) => {
		const requests = await observe(page);
		await page.goto(
			`${target.url}/?utm_source=consent-fixture&utm_medium=acceptance`
		);
		await page.locator('[data-cky-tag="settings-button"]').click();
		if (purpose !== 'marketing')
			await page.locator('#ckySwitchanalytics').check();
		if (purpose !== 'statistics')
			await page.locator('#ckySwitchadvertisement').check();
		await page.locator('[data-cky-tag="detail-save-button"]').click();
		if (purpose !== 'marketing') {
			await expect
				.poll(() => requests.some((url) => url.includes('/g/collect')))
				.toBe(true);
			const collect = requests.find((url) => url.includes('/g/collect'))!;
			expect(new URL(collect).searchParams.get('gcs')).toBe('G101');
		} else {
			await page.waitForTimeout(900);
			expect(requests).toEqual([]);
		}
		const cookies = await page.context().cookies();
		await test.info().attach('cookie-expiry-evidence', {
			body: JSON.stringify({
				purpose,
				observedAt: Date.now() / 1000,
				cookies: cookies.filter((cookie) =>
					/^(_ga(?:_|$)|sbjs_|cookieyes-consent)/.test(cookie.name)
				),
			}),
			contentType: 'application/json',
		});
		await test.info().attach('google-requests', {
			body: JSON.stringify(requests),
			contentType: 'application/json',
		});

		expect(cookies.some((cookie) => cookie.name === '_ga')).toBe(
			purpose !== 'marketing'
		);
		expect(
			cookies.some(
				(cookie) =>
					cookie.name === 'sbjs_current' &&
					cookie.value.includes('consent-fixture')
			)
		).toBe(purpose !== 'statistics');
		await page.goto(`${target.url}/de/`);
		await expect(page.locator('.cky-consent-container')).not.toBeVisible();
	});
}

for (const source of [false, true]) {
	test(`withdraw analytics${source ? ' and visit source' : ' only'}: no denied ping, no cookies on next page`, async ({
		page,
	}) => {
		const requests = await observe(page);
		await page.goto(`${target.url}/`);
		await page.locator('[data-cky-tag="settings-button"]').click();
		await page.locator('#ckySwitchanalytics').check();
		if (source) await page.locator('#ckySwitchadvertisement').check();
		await page.locator('[data-cky-tag="detail-save-button"]').click();
		await expect
			.poll(() => requests.some((url) => url.includes('/g/collect')))
			.toBe(true);
		await page.locator('.cky-banner-element').first().click();
		const before = requests.length;
		await page.locator('[data-cky-tag="detail-reject-button"]').click();
		await page.waitForTimeout(1200);
		await page.goto(`${target.url}/de/`);
		await page.waitForTimeout(900);
		expect(requests.slice(before)).toEqual([]);
		expect(await trackingCookies(page)).toEqual([]);
	});
}

test('withdraw marketing only: analytics stays denied and source cookies clear', async ({
	page,
}) => {
	const requests = await observe(page);
	await page.goto(
		`${target.url}/?utm_source=consent-fixture&utm_medium=acceptance`
	);
	await page.locator('[data-cky-tag="settings-button"]').click();
	await page.locator('#ckySwitchadvertisement').check();
	await page.locator('[data-cky-tag="detail-save-button"]').click();
	await expect
		.poll(async () =>
			(await page.context().cookies()).some(
				(cookie) =>
					cookie.name === 'sbjs_current' &&
					cookie.value.includes('consent-fixture')
			)
		)
		.toBe(true);
	expect(requests.filter((url) => url.includes('/g/collect'))).toEqual([]);
	expect(
		(await page.context().cookies()).some((cookie) => cookie.name === '_ga')
	).toBe(false);

	await page.locator('.cky-banner-element').first().click();
	await page.locator('#ckySwitchadvertisement').uncheck();
	await page.locator('[data-cky-tag="detail-save-button"]').click();
	await page.waitForTimeout(1200);
	await page.goto(`${target.url}/de/`);
	await page.waitForTimeout(900);
	expect(requests.filter((url) => url.includes('/g/collect'))).toEqual([]);
	expect(await trackingCookies(page)).toEqual([]);
});
