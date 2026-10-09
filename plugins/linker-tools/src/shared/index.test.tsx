/**
 * External dependencies
 */
import { act, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';

/**
 * WordPress dependencies
 */
import { resetLocaleData, setLocaleData } from '@wordpress/i18n';

async function loadEntry( markup: string ) {
	document.body.innerHTML = markup;
	await act( async () => {
		await import( './index' );
	} );
}

beforeEach( () => {
	// Each test evaluates the entry afresh, as a page load would.
	vi.resetModules();
} );

afterEach( () => {
	resetLocaleData( {}, 'linker-tools' );
	document.body.innerHTML = '';
} );

test( 'mounts on every data-linker-app="shared" element and nowhere else', async () => {
	await loadEntry(
		'<div data-linker-app="shared"></div>' +
			'<div data-linker-app="shared"></div>' +
			'<div data-linker-app="genie"></div>'
	);

	expect( screen.getAllByText( 'Linker Tools' ) ).toHaveLength( 2 );
	expect(
		document.querySelector( '[data-linker-app="genie"]' )
	).toBeEmptyDOMElement();
} );

test( 'renders the translation registered for the linker-tools domain', async () => {
	// PHP hands WordPress these strings through wp_set_script_translations().
	setLocaleData( { 'Linker Tools': [ 'Linker-Werkzeuge' ] }, 'linker-tools' );

	await loadEntry( '<div data-linker-app="shared"></div>' );

	expect( screen.getByText( 'Linker-Werkzeuge' ) ).toBeInTheDocument();
} );
