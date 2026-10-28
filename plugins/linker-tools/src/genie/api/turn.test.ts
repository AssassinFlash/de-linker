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
	const source = {
		type: 'planning_sources',
		schema_version: 1,
		status: 'available',
		binding: {
			planning_project_id: 'a'.repeat( 32 ),
			planning_revision: 3,
			planning_run_ids: [ 'b'.repeat( 32 ) ],
			runs: [
				{
					id: 'b'.repeat( 32 ),
					revision: 2,
					manifest_sha256: 'c'.repeat( 64 ),
					result_sha256: 'd'.repeat( 64 ),
				},
			],
		},
		results: [
			{
				revision: 2,
				groups: [
					{
						kind: 'pv',
						role: 'selected',
						input_quantity: 'pv_available_ac',
						source_scope: 'whole_reference',
						timezone: 'Europe/Paris',
						periods_utc: [
							{
								start_utc: '2023-06-16T09:00:00+00:00',
								end_utc: '2023-06-16T11:00:00+00:00',
							},
						],
					},
				],
			},
		],
		url: 'https://de-linker.test/solution-configurator/',
	};
	const sourceStream = ( block: unknown ) =>
		`event: block\ndata: ${ JSON.stringify( block ) }\n\nevent: done\ndata: {}\n\n`;
	const unavailable = [
		{ type: 'planning_sources', schema_version: 1, status: 'unavailable' },
	];
	expect( parseStream( sourceStream( source ) ).blocks ).toEqual( [
		source,
	] );
	expect(
		parseStream(
			sourceStream( {
				...source,
				results: [
					{
						revision: 2,
						groups: [
							{
								...source.results[ 0 ].groups[ 0 ],
								input_quantity: 'guessed-port',
							},
						],
					},
				],
			} )
		).blocks
	).toEqual( unavailable );
	expect(
		parseStream(
			sourceStream( {
				...source,
				binding: {
					...source.binding,
					planning_project_id: 'not-an-owned-reference',
				},
			} )
		).blocks
	).toEqual( unavailable );
	expect(
		parseStream(
			sourceStream( {
				...source,
				results: [ { ...source.results[ 0 ], revision: 4 } ],
			} )
		).blocks
	).toEqual( unavailable );
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

test( 'a completed service turn survives native request overhead beyond the model budget', async () => {
	vi.useFakeTimers();
	const fetcher = vi.fn( async () => {
		await new Promise( ( resolve ) => setTimeout( resolve, 60_001 ) );
		return {
			ok: true,
			json: async () => ( {
				stream:
					'event: block\ndata: {"type":"text","text":"25000 W","refs":[]}\n\n' +
					'event: done\ndata: {"ok":true}\n\n',
			} ),
		} as Response;
	} );
	const outcome = sendTurn( {
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		nonce: 'n',
		locale: 'en',
		messages: [ { role: 'user', content: 'rated AC power' } ],
		page: { type: 'category' },
		fetcher,
	} ).then(
		( turn ) => turn,
		( error: unknown ) => error
	);
	try {
		await vi.advanceTimersByTimeAsync( 60_001 );
		await expect( outcome ).resolves.toMatchObject( {
			blocks: [ { type: 'text', text: '25000 W' } ],
		} );
		expect( vi.getTimerCount() ).toBe( 0 );
	} finally {
		vi.useRealTimers();
	}
} );

