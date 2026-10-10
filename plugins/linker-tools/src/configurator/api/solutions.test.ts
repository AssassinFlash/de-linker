/**
 * Saving a solution posts the engine input and the lines the customer saw to
 * the account's route (linker/v1/solutions, the contract of #11's linker-commerce).
 */

/**
 * External dependencies
 */
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { saveSolution } from './solutions';

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

test( 'posts the design and its lines with the nonce', async () => {
	const fetcher = vi.fn< typeof fetch >(
		async () =>
			new Response(
				JSON.stringify( { id: 61, url: '/my-account/solutions/61/' } ),
				{ status: 201 }
			)
	);
	const saved = await saveSolution(
		'https://site.test/wp-json/',
		'nonce-1',
		{
			kind: 'residential',
			title: 'Munich home',
			input,
			lines: [
				{ productId: 3556, quantity: 1 },
				{ productId: 3611, quantity: 1 },
			],
		},
		fetcher
	);
	expect( saved ).toEqual( {
		id: 61,
		url: '/my-account/solutions/61/',
	} );
	const [ url, init ] = fetcher.mock.calls[ 0 ];
	expect( url ).toBe( 'https://site.test/wp-json/linker/v1/solutions' );
	expect( init?.method ).toBe( 'POST' );
	expect( init?.credentials ).toBe( 'same-origin' );
	expect(
		( init?.headers as Record< string, string > )[ 'X-WP-Nonce' ]
	).toBe( 'nonce-1' );
	expect( JSON.parse( String( init?.body ) ) ).toEqual( {
		kind: 'residential',
		title: 'Munich home',
		input,
		lines: [
			{ product_id: 3556, quantity: 1 },
			{ product_id: 3611, quantity: 1 },
		],
	} );
} );

test( 'a refused save throws instead of reporting a saved solution', async () => {
	const fetcher = vi.fn< typeof fetch >(
		async () => new Response( '[]', { status: 403 } )
	);
	await expect(
		saveSolution(
			'https://site.test/wp-json/',
			'nonce-1',
			{
				kind: 'residential',
				title: 'Munich home',
				input,
				lines: [],
			},
			fetcher
		)
	).rejects.toThrow( 'save 403' );
} );
