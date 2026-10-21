/** Filled drafts must inherit the same usable actions as the empty state. */
import { expect, test } from '@playwright/test';
import { instance, loginLink } from '../lib/instance';

test.setTimeout(60_000);

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${locale} ${width}: filled draft actions, quantity and inquiry entry`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 900 });
			const base = instance().url;
			const draft = locale === 'en' ? '/cart/' : '/de/loesungsentwurf/';
			const product =
				locale === 'en'
					? '/product/saj-bu2-5-0-hv1/'
					: '/de/produkt/saj-bu2-5-0-hv1/';
			await page.goto(base + draft);
			const reject = page.getByRole('button', {
				name: /^(Reject all|Alle ablehnen)$/,
			});
			if (await reject.isVisible()) await reject.click();
			await expect(page.locator('.sf-cart-empty')).toBeVisible();
			await page.goto(base + product);
			await page
				.locator('a[href*="add-to-cart="]:visible')
				.first()
				.click();
			await page.goto(base + draft);
			const summary = page.locator('.linker-login-box');
			const primary = summary.locator('a.button');
			await expect(primary).toHaveCSS('color', 'rgb(255, 255, 255)');
			await expect(summary).toHaveCSS(
				'background-color',
				'rgb(255, 255, 255)'
			);
			const geometry = await summary.evaluate((node) => {
				const intro = node.querySelector('p')!.getBoundingClientRect();
				const action = node
					.querySelector('a.button')!
					.getBoundingClientRect();
				const account = node
					.querySelector('.linker-create-account')!
					.getBoundingClientRect();
				return {
					gap: action.top - intro.bottom,
					height: action.height,
					secondaryGap: account.top - action.bottom,
					secondaryHeight: account.height,
				};
			});
			// Reuse the site's 16px spacing token and 44px control footprint.
			expect(geometry.gap).toBeGreaterThanOrEqual(16);
			expect(geometry.height).toBeGreaterThanOrEqual(44);
			expect(geometry.secondaryGap).toBeGreaterThanOrEqual(12);
			expect(geometry.secondaryHeight).toBeGreaterThanOrEqual(44);
			await expect(
				page.locator('.cart_item .linker-price-entries:visible')
			).toHaveCount(1);
			const quantity = page.locator('input.qty');
			await quantity.fill('2');
			await quantity.press('Tab');
			const [updated] = await Promise.all([
				page.waitForResponse(
					(response) =>
						new URL(response.url()).pathname === draft &&
						response.request().method() === 'POST'
				),
				page.locator('button[name="update_cart"]').click(),
			]);
			await updated.finished();
			await expect(
				page.locator('button[name="update_cart"]')
			).toBeDisabled();
			await expect(quantity).toHaveValue('2');
			await page.reload();
			await expect(quantity).toHaveValue('2');
			await primary.click();
			await expect(page.locator('.linker-inquiry-form')).toBeVisible();
			await expect(page.locator('body')).toContainText('SAJ BU2-5.0-HV1');
			// Entry only: no inquiry or registration is submitted.
			await page.goto(base + draft);
			await page
				.locator('.linker-login-box .linker-create-account')
				.click();
			await expect(page).toHaveURL(/\/(?:register|registrieren)\/$/);
			// Existing local staff has approved price access; no account is created.
			await page.goto(loginLink(instance().name, '857558227@qq.com'));
			await page.goto(base + draft);
			await expect(page.locator('.linker-login-box')).toHaveCount(0);
			const priced = page
				.locator('.cart_item')
				.filter({ hasText: 'SAJ BU2-5.0-HV1' });
			await expect(
				priced.locator('.product-price .woocommerce-Price-amount')
			).toBeVisible();
		});
	}
}
