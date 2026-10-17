/**
 * The mount's page context reaches every turn (#234).
 */

/**
 * External dependencies
 */
import { describe, expect, it } from 'vitest';

/**
 * Internal dependencies
 */
import { readConfig } from './config';

function mount( attributes: Record< string, string > ): HTMLElement {
	const element = document.createElement( 'div' );
	for ( const [ name, value ] of Object.entries( attributes ) ) {
		element.setAttribute( name, value );
	}
	return element;
}

describe( 'readConfig', () => {
	it( 'reads the page context the dock prints', () => {
		const page = {
			type: 'product',
			title: 'SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)',
			product_id: 4107,
			post_id: 6741,
			url: 'https://de-linker.com/de/produkt/saj-h2-10k-t3/',
		};
		const config = readConfig(
			mount( {
				'data-page-type': 'product',
				'data-product-id': '4107',
				'data-page': JSON.stringify( page ),
			} )
		);
		expect( config.page ).toEqual( page );
	} );

	it( 'falls back to the page type and product of an older mount', () => {
		const config = readConfig(
			mount( { 'data-page-type': 'product', 'data-product-id': '3555' } )
		);
		expect( config.page ).toEqual( { type: 'product', product_id: 3555 } );
		expect(
			readConfig( mount( { 'data-page': 'not json' } ) ).page
		).toEqual( { type: 'other' } );
	} );
} );
