import { expect, test, vi } from 'vitest';
import { sendTurn } from './turn';

test( 'a change of conversation owner before dispatch sends no question', async () => {
	const fetcher = vi.fn< typeof fetch >();
	const result = sendTurn( {
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		nonce: 'wp',
		locale: 'en',
		page: { type: 'other' },
		messages: [ { role: 'user', content: 'My saved plan' } ],
		fetcher,
		owner: {
			signal: new AbortController().signal,
			beforeDispatch: async () => {
				throw new Error( 'verification_cancelled' );
			},
			onDispatch: vi.fn(),
		},
	} );
	await expect( result ).rejects.toThrow( 'verification_cancelled' );
	expect( fetcher ).not.toHaveBeenCalled();
} );

test.each( [
	[ 'helper', 'floating', 'faq' ],
	[ 'workspace', 'workspace', 'other' ],
	[ 'hero', 'hero', 'home' ],
] as const )(
	'a question sent from %s reports the %s surface and %s page',
	async ( surface, expected, type ) => {
		const track = vi.fn();
		window.linkerTrack = track;
		try {
			const fetcher = vi.fn< typeof fetch >( async () =>
				Response.json( { code: 'unavailable' }, { status: 503 } )
			);
			await expect(
				sendTurn( {
					surface,
					turnUrl: '/wp-json/linker-ai/v1/genie/turn',
					nonce: 'wp',
					locale: 'en',
					page: { type },
					messages: [
						{ role: 'user', content: 'private@example.invalid' },
					],
					fetcher,
				} )
			).rejects.toThrow();
			expect( fetcher ).toHaveBeenCalledTimes( 1 );
			expect( track.mock.calls ).toEqual( [
				[ 'genie_ask', { surface: expected, page_type: type } ],
			] );
		} finally {
			delete window.linkerTrack;
		}
	}
);
