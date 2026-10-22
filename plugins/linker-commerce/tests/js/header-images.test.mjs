/**
 * Header photos keep real, site-absolute image sources. Closed navigation
 * must defer those images through native loading="lazy" while the visible
 * brand logo stays eager. This also protects open-menu image availability
 * without a separate data-src hydration path.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';

const require = createRequire( import.meta.url );
const { JSDOM } = require( '../../../linker-tools/node_modules/jsdom' );

const partials = {
	en: '../../content/livecanvas/partials/header.html',
	de: '../../content/livecanvas/partials/de/header.html',
};

function images( lang ) {
	const html = readFileSync( new URL( partials[ lang ], import.meta.url ), 'utf8' );
	const dom = new JSDOM( html );
	return [ ...dom.window.document.querySelectorAll( 'img' ) ];
}

test( 'every header image resolves through its own src in both languages', () => {
	for ( const lang of Object.keys( partials ) ) {
		for ( const img of images( lang ) ) {
			const src = img.getAttribute( 'src' );
			assert.ok( src, `an <img> in the ${ lang } header has no src: ${ img.outerHTML }` );
			assert.notEqual( src.trim(), '', `an <img> in the ${ lang } header has an empty src: ${ img.outerHTML }` );
		}
	}
} );

test( 'no header image defers through data-src or data-srcset', () => {
	for ( const lang of Object.keys( partials ) ) {
		for ( const img of images( lang ) ) {
			assert.equal( img.hasAttribute( 'data-src' ), false, `deferred data-src back in the ${ lang } header: ${ img.outerHTML }` );
			assert.equal( img.hasAttribute( 'data-srcset' ), false, `deferred data-srcset back in the ${ lang } header: ${ img.outerHTML }` );
		}
	}
} );

test( 'menu image sources are site-absolute uploads paths', () => {
	for ( const lang of Object.keys( partials ) ) {
		for ( const img of images( lang ) ) {
			const src = img.getAttribute( 'src' ) || '';
			assert.match(
				src,
				/^\/wp-content\/uploads\//,
				`the ${ lang } header references a non-uploads source: ${ src }`
			);
		}
	}
} );

test( 'both language headers ship the same set of photos', () => {
	const sources = ( lang ) => images( lang ).map( ( img ) => img.getAttribute( 'src' ) ).sort();
	assert.deepEqual( sources( 'en' ), sources( 'de' ) );
	assert.ok( sources( 'en' ).length > 0, 'the header partials carry no images at all' );
} );

test( 'only the visible brand logo loads eagerly; every menu photo is native lazy', () => {
	for ( const lang of Object.keys( partials ) ) {
		const imgs = images( lang );
		const logos = imgs.filter( ( img ) => img.classList.contains( 'tv-brand-logo' ) );
		const menuPhotos = imgs.filter( ( img ) => ! img.classList.contains( 'tv-brand-logo' ) );
		assert.equal( logos.length, 1 );
		assert.equal( logos[ 0 ].getAttribute( 'loading' ), 'eager' );
		assert.ok( menuPhotos.length > 0 );
		for ( const img of menuPhotos ) {
			assert.equal( img.getAttribute( 'loading' ), 'lazy', `the ${ lang } header starts a hidden menu photo eagerly: ${ img.outerHTML }` );
			assert.equal( img.getAttribute( 'decoding' ), 'async' );
		}
	}
} );
