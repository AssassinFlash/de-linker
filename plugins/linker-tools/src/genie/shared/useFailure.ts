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
import {
	preserveEditing,
	type EditingSnapshot,
	type EditingAuthority,
} from './editingDraft';
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
	const editingCursor = useRef< FailureCursor | null >( null );
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
					if ( ! journal.consume( cursor.current, true ) ) {
						setUnsaved( true );
						return failureState.current;
					}
				}
				cursor.current = null;
				try {
					setUnsaved( !! journal.candidate()?.cursor.memory );
				} catch {
					setUnsaved( true );
				}
				return next;
			}
			const editor = context.editor;
			const checkpoint = editingCursor.current;
			const promoting =
				start &&
				editor &&
				checkpoint?.owner.scope === editor.scope &&
				checkpoint.owner.attempt === editor.attempt;
			const checked = promoting ? journal.rebase( checkpoint ) : null;
			if (
				promoting &&
				( ! checked ||
					! journal.sameCheckpoint( checkpoint, checked.cursor ) )
			) {
				setUnsaved( true );
				const newer = journal.editing( editor );
				if ( newer ) {
					setDeferredFailure( newer );
				}
				return failureState.current;
			}
			let result;
			if ( checked ) {
				result = journal.save(
					{
						...next,
						draft: next.draft
							? { ...next.draft, owner: editor! }
							: null,
					},
					checked.cursor
				);
			} else if ( start || ! cursor.current ) {
				result = journal.begin( next, editor ?? undefined );
			} else {
				result = journal.save( next, cursor.current );
			}
			if ( result.conflict ) {
				setUnsaved( true );
				return failureState.current;
			}
			cursor.current = result.cursor;
			if ( result.state.phase === 'editing' ) {
				editingCursor.current = result.cursor;
			}
			if ( start ) {
				context.releaseEditor();
			}
			setUnsaved(
				! result.durable ||
					!! journal.alternative( result.cursor )?.cursor.memory
			);
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
				editingCursor.current = cursor.current;
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
		editingCursor.current = null;
	}, [] );

	const exposeAlternative = useCallback( () => {
		const current = editingCursor.current;
		const identity = context.identity;
		if (
			! current ||
			context.phase !== 'ready' ||
			! identity ||
			context.editor?.scope !== current.owner.scope ||
			context.editor.attempt !== current.owner.attempt ||
			identity.scope !== current.owner.scope
		) {
			return;
		}
		const other = new FailureJournal(
			pageFailureStore(),
			identity
		).alternative( current );
		if ( other ) {
			setDeferredFailure( other );
			setUnsaved( !! current.memory || !! other.cursor.memory );
		}
	}, [ context ] );
	useEffect(
		() => context.subscribe( exposeAlternative ),
		[ context, exposeAlternative ]
	);

	const preserveEditor = useCallback(
		( snapshot: EditingSnapshot, accepted?: EditingAuthority ) => {
			const identity = accepted?.identity ?? context.identity;
			const owner = accepted?.owner ?? context.editor;
			const original = editingCursor.current;
			const authority =
				accepted ??
				( owner &&
				identity &&
				original?.owner.scope === owner.scope &&
				original.owner.attempt === owner.attempt
					? { owner, identity, cursor: original }
					: undefined );
			let result = preserveEditing( context, snapshot, authority );
			if (
				result?.conflict &&
				! accepted &&
				authority?.cursor &&
				identity &&
				owner
			) {
				const journal = new FailureJournal(
					pageFailureStore(),
					identity
				);
				const acknowledged = journal.acknowledged( authority.cursor );
				const occupied =
					!! snapshot.text ||
					!! snapshot.uploads.length ||
					!! snapshot.missing.length;
				const unchanged =
					acknowledged &&
					acknowledged.text === snapshot.text &&
					JSON.stringify( acknowledged.uploads ) ===
						JSON.stringify( snapshot.uploads ) &&
					JSON.stringify( acknowledged.omitted ) ===
						JSON.stringify( snapshot.missing );
				if ( occupied && ! unchanged ) {
					result = journal.retain(
						{
							phase: 'editing',
							kind: null,
							draft: {
								owner,
								editing: true,
								text: snapshot.text,
								question:
									buildQuestion(
										snapshot.text,
										snapshot.uploads
									) || snapshot.missing.join( '\n' ),
								uploads: snapshot.uploads,
								omitted: snapshot.missing,
							},
						},
						authority.cursor
					);
				} else {
					// A newer same-copy record is recovery evidence, never permission
					// for this stale editor to overwrite or delete that version.
					const newer = journal.editing( owner );
					if ( newer ) {
						setDeferredFailure( newer );
					}
					if ( ! occupied && context.editor === owner ) {
						context.releaseEditor();
						editingCursor.current = null;
					}
				}
			}
			if ( result ) {
				setUnsaved( ! result.durable );
				if ( ! result.conflict && result.state.phase === 'editing' ) {
					editingCursor.current = result.cursor;
					exposeAlternative();
				}
				// Only our own synchronous checkpoint can advance the pending cursor
				// over a different editor's write. Late callbacks never rebase it.
				if ( ! result.conflict && cursor.current && identity ) {
					const current = new FailureJournal(
						pageFailureStore(),
						identity
					).rebase( cursor.current );
					if ( current ) {
						cursor.current = current.cursor;
					}
				}
			}
			return result;
		},
		[ context, exposeAlternative ]
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
			editingCursor.current = cursor.current;
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
			let target = journal.variant( candidate.cursor );
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
				const owner = context.editor;
				const expected = editingCursor.current;
				if ( ! owner ) {
					// An automatically restored failure already has an exact stored
					// record. It is not a newly accepted editing owner to reassign.
					parked = cursor.current
						? journal.variant( cursor.current )
						: null;
					if (
						! parked ||
						parked.record.text !== displaced.draft.text ||
						JSON.stringify( parked.record.uploads ) !==
							JSON.stringify( displaced.draft.uploads ) ||
						JSON.stringify( parked.record.omitted ) !==
							JSON.stringify( displaced.draft.omitted )
					) {
						return null;
					}
				} else {
					const state = {
						...displaced,
						draft: { ...displaced.draft, owner },
					};
					let saved =
						expected?.owner.scope === owner.scope &&
						expected.owner.attempt === owner.attempt
							? journal.checkpoint( state, expected )
							: journal.begin( state, owner );
					if ( saved.conflict && expected ) {
						const acknowledged = journal.acknowledged( expected );
						const same =
							acknowledged?.text === state.draft.text &&
							JSON.stringify( acknowledged.uploads ) ===
								JSON.stringify( state.draft.uploads ) &&
							JSON.stringify( acknowledged.omitted ) ===
								JSON.stringify( state.draft.omitted );
						if ( same ) {
							const newer = journal.editing( owner );
							if ( newer ) {
								parked = newer;
							}
						} else {
							saved = journal.retain( state, expected );
						}
					}
					setUnsaved( ! saved.durable );
					if (
						( saved.conflict && ! parked ) ||
						( ! saved.durable &&
							! saved.cursor.memory &&
							! parked ) ||
						! saved.state.draft
					) {
						return null;
					}
					parked ??= {
						record: {
							...saved.state.draft,
							v: 1,
							kind: saved.state.kind,
						},
						cursor: saved.cursor,
					};
				}
				target = journal.variant( candidate.cursor );
				if ( ! target ) {
					return null;
				}
			}
			target = journal.select( target.cursor );
			if ( ! target ) {
				return null;
			}
			const state = reconcile( target.record, messages );
			if ( state.phase === 'clear' ) {
				if ( ! journal.consume( target.cursor, true ) ) {
					setUnsaved( true );
				}
				setDeferredFailure(
					journal.alternative( target.cursor ) ??
						( parked ? journal.variant( parked.cursor ) : null )
				);
				return state;
			}
			const saved = journal.save( state, target.cursor );
			if (
				saved.conflict ||
				( ! saved.durable && ! saved.cursor.memory )
			) {
				setUnsaved( true );
				if ( parked ) {
					journal.select( parked.cursor );
				}
				return null;
			}
			setUnsaved(
				! saved.durable ||
					!! parked?.cursor.memory ||
					!! journal.alternative( saved.cursor )?.cursor.memory
			);
			cursor.current = saved.cursor;
			editingCursor.current =
				saved.state.phase === 'editing' ? saved.cursor : null;
			failureState.current = saved.state;
			if ( saved.state.phase === 'editing' && saved.state.draft?.owner ) {
				context.adoptEditor( saved.state.draft.owner );
			} else {
				context.releaseEditor();
			}
			// Rebase the parked record over the activation write without consuming either owner.
			setDeferredFailure(
				journal.alternative( saved.cursor ) ??
					( parked ? journal.variant( parked.cursor ) : null )
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
