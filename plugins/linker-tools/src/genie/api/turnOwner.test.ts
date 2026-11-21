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
