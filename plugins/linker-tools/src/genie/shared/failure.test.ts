// @vitest-environment jsdom

/**
 * The shell's failure machine (ticket #411): a stream with no `done` is not
 * an answer, a 502 or a timeout comes back to the field, and a reload still
 * has the error and one retry.
 */

/**
 * External dependencies
 */
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import { TurnError } from '../api/turn';
import type { Upload } from '../attachments/prepare';
import {
	FAILURE_KEY,
	failureKind,
	failureReducer,
	shownFailureKind,
	failureText,
	initialFailureState,
	presentFailure,
	readFailure,
	reconcile,
	retryMessages,
	writeFailure,
	type FailureDraft,
	type FailureState,
	type FailureStore,
} from './failure';

const PDF: Upload = {
	name: 'nameplate.pdf',
	type: 'application/pdf',
	data: 'JVBERi0=',
};

const DRAFT: FailureDraft = {
	text: 'Do you stock the SAJ H2-10K-T2?',
	question: 'Do you stock the SAJ H2-10K-T2?',
	uploads: [ PDF ],
	base: 0,
};

function memory(
	quota = Infinity
): FailureStore & { raw: Map< string, string > } {
	const raw = new Map< string, string >();
	return {
		raw,
		getItem( key ) {
			return raw.get( key ) ?? null;
		},
		setItem( key, value ) {
			if ( value.length > quota ) {
				throw new Error( 'quota' );
			}
			raw.set( key, value );
		},
		removeItem( key ) {
			raw.delete( key );
		},
	};
}

function pending(): FailureState {
	return failureReducer( initialFailureState(), {
		type: 'send',
		draft: DRAFT,
	} );
}

test( 'the failure sentence is the reviewed one', () => {
	expect( failureText() ).toBe( 'Genie did not answer. Please try again.' );
} );

test( 'a 502, a timeout and a network failure are upstream; a stream without done is truncated', () => {
	expect( failureKind( new TurnError( 502, 'linker_genie_upstream' ) ) ).toBe(
		'upstream'
	);
	expect( failureKind( new DOMException( 'timed out', 'AbortError' ) ) ).toBe(
		'upstream'
	);
	expect( failureKind( new TypeError( 'Failed to fetch' ) ) ).toBe(
		'upstream'
	);
	expect( failureKind( new Error( 'stream without done' ) ) ).toBe(
		'truncated'
	);
	expect(
		failureKind( new TurnError( 409, 'linker_genie_turn_conflict' ) )
	).toBeNull();
	expect(
		failureKind( new TurnError( 415, 'linker_genie_attachment_type' ) )
	).toBeNull();
} );

test( 'a 502 on a question the server already kept stays truncated', () => {
	const stored = [ user( 'backup for 10 kW' ) ];
	expect(
		shownFailureKind(
			new TurnError( 502, 'linker_genie_upstream' ),
			stored,
			'backup for 10 kW'
		)
	).toBe( 'truncated' );
	expect(
		shownFailureKind(
			new TurnError( 502, 'linker_genie_upstream' ),
			[],
			'backup for 10 kW'
		)
	).toBe( 'upstream' );
	expect(
		shownFailureKind(
			new Error( 'stream without done' ),
			[],
			'backup for 10 kW'
		)
	).toBe( 'truncated' );
	expect(
		shownFailureKind(
			new TurnError( 409, 'linker_genie_turn_conflict' ),
			[],
			'backup for 10 kW'
		)
	).toBeNull();
} );

test( 'an upstream failure restores the question and keeps the files off the thread', () => {
	const failed = failureReducer( pending(), { type: 'upstream' } );
	expect( failed.phase ).toBe( 'failed' );
	expect( failed.kind ).toBe( 'upstream' );
	const view = presentFailure(
		'upstream',
		[],
		[ user( DRAFT.question ) ],
		DRAFT
	);
	expect( view.messages ).toEqual( [] );
	expect( view.field ).toBe( DRAFT.text );
	expect( view.chips ).toEqual( [ PDF ] );
} );

