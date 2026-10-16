/**
 * External dependencies
 */
import { act } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';

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

		// Each app shows its title in its own mount points and nothing in the others.
		const shown = entries.map( ( name ) => {
			const text =
				document.querySelector( `[data-linker-app="${ name }"]` )
					?.textContent ?? '';
			return name === entry
				? text.includes( titles[ entry ] )
				: text === '';
		} );
		expect( shown ).toEqual( entries.map( () => true ) );
	}
);
