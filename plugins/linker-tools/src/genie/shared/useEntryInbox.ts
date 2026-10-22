/** One marketing attempt owns one delivery before it enters the turn lane. */
import { useCallback, useEffect, useRef, useState } from '@wordpress/element';
import type { DraftContext } from './draftContext';
import type { GenieConfig } from '../config';
import type { Attachments } from '../attachments/useAttachments';
import type { Upload } from '../attachments/prepare';
import { EntryScopeError } from './entryFailure';
import { pageFailureStore } from './failure';
import { hasOwnedRecovery } from './ownedFailure';
import {
	ENTRY_KEY,
	entryAck,
	entryScope,
	finishEntry,
	isEntryDraft,
	readEntryRecovery,
	updateEntryRecovery,
	type EntryDraft,
} from './entryDraft';
interface Incoming {
	draft: EntryDraft;
	automatic: boolean;
}
interface Parked {
	text: string;
	uploads: Upload[];
	missing: string[];
}
interface Options {
	context: DraftContext;
	config: GenieConfig;
	input: string;
	setInput: ( text: string ) => void;
	files: Attachments;
	busy: boolean;
	ask: ( text: string, entryId: string, scope: string ) => Promise< boolean >;
	onVerified: ( scope: string ) => void;
	onComposerClaim: () => void;
	onMode: ( mode: EntryDraft[ 'mode' ] ) => void;
	onReplace: () => void;
	onInvalidated: ( scope: string ) => void;
	onRecovery: () => Promise< void >;
}
export function useEntryInbox( options: Options ) {
	const current = useRef( options );
	current.current = options;
	const nativeOwner = useCallback( async ( fresh = false ) => {
		// Entry authority remains a fresh durable read. Its accepted bytes must also
		// join the same current native owner as ordinary editing in this surface.
		const verified = await entryScope(
			current.current.config,
			fresh || !! current.current.context.identity
		);
		const context = current.current.context;
		await context.initialized();
		if ( context.identity?.scope !== verified ) {
			await context.verify( true );
		}
		const lease = await context.ready();
		if ( lease?.scope !== verified ) {
			throw new Error( 'entry-native-owner' );
		}
		return { scope: verified, lease };
	}, [] );

	const composerEpoch = useRef( 0 );
	const previousComposer = useRef( {
		input: options.input,
		picked: options.files.picked,
		busy: options.busy,
	} );
	if (
		previousComposer.current.input !== options.input ||
		previousComposer.current.picked !== options.files.picked ||
		previousComposer.current.busy !== options.busy
	) {
		composerEpoch.current += 1;
		previousComposer.current = {
			input: options.input,
			picked: options.files.picked,
			busy: options.busy,
		};
	}

	const [ inbox, setInbox ] = useState< Incoming[] >( [] );
	const [ parked, setParked ] = useState< Parked | null >( null );
	const [ missing, setMissing ] = useState< string[] >( [] );
	const [ identityError, setIdentityError ] = useState( false );
	const [ recoveryBlocked, setRecoveryBlocked ] = useState( false );
	const claimed = useRef( new Set< string >() );
	const checking = useRef( new Set< string >() );
	const handling = useRef( false );
	const handlingGeneration = useRef( 0 );
	const scope = useRef( '' );
	const live = useRef( true );
	const owned = useRef( false );
	const loaded = useRef< Promise< string > | null >( null );
	const recoveryPending = useRef( hasOwnedRecovery( pageFailureStore() ) );
	const blockedEpoch = useRef( 0 );
	const markRecoveryBlocked = useCallback( () => {
		recoveryPending.current = true;
		blockedEpoch.current += 1;
		setIdentityError( true );
		setRecoveryBlocked( true );
	}, [] );
	const claimComposer = useCallback(
		( verified: string, releasePending = false ) => {
			if ( current.current.context.identity?.scope !== verified ) {
				throw new Error( 'entry-native-owner' );
			}
			scope.current = verified;
			owned.current = true;
			current.current.onVerified( verified );
			current.current.onComposerClaim();
			if ( releasePending ) {
				recoveryPending.current = false;
			}
		},
		[]
	);
	const parkedRef = useRef( parked );
	parkedRef.current = parked;
	const missingRef = useRef( missing );
	if ( missingRef.current !== missing ) {
		composerEpoch.current += 1;
	}
	missingRef.current = missing;
	const offerRecovery = useCallback(
		( verified: string, candidate: Parked, releasePending = true ) => {
			const now = current.current;
			if ( now.busy || now.files.busy ) {
				markRecoveryBlocked();
				return false;
			}
			const occupied =
				now.input ||
				now.files.picked.length ||
				missingRef.current.length;
			if (
				! occupied ||
				( owned.current &&
					scope.current === verified &&
					now.input === candidate.text &&
					JSON.stringify( now.files.uploads ) ===
						JSON.stringify( candidate.uploads ) &&
					JSON.stringify( missingRef.current ) ===
						JSON.stringify( candidate.missing ) )
			) {
				if ( releasePending ) {
					recoveryPending.current = false;
				}
				return true;
			}
			if ( parkedRef.current || readEntryRecovery( verified ).parked ) {
				markRecoveryBlocked();
				return false;
			}
			const saved = updateEntryRecovery( verified, ( record ) => ( {
				...record,
				composer: {
					text: now.input,
					missing: [
						...missingRef.current,
						...now.files.uploads.map( ( file ) => file.name ),
					],
				},
				parked: {
					text: candidate.text,
					missing: [
						...candidate.missing,
						...candidate.uploads.map( ( file ) => file.name ),
					],
				},
			} ) );
			if ( ! saved ) {
				setIdentityError( true );
				markRecoveryBlocked();
				return false;
			}
			claimComposer( verified, releasePending );
			setParked( candidate );
			setRecoveryBlocked( false );
			setIdentityError( false );
			return false;
		},
		[ claimComposer, markRecoveryBlocked ]
	);
	const initialise = useCallback( () => {
		if ( loaded.current ) {
			return loaded.current;
		}
		loaded.current = nativeOwner()
			.then( ( { scope: next, lease } ) => {
				if (
					! live.current ||
					! current.current.context.owns( lease )
				) {
					throw new Error( 'entry-native-owner' );
				}
				scope.current = next;
				const record = readEntryRecovery( next );
				current.current.onVerified( next );
				setInbox(
					record.entries.map( ( draft ) => ( {
						draft,
						automatic: false,
					} ) )
				);
				if (
					record.composer &&
					offerRecovery(
						next,
						{ ...record.composer, uploads: [] },
						false
					)
				) {
					claimComposer( next );
					current.current.setInput( record.composer.text );
					setMissing( record.composer.missing );
				}
				if ( record.parked ) {
					setParked( { ...record.parked, uploads: [] } );
				}
				return next;
			} )
			.catch( ( error: unknown ) => {
				loaded.current = null;
				setIdentityError( true );
				markRecoveryBlocked();
				throw error;
			} );
		return loaded.current;
	}, [ claimComposer, offerRecovery, markRecoveryBlocked, nativeOwner ] );
	useEffect( () => {
		live.current = true;
		try {
			if ( sessionStorage.getItem( ENTRY_KEY ) ) {
				void initialise().catch( () => undefined );
			}
		} catch {
			/* No storage: live editor remains owner. */
		}
		return () => {
			live.current = false;
		};
	}, [ initialise, nativeOwner ] );
	const receive = useCallback(
		( value: unknown ) => {
			if ( ! isEntryDraft( value ) ) {
				return;
			}
			// Synchronous reservation before all awaits and React paint.
			if ( checking.current.has( value.id ) ) {
				return;
			}
			checking.current.add( value.id );
			void initialise()
				.then( async () => {
					const { scope: verified, lease } =
						await nativeOwner( true );
					if (
						! live.current ||
						! current.current.context.owns( lease )
					) {
						return;
					}
					if ( verified !== value.scope ) {
						readEntryRecovery( verified );
						if ( owned.current ) {
							current.current.setInput( '' );
							current.current.files.clear();
						}
						current.current.onInvalidated( scope.current );
						setInbox( [] );
						setParked( null );
						setMissing( [] );
						setIdentityError( true );
						entryAck( value, 'failed' );
						return;
					}
					if ( scope.current !== verified ) {
						loaded.current = null;
						await initialise();
					}
					if ( ! current.current.context.owns( lease ) ) {
						throw new Error( 'entry-native-owner' );
					}
					if ( claimed.current.has( value.id ) ) {
						if (
							readEntryRecovery( verified ).entries.some(
								( item ) => item.id === value.id
							)
						) {
							setInbox( ( items ) =>
								items.some(
									( item ) => item.draft.id === value.id
								)
									? items
									: [
											...items,
											{ draft: value, automatic: false },
										]
							);
						}
						entryAck( value, 'accepted' );
						return;
					}
					setIdentityError( false );
					const wasOwned = readEntryRecovery(
						verified
					).claimed.includes( value.id );
					if (
						wasOwned &&
						! readEntryRecovery( verified ).entries.some(
							( item ) => item.id === value.id
						)
					) {
						entryAck( value, 'accepted' );
						return;
					}
					const saved = updateEntryRecovery(
						verified,
						( state ) => ( {
							...state,
							entries: state.entries.some(
								( item ) => item.id === value.id
							)
								? state.entries
								: [ ...state.entries, value ],
							claimed: [
								...new Set( [ ...state.claimed, value.id ] ),
							],
						} )
					);
					if ( ! saved ) {
						throw new Error( 'entry-recovery' );
					}
					setInbox( ( items ) => [
						...items.filter(
							( item ) => item.draft.id !== value.id
						),
						{ draft: value, automatic: ! wasOwned },
					] );
					claimed.current.add( value.id );
					entryAck( value, 'accepted' );
				} )
				.catch( () => {
					claimed.current.delete( value.id );
					if (
						current.current.context.identity?.scope === value.scope
					) {
						setInbox( ( items ) =>
							items.some( ( item ) => item.draft.id === value.id )
								? items
								: [
										...items,
										{ draft: value, automatic: false },
									]
						);
					}
					setIdentityError( true );
					entryAck( value, 'failed' );
				} )
				.finally( () => checking.current.delete( value.id ) );
		},
		[ initialise, nativeOwner ]
	);
	const remove = useCallback( ( draft: EntryDraft ) => {
		if ( ! finishEntry( draft ) ) {
			return false;
		}
		setInbox( ( items ) =>
			items.filter( ( item ) => item.draft.id !== draft.id )
		);
		return true;
	}, [] );
	const accept = useCallback(
		async ( draft: EntryDraft, separate = false ) => {
			const now = current.current;
			const startingLease = now.context.capture();
			if (
				! startingLease ||
				handling.current ||
				now.busy ||
				now.files.busy
			) {
				return;
			}
			handling.current = true;
			const operation = ++handlingGeneration.current;
			const epoch = composerEpoch.current;
			try {
				const { scope: verified, lease } = await nativeOwner( true );
				if (
					! current.current.context.owns( startingLease ) ||
					handlingGeneration.current !== operation
				) {
					return;
				}
				if ( verified !== draft.scope ) {
					readEntryRecovery( verified );
					if ( owned.current ) {
						current.current.setInput( '' );
						current.current.files.clear();
					}
					current.current.onInvalidated( scope.current );
					setInbox( [] );
					setParked( null );
					setMissing( [] );
					setIdentityError( true );
					return;
				}
				if (
					composerEpoch.current !== epoch ||
					! current.current.context.owns( lease ) ||
					current.current.input !== now.input ||
					current.current.files.picked !== now.files.picked ||
					current.current.busy
				) {
					setInbox( ( items ) =>
						items.map( ( item ) =>
							item.draft.id === draft.id
								? { ...item, automatic: false }
								: item
						)
					);
					return;
				}
				if ( separate && parked ) {
					return;
				}
				const previous = separate
					? {
							text: now.input,
							uploads: [ ...now.files.uploads ],
							missing: [ ...missing ],
						}
					: null;
				const persisted = updateEntryRecovery(
					verified,
					( record ) => ( {
						...record,
						claimed: [
							...new Set( [ ...record.claimed, draft.id ] ),
						],
						...( previous
							? {
									parked: {
										text: previous.text,
										missing: [
											...previous.missing,
											...previous.uploads.map(
												( file ) => file.name
											),
										],
									},
								}
							: {} ),
						...( draft.mode !== 'compose'
							? {
									composer: { text: draft.text, missing: [] },
									entries: record.entries.filter(
										( item ) => item.id !== draft.id
									),
								}
							: {} ),
					} )
				);
				if ( ! persisted ) {
					throw new Error( 'entry-recovery' );
				}
				if ( previous ) {
					setParked( previous );
					now.files.clear();
				}
				claimed.current.add( draft.id );
				entryAck( draft, 'accepted' );
				claimComposer( verified );
				setMissing( [] );
				if ( draft.mode === 'compose' ) {
					const completed = await now.ask(
						draft.text,
						draft.id,
						draft.scope
					);
					if (
						! current.current.context.valid( lease ) ||
						handlingGeneration.current !== operation
					) {
						return;
					}
					if ( ! completed ) {
						setInbox( ( items ) =>
							items.map( ( item ) =>
								item.draft.id === draft.id
									? { ...item, automatic: false }
									: item
							)
						);
						return;
					}
				} else {
					now.setInput( draft.text );
					now.onMode( draft.mode );
				}
				if (
					! current.current.context.valid( lease ) ||
					handlingGeneration.current !== operation
				) {
					return;
				}
				if ( ! remove( draft ) ) {
					throw new Error( 'entry-recovery' );
				}
				entryAck( draft, 'settled' );
			} catch {
				if (
					! live.current ||
					! current.current.context.owns( startingLease ) ||
					handlingGeneration.current !== operation
				) {
					return;
				}
				setIdentityError( true );
				entryAck( draft, 'failed' );
				setInbox( ( items ) =>
					items.map( ( item ) =>
						item.draft.id === draft.id
							? { ...item, automatic: false }
							: item
					)
				);
			} finally {
				if ( handlingGeneration.current === operation ) {
					handling.current = false;
				}
			}
		},
		[ missing, remove, parked, claimComposer, nativeOwner ]
	);
	useEffect( () => {
		const first = inbox[ 0 ];
		if (
			first?.automatic &&
			options.context.phase === 'ready' &&
			! options.busy &&
			! options.input &&
			options.files.picked.length === 0 &&
			missing.length === 0
		) {
			void accept( first.draft );
		}
	}, [
		inbox,
		options.context.phase,
		options.busy,
		options.input,
		options.files.picked.length,
		missing.length,
		accept,
	] );
	useEffect( () => {
		if ( ! scope.current || ! owned.current || options.busy ) {
			return;
		}
		updateEntryRecovery( scope.current, ( record ) => ( {
			...record,
			composer:
				options.input || options.files.picked.length || missing.length
					? {
							text: options.input,
							missing: [
								...new Set( [
									...missing,
									...options.files.picked
										.filter(
											( item ) => item.state !== 'refused'
										)
										.map( ( item ) => item.name ),
								] ),
							],
						}
					: null,
		} ) );
	}, [ options.input, options.files.picked, options.busy, missing ] );
	useEffect( () => {
		if ( missing.length === 0 ) {
			return;
		}
		const ready = new Set(
			options.files.uploads.map( ( file ) => file.name )
		);
		if ( missing.some( ( name ) => ready.has( name ) ) ) {
			setMissing( ( names ) =>
				names.filter( ( name ) => ! ready.has( name ) )
			);
		}
	}, [ options.files.uploads, missing ] );

	const verifyCurrent = useCallback(
		async ( expected: string, transport = false ) => {
			try {
				const { scope: next, lease } = await nativeOwner( true );
				if ( ! current.current.context.owns( lease ) ) {
					return false;
				}
				if ( next === expected ) {
					return true;
				}
				readEntryRecovery( next );
				current.current.onInvalidated( expected );
				if ( owned.current ) {
					current.current.setInput( '' );
					current.current.files.clear();
				}
				setInbox( [] );
				setParked( null );
				setMissing( [] );
			} catch {
				setIdentityError( true );
				if ( transport ) {
					throw new EntryScopeError( false );
				}
				return false;
			}
			setIdentityError( true );
			return false;
		},
		[ nativeOwner ]
	);
	const append = useCallback(
		async ( draft: EntryDraft ) => {
			if ( handling.current || current.current.busy ) {
				return;
			}
			handling.current = true;
			const epoch = composerEpoch.current;
			// Must precede the await: New/Select invalidates this restoration.
			// eslint-disable-next-line @wordpress/no-unused-vars-before-return
			const lease = current.current.context.capture();
			try {
				if ( ! ( await verifyCurrent( draft.scope ) ) ) {
					return;
				}
				if (
					composerEpoch.current !== epoch ||
					! current.current.context.owns( lease ) ||
					current.current.busy ||
					current.current.files.busy
				) {
					return;
				}
				const now = current.current;
				const combined = now.input
					? `${ now.input }\n${ draft.text }`
					: draft.text;
				if (
					! updateEntryRecovery( draft.scope, ( record ) => ( {
						...record,
						claimed: [
							...new Set( [ ...record.claimed, draft.id ] ),
						],
						composer: {
							text: combined,
							missing: [
								...missing,
								...now.files.uploads.map(
									( file ) => file.name
								),
							],
						},
						entries: record.entries.filter(
							( item ) => item.id !== draft.id
						),
					} ) )
				) {
					setIdentityError( true );
					return;
				}
				claimed.current.add( draft.id );
				entryAck( draft, 'accepted' );
				claimComposer( draft.scope );
				now.setInput( combined );
				now.onMode( draft.mode );
				remove( draft );
			} finally {
				handling.current = false;
			}
		},
		[ remove, verifyCurrent, missing, claimComposer ]
	);

	const defer = useCallback( ( draft: EntryDraft ) => {
		setInbox( ( items ) =>
			items.map( ( item ) =>
				item.draft.id === draft.id
					? { ...item, automatic: false }
					: item
			)
		);
	}, [] );
	const restoreParked = useCallback( async () => {
		if (
			! parked ||
			handling.current ||
			current.current.busy ||
			current.current.files.busy
		) {
			return;
		}
		handling.current = true;
		const epoch = composerEpoch.current;
		// Must precede the await: New/Select invalidates this restoration.
		// eslint-disable-next-line @wordpress/no-unused-vars-before-return
		const lease = current.current.context.capture();
		try {
			if ( ! ( await verifyCurrent( scope.current ) ) ) {
				return;
			}
			if (
				composerEpoch.current !== epoch ||
				! current.current.context.owns( lease ) ||
				current.current.busy ||
				current.current.files.busy
			) {
				return;
			}
			const now = current.current;
			const next =
				now.input || now.files.uploads.length || missing.length
					? {
							text: now.input,
							uploads: [ ...now.files.uploads ],
							missing: [ ...missing ],
						}
					: null;
			if (
				! updateEntryRecovery( scope.current, ( record ) => ( {
					...record,
					composer: {
						text: parked.text,
						missing: [
							...parked.missing,
							...parked.uploads.map( ( file ) => file.name ),
						],
					},

					parked: next
						? {
								text: next.text,
								missing: [
									...next.missing,
									...next.uploads.map(
										( file ) => file.name
									),
								],
							}
						: null,
				} ) )
			) {
				setIdentityError( true );
				return;
			}
			claimComposer( scope.current );
			now.onReplace();
			now.setInput( parked.text );
			now.files.restore( parked.uploads );
			setMissing( parked.missing );
			setParked( next );
		} finally {
			handling.current = false;
		}
	}, [ parked, missing, verifyCurrent, claimComposer ] );

	return {
		detach: () => {
			handlingGeneration.current += 1;
			handling.current = false;
			owned.current = false;
			scope.current = '';
			loaded.current = null;
			composerEpoch.current += 1;
			setInbox( [] );
			setParked( null );
			setMissing( [] );
			setIdentityError( false );
		},
		claimComposer,
		resolveRecovery: () => {
			recoveryPending.current = false;
			setRecoveryBlocked( false );
			setIdentityError( false );
		},
		offerRecovery,
		blockRecovery: () => {
			setIdentityError( true );
			markRecoveryBlocked();
		},
		retryRecovery: async () => {
			if (
				current.current.busy ||
				current.current.files.busy ||
				handling.current
			) {
				return;
			}
			const epoch = composerEpoch.current;
			loaded.current = null;
			try {
				await initialise();
				if (
					current.current.busy ||
					current.current.files.busy ||
					composerEpoch.current !== epoch
				) {
					return;
				}
				setIdentityError( false );
				setRecoveryBlocked( false );
				const boundary = blockedEpoch.current;
				await current.current.onRecovery();
				if (
					blockedEpoch.current === boundary &&
					! current.current.busy &&
					! current.current.files.busy
				) {
					recoveryPending.current = false;
				}
			} catch {
				/* Keep the record hidden and recoverable. */
			}
		},
		recoveryBlocked,
		recoveryPending,
		resetComposer: () => {
			owned.current = false;
			composerEpoch.current += 1;
			setMissing( [] );
			setInbox( ( items ) =>
				items.map( ( item ) => ( { ...item, automatic: false } ) )
			);
			if ( scope.current ) {
				updateEntryRecovery( scope.current, ( record ) => ( {
					...record,
					composer: null,
				} ) );
			}
		},
		authorize: ( expected?: string ) =>
			expected || owned.current
				? verifyCurrent( expected ?? scope.current, true )
				: Promise.resolve( true ),
		receive,
		inbox,
		accept,
		append,
		defer,
		parked,
		restoreParked,
		missing,
		setMissing,
		identityError,
		owned,
	};
}
