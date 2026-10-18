// @vitest-environment jsdom

/**
 * An ask that starts while a conversation switch is still resolving must wait
 * for that switch, then send only the target conversation's thread.
 *
 * The control is the same ask after select has resolved and the new thread has
 * been read. Both must send the target thread. A switch that only guards
 * `sending` lets the in-flight ask keep the previous thread.
 */

/**
 * External dependencies
 */
import {
	act,
	fireEvent,
	render,
	screen,
	waitFor,
} from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { GenieConfig } from './config';
import { App, resetTurnLane } from './App';

type Read = {
	messages: { role: 'user' | 'assistant'; content: string }[];
	turn: null;
	contacts: [];
};

function deferred< T >() {
	let resolve!: ( value: T ) => void;
	const promise = new Promise< T >( ( settle ) => {
		resolve = settle;
	} );
	return { promise, resolve };
}

const reads: Array< ReturnType< typeof deferred< Read > > > = [];
let selectGate: ReturnType< typeof deferred< unknown > > | null = null;

vi.mock( './api/turn', async ( importOriginal ) => {
	const actual = await importOriginal< typeof import( './api/turn' ) >();
	return {
		assistantMessage: actual.assistantMessage,
		readThread: vi.fn( () => {
			const pending = deferred< Read >();
			reads.push( pending );
			return pending.promise;
		} ),
		listConversations: vi.fn( async () => ( {
			currentId: 7,
			ok: true,
			conversations: [
				{ id: 7, title: 'Seven', updated: '2026-10-12' },
				{ id: 8, title: 'Eight', updated: '2026-10-12' },
			],
		} ) ),
		selectConversation: vi.fn( () => {
			selectGate = deferred();
			return selectGate.promise;
		} ),
		sendTurn: vi.fn( async () => ( {
			meta: {
				turn_id: 1,
				grounded: true,
				fallback: false,
				attempts: 1,
				failures: [],
				language: 'en',
			},
			blocks: [ { type: 'text', text: 'answer', refs: [] } ],
		} ) ),
		sendVote: vi.fn( async () => true ),
	};
} );

import {
	listConversations,
	readThread,
	selectConversation,
	sendTurn,
} from './api/turn';

function hangReads() {
	vi.mocked( readThread ).mockImplementation( () => {
		const pending = deferred< Read >();
		reads.push( pending );
		return pending.promise;
	} );
}

beforeEach( () => {
	resetTurnLane();
	reads.length = 0;
	selectGate = null;
	hangReads();
	vi.mocked( selectConversation ).mockImplementation( () => {
		selectGate = deferred();
		return selectGate.promise as Promise< typeof listed >;
	} );
} );

const listed = {
	currentId: 8,
	ok: true,
	conversations: [
		{ id: 7, title: 'Seven', updated: '2026-10-12' },
		{ id: 8, title: 'Eight', updated: '2026-10-12' },
	],
};

function config(): GenieConfig {
	return {
		surface: 'workspace',
		locale: 'en',
		pageType: 'other',
		productId: 0,
		page: { type: 'other' },
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		threadUrl: '/wp-json/linker-ai/v1/genie/conversation',
		conversationsUrl: '/wp-json/linker-ai/v1/genie/conversations',
		voteUrl: '/wp-json/linker-ai/v1/genie/turn',
		restUrl: '/wp-json/',
		restNonce: 'n',
		disclosure: 'AI.',
		accountUrl: '/my-account/',
		workspaceUrl: '/genie/',
		contactUrl: '/wp-json/linker-ai/v1/genie/contact',
		inquiryUrl: '/wp-json/linker-ai/v1/genie/inquiry',
		prompts: [ 'Ask Genie' ],
		signedIn: false,
		retentionDays: 90,
		mailStarted: '1800000000',
		mailStartedNonce: 'stamp-nonce',
	};
}

function targetThread() {
	return [
		{ role: 'user', content: 'eight' },
		{ role: 'user', content: 'question for eight' },
	];
}

