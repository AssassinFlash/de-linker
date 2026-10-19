/**
 * A failed Genie turn, kept across a reload (ticket #411).
 *
 * The proxy stores a user message when it returns a stream, and stores
 * nothing when it answers 502. The shell used to keep the error only in
 * React state, so a reload dropped it: an unfinished stream left the
 * question with no error, and a 502 left nothing, including the field.
 *
 * One machine for the dock and the home hero. The record lives in
 * sessionStorage, which a reload of this tab keeps and a later visit does
 * not. The words are the reviewed failure sentence; this module does not
 * add copy.
 *
 * | phase    | kind      | field                         | thread                          | retry                                      |
 * | -------- | --------- | ----------------------------- | ------------------------------- | ------------------------------------------ |
 * | clear    | —         | untouched                     | untouched                       | —                                          |
 * | pending  | —         | cleared for the send          | the question is on its way      | a second retry does not send               |
 * | failed   | truncated | stays empty                   | question kept, no answer blocks | one resend of that thread, no second copy  |
 * | failed   | upstream  | question and files restored   | question removed                | one send of the question                   |
 *
 * Reload reads the record against the stored thread: a tail that is the
 * question is truncated (the partial stream is not an answer); a question
 * the server never kept is upstream; a question already followed by an
 * assistant is clear.
 */

/**
 * WordPress dependencies
 */
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { isTurnConflict, isUnfinishedStream } from '../api/turn';
import type { Upload } from '../attachments/prepare';
import { attachmentRefusalReason } from './conversation';

/** sessionStorage key. One tab, both surfaces. */
export const FAILURE_KEY = 'linker-genie-turn-failure';

/** Why the turn failed. `truncated` is a stream with no `done`; `upstream` is a 502, a timeout, or a network failure. */
export type FailureKind = 'truncated' | 'upstream';

/** The turn that was sent, or is about to be. */
export interface FailureDraft {
	/** The words in the field, before file names are joined in. */
	text: string;
	/** The message the proxy received. */
	question: string;
	uploads: Upload[];
	/** Thread length before this question. */
	base: number;
}

/** What sessionStorage holds. `kind` is null while the request is in flight. */
export interface StoredFailure extends FailureDraft {
	v: 1;
	kind: FailureKind | null;
}

export interface FailureState {
	phase: 'clear' | 'pending' | 'failed';
	draft: FailureDraft | null;
	kind: FailureKind | null;
}

export type FailureEvent =
	| { type: 'send'; draft: FailureDraft }
	| { type: 'answered' }
	| { type: 'abandon' }
	| { type: 'truncated' }
	| { type: 'upstream' }
	| { type: 'retry' };

/** A message the retry compares. The shell's own messages are a subtype. */
export interface FailureMessage {
	role: string;
	content: string;
}

/** How the shell shows a failure. Chips are empty for a truncated stream: the bytes stay on the record for the retry, not on the next typed question. */
export interface PresentedFailure {
	kind: FailureKind;
	messages: FailureMessage[];
	/** Restored into the field. Empty when the question is the thread's tail. */
	field: string;
	chips: Upload[];
}

/** The store the record uses. `window.sessionStorage` is one. */
export interface FailureStore {
	getItem: ( key: string ) => string | null;
	setItem: ( key: string, value: string ) => void;
	removeItem: ( key: string ) => void;
}

const CLEAR: FailureState = { phase: 'clear', draft: null, kind: null };

/**
 * The reviewed failure sentence, EN and DE already in the catalog.
 */
export function failureText(): string {
	return __( 'Genie did not answer. Please try again.', 'linker-tools' );
}

/**
 * A fresh machine.
 */
export function initialFailureState(): FailureState {
	return CLEAR;
}

/**
 * Folds one event into the failure state.
 *
 * `truncated` and `upstream` apply only while a send is in flight, so a
 * late error cannot mark a turn that already succeeded. `retry` leaves
 * `pending` alone: the send that is already going is the one send.
 *
 * @param state The state before the event.
 * @param event What happened.
 */
