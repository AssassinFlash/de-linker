/** Pending customers keep their workspace and the same session when approved. */
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { instance, REPO_ROOT, wp } from '../lib/instance';
import { mark, since } from '../lib/mail';

const fixture = join(REPO_ROOT, 'tests/e2e/fixtures/pending-account.php');
const run = (...args: string[]) => wp(['eval-file', fixture, ...args]);
const read = () => JSON.parse(run('read'));
const output = join(
	REPO_ROOT,
	'.scratch/e2e-shots/pending-account',
	process.env.LINKER_222_RUN ?? 'latest'
);
const password = '222-Browser-Only!2026';

async function shot(page: Page, name: string): Promise<void> {
	await page.evaluate(async () => {
		await document.fonts.ready;
		await Promise.all(
			Array.from(document.images, async (image) => {
				image.loading = 'eager';
				await image.decode().catch(() => undefined);
			})
		);
	});
	expect(
		await page.evaluate(
			() => document.documentElement.scrollWidth <= innerWidth
		),
		'No horizontal overflow'
	).toBe(true);
	await page.screenshot({
		path: join(output, `${name}.png`),
		fullPage: true,
		animations: 'disabled',
	});
}

for (const language of ['en', 'de'] as const) {
	for (const width of [1440, 390]) {
		test(`${language} ${width}: register → pending workspace and inquiry → approve in the same session`, async ({
			browser,
		}) => {
			expect(instance().name).toBe('c222');
			const email = `tester222-${language}-${width}-${Date.now()}@example.test`;
			const base = instance().url;
			const account =
				language === 'de' ? '/de/mein-konto/' : '/my-account/';
			const product =
				language === 'de'
					? '/de/produkt/saj-h2-10k-t3/'
					: '/product/saj-h2-10k-t3/';
			const request =
				language === 'de'
					? '/de/proforma-anfrage/'
					: '/proforma-request/';
			const pending =
				language === 'de'
					? 'Ihr Konto wird geprüft. Preise nach Freigabe.'
					: 'Account under review. Prices after approval.';
			const prefix = `${language}-${width}`;
			mkdirSync(output, { recursive: true });
			run('setup', email);
			const context = await browser.newContext({
				viewport: { width, height: 900 },
				reducedMotion: 'reduce',
			});
			try {
				await context.addInitScript(() =>
					localStorage.setItem(
						'linker-genie-peek-dismissed-until',
						String(Date.now() + 86_400_000)
					)
				);
				const page = await context.newPage();
				await page.goto(base + account + 'register/');
				await page.fill('#billing_company', '222 Browser Solar GmbH');
				await page.selectOption('#linker_customer_role', 'installer');
				await page.selectOption('#billing_country', 'DE');
				await page.fill('#billing_first_name', 'Maria');
				await page.fill('#billing_last_name', 'Beispiel');
				await page.fill('#billing_address_1', 'Teststraße 1');
				await page.fill('#billing_postcode', '39179');
				await page.fill('#billing_city', 'Barleben');
				await page.fill('#reg_email', email);
				await page.fill('#reg_password', password);
				await shot(page, `${prefix}-register`);
				await page.locator('button[name="register"]').focus();
				await page.keyboard.press('Enter');
				await expect(
					page.locator('.linker-account-status')
				).toBeVisible();
				await expect(
					page.locator('.linker-account-main')
				).toBeVisible();
				await expect(
					page.locator('a[href*="action=logout"]').first()
				).toBeAttached();
				const loginCookie = (await context.cookies()).find((cookie) =>
					cookie.name.startsWith('wordpress_logged_in_')
				);
				expect(
					Boolean(loginCookie),
					'Registration establishes a WordPress session'
				).toBe(true);
				const registered = read();
				expect(registered.status).toBe('pending');
				expect(
					registered.mail.some(
						(mail: { to: string[]; subject: string }) =>
							mail.to.includes(email) &&
							/registration|Registrierung/i.test(mail.subject)
					)
				).toBe(true);
				await shot(page, `${prefix}-registered`);

				await page.goto(base + product);
				await expect(page.locator('.pdp-purchase')).toContainText(
					pending
				);
				await expect(
					page.locator('.pdp-purchase .woocommerce-Price-amount')
				).toHaveCount(0);
				await shot(page, `${prefix}-pending-product`);
				await page
					.locator('.pdp-purchase a')
					.filter({
						hasText:
							language === 'de'
								? 'Zum Lösungsentwurf'
								: 'Add to solution draft',
					})
					.click();
				await page.goto(base + request);
				const form = page.locator('form.linker-inquiry-form');
				await expect(form).toBeVisible();
				await form
					.locator('[name="message"]')
					.fill('Please contact me about this product.');
				await form.locator('[name="consent"]').check();
				// PublicGuard's sourced minimum form time is three seconds.
				await page.waitForTimeout(3_100);
				await form.locator('[type="submit"]').click();
				await expect(
					page.locator('.linker-form-success')
				).toBeVisible();
				const inquiry = read();
				expect(inquiry.orders).toHaveLength(1);
				expect(inquiry.orders[0]).toEqual({
					customer: registered.user,
					status: 'inquiry-received',
					items: 1,
				});
				await shot(page, `${prefix}-pending-inquiry`);

				await page.goto(base + account);
				await expect(
					page.locator('.linker-account-status h2')
				).toBeVisible();
				await expect(
					page
						.locator(
							width === 390
								? '.linker-account-bottom-nav'
								: '.linker-account-nav'
						)
						.first()
				).toBeVisible();
				await shot(page, `${prefix}-pending-account`);
				for (const endpoint of [
					'inquiries/',
					'documents/',
					'saved-solutions/',
					'company/',
					'edit-account/',
				]) {
					await page.goto(base + account + endpoint);
					await expect(page).toHaveURL(base + account + endpoint);
					await expect(
						page.locator('.linker-account-status')
					).toBeVisible();
					await expect(page.locator('#username')).toHaveCount(0);
				}

				run('approved');
				await page.goto(base + product);
				await expect(
					page
						.locator('.pdp-purchase .woocommerce-Price-amount')
						.first()
				).toBeVisible();
				await expect(page.locator('.pdp-purchase')).not.toContainText(
					pending
				);
				const approvedCookie = (await context.cookies()).find(
					(cookie) => cookie.name === loginCookie?.name
				);
				expect(
					approvedCookie?.value === loginCookie?.value,
					'Approval preserves the original customer session cookie'
				).toBe(true);
				await shot(page, `${prefix}-approved-product`);
				await page.goto(base + account);
				await expect(
					page.locator('.linker-account-status')
				).toHaveCount(0);
				await shot(page, `${prefix}-approved-account`);
				const approved = read();
				expect(
					approved.mail.some(
						(mail: { to: string[]; subject: string }) =>
							mail.to.includes(email) &&
							/approved|freigegeben/i.test(mail.subject)
					)
				).toBe(true);
				if (language === 'en' && width === 1440) {
					const before = mark();
					run('deliver-one');
					const captured = since(before);
					expect(captured).toHaveLength(1);
					expect(captured[0]?.to).toEqual(['tester222@example.test']);
					expect(captured[0]?.cc).toEqual([]);
					expect(captured[0]?.bcc).toEqual([]);
				}
				const reason =
					language === 'de'
						? 'Bitte ergänzen Sie Ihre Unternehmensdaten.'
						: 'Please complete your company information.';
				run('restricted', reason);
				await page.goto(base + request);
				await expect(
					page.locator('.linker-inquiry-restriction')
				).toContainText(reason);
				await expect(
					page.locator('form.linker-inquiry-form')
				).toBeVisible();
				await shot(page, `${prefix}-restricted-reason`);
				run('rejected', reason);
				await page.goto(base + account);
				await expect(page.locator('#username')).toBeVisible();
				writeFileSync(
					join(output, `${prefix}.json`),
					JSON.stringify(
						{
							language,
							width,
							registered: registered.status,
							inquiry: inquiry.orders,
							approvalPreservedSession: true,
							approved: approved.status,
							mail: approved.mail,
							rejectedSessionEnded: true,
						},
						null,
						2
					)
				);
			} finally {
				await context.close();
				run('cleanup');
			}
		});
	}
}
