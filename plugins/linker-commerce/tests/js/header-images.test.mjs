/**
 * Image reference resolution in the shipped header partials.
 *
 * The mega panels and the mobile drawer show their photos only when every
 * <img> resolves through its own src. The empty-box defect (debt family 12,
 * docs/debt/ADJUDICATION-2026-10-14.md) shipped the thumbnails as
 * data-src with no src: nothing fetched them unless the hydration script
 * happened to see the exact open event, so the menus rendered as empty
 * boxes. These tests pin the resolving form: a src on every image, no
 * deferred data-src/data-srcset, site-absolute uploads paths, and the
 * same photos in both languages.
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
