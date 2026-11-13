/**
 * The language switch keeps the section the visitor is reading.
 *
 * The server builds every language link from the request; a fragment never
 * travels with it, so the account chain's own sections (`#step-2`,
 * `#reset-card`) were dropped on the way to the other language. The rule is
 * narrow on purpose: carry the hash only when this page actually has that
 * element, and never for a link that opens its own window.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';

const require = createRequire(import.meta.url);
const { JSDOM } = require('../../../linker-tools/node_modules/jsdom');
const source = readFileSync(
	new URL('../../assets/language-hash.js', import.meta.url),
	'utf8'
);

function page(url, html) {
	const dom = new JSDOM(html, { url, runScripts: 'outside-only' });
	dom.window.eval(source);
	return dom.window;
}

function switchTo(window, index = 0) {
	const link = window.document.querySelectorAll(
		'a[data-linker-language-choice]'
	)[index];
	link.dispatchEvent(
		new window.MouseEvent('click', { bubbles: true, cancelable: true })
	);
	return link;
}

const LINKS =
	'<div id="step-2"></div><div id="reset-card"></div>' +
	'<a data-linker-language-choice="de" href="/de/mein-konto/registrieren/">DE</a>' +
	'<a data-linker-language-choice="en" href="/de/mein-konto/registrieren/" target="_blank">EN</a>';

test('an existing section travels with the switch', () => {
	const window = page(
		'http://linker.test/my-account/register/#step-2',
		LINKS
	);
	assert.equal(
		switchTo(window).href,
		'http://linker.test/de/mein-konto/registrieren/#step-2'
	);
});

test('a hash with no element behind it is not carried', () => {
	const window = page(
		'http://linker.test/my-account/register/#step-9',
		LINKS
	);
	assert.equal(
		switchTo(window).href,
		'http://linker.test/de/mein-konto/registrieren/'
	);
});

test('no hash leaves the server destination alone', () => {
	const window = page('http://linker.test/my-account/register/', LINKS);
	assert.equal(
		switchTo(window).href,
		'http://linker.test/de/mein-konto/registrieren/'
	);
});

test('a link that opens its own window keeps its destination', () => {
	const window = page(
		'http://linker.test/my-account/register/#step-2',
		LINKS
	);
	assert.equal(
		switchTo(window, 1).href,
		'http://linker.test/de/mein-konto/registrieren/'
	);
});
