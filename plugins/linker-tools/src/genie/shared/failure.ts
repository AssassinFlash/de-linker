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
 * not. The failure sentence is the reviewed one. A file the record cannot
 * hold is named in a separate notice, because the retry will not send it.
 *
 * | phase    | kind      | field                         | thread                          | retry                                      |
 * | -------- | --------- | ----------------------------- | ------------------------------- | ------------------------------------------ |
 * | clear    | —         | untouched                     | untouched                       | —                                          |
 * | pending  | —         | cleared for the send          | the question is on its way      | a second retry does not send               |
 * | failed   | truncated | stays empty; files stay as chips | question kept, no answer blocks | one resend of that thread, no second copy  |
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
import { __, _n, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { resourceRefusalReason } from './resourceFailure';
import { isTurnConflict, isUnfinishedStream } from '../api/turn';
import { UPLOAD_TYPES, type Upload } from '../attachments/prepare';
import { attachmentRefusalReason } from './conversation';

/** sessionStorage key. One tab, both surfaces. */
export const FAILURE_KEY = 'linker-genie-turn-failure';

/** Why the turn failed. `truncated` is a stream with no `done`; `upstream` is a 502, a timeout, or a network failure. */
export type FailureKind = 'truncated' | 'upstream';

/** The turn that was sent, or is about to be. */
export interface FailureOwner {
	scope: string;
	attempt: string;
}
export interface FailureDraft {
	/** Independent native owner. Marketing provenance remains separate. */
	owner?: FailureOwner;
	/** Accepted editor content, never presented as a failed model turn. */
	editing?: boolean;
	/** Marketing ownership retained through retry/reload. */
	entryId?: string;
	entryScope?: string;
	/** The words in the field, before file names are joined in. */
	text: string;
	/** The message the proxy received. A retry of an upstream failure may drop attachment lines the record could not keep. */
	question: string;
	uploads: Upload[];
	/**
	 * Names of files the record could not hold. Empty when every file is
	 * in `uploads` or the turn had none.
	 */
	omitted: string[];
}

/** What sessionStorage holds. `kind` is null while the request is in flight. */
export interface StoredFailure extends FailureDraft {
	v: 1;
	kind: FailureKind | null;
}

export interface FailureState {
	phase: 'clear' | 'editing' | 'pending' | 'failed';
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

/**
 * How the shell shows a failure. Chips are the files still held, including
 * after a truncated stream, so they can be removed. A new question sends
 * whatever chips are still there.
 */
export interface PresentedFailure {
	kind: FailureKind;
	messages: FailureMessage[];
	/** Restored into the field. Empty when the question is the thread's tail. */
	field: string;
	chips: Upload[];
	/** Files the record could not hold. The shell says to attach them again. */
	omitted: string[];
}

/**
 * What one failed send asks the shell to show. Refusal and conflict keep
 * their own recovery. A failure names its kind; the shell draws the view
 * after the record is stored.
 */
export type TurnSettlement =
	| { action: 'resource'; reason: string; field: string }
	| { action: 'refusal'; reason: string; field: string }
	| { action: 'conflict'; field: string }
	| { action: 'failed'; kind: FailureKind };

/** The store the record uses. `window.sessionStorage` is one. */
export interface FailureStore {
	getItem: ( key: string ) => string | null;
	setItem: ( key: string, value: string ) => void;
	removeItem: ( key: string ) => void;
	keys?: () => string[];
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
	if (
		isTurnConflict( error ) ||
		resourceRefusalReason( error ) ||
		attachmentRefusalReason( error )
	) {
		return null;
	}
	return isUnfinishedStream( error ) ? 'truncated' : 'upstream';
}

/**
 * The kind a failure shows against the thread. A 502 on a question the
 * server already kept stays truncated: the question is the thread's tail,
 * and putting it back in the field would ask it a second time.
 *
 * @param kind     Which failure.
 * @param before   The thread this attempt posted on top of.
 * @param question The failed question.
 */
function tailKind(
	kind: FailureKind,
	before: readonly FailureMessage[],
	question: string
): FailureKind {
	const tail = before[ before.length - 1 ];
	if ( tail && 'user' === tail.role && tail.content === question ) {
		return 'truncated';
	}
	return kind;
}

/**
 * The kind the shell shows, or null when this machine does not own the
 * failure.
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
	return kind ? tailKind( kind, before, question ) : null;
}

/**
 * The reason word the refusal sentence knows. The proxy names four; any
 * other word is a file the shell could not read.
 */
export type RefusalWord =
	'count' | 'size' | 'type' | 'throttled' | 'unreadable';

/**
 * The refusal's reason for the sentence.
 *
 * @param reason The proxy's reason code.
 */
export function refusalReason( reason: string ): RefusalWord {
	switch ( reason ) {
		case 'count':
		case 'size':
		case 'type':
		case 'throttled':
			return reason;
		default:
			return 'unreadable';
	}
}

/**
 * The field, the chips and the files that have to be picked again.
 *
 * A truncated stream keeps the question in the thread, so the field stays
 * empty, and the files stay as chips. An upstream failure puts the typed
 * words back with those chips.
 *
 * @param kind  Which failure.
 * @param draft The pending question.
 */
export function composerFor(
	kind: FailureKind,
	draft: FailureDraft
): Pick< PresentedFailure, 'field' | 'chips' | 'omitted' > {
	return {
		field: 'truncated' === kind ? '' : draft.text,
		chips: draft.uploads,
		omitted: draft.omitted,
	};
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
	return {
		kind,
		messages: 'truncated' === kind ? sent : before,
		...composerFor( kind, draft ),
	};
}

/**
 * Refusal, a 409, or a failure this machine owns. Both surfaces apply this
 * and do not re-decide it. The view is not built here: `writeFailure` may
 * drop a file before the shell draws the failure.
 *
 * @param error  The rejection from sendTurn.
 * @param before The thread this attempt posted on top of.
 * @param draft  The pending question.
 */
export function settleTurnFailure(
	error: unknown,
	before: readonly FailureMessage[],
	draft: FailureDraft
): TurnSettlement {
	const resourceReason = resourceRefusalReason( error );
	if ( resourceReason ) {
		return {
			action: 'resource',
			reason: resourceReason,
			field: draft.text,
		};
	}
	const kind = failureKind( error );
	if ( ! kind ) {
		// The two recoveries that are not a failure. A refusal names its
		// reason; everything else here is the 409.
		const reason =
			resourceRefusalReason( error ) || attachmentRefusalReason( error );
		if ( reason ) {
			return { action: 'refusal', reason, field: draft.text };
		}
		return { action: 'conflict', field: draft.text };
	}
	return {
		action: 'failed',
		kind: tailKind( kind, before, draft.question ),
	};
}

/**
 * The line `buildQuestion` adds for one file.
 *
 * @param name The file's name.
 */
function attachmentLine( name: string ): string {
	// translators: %s is the name of a file the visitor attached.
	return __( 'Attached: %s', 'linker-tools' ).replace( '%s', name );
}

/**
 * The question without `Attached:` lines for files that will not be sent.
 *
 * @param question The message.
 * @param names    File names to drop.
 */
export function withoutAttachmentClaims(
	question: string,
	names: readonly string[]
): string {
	if ( 0 === names.length ) {
		return question;
	}
	const drop = new Set( names.map( attachmentLine ) );
	return question
		.split( '\n' )
		.filter( ( line ) => ! drop.has( line ) )
		.join( '\n' );
}

/**
 * The question one retry posts. A truncated stream must send the words the
 * server already stored. An upstream failure sends the typed words plus the
 * files still held, and does not claim a file the record dropped.
 *
 * @param kind    Which failure.
 * @param draft   The failed question.
 * @param uploads The files the composer still holds.
 */
export function questionForRetry(
	kind: FailureKind,
	draft: FailureDraft,
	uploads: readonly Upload[]
): string {
	if ( 'truncated' === kind ) {
		return draft.question;
	}
	const sending = new Set( uploads.map( ( file ) => file.name ) );
	let question = withoutAttachmentClaims( draft.question, [
		...draft.omitted.filter( ( name ) => ! sending.has( name ) ),
		...draft.uploads
			.map( ( file ) => file.name )
			.filter( ( name ) => ! sending.has( name ) ),
	] );
	for ( const upload of uploads ) {
		const line = attachmentLine( upload.name );
		if ( question.split( '\n' ).includes( line ) ) {
			continue;
		}
		question = '' === question ? line : `${ question }\n${ line }`;
	}
	return question;
}

/**
 * One retry, or null when this is not a failed turn or an upstream retry
 * would send an empty message. The caller leaves `failed` only after this
 * returns a payload, so a second click does not send.
 *
 * @param state   The machine.
 * @param thread  The thread to send on top of.
 * @param uploads The files the composer still holds.
 */
export function retryPayload< T extends FailureMessage >(
	state: FailureState,
	thread: readonly T[],
	uploads: readonly Upload[]
): { question: string; uploads: Upload[]; messages: T[] } | null {
	if ( 'failed' !== state.phase || ! state.draft || ! state.kind ) {
		return null;
	}
	const question = questionForRetry( state.kind, state.draft, uploads );
	if ( 'truncated' !== state.kind && '' === question ) {
		return null;
	}
	return {
		question,
		uploads: [ ...uploads ],
		messages: retryMessages( thread, question ),
	};
}

/**
 * The composer changed while a failure is on screen: a removed chip leaves
 * the record, and attaching one of the omitted names clears that notice.
 *
 * @param state   The machine.
 * @param uploads The files the composer holds now.
 */
export function failureWithUploads(
	state: FailureState,
	uploads: readonly Upload[]
): FailureState {
	if ( 'failed' !== state.phase || ! state.draft ) {
		return state;
	}
	const names = new Set( uploads.map( ( file ) => file.name ) );
	const omitted = state.draft.omitted.filter(
		( name ) => ! names.has( name )
	);
	if (
		sameUploads( state.draft.uploads, uploads ) &&
		omitted.length === state.draft.omitted.length
	) {
		return state;
	}
	// From the draft before this edit, so a removed chip is a removal and
	// a file the visitor attaches again is an addition.
	const question = state.kind
		? questionForRetry( state.kind, state.draft, uploads )
		: state.draft.question;
	return {
		...state,
		draft: {
			...state.draft,
			uploads: uploads.map( ( file ) => ( { ...file } ) ),
			omitted,
			question,
		},
	};
}

/**
 * Names the customer has to attach again. Empty when every file was kept.
 *
 * @param names File names the record could not hold.
 */
export function omittedFileNotice( names: readonly string[] ): string {
	if ( 0 === names.length ) {
		return '';
	}
	// translators: %s is the file name. The plural does not repeat names.
	const sentence = _n(
		'Attach %s again. It could not be kept for another try.',
		'Attach these files again. They could not be kept for another try.',
		names.length,
		'linker-tools'
	);
	return 1 === names.length ? sprintf( sentence, names[ 0 ] ) : sentence;
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
		...( stored.owner ? { owner: stored.owner } : {} ),
		...( stored.editing ? { editing: true } : {} ),
		...( stored.entryId
			? { entryId: stored.entryId, entryScope: stored.entryScope }
			: {} ),
		text: stored.text,
		question: stored.question,
		uploads: stored.uploads,
		omitted: stored.omitted,
	};
	if ( stored.editing ) {
		return { phase: 'editing', draft, kind: null };
	}

	// The record has no conversation identity or posted-message prefix. An
	// answered question with the same text may be historical or belong to a
	// different conversation. Only the live sender can witness completion.
	const last = messages[ messages.length - 1 ];
	if ( last && 'user' === last.role && last.content === stored.question ) {
		return { phase: 'failed', draft, kind: 'truncated' };
	}
	return {
		phase: 'failed',
		draft: {
			...draft,
			question: withoutAttachmentClaims( draft.question, draft.omitted ),
		},
		kind: 'upstream',
	};
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
 * A record with its files can be larger than the store allows. Files that
 * fit are kept, in the order the customer attached them. Each file that
 * does not fit is named on `omitted` and, for an upstream failure, taken
 * out of the question the retry will send. The returned state is what was
 * stored.
 *
 * @param store The store.
 * @param state The machine.
 */
export function writeFailure(
	store: FailureStore,
	state: FailureState
): FailureState {
	if ( 'clear' === state.phase || ! state.draft ) {
		try {
			store.removeItem( FAILURE_KEY );
		} catch {
			// Nothing newer to keep.
		}
		return CLEAR;
	}
	// A pending write may already have dropped files and left their
	// `Attached:` lines in the question. Marking that record upstream has
	// to take the lines out, even when the smaller record now fits.
	const normalized = withHeldClaims( state );
	if ( ! normalized.draft ) {
		return normalized;
	}
	if ( saveFailure( store, recordOf( normalized ) ) ) {
		return normalized;
	}
	const draft = normalized.draft;
	const kept: Upload[] = [];
	for ( const upload of draft.uploads ) {
		const candidate = draftWith( normalized, [ ...kept, upload ] );
		if ( saveFailure( store, recordOf( candidate ) ) ) {
			kept.push( upload );
		}
	}
	const next = draftWith( normalized, kept );
	saveFailure( store, recordOf( next ) );
	return next;
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
	return {
		getItem: ( key ) => window.sessionStorage.getItem( key ),
		setItem: ( key, value ) => window.sessionStorage.setItem( key, value ),
		removeItem: ( key ) => window.sessionStorage.removeItem( key ),
		keys: () => Object.keys( window.sessionStorage ),
	};
}

/**
 * One stored object, or null when it is not ours.
 *
 * @param value JSON.
 */
export function parseFailure( value: unknown ): StoredFailure | null {
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
	const omitted = Array.isArray( record.omitted )
		? record.omitted.filter(
				( name ): name is string =>
					'string' === typeof name && '' !== name
			)
		: [];
	// An owned attachment-only upstream failure can have no retryable words
	// after withheld attachment claims are removed. It remains an explicit
	// reselection record, never an empty editing draft or a sendable payload.
	if (
		record.question === '' &&
		( record.editing === true ||
			record.kind !== 'upstream' ||
			typeof record.owner?.attempt !== 'string' ||
			! record.owner.attempt ||
			! /^[a-f0-9]{64}$/.test( record.owner.scope ) ||
			uploads.length !== 0 ||
			omitted.length === 0 )
	) {
		return null;
	}

	return {
		v: 1,
		...( record.owner &&
		typeof record.owner.scope === 'string' &&
		typeof record.owner.attempt === 'string' &&
		record.owner.attempt
			? { owner: record.owner }
			: {} ),
		...( typeof record.entryId === 'string'
			? { entryId: record.entryId, entryScope: record.entryScope }
			: {} ),
		...( record.editing === true ? { editing: true } : {} ),
		text: record.text,
		question: record.question,
		uploads: uploads as Upload[],
		omitted,
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
	if ( ! ( UPLOAD_TYPES as readonly unknown[] ).includes( upload.type ) ) {
		return null;
	}
	return {
		name: upload.name,
		type: upload.type as Upload[ 'type' ],
		data: upload.data,
	};
}

/**
 * The record for `state`, including only `uploads`.
 *
 * @param state The machine. Its draft is required.
 */
export function recordOf( state: FailureState ): StoredFailure {
	const draft = state.draft as FailureDraft;
	return {
		v: 1,
		...( draft.owner ? { owner: draft.owner } : {} ),
		...( draft.entryId
			? { entryId: draft.entryId, entryScope: draft.entryScope }
			: {} ),
		...( draft.editing ? { editing: true } : {} ),
		text: draft.text,
		question: draft.question,
		uploads: draft.uploads,
		omitted: draft.omitted,
		kind: state.kind,
	};
}

/**
 * An upstream failure does not claim a file the record could not hold.
 * A truncated stream, and a request still in flight, keep the question
 * the server may already have stored.
 *
 * @param state The machine.
 */
export function withHeldClaims( state: FailureState ): FailureState {
	if ( ! state.draft || 'upstream' !== state.kind ) {
		return state;
	}
	const question = withoutAttachmentClaims(
		state.draft.question,
		state.draft.omitted
	);
	if ( question === state.draft.question ) {
		return state;
	}
	return { ...state, draft: { ...state.draft, question } };
}

/**
 * `state` with `uploads` kept and the question's attachment claims matched
 * to that list. A truncated stream keeps the question the server stored.
 *
 * @param state   The machine.
 * @param uploads The files that fit.
 */
export function draftWith(
	state: FailureState,
	uploads: Upload[]
): FailureState {
	const draft = state.draft as FailureDraft;
	const kept = new Set( uploads.map( ( file ) => file.name ) );
	const omitted = [
		...new Set( [
			...draft.omitted.filter( ( name ) => ! kept.has( name ) ),
			...draft.uploads
				.filter( ( file ) => ! uploads.includes( file ) )
				.map( ( file ) => file.name ),
		] ),
	];
	const question =
		'upstream' === state.kind
			? withoutAttachmentClaims( draft.question, omitted )
			: draft.question;
	return {
		...state,
		draft: { ...draft, uploads, omitted, question },
	};
}

/**
 * Writes one record. False when the store refuses it.
 *
 * @param store  The store.
 * @param record The record.
 */
function saveFailure( store: FailureStore, record: StoredFailure ): boolean {
	try {
		store.setItem( FAILURE_KEY, JSON.stringify( record ) );
		return true;
	} catch {
		return false;
	}
}

/**
 * The same files, in the same order.
 *
 * @param left  One list.
 * @param right The other.
 */
function sameUploads(
	left: readonly Upload[],
	right: readonly Upload[]
): boolean {
	return (
		left.length === right.length &&
		left.every(
			( file, index ) =>
				file.name === right[ index ].name &&
				file.type === right[ index ].type &&
				file.data === right[ index ].data
		)
	);
}
