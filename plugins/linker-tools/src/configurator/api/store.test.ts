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
	failAdd = new Set< number >(),
	before: { id: number; quantity: number }[] = [ { id: 7, quantity: 1 } ]
) {
	const carts = [
		json( { items: before }, { Nonce: 'abc' } ),
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

test( 'a second add of the same scheme does not stack quantities', async () => {
	const items: { id: number; quantity: number }[] = [];
	const fetcher = vi.fn< typeof fetch >( async ( input, init ) => {
		const url = String( input );
		if ( url.endsWith( '/cart' ) ) {
			return json( { items }, { Nonce: 'abc' } );
		}
		const body = JSON.parse( String( init?.body ) ) as {
			id: number;
			quantity: number;
		};
		const current = items.find( ( item ) => item.id === body.id );
		if ( current ) {
			current.quantity += body.quantity;
		} else {
			items.push( { id: body.id, quantity: body.quantity } );
		}
		return new Response( '{}', { status: 201 } );
	} );
	const client = storeClient( '/wp-json/', fetcher );
	const lines = [
		{ productId: 7, quantity: 1 },
		{ productId: 9, quantity: 2 },
	];
	const first = new Map< number, AddStatus >();
	expect(
		await client.addAll( lines, ( id, status ) => first.set( id, status ) )
	).toBe( true );
	const second = new Map< number, AddStatus >();
	expect(
		await client.addAll( lines, ( id, status ) => second.set( id, status ) )
	).toBe( true );
	expect( items ).toEqual( [
		{ id: 7, quantity: 1 },
		{ id: 9, quantity: 2 },
	] );
	expect( [ ...second.values() ] ).toEqual( [ 'added', 'added' ] );
	const posts = fetcher.mock.calls.filter( ( call ) =>
		String( call[ 0 ] ).endsWith( '/cart/add-item' )
	);
	expect( posts ).toHaveLength( 2 );
} );

test( 'a line already at the scheme quantity is not written again, a refused one asks to retry', async () => {
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
	expect( statuses.get( 7 ) ).toBe( 'added' );
	expect( statuses.get( 9 ) ).toBe( 'retry' );
	const posted = fetcher.mock.calls
		.filter( ( call ) => String( call[ 0 ] ).endsWith( '/cart/add-item' ) )
		.map( ( call ) => JSON.parse( String( call[ 1 ]?.body ) ) );
	expect( posted ).toEqual( [ { id: 9, quantity: 2 } ] );
} );

test( 'a line short of the scheme quantity is topped up by the difference', async () => {
	const fetcher = cartFetch(
		[
			{ id: 7, quantity: 2 },
			{ id: 9, quantity: 2 },
		],
		new Set(),
		[ { id: 7, quantity: 1 } ]
	);
	const statuses = new Map< number, AddStatus >();
	const complete = await storeClient( '/wp-json/', fetcher ).addAll(
		[ { productId: 7, quantity: 2 } ],
		( id, status ) => statuses.set( id, status )
	);
	expect( complete ).toBe( true );
	expect( statuses.get( 7 ) ).toBe( 'added' );
	const posted = fetcher.mock.calls
		.filter( ( call ) => String( call[ 0 ] ).endsWith( '/cart/add-item' ) )
		.map( ( call ) => JSON.parse( String( call[ 1 ]?.body ) ) );
	expect( posted ).toEqual( [ { id: 7, quantity: 1 } ] );
} );

test( 'a line already above the scheme quantity is left alone and counted added', async () => {
	const fetcher = cartFetch( [ { id: 7, quantity: 5 } ], new Set(), [
		{ id: 7, quantity: 5 },
	] );
	const statuses = new Map< number, AddStatus >();
	const complete = await storeClient( '/wp-json/', fetcher ).addAll(
		[ { productId: 7, quantity: 2 } ],
		( id, status ) => statuses.set( id, status )
	);
	expect( complete ).toBe( true );
	expect( statuses.get( 7 ) ).toBe( 'added' );
	const posted = fetcher.mock.calls.filter( ( call ) =>
		String( call[ 0 ] ).endsWith( '/cart/add-item' )
	);
	expect( posted ).toHaveLength( 0 );
} );

test( 'a sent line the draft does not bring up to the scheme quantity stays unverified', async () => {
	const fetcher = cartFetch( [ { id: 9, quantity: 1 } ] );
	const statuses = new Map< number, AddStatus >();
	const complete = await storeClient( '/wp-json/', fetcher ).addAll(
		[ { productId: 9, quantity: 2 } ],
		( id, status ) => statuses.set( id, status )
	);
	expect( complete ).toBe( false );
	expect( statuses.get( 9 ) ).toBe( 'unverified' );
} );

test( 'a short readback is read once more before a line is called unverified', async () => {
	let reads = 0;
	const fetcher = vi.fn< typeof fetch >( async ( input ) => {
		const url = String( input );
		if ( url.endsWith( '/cart' ) ) {
			reads += 1;
			return json(
				{
					items:
						reads < 3
							? [ { id: 7, quantity: 0 } ]
							: [ { id: 7, quantity: 2 } ],
				},
				reads === 1 ? { Nonce: 'abc' } : {}
			);
		}
		return new Response( '{}', { status: 201 } );
	} );
	const statuses = new Map< number, AddStatus >();
	const complete = await storeClient( '/wp-json/', fetcher ).addAll(
		[ { productId: 7, quantity: 2 } ],
		( id, status ) => statuses.set( id, status )
	);
	expect( complete ).toBe( true );
	expect( statuses.get( 7 ) ).toBe( 'added' );
	expect( reads ).toBe( 3 );
} );
