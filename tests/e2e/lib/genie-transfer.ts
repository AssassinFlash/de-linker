import {
	expect,
	test as base,
	type Locator,
	type Page,
} from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { join } from 'node:path';
import {
	applyTurnstileProfile,
	isolateMailBudgets,
	loginLink,
	REPO_ROOT,
	wp,
} from './instance';
import { seedConsentCookies } from './consent';
import { since } from './mail';
import { waitForTurnstile } from './turnstile';

export type Role = 'guest' | 'approved' | 'pending';
export type Transfer = 'contact' | 'inquiry';
interface Record {
	id: number;
	status: string;
	locale: string;
	source: Transfer;
	transfer: string | null;
	summary: boolean;
	lines: { name: string; quantity: number }[];
	message: string;
}
interface Customer {
	email: string;
	read: () => Record[];
	login: (role: Exclude<Role, 'guest'>) => Promise<void>;
	mail: (order: number, sinceMs: number) => Promise<void>;
}

export const test = base.extend<{ customer: Customer }, { officialKeys: void }>(
	{
		officialKeys: [
			async ({}, use) => {
				const restore = applyTurnstileProfile();
				try {
					await use();
				} finally {
					restore();
				}
			},
			{ scope: 'worker', auto: true },
		],
		customer: async ({ page }, use) => {
			const restoreMailBudget = isolateMailBudgets(true);
			const email = `e2e-transfer-${randomUUID()}@example.test`;
			const fixture = (command: string, ...args: string[]) =>
				wp([
					'eval-file',
					join(REPO_ROOT, 'tests/e2e/fixtures/genie-transfer.php'),
					command,
					email,
					...args,
				]).trim();
			const turns = new Set<number>();
			const read = (): Record[] =>
				JSON.parse(fixture('read', String([...turns][0] ?? 0)));
			page.on('response', async (response) => {
				if (
					response.ok() &&
					response.request().method() === 'GET' &&
					/\/genie\/(?:inquiry|contact)(?:\?|$)/.test(response.url())
				) {
					const { source } = await response.json().catch(() => ({}));
					const id = Number(String(source).split(':')[0]);
					if (Number.isSafeInteger(id) && id > 0) turns.add(id);
				}
			});
			await seedConsentCookies(page.context());
			try {
				await use({
					email,
					read,
					login: async (role) => {
						expect(fixture('account', role)).toBe(role);
						await page.goto(
							loginLink(undefined, email.split('@')[0])
						);
					},
					mail: async (id, at) => {
						const customer = new RegExp(
							`^(Your inquiry #|Ihre Anfrage #)${id}\\b`
						);
						const team = new RegExp(`^New inquiry #${id}\\b`);
						await expect
							.poll(
								() => {
									fixture('tick');
									return [
										since(at, customer).length,
										since(at, team).length,
									];
								},
								{ timeout: 90_000, intervals: [3000, 5000] }
							)
							.toEqual([1, 1]);
					},
				});
			} finally {
				try {
					fixture('cleanup', String([...turns][0] ?? 0));
				} finally {
					restoreMailBudget();
				}
			}
		},
	}
);

export async function ask(page: Page, question: string): Promise<void> {
	const answers = page.locator('.linker-genie-app__votes');
	const before = await answers.count();
	await page.locator('#linker-genie-input:visible').fill(question);
	const incoming = page.waitForResponse(
		(r) =>
			r.url().includes('/genie/turn') && r.request().method() === 'POST',
		{ timeout: 120_000 }
	);
	await page.locator('.linker-genie-app__send:visible').click();
	const response = await incoming;
	const result = await response.json();
	expect(
		response.ok(),
		'Genie turn: ' + response.status() + ' ' + (result.code ?? '')
	).toBe(true);
	await expect(answers).toHaveCount(before + 1, { timeout: 120_000 });
}

/** Give the local HTTP workers their configured interval to reload wp-config.php. */
async function waitForProfileReload(): Promise<void> {
	const seconds = Number(
		wp(['eval', "echo (int) ini_get('opcache.revalidate_freq');"])
	);
	await new Promise((resolve) => setTimeout(resolve, (seconds + 1) * 1000));
}

/** A failure from the official always-reject secret, followed by the passing key. */
export async function rejected(
	page: Page,
	card: Locator,
	action: Transfer
): Promise<void> {
	await waitForTurnstile(card);
	const restore = applyTurnstileProfile(undefined, 'fail');
	try {
		await waitForProfileReload();
		const [response] = await Promise.all([
			page.waitForResponse(
				(r) =>
					r.url().includes(`/genie/${action}`) &&
					r.request().method() === 'POST'
			),
			card.locator(`.linker-genie-${action}__send`).click(),
		]);
		expect(response.status()).toBe(400);
		expect((await response.json()).code).toBe('linker_admission_proof');
		expect(
			Boolean(response.request().postDataJSON()['cf-turnstile-response'])
		).toBe(true);
		expect(response.request().headers()['x-wp-nonce']).toBeUndefined();
		await expect(card.getByRole('alert')).toBeVisible();
	} finally {
		restore();
		await waitForProfileReload();
	}
}

/** Drop only the browser's acknowledgement after the native Woo handler succeeded. */
export async function loseAcknowledgement(
	page: Page,
	card: Locator,
	action: Transfer
): Promise<void> {
	const endpoint = new RegExp(`/genie/${action}(?:\\?|$)`);
	await page.route(
		endpoint,
		async (route) => {
			const saved = await route.fetch();
			expect(
				saved.status(),
				'the real submit must commit before its acknowledgement is lost'
			).toBe(200);
			await route.abort('failed');
		},
		{ times: 1 }
	);
	await card.locator(`.linker-genie-${action}__send`).click();
	await expect(card.getByRole('alert')).toBeVisible();
}
