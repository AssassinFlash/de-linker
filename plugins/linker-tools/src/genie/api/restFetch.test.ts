import { afterEach, expect, it, vi } from 'vitest';
import { genieFetch } from './restFetch';

afterEach( () => {
	vi.unstubAllGlobals();
	document.body.replaceChildren();
} );

it( 'resumes the original operation once after WordPress rejects the old cookie nonce', async () => {
	const mount = document.createElement( 'div' );
	mount.dataset.genieNonceUrl = '/wp-admin/admin-ajax.php?action=rest-nonce';
	document.body.append( mount );
	const stale = () =>
		Response.json( { code: 'rest_cookie_invalid_nonce' }, { status: 403 } );
	const transport = vi
		.fn< typeof fetch >()
		.mockResolvedValueOnce( stale() )
		.mockResolvedValueOnce( new Response( 'abcdefgh12' ) )
		.mockResolvedValueOnce( new Response( 'ok' ) )
		.mockResolvedValueOnce( new Response( 'again' ) );
	vi.stubGlobal( 'fetch', transport );
	const request = {
		method: 'POST',
		body: '{"question":"Which inverter?"}',
		headers: {
			'X-WP-Nonce': 'oldnonce01',
			'X-Linker-Operation': 'first-turn',
		},
	};
	const url = '/wp-json/linker-ai/v1/genie/turn/start';
	expect( await ( await genieFetch( url, request ) ).text() ).toBe( 'ok' );
	expect( transport.mock.calls[ 1 ][ 0 ] ).toBe(
		mount.dataset.genieNonceUrl
	);
	expect( transport.mock.calls[ 2 ][ 1 ]?.body ).toBe( request.body );
	expect(
		new Headers( transport.mock.calls[ 2 ][ 1 ]?.headers ).get(
			'X-Linker-Operation'
		)
	).toBe( 'first-turn' );
	await genieFetch( url, request );
	expect(
		new Headers( transport.mock.calls[ 3 ][ 1 ]?.headers ).get(
			'X-WP-Nonce'
		)
	).toBe( 'abcdefgh12' );
	expect( transport ).toHaveBeenCalledTimes( 4 );
} );

it( 'returns ownership refusals without replaying the request', async () => {
	const response = Response.json( { code: 'not_owner' }, { status: 403 } );
	const transport = vi.fn< typeof fetch >().mockResolvedValue( response );
	vi.stubGlobal( 'fetch', transport );
	expect(
		await genieFetch( '/thread', { headers: { 'X-WP-Nonce': 'valid' } } )
	).toBe( response );
	expect( transport ).toHaveBeenCalledTimes( 1 );
} );

it( 'keeps an expired anonymous page usable when core confirms the visitor is still a guest', async () => {
	const mount = document.createElement( 'div' );
	mount.dataset.genieNonceUrl = '/wp-admin/admin-ajax.php?action=rest-nonce';
	mount.dataset.signedIn = '0';
	document.body.append( mount );
	const transport = vi
		.fn< typeof fetch >()
		.mockResolvedValueOnce(
			Response.json(
				{ code: 'rest_cookie_invalid_nonce' },
				{ status: 403 }
			)
		)
		.mockResolvedValueOnce( new Response( '0', { status: 400 } ) )
		.mockResolvedValueOnce( new Response( 'ok' ) );
	vi.stubGlobal( 'fetch', transport );
	await genieFetch( '/thread', { headers: { 'X-WP-Nonce': 'guest-stale' } } );
	expect( transport ).toHaveBeenCalledTimes( 3 );
	expect(
		new Headers( transport.mock.calls[ 2 ][ 1 ]?.headers ).has(
			'X-WP-Nonce'
		)
	).toBe( false );
} );

it( 'returns the second 403 without starting another renewal', async () => {
	const mount = document.createElement( 'div' );
	mount.dataset.genieNonceUrl = '/wp-admin/admin-ajax.php?action=rest-nonce';
	document.body.append( mount );
	const denial = () =>
		Response.json( { code: 'rest_cookie_invalid_nonce' }, { status: 403 } );
	const transport = vi
		.fn< typeof fetch >()
		.mockResolvedValueOnce( denial() )
		.mockResolvedValueOnce( new Response( 'refreshed1' ) )
		.mockResolvedValueOnce( denial() );
	vi.stubGlobal( 'fetch', transport );
	expect(
		(
			await genieFetch( '/thread', {
				headers: { 'X-WP-Nonce': 'stale' },
			} )
		).status
	).toBe( 403 );
	expect( transport ).toHaveBeenCalledTimes( 3 );
} );