export function failureReducer(
	state: FailureState,
	event: FailureEvent
): FailureState {
	switch ( event.type ) {
		case 'send':
			return { phase: 'pending', draft: event.draft, kind: null };
		case 'answered':
		case 'abandon':
			return CLEAR;
		case 'truncated':
		case 'upstream':
			if ( 'pending' !== state.phase || ! state.draft ) {
				return state;
			}
			return { phase: 'failed', draft: state.draft, kind: event.type };
		case 'retry':
			if ( 'failed' !== state.phase || ! state.draft ) {
				return state;
			}
			return { phase: 'pending', draft: state.draft, kind: null };
	}
}

/**
 * The kind of failure `sendTurn` raised, or null when this machine does
 * not own it (a 409, or a file the proxy refused).
 *
 * @param error The rejection from sendTurn.
 */
export function failureKind( error: unknown ): FailureKind | null {
	if ( isTurnConflict( error ) || attachmentRefusalReason( error ) ) {
		return null;
	}
	return isUnfinishedStream( error ) ? 'truncated' : 'upstream';
}

/**
 * The kind the shell shows. A 502 on a question the server already kept
 * stays truncated: the question is the thread's tail, and putting it back
 * in the field would ask it a second time.
 *
 * @param error    The rejection from sendTurn.
 * @param before   The thread this attempt posted on top of.
 * @param question The failed question.
 */
export function shownFailureKind(
	error: unknown,
	before: readonly FailureMessage[],
	question: string
): FailureKind | null {
	const kind = failureKind( error );
	if ( ! kind ) {
		return null;
	}
	const tail = before[ before.length - 1 ];
	if ( tail && 'user' === tail.role && tail.content === question ) {
		return 'truncated';
	}
	return kind;
}

/**
 * What the shell shows for a failed send. A stream without `done` is not
 * drawn: the question stays the tail and the blocks stay the previous
 * turn's. A 502 or a timeout puts the question and its files back.
 *
 * @param kind   Which failure.
 * @param before The thread before this question was appended.
 * @param sent   The thread that was posted, including the question.
 * @param draft  The pending question.
 */
export function presentFailure(
	kind: FailureKind,
	before: FailureMessage[],
	sent: FailureMessage[],
	draft: FailureDraft
): PresentedFailure {
	if ( 'truncated' === kind ) {
		return { kind, messages: sent, field: '', chips: [] };
	}
	return {
		kind,
		messages: before,
		field: draft.text,
		chips: draft.uploads,
	};
}

/**
 * The messages one retry posts. The question is appended only when the
 * thread does not already end with it, so a stored turn is not asked twice.
 *
 * @param thread   The thread to send on top of.
 * @param question The failed question.
 */
export function retryMessages< T extends FailureMessage >(
	thread: readonly T[],
	question: string
): T[] {
	const last = thread[ thread.length - 1 ];
	if ( last && 'user' === last.role && last.content === question ) {
		return [ ...thread ];
	}
	return [ ...thread, { role: 'user', content: question } as T ];
}

/**
 * The record as a reload should show it, given the thread the proxy kept.
 *
 * @param stored   The record, or null.
 * @param messages The stored thread. An unfinished stream contributes no assistant message.
 */
export function reconcile(
	stored: StoredFailure | null,
	messages: readonly FailureMessage[]
): FailureState {
	if ( ! stored ) {
		return CLEAR;
	}
	const draft: FailureDraft = {
		text: stored.text,
		question: stored.question,
		uploads: stored.uploads,
		base: stored.base,
	};
	let lastAsk = -1;
	for ( let index = 0; index < messages.length; index++ ) {
		const message = messages[ index ];
		if ( 'user' === message.role && message.content === stored.question ) {
			lastAsk = index;
		}
	}
	if (
		lastAsk >= 0 &&
		messages
			.slice( lastAsk + 1 )
			.some( ( message ) => 'assistant' === message.role )
	) {
		return CLEAR;
	}
	const last = messages[ messages.length - 1 ];
	if ( last && 'user' === last.role && last.content === stored.question ) {
		return { phase: 'failed', draft, kind: 'truncated' };
	}
	return { phase: 'failed', draft, kind: 'upstream' };
}