test( 'a connection that never answers is the upstream timeout', async () => {
	vi.useFakeTimers();
	const fetcher = vi.fn( () => new Promise< Response >( () => undefined ) );
	const hung = sendTurn( {
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		nonce: 'n',
		locale: 'en',
		messages: [ { role: 'user', content: 'backup for 10 kW' } ],
		page: { type: 'category' },
		fetcher,
		timeoutMs: TURN_TIMEOUT_MS,
	} );
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

test( 'headers without a body are the upstream timeout too', async () => {
	vi.useFakeTimers();
	// The proxy answered its headers, then stopped: json() never settles.
	const fetcher = vi.fn( async () => ( {
		ok: true,
		json: () => new Promise< never >( () => undefined ),
	} ) ) as unknown as typeof fetch;
	const hung = sendTurn( {
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		nonce: 'n',
		locale: 'en',
		messages: [ { role: 'user', content: 'backup for 10 kW' } ],
		page: { type: 'category' },
		fetcher,
		timeoutMs: TURN_TIMEOUT_MS,
	} );
	const timedOut = hung.then(
		() => {
			throw new Error( 'the stalled body resolved' );
		},
		( error: unknown ) => error
	);
	try {
		await vi.advanceTimersByTimeAsync( TURN_TIMEOUT_MS );
		await expect( timedOut ).resolves.toMatchObject( {
			name: 'AbortError',
		} );
		expect( fetcher ).toHaveBeenCalledTimes( 1 );
		expect( vi.getTimerCount() ).toBe( 0 );
	} finally {
		vi.useRealTimers();
	}
} );

test( 'a refusal whose body stalls is the timeout, not an empty refusal code', async () => {
	vi.useFakeTimers();
	const fetcher = vi.fn( async () => ( {
		ok: false,
		status: 502,
		json: () => new Promise< never >( () => undefined ),
	} ) ) as unknown as typeof fetch;
	const hung = sendTurn( {
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		nonce: 'n',
		locale: 'en',
		messages: [ { role: 'user', content: 'backup for 10 kW' } ],
		page: { type: 'category' },
		fetcher,
		timeoutMs: TURN_TIMEOUT_MS,
	} );
	const timedOut = hung.then(
		() => {
			throw new Error( 'the stalled refusal resolved' );
		},
		( error: unknown ) => error
	);
	try {
		await vi.advanceTimersByTimeAsync( TURN_TIMEOUT_MS );
		await expect( timedOut ).resolves.toMatchObject( {
			name: 'AbortError',
		} );
		expect( vi.getTimerCount() ).toBe( 0 );
	} finally {
		vi.useRealTimers();
	}
} );

test( 'a fetcher that throws before the request does not leave the timer armed', async () => {
	vi.useFakeTimers();
	const fetcher = () => {
		throw new Error( 'sync' );
	};
	const failed = sendTurn( {
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		nonce: 'n',
		locale: 'en',
		messages: [ { role: 'user', content: 'backup for 10 kW' } ],
		page: { type: 'category' },
		fetcher,
		timeoutMs: TURN_TIMEOUT_MS,
	} ).then(
		() => {
			throw new Error( 'the turn resolved' );
		},
		( error: unknown ) => error
	);
	try {
		await expect( failed ).resolves.toMatchObject( { message: 'sync' } );
		expect( vi.getTimerCount() ).toBe( 0 );
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
	expect( thread.conversationId ).toBe( 12 );
	expect( thread.messages[ 1 ].turnId ).toBe( 9 );
	const unavailable = {
		type: 'planning_sources',
		schema_version: 1,
		status: 'unavailable',
	};
	const stored = {
		conversation_id: 12,
		messages: [ { role: 'user', content: 'Explain the saved result.' } ],
		stream: `event: block\ndata: ${ JSON.stringify( unavailable ) }\n\nevent: done\ndata: {}\n\n`,
	};
	const context = { restUrl: '/wp-json/', locale: 'en' as const };
	const session = {
		schema_version: 1,
		kind: 'guest',
		cookie_confirmed: true,
		expires_at: Math.floor( Date.now() / 1000 ) + 3600,
		query_scope: 'a'.repeat( 64 ),
		nonce: 'fresh-proof',
	};
	const readback = vi.fn< typeof fetch >(
		async () => new Response( JSON.stringify( stored ) )
	);
	// A passive reload forwards cached proof but cannot bootstrap an owner.
	await readThread( '/thread', 'n', readback, context, {
		plannerNonce: 'cached-proof',
	} );
	expect(
		readback.mock.calls.filter(
			( [ url ] ) => ! String( url ).endsWith( '/publication/manifest' )
		)
	).toHaveLength( 1 );
	expect( readback.mock.calls[ 0 ][ 1 ] ).toMatchObject( {
		headers: { 'X-Linker-Planner-Nonce': 'cached-proof' },
	} );
	readback.mockClear();
	readback
		.mockResolvedValueOnce( new Response( JSON.stringify( stored ) ) )
		.mockResolvedValueOnce( new Response( JSON.stringify( session ) ) )
		.mockResolvedValueOnce( new Response( JSON.stringify( stored ) ) );
	const remember = vi.fn();
	const recovered = await readThread( '/thread', 'n', readback, context, {
		plannerNonce: 'expired-proof',
		allowExistingOwnerBootstrap: true,
		onPlannerNonce: remember,
	} );
	expect(
		readback.mock.calls.filter(
			( [ url ] ) => ! String( url ).endsWith( '/publication/manifest' )
		)
	).toHaveLength( 3 );
	expect( readback.mock.calls[ 1 ] ).toEqual( [
		'/wp-json/linker/v1/planner/bootstrap',
		expect.objectContaining( {
			method: 'POST',
			credentials: 'same-origin',
			body: JSON.stringify( {
				schema_version: 1,
				existing_owner_only: true,
			} ),
		} ),
	] );
	expect( readback.mock.calls[ 2 ][ 1 ] ).toMatchObject( {
		headers: { 'X-Linker-Planner-Nonce': 'fresh-proof' },
	} );
	expect( remember ).toHaveBeenCalledWith( 'fresh-proof' );
	expect( recovered.turn?.blocks ).toEqual( [ unavailable ] ); // No retry loop on revoked/mismatched result proof.
	readback.mockClear();
	readback
		.mockResolvedValueOnce( new Response( JSON.stringify( stored ) ) )
		.mockResolvedValueOnce(
			new Response(
				JSON.stringify( { ...session, cookie_confirmed: false } )
			)
		);
	const refused = await readThread( '/thread', 'n', readback, context, {
		allowExistingOwnerBootstrap: true,
	} );
	expect(
		readback.mock.calls.filter(
			( [ url ] ) => ! String( url ).endsWith( '/publication/manifest' )
		)
	).toHaveLength( 2 );
	expect( refused.turn?.blocks ).toEqual( [ unavailable ] );
	readback.mockClear();
	readback
		.mockResolvedValueOnce( new Response( JSON.stringify( stored ) ) )
		.mockResolvedValueOnce( new Response( JSON.stringify( session ) ) )
		.mockResolvedValueOnce(
			new Response(
				JSON.stringify( {
					...stored,
					stream: 'event: meta\ndata: {}\n\n',
				} )
			)
		);
	const incomplete = await readThread( '/thread', 'n', readback, context, {
		allowExistingOwnerBootstrap: true,
	} );
	expect( incomplete.turn?.blocks ).toEqual( [ unavailable ] );
	expect( incomplete.messages[ 0 ].content ).toBe(
		'Explain the saved result.'
	);
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
		await emailConversation(
			'/c',
			'n',
			9,
			'en',
			undefined,
			undefined,
			answer( 202, { status: 'pending', to: 'a@example.test' } )
		)
	).toEqual( { outcome: 'pending', to: 'a@example.test', limit: 0 } );
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

test( 'a complete answer near its connection deadline survives a slow auxiliary metadata read, with its live price unchanged', async () => {
	vi.useFakeTimers();
	const stream = [
		[ 'block', { type: 'text', text: 'A valid answer.', refs: [] } ],
		[
			'block',
			{
				type: 'cards',
				product_ids: [ 3573 ],
				prices: [
					{
						product_id: 3573,
						text: 'Current service line',
						reason: 'login',
					},
				],
			},
		],
		[
			'block',
			{
				type: 'document',
				ref: 'p3573.document.0',
				document_id: 'doc',
				document_revision: 'revision-1',
				label: 'Old label · p. 1',
				url: 'https://de-linker.test/file.pdf#page=1',
			},
		],
		[ 'done', { ok: true } ],
	]
		.map(
			( [ event, data ] ) =>
				`event: ${ event }\ndata: ${ JSON.stringify( data ) }\n\n`
		)
		.join( '' );
	let release!: () => void;
	const fetcher = vi.fn( async ( url: RequestInfo | URL ) => {
		if ( String( url ) === '/turn' ) {
			return {
				ok: true,
				json: () =>
					new Promise( ( resolve ) => {
						release = () => resolve( { stream } );
					} ),
			} as unknown as Response;
		}
		if ( String( url ).endsWith( '/publication/manifest' ) ) {
			return {
				ok: true,
				json: async () => ( {
					schema_version: 1,
					products: [
						{ product_id: 3573, published_locale_ids: [ 3573 ] },
					],
					documents: [
						{
							document_id: 'doc',
							document_revision: 'revision-1',
							url: 'https://de-linker.test/file.pdf',
						},
					],
				} ),
			} as unknown as Response;
		}
		return {
			ok: true,
			json: () =>
				new Promise( ( resolve ) =>
					setTimeout(
						() =>
							resolve( {
								product_id: 3573,
								model: 'eSolar AIO3',
								documents: [
									{
										url: 'https://de-linker.test/file.pdf',
										type: 'datasheet',
										lang: 'en',
									},
								],
							} ),
						3_000
					)
				),
		} as unknown as Response;
	} );
	try {
		const result = sendTurn( {
			turnUrl: '/turn',
			restUrl: '/wp-json/',
			nonce: 'n',
			locale: 'en',
			messages: [],
			page: { type: 'home' },
			fetcher,
		} );
		await vi.advanceTimersByTimeAsync( TURN_TIMEOUT_MS - 2_000 );
		release();
		await vi.advanceTimersByTimeAsync( 3_000 );
		const turn = await result;
		expect( turn.blocks[ 1 ] ).toMatchObject( {
			prices: [ { text: 'Current service line' } ],
		} );
		expect( turn.blocks[ 2 ] ).toMatchObject( {
			label: 'eSolar AIO3 · Datasheet (EN) · p.\u00a01',
		} );
		expect( vi.getTimerCount() ).toBe( 0 );
	} finally {
		vi.useRealTimers();
	}
} );
