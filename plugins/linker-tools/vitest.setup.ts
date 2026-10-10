/**
 * External dependencies
 */
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

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
