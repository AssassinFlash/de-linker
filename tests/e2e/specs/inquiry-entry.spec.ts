/** A native product add is consumed once before editing the inquiry draft. */
import { expect, test } from '@playwright/test';
import { instance } from '../lib/instance';

test.setTimeout(60_000);

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${locale} ${width}: product entry, undo and reload never add another item`, async ({
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
			// Follow the actual product link; do not normalize the URL in the test.
			await expect(
				page.locator('.linker-inquiry-line input.qty')
			).toHaveValue('1');
			await expect(page).toHaveURL(base + request);
			const message = page.locator(
				'.linker-inquiry-form [name="message"]'
			);
			await message.fill('Unsent native-entry check.');
			const quantity = page.locator('.linker-inquiry-line input.qty');
			await quantity.fill('2');
			await quantity.press('Tab');
			await page.locator('.linker-inquiry-update').click();
			await expect(page.locator('.linker-inquiry-update')).toBeDisabled();
			await expect(quantity).toHaveValue('2');
			await page.locator('.linker-inquiry-remove').click();
			await expect(page.locator('.linker-inquiry-line')).toHaveCount(0);
			await page.locator('.restore-item').click();
			await expect(quantity).toHaveValue('2');
			await expect(message).toHaveValue('Unsent native-entry check.');
			await page.reload();
			await expect(page).toHaveURL(base + request);
			await expect(quantity).toHaveValue('2');
			await message.fill('Unsent zero-quantity check.');
			await quantity.fill('0');
			await quantity.press('Enter');
			await expect(page.locator('.linker-inquiry-line')).toHaveCount(0);
			await expect(message).toHaveValue('Unsent zero-quantity check.');
			// No inquiry, account or email is submitted.
		});
	}
}
