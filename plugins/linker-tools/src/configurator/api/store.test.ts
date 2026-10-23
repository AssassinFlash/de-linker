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

test( 'product display is asked in the page language and the permalink is kept', async () => {
	const german = [
		{
			id: 4107,
			name: 'SAJ H2-10K-T3',
			permalink: 'https://de-linker.test/de/produkt/saj-h2-10k-t3/',
			images: [],
			is_in_stock: true,
		},
		{
			id: 1957,
			name: 'GoodWe GW208.9-BAT-LCD-G10',
			permalink: 'https://de-linker.test/de/produkt/gw208-9-bat-lcd-g10/',
			images: [],
			is_in_stock: true,
		},
	];
	const fetcher = vi.fn< typeof fetch >( async () => json( german ) );
	const products = await storeClient( '/wp-json/', fetcher ).products(
		[ 4107, 1957 ],
		'de'
	);
	expect( fetcher ).toHaveBeenCalledWith(
		'/wp-json/wc/store/v1/products?include=4107,1957&per_page=2&lang=de',
		{ credentials: 'same-origin' }
	);
	expect( products.map( ( product ) => product.permalink ) ).toEqual( [
		'https://de-linker.test/de/produkt/saj-h2-10k-t3/',
		'https://de-linker.test/de/produkt/gw208-9-bat-lcd-g10/',
	] );

	fetcher.mockResolvedValueOnce(
		json( [
			{
				...german[ 0 ],
				permalink: 'https://de-linker.test/product/saj-h2-10k-t3/',
			},
		] )
	);
	const english = await storeClient( '/wp-json/', fetcher ).products(
		[ 4107 ],
		'en'
	);
	expect( String( fetcher.mock.calls.at( -1 )?.[ 0 ] ) ).toBe(
		'/wp-json/wc/store/v1/products?include=4107&per_page=1&lang=en'
	);
	expect( english[ 0 ].permalink ).toBe(
		'https://de-linker.test/product/saj-h2-10k-t3/'
	);
} );

const proof = {
	kind: 'residential' as const,
	input: {
		plz: '39179',
		annual_kwh: 5000,
		pv_kwp: 10,
		phase: 3 as const,
		locale: 'en' as const,
		backup: 'none' as const,
		heat_pump: false,
		electric_vehicle: false,
	},
	selection_fingerprint: 'a'.repeat( 64 ),
};

test( 'one complete write uses the server proof and actual readback', async () => {
	const fetcher = vi.fn< typeof fetch >( async ( input, init ) => {
		if ( String( input ).endsWith( '/cart' ) ) {
			return json(
				{ items: [ { id: 7, quantity: 1 } ] },
				{ Nonce: 'abc' }
			);
		}
		expect( String( input ) ).toBe( '/wp-json/linker/v1/solutions/draft' );
		expect( JSON.parse( String( init?.body ) ) ).toEqual( proof );
		expect( init?.headers ).toEqual( {
			'Content-Type': 'application/json',
			Nonce: 'abc',
			'X-WP-Nonce': 'rest',
		} );
		return json( {
			items: [
				{ id: 7, quantity: 1 },
				{ id: 9, quantity: 2 },
			],
		} );
	} );
	const statuses = new Map< number, AddStatus >();
	expect(
		await storeClient( '/wp-json/', fetcher, 'rest' ).addAll(
			[
				{ productId: 7, quantity: 1 },
				{ productId: 9, quantity: 2 },
			],
			( id, status ) => statuses.set( id, status ),
			proof
		)
	).toBe( true );
	expect( [ ...statuses.values() ] ).toEqual( [ 'added', 'added' ] );
	expect( fetcher ).toHaveBeenCalledTimes( 2 );
	expect(
		fetcher.mock.calls.filter( ( [ , init ] ) => init?.method === 'POST' )
	).toHaveLength( 1 );
} );

test( 'withdrawal refuses the whole design and never falls back to individual writes', async () => {
	const fetcher = vi.fn< typeof fetch >( async ( input ) =>
		String( input ).endsWith( '/cart' )
			? json( { items: [] }, { Nonce: 'abc' } )
			: new Response(
					JSON.stringify( { code: 'linker_solution_changed' } ),
					{ status: 409 }
				)
	);
	const statuses = new Map< number, AddStatus >();
	expect(
		await storeClient( '/wp-json/', fetcher ).addAll(
			[
				{ productId: 7, quantity: 1 },
				{ productId: 9, quantity: 2 },
			],
			( id, status ) => statuses.set( id, status ),
			proof
		)
	).toBe( false );
	expect( [ ...statuses.values() ] ).toEqual( [ 'stale', 'stale' ] );
	expect( fetcher ).toHaveBeenCalledTimes( 2 );
	expect(
		fetcher.mock.calls.some( ( [ input ] ) =>
			String( input ).includes( '/cart/add-item' )
		)
	).toBe( false );
} );

test( 'missing proof cannot degrade to a subset of product IDs', async () => {
	const fetcher = vi.fn< typeof fetch >();
	const statuses = new Map< number, AddStatus >();
	expect(
		await storeClient( '/wp-json/', fetcher ).addAll(
			[ { productId: 7, quantity: 1 } ],
			( id, status ) => statuses.set( id, status )
		)
	).toBe( false );
	expect( fetcher ).not.toHaveBeenCalled();
	expect( statuses.get( 7 ) ).toBe( 'stale' );
} );

test( 'a short or unreadable response never reports partial success', async () => {
	const fetcher = vi.fn< typeof fetch >( async ( input ) =>
		String( input ).endsWith( '/cart' )
			? json( { items: [] }, { Nonce: 'abc' } )
			: json( { items: [ { id: 7, quantity: 1 } ] } )
	);
	const statuses = new Map< number, AddStatus >();
	expect(
		await storeClient( '/wp-json/', fetcher ).addAll(
			[
				{ productId: 7, quantity: 1 },
				{ productId: 9, quantity: 2 },
			],
			( id, status ) => statuses.set( id, status ),
			proof
		)
	).toBe( false );
	expect( [ ...statuses.values() ] ).toEqual( [
		'unverified',
		'unverified',
	] );
} );

test( 'Genie cards use their signed complete list without an engineering fallback', async () => {
	const fetcher = vi.fn< typeof fetch >( async ( input, init ) => {
		if ( String( input ).endsWith( '/cart' ) ) {
			return json( { items: [] }, { Nonce: 'abc' } );
		}
		expect( String( input ) ).toBe( '/wp-json/linker-ai/v1/genie/draft' );
		expect( JSON.parse( String( init?.body ) ) ).toEqual( {
			proof: 'signed-complete-list',
		} );
		return json( { items: [ { id: 7, quantity: 2 } ] } );
	} );
	const statuses = new Map< number, AddStatus >();
	expect(
		await storeClient( '/wp-json/', fetcher ).addAll(
			[ { productId: 7, quantity: 2 } ],
			( id, status ) => statuses.set( id, status ),
			{ kind: 'genie', token: 'signed-complete-list' }
		)
	).toBe( true );
	expect( statuses.get( 7 ) ).toBe( 'added' );
	expect( fetcher ).toHaveBeenCalledTimes( 2 );
} );
