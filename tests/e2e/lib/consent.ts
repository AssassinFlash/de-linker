/**
 * External dependencies
 */
import type { BrowserContext } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from './instance';

/**
 * Pre-seeds the consent cookies the CookieYes banner reads, so every page load
 * in a fresh test context starts from an answered banner instead of the
 * overlay that covers the Genie dock on phones. The value is the real cookie
 * CookieYes writes on "reject all" (captured 2026-11-08): a bare
 * `consentid:…` does not answer the banner — without `action:yes` the overlay
 * still intercepts pointer events over the dock.
 */
export async function seedConsentCookies(context: BrowserContext): Promise<void> {
	const url = new URL(instance().url);
	await context.addCookies(
		[
			{
				name: 'cookieyes-consent',
				value:
					'consentid:e2e,consent:no,action:yes,necessary:yes,analytics:no,advertisement:no',
			},
			{ name: 'wp_consent_preferences', value: 'deny' },
			{ name: 'wp_consent_statistics', value: 'deny' },
			{ name: 'wp_consent_statistics-anonymous', value: 'deny' },
			{ name: 'wp_consent_functional', value: 'deny' },
			{ name: 'wp_consent_marketing', value: 'deny' },
		].map((cookie) => ({ ...cookie, domain: url.hostname, path: '/' }))
	);
}
