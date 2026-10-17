/** Customer admin access through Woo's native protection and real sessions. */
import { expect, test } from '@playwright/test';
import { existsSync, mkdirSync, unlinkSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { instance, loginLink, REPO_ROOT, wp } from '../lib/instance';

test.setTimeout(60_000);

const evidence = join(REPO_ROOT, 'docs/acceptance/2026-10-18/245');
const base = () => instance().url;

for (const language of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${language} ${width}: customers read the admin explanation in every approval state`, async ({
			page,
		}) => {
			const login = `c245-${language}-${width}-${Date.now()}`;
			const email = `${login}@example.test`;
			const id = wp([
				'user',
				'create',
				login,
				email,
				'--role=customer',
				'--porcelain',
			]).trim();
			try {
				await page.setViewportSize({ width, height: 900 });
				await page.goto(loginLink(undefined, login));
				await page.goto(
					`${base()}${language === 'de' ? '/de/mein-konto/' : '/my-account/'}`
				);
				for (const state of [
					'approved',
					'pending',
					'restricted',
					'rejected',
				]) {
					wp([
						'user',
						'meta',
						'update',
						id,
						'linker_approval_status',
						state,
					]);
					for (const path of [
						'/wp-admin',
						'/wp-admin/',
						'/wp-admin/users.php',
					]) {
						await page.goto(`${base()}${path}`);
						const notice = page.locator(
							'[data-linker-admin-notice]'
						);
						await expect(notice).toBeVisible();
						await expect(notice).toContainText(email);
						await expect(notice).toContainText(
							language === 'de'
								? 'Der Verwaltungsbereich ist ausschließlich für Linker-Mitarbeitende vorgesehen.'
								: 'The admin area is for Linker staff only.'
						);
						await expect(page).toHaveURL(
							language === 'de'
								? /\/de\/mein-konto\/\?admin-access=staff/
								: /\/my-account\/\?admin-access=staff/
						);
						const account = notice.getByRole('link', {
							name:
								language === 'de'
									? 'Zu meinem Konto'
									: 'Go to my account',
							exact: true,
						});
						await expect(account).toHaveAttribute(
							'href',
							`${base()}${language === 'de' ? '/de/mein-konto/' : '/my-account/'}`
						);
						expect(
							await page.evaluate(
								() =>
									document.documentElement.scrollWidth <=
									innerWidth
							)
						).toBe(true);
						if (path !== '/wp-admin') {
							mkdirSync(evidence, { recursive: true });
							await page.evaluate(async () => {
								await document.fonts.ready;
							});
							await page.screenshot({
								path: join(
									evidence,
									`${language}-${width}-${state}-${path.includes('users') ? 'users' : 'admin'}.png`
								),
								fullPage: true,
								animations: 'disabled',
							});
						}
					}
				}
			} finally {
				wp(['user', 'delete', id, '--yes']);
			}
		});
	}
}

for (const language of ['en', 'de'] as const) {
	test(`${language}: one click signs out and staff sign-in reaches wp-admin`, async ({
		page,
	}) => {
		const stamp = Date.now();
		const customer = `c245-customer-${stamp}`;
		const staff = `c245-staff-${stamp}`;
		const password = 'C245-local-fixture-9!';
		const customerId = wp([
			'user',
			'create',
			customer,
			`${customer}@example.test`,
			'--role=customer',
			'--porcelain',
		]).trim();
		const staffId = wp([
			'user',
			'create',
			staff,
			`${staff}@example.test`,
			'--role=administrator',
			`--user_pass=${password}`,
			'--porcelain',
		]).trim();
		try {
			await page.goto(loginLink(undefined, customer));
			await page.goto(
				`${base()}${language === 'de' ? '/de/mein-konto/' : '/my-account/'}`
			);
			await page.goto(`${base()}/wp-admin/users.php`);
			await page
				.locator('[data-linker-admin-notice] .is-primary')
				.click();
			await expect(page.locator('#user_login')).toBeVisible();
			await expect(page.locator('html')).toHaveAttribute(
				'lang',
				language === 'de' ? 'de-DE' : 'en-US'
			);
			await expect(page).toHaveURL(/\/wp-login.php\?redirect_to=/);
			await expect(
				page.locator('#loginform input[name="redirect_to"]')
			).toHaveValue(`${base()}/wp-admin/`);
			await page.screenshot({
				path: join(evidence, `${language}-staff-login.png`),
				fullPage: false,
				animations: 'disabled',
			});
			await page.locator('#user_login').fill(staff);
			await page.locator('#user_pass').fill(password);
			await page.locator('#wp-submit').click();
			await expect(page).toHaveURL(`${base()}/wp-admin/`);
			await expect(page.locator('body.wp-admin')).toBeVisible();
			await expect(
				page.locator('[data-linker-admin-notice]')
			).toHaveCount(0);
			await page.screenshot({
				path: join(evidence, `${language}-staff-after-login.png`),
				fullPage: false,
				animations: 'disabled',
			});
		} finally {
			wp(['user', 'delete', customerId, staffId, '--yes']);
		}
	});
}

test('User Switching: switch to customer, read explanation, switch back to staff', async ({
	page,
}) => {
	const stamp = Date.now();
	const customer = `c245-switch-customer-${stamp}`;
	const staff = `c245-switch-staff-${stamp}`;
	const customerId = wp([
		'user',
		'create',
		customer,
		`${customer}@example.test`,
		'--role=customer',
		'--porcelain',
	]).trim();
	const staffId = wp([
		'user',
		'create',
		staff,
		`${staff}@example.test`,
		'--role=administrator',
		'--porcelain',
	]).trim();
	try {
		wp([
			'user',
			'meta',
			'update',
			customerId,
			'linker_approval_status',
			'approved',
		]);
		await page.goto(loginLink(undefined, staff));
		await page.goto(`${base()}/wp-admin/users.php?s=${customer}`);
		await page.locator(`#user-${customerId}`).hover();
		await page
			.locator(`#user-${customerId} a[href*="action=switch_to_user"]`)
			.click();
		await page.goto(`${base()}/wp-admin/users.php`);
		await expect(page.locator('[data-linker-admin-notice]')).toContainText(
			`${customer}@example.test`
		);
		const switchBack = page.locator('#user_switching_switch_on a');
		await expect(switchBack).toBeVisible();
		await page.screenshot({
			path: join(evidence, 'user-switching-customer.png'),
			fullPage: true,
			animations: 'disabled',
		});
		await switchBack.click();
		await page.goto(`${base()}/wp-admin/`);
		await expect(page.locator('body.wp-admin')).toBeVisible();
		await expect(page.locator('#wp-admin-bar-my-account')).toContainText(
			staff
		);
		await page.screenshot({
			path: join(evidence, 'user-switching-back.png'),
			fullPage: false,
			animations: 'disabled',
		});
	} finally {
		wp(['user', 'delete', customerId, staffId, '--yes']);
	}
});

