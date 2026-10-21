/**
 * External dependencies
 */
import { act } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import webpackConfig from '../webpack.config.js';

// The entries are whatever webpack.config.js builds. The apps render into
// mount points, with the titles the test expects; a page script mounts
// nothing (the preview card's rules, ticket #249, have their own tests).
const titles: Record< string, string > = {
	genie: "Genie - Linker's AI assistant",
	configurator: 'Solution Configurator',
};
const scripts: Record< string, string > = {
	marketing: './src/marketing/index.ts',
	preview: './src/preview/index.ts',
	// The home hero mounts into the page's own `.hero-cinematic` (ticket #232),
	// not into a `data-linker-app` mount.
	hero: './src/hero/index.tsx',
};
const entries = Object.keys( webpackConfig.entry ).filter(
	( entry ) => ! ( entry in scripts )
);

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

test( 'every built app is src/<entry>/index.tsx and has an expected title', () => {
	expect( webpackConfig.entry ).toEqual( {
		...Object.fromEntries(
			Object.keys( titles ).map( ( entry ) => [
				entry,
				`./src/${ entry }/index.tsx`,
			] )
		),
		...scripts,
	} );
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
