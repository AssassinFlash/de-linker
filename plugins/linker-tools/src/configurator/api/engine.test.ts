/**
 * Engine failures reach the screens as kinds they can explain.
 */

/**
 * External dependencies
 */
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { EngineError, engineClient } from './engine';

const input = {
	locale: 'en' as const,
	plz: '80538',
	annual_kwh: 5000,
	pv_kwp: 10,
	phase: 3 as const,
	backup: 'none' as const,
	heat_pump: false,
	electric_vehicle: false,
};

test.each( [
	[
		409,
		{ detail: { error: 'publication_changed' } },
		'unavailable',
		undefined,
	],
	[
		422,
		{ detail: { error: 'invalid_input', field: 'plz' } },
		'invalid',
		'plz',
	],
	[
		503,
		{ detail: { error: 'yield_unavailable' } },
		'unavailable',
		undefined,
	],
	[
		404,
		{ detail: { error: 'unknown_plz', field: 'plz' } },
		'not_found',
		'plz',
	],
] )( 'status %i becomes %s', async ( status, body, kind, field ) => {
	const fetcher = vi.fn< typeof fetch >(
		async () => new Response( JSON.stringify( body ), { status } )
	);
	const error = await engineClient( 'https://engine.test', fetcher )
		.residential( input )
		.catch( ( failure ) => failure );
	expect( error ).toBeInstanceOf( EngineError );
	expect( [ error.kind, error.field ] ).toEqual( [ kind, field ] );
} );

test( 'no answer at all is a network failure', async () => {
	const fetcher = vi.fn< typeof fetch >( async () => {
		throw new TypeError( 'offline' );
	} );
	const error = await engineClient( 'https://engine.test', fetcher )
		.place( '80538' )
		.catch( ( failure ) => failure );
	expect( error.kind ).toBe( 'network' );
} );

test( 'requests go to the engine paths', async () => {
	const fetcher = vi.fn< typeof fetch >(
		async () => new Response( '{}', { status: 200 } )
	);
	const client = engineClient( 'https://engine.test', fetcher );
	await client.residential( input );
	await client.roof( '80538', 48.1, 11.5, 'de' );
	expect( fetcher.mock.calls.map( ( call ) => call[ 0 ] ) ).toEqual( [
		'https://engine.test/design/residential',
		'https://engine.test/roof/outline',
	] );
} );

test( 'a new PDF carries the fingerprint of the confirmed screen', async () => {
	const fetcher = vi.fn< typeof fetch >(
		async () => new Response( '%PDF-test' )
	);
	await engineClient( 'https://engine.test', fetcher ).reportPdf(
		input,
		null,
		'a'.repeat( 64 )
	);
	expect(
		JSON.parse( String( fetcher.mock.calls[ 0 ][ 1 ]?.body ) )
	).toEqual( {
		input,
		logo: null,
		selection_fingerprint: 'a'.repeat( 64 ),
	} );
} );
