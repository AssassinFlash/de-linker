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
 * overlay that covers the Genie dock on phones. Same cookies as the inline
 * block in specs/account-entries.spec.ts, which introduced the pattern.
 */
export async function seedConsentCookies(context: BrowserContext): Promise<void> {
	const url = new URL(instance().url);
	await context.addCookies(
		[
			{ name: 'cookieyes-consent', value: 'consentid:e2e' },
			{ name: 'wp_consent_preferences', value: 'deny' },
			{ name: 'wp_consent_statistics', value: 'deny' },
			{ name: 'wp_consent_statistics-anonymous', value: 'deny' },
			{ name: 'wp_consent_functional', value: 'deny' },
			{ name: 'wp_consent_marketing', value: 'deny' },
		].map((cookie) => ({ ...cookie, domain: url.hostname, path: '/' }))
	);
}
