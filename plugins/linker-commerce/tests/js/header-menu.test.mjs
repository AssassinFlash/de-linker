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
				<button class="tv-b2b-acct-btn" aria-haspopup="true" aria-expanded="false">Account</button>
				<div class="tv-b2b-acct-menu"><a href="/my-account/">Sign in</a><a href="/my-account/register/">Create account</a></div>
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

function wideEarlyPage() {
	const dom = new JSDOM( `<!doctype html><html lang="en"><head><style>
		.tv-nav-frame { padding:0; column-gap:0; }
		.tv-mobile-navigation { display:none; }
		#tv-header-v2[data-tv-nav-folded="true"] .tv-mobile-navigation { display:block; }
		#tv-header-v2[data-tv-nav-folded="true"] .tv-desktop-nav,
		#tv-header-v2[data-tv-nav-folded="true"] .tv-header-cta { display:none; }
	</style></head><body><header id="tv-header-v2"><div class="tv-nav-frame">
		<a class="tv-brand" data-fixture-width="100" href="/">Home</a>
		<div class="tv-desktop-nav" data-fixture-width="600"><div class="tv-nav-item">
			<button class="tv-nav-link" aria-expanded="false">Products</button>
			<div class="tv-mega-menu"><a href="/products/">All products</a></div>
		</div></div>
		<div class="tv-desktop-actions" data-fixture-width="200"></div>
		<a class="tv-header-cta" data-fixture-width="100" href="/contact/">Contact</a>
		<details class="tv-mobile-navigation" data-fixture-width="44" open>
			<summary id="tv-mobile-toggle" aria-label="Open menu">Menu</summary>
			<div id="tv-mobile-panel"><a href="/products/">Products</a></div>
		</details>
	</div></header><button id="outside">Outside</button></body></html>`, { runScripts: 'outside-only', pretendToBeVisual: true } );
	const { window } = dom;
	const frame = window.document.querySelector( '.tv-nav-frame' );
	// JSDOM has no layout. These fixture boxes leave room for the normal row,
	// so keeping an early opening cannot pass merely because the row is full.
	Object.defineProperty( frame, 'clientWidth', { value: 1200 } );
	window.HTMLElement.prototype.getBoundingClientRect = function () {
		return { width: Number( this.getAttribute( 'data-fixture-width' ) ) };
	};
	window.matchMedia = () => ( { matches: true } );
	window.ResizeObserver = class { observe() {} };
	Object.defineProperty( window.document, 'fonts', { value: { ready: Promise.resolve() } } );
	const toggle = window.document.querySelector( 'summary' );
	toggle.focus();
	window.eval( source );
	return { window, toggle, details: window.document.querySelector( 'details' ), header: window.document.querySelector( 'header' ), primary: window.document.querySelector( '.tv-nav-link' ) };
}

test( 'an early desktop opening stays usable even when the full row fits', () => {
	const { window, details, header } = wideEarlyPage();
	assert.equal( details.open, true );
	assert.equal( header.dataset.tvNavFolded, 'true' );
	assert.equal( window.getComputedStyle( window.document.querySelector( '.tv-mobile-navigation' ) ).display, 'block' );
	window.close();
} );

test( 'closing an early desktop opening restores the full row and keyboard focus', async () => {
	const { window, toggle, details, header, primary } = wideEarlyPage();
	assert.equal( details.open, true );
	toggle.click();
	await new Promise( resolve => window.requestAnimationFrame( () => window.requestAnimationFrame( resolve ) ) );
	assert.equal( details.open, false );
	assert.notEqual( header.dataset.tvNavFolded, 'true' );
	assert.equal( window.document.activeElement, primary );
	window.close();
} );

test( 'unfolding after an outside focus change does not take that focus', async () => {
	const { window, details, header } = wideEarlyPage();
	const outside = window.document.querySelector( '#outside' );
	assert.equal( details.open, true );
	outside.focus();
	await new Promise( resolve => window.requestAnimationFrame( () => window.requestAnimationFrame( resolve ) ) );
	assert.equal( details.open, false );
	assert.notEqual( header.dataset.tvNavFolded, 'true' );
	assert.equal( window.document.activeElement, outside );
	window.close();
} );

