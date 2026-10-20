// @vitest-environment jsdom

/**
 * The hero and the dock share one conversation (ticket #232): the hero reads
 * the thread the dock stored and sends the whole thread back, so neither
 * surface replaces the other's history.
 */

/**
 * External dependencies
 */
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import {
	assistantMessage,
	type Turn,
	type TurnMessage,
} from '../genie/api/turn';
import type { Upload } from '../genie/attachments/prepare';
import { HeroSession, type HeroSessionConfig } from './session';

const CONFIG: HeroSessionConfig = {
	turnUrl: '/wp-json/linker-ai/v1/genie/turn',
	threadUrl: '/wp-json/linker-ai/v1/genie/conversation',
	nonce: 'n',
	locale: 'en',
	page: { type: 'home', url: '/', title: 'Home page' },
};

const DOCK_THREAD: TurnMessage[] = [
	{ role: 'user', content: 'Which inverters fit a three-phase home?' },
	{ role: 'assistant', content: 'These three fit.' },
];

function answer( text: string ): Turn {
	return {
		meta: {
			turn_id: 7,
			grounded: true,
			fallback: false,
			attempts: 1,
			failures: [],
			language: 'en',
		},
		blocks: [ { type: 'text', text, refs: [] } ],
	};
}

/**
 * A server that keeps one thread, as the proxy's conversation post does.
 *
 * @param stored The thread the server already holds.
 */
function server( stored: TurnMessage[] = [] ) {
	const state = { messages: [ ...stored ], turn: null as Turn | null };
	const read = vi.fn( async () => ( {
		messages: [ ...state.messages ],
		turn: state.turn,
	} ) );
	const send = vi.fn(
		async ( request: { messages: TurnMessage[]; uploads?: Upload[] } ) => {
			const reply = answer( `Answer ${ state.messages.length + 1 }` );
			state.messages = [ ...request.messages, assistantMessage( reply ) ];
			state.turn = reply;
			return reply;
		}
	);
	return { state, read, send };
}

test( 'loading reads the thread the dock stored', async () => {
	const { read, send } = server( DOCK_THREAD );
	const session = new HeroSession( CONFIG, read, send );

	const stored = await session.load();

	expect( stored.messages ).toEqual( DOCK_THREAD );
	expect( session.messages ).toEqual( DOCK_THREAD );
	expect( read ).toHaveBeenCalledWith( CONFIG.threadUrl, CONFIG.nonce );
	expect( send ).not.toHaveBeenCalled();
} );

test( 'the hero sends the whole thread, so the dock history is kept', async () => {
	const { read, send } = server( DOCK_THREAD );
	const session = new HeroSession( CONFIG, read, send );

	await session.ask( 'And which batteries pair with them?' );

	expect( send ).toHaveBeenCalledTimes( 1 );
	const sent = send.mock.calls[ 0 ][ 0 ].messages;
	expect( sent.map( ( message ) => message.content ) ).toEqual( [
		...DOCK_THREAD.map( ( message ) => message.content ),
		'And which batteries pair with them?',
	] );
} );

test( 'an ask loads the stored thread first, even without an explicit load', async () => {
	const { read, send } = server( DOCK_THREAD );
	const session = new HeroSession( CONFIG, read, send );

	await session.ask( 'Show me the first one.' );

	expect( read ).toHaveBeenCalledTimes( 1 );
	expect( send.mock.calls[ 0 ][ 0 ].messages ).toHaveLength( 3 );
} );

test( 'the conversation the hero answered is what the dock reads next', async () => {
	const { state, read, send } = server( DOCK_THREAD );
	const hero = new HeroSession( CONFIG, read, send );

	const result = await hero.ask( 'Which battery pairs with it?' );

	const dock = new HeroSession( CONFIG, read, send );
	const stored = await dock.load();

	expect( result.messages ).toHaveLength( 4 );
	expect( stored.messages ).toEqual( result.messages );
	expect( state.messages ).toEqual( result.messages );
	expect( stored.turn?.meta?.turn_id ).toBe( 7 );
} );

test( 'the files of the turn ride apart from the messages', async () => {
	const { read, send } = server();
	const session = new HeroSession( CONFIG, read, send );
	const upload = {
		name: 'nameplate.jpg',
		type: 'image/jpeg' as const,
		data: 'AA==',
	};

	await session.ask( 'Attached: nameplate.jpg', [ upload ] );

	expect( send.mock.calls[ 0 ][ 0 ].uploads ).toEqual( [ upload ] );
	expect(
		send.mock.calls[ 0 ][ 0 ].messages.map( ( message ) => message.content )
	).toEqual( [ 'Attached: nameplate.jpg' ] );
} );

test( 'a refused turn leaves the stored thread as it was', async () => {
	const { read } = server( DOCK_THREAD );
	const send = vi.fn( async () => {
		throw new Error( 'turn 429' );
	} );
	const session = new HeroSession( CONFIG, read, send );

	await expect( session.ask( 'Hello' ) ).rejects.toThrow( 'turn 429' );
	expect( session.messages ).toEqual( DOCK_THREAD );
} );

test( 'load is read once per session', async () => {
	const { read, send } = server( DOCK_THREAD );
	const session = new HeroSession( CONFIG, read, send );

	await session.load();
	await session.load();

	expect( read ).toHaveBeenCalledTimes( 1 );
} );

test( 'every send re-reads the thread, so a dock turn is not overwritten', async () => {
	const { state, read, send } = server( DOCK_THREAD );
	const session = new HeroSession( CONFIG, read, send );

	await session.load();
	// The dock answered while the hero was folded (or both surfaces are open).
	state.messages = [
		...DOCK_THREAD,
		{ role: 'user', content: 'Dock follow-up' },
		{ role: 'assistant', content: 'Dock answer' },
	] as TurnMessage[];

	await session.ask( 'Hero follow-up' );

	const sent = send.mock.calls[ 0 ][ 0 ].messages.map(
		( message ) => message.content
	);
	expect( sent ).toEqual( [
		'Which inverters fit a three-phase home?',
		'These three fit.',
		'Dock follow-up',
		'Dock answer',
		'Hero follow-up',
	] );
	expect( state.messages.map( ( message ) => message.content ) ).toEqual( [
		...sent,
		'Answer 5',
	] );
	expect( read ).toHaveBeenCalledTimes( 2 );
} );
