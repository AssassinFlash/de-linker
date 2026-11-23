/** The mobile assistant opens in place without covering the public form. */
import { expect, test } from '@playwright/test';
import { seedConsentCookies } from '../lib/consent';
import { instance } from '../lib/instance';

const routes = {
	en: ['/contact/', '/my-account/register/', '/proforma-request/'],
	de: [
		'/de/kontakt/',
		'/de/mein-konto/registrieren/',
		'/de/proforma-anfrage/',
	],
};

for (const [language, forms] of Object.entries(routes)) {
	for (const route of forms) {
		test(
			language + ' mobile assistant keeps the form open on ' + route,
			async ({ context, page }) => {
				await seedConsentCookies(context);
				await page.setViewportSize({ width: 390, height: 844 });
				await page.goto(instance().url + route);
				const opener = page.locator('a.linker-form-assistant');
				await expect(opener).toBeVisible();
				await expect(page.locator('.linker-genie-open')).toBeHidden();
				const name = page
					.locator(
						'#linker-contact-name, #billing_company, #inquiry-name'
					)
					.first();
				await name.fill('Browser visual check');
				await opener.click();
				await expect(page.locator('.linker-genie-panel')).toBeVisible();
				await expect(opener).toHaveAttribute('aria-expanded', 'true');
				await expect(
					page.locator('.linker-genie-app__composer')
				).toBeVisible();
				await page.keyboard.press('Escape');
				await expect(page.locator('.linker-genie-panel')).toBeHidden();
				await expect(name).toHaveValue('Browser visual check');
				await expect(page).toHaveURL(instance().url + route);
			}
		);
	}
}
