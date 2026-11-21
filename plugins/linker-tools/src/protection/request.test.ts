import { expect, test, vi } from 'vitest';
import { resourceFetch } from './request';

test( 'a normal turn makes one native request and keeps its identity after a lost reply', async () => {
	const ids: string[] = [];
	const transport = vi.fn< typeof fetch >( async ( input, init ) => {
		expect( String( input ) ).toBe( '/wp-json/linker-ai/v1/genie/turn' );
		const headers = new Headers( init?.headers );
		expect( headers.get( 'X-Linker-Proof' ) ).toBeNull();
		ids.push( headers.get( 'X-Linker-Operation' ) ?? '' );
		if ( ids.length === 1 ) {
			throw new TypeError( 'Lost reply' );
		}
		return new Response( '{}' );
	} );
	const init = { method: 'POST', body: '{"message":"Saved selection"}' };
	const url = '/wp-json/linker-ai/v1/genie/turn';
	await expect( resourceFetch( transport, url, init ) ).rejects.toThrow(
		'Lost reply'
	);
	await resourceFetch( transport, url, init );
	await resourceFetch( transport, url, init );
	expect( ids[ 0 ] ).toBeTruthy();
	expect( ids[ 1 ] ).toBe( ids[ 0 ] );
	expect( ids[ 2 ] ).not.toBe( ids[ 0 ] );
	expect( transport ).toHaveBeenCalledTimes( 3 );
} );

test( 'viewing a conversation needs only its native read', async () => {
	const transport = vi.fn< typeof fetch >( async () => new Response( '{}' ) );
	await resourceFetch(
		transport,
		'/wp-json/linker-ai/v1/genie/conversation'
	);
	expect( transport ).toHaveBeenCalledWith(
		'/wp-json/linker-ai/v1/genie/conversation',
		undefined
	);
} );
