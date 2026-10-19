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
import {
	assistantMessage,
	emailConversation,
	isUnfinishedStream,
	parseStream,
	readThread,
	sendTurn,
	sendVote,
	TURN_TIMEOUT_MS,
} from './turn';

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
	let unfinished: unknown;
	try {
		parseStream(
			'event: meta\n' +
				'data: {"grounded":true,"fallback":false,"attempts":1,"failures":[],"language":"en"}\n\n' +
				'event: block\n' +
				'data: {"type":"text","text":"10 kW from a cut stream","refs":[]}\n\n'
		);
	} catch ( error ) {
		unfinished = error;
	}
	expect( isUnfinishedStream( unfinished ) ).toBe( true );
	expect( isUnfinishedStream( new Error( 'stream without done' ) ) ).toBe(
		false
	);
	expect( isUnfinishedStream( new Error( 'turn 502' ) ) ).toBe( false );
} );

test( 'a connection that never answers is the upstream timeout', async () => {
	vi.useFakeTimers();
	const fetcher = vi.fn( () => new Promise< Response >( () => undefined ) );
	const hung = sendTurn(
		'/wp-json/linker-ai/v1/genie/turn',
		'n',
		'en',
		[ { role: 'user', content: 'backup for 10 kW' } ],
		{ type: 'category' },
		[],
		fetcher,
		TURN_TIMEOUT_MS
	);
	const timedOut = hung.then(
		() => {
			throw new Error( 'the hung turn resolved' );
		},
		( error: unknown ) => error
	);
	try {
		await vi.advanceTimersByTimeAsync( TURN_TIMEOUT_MS );
		await expect( timedOut ).resolves.toMatchObject( {
			name: 'AbortError',
		} );
		expect( fetcher ).toHaveBeenCalledTimes( 1 );
	} finally {
		vi.useRealTimers();
	}
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

test( 'a reload reads the stored thread back and re-adds the last answer', async () => {
	const stream =
		'event: meta\n' +
		'data: {"turn_id":9,"grounded":true,"fallback":false,"attempts":1,"failures":[],"language":"en"}\n\n' +
		'event: block\n' +
		'data: {"type":"text","text":"Two of them fit.","refs":["3556"]}\n\n' +
		'event: block\n' +
		'data: {"type":"cards","product_ids":[3556]}\n\n' +
		'event: done\n' +
		'data: {"ok":true}\n\n';
	const fetchDouble = vi.fn( async () => ( {
		ok: true,
		json: async () => ( {
			conversation_id: 12,
			messages: [ { role: 'user', content: 'Which inverters fit?' } ],
			stream,
		} ),
	} ) ) as unknown as typeof fetch;

	const thread = await readThread(
		'/wp-json/linker-ai/v1/genie/conversation',
		'n',
		fetchDouble
	);

	expect( thread.messages.map( ( message ) => message.content ) ).toEqual( [
		'Which inverters fit?',
		'Two of them fit.',
	] );
	expect( thread.turn?.blocks ).toHaveLength( 2 );
	expect( thread.messages[ 1 ].turnId ).toBe( 9 );
} );

test( 'a reload without a conversation answers empty, and a truncated stream keeps the words', async () => {
	const empty = vi.fn( async () => ( {
		ok: true,
		json: async () => ( { conversation_id: 0, messages: [], stream: '' } ),
	} ) ) as unknown as typeof fetch;
	expect( await readThread( '/thread', 'n', empty ) ).toEqual( {
		messages: [],
		turn: null,
		inquiries: [],
		contacts: [],
	} );

	const truncated = vi.fn( async () => ( {
		ok: true,
		json: async () => ( {
			conversation_id: 12,
			messages: [ { role: 'user', content: 'Hello' } ],
			stream: 'event: meta\ndata: {"grounded":true}\n\n',
		} ),
	} ) ) as unknown as typeof fetch;
	const thread = await readThread( '/thread', 'n', truncated );
	expect( thread.messages ).toEqual( [ { role: 'user', content: 'Hello' } ] );
	expect( thread.turn ).toBeNull();

	const failing = vi.fn( async () => ( {
		ok: false,
	} ) ) as unknown as typeof fetch;
	expect( await readThread( '/thread', 'n', failing ) ).toEqual( {
		messages: [],
		turn: null,
		contacts: [],
		inquiries: [],
	} );
} );

test( 'an assistant message is the turn text, wherever it came from', () => {
	const turn = parseStream(
		'event: meta\n' +
			'data: {"turn_id":3,"grounded":true,"fallback":false,"attempts":1,"failures":[],"language":"en"}\n\n' +
			'event: block\n' +
			'data: {"type":"text","text":"First.","refs":[]}\n\n' +
			'event: block\n' +
			'data: {"type":"cards","product_ids":[3556]}\n\n' +
			'event: block\n' +
			'data: {"type":"text","text":"Second.","refs":[]}\n\n' +
			'event: done\n' +
			'data: {"ok":true}\n\n'
	);
	expect( assistantMessage( turn ) ).toEqual( {
		role: 'assistant',
		content: 'First. Second.',
		turnId: 3,
	} );
} );

test( 'an email answer reads the outcome from the route, refusals from their code', async () => {
	const answer = ( status: number, body: unknown ) =>
		vi.fn< typeof fetch >(
			async () => new Response( JSON.stringify( body ), { status } )
		);
	const guard = { started: '1', started_nonce: 'n', website: '' };

	const confirm = answer( 202, { status: 'confirm', to: 'a@example.test' } );
	expect(
		await emailConversation(
			'/c',
			'n',
			9,
			'de',
			'a@example.test',
			guard,
			confirm
		)
	).toEqual( { outcome: 'confirm', to: 'a@example.test', limit: 0 } );
	expect(
		JSON.parse( String( confirm.mock.calls[ 0 ]?.[ 1 ]?.body ) )
	).toEqual( {
		locale: 'de',
		email: 'a@example.test',
		started: '1',
		started_nonce: 'n',
		website: '',
	} );

	expect(
		await emailConversation(
			'/c',
			'n',
			9,
			'en',
			undefined,
			undefined,
			answer( 429, {
				code: 'linker_genie_email_capped',
				data: { status: 429, limit: 3 },
			} )
		)
	).toEqual( { outcome: 'capped', to: '', limit: 3 } );
	expect(
		await emailConversation(
			'/c',
			'n',
			9,
			'en',
			undefined,
			undefined,
			answer( 500, { code: 'rest_error' } )
		)
	).toEqual( { outcome: 'unavailable', to: '', limit: 0 } );
} );

test( 'a reload keeps the sent contact cards where they were (#243)', async () => {
	const fetchDouble = vi.fn( async () => ( {
		ok: true,
		json: async () => ( {
			conversation_id: 12,
			messages: [
				{ role: 'user', content: 'Can I talk to a person?' },
				{ role: 'assistant', content: 'Someone can get in touch.' },
				{ role: 'user', content: 'Which battery fits?' },
			],
			stream: '',
			contacts: [
				{ after: 1, email: 'maria@example.test' },
				{ after: 'x', email: 'broken' },
			],
		} ),
	} ) ) as unknown as typeof fetch;
	const thread = await readThread( '/thread', 'n', fetchDouble );
	expect( thread.contacts ).toEqual( [
		{ after: 1, email: 'maria@example.test' },
	] );
} );
