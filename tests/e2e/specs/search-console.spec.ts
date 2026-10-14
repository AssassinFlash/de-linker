/**
 * Search Console (docs/specs/145-search-console.md): Site Kit by Google holds
 * the site's Search Console verification, so it stays active. A review
 * instance is never connected to Google; the connection itself is checked on
 * production by `just cutover verify`.
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import { instance } from '../lib/instance';

test('Site Kit by Google is still active', async () => {
	const html = await (await fetch(`${instance().url}/`)).text();
	expect(html, 'Site Kit prints its generator tag').toMatch(
		/<meta name="generator" content="Site Kit by Google /
	);
});
