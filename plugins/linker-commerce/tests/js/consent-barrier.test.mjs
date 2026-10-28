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

test('late CookieYes preferences receive focus and return to their real opener', async () => {
	const window = page('<button class="cky-banner-element">Cookie-Einstellungen</button>');
	await new Promise((resolve) => window.document.addEventListener('DOMContentLoaded', resolve, { once: true }));
	const opener = window.document.querySelector('button');
	// CookieYes inserts its modal after loading configuration. Its native
	// revisit handler toggles this class but does not move or retain focus.
	window.document.body.insertAdjacentHTML('beforeend', `
		<div class="cky-modal"><section id="ckyPreferenceCenter" aria-label="Customise Consent Preferences">
			<h2 data-cky-tag="detail-title">Ihre Cookie-Auswahl</h2>
			<button data-cky-tag="detail-close">Schließen</button>
			<input type="checkbox" checked>
		</section></div>`);
	const modal = window.document.querySelector('.cky-modal');
	const panel = window.document.querySelector('#ckyPreferenceCenter');
	const close = panel.querySelector('button');
	close.addEventListener('click', () => modal.classList.remove('cky-modal-open'));
	await new Promise(window.queueMicrotask);
	opener.focus();
	modal.classList.add('cky-modal-open');
	await new Promise(window.queueMicrotask);
	assert.equal(panel.ownerDocument.activeElement, close);
	assert.equal(panel.getAttribute('aria-labelledby'), panel.querySelector('h2').id);
	close.click();
	await new Promise(window.queueMicrotask);
	assert.equal(panel.ownerDocument.activeElement, opener);

	// Native CookieYes transitions visibility: the first focus attempt can
	// occur while the opening panel is still hidden.
	const focus = close.focus.bind(close);
	let starting = true;
	close.focus = () => {
		if (!starting) {
			focus();
		}
	};
	modal.classList.add('cky-modal-open');
	await new Promise(window.queueMicrotask);
	assert.equal(panel.ownerDocument.activeElement, opener);
	starting = false;
	modal.dispatchEvent(new window.Event('transitionstart', { bubbles: true }));
	assert.equal(panel.ownerDocument.activeElement, close);
	close.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
	await new Promise(window.queueMicrotask);
	assert.equal(modal.classList.contains('cky-modal-open'), false);
	assert.equal(panel.ownerDocument.activeElement, opener);
	assert.equal(panel.querySelector('input').checked, true);
	assert.equal(window.__reloads, 0);
});
