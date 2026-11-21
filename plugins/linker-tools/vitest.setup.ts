/**
 * External dependencies
 */
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach } from 'vitest';
import { webcrypto } from 'node:crypto';

if ( ! globalThis.crypto.subtle ) {
	Object.defineProperty( globalThis.crypto, 'subtle', {
		value: webcrypto.subtle,
		configurable: true,
	} );
}

// Simulate the commerce widget's callback at the cross-bundle boundary.
if ( typeof window !== 'undefined' ) {
	beforeEach( () => {
		window.linkerTurnstile = {
			mount: ( _node, _action, onToken ) => {
				onToken( 'native-test-response' );
				return () => {};
			},
			refresh: () => {},
		};
	} );
	afterEach( () => {
		delete window.linkerTurnstile;
	} );
}
afterEach( cleanup );

// jsdom has no layout, so it does not implement scrolling; the apps call it.
if ( typeof Element !== 'undefined' && ! Element.prototype.scrollIntoView ) {
	Element.prototype.scrollIntoView = () => undefined;
}

// jsdom has no Blob#text (browsers have had it since 2020); the C&I panel
// reads the uploaded load profile with it.
if ( typeof Blob !== 'undefined' && ! Blob.prototype.text ) {
	Blob.prototype.text = function text( this: Blob ) {
		return new Promise< string >( ( resolve, reject ) => {
			const reader = new FileReader();
			reader.onload = () => resolve( String( reader.result ) );
			reader.onerror = () => reject( reader.error );
			reader.readAsText( this );
		} );
	};
}