test( 'a stream without done keeps the question and renders no answer', () => {
	const failed = failureReducer( pending(), { type: 'truncated' } );
	const sent = [ user( DRAFT.question ) ];
	const view = presentFailure( 'truncated', [], sent, DRAFT );
	expect( failed.kind ).toBe( 'truncated' );
	expect( view.messages ).toEqual( sent );
	expect( view.field ).toBe( '' );
	expect( view.chips ).toEqual( [] );
	expect(
		view.messages.some( ( message ) => 'assistant' === message.role )
	).toBe( false );
} );

test( 'a success, a 409 and a refused file clear the failure', () => {
	const sent = pending();
	expect( failureReducer( sent, { type: 'answered' } ).phase ).toBe(
		'clear'
	);
	expect( failureReducer( sent, { type: 'abandon' } ).phase ).toBe( 'clear' );
	expect(
		failureReducer( initialFailureState(), { type: 'upstream' } ).phase
	).toBe( 'clear' );
} );

test( 'retry sends once: a second retry while the first is in flight does not start another', () => {
	const failed = failureReducer( pending(), { type: 'upstream' } );
	const again = failureReducer( failed, { type: 'retry' } );
	expect( again.phase ).toBe( 'pending' );
	expect( failureReducer( again, { type: 'retry' } ) ).toEqual( again );
	const thread = [ user( 'Earlier' ), assistant( 'Answered.' ) ];
	expect( retryMessages( thread, DRAFT.question ) ).toEqual( [
		...thread,
		user( DRAFT.question ),
	] );
	const stored = [ ...thread, user( DRAFT.question ) ];
	expect( retryMessages( stored, DRAFT.question ) ).toEqual( stored );
} );

test( 'a reload of an unfinished stream shows the error and not an answer', () => {
	const store = memory();
	writeFailure( store, failureReducer( pending(), { type: 'truncated' } ) );
	const restored = reconcile( readFailure( store ), [
		user( DRAFT.question ),
	] );
	expect( restored.phase ).toBe( 'failed' );
	expect( restored.kind ).toBe( 'truncated' );
	expect( restored.draft?.uploads ).toEqual( [ PDF ] );
} );

test( 'a reload after a 502 puts the question back; an answered question clears it', () => {
	const store = memory();
	writeFailure( store, failureReducer( pending(), { type: 'upstream' } ) );
	const lost = reconcile( readFailure( store ), [] );
	expect( lost.kind ).toBe( 'upstream' );
	expect( lost.draft?.text ).toBe( DRAFT.text );

	const answered = reconcile( readFailure( store ), [
		user( DRAFT.question ),
		assistant( 'The H2-10K-T3 is the current model.' ),
	] );
	expect( answered.phase ).toBe( 'clear' );
} );

test( 'a reload during the request follows the thread the server kept', () => {
	const store = memory();
	writeFailure( store, pending() );
	expect( readFailure( store )?.kind ).toBeNull();
	expect(
		reconcile( readFailure( store ), [ user( DRAFT.question ) ] ).kind
	).toBe( 'truncated' );
	expect( reconcile( readFailure( store ), [] ).kind ).toBe( 'upstream' );
} );

test( 'a record the store cannot hold whole still keeps the question', () => {
	const store = memory( 150 );
	writeFailure( store, failureReducer( pending(), { type: 'upstream' } ) );
	const stored = readFailure( store );
	expect( stored?.question ).toBe( DRAFT.question );
	expect( stored?.uploads ).toEqual( [] );
	expect( stored?.kind ).toBe( 'upstream' );
} );

test( 'a record this module did not write is ignored', () => {
	const store = memory();
	store.setItem( FAILURE_KEY, '{' );
	expect( readFailure( store ) ).toBeNull();
	store.setItem( FAILURE_KEY, JSON.stringify( { v: 2, question: 'x' } ) );
	expect( readFailure( store ) ).toBeNull();
	writeFailure( store, failureReducer( pending(), { type: 'answered' } ) );
	expect( store.getItem( FAILURE_KEY ) ).toBeNull();
} );

/**
 * @param content The message.
 */
function user( content: string ) {
	return { role: 'user', content };
}

/**
 * @param content The message.
 */
function assistant( content: string ) {
	return { role: 'assistant', content };
}
