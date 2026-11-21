import { expect, type Locator, type Page } from '@playwright/test';

/** The provider puts its signed response in the native form field. */
export async function waitForTurnstile(form: Locator): Promise<void> {
	await expect(form.locator('input[name="cf-turnstile-response"]')).toHaveValue(/\S/, { timeout: 60_000 });
}

/** Observe third-party traffic before navigating or opening a Genie transfer. */
export function challengeRequests(page: Page): string[] {
	const requests: string[] = [];
	page.on('request', (request) => {
		const url = new URL(request.url());
		if (url.hostname === 'challenges.cloudflare.com') requests.push(url.pathname);
	});
	return requests;
}
