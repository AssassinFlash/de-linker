/**
 * "Add all" counts a line as added only when the draft shows it afterwards.
 */

/**
 * External dependencies
 */
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { storeClient, type AddStatus } from './store';

function json( body: unknown, headers: Record< string, string > = {} ) {
	return new Response( JSON.stringify( body ), {
		status: 200,
		headers: { 'Content-Type': 'application/json', ...headers },
	} );
}

function cartFetch(
	after: { id: number; quantity: number }[],
	failAdd = new Set< number >()
) {
	const carts = [
		json( { items: [ { id: 7, quantity: 1 } ] }, { Nonce: 'abc' } ),
		json( { items: after } ),
	];
	return vi.fn< typeof fetch >( async ( input, init ) => {
		const url = String( input );
		if ( url.endsWith( '/cart' ) ) {
			return carts.shift()!;
		}
		const body = JSON.parse( String( init?.body ) );
		expect( ( init?.headers as Record< string, string > ).Nonce ).toBe(
			'abc'
		);
		return new Response( '{}', {
			status: failAdd.has( body.id ) ? 400 : 201,
		} );
	} );
}

test( 'lines the draft shows afterwards are added', async () => {
	const fetcher = cartFetch( [
		{ id: 7, quantity: 2 },
		{ id: 9, quantity: 2 },
	] );
	const statuses = new Map< number, AddStatus >();
	const complete = await storeClient( '/wp-json/', fetcher ).addAll(
		[
			{ productId: 7, quantity: 1 },
			{ productId: 9, quantity: 2 },
		],
		( id, status ) => statuses.set( id, status )
	);
	expect( complete ).toBe( true );
	expect( [ ...statuses ] ).toEqual( [
		[ 7, 'added' ],
		[ 9, 'added' ],
	] );
	expect( fetcher ).toHaveBeenCalledWith(
		'/wp-json/wc/store/v1/cart/add-item',
		expect.objectContaining( { method: 'POST' } )
	);
} );

test( 'a line the draft does not show stays unverified, a refused one asks to retry', async () => {
	const fetcher = cartFetch( [ { id: 7, quantity: 1 } ], new Set( [ 9 ] ) );
	const statuses = new Map< number, AddStatus >();
	const complete = await storeClient( '/wp-json/', fetcher ).addAll(
		[
			{ productId: 7, quantity: 1 },
			{ productId: 9, quantity: 2 },
		],
		( id, status ) => statuses.set( id, status )
	);
	expect( complete ).toBe( false );
	expect( statuses.get( 7 ) ).toBe( 'unverified' );
	expect( statuses.get( 9 ) ).toBe( 'retry' );
} );
