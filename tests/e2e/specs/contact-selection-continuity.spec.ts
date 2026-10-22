/** Native archive invitation → Contact inclusion state; no submit, mail, model or mocked consumer. */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { instance, REPO_ROOT } from '../lib/instance';

const run =
	process.env.LINKER_CONTACT_RUN_ID ??
	new Date().toISOString().replaceAll(/[-:.]/g, '');
const output = join(
	REPO_ROOT,
	'docs/acceptance/2026-10-22/full-site/product-selection-continuity/browser',
	run
);
const paths = { en: '/products/', de: '/de/produkte/' };

async function capture(page: Page, name: string) {
	const data = await page
		.locator('.linker-contact-selection')
		.evaluate((field) => {
			const label = field.querySelector('label')!;
			const checkbox = field.querySelector<HTMLInputElement>(
				'input[type="checkbox"]'
			)!;
			const summary = field.querySelector(
				'.linker-contact-selection__summary'
			)!;
			const excluded = field.querySelector(
				'.linker-contact-selection__excluded'
			)!;
			return {
				url: location.href,
				collectedAt: new Date().toISOString(),
				viewport: { width: innerWidth, height: innerHeight },
				field: field.getBoundingClientRect().toJSON(),
				label: label.getBoundingClientRect().toJSON(),
				included: checkbox.checked,
				summaryDisplay: getComputedStyle(summary).display,
				excludedDisplay: getComputedStyle(excluded).display,
				text: field.textContent,
			};
		});
	mkdirSync(output, { recursive: true });
	writeFileSync(join(output, `${name}.json`), JSON.stringify(data, null, 2));
	await page
		.locator('form.linker-contact-form')
		.screenshot({ path: join(output, `${name}.png`) });
	expect(data.label.height).toBeGreaterThanOrEqual(44);
	expect(data.field.x).toBeGreaterThanOrEqual(0);
	expect(data.field.right).toBeLessThanOrEqual(data.viewport.width);
	return data;
}

for (const locale of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${locale} ${width}: actual selected archive context can be excluded without changing the question`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 1000 });
			const base = instance().url;
			await page.goto(
				`${base}${paths[locale]}?q=owned-no-match-SAJ&brand=saj&phase=3&kw_min=5.5&sort=name`
			);
			const reject = page.getByRole('button', {
				name: /^(Reject all|Alle ablehnen)$/,
			});
			if (await reject.isVisible()) await reject.click();
			const invitation = page.locator(
				'.linker-contact-products a.linker-contact-primary'
			);
			const href = await invitation.getAttribute('href');
			expect(href).toBeTruthy();
			const transport = JSON.parse(
				new URL(href!, base).searchParams.get(
					'linker_contact_selection'
				)!
			);
			expect(transport.selection).toEqual({
				brand: 'saj',
				phase: '3',
				kw_min: 5.5,
				q: 'owned-no-match-SAJ',
				sort: 'name',
			});
			await invitation.click();
			const field = page.locator('.linker-contact-selection');
			await expect(field).toBeVisible();
			await expect(
				field.locator('.linker-contact-selection__summary')
			).toContainText('owned-no-match-SAJ');
			const question = page.locator('textarea[name="message"]');
			await expect(question).toHaveValue('');
			await expect(page.locator('select[name="intent"]')).toHaveValue(
				'product'
			);
			await question.fill(
				'My own question. / Meine eigene Frage. \\ unchanged'
			);
			const checkbox = field.getByRole('checkbox');
			await expect(checkbox).toBeChecked();
			const includedData = await page
				.locator('form.linker-contact-form')
				.evaluate((form) =>
					Array.from(new FormData(form as HTMLFormElement).entries())
				);
			expect(
				includedData.some(([key]) => key === 'linker_contact_selection')
			).toBe(true);
			const included = await capture(page, `${locale}-${width}-included`);
			expect(included.summaryDisplay).not.toBe('none');
			expect(included.excludedDisplay).toBe('none');
			await checkbox.focus();
			await checkbox.press('Space');
			await expect(checkbox).not.toBeChecked();
			await expect(
				field.locator('.linker-contact-selection__summary')
			).toBeHidden();
			await expect(
				field.locator('.linker-contact-selection__excluded')
			).toHaveText(
				locale === 'de'
					? 'Diese Auswahl wird nicht mitgesendet.'
					: 'This selection will not be sent.'
			);
			await expect(question).toHaveValue(
				'My own question. / Meine eigene Frage. \\ unchanged'
			);
			const excludedData = await page
				.locator('form.linker-contact-form')
				.evaluate((form) =>
					Array.from(new FormData(form as HTMLFormElement).entries())
				);
			expect(
				excludedData.some(([key]) => key === 'linker_contact_selection')
			).toBe(false);
			expect(JSON.stringify(excludedData)).not.toContain(
				'owned-no-match-SAJ'
			);
			await capture(page, `${locale}-${width}-excluded`);
		});

		test(`${locale} ${width}: invalid source stays an explicit exclusion decision`, async ({
			page,
		}) => {
			await page.setViewportSize({ width, height: 1000 });
			const path = locale === 'de' ? '/de/kontakt/' : '/contact/';
			const query = new URLSearchParams({
				intent: 'product',
				linker_contact_selection: JSON.stringify({
					source: 'https://foreign.invalid/products/',
					selection: { q: 'not a trusted source' },
				}),
			});
			await page.goto(`${instance().url}${path}?${query}`);
			const reject = page.getByRole('button', {
				name: /^(Reject all|Alle ablehnen)$/,
			});
			if (await reject.isVisible()) await reject.click();
			const field = page.locator('.linker-contact-selection');
			await expect(
				field.locator(
					'.linker-contact-selection__summary [role="status"]'
				)
			).toBeVisible();
			await expect(field.locator('a')).toHaveCount(0);
			await capture(page, `${locale}-${width}-unavailable`);
			await field.getByRole('checkbox').uncheck();
			await expect(
				field.locator('.linker-contact-selection__excluded')
			).toBeVisible();
			await expect(page.locator('textarea[name="message"]')).toHaveValue(
				''
			);
			await capture(page, `${locale}-${width}-unavailable-excluded`);
		});
	}
}
