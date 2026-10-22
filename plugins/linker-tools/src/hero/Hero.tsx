/**
 * The conversation the home hero unfolds in place (ticket #232, variant B):
 * the header the owner specified, the shared thread (session.ts), the #236
 * attachment cards, the #250 inquiry confirmation card and the #243 contact
 * card, and the answer's cards in a four-column grid (two on a phone).
 *
 * The page's own textarea stays the follow-up field: this component renders
 * above it, inside `.hero-dialog`, and the controller wires Enter, the send
 * button and the capsules to the bridge this component registers.
 */

/**
 * WordPress dependencies
 */
import { useCallback, useEffect, useRef, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { storeClient } from '../configurator/api/store';
import { rememberInquiry } from '../protection/inquiryHandoff';
import type { SentInquiry } from '../genie/api/inquiry';
import {
	assistantMessage,
	turnConflictText,
	type Block,
	type ContactBlock,
	type SentContact,
	type SentInquiryCard,
	type Turn,
	type TurnMessage,
} from '../genie/api/turn';
import type { Upload } from '../genie/attachments/prepare';
import { useAttachments } from '../genie/attachments/useAttachments';
import { AttachmentCard } from '../genie/components/AttachmentCard';
import {
	AttachmentChips,
	refusalText,
} from '../genie/components/AttachmentChips';
import { BlockView } from '../genie/components/BlockView';
import { Compare } from '../genie/components/Compare';
import { ContactCard, ContactSent } from '../genie/components/ContactCard';
import { GenieCard } from '../genie/components/GenieCard';
import { InquiryCard, InquirySent } from '../genie/components/InquiryCard';
import { MissingFiles } from '../genie/components/MissingFiles';
import { OwnedRecovery } from '../genie/components/OwnedRecovery';
import { Reply } from '../genie/components/Reply';
import { Transcript } from '../genie/components/Transcript';
import type { GenieConfig } from '../genie/config';
import { idsOf, pricesOf } from '../genie/shared/blocks';
import { useCardActions } from '../genie/shared/cardActions';
import { buildQuestion, typeModelPrompt } from '../genie/shared/conversation';
import {
	composerFor,
	failureText,
	omittedFileNotice,
	pageFailureStore,
	presentFailure,
	reconcile,
	refusalReason,
	retryMessages,
	settleTurnFailure,
	type FailureDraft,
} from '../genie/shared/failure';
import {
	EntryScopeError,
	verifiedEntryFailure,
} from '../genie/shared/entryFailure';
import { newEntryId, updateEntryRecovery } from '../genie/shared/entryDraft';
import { useDraftContext } from '../genie/shared/useDraftContext';
import type { DraftContext, DraftLease } from '../genie/shared/draftContext';
import { useFailure } from '../genie/shared/useFailure';
import { HeroSession } from './session';

const emptyPrompt = () => ( { text: '', version: 0 } );

/** The controller's way into the conversation while it is unfolded. */
export interface HeroBridge {
	/**
	 * Asks a question; picked files are prepared first and sent with it.
	 *
	 * @param text  The question (empty when the files are the question).
	 * @param files The files just picked, if any.
	 */
	ask: ( text: string, files?: ArrayLike< File > ) => void;
	mode: ( mode: 'attach' | 'nameplate' | 'voice' ) => void;
}

/** Everything the page hands the conversation. */
export interface HeroConversationProps {
	config: GenieConfig;
	session: HeroSession;
	/** Registers the bridge the page's controls call. */
	onReady: ( bridge: HeroBridge ) => void;
	/** "Continue in the side panel". */
	onContinue: () => void;
	/** The × restores the resting hero. */
	onClose: () => void;
	/** Whether the conversation now has messages (the page shows its way back). */
	onConversation: ( has: boolean ) => void;
	/** Writes the page's follow-up field (the manual model exit). */
	setPrompt: ( text: string ) => void;
	/** Focuses the page's follow-up field. */
	focusPrompt: () => void;
	readPrompt?: () => { text: string; version: number };
	/** Opens the page's file picker. */
	requestPicker: () => void;
	requestVoice?: () => void;
	context?: DraftContext;
}

type Phase = 'ask' | 'waiting' | 'error';

export function HeroConversation( {
	config,
	session,
	onReady,
	onContinue,
	onClose,
	onConversation,
	setPrompt,
	focusPrompt,
	readPrompt = emptyPrompt,
	requestPicker,
	requestVoice,
	context,
}: HeroConversationProps ) {
	const [ thread, setThread ] = useState< TurnMessage[] >( [] );
	const [ turn, setTurn ] = useState< Turn | null >( null );
	const [ phase, setPhase ] = useState< Phase >( 'ask' );
	const [ refused, setRefused ] = useState( '' );
	const [ recoveryBlocked, setRecoveryBlocked ] = useState( false );
	const [ hydrated, setHydrated ] = useState( false );
	const [ recoveryAttempt, setRecoveryAttempt ] = useState( 0 );
	// The stored thread moved while Genie was answering (#373). The question
	// goes back into the page's field; it was not stored.
	const [ conflict, setConflict ] = useState( '' );
	// The newest answer, spoken by the live region when it arrives.
	const [ live, setLive ] = useState( '' );
	const [ pendingSend, setPendingSend ] = useState< {
		text: string;
	} | null >( null );
	// The cards that were already sent from this conversation (#243/#250).
	const [ contacts, setContacts ] = useState< SentContact[] >( [] );
	const [ inquiries, setInquiries ] = useState< SentInquiryCard[] >( [] );
	const turnAt = useRef( -1 );
	const sending = useRef( false );
	const entryOwnerScope = useRef< string | undefined >( undefined );
	const recoveryPending = useRef( true );
	const closeRef = useRef< HTMLButtonElement >( null );
	const ownerCleanup = useRef< () => void >( () => undefined );
	const draftContext = useDraftContext(
		config,
		() => ownerCleanup.current(),
		context
	);
	const [ retainedMode, setRetainedMode ] = useState<
		'attach' | 'nameplate' | 'voice' | null
	>( null );
	const files = useAttachments( draftContext );
	// The bridge is registered once; the refs keep it calling the latest
	// render's send and file state.
	const filesRef = useRef( files );
	filesRef.current = files;
	const {
		failureState,
		adoptFailure,
		detachFailure,
		unsaved,
		deferredFailure,
		deferFailure,
		exchangeFailure,
		returnToEditing,
		parkFailure,
		preserveEditor,
		ignoreCurrentCandidate,
		omitted,
		setOmitted,
		commitFailure,
		placeChips,
		openRetry,
		payloadOrRestore,
	} = useFailure( files, draftContext );
	ownerCleanup.current = () => {
		session.invalidate();
		detachFailure();
		setPrompt( '' );
		filesRef.current.clear();
		sending.current = false;
		setPhase( 'ask' );
		setThread( [] );
		setTurn( null );
		setContacts( [] );
		setInquiries( [] );
		setLive( '' );
		setRefused( '' );
		setConflict( '' );
		setPendingSend( null );
		entryOwnerScope.current = undefined;
		setHydrated( false );
		recoveryPending.current = true;
	};
	const omittedRef = useRef( omitted );
	omittedRef.current = omitted;
	useEffect(
		() =>
			draftContext.beforeLeave( () => {
				preserveEditor( {
					text: readPrompt().text,
					uploads: filesRef.current.uploads,
					missing: [
						...omittedRef.current,
						...filesRef.current.picked
							.filter( ( item ) => item.state !== 'ready' )
							.map( ( item ) => item.name ),
					],
				} );
			} ),
		[ draftContext, preserveEditor, readPrompt ]
	);

	const sendRef = useRef< ( text: string ) => void >( () => undefined );
	const [ store ] = useState( () => storeClient( config.restUrl ) );
	const {
		statusFor,
		addToDraft: addCardToDraft,
		addPartsToDraft,
		saveCardSolution,
	} = useCardActions( {
		restUrl: config.restUrl,
		restNonce: config.restNonce,
		locale: config.locale,
		store,
	} );
	const locale = config.locale;

	// The conversation the browser already has: the dock's thread, or what
	// the hero itself asked before it was folded and unfolded again.
	useEffect( () => {
		if ( draftContext.phase !== 'ready' ) {
			return;
		}
		let cancelled = false;
		const hasPendingOwner = () => failureState.current.phase === 'pending';
		const lease = draftContext.capture();
		void session
			.load()
			.then( async ( stored ) => {
				if (
					cancelled ||
					! draftContext.valid( lease ) ||
					hasPendingOwner()
				) {
					// A send on this mount already owns the thread. Applying
					// the read that started earlier would wipe it.
					return;
				}
				setThread( stored.messages );
				setTurn( stored.turn );
				setContacts( stored.contacts ?? [] );
				setInquiries( stored.inquiries ?? [] );
				turnAt.current = stored.turn ? stored.messages.length - 1 : -1;
				const checked = await verifiedEntryFailure(
					config,
					pageFailureStore(),
					draftContext
				);
				if ( ! checked && ! cancelled ) {
					setRecoveryBlocked( true );
				}
				if (
					! checked ||
					! checked.unchanged() ||
					cancelled ||
					! draftContext.valid( lease ) ||
					checked.identity.scope !== lease?.scope ||
					hasPendingOwner()
				) {
					return;
				}
				recoveryPending.current = false;
				setHydrated( true );
				const now = readPrompt();
				const occupied =
					!! now.text ||
					filesRef.current.picked.length > 0 ||
					omittedRef.current.length > 0;
				if (
					checked.candidate &&
					checked.record?.editing &&
					draftContext.editor?.attempt ===
						checked.record.owner?.attempt &&
					now.text === checked.record.text &&
					JSON.stringify( filesRef.current.uploads ) ===
						JSON.stringify( checked.record.uploads ) &&
					JSON.stringify( omittedRef.current ) ===
						JSON.stringify( checked.record.omitted )
				) {
					ignoreCurrentCandidate( checked.candidate );
					setRecoveryBlocked( false );
					return;
				}
				const reconciled = reconcile( checked.record, stored.messages );
				if (
					checked.candidate &&
					reconciled.phase !== 'clear' &&
					( ! checked.record?.entryId || occupied )
				) {
					deferFailure( checked.candidate );
					setRecoveryBlocked( false );
					return;
				}
				setRecoveryBlocked( false );
				entryOwnerScope.current = checked.record?.entryScope;
				recoveryPending.current = false;
				const restored = adoptFailure(
					checked.candidate,
					reconcile( checked.record, stored.messages )
				);
				failureState.current = restored;
				if (
					'failed' === restored.phase &&
					restored.draft &&
					restored.kind
				) {
					const composer = composerFor(
						restored.kind,
						restored.draft
					);
					setPrompt( composer.field );
					placeChips( composer.chips );
					setOmitted( composer.omitted );
					setPhase( 'error' );
				} else {
					setOmitted( [] );
				}
			} )
			.catch( () => undefined );
		return () => {
			cancelled = true;
		};
	}, [
		session,
		setPrompt,
		placeChips,
		failureState,
		setOmitted,
		config,
		recoveryAttempt,
		readPrompt,
		draftContext,
		draftContext.identity?.scope,
		adoptFailure,
		deferFailure,
		ignoreCurrentCandidate,
	] );

	const restoreOwnedFailure = async () => {
		const candidate = deferredFailure;
		const lease = draftContext.capture();
		if (
			! candidate ||
			! lease ||
			sending.current ||
			filesRef.current.busy
		) {
			return;
		}
		const before = readPrompt();
		const picked = filesRef.current.picked;
		const missing = omittedRef.current;

		if (
			! ( await draftContext.authorize( lease ) ) ||
			readPrompt().text !== before.text ||
			readPrompt().version !== before.version ||
			filesRef.current.picked !== picked ||
			omittedRef.current !== missing ||
			sending.current ||
			filesRef.current.busy
		) {
			return;
		}
		const displaced =
			before.text || filesRef.current.uploads.length || missing.length
				? {
						phase: 'editing' as const,
						kind: null,
						draft: {
							...failureState.current.draft,
							editing: true,
							text: before.text,
							question:
								buildQuestion(
									before.text,
									filesRef.current.uploads
								) || missing.join( '\n' ),
							uploads: filesRef.current.uploads,
							omitted: missing,
						},
					}
				: null;
		const restored = exchangeFailure(
			candidate,
			displaced,
			session.messages
		);
		if ( ! restored?.draft ) {
			return;
		}
		entryOwnerScope.current = restored.draft.entryScope;
		if ( restored.phase === 'editing' ) {
			setPrompt( restored.draft.text );
			placeChips( restored.draft.uploads );
			setOmitted( restored.draft.omitted );
			setPhase( 'ask' );
			return;
		}
		if ( ! restored.kind ) {
			return;
		}
		const composer = composerFor( restored.kind, restored.draft );
		setPrompt( composer.field );
		placeChips( composer.chips );
		setOmitted( composer.omitted );
		setPhase( 'error' );
	};

	// The conversation has the focus when it unfolds; the page's trigger gets
	// it back when it closes (the controller restores it).
	useEffect( () => {
		closeRef.current?.focus();
	}, [] );

	useEffect( () => {
		onConversation( thread.length > 0 );
	}, [ thread.length, onConversation ] );

	const sent = useCallback( ( email: string, receipt: boolean ) => {
		const after = turnAt.current;
		setContacts( ( known ) =>
			known.some( ( card ) => card.after === after )
				? known
				: [ ...known, { after, email, receipt } ]
		);
	}, [] );

	const inquirySent = useCallback( ( inquiry: SentInquiry ) => {
		const after = turnAt.current;
		setInquiries( ( known ) =>
			known.some( ( card ) => card.after === after )
				? known
				: [ ...known, { ...inquiry, after } ]
		);
	}, [] );

	const handleTurnError = useCallback(
		async (
			error: unknown,
			before: TurnMessage[],
			draft: FailureDraft,
			lease: DraftLease
		) => {
			const settled = settleTurnFailure( error, before, draft );
			// A newly accepted next question is a different editor from this turn.
			draftContext.checkpoint();
			if ( 'resource' === settled.action ) {
				const returned = returnToEditing( {
					text: settled.field,
					uploads: draft.uploads,
					missing: draft.omitted,
				} );
				setThread( before );
				if ( returned ) {
					placeChips( draft.uploads );
					setPrompt( settled.field );
					setRefused( settled.reason );
				}
				setPhase( 'ask' );
				return;
			}
			if ( 'refusal' === settled.action ) {
				const returned = returnToEditing( {
					text: settled.field,
					uploads: [],
					missing: [],
				} );
				if ( returned ) {
					placeChips( [] );
				}
				setThread( before );
				if ( returned ) {
					setPrompt( settled.field );
				}
				setRefused( refusalText( refusalReason( settled.reason ) ) );
				setPhase( 'ask' );
				return;
			}
			if ( 'conflict' === settled.action ) {
				const stored = await session.reload();
				if ( ! ( await draftContext.settle( lease ) ) ) {
					return;
				}
				setThread( stored.messages );
				setTurn( stored.turn );
				setContacts( stored.contacts ?? [] );
				setInquiries( stored.inquiries ?? [] );
				turnAt.current = stored.turn ? stored.messages.length - 1 : -1;
				draftContext.checkpoint();
				if (
					returnToEditing( {
						text: settled.field,
						uploads: draft.uploads,
						missing: draft.omitted,
					} )
				) {
					setPrompt( settled.field );
					placeChips( draft.uploads );
				}
				setConflict( turnConflictText() );
				setPhase( 'ask' );
				return;
			}
			commitFailure( { type: settled.kind } );
			if ( draftContext.editor ) {
				parkFailure();
				setPhase( 'ask' );
				return;
			}
			const draftNow = failureState.current.draft ?? draft;
			const view = presentFailure(
				settled.kind,
				before,
				retryMessages( before, draftNow.question ),
				draftNow
			);
			setThread( view.messages as TurnMessage[] );
			setPrompt( view.field );
			placeChips( view.chips );
			setPhase( 'error' );
		},
		[
			commitFailure,
			session,
			setPrompt,
			placeChips,
			draftContext,
			returnToEditing,
			parkFailure,
			failureState,
		]
	);

	const retainUnverifiedTurn = useCallback(
		(
			lease: DraftLease,
			draft: FailureDraft,
			kind: 'upstream' | 'truncated' = 'upstream'
		) => {
			if ( ! draftContext.owns( lease ) ) {
				return;
			}
			commitFailure( { type: kind } );
			if ( draftContext.editor ) {
				parkFailure();
				setPhase( 'ask' );
				return;
			}
			setPrompt( draft.text );
			setPhase( 'error' );
		},
		[ draftContext, commitFailure, setPrompt, parkFailure ]
	);

	const send = useCallback(
		async ( text: string ) => {
			const lease = draftContext.capture();
			if ( ! lease ) {
				return;
			}
			const picked = filesRef.current.uploads;
			const question = buildQuestion( text, picked );
			if (
				! question ||
				recoveryPending.current ||
				sending.current ||
				filesRef.current.busy ||
				omittedRef.current.length > 0
			) {
				return;
			}
			const draft: FailureDraft = {
				text,
				question,
				uploads: picked,
				omitted: [],
				...( entryOwnerScope.current
					? {
							entryId: newEntryId(),
							entryScope: entryOwnerScope.current,
						}
					: {} ),
			};
			const pending = commitFailure( { type: 'send', draft } );
			if (
				pending.phase !== 'pending' ||
				pending.draft?.question !== question
			) {
				return;
			}
			sending.current = true;
			setRefused( '' );
			setConflict( '' );
			setLive( '' );
			setPhase( 'waiting' );
			setPrompt( '' );
			setThread( [
				...session.messages,
				{ role: 'user', content: question },
			] );
			try {
				// session.ask re-reads the shared thread before it sends, so
				// a dock turn is neither lost nor overwritten (session.ts).
				const result = await session.ask(
					question,
					picked,
					lease.scope,
					{
						authorize: () => draftContext.authorize( lease ),
						settle: () => draftContext.settle( lease ),
					}
				);
				if ( ! ( await draftContext.settle( lease ) ) ) {
					retainUnverifiedTurn( lease, draft );
					return;
				}
				if ( ! draftContext.editor ) {
					filesRef.current.clear();
				}
				draftContext.checkpoint();
				commitFailure( { type: 'answered' } );
				setThread( result.messages );
				setTurn( result.answer );
				setContacts( result.contacts ?? [] );
				setInquiries( result.inquiries ?? [] );
				turnAt.current = result.messages.length - 1;
				setLive( assistantMessage( result.answer ).content );
				setPhase( 'ask' );
			} catch ( error ) {
				if ( ! ( await draftContext.settle( lease ) ) ) {
					retainUnverifiedTurn( lease, draft );
					return;
				}
				if ( error instanceof EntryScopeError && error.changed ) {
					void draftContext.verify().catch( () => undefined );
					setPrompt( '' );
					placeChips( [] );
					setPhase( 'ask' );
					setRefused( __( 'Genie could not load.', 'linker-tools' ) );
					return;
				}
				// ask() commits the thread only after the proxy answered, so
				// session.messages is the thread this question was not added to.
				await handleTurnError( error, session.messages, draft, lease );
			} finally {
				if ( draftContext.owns( lease ) ) {
					sending.current = false;
				}
			}
		},
		[
			session,
			setPrompt,
			commitFailure,
			handleTurnError,
			placeChips,
			draftContext,
			retainUnverifiedTurn,
		]
	);
	sendRef.current = send;

	// One resend. The machine leaves `failed` before the request, so a
	// second click does not send.
	const retry = useCallback( async () => {
		const lease = draftContext.capture();
		if ( ! lease || sending.current || recoveryPending.current ) {
			return;
		}
		const opened = openRetry( session.messages );
		if ( ! opened ) {
			return;
		}
		const { draft, kind } = opened;
		sending.current = true;
		setRefused( '' );
		setConflict( '' );
		setLive( '' );
		setPhase( 'waiting' );
		setPrompt( '' );
		let payload: { question: string; uploads: Upload[] } | null = null;
		try {
			payload = payloadOrRestore( draft, kind, session.messages );
			if ( ! payload ) {
				setPhase( 'error' );
				setPrompt( 'upstream' === kind ? draft.text : '' );
				return;
			}
			const result = await session.retry(
				payload.question,
				payload.uploads,
				lease.scope,
				{
					authorize: () => draftContext.authorize( lease ),
					settle: () => draftContext.settle( lease ),
				}
			);
			if ( ! ( await draftContext.settle( lease ) ) ) {
				retainUnverifiedTurn( lease, draft );
				return;
			}
			if ( ! draftContext.editor ) {
				filesRef.current.clear();
			}
			draftContext.checkpoint();
			commitFailure( { type: 'answered' } );
			setThread( result.messages );
			setTurn( result.answer );
			setContacts( result.contacts ?? [] );
			setInquiries( result.inquiries ?? [] );
			turnAt.current = result.messages.length - 1;
			setLive( assistantMessage( result.answer ).content );
			setPhase( 'ask' );
		} catch ( error ) {
			if ( ! ( await draftContext.settle( lease ) ) ) {
				retainUnverifiedTurn( lease, draft );
				return;
			}
			if ( error instanceof EntryScopeError && error.changed ) {
				void draftContext.verify().catch( () => undefined );
				setPrompt( '' );
				placeChips( [] );
				setPhase( 'ask' );
				setRefused( __( 'Genie could not load.', 'linker-tools' ) );
				return;
			}
			await handleTurnError(
				error,
				session.messages,
				{
					...draft,
					question: payload?.question ?? draft.question,
					uploads: payload?.uploads ?? draft.uploads,
				},
				lease
			);
		} finally {
			if ( draftContext.owns( lease ) ) {
				sending.current = false;
			}
		}
	}, [
		session,
		setPrompt,
		commitFailure,
		handleTurnError,
		openRetry,
		payloadOrRestore,
		placeChips,
		draftContext,
		retainUnverifiedTurn,
	] );

	const updateMissing = useCallback(
		( names: string[] ) => {
			if ( ! draftContext.capture() ) {
				return;
			}
			if (
				entryOwnerScope.current &&
				! updateEntryRecovery(
					entryOwnerScope.current,
					( record ) => ( {
						...record,
						composer: {
							text: readPrompt().text,
							missing: [
								...names,
								...files.uploads.map( ( file ) => file.name ),
							],
						},
					} )
				)
			) {
				return;
			}
			setOmitted( names );
			if ( draftContext.editor ) {
				preserveEditor( {
					text: readPrompt().text,
					uploads: files.uploads,
					missing: names,
				} );
			}
		},
		[ draftContext, files.uploads, preserveEditor, readPrompt, setOmitted ]
	);
	useEffect( () => {
		const ready = new Set( files.uploads.map( ( file ) => file.name ) );
		const names = omittedRef.current.filter(
			( name ) => ! ready.has( name )
		);
		if ( names.length !== omittedRef.current.length ) {
			updateMissing( names );
		}
	}, [ files.uploads, updateMissing ] );

	// Files were picked for the hero: once they are prepared, send them as
	// the turn's question (a photo or a document is itself the question).
	useEffect( () => {
		if ( ! pendingSend || files.busy ) {
			return;
		}
		setPendingSend( null );
		if ( files.uploads.length > 0 ) {
			void sendRef.current( pendingSend.text );
		}
	}, [ pendingSend, files ] );

	const bridgeAsk = useCallback(
		( text: string, picked?: ArrayLike< File > ) => {
			if ( picked && picked.length > 0 ) {
				if ( ! draftContext.acceptEditor() ) {
					return;
				}
				setPendingSend( { text } );
				filesRef.current.add( picked );
				return;
			}
			void sendRef.current( text );
		},
		[ draftContext ]
	);

	// One ask and one "type the model" for every card in the hero — the same
	// action whether the card is an attachment, a parts block or a product, so
	// the surfaces cannot drift apart (the dock's typeModel does the same).
	const askCard = useCallback(
		( message: string ) => bridgeAsk( message ),
		[ bridgeAsk ]
	);
	const typeModelCard = useCallback( () => {
		if ( ! draftContext.acceptEditor() ) {
			return;
		}
		setPrompt( typeModelPrompt() );
		focusPrompt();
	}, [ setPrompt, focusPrompt, draftContext ] );

	useEffect( () => {
		if ( draftContext.phase === 'ready' && hydrated ) {
			onReady( { ask: bridgeAsk, mode: setRetainedMode } );
		}
	}, [ onReady, bridgeAsk, draftContext, draftContext.phase, hydrated ] );

	const blocks: Block[] = turn?.blocks ?? [];
	const cardIds = idsOf( blocks, 'cards' );
	const compareIds = idsOf( blocks, 'compare' );
	const cardPrices = pricesOf( blocks );
	const hasCompare = blocks.some( ( block ) => 'compare' === block.type );
	const hasCards = blocks.some( ( block ) => 'cards' === block.type );
	const offersInquiry = blocks.some(
		( block ) => 'action' === block.type && 'send_inquiry' === block.name
	);
	const currentInquiry = inquiries.find(
		( card ) => card.after === turnAt.current
	);
	const contactBlock = blocks.find(
		( block ): block is ContactBlock =>
			'contact' === block.type &&
			! contacts.some( ( card ) => card.after === turnAt.current )
	);
	// The inquiry card, or the record once it was sent (review round 1, P0).
	const inquiryAfterAnswer = currentInquiry ? (
		<InquirySent inquiry={ currentInquiry } />
	) : (
		<InquiryCard
			inquiryUrl={ config.inquiryUrl }
			nonce={ config.restNonce }
			locale={ locale }
			page={ config.page }
			onSent={ inquirySent }
		/>
	);

	return (
		<div className="linker-genie-hero__surface" lang={ locale }>
			<header className="linker-genie-hero__bar">
				<p className="linker-genie-hero__title">
					{ __( "Genie - Linker's AI assistant", 'linker-tools' ) }
				</p>
				<div className="linker-genie-hero__actions">
					<button
						type="button"
						className="linker-genie-hero__continue"
						onClick={ onContinue }
					>
						{ __( 'Continue in the side panel', 'linker-tools' ) }
					</button>
					<button
						ref={ closeRef }
						type="button"
						className="linker-genie-hero__close"
						aria-label={ __( 'Close', 'linker-tools' ) }
						onClick={ onClose }
					>
						<span aria-hidden="true">&times;</span>
					</button>
				</div>
			</header>
			<p className="linker-genie-hero__intro">
				<strong>
					{ __( "Genie is Linker's AI assistant.", 'linker-tools' ) }
				</strong>{ ' ' }
				{ __(
					'Answers come from our product data and documents, and can still be wrong.',
					'linker-tools'
				) }
			</p>
			<p className="screen-reader-text" role="status" aria-live="polite">
				{ draftContext.phase === 'ready' ? live : '' }
			</p>
			{ thread.length > 0 && draftContext.phase === 'ready' ? (
				<Transcript
					followKey={
						'waiting' === phase
							? thread.filter(
									( message ) => message.role === 'user'
								).length
							: 0
					}
				>
					<ol className="linker-genie-app__thread">
						{ thread.map( ( message, index ) => (
							<li
								key={ `${ index }:${ message.role }:${ message.turnId ?? message.content }` }
								className={ `linker-genie-app__message linker-genie-app__message--${ message.role }` }
							>
								{ 'assistant' === message.role ? (
									<div className="linker-genie-app__answer-brand">
										<span
											className="linker-genie-app__monogram"
											aria-hidden="true"
										>
											G
										</span>
										<span>
											{ __( 'Genie', 'linker-tools' ) }
										</span>
									</div>
								) : null }
								{ 'assistant' === message.role ? (
									<Reply
										text={ message.content }
										locale={ locale }
									/>
								) : (
									message.content
								) }
								{ 'assistant' === message.role
									? contacts
											.filter(
												( card ) => card.after === index
											)
											.slice( 0, 1 )
											.map( ( card ) => (
												<ContactSent
													key={ card.email }
													email={ card.email }
													receipt={
														false !== card.receipt
													}
												/>
											) )
									: null }
								{ 'assistant' === message.role
									? inquiries
											.filter(
												( card ) =>
													card.after === index &&
													card.after !==
														turnAt.current
											)
											.slice( 0, 1 )
											.map( ( card ) => (
												<InquirySent
													key={ card.order }
													inquiry={ card }
												/>
											) )
									: null }
							</li>
						) ) }
						{ 'waiting' === phase ? (
							<li className="linker-genie-app__message linker-genie-app__message--assistant linker-genie-wait">
								<div
									role="status"
									className="linker-genie-wait__status"
								>
									<span
										className="linker-genie-wait__dot"
										aria-hidden="true"
									/>
									{ __(
										'Genie is thinking…',
										'linker-tools'
									) }
								</div>
							</li>
						) : null }
					</ol>
					{ conflict ? (
						<p role="alert" className="linker-genie-app__error">
							{ conflict }
						</p>
					) : null }
					{ 'waiting' !== phase
						? turn?.attachments?.map( ( card ) => (
								<AttachmentCard
									key={ card.id }
									card={ card }
									onAsk={ askCard }
									onTypeModel={ typeModelCard }
									onPhoto={ () => requestPicker() }
								/>
							) )
						: null }
					{ blocks
						.filter(
							( block ) =>
								'text' !== block.type &&
								'contact' !== block.type
						)
						.map( ( block, index ) => (
							<BlockView
								key={ index }
								block={ block }
								accountUrl={ config.accountUrl }
								onAsk={ askCard }
								parts={ {
									onAsk: askCard,
									onAdd: addPartsToDraft,
									onTypeModel: typeModelCard,
								} }
							/>
						) ) }
					{ hasCards ? (
						<div className="linker-genie-hero__cards">
							{ cardIds.map( ( productId ) => (
								<GenieCard
									key={ productId }
									productId={ productId }
									restUrl={ config.restUrl }
									store={ store }
									locale={ locale }
									status={ statusFor( productId ) }
									price={ cardPrices.find(
										( line ) =>
											line.product_id === productId
									) }
									onAdd={ addCardToDraft }
									onSave={ saveCardSolution }
								/>
							) ) }
						</div>
					) : null }
					{ hasCompare ? (
						<Compare
							products={ compareIds }
							store={ store }
							locale={ locale }
						/>
					) : null }
					{ 'waiting' !== phase && contactBlock ? (
						<ContactCard
							key={ `${ turn?.meta?.turn_id ?? 0 }-contact` }
							block={ contactBlock }
							contactUrl={ config.contactUrl }
							nonce={ config.restNonce }
							locale={ locale }
							page={ config.page }
							onSent={ sent }
						/>
					) : null }
					{ 'waiting' !== phase && offersInquiry
						? inquiryAfterAnswer
						: null }
				</Transcript>
			) : null }
			<OwnedRecovery
				candidate={
					draftContext.phase === 'ready' ? deferredFailure : null
				}
				restore={ () => {
					void restoreOwnedFailure();
				} }
				busy={ phase === 'waiting' || files.busy }
			/>
			<AttachmentChips
				picked={ draftContext.phase === 'ready' ? files.picked : [] }
				onRemove={ files.remove }
			/>
			{ refused && draftContext.phase === 'ready' ? (
				<p role="alert" className="linker-genie-app__refused">
					{ refused }
					{ config.requestPageUrl ? (
						<>
							{ ' ' }
							<a
								href={ config.requestPageUrl }
								onClick={ () => {
									// The hero field lives outside React. Read its
									// current bytes with its accepted editor.
									const owner = draftContext.editor;
									const prompt = readPrompt();
									if (
										owner &&
										draftContext.editor === owner &&
										draftContext.capture()?.scope ===
											owner.scope
									) {
										rememberInquiry(
											config.requestPageUrl!,
											prompt.text,
											owner.scope
										);
									}
								} }
							>
								{ __( 'Send an inquiry', 'linker-tools' ) }
							</a>
						</>
					) : null }
				</p>
			) : null }
			{ unsaved ||
			( draftContext.identity?.persistent === false &&
				( readPrompt().text || files.picked.length > 0 ) ) ? (
				<p className="linker-genie-app__refused" role="status">
					{ __(
						'This question could not be saved. It may be lost if you refresh or leave this page.',
						'linker-tools'
					) }
				</p>
			) : null }
			{ retainedMode && draftContext.phase === 'ready' ? (
				<section className="linker-genie-app__photo-prompt">
					<button
						type="button"
						className="linker-genie-app__prompt"
						onClick={
							retainedMode === 'voice'
								? requestVoice
								: requestPicker
						}
					>
						{ retainedMode === 'voice'
							? __( 'Dictate', 'linker-tools' )
							: __( 'Choose a file', 'linker-tools' ) }
					</button>
				</section>
			) : null }
			{ draftContext.phase !== 'ready' || recoveryBlocked ? (
				<div className="linker-genie-app__error" role="alert">
					<p>
						{ draftContext.phase === 'loading'
							? __( 'Opening Genie…', 'linker-tools' )
							: __( 'Genie could not load.', 'linker-tools' ) }
					</p>
					<button
						type="button"
						className="linker-genie-app__prompt"
						onClick={ () => {
							void draftContext
								.verify()
								.then( () =>
									setRecoveryAttempt(
										( attempt ) => attempt + 1
									)
								)
								.catch( () => undefined );
						} }
					>
						{ __( 'Try again', 'linker-tools' ) }
					</button>
				</div>
			) : null }
			{ phase === 'ask' && draftContext.phase === 'ready' ? (
				<MissingFiles
					names={ omitted }
					remove={ ( name ) =>
						updateMissing(
							omitted.filter( ( item ) => item !== name )
						)
					}
					choose={ requestPicker }
				/>
			) : null }

			{ 'error' === phase && draftContext.phase === 'ready' ? (
				<>
					<p role="alert" className="linker-genie-app__error">
						{ failureText() }
						{ omitted.length > 0
							? ` ${ omittedFileNotice( omitted ) }`
							: '' }
					</p>
					<button
						type="button"
						className="linker-genie-app__prompt"
						onClick={ () => void retry() }
					>
						{ __( 'Try again', 'linker-tools' ) }
					</button>
				</>
			) : null }
		</div>
	);
}