test( 'site search shows linked model suggestions and preserves native search submission', async () => {
	const dom = new JSDOM( `<html lang="de"><body><header id="tv-header-v2">
		<a href="/de/produkte/#search-box" data-tv-header-search data-search-min="2" data-search-url="/wp-json/linker/v1/catalog-search">Suche</a>
		<dialog id="tv-site-search"><h2>Website durchsuchen</h2><button data-tv-search-close></button><form action="/de/"><input type="search" name="s"></form>
		<ul class="tv-search-matches" hidden></ul><p role="status"></p></dialog></header></body></html>`,
		{ url: 'https://example.test/de/', runScripts: 'outside-only' } );
	try {
		const w = dom.window;
		const doc = w.document;
		const dialog = doc.querySelector( 'dialog' );
		dialog.showModal = () => { dialog.open = true; };
		dialog.close = () => { dialog.open = false; dialog.dispatchEvent( new w.Event( 'close' ) ); };
		let requested;
		w.fetch = async ( url ) => {
			requested = url;
			return { ok: true, json: async () => ( { items: [ { title: 'GoodWe GW80K', sku: 'DLK-GW80K', url: '/de/produkt/gw80k/' } ] } ) };
		};
		w.eval( source );
		const opener = doc.querySelector( '[data-tv-header-search]' );
		opener.click();
		assert( dialog.open );
		const input = doc.querySelector( '[name=s]' );
		assert.equal( doc.activeElement, input );
		input.value = 'GW80K';
		const shown = new Promise( resolve => {
			const observer = new w.MutationObserver( () => { observer.disconnect(); resolve(); } );
			observer.observe( doc.querySelector( '.tv-search-matches' ), { childList: true } );
		} );
		input.dispatchEvent( new w.Event( 'input' ) );
		await shown;
		assert.equal( requested.searchParams.get( 'lang' ), 'de' );
		assert.equal( requested.searchParams.get( 'q' ), 'GW80K' );
		const match = doc.querySelector( '.tv-search-matches a' );
		assert.equal( match.pathname, '/de/produkt/gw80k/' );
		assert.equal( match.querySelector( 'small' ).textContent, 'DLK-GW80K' );
		assert.equal( new w.FormData( input.form ).get( 's' ), 'GW80K' );
		input.dispatchEvent( new w.KeyboardEvent( 'keydown', { key: 'Escape', bubbles: true, cancelable: true } ) );
		assert.equal( dialog.open, false );
		assert.equal( doc.activeElement, opener );
		assert.equal( input.value, '' );
	} finally { dom.window.close(); }
} );

test( 'cached headers show the native draft total on both links, and a clean visitor makes no cart request', async () => {
	const link = '<a class="tv-header-cart-link" data-cart-count-url="/wp-json/wc/store/v1/cart" aria-label="Solution draft">Draft</a>';
	const dom = new JSDOM( '<header id="tv-header-v2">' + link + link + '</header>', { url: 'https://linker.test/about/', runScripts: 'outside-only' } );
	const { window } = dom;
	let calls = 0;
	let count = 3;
	window.fetch = async ( url ) => {
		assert.equal( new URL( url ).searchParams.get( '_fields' ), 'items_count' );
		calls++;
		return { ok: true, json: async () => ( { items_count: count } ) };
	};
	window.eval( source );
	assert.equal( calls, 0 );
	window.document.cookie = 'woocommerce_items_in_cart=1; path=/';
	window.dispatchEvent( new window.PageTransitionEvent( 'pageshow', { persisted: true } ) );
	await new Promise( resolve => setTimeout( resolve, 0 ) );
	const badges = () => Array.from( window.document.querySelectorAll( '.tv-b2b-acct-count' ), item => item.textContent );
	assert.deepEqual( badges(), [ '3', '3' ] );
	count = 5;
	window.document.body.dispatchEvent( new window.CustomEvent( 'wc-blocks_added_to_cart', { bubbles: true } ) );
	await new Promise( resolve => setTimeout( resolve, 0 ) );
	assert.deepEqual( badges(), [ '5', '5' ] );
	count = 0;
	window.document.cookie = 'woocommerce_items_in_cart=; path=/; max-age=0';
	window.dispatchEvent( new window.PageTransitionEvent( 'pageshow', { persisted: true } ) );
	await new Promise( resolve => setTimeout( resolve, 0 ) );
	assert.deepEqual( badges(), [] );
	dom.window.close();
} );

test( 'a Genie-only guest carries the draft into a fresh cached header, then clears the signal when Woo is empty', async () => {
	const dom = new JSDOM( '<header id="tv-header-v2"></header>', { url: 'https://linker.test/', runScripts: 'outside-only' } );
	const { window } = dom;
	let count = 1;
	let calls = 0;
	window.fetch = async () => { calls++; return { ok: true, json: async () => ( { items_count: count } ) }; };
	const settle = () => new Promise( resolve => setTimeout( resolve, 0 ) );
	const header = window.document.querySelector( 'header' );
	const visit = ( serverBadge = '' ) => {
		header.innerHTML = '<a data-cart-count-url="/wp-json/wc/store/v1/cart">' + serverBadge + '</a>';
		window.eval( source );
	};
	const badge = () => header.querySelector( '.tv-b2b-acct-count' )?.textContent;
	try {
		visit();
		assert.equal( calls, 0 );
		window.document.body.dispatchEvent( new window.CustomEvent( 'wc-blocks_added_to_cart', { bubbles: true } ) );
		await settle();
		assert.equal( badge(), '1' );
		visit(); // Cached homepage has no server-rendered badge or readable Woo cookies.
		await settle();
		assert.equal( badge(), '1' );
		visit();
		await settle();
		assert.equal( badge(), '1' );
		count = 0;
		visit();
		await settle();
		assert.equal( badge(), undefined );
		const before = calls;
		visit();
		await settle();
		assert.equal( calls, before );

		count = 2;
		visit( '<span class="tv-b2b-acct-count">2</span>' );
		assert.equal( badge(), '2' );
		await settle();
		assert.equal( badge(), '2' );
	} finally { window.close(); }
} );
