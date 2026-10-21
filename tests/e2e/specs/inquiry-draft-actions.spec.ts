/** Native Woo edits stay inside the inquiry; unsent reply fields survive. */
import { expect, test } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { instance, REPO_ROOT } from '../lib/instance';

const shots = join(
	REPO_ROOT,
	'docs/acceptance/2026-10-22/component-states/screens'
);
test.setTimeout(60_000);
for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${locale} ${width}: inquiry draft remove, undo, zero and link feedback`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 900 });
			const base = instance().url;
			const request =
				locale === 'en'
					? '/proforma-request/'
					: '/de/proforma-anfrage/';
			const product =
				locale === 'en'
					? '/product/saj-bu2-5-0-hv1/'
					: '/de/produkt/saj-bu2-5-0-hv1/';
			await page.goto(base + product);
			const reject = page.getByRole('button', {
				name: /^(Reject all|Alle ablehnen)$/,
			});
			if (await reject.isVisible()) await reject.click();
			await page
				.locator('a[href*="add-to-cart="]:visible')
				.first()
				.click();
			await page.goto(base + request);
			await expect(page.locator('#wc-cart-js')).toBeAttached();
			const lines = page.locator('.linker-inquiry-line');
			const productLink = page.locator('.linker-inquiry-product');
			const normalColor = await productLink.evaluate(
				(node) => getComputedStyle(node).color
			);
			await productLink.hover();
			await expect(productLink).not.toHaveCSS('color', normalColor);
			await expect(productLink).toHaveCSS(
				'text-decoration-line',
				'underline'
			);
			await page.mouse.move(0, 0);
			await productLink.focus();
			await expect(productLink).toHaveCSS('outline-style', 'solid');
			const target = await productLink.getAttribute('href');
			await productLink.press('Enter');
			await expect(page).toHaveURL(target!);
			await page.goto(base + request);
			const main = page.locator('.linker-inquiry-form');
			await main.locator('[name="message"]').fill('Unsent visual check.');
			await main.locator('[name="name"]').fill('Visual Check');
			await main
				.locator('[name="email"]')
				.fill('visual-check@example.test');
			await main.locator('[name="consent"]').check();
			const unchanged = async () => {
				await expect(main.locator('[name="message"]')).toHaveValue(
					'Unsent visual check.'
				);
				await expect(main.locator('[name="name"]')).toHaveValue(
					'Visual Check'
				);
				await expect(main.locator('[name="email"]')).toHaveValue(
					'visual-check@example.test'
				);
				await expect(page).toHaveURL(base + request);
			};
			const remove = page.locator('.linker-inquiry-remove');
			await expect(remove).toBeVisible();
			expect((await remove.boundingBox())!.height).toBeGreaterThanOrEqual(
				44
			);
			await remove.click();
			await expect(lines).toHaveCount(0);
			await expect(page.locator('.linker-inquiry-empty')).toBeVisible();
			await unchanged();
			await page.locator('.restore-item').click();
			await expect(lines).toHaveCount(1);
			await unchanged();
			const quantity = lines.locator('input.qty');
			await quantity.fill('2');
			await quantity.press('Tab');
			const update = page.locator('.linker-inquiry-update');
			let release!: () => void;
			const held = new Promise<void>((resolve) => {
				release = resolve;
			});
			await page.route(base + request, async (route) => {
				if (route.request().method() === 'POST') await held;
				await route.continue();
			});
			let inquiries = 0;
			await page.route('**/wp-admin/admin-post.php', (route) => {
				inquiries++;
				return route.fulfill({
					status: 409,
					body: 'Fixture blocks all inquiry submissions.',
				});
			});
			try {
				await update.click();
				await expect(
					main.locator('button[type="submit"]')
				).toBeDisabled();
				await expect(main.locator('button[type="submit"]')).toHaveCSS(
					'opacity',
					'0.6'
				);
				await main.evaluate((form) =>
					(form as HTMLFormElement).requestSubmit()
				);
				await expect(main).not.toHaveAttribute(
					'data-account-state',
					'submitting'
				);
				expect(inquiries).toBe(0);
			} finally {
				release();
			}
			await expect(update).toBeDisabled();
			await expect(quantity).toHaveValue('2');
			await expect(main.locator('button[type="submit"]')).toBeEnabled();
			await unchanged();
			expect(
				await page.evaluate(
					() => document.documentElement.scrollWidth <= innerWidth
				)
			).toBe(true);
			mkdirSync(shots, { recursive: true });
			await page.locator('.linker-inquiry-draft').screenshot({
				path: join(shots, `inquiry-${locale}-local-${width}.png`),
				animations: 'disabled',
			});
			await quantity.fill('0');
			await quantity.press('Enter');
			await expect(lines).toHaveCount(0);
			await expect(page.locator('.linker-inquiry-empty')).toBeVisible();
			await unchanged();
			// No inquiry, registration or email submission.
		});
	}
}
