import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';

const { JSDOM } = createRequire( import.meta.url )( '../../../linker-tools/node_modules/jsdom' );
const source = readFileSync( new URL( '../../assets/blog-author-dialog.js', import.meta.url ), 'utf8' );

for ( const failure of [ 'error', 'timeout' ] ) {
	test( 'the article contact link stays reachable after an iframe ' + failure, () => {
		const dom = new JSDOM( `<a class="reader-author-cta" href="/contact/">Contact</a>
			<dialog id="tv-blog-author-dialog"><div class="reader-author-dialog-loading">Loading</div>
			<a class="reader-author-dialog-fallback" href="/contact/" hidden>Open contact</a>
			<iframe class="reader-author-dialog-frame" data-src="/contact/?article_contact=1" hidden></iframe></dialog>`,
			{ url: 'https://linker.test/article/', runScripts: 'outside-only' } );
		const { window } = dom;
		const doc = window.document;
		doc.querySelector( 'dialog' ).showModal = () => {};
		let timeout;
		window.setTimeout = callback => { timeout = callback; return 1; };
		window.eval( source );
		doc.querySelector( '.reader-author-cta' ).click();
		if ( failure === 'error' ) doc.querySelector( 'iframe' ).dispatchEvent( new window.Event( 'error' ) );
		else timeout();
		assert.equal( doc.querySelector( '.reader-author-dialog-loading' ).hidden, true );
		assert.equal( doc.querySelector( '.reader-author-dialog-fallback' ).hidden, false );
		assert.equal( doc.querySelector( '.reader-author-dialog-fallback' ).href, 'https://linker.test/contact/' );
		dom.window.close();
	} );
}
