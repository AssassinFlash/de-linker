/**
 * External dependencies
 */
import { afterEach, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { AccountsApi } from './api';

afterEach( () => vi.unstubAllGlobals() );

test.each( [
	[
		'https://example.test/wp-json/linker/v1/accounts',
		'https://example.test/wp-json/linker/v1/accounts/17/approval',
	],
	[
		'https://example.test/?rest_route=%2Flinker%2Fv1%2Faccounts',
		'https://example.test/?rest_route=%2Flinker%2Fv1%2Faccounts%2F17%2Fapproval',
	],
] )(
	'decision is a nonce-authenticated POST for %s',
	async ( base, destination ) => {
		const fetch = vi
			.fn()
			.mockResolvedValue( { ok: true, json: async () => ( {} ) } );
		vi.stubGlobal( 'fetch', fetch );
		await new AccountsApi( base, 'staff-nonce' ).decide(
			17,
			'restricted',
			'Missing website'
		);
		const localized = new URL( destination );
		localized.searchParams.set( '_locale', 'user' );
		expect( fetch ).toHaveBeenCalledWith(
			localized.href,
			expect.objectContaining( {
				method: 'POST',
				credentials: 'same-origin',
				headers: {
					'Content-Type': 'application/json',
					'X-WP-Nonce': 'staff-nonce',
				},
				body: JSON.stringify( {
					status: 'restricted',
					reason: 'Missing website',
				} ),
			} )
		);
	}
);

test( 'a failed REST response is not reported as a saved decision', async () => {
	vi.stubGlobal(
		'fetch',
		vi.fn().mockResolvedValue( {
			ok: false,
			json: async () => ( { message: 'No permission' } ),
		} )
	);
	await expect(
		new AccountsApi(
			'https://example.test/wp-json/linker/v1/accounts',
			'nonce'
		).decide( 17, 'approved', '' )
	).rejects.toThrow( 'No permission' );
} );