test('the language switch keeps the explanation open in both directions', async ({
	page,
}) => {
	const login = `c245-language-${Date.now()}`;
	const id = wp([
		'user',
		'create',
		login,
		`${login}@example.test`,
		'--role=customer',
		'--porcelain',
	]).trim();
	try {
		await page.goto(loginLink(undefined, login));
		await page.goto(`${base()}/my-account/`);
		await page.goto(`${base()}/wp-admin/`);
		await page
			.getByRole('banner')
			.getByRole('link', { name: 'DE', exact: true })
			.click();
		await expect(page.locator('[data-linker-admin-notice]')).toContainText(
			'Bereich für Linker-Mitarbeitende'
		);
		await page
			.getByRole('banner')
			.getByRole('link', { name: 'EN', exact: true })
			.click();
		await expect(page.locator('[data-linker-admin-notice]')).toContainText(
			'Linker staff only'
		);
	} finally {
		wp(['user', 'delete', id, '--yes']);
	}
});

test('native AJAX, admin-post and guest sign-in remain outside the explanation', async ({
	page,
}) => {
	const login = `c245-exempt-${Date.now()}`;
	const id = wp([
		'user',
		'create',
		login,
		`${login}@example.test`,
		'--role=customer',
		'--porcelain',
	]).trim();
	try {
		await page.goto(loginLink(undefined, login));
		for (const path of [
			'/wp-admin/admin-ajax.php',
			'/wp-admin/admin-post.php',
		]) {
			const response = await page.request.get(`${base()}${path}`, {
				maxRedirects: 0,
			});
			expect(response.headers().location).toBeUndefined();
			expect(await response.text()).not.toContain(
				'data-linker-admin-notice'
			);
		}
		await page.context().clearCookies();
		await page.goto(`${base()}/wp-admin/users.php`);
		await expect(page.locator('#user_login')).toBeVisible();
		await expect(page.locator('[data-linker-admin-notice]')).toHaveCount(0);
	} finally {
		wp(['user', 'delete', id, '--yes']);
	}
});

test('Woo extension decisions control the explanation across requests without a role rule', async ({
	page,
}) => {
	const fixture = join(
		instance().dir,
		'wordpress/wp-content/mu-plugins/c245-woo-decision.php'
	);
	if (existsSync(fixture)) {
		throw new Error(
			'c245 Woo decision fixture already exists; refusing to overwrite it'
		);
	}
	const login = `c245-woo-decision-${Date.now()}`;
	const id = wp([
		'user',
		'create',
		login,
		`${login}@example.test`,
		'--role=customer',
		'--porcelain',
	]).trim();
	try {
		wp([
			'user',
			'meta',
			'update',
			id,
			'linker_approval_status',
			'approved',
		]);
		wp(['user', 'meta', 'update', id, 'c245_notice_decision', 'allow']);
		// Woo's native default-priority filter runs before the final observer.
		writeFileSync(
			fixture,
			`<?php
add_filter('woocommerce_prevent_admin_access', static function ($prevent) {
if (get_current_user_id() !== ${Number(id)}) { return $prevent; }
return 'deny' === get_user_meta(${Number(id)}, 'c245_notice_decision', true);
});
`
		);
		await page.goto(loginLink(undefined, login));
		await page.goto(`${base()}/my-account/?admin-access=staff`);
		await expect(page.locator('[data-linker-admin-notice]')).toHaveCount(0);
		wp(['user', 'meta', 'update', id, 'c245_notice_decision', 'deny']);
		await page.goto(`${base()}/wp-admin/users.php`);
		await expect(page.locator('[data-linker-admin-notice]')).toContainText(
			`${login}@example.test`
		);
		wp(['user', 'meta', 'update', id, 'c245_notice_decision', 'allow']);
		await page.goto(`${base()}/wp-admin/`);
		await expect(page.locator('body.wp-admin')).toBeVisible();
		await page.goto(`${base()}/my-account/?admin-access=staff`);
		await expect(page.locator('[data-linker-admin-notice]')).toHaveCount(0);
	} finally {
		if (existsSync(fixture)) {
			unlinkSync(fixture);
		}
		wp(['user', 'delete', id, '--yes']);
	}
});
