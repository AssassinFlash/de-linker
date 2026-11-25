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
			name: 'SAJ CB2-100.3-HV5 (100.3 kWh C&#038;I battery cabinet)',
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
	expect( products[ 0 ].name ).toBe(
		'SAJ CB2-100.3-HV5 (100.3 kWh C&I battery cabinet)'
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

const proof = 'signed-list';

test( 'one complete write uses the server proof and actual readback', async () => {
	const cartChanged = vi.fn();
	document.addEventListener( 'wc-blocks_added_to_cart', cartChanged, {
		once: true,
	} );
	const fetcher = vi.fn< typeof fetch >( async ( input, init ) => {
		if ( String( input ).endsWith( '/cart' ) ) {
			return json(
				{ items: [ { id: 7, quantity: 1 } ] },
				{ Nonce: 'abc' }
			);
		}
		expect( String( input ) ).toBe( '/wp-json/linker-ai/v1/genie/draft' );
		expect( JSON.parse( String( init?.body ) ) ).toEqual( {
			proof,
		} );
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
	expect( cartChanged ).toHaveBeenCalledOnce();
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

test( 'a refused product read rejects instead of passing an empty shelf', async () => {
	const fetcher = vi
		.fn< typeof fetch >()
		.mockResolvedValue( new Response( 'forbidden', { status: 403 } ) );
	await expect(
		storeClient( '/wp-json/', fetcher ).products( [ 4107 ], 'en' )
	).rejects.toThrow( 'products 403' );
} );

test.each( [
	{
		receipt: 'HTML from a bad gateway',
		write: () =>
			new Response( '<html>Bad Gateway</html>', {
				status: 502,
				headers: { 'Content-Type': 'text/html' },
			} ),
	},
	{
		receipt: 'empty gateway timeout',
		write: () => new Response( null, { status: 504 } ),
	},
	{ receipt: 'incomplete JSON', write: () => new Response( '{"items":' ) },
	{ receipt: 'missing line', write: () => json( { items: [] } ) },
	{
		receipt: 'connection lost after sending',
		write: () => {
			throw new TypeError( 'Failed to fetch' );
		},
	},
] )(
	'confirms a committed draft from Woo after $receipt without repeating the write',
	async ( { write } ) => {
		const events = vi.fn();
		document.addEventListener( 'wc-blocks_added_to_cart', events );
		const fetcher = vi
			.fn< typeof fetch >()
			.mockResolvedValueOnce(
				json(
					{ items: [ { id: 6530, quantity: 1 } ] },
					{ Nonce: 'guest-cart' }
				)
			)
			.mockImplementationOnce( async () => write() )
			.mockResolvedValueOnce(
				json( {
					items_count: 2,
					items: [
						{ id: 6530, quantity: 1 },
						{ id: 4106, quantity: 1 },
					],
				} )
			);
		const status = vi.fn();
		try {
			expect(
				await storeClient( '/wp-json/', fetcher ).addAll(
					[ { productId: 4106, quantity: 1 } ],
					status,
					proof
				)
			).toBe( true );
			expect( status ).toHaveBeenLastCalledWith( 4106, 'added' );
			expect( events ).toHaveBeenCalledOnce();
			expect(
				fetcher.mock.calls.map( ( [ url, init ] ) => [
					init?.method ?? 'GET',
					String( url ).split( '?' )[ 0 ],
				] )
			).toEqual( [
				[ 'GET', '/wp-json/wc/store/v1/cart' ],
				[ 'POST', '/wp-json/linker-ai/v1/genie/draft' ],
				[ 'GET', '/wp-json/wc/store/v1/cart' ],
			] );
			expect( fetcher.mock.calls[ 2 ][ 1 ] ).toMatchObject( {
				credentials: 'same-origin',
				cache: 'no-store',
			} );
		} finally {
			document.removeEventListener( 'wc-blocks_added_to_cart', events );
		}
	}
);

test.each( [
	[ 'another product', [ { id: 4105, quantity: 2 } ] ],
	[ 'insufficient requested quantity', [ { id: 4106, quantity: 1 } ] ],
] as const )(
	'Woo readback of %s cannot confirm the selected model and quantity',
	async ( _reason, items ) => {
		const fetcher = vi
			.fn< typeof fetch >()
			.mockResolvedValueOnce( json( {}, { Nonce: 'guest' } ) )
			.mockResolvedValueOnce( new Response( '{' ) )
			.mockResolvedValueOnce( json( { items } ) );
		const onStatus = vi.fn();
		expect(
			await storeClient( '/wp-json/', fetcher ).addAll(
				[ { productId: 4106, quantity: 2 } ],
				onStatus,
				proof
			)
		).toBe( false );
		expect( onStatus ).toHaveBeenLastCalledWith( 4106, 'unverified' );
		expect( fetcher ).toHaveBeenCalledTimes( 3 );
	}
);

test.each( [ 403, 502, 503, 504 ] )(
	'an explicit %i refusal cannot be confirmed from a product already in the cart',
	async ( status ) => {
		const fetcher = vi
			.fn< typeof fetch >()
			.mockResolvedValueOnce(
				json(
					{ items: [ { id: 4106, quantity: 1 } ] },
					{ Nonce: 'guest' }
				)
			)
			.mockResolvedValueOnce(
				Response.json( { code: 'rest_forbidden' }, { status } )
			);
		const onStatus = vi.fn();
		expect(
			await storeClient( '/wp-json/', fetcher ).addAll(
				[ { productId: 4106, quantity: 1 } ],
				onStatus,
				proof
			)
		).toBe( false );
		expect( onStatus ).toHaveBeenLastCalledWith( 4106, 'unverified' );
		expect( fetcher ).toHaveBeenCalledTimes( 2 );
	}
);
