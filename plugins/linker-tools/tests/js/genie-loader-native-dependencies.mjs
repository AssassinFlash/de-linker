/** Execute the real loader with an already printed native script and no network. */
import { JSDOM } from 'jsdom';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const code = readFileSync( process.argv[ 2 ], 'utf8' );
const results = [];
for ( const initial of [ 'present', 'missing', 'failed-fallback' ] ) {
	const dom = new JSDOM(
		'<body><div data-linker-genie-mount></div><script id="wp-i18n-js" src="/native-i18n.js"></script><script data-linker-genie-loader></script></body>',
		{
			runScripts: 'outside-only',
			pretendToBeVisual: true,
			url: 'https://fixture.test/',
		}
	);
	const win = dom.window;
	const doc = win.document;
	let translated = false;
	const runtime = {
		setLocaleData() {
			translated = true;
		},
		__() {
			return translated ? 'Senden' : 'Send';
		},
	};
	if ( initial === 'present' ) {
		win.wp = { i18n: runtime };
	}
	const payload = {
		src: 'https://fixture.test/genie.js',
		deps: [ 'https://fixture.test/fallback-i18n.js' ],
		nativeDependencies: {
			'https://fixture.test/fallback-i18n.js': [ 'wp', 'i18n' ],
		},
		translations: [ 'window.wp.i18n.setLocaleData({});' ],
		error: 'Genie could not load.',
		retry: 'Try again',
		title: "Genie - Linker's AI assistant",
		close: 'Close',
		open: true,
	};
	doc.querySelector( '[data-linker-genie-loader]' ).setAttribute(
		'data-linker-genie-boot-payload',
		JSON.stringify( payload )
	);
	const requested = [];
	let ready = 0;
	let failFallback = initial === 'failed-fallback';
	win.addEventListener( 'linker-genie-ready', () => {
		ready += 1;
	} );
	const append = doc.body.appendChild.bind( doc.body );
	doc.body.appendChild = ( node ) => {
		if ( node.tagName !== 'SCRIPT' ) {
			return append( node );
		}
		append( node );
		if ( ! node.src ) {
			win.eval( node.textContent );
			return node;
		}
		requested.push( node.src );
		queueMicrotask( () => {
			if ( node.src.endsWith( '/fallback-i18n.js' ) ) {
				if ( failFallback ) {
					node.dispatchEvent( new win.Event( 'error' ) );
					return;
				}
				win.wp = { i18n: runtime };
			} else {
				assert.equal( win.wp.i18n.__(), 'Senden' );
				win.dispatchEvent(
					new win.CustomEvent( 'linker-genie-ready' )
				);
			}
			node.dispatchEvent( new win.Event( 'load' ) );
		} );
		return node;
	};
	win.eval( code );
	// Drain only the fixture's in-memory dependency/app microtasks.
	await new Promise( ( resolve ) => setImmediate( resolve ) );
	if ( initial === 'failed-fallback' ) {
		assert.equal( ready, 0 );
		const retry = doc.querySelector(
			'[data-linker-genie-load-error] .linker-genie-load-error__actions button'
		);
		assert(
			retry,
			'a failed native fallback retains the original retry UI'
		);
		failFallback = false;
		retry.click();
		await new Promise( ( resolve ) => setImmediate( resolve ) );
	}
	assert.equal( ready, 1 );
	assert.equal( win.wp.i18n, runtime );
	const expectedDependencyRequests = {
		present: 0,
		missing: 1,
		'failed-fallback': 2,
	};
	assert.equal(
		requested.filter( ( url ) => url.endsWith( '/fallback-i18n.js' ) )
			.length,
		expectedDependencyRequests[ initial ]
	);
	assert.equal(
		requested.filter( ( url ) => url.endsWith( '/genie.js' ) ).length,
		1
	);
	results.push( {
		initial,
		ready,
		dependencyRequests: requested.length - 1,
	} );
	dom.window.close();
}
process.stdout.write( JSON.stringify( results ) );
