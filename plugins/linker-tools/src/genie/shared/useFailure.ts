/**
 * The failed-turn record for both Genie surfaces (ticket #411).
 *
 * The dock and the home hero keep the same record, the same chips, and the
 * same decision to send a retry. Each surface still sends on its own route.
 */

/**
 * WordPress dependencies
 */
import { useCallback, useEffect, useRef, useState } from '@wordpress/element';

/**
 * Internal dependencies
 */
import type { Upload } from '../attachments/prepare';
import { buildQuestion } from './conversation';
import {
	failureReducer,
	failureWithUploads,
	reconcile,
	pageFailureStore,
	recordOf,
	retryPayload,
	type FailureDraft,
	type FailureEvent,
	type FailureKind,
	type FailureMessage,
	type FailureState,
} from './failure';
import { preserveEditing, type EditingSnapshot } from './editingDraft';
import type { DraftContext } from './draftContext';
import {
	FailureJournal,
	type FailureCandidate,
	type FailureCursor,
} from './ownedFailure';

/** The composer files this record reads and puts back. */
export interface FailureFiles {
	uploads: readonly Upload[];
	restore: ( uploads: Upload[] ) => void;
	clear: () => void;
}

/** A retry that is allowed to send. The machine is already `pending`. */
export interface OpenRetry {
	draft: FailureDraft;
	kind: FailureKind;
}

/**
 * The shared failure record.
 *
 * @param files   The composer's files.
 * @param context The mounted surface identity and epoch.
 */
