/** Execute the actual inline bootstrap while its external app is unavailable. */
import { JSDOM } from 'jsdom';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const code = readFileSync( process.argv[ 2 ], 'utf8' );
async function scenario( width, workspace ) {
	const dom = new JSDOM(
		'<body style="overflow:clip"><main id="background"><button id="opener" data-linker-genie-open>Open Genie</button><textarea id="source">Original source question</textarea></main><div><div data-linker-genie-mount hidden role="region" aria-label="Prior label" aria-modal="false"><div><a href="/account">Account</a></div></div></div><script data-linker-genie-loader></script></body>',
		{
			runScripts: 'outside-only',
			pretendToBeVisual: true,
			url: 'https://fixture.test/',
		}
	);
	const win = dom.window,
		doc = win.document,
		panel = doc.querySelector( '[data-linker-genie-mount]' ),
		opener = doc.getElementById( 'opener' );
	Object.defineProperty( win, 'innerWidth', { value: width } );
	win.HTMLElement.prototype.getClientRects = function () {
		return this.closest( '[hidden]' ) ? [] : [ { width: 44, height: 44 } ];
	};
	doc.querySelector( '[data-linker-genie-loader]' ).setAttribute(
		'data-linker-genie-boot-payload',
		JSON.stringify( {
			src: 'genie.js',
			deps: [],
			translations: [],
			error: 'Genie could not load.',
			retry: 'Try again',
			title: "Genie - Linker's AI assistant",
			close: 'Close',
			open: workspace,
		} )
	);
	const scripts = [];
	const append = doc.body.appendChild.bind( doc.body );
	doc.body.appendChild = function ( node ) {
		if ( node.tagName === 'SCRIPT' ) {
			scripts.push( node );
			return node;
		}
		return append( node );
	};
	const delivered = [];
	win.addEventListener( 'linker-genie-open', ( event ) =>
		delivered.push( event.detail )
	);
	win.eval( code );
	if ( ! workspace ) {
		opener.focus();
		win.dispatchEvent(
			new win.CustomEvent( 'linker-genie-ask', {
				detail: { message: 'Original pending legacy question', opener },
			} )
		);
		win.dispatchEvent(
			new win.CustomEvent( 'linker-genie-ask', {
				detail: { entry: { id: 'entry-a' }, opener },
			} )
		);
	}
	scripts.at( -1 ).dispatchEvent( new win.Event( 'error' ) );
	await new Promise( ( resolve ) => setTimeout( resolve, 20 ) );
	const failure = doc.querySelector( '[data-linker-genie-load-error]' );
	assert( failure );
	assert.equal(
		failure.querySelector( '.linker-genie-load-error__actions button' )
			.className,
		'linker-genie-app__prompt'
	);
	if ( workspace ) {
		assert.equal(
			failure.querySelector( '.linker-genie-load-error__header button' ),
			null
		);
		doc.dispatchEvent(
			new win.KeyboardEvent( 'keydown', { key: 'Escape', bubbles: true } )
		);
		assert.equal( panel.hidden, false );
		assert.equal( doc.body.style.overflow, 'clip' );
		assert.equal( panel.getAttribute( 'role' ), 'region' );
	} else {
		assert.equal( panel.getAttribute( 'role' ), 'dialog' );
		assert.equal(
			panel.getAttribute( 'aria-modal' ),
			width <= 860 ? 'true' : null
		);
		assert.equal(
			Boolean( doc.getElementById( 'background' ).inert ),
			width <= 860
		);
		const retry = failure.querySelector(
			'.linker-genie-load-error__actions button'
		);
		assert.equal( doc.activeElement, retry );
		if ( width <= 860 ) {
			doc.dispatchEvent(
				new win.KeyboardEvent( 'keydown', {
					key: 'Tab',
					bubbles: true,
					cancelable: true,
				} )
			);
			assert.equal( doc.activeElement, panel.querySelector( 'a' ) );
		}
		retry.click();
		assert.equal( panel.getAttribute( 'role' ), 'region' );
		assert.equal( doc.body.style.overflow, 'clip' );
		scripts.at( -1 ).dispatchEvent( new win.Event( 'error' ) );
		await new Promise( ( resolve ) => setTimeout( resolve, 20 ) );
		doc.dispatchEvent(
			new win.KeyboardEvent( 'keydown', {
				key: 'Escape',
				bubbles: true,
				cancelable: true,
			} )
		);
		assert.equal( panel.hidden, true );
		assert.equal( doc.activeElement, opener );
		assert.equal( panel.getAttribute( 'role' ), 'region' );
		assert.equal( panel.getAttribute( 'aria-label' ), 'Prior label' );
		assert.equal( panel.getAttribute( 'aria-modal' ), 'false' );
		assert.equal( doc.body.style.overflow, 'clip' );
		assert.equal(
			Boolean( doc.getElementById( 'background' ).inert ),
			false
		);
		assert.equal(
			doc.getElementById( 'source' ).value,
			'Original source question'
		);
		win.dispatchEvent( new win.CustomEvent( 'linker-genie-ready' ) );
		assert.equal( panel.hidden, true );
		assert.equal( delivered.length, 0 );
		opener.click();
		assert.equal( delivered.length, 1 );
		assert.equal( delivered[ 0 ].message, '' );
		assert.equal( delivered[ 0 ].opener, opener );
		win.dispatchEvent(
			new win.CustomEvent( 'linker-genie-ask', {
				detail: { entry: { id: 'entry-b' }, opener },
			} )
		);
		assert.deepEqual(
			delivered
				.filter( ( item ) => item.entry )
				.map( ( item ) => item.entry.id ),
			[ 'entry-b' ]
		);
		assert( delivered.every( ( item ) => item.opener === opener ) );
	}
	dom.window.close();
	return { width, workspace, ok: true };
}
const results = [];
for ( const width of [ 1440, 390 ] ) {
	for ( const workspace of [ false, true ] ) {
		results.push( await scenario( width, workspace ) );
	}
}
process.stdout.write( JSON.stringify( results ) );
