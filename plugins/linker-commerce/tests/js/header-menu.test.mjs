/**
 * Behavior of assets/header-menu.js.
 *
 * The mega menu fades in on a visibility transition. Focusing a link in the
 * same turn as the first open is dropped. The first ArrowDown waits for
 * transitionend (property visibility) and keeps a 250ms fallback. A later
 * arrow, on a menu that is already open, focuses immediately.
 */
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
	const queued = [];
	window.setTimeout = ( fn, ms ) => {
		queued.push( { fn, ms } );
		return queued.length;
	};
	window.eval( source );
	const button = window.document.querySelector( '.tv-nav-link' );
	const menu = window.document.querySelector( '.tv-mega-menu' );
	const first = window.document.querySelector( 'a' );
	button.focus();
	return { window, button, menu, first, queued };
}

function arrow( window, target ) {
	target.dispatchEvent( new window.KeyboardEvent( 'keydown', { key: 'ArrowDown', bubbles: true, cancelable: true } ) );
}

test( 'the first ArrowDown opens the mega menu and focuses after visibility', () => {
	const { window, button, menu, first, queued } = page();
	arrow( window, button );
	assert.equal( button.getAttribute( 'aria-expanded' ), 'true' );
	assert.notEqual( window.document.activeElement, first );
	assert.equal( queued.length, 1 );
	assert.equal( queued[ 0 ].ms, 250 );
	const ended = new window.Event( 'transitionend', { bubbles: true } );
	Object.defineProperty( ended, 'propertyName', { value: 'visibility' } );
	Object.defineProperty( ended, 'target', { value: menu } );
	menu.dispatchEvent( ended );
	assert.equal( window.document.activeElement, first );
	queued[ 0 ].fn();
	assert.equal( window.document.activeElement, first );
} );

test( 'the fallback focuses when the visibility transition never ends', () => {
	const { window, button, first, queued } = page();
	arrow( window, button );
	assert.notEqual( window.document.activeElement, first );
	queued[ 0 ].fn();
	assert.equal( window.document.activeElement, first );
} );

test( 'a later ArrowDown on an open menu focuses in the same turn', () => {
	const { window, button, first, queued } = page();
	button.setAttribute( 'aria-expanded', 'true' );
	arrow( window, button );
	assert.equal( window.document.activeElement, first );
	assert.equal( queued.length, 0 );
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
