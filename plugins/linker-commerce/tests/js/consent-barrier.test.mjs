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

function page(html, options = {}) {
	assert.match(source, /location\.reload\(\)/);
	const dom = new JSDOM(html, {
		url: 'http://linker.test/',
		runScripts: 'outside-only',
		...options,
	});
	const { window } = dom;
	window.linkerConsentMeasurementID = 'G-TEST201123';
	window.__reloads = 0;
	window.calls = [];
	window.gtag = (...args) => window.calls.push(args);
	window.eval(source.replace('location.reload()', 'window.__reloads += 1'));
	return window;
}

function consent(window, detail) {
	window.document.dispatchEvent(
		new window.CustomEvent('wp_listen_for_consent_change', { detail })
	);
}

test('analytics consent releases the tag once and does not reload', () => {
	const window = page(
		'<script id="google_gtagjs-js" type="text/plain" data-cookieyes="cookieyes-analytics" src="https://www.googletagmanager.com/gtag/js?id=G-TEST201123"></script>'
	);
	window.document.cookie = '_ga=GA1.1.fixture';

	consent(window, { statistics: 'allow' });

	assert.equal(window['ga-disable-G-TEST201123'], false);
	assert.equal(window.__reloads, 0);
	assert.match(window.document.cookie, /_ga=/);
	assert.equal(
		window.document.querySelector('script').dataset.linkerGtagReleased,
		'1'
	);
});

const held = '<script type="text/plain" src="https://www.googletagmanager.com/gtag/js?id=GT-TAG"></script>';

test('a returning consented visit releases one live tag on the next page', async () => {
	const window = page(held);
	window.document.cookie = 'cookieyes-consent=action:yes,analytics:yes,advertisement:no';
	await new Promise((done) => window.document.addEventListener('DOMContentLoaded', done));
	window.document.dispatchEvent(new window.Event('cookieyes_consent_update'));
	consent(window, {statistics: 'allow'});
	assert.equal(window.document.scripts.length, 1);
	assert.equal(window.document.scripts[0].type, '');
	assert.equal(window.document.scripts[0].async, true);
	assert.equal(window.document.scripts[0].dataset.linkerGtagReleased, '1');
	assert.equal(window['ga-disable-G-TEST201123'], false);
});

test('a first or rejected visit leaves the Google script inert', async () => {
	for (const cookie of ['', 'cookieyes-consent=action:yes,analytics:no']) {
		const window = page(held);
		if (cookie) window.document.cookie = cookie;
		await new Promise((done) => window.document.addEventListener('DOMContentLoaded', done));
		window.document.dispatchEvent(new window.Event('cookieyes_consent_update'));
		assert.equal(window.document.scripts.length, 1);
		assert.equal(window.document.scripts[0].type, 'text/plain');
	}
});

test('conversion events send only the approved fields and page language after permission', () => {
	const window = page('<html lang="de-DE">' + held);
	const params = { lead_surface: 'inquiry', email: 'someone@example.invalid', message: 'private note' };
	window.linkerTrack('generate_lead', params);
	assert.equal(window.calls.filter(call => call[0] === 'event').length, 0);
	consent(window, { statistics: 'allow' });
	window.linkerTrack('generate_lead', params);
	window.linkerTrack('someone@example.invalid', params);
	assert.deepEqual(JSON.parse(JSON.stringify(window.calls.filter(call => call[0] === 'event'))), [
		['event', 'generate_lead', {page_lang: 'de', lead_surface: 'inquiry'}]
	]);
	consent(window, {statistics: 'deny'});
	window.linkerTrack('configurator_start');
	assert.equal(window.calls.filter(call => call[0] === 'event').length, 1);
});

test('GA attribution preserves campaign tags and excludes private receipt, search and referral values', () => {
	const window = page(held, {
		url: 'https://linker.test/contact/?contact_order=wc_order_secret&utm_source=partner#private',
		referrer: 'https://linker.test/?s=someone@example.invalid',
	});
	const config = window.calls.find(call => call[0] === 'set')[1];
	assert.equal(config.page_location, 'https://linker.test/contact/?utm_source=partner');
	assert.equal(config.page_referrer, 'https://linker.test/search/');
});

test('search terms never reach GA page titles, locations, or the following page referrer', () => {
	for (const prefix of ['/', '/de/']) {
		const base = 'https://linker.test' + prefix;
		for (const search of [base + 'search/private%40example.invalid/', base + '?s=private%40example.invalid']) {
			const url = new URL(search);
			url.searchParams.set('utm_source', 'partner');
			const results = page('<title>Search results for private@example.invalid</title>' + held, { url: url.href });
			const config = results.calls.find(call => call[0] === 'set')[1];
			assert.equal(config.page_location, base + 'search/?utm_source=partner');
			assert.equal(config.page_title, 'Search');

			const next = page(held, { url: base + 'products/', referrer: url.href });
			assert.equal(next.calls.find(call => call[0] === 'set')[1].page_referrer, base + 'search/');
		}
	}
});

test('Woo account-claim and password-reset parameters stay out of GA location and referrer', () => {
	for (const path of [
		'/my-account/register/?linker_inquiry=17&linker_key=wc_order_private',
		'/my-account/lost-password/?key=private&login=private%40example.invalid',
	]) {
		const url = new URL(path, 'https://linker.test');
		const window = page(held, { url: url.href, referrer: url.href });
		const config = window.calls.find(call => call[0] === 'set')[1];
		assert.equal(config.page_location, url.origin + url.pathname);
		assert.equal(config.page_referrer, url.origin + url.pathname);
	}
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
