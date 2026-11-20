import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, type Browser, type Page } from '@playwright/test';
import { instance, loginLink, REPO_ROOT, wp } from './instance';
import { since, type Message } from './mail';

export const fixture = (...args: string[]) =>
	wp([
		'eval-file',
		join(REPO_ROOT, 'tests/e2e/fixtures/known-project-quotation.php'),
		...args,
	]);
export type Inquiry = {
	id: number;
	number: string;
	locale: string;
	owner: number;
	status: string;
	lines: number;
	note: string;
	project: string;
	quote: string;
	edit_url: string;
};
export const inquiry = (email: string): Inquiry =>
	JSON.parse(fixture('order', email));

export async function customerMail(
	started: number,
	email: string,
	match: (message: Message) => boolean,
	deliver?: 'quotation' | 'receipt'
) {
	let found: Message | undefined;
	await expect
		.poll(
			() => {
				found = since(started).find(
					(m) => m.to.includes(email) && match(m)
				);
				if (!found && deliver) fixture('deliver', email, deliver);
				return Boolean(found);
			},
			{
				message: 'the isolated mailbox received the requested message',
				timeout: 180_000,
				intervals: [1000, 2500, 5000],
			}
		)
		.toBe(true);
	return found!;
}

// Open the button from the received HTML in this customer's browser context.
export async function mailButton(
	page: Page,
	message: Message,
	name: RegExp
): Promise<string> {
	const html = message.html;
	expect(Boolean(html)).toBe(true);
	const mailbox = await page.context().newPage();
	try {
		await mailbox.route('**/*', (route) => route.abort());
		await mailbox.setContent(html);
		const href = await mailbox
			.getByRole('link', { name })
			.getAttribute('href');
		const url = new URL(href!);
		expect(url.origin).toBe(instance().url);
		return url.href;
	} finally {
		await mailbox.close();
	}
}

export async function salesIssue(
	browser: Browser,
	order: Inquiry,
	email: string
) {
	const context = await browser.newContext();
	try {
		const sales = await context.newPage();
		sales.setDefaultTimeout(20_000);
		const staff = wp([
			'user',
			'list',
			'--role=administrator',
			'--field=user_login',
		])
			.trim()
			.split('\n')
			.at(-1)!
			.trim();
		await sales.goto(loginLink(undefined, staff));
		await sales.goto(order.edit_url);
		const sku = 'DLK-SAJ-B250HV1';
		await sales.locator('button.add-line-item').click();
		await sales.locator('button.add-order-item').click();
		const dialog = sales.locator('.wc-backbone-modal-add-products');
		await sales.locator('.select2-search__field:visible').fill(sku);
		await sales
			.locator('.select2-results__option[aria-selected]')
			.filter({ hasText: sku })
			.first()
			.click();
		await dialog.locator('[name=item_qty]').first().fill('1');
		await dialog.locator('#btn-ok').click();
		await expect(sales.locator('#order_line_items tr.item')).toContainText(
			'B2-5.0-HV1'
		);
		await sales.reload(); // Woo saved the product through its own order-item action.
		const issued = sales.locator('#linker-quotation');
		await issued.locator('button[name=linker_issue_quotation]').click();
		await expect(issued.locator('strong')).toHaveText(/DLK-QT-\d{4}-\d+/);
		const number = (await issued.locator('strong').innerText()).trim();
		expect(inquiry(email)).toMatchObject({
			id: order.id,
			quote: number,
			status: 'quotation-issued',
			project: order.project,
		});
		return number;
	} finally {
		await context.close();
	}
}

export async function signIn(page: Page, email: string, password: string) {
	await page.locator('input#username').fill(email);
	await page.locator('input#password').fill(password);
	await page.locator('button[name=login]').click();
}

export async function recoverPassword(
	page: Page,
	email: string,
	password: string,
	actions: string[]
) {
	const lost = page.locator('[href="#linker-auth-reset"]');
	await lost.click();
	actions.push('Open password recovery');
	const reset = page
		.locator('form')
		.filter({ has: page.locator('input[name=wc_reset_password]') });
	await reset.getByRole('textbox').fill(email);
	const start = Date.now();
	await reset
		.getByRole('button', {
			name: /send reset link|link zum zurücksetzen senden/i,
		})
		.click();
	actions.push('Request a reset email');
	const message = await customerMail(start, email, (m) =>
		/[?&](?:amp;)?key=/.test(m.html)
	);
	const url = new URL(
		await mailButton(page, message, /reset|passwort|password|zurücksetzen/i)
	);
	expect(url.searchParams.has('redirect_to')).toBe(false);
	await page.goto(url.href);
	actions.push('Open the reset email link in the same browser');
	await page.locator('#password_1').fill(password);
	await page.locator('#password_2').fill(password);
	await page
		.locator('form')
		.filter({ has: page.locator('#password_1') })
		.getByRole('button', {
			name: /set new password|neues passwort speichern/i,
		})
		.click();
	actions.push('Set the new password');
	await signIn(page, email, password);
	actions.push('Sign in with the new password');
}

export async function register(page: Page, email: string, password: string) {
	const form = page.locator('form[data-linker-register]');
	await form
		.locator('[name=billing_company]')
		.pressSequentially('Konstanz Solar Review', { delay: 70 });
	await form.locator('[name=billing_country]').selectOption('DE');
	await form.locator('#linker_customer_role_installer').check();
	await form
		.locator('[name=linker_company_website]')
		.fill('https://example.test');
	await form.locator('[data-next]').click();
	await form.locator('[name=billing_first_name]').fill('Konstanz');
	await form.locator('[name=billing_last_name]').fill('Review');
	await form.locator('[name=email]').fill(email);
	await form.locator('[name=password]').fill(password);
	await expect(form.locator('[name=register]')).toBeEnabled();
	await form.locator('[name=register]').click();
	await expect(
		form,
		'the native registration opens the customer account'
	).toHaveCount(0);
}

export const quotationLink = (page: Page) =>
	page.locator('main a[href*="linker-document=quotation"]');
export async function downloadQuotation(
	page: Page,
	order: Inquiry,
	number: string
) {
	const link = quotationLink(page).first();
	expect(
		new URL(
			(await link.getAttribute('href'))!,
			page.url()
		).searchParams.get('id')
	).toBe(String(order.id));
	const result = page.waitForEvent('download');
	await link.click();
	const download = await result;
	expect(download.suggestedFilename()).toBe(number + '.pdf');
	const path = (await download.path())!;
	const bytes = readFileSync(path);
	expect(bytes.subarray(0, 5).toString()).toBe('%PDF-');
	const text = execFileSync('pdftotext', ['-layout', path, '-'], {
		encoding: 'utf8',
	});
	expect(text).toContain(number);
	expect(text).toContain(order.number);
	expect(text).toContain('B2-5.0-HV1');
	await download.delete();
	return { filename: download.suggestedFilename(), bytes: bytes.length };
}
