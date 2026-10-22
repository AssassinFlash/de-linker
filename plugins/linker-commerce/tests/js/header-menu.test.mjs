/** Native disclosure keyboard behavior; opening makes links visible immediately. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';

const require = createRequire( import.meta.url );
const { JSDOM } = require( '../../../linker-tools/node_modules/jsdom' );

const source = readFileSync( new URL( '../../assets/header-menu.js', import.meta.url ), 'utf8' );

function page() {
	const dom = new JSDOM( `<!doctype html><html lang="en"><body>
		<header id="tv-header-v2">
			<nav class="tv-desktop-nav">
				<div class="tv-nav-item" data-tv-nav-primary="products">
					<button class="tv-nav-link" aria-expanded="false">Products</button>
					<div class="tv-mega-menu" role="menu">
						<a href="/products/a/">A</a>
						<a href="/products/b/">B</a>
					</div>
				</div>
			</nav>
		</header>
	</body></html>`, { runScripts: 'outside-only', pretendToBeVisual: true } );
	const { window } = dom;
	window.eval( source );
	const button = window.document.querySelector( '.tv-nav-link' );
	const menu = window.document.querySelector( '.tv-mega-menu' );
	const first = window.document.querySelector( 'a' );
	button.focus();
	return { window, button, menu, first };
}

function arrow( window, target ) {
	target.dispatchEvent( new window.KeyboardEvent( 'keydown', { key: 'ArrowDown', bubbles: true, cancelable: true } ) );
}

test( 'the first ArrowDown opens the mega menu and focuses its first link', () => {
	const { window, button, first } = page();
	arrow( window, button );
	assert.equal( button.getAttribute( 'aria-expanded' ), 'true' );
	assert.equal( window.document.activeElement, first );
} );

test( 'ArrowUp opens a closed menu at its last link', () => {
	const { window, button, menu } = page();
	button.dispatchEvent( new window.KeyboardEvent( 'keydown', { key: 'ArrowUp', bubbles: true, cancelable: true } ) );
	assert.equal( button.getAttribute( 'aria-expanded' ), 'true' );
	assert.equal( window.document.activeElement, menu.querySelectorAll( 'a' )[ 1 ] );
} );

test( 'a later ArrowDown keeps the next keyboard selection', () => {
	const { window, button, menu, first } = page();
	arrow( window, button );
	arrow( window, first );
	assert.equal( window.document.activeElement, menu.querySelectorAll( 'a' )[ 1 ] );
} );

test( 'Escape closes the menu and returns focus to its disclosure', () => {
	const { window, button } = page();
	arrow( window, button );
	window.document.activeElement.dispatchEvent( new window.KeyboardEvent( 'keydown', { key: 'Escape', bubbles: true } ) );
	assert.equal( button.getAttribute( 'aria-expanded' ), 'false' );
	assert.equal( window.document.activeElement, button );
} );

test( 'Home and End move to the first and last menu links', () => {
	const { window, button, menu, first } = page();
	button.dispatchEvent( new window.KeyboardEvent( 'keydown', { key: 'End', bubbles: true, cancelable: true } ) );
	assert.equal( window.document.activeElement, menu.querySelectorAll( 'a' )[ 1 ] );
	window.document.activeElement.dispatchEvent( new window.KeyboardEvent( 'keydown', { key: 'Home', bubbles: true, cancelable: true } ) );
	assert.equal( window.document.activeElement, first );
} );

test( 'an account menu served without hidden is closed on load', () => {
	const dom = new JSDOM( `<!doctype html><html lang="en"><body>
		<header id="tv-header-v2">
			<div class="tv-b2b-acct">
				<button class="tv-b2b-acct-btn" aria-haspopup="true" aria-expanded="false">Sign in</button>
				<div class="tv-b2b-acct-menu"><a href="/my-account/">My account</a></div>
			</div>
		</header>
	</body></html>`, { runScripts: 'outside-only', pretendToBeVisual: true } );
	const { window } = dom;
	window.eval( source );
	const button = window.document.querySelector( '.tv-b2b-acct-btn' );
	const menu = window.document.querySelector( '.tv-b2b-acct-menu' );
	assert.equal( button.getAttribute( 'aria-expanded' ), 'false' );
	assert.equal( menu.hidden, true );
	assert.equal( menu.id, 'linker-menu-account' );
	assert.equal( button.getAttribute( 'aria-controls' ), menu.id );
} );

function mobilePage( open = false ) {
	const dom = new JSDOM( `<!doctype html><html lang="en"><body>
		<header id="tv-header-v2">
			<details class="tv-mobile-navigation" ${ open ? 'open' : '' }>
				<summary id="tv-mobile-toggle" role="button" aria-controls="tv-mobile-panel" aria-label="Open menu">Menu</summary>
				<div id="tv-mobile-panel"><a href="/products/">Products</a></div>
			</details>
		</header><button id="outside">Outside</button>
	</body></html>`, { runScripts: 'outside-only', pretendToBeVisual: true } );
	const { window } = dom;
	window.eval( source );
	return {
		window,
		details: window.document.querySelector( 'details' ),
		toggle: window.document.querySelector( 'summary' ),
		panel: window.document.querySelector( '#tv-mobile-panel' ),
	};
}

test( 'an opening made before the enhancement is retained', () => {
	const { details, toggle, panel } = mobilePage( true );
	assert.equal( details.open, true );
	assert.equal( panel.dataset.open, 'true' );
	assert.equal( toggle.getAttribute( 'aria-label' ), 'Close menu' );
	assert.equal( toggle.hasAttribute( 'aria-expanded' ), false );
	assert.equal( toggle.getAttribute( 'aria-controls' ), panel.id );
} );

test( 'native summary activation is not toggled twice by the enhancement', async () => {
	const { window, details, toggle, panel } = mobilePage();
	toggle.click();
	await new Promise( resolve => window.setTimeout( resolve, 0 ) );
	assert.equal( details.open, true );
	assert.equal( panel.dataset.open, 'true' );
	toggle.click();
	await new Promise( resolve => window.setTimeout( resolve, 0 ) );
	assert.equal( details.open, false );
	assert.equal( panel.dataset.open, 'false' );
} );

test( 'Escape closes the actual native disclosure and returns focus', () => {
	const { window, details, toggle, panel } = mobilePage( true );
	panel.querySelector( 'a' ).focus();
	window.document.activeElement.dispatchEvent( new window.KeyboardEvent( 'keydown', { key: 'Escape', bubbles: true } ) );
	assert.equal( details.open, false );
	assert.equal( panel.dataset.open, 'false' );
	assert.equal( window.document.activeElement, toggle );
} );

test( 'an outside click closes native open state as well as the CSS state', () => {
	const { window, details, panel } = mobilePage( true );
	window.document.querySelector( '#outside' ).click();
	assert.equal( details.open, false );
	assert.equal( panel.dataset.open, 'false' );
} );
