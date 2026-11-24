import { expect, test } from '@playwright/test';
import { instance } from '../lib/instance';

for (const lang of ['en', 'de'] as const) {
	test(`${lang}: workspace labels are spoken without taking up space`, async ({
		page,
	}) => {
		await page.goto(instance().url + (lang === 'de' ? '/de/genie/' : '/genie/'));
		const input = page.locator('#linker-genie-input');
		const label = page.locator('label[for="linker-genie-input"]');
		await expect(input).toHaveAccessibleName(lang === 'de' ? 'Genie fragen' : 'Ask Genie');
		await expect(label).toHaveCSS('clip-path', 'inset(50%)');
		await expect(label).toHaveCSS('position', 'absolute');
		await expect(label).toHaveCSS('width', '1px');
		await expect(input).toBeEnabled();
		await input.focus();
		await expect(input).toBeFocused();
	});
}
