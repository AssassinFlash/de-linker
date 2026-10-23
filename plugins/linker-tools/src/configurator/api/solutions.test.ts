/**
 * Saving a solution posts the engine input and the lines the customer saw to
 * the account's route (linker/v1/solutions, the contract of #11's linker-commerce).
 * The route answers the account's URL in the request's language (#473), so the
 * post carries the page's `lang`, as the product reads in store.ts do.
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
			selectionFingerprint: 'a'.repeat( 64 ),
			input,
			lines: [
				{ productId: 3556, quantity: 1 },
				{ productId: 3611, quantity: 1 },
			],
		},
		'en',
		fetcher
	);
	expect( saved ).toEqual( {
		id: 61,
		url: '/my-account/solutions/61/',
	} );
	const [ url, init ] = fetcher.mock.calls[ 0 ];
	expect( url ).toBe(
		'https://site.test/wp-json/linker/v1/solutions?lang=en'
	);
	expect( init?.method ).toBe( 'POST' );
	expect( init?.credentials ).toBe( 'same-origin' );
	expect(
		( init?.headers as Record< string, string > )[ 'X-WP-Nonce' ]
	).toBe( 'nonce-1' );
	expect( JSON.parse( String( init?.body ) ) ).toEqual( {
		kind: 'residential',
		title: 'Munich home',
		selection_fingerprint: 'a'.repeat( 64 ),
		input,
		lines: [
			{ product_id: 3556, quantity: 1 },
			{ product_id: 3611, quantity: 1 },
		],
	} );
} );

test( 'a German page saves in German, so the answered URL is the German account page', async () => {
	const fetcher = vi.fn< typeof fetch >(
		async () =>
			new Response(
				JSON.stringify( {
					id: 0,
					url: 'https://site.test/de/mein-konto/gespeicherte-loesungen/',
				} ),
				{ status: 202 }
			)
	);
	const saved = await saveSolution(
		'https://site.test/wp-json/',
		'nonce-1',
		{
			kind: 'residential',
			title: 'Haus München',
			input,
			lines: [ { productId: 3556, quantity: 1 } ],
		},
		'de',
		fetcher
	);
	expect( fetcher.mock.calls[ 0 ][ 0 ] ).toBe(
		'https://site.test/wp-json/linker/v1/solutions?lang=de'
	);
	expect( saved.url ).toBe(
		'https://site.test/de/mein-konto/gespeicherte-loesungen/'
	);
} );

test( 'posts the design report as the base64 PDF the route already accepts', async () => {
	const bytes = new Uint8Array( [
		0x25, 0x50, 0x44, 0x46, 0x2d, 0xff, 0x00, 0x80,
	] );
	const fetcher = vi.fn< typeof fetch >(
		async () =>
			new Response(
				JSON.stringify( { id: 62, url: '/my-account/solutions/62/' } ),
				{ status: 201 }
			)
	);
	await saveSolution(
		'https://site.test/wp-json/',
		'nonce-1',
		{
			kind: 'residential',
			title: 'Munich home',
			input,
			lines: [],
			reportPdf: new Blob( [ bytes ], { type: 'application/pdf' } ),
		},
		'en',
		fetcher
	);
	const posted = JSON.parse( String( fetcher.mock.calls[ 0 ][ 1 ]?.body ) );
	expect( posted.report_pdf ).toBe(
		Buffer.from( bytes ).toString( 'base64' )
	);
	expect( posted.kind ).toBe( 'residential' );
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
			'en',
			fetcher
		)
	).rejects.toThrow( 'save 403' );
} );
