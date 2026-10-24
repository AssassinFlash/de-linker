// @vitest-environment jsdom
import { expect, test, vi } from 'vitest';
import { saveGenieSolution, GenieSaveUnconfirmedError } from './solution';
import { SolutionWriteError } from '../../configurator/api/solutions';

function cart() {
	return new Response( JSON.stringify( { items: [] } ), {
		headers: { Nonce: 'woo-session' },
	} );
}

test( 'the current Genie list saves only its signed proof, with native session nonce and locale', async () => {
	const fetcher = vi
		.fn< typeof fetch >()
		.mockResolvedValueOnce( cart() )
		.mockResolvedValueOnce(
			new Response(
				JSON.stringify( {
					id: 3,
					url: '/de/mein-konto/gespeicherte-loesungen/#linker-solution-3',
				} ),
				{ status: 201 }
			)
		);
	const saved = await saveGenieSolution(
		'/wp-json/',
		'wp-nonce',
		'exact-signed-list',
		'de',
		fetcher
	);
	expect( saved.id ).toBe( 3 );
	expect( fetcher.mock.calls[ 1 ][ 0 ] ).toBe(
		'/wp-json/linker-ai/v1/genie/solution?lang=de'
	);
	const init = fetcher.mock.calls[ 1 ][ 1 ]!;
	expect( JSON.parse( String( init.body ) ) ).toEqual( {
		proof: 'exact-signed-list',
	} );
	expect( new Headers( init.headers ).get( 'Nonce' ) ).toBe( 'woo-session' );
	expect( new Headers( init.headers ).get( 'X-WP-Nonce' ) ).toBe(
		'wp-nonce'
	);
} );

test( 'history without a current proof makes no save request', async () => {
	const fetcher = vi.fn< typeof fetch >();
	await expect(
		saveGenieSolution( '/wp-json/', 'n', '', 'en', fetcher )
	).rejects.toMatchObject( { changed: true } );
	expect( fetcher ).not.toHaveBeenCalled();
} );

test( 'a definite current-list refusal is distinct from a lost POST response', async () => {
	const stale = vi
		.fn< typeof fetch >()
		.mockResolvedValueOnce( cart() )
		.mockResolvedValueOnce(
			new Response(
				JSON.stringify( { code: 'linker_solution_changed' } ),
				{ status: 409 }
			)
		);
	await expect(
		saveGenieSolution( '/wp-json/', 'n', 'signed', 'en', stale )
	).rejects.toBeInstanceOf( SolutionWriteError );
	const lost = vi
		.fn< typeof fetch >()
		.mockResolvedValueOnce( cart() )
		.mockRejectedValueOnce(
			new TypeError( 'connection reset after commit' )
		);
	await expect(
		saveGenieSolution( '/wp-json/', 'n', 'signed', 'en', lost )
	).rejects.toBeInstanceOf( GenieSaveUnconfirmedError );
} );

test( 'an ambiguous server error does not claim the list was not saved', async () => {
	const fetcher = vi
		.fn< typeof fetch >()
		.mockResolvedValueOnce( cart() )
		.mockResolvedValueOnce( new Response( '', { status: 502 } ) );
	await expect(
		saveGenieSolution( '/wp-json/', 'n', 'signed', 'en', fetcher )
	).rejects.toBeInstanceOf( GenieSaveUnconfirmedError );
} );
