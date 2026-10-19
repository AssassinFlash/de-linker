/**
 * The pre-consent barrier's browser half. CookieYes releases a held tag after
 * analytics consent; this script re-blocks on withdrawal. location.reload is
 * read-only in jsdom, so the test rewrites that one call before evaluating
 * the file it still requires to contain.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';

const require = createRequire(import.meta.url);
const { JSDOM } = require('../../../linker-tools/node_modules/jsdom');
const source = readFileSync(new URL('../../assets/consent.js', import.meta.url), 'utf8');

function page(html) {
	assert.match(source, /location\.reload\(\)/);
	const dom = new JSDOM(html, {
		url: 'http://linker.test/',
		runScripts: 'outside-only',
	});
	const { window } = dom;
	window.linkerConsentMeasurementID = 'G-TEST201123';
	window.__reloads = 0;
	window.eval(source.replace('location.reload()', 'window.__reloads += 1'));
	return window;
}

function consent(window, detail) {
	window.document.dispatchEvent(
		new window.CustomEvent('wp_listen_for_consent_change', { detail })
	);
}

test('analytics consent releases the disable flag and does not reload', () => {
	const window = page(
		'<script id="google_gtagjs-js" type="text/plain" data-cookieyes="cookieyes-analytics" src="https://www.googletagmanager.com/gtag/js?id=G-TEST201123"></script>'
	);
	window.document.cookie = '_ga=GA1.1.fixture';

	consent(window, { statistics: 'allow' });

	assert.equal(window['ga-disable-G-TEST201123'], false);
	assert.equal(window.__reloads, 0);
	assert.match(window.document.cookie, /_ga=/);
	assert.equal(
		window.document.querySelector('script').getAttribute('type'),
		'text/plain'
	);
});

test('withdrawing analytics re-blocks, clears measurement cookies, and reloads a live tag', () => {
	const window = page(
		'<script id="google_gtagjs-js" src="https://www.googletagmanager.com/gtag/js?id=G-TEST201123"></script>'
	);
	consent(window, { statistics: 'allow' });
	window.document.cookie = '_ga=GA1.1.fixture';

	consent(window, { statistics: 'deny' });

	assert.equal(window['ga-disable-G-TEST201123'], true);
	assert.equal(window.document.cookie.includes('_ga='), false);
	assert.equal(window.__reloads, 1);
});

test('a held placeholder is not reloaded when analytics is withdrawn', () => {
	const window = page(
		'<script id="google_gtagjs-js" type="text/plain" src="https://www.googletagmanager.com/gtag/js?id=G-TEST201123"></script>'
	);

	consent(window, { statistics: 'deny' });

	assert.equal(window['ga-disable-G-TEST201123'], true);
	assert.equal(window.__reloads, 0);
});

test('withdrawing marketing only leaves analytics denied', () => {
	const window = page(
		'<script id="google_gtagjs-js" type="text/plain" src="https://www.googletagmanager.com/gtag/js?id=G-TEST201123"></script>'
	);
	window.document.cookie = '_ga=GA1.1.fixture; sbjs_current=utm';

	consent(window, { marketing: 'deny' });

	assert.equal(window['ga-disable-G-TEST201123'], undefined);
	assert.equal(window.__reloads, 0);
	assert.match(window.document.cookie, /_ga=/);
});
