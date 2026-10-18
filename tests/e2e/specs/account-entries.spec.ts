/** Guest sign-in surfaces also offer the native registration endpoint (#223). */
import { expect, test } from '@playwright/test';
import { instance, loginLink, wp } from '../lib/instance';

test.describe.configure({ timeout: 60_000 });

for (const locale of ['en', 'de'] as const) {
	const home = locale === 'de' ? '/de/' : '/';
	const account = locale === 'de' ? '/de/mein-konto/' : '/my-account/';
	for (const width of [1440, 390]) {
		for (const surface of ['dock', 'workspace']) {
			test(`${locale}-${width}: Genie ${surface} has native guest entries`, async ({
				page,
			}) => {
				await page.setViewportSize({ width, height: 900 });
				await page.goto(
					instance().url +
						(surface === 'workspace'
							? home + 'genie/'
							: width === 390
								? locale === 'de'
									? '/de/produkte/'
									: '/products/'
								: home)
				);
				if (surface === 'dock')
					await page
						.locator(
							width === 390
								? '.product-mobile-actions .linker-genie-chip'
								: '.linker-genie-open'
						)
						.click();
				const entries = page.locator(
					'.linker-genie-panel>.linker-guest-account-links'
				);
				await expect(entries).toBeVisible();
				await expect(entries.locator('a').first()).toHaveAttribute(
					'href',
					instance().url + account
				);
				const create = entries.locator('.linker-create-account');
				await expect(create).toHaveText(
					locale === 'de' ? 'Konto erstellen' : 'Create account'
				);
				await create.click();
				await expect(page).toHaveURL(
					instance().url + account + 'register/'
				);
			});
		}
		for (const [surface, route, selector] of [
			[
				'shop',
				locale === 'de' ? '/de/produkte/' : '/products/',
				'.sf-card-actions',
			],
			[
				'category',
				locale === 'de'
					? '/de/produkt-kategorie/wechselrichter/'
					: '/product-category/inverters/',
				'.sf-card-actions',
			],
			[
				'product',
				locale === 'de'
					? '/de/produkt/saj-h2-10k-t3/'
					: '/product/saj-h2-10k-t3/',
				'.pdp-price',
			],
			[
				'compare',
				home + 'compare-products/?ids=4107,4108',
				'#linker-compare',
			],
		]) {
			test(`${locale}-${width}: ${surface} price prompt offers registration`, async ({
				page,
			}) => {
				await page.setViewportSize({ width, height: 900 });
				await page.goto(instance().url + route);
				const create = page
					.locator(`${selector} .linker-create-account:visible`)
					.first();
				await expect(create).toBeVisible();
				await create.click();
				await expect(page).toHaveURL(
					instance().url + account + 'register/'
				);
			});
		}
		for (const [surface, route, selector] of [
			[
				'draft',
				locale === 'de' ? '/de/warenkorb/' : '/cart/',
				'.sf-cart-empty',
			],
			['lost', account + 'lost-password/', '.linker-auth-links'],
			[
				'lost-confirmation',
				account + 'lost-password/?reset-link-sent=true',
				'.linker-auth-links',
			],
			[
				'document',
				home + '?linker-document=proforma&id=1',
				'#error-page',
			],
		]) {
			test(`${locale}-${width}: ${surface} has independent registration`, async ({
				page,
			}) => {
				await page.setViewportSize({ width, height: 900 });
				const response = await page.goto(instance().url + route);
				if (surface === 'document')
					expect(response?.status()).toBe(403);
				const create = page
					.locator(selector!)
					.locator('.linker-create-account');
				await expect(create).toBeVisible();
				await create.click();
				await expect(page).toHaveURL(
					instance().url + account + 'register/'
				);
			});
		}
		test(`${locale}-${width}: open inquiry keeps both optional account entries`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 900 });
			await page.goto(
				instance().url +
					(locale === 'de'
						? '/de/proforma-anfrage/'
						: '/proforma-request/')
			);
			await expect(page.locator('#inquiry-email')).toBeVisible();
			const create = page.locator(
				'.linker-inquiry-guest .linker-create-account'
			);
			await expect(create).toBeVisible();
			await create.click();
			await expect(page).toHaveURL(
				instance().url + account + 'register/'
			);
		});
		test(`${locale}-${width}: footer offers a direct registration entry`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 900 });
			await page.goto(instance().url + home);
			await page.locator('#footer-tab-account').click();
			const panel = page.locator('#footer-panel-account');
			await expect(panel.locator('.linker-create-account')).toBeVisible();
			await expect(panel.locator('.footer-panel-count')).toHaveText('04');
			await panel.locator('.linker-create-account').click();
			await expect(page).toHaveURL(
				instance().url + account + 'register/'
			);
		});
		test(`${locale}-${width}: header registration opens its own language's form`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 900 });
			await page.goto(instance().url + home);
			if (width === 1440) await page.locator('.tv-b2b-acct-btn').click();
			else await page.locator('#tv-mobile-toggle').click();
			const scope = page.locator(
				width === 1440 ? '.tv-b2b-acct-menu' : '#tv-mobile-panel'
			);
			const create = scope.locator('.linker-create-account');
			await expect(create).toBeVisible();
			await expect(create).toHaveAttribute(
				'href',
				instance().url + account + 'register/'
			);
			await create.click();
			await expect(page).toHaveURL(
				instance().url + account + 'register/'
			);
			await expect(page.locator('form.register')).toBeVisible();
		});
	}
}

test('a separate newly created account still cannot read another account document', async ({
	page,
}) => {
	const fixture = JSON.parse(
		wp([
			'eval',
			`$a = wp_insert_user( [ 'user_login' => 'c223_document_owner', 'user_email' => 'c223-owner@example.test', 'role' => 'customer', 'user_pass' => wp_generate_password() ] ); $b = wp_insert_user( [ 'user_login' => 'c223_document_other', 'user_email' => 'c223-other@example.test', 'role' => 'customer', 'user_pass' => wp_generate_password() ] ); if ( is_wp_error( $a ) || is_wp_error( $b ) ) { throw new Exception( 'fixture account already exists' ); } $o = wc_create_order( [ 'customer_id' => $a ] ); update_user_meta( $b, 'linker_approval_status', 'approved' ); echo json_encode( [ 'owner' => $a, 'other' => $b, 'order' => $o->get_id() ] );`,
		])
	) as { owner: number; other: number; order: number };
	try {
		const route = `${instance().url}/?linker-document=proforma&id=${fixture.order}`;
		expect((await page.goto(route))?.status()).toBe(403);
		await expect(page.locator('.linker-create-account')).toBeVisible();
		await page.goto(loginLink(undefined, 'c223_document_other'));
		expect((await page.goto(route))?.status()).toBe(403);
		await expect(page.locator('.linker-create-account')).toHaveCount(0);
	} finally {
		wp([
			'eval',
			`$o = wc_get_order( ${fixture.order} ); if ( $o ) { $o->delete( true ); } require_once ABSPATH . 'wp-admin/includes/user.php'; wp_delete_user( ${fixture.owner} ); wp_delete_user( ${fixture.other} );`,
		]);
	}
});