test( 'an ask that starts after select resolves still waits for the target thread', async () => {
	render( <App config={ config() } /> );

	await waitFor( () => expect( reads.length ).toBeGreaterThanOrEqual( 1 ) );
	reads[ 0 ].resolve( {
		messages: [ { role: 'user', content: 'seven' } ],
		turn: null,
		contacts: [],
	} );

	fireEvent.click( await screen.findByRole( 'button', { name: 'Eight' } ) );
	await waitFor( () => expect( selectGate ).not.toBeNull() );
	selectGate!.resolve( listed );

	await waitFor( () => expect( reads.length ).toBeGreaterThanOrEqual( 2 ) );
	const input = screen.getByRole( 'textbox' );
	fireEvent.change( input, { target: { value: 'question for eight' } } );
	fireEvent.submit( input.closest( 'form' )! );
	reads[ 1 ].resolve( {
		messages: [ { role: 'user', content: 'eight' } ],
		turn: null,
		contacts: [],
	} );

	await waitFor( () => expect( sendTurn ).toHaveBeenCalled() );
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ]![ 3 ] ).toEqual(
		targetThread()
	);
} );

test( 'control: an ask after the switch settles carries the new thread', async () => {
	vi.mocked( sendTurn ).mockClear();
	render( <App config={ config() } /> );

	await waitFor( () => expect( reads.length ).toBeGreaterThanOrEqual( 1 ) );
	reads[ 0 ].resolve( {
		messages: [ { role: 'user', content: 'seven' } ],
		turn: null,
		contacts: [],
	} );

	fireEvent.click( await screen.findByRole( 'button', { name: 'Eight' } ) );
	await waitFor( () => expect( selectGate ).not.toBeNull() );
	selectGate!.resolve( listed );

	await waitFor( () => expect( reads.length ).toBeGreaterThanOrEqual( 2 ) );
	reads[ 1 ].resolve( {
		messages: [ { role: 'user', content: 'eight' } ],
		turn: null,
		contacts: [],
	} );

	const input = await screen.findByRole( 'textbox' );
	fireEvent.change( input, { target: { value: 'question for eight' } } );
	fireEvent.submit( input.closest( 'form' )! );

	await waitFor( () => expect( sendTurn ).toHaveBeenCalled() );
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ]![ 3 ] ).toEqual(
		targetThread()
	);
} );

test( 'two history clicks in a row continue the last one, not the first', async () => {
	vi.mocked( sendTurn ).mockClear();
	const selects: Array< ReturnType< typeof deferred< unknown > > > = [];
	vi.mocked( selectConversation ).mockImplementation( () => {
		const pending = deferred();
		selects.push( pending );
		selectGate = pending;
		return pending.promise as Promise< typeof listed >;
	} );

	render( <App config={ config() } /> );
	await waitFor( () => expect( reads.length ).toBeGreaterThanOrEqual( 1 ) );
	reads[ 0 ].resolve( {
		messages: [ { role: 'user', content: 'seven' } ],
		turn: null,
		contacts: [],
	} );

	fireEvent.click( await screen.findByRole( 'button', { name: 'Eight' } ) );
	await waitFor( () => expect( selects.length ).toBe( 1 ) );
	fireEvent.click( screen.getByRole( 'button', { name: 'Seven' } ) );

	selects[ 0 ].resolve( listed );
	await waitFor( () => expect( reads.length ).toBeGreaterThanOrEqual( 2 ) );
	reads[ 1 ].resolve( {
		messages: [ { role: 'user', content: 'eight' } ],
		turn: null,
		contacts: [],
	} );
	await waitFor( () => expect( selects.length ).toBe( 2 ) );
	selects[ 1 ].resolve( {
		currentId: 7,
		ok: true,
		conversations: listed.conversations,
	} );
	await waitFor( () => expect( reads.length ).toBeGreaterThanOrEqual( 3 ) );
	reads[ 2 ].resolve( {
		messages: [ { role: 'user', content: 'seven' } ],
		turn: null,
		contacts: [],
	} );

	const input = await screen.findByRole( 'textbox' );
	fireEvent.change( input, { target: { value: 'question for seven' } } );
	fireEvent.submit( input.closest( 'form' )! );

	await waitFor( () => expect( sendTurn ).toHaveBeenCalled() );
	expect( vi.mocked( sendTurn ).mock.calls[ 0 ]![ 3 ] ).toEqual( [
		{ role: 'user', content: 'seven' },
		{ role: 'user', content: 'question for seven' },
	] );
	expect(
		vi.mocked( selectConversation ).mock.calls.map( ( call ) => call[ 2 ] )
	).toEqual( [ 8, 7 ] );
} );

