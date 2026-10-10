// @vitest-environment node

/**
 * The SSE answer parser: meta, blocks, the mandatory done event, and the vote
 * call (docs/specs/13-genie.md).
 */

/**
 * External dependencies
 */
import { afterEach, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import { parseStream, sendVote } from './turn';

afterEach( () => {
	vi.restoreAllMocks();
} );

test( 'meta and every block come out in order', () => {
	const turn = parseStream(
		'event: meta\n' +
			'data: {"turn_id":7,"grounded":true,"fallback":false,"attempts":1,"failures":[],"language":"en"}\n\n' +
			'event: block\n' +
			'data: {"type":"text","text":"These three fit.","refs":["p3556"]}\n\n' +
			'event: block\n' +
			'data: {"type":"cards","product_ids":[3556,3555]}\n\n' +
			'event: block\n' +
			'data: {"type":"handoff","summary":"Installation is out of scope."}\n\n' +
			'event: done\n' +
			'data: {"ok":true}\n\n'
	);
	expect( turn.meta ).toEqual( {
		turn_id: 7,
		grounded: true,
		fallback: false,
		attempts: 1,
		failures: [],
		language: 'en',
	} );
	expect( turn.blocks.map( ( block ) => block.type ) ).toEqual( [
		'text',
		'cards',
		'handoff',
	] );
} );

test( 'a stream without done is an error, not a partial answer', () => {
	expect( () => parseStream( '' ) ).toThrow( 'stream without done' );
	expect( () =>
		parseStream(
			'event: meta\n' +
				'data: {"grounded":true,"fallback":false,"attempts":1,"failures":[],"language":"en"}\n\n'
		)
	).toThrow( 'stream without done' );
} );

test( 'sendVote posts to the turn and reports the answer', async () => {
	const fetcher = vi.fn(
		async () => new Response( '{"ok":true}', { status: 200 } )
	);
	await expect(
		sendVote( '/wp-json/linker-ai/v1/genie/turn', 'n', 7, -1, fetcher )
	).resolves.toBe( true );
	expect( fetcher ).toHaveBeenCalledWith(
		'/wp-json/linker-ai/v1/genie/turn/7/vote',
		{
			method: 'POST',
			credentials: 'same-origin',
			headers: {
				'Content-Type': 'application/json',
				'X-WP-Nonce': 'n',
			},
			body: JSON.stringify( { vote: -1 } ),
		}
	);
} );

test( 'a failed vote is best effort, never an exception', async () => {
	const fetcher = vi.fn( async () => {
		throw new Error( 'offline' );
	} );
	await expect(
		sendVote( '/wp-json/linker-ai/v1/genie/turn', 'n', 7, 1, fetcher )
	).resolves.toBe( false );
} );
