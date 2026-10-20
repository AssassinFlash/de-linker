/**
 * The mount's size-hint attributes become the residential form's defaults.
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

const BASE = {
	'data-engine-url': 'https://engine.test/',
	'data-rest-url': '/wp-json',
	'data-rest-nonce': 'n',
};

describe( 'readConfig', () => {
	it( 'reads the engine address and leaves the form defaults empty', () => {
		expect( readConfig( mount( BASE ) ) ).toEqual( {
			engineUrl: 'https://engine.test',
			restUrl: '/wp-json/',
			restNonce: 'n',
			locale: 'en',
			openRoof: false,
			defaults: {},
		} );
	} );

	it( 'maps a size-hint mount onto the fields that differ from the empty defaults', () => {
		const config = readConfig(
			mount( {
				...BASE,
				'data-pv-kwp': '10',
				'data-annual-kwh': '4500',
				'data-phase': '3',
				'data-backup': 'needed',
				'data-plz': '80538',
			} )
		);
		expect( config.defaults ).toEqual( {
			pv_kwp: '10',
			annual_kwh: '4500',
			backup: 'needed',
			plz: '80538',
		} );
	} );

	it( 'carries phase 1 and the accessory backup, and ignores values the form does not accept', () => {
		expect(
			readConfig(
				mount( {
					...BASE,
					'data-pv-kwp': '10.5',
					'data-annual-kwh': '0',
					'data-phase': '1',
					'data-backup': 'needed_accessory_ok',
					'data-plz': '8053',
				} )
			).defaults
		).toEqual( {
			pv_kwp: '10.5',
			phase: '1',
			backup: 'needed_accessory_ok',
		} );
		expect(
			readConfig(
				mount( {
					...BASE,
					'data-phase': '3',
					'data-backup': 'none',
					'data-pv-kwp': '-1',
					'data-plz': 'abc',
				} )
			).defaults
		).toEqual( {} );
	} );

	it( 'still opens the roof step from data-step', () => {
		expect(
			readConfig( mount( { ...BASE, 'data-step': 'roof' } ) ).openRoof
		).toBe( true );
	} );
} );