/**
 * Reads the record. A shape this module did not write is no record.
 *
 * @param store The store.
 */
export function readFailure( store: FailureStore ): StoredFailure | null {
	let raw: string | null;
	try {
		raw = store.getItem( FAILURE_KEY );
	} catch {
		return null;
	}
	if ( ! raw ) {
		return null;
	}
	try {
		return parseFailure( JSON.parse( raw ) );
	} catch {
		return null;
	}
}

/**
 * Writes the record, or removes it when the machine is clear.
 *
 * A record with its files can be larger than the store allows. The question
 * and the marker are written again without the files; the live view still
 * holds the files for a retry that has not reloaded.
 *
 * @param store The store.
 * @param state The machine.
 */
export function writeFailure( store: FailureStore, state: FailureState ): void {
	if ( 'clear' === state.phase || ! state.draft ) {
		try {
			store.removeItem( FAILURE_KEY );
		} catch {
			// Nothing newer to keep.
		}
		return;
	}
	const record: StoredFailure = {
		v: 1,
		text: state.draft.text,
		question: state.draft.question,
		uploads: state.draft.uploads,
		base: state.draft.base,
		kind: state.kind,
	};
	try {
		store.setItem( FAILURE_KEY, JSON.stringify( record ) );
	} catch {
		try {
			store.setItem(
				FAILURE_KEY,
				JSON.stringify( { ...record, uploads: [] } )
			);
		} catch {
			// The live view still holds the question.
		}
	}
}

/**
 * sessionStorage, with a read that fails closed. `setItem` still throws
 * when the quota is full, which is what `writeFailure` catches.
 *
 * @param storage The browser store, or a double.
 */
export function browserStore( storage: FailureStore ): FailureStore {
	return {
		getItem( key: string ): string | null {
			try {
				return storage.getItem( key );
			} catch {
				return null;
			}
		},
		setItem( key: string, value: string ): void {
			storage.setItem( key, value );
		},
		removeItem( key: string ): void {
			try {
				storage.removeItem( key );
			} catch {
				// A store that cannot drop the key keeps the last setItem.
			}
		},
	};
}

/**
 * This tab's sessionStorage.
 */
export function pageFailureStore(): FailureStore {
	return browserStore( window.sessionStorage );
}

/**
 * One stored object, or null when it is not ours.
 *
 * @param value JSON.
 */
function parseFailure( value: unknown ): StoredFailure | null {
	if ( ! value || 'object' !== typeof value ) {
		return null;
	}
	const record = value as Partial< StoredFailure >;
	if ( 1 !== record.v ) {
		return null;
	}
	if (
		'string' !== typeof record.text ||
		'string' !== typeof record.question
	) {
		return null;
	}
	if ( '' === record.question ) {
		return null;
	}
	if (
		null !== record.kind &&
		'truncated' !== record.kind &&
		'upstream' !== record.kind
	) {
		return null;
	}
	const uploads = Array.isArray( record.uploads )
		? record.uploads.map( uploadOf ).filter( ( upload ) => null !== upload )
		: [];
	return {
		v: 1,
		text: record.text,
		question: record.question,
		uploads: uploads as Upload[],
		base: 'number' === typeof record.base ? record.base : 0,
		kind: record.kind ?? null,
	};
}

/**
 * One upload, or null.
 *
 * @param value A JSON object.
 */
function uploadOf( value: unknown ): Upload | null {
	if ( ! value || 'object' !== typeof value ) {
		return null;
	}
	const upload = value as Partial< Upload >;
	if ( 'string' !== typeof upload.name || 'string' !== typeof upload.data ) {
		return null;
	}
	if (
		'image/jpeg' !== upload.type &&
		'application/pdf' !== upload.type &&
		'text/csv' !== upload.type &&
		'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' !==
			upload.type
	) {
		return null;
	}
	return { name: upload.name, type: upload.type, data: upload.data };
}
