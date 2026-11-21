import { expect, test, type Locator, type Page } from '@playwright/test';

/** The provider puts its signed response in the native form field. */
export async function waitForTurnstile(form: Locator): Promise<void> {
	const response = form.locator('input[name="cf-turnstile-response"]');
	const retry = form
		.locator('[role="status"]:visible + button:visible')
		.filter({
			hasText: /^(Try again|Erneut versuchen)$/,
		});
	await expect
		.poll(
			async () =>
				Boolean(
					(await response.count()) &&
					(await response.first().inputValue())
				) || (await retry.isVisible()),
			{ timeout: 60_000 }
		)
		.toBe(true);
	if (await retry.isVisible()) {
		test.info().annotations.push({
			type: 'widget retry',
			description:
				'Used the displayed retry after the provider reported a loading error.',
		});
		await retry.click();
	}
	await expect(response).toHaveValue(/\S/, { timeout: 60_000 });
}

/** Observe third-party traffic before navigating or opening a Genie transfer. */
export function challengeRequests(page: Page): string[] {
	const requests: string[] = [];
	page.on('request', (request) => {
		const url = new URL(request.url());
		if (url.hostname === 'challenges.cloudflare.com')
			requests.push(url.pathname);
	});
	return requests;
}
