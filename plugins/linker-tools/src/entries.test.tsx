/**
 * External dependencies
 */
import { act, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';

/**
 * WordPress dependencies
 */
import { resetLocaleData, setLocaleData } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import webpackConfig from '../webpack.config.js';

// The entries are whatever webpack.config.js builds; the titles are what the
// test expects each app to render.
const entries = Object.keys( webpackConfig.entry );
const titles: Record< string, string > = {
	genie: "Genie - Linker's AI assistant",
	configurator: 'Solution Configurator',
	shared: 'Linker Tools',
};

function mountPoint( name: string ) {
	return `<div data-linker-app="${ name }"></div>`;
}

async function loadEntry( entry: string, markup: string ) {
	document.body.innerHTML = markup;
	await act( async () => {
		await import( `./${ entry }/index.tsx` );
	} );
}

beforeEach( () => {
	// Each test evaluates an entry afresh, as a page load would.
	vi.resetModules();
} );

afterEach( () => {
	resetLocaleData( {}, 'linker-tools' );
	document.body.innerHTML = '';
} );

test( 'every built entry is src/<entry>/index.tsx and has an expected title', () => {
	expect( webpackConfig.entry ).toEqual(
		Object.fromEntries(
			Object.keys( titles ).map( ( entry ) => [
				entry,
				`./src/${ entry }/index.tsx`,
			] )
		)
	);
} );

test.each( entries )(
	'the %s entry renders into its own mount points only',
	async ( entry ) => {
		await loadEntry( entry, entries.map( mountPoint ).join( '' ) );

		expect(
			entries.map(
				( name ) =>
					document.querySelector( `[data-linker-app="${ name }"]` )
						?.textContent
			)
		).toEqual(
			entries.map( ( name ) => ( name === entry ? titles[ entry ] : '' ) )
		);
	}
);

test( 'an entry mounts on every element that names it', async () => {
	await loadEntry(
		'shared',
		mountPoint( 'shared' ) + mountPoint( 'shared' )
	);

	expect( screen.getAllByText( 'Linker Tools' ) ).toHaveLength( 2 );
} );

test( 'strings come from the linker-tools text domain', async () => {
	// PHP hands WordPress these strings through wp_set_script_translations().
	setLocaleData( { 'Linker Tools': [ 'Linker-Werkzeuge' ] }, 'linker-tools' );

	await loadEntry( 'shared', mountPoint( 'shared' ) );

	expect( screen.getByText( 'Linker-Werkzeuge' ) ).toBeInTheDocument();
} );