export function useFailure( files: FailureFiles, context: DraftContext ) {
	const failureState = useRef< FailureState >( {
		phase: 'clear',
		draft: null,
		kind: null,
	} );
	const [ omitted, setOmitted ] = useState< string[] >( [] );
	// True while this component is putting chips back, so that paint is not
	// read as the customer removing them.
	const placingChips = useRef( false );
	const filesRef = useRef( files );
	filesRef.current = files;

	const cursor = useRef< FailureCursor | null >( null );
	const [ unsaved, setUnsaved ] = useState( false );
	const [ deferredFailure, setDeferredFailure ] =
		useState< FailureCandidate | null >( null );
	const persist = useCallback(
		( next: FailureState, start = false ) => {
			const identity = context.identity;
			if ( ! identity || context.phase !== 'ready' ) {
				return next;
			}
			const journal = new FailureJournal( pageFailureStore(), identity );
			if ( next.phase === 'clear' ) {
				if ( cursor.current ) {
					if ( ! journal.consume( cursor.current ) ) {
						setUnsaved( true );
						return failureState.current;
					}
				}
				cursor.current = null;
				setUnsaved( false );
				return next;
			}
			const result =
				start || ! cursor.current
					? journal.begin( next, context.editor ?? undefined )
					: journal.save( next, cursor.current );
			if ( result.conflict ) {
				setUnsaved( true );
				return failureState.current;
			}
			cursor.current = result.cursor;
			if ( start ) {
				context.releaseEditor();
			}
			setUnsaved( ! result.durable );
			return result.state;
		},
		[ context ]
	);
	const commitFailure = useCallback(
		( event: FailureEvent ) => {
			const previous = failureState.current;
			const reduced = failureReducer( previous, event );
			const stored = persist( reduced, event.type === 'send' );
			failureState.current = stored;
			setOmitted(
				'failed' === stored.phase ? ( stored.draft?.omitted ?? [] ) : []
			);
			return stored;
		},
		[ persist ]
	);
	/** A verified selector hands over its exact CAS cursor before any restoration. */
	const adoptFailure = useCallback(
		( candidate: FailureCandidate | null, next: FailureState ) => {
			cursor.current = candidate?.cursor ?? null;
			const stored = candidate ? persist( next ) : next;
			failureState.current = stored;
			if ( stored.phase === 'editing' && stored.draft?.owner ) {
				context.adoptEditor( stored.draft.owner );
			}
			return stored;
		},
		[ persist, context ]
	);
	/** Identity/context invalidation quarantines UI without consuming old durable bytes. */
	const detachFailure = useCallback( () => {
		cursor.current = null;
		failureState.current = { phase: 'clear', draft: null, kind: null };
		setOmitted( [] );
		setUnsaved( false );
		setDeferredFailure( null );
	}, [] );

	const preserveEditor = useCallback(
		( snapshot: EditingSnapshot ) => {
			const result = preserveEditing( context, snapshot );
			if ( result ) {
				setUnsaved( ! result.durable );
				// Only our own synchronous checkpoint can advance the pending cursor
				// over a different editor's write. Late callbacks never rebase it.
				if ( ! result.conflict && cursor.current && context.identity ) {
					const current = new FailureJournal(
						pageFailureStore(),
						context.identity
					).rebase( cursor.current );
					if ( current ) {
						cursor.current = current.cursor;
					}
				}
			}
			return result;
		},
		[ context ]
	);

	/** Keep a settled earlier turn reachable without taking a newly accepted editor. */
	const parkFailure = useCallback( () => {
		if ( ! cursor.current || ! failureState.current.draft ) {
			return;
		}
		setDeferredFailure( {
			record: recordOf( failureState.current ),
			cursor: cursor.current,
		} );
		cursor.current = null;
		failureState.current = { phase: 'clear', draft: null, kind: null };
	}, [] );

	/** Refusal/conflict returns the same immutable attempt to editing, without consuming it. */
	const returnToEditing = useCallback(
		( snapshot: EditingSnapshot ) => {
			const previous = failureState.current;
			if ( ! previous.draft ) {
				return false;
			}
			const occupied =
				!! context.editor &&
				context.editor.attempt !== previous.draft.owner?.attempt;
			const question =
				buildQuestion( snapshot.text, snapshot.uploads ) ||
				snapshot.missing.join( '\n' );
			if ( ! question ) {
				commitFailure( { type: 'abandon' } );
				return ! occupied;
			}
			const next: FailureState = {
				phase: 'editing',
				kind: null,
				draft: {
					...previous.draft,
					editing: true,
					text: snapshot.text,
					question,
					uploads: snapshot.uploads,
					omitted: snapshot.missing,
				},
			};
			const stored = persist( next );
			failureState.current = stored;
			if ( stored.phase !== 'editing' || ! stored.draft?.owner ) {
				return false;
			}
			if ( occupied ) {
				parkFailure();
				return false;
			}
			context.adoptEditor( stored.draft.owner );
			setOmitted( stored.draft.omitted );
			return true;
		},
		[ context, persist, commitFailure, parkFailure ]
	);

	/** Caller verifies scope and editor epoch before this synchronous durable exchange. */
	const exchangeFailure = useCallback(
		(
			candidate: FailureCandidate,
			displaced: FailureState | null,
			messages: readonly FailureMessage[] = []
		) => {
			if (
				context.phase !== 'ready' ||
				! context.identity ||
				context.identity.scope !== candidate.cursor.owner.scope
			) {
				return null;
			}
			const journal = new FailureJournal(
				pageFailureStore(),
				context.identity
			);
			let target = journal.rebase( candidate.cursor );
			if ( ! target ) {
				return null;
			}
			let parked: FailureCandidate | null = null;
			if (
				displaced?.draft &&
				( displaced.draft.text ||
					displaced.draft.uploads.length ||
					displaced.draft.omitted.length )
			) {
				const saved = journal.begin(
					displaced,
					context.editor ?? undefined
				);
				setUnsaved( ! saved.durable );
				if (
					saved.conflict ||
					( ! saved.durable && ! saved.cursor.memory ) ||
					! saved.state.draft
				) {
					return null;
				}
				parked = {
					record: {
						...saved.state.draft,
						v: 1,
						kind: saved.state.kind,
					},
					cursor: saved.cursor,
				};
				target = journal.rebase( candidate.cursor );
				if ( ! target ) {
					return null;
				}
			}
			const state = reconcile( target.record, messages );
			if ( state.phase === 'clear' ) {
				if ( ! journal.consume( target.cursor ) ) {
					setUnsaved( true );
				}
				setDeferredFailure(
					parked ? journal.rebase( parked.cursor ) : null
				);
				return state;
			}
			const saved = journal.save( state, target.cursor );
			if (
				saved.conflict ||
				( ! saved.durable && ! saved.cursor.memory )
			) {
				setUnsaved( true );
				return null;
			}
			setUnsaved( ! saved.durable );
			cursor.current = saved.cursor;
			failureState.current = saved.state;
			if ( saved.state.phase === 'editing' && saved.state.draft?.owner ) {
				context.adoptEditor( saved.state.draft.owner );
			} else {
				context.releaseEditor();
			}
			// Rebase the parked record over the activation write without consuming either owner.
			setDeferredFailure(
				parked ? journal.rebase( parked.cursor ) : null
			);
			return saved.state;
		},
		[ context ]
	);

	const placeChips = useCallback( ( chips: readonly Upload[] ) => {
		placingChips.current = true;
		if ( chips.length > 0 ) {
			filesRef.current.restore( [ ...chips ] );
		} else {
			filesRef.current.clear();
		}
	}, [] );

	// A chip removed, or a file attached again, while the failure is up.
	useEffect( () => {
		if ( placingChips.current ) {
			placingChips.current = false;
			return;
		}
		const next = failureWithUploads( failureState.current, files.uploads );
		if ( next === failureState.current ) {
			return;
		}
		failureState.current = persist( next );
		setOmitted( failureState.current.draft?.omitted ?? [] );
	}, [ files.uploads, persist ] );

	/**
	 * Leaves `failed` only when a retry would send. A second call finds
	 * `pending` and does not send.
	 *
	 * @param thread The thread the retry would post on top of.
	 */
	const openRetry = useCallback(
		( thread: readonly FailureMessage[] ): OpenRetry | null => {
			const current = failureState.current;
			if (
				'failed' !== current.phase ||
				! current.draft ||
				! current.kind ||
				! retryPayload( current, thread, filesRef.current.uploads )
			) {
				return null;
			}
			const identity = context.identity;
			if ( ! identity || context.phase !== 'ready' || ! cursor.current ) {
				return null;
			}
			// Preserve an accepted replacement before the Retry clears its field.
			context.checkpoint();
			// A deliberate Retry can refresh unchanged attempt bytes over another attempt's write.
			// Asynchronous settlements never rebase their captured cursor.
			const fresh = new FailureJournal(
				pageFailureStore(),
				identity
			).rebase( cursor.current );
			if ( ! fresh ) {
				return null;
			}
			cursor.current = fresh.cursor;
			const opened = { draft: current.draft, kind: current.kind };
			const committed = commitFailure( { type: 'retry' } );
			if (
				committed.phase === 'pending' &&
				committed.draft?.owner?.attempt === opened.draft.owner?.attempt
			) {
				context.releaseEditor();
				return opened;
			}
			return null;
		},
		[ commitFailure, context ]
	);

	/**
	 * The payload a retry would send, without changing the record. The
	 * catch of a send that never left still has this.
	 *
	 * @param draft  The failed question, as it was when the retry opened.
	 * @param kind   Which failure.
	 * @param thread The thread to send on top of.
	 */
	const previewRetry = useCallback(
		< T extends FailureMessage >(
			draft: FailureDraft,
			kind: FailureKind,
			thread: readonly T[]
		) =>
			retryPayload(
				{ phase: 'failed', draft, kind },
				thread,
				filesRef.current.uploads
			),
		[]
	);

	/**
	 * The payload against the thread now, or null after the failure is put
	 * back. An empty upstream question does not send.
	 *
	 * @param draft  The failed question, as it was when the retry opened.
	 * @param kind   Which failure.
	 * @param thread The thread to send on top of.
	 */
	const payloadOrRestore = useCallback(
		< T extends FailureMessage >(
			draft: FailureDraft,
			kind: FailureKind,
			thread: readonly T[]
		) => {
			const payload = retryPayload(
				{ phase: 'failed', draft, kind },
				thread,
				filesRef.current.uploads
			);
			if ( ! payload ) {
				commitFailure( { type: kind } );
				return null;
			}
			return payload;
		},
		[ commitFailure ]
	);

	return {
		failureState,
		adoptFailure,
		detachFailure,
		unsaved,
		deferredFailure,
		deferFailure: useCallback( ( candidate: FailureCandidate ) => {
			setDeferredFailure( candidate );
			setUnsaved( !! candidate.cursor.memory );
		}, [] ),
		preserveEditor,
		ignoreCurrentCandidate: useCallback(
			( candidate: FailureCandidate ) =>
				setDeferredFailure( ( previous ) =>
					previous?.cursor.owner.attempt ===
					candidate.cursor.owner.attempt
						? null
						: previous
				),
			[]
		),
		exchangeFailure,
		returnToEditing,
		parkFailure,
		omitted,
		setOmitted,
		commitFailure,
		placeChips,
		openRetry,
		previewRetry,
		payloadOrRestore,
	};
}