test( 'a history refresh started by an ask cannot put the old conversation back', async () => {
	vi.mocked( sendTurn ).mockClear();
	const slow = deferred< void >();
	let stale = {
		currentId: 7,
		ok: true,
		conversations: [
			{ id: 7, title: 'Seven', updated: '2026-10-12' },
			{ id: 8, title: 'Eight', updated: '2026-10-12' },
		],
	};
	vi.mocked( listConversations ).mockImplementation( async () => {
		await slow.promise;
		return stale;
	} );
	vi.mocked( selectConversation ).mockImplementation( async () => ( {
		currentId: 9,
		ok: true,
		conversations: [
			{ id: 8, title: 'Eight', updated: '2026-10-12' },
			{ id: 9, title: 'Nine', updated: '2026-10-12' },
		],
	} ) );

	render( <App config={ config() } /> );
	await waitFor( () => expect( reads.length ).toBeGreaterThanOrEqual( 1 ) );
	await act( async () => {
		reads[ 0 ].resolve( { messages: [], turn: null, contacts: [] } );
	} );
	await waitFor( () =>
		expect( listConversations ).toHaveBeenCalledTimes( 1 )
	);
	slow.resolve();
	await screen.findByRole( 'button', { name: 'Eight' } );
	expect( screen.getByRole( 'button', { name: 'Seven' } ) ).toHaveAttribute(
		'aria-current',
		'true'
	);

	const held = deferred< void >();
	const selected =
		deferred< Awaited< ReturnType< typeof selectConversation > > >();
	slow.promise = held.promise;
	vi.mocked( selectConversation ).mockImplementation(
		() => selected.promise
	);
	const input = screen.getByRole( 'textbox' );
	fireEvent.change( input, { target: { value: 'question for eight' } } );
	fireEvent.submit( input.closest( 'form' )! );
	await waitFor( () => expect( sendTurn ).toHaveBeenCalled() );
	await waitFor( () =>
		expect( listConversations ).toHaveBeenCalledTimes( 2 )
	);

	fireEvent.click(
		screen.getByRole( 'button', { name: 'New conversation' } )
	);
	stale = {
		currentId: 8,
		ok: true,
		conversations: [
			{ id: 7, title: 'Seven', updated: '2026-10-12' },
			{ id: 8, title: 'Eight', updated: '2026-10-12' },
		],
	};
	held.resolve();
	await waitFor( () => expect( selectConversation ).toHaveBeenCalled() );

	expect( screen.getByRole( 'button', { name: 'Seven' } ) ).toHaveAttribute(
		'aria-current',
		'true'
	);
	expect(
		screen.getByRole( 'button', { name: 'Eight' } )
	).not.toHaveAttribute( 'aria-current', 'true' );

	selected.resolve( {
		currentId: 9,
		ok: true,
		conversations: [
			{ id: 8, title: 'Eight', updated: '2026-10-12' },
			{ id: 9, title: 'Nine', updated: '2026-10-12' },
		],
	} );
	await waitFor( () => expect( reads.length ).toBeGreaterThanOrEqual( 2 ) );
	reads[ 1 ].resolve( { messages: [], turn: null, contacts: [] } );
	expect(
		await screen.findByRole( 'button', { name: 'Nine' } )
	).toHaveAttribute( 'aria-current', 'true' );
} );
