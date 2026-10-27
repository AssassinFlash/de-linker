/**
 * The Genie panel: one thread, the blocks of the current turn, and the
 * actions the customer can run on a card (docs/specs/13-genie.md). The pieces
 * live in ./components/, the API clients in ./api/.
 */

/**
 * WordPress dependencies
 */
import { useCallback, useEffect, useRef, useState } from '@wordpress/element';
import { __, _n, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { storeClient } from '../configurator/api/store';
import { rememberInquiry } from '../protection/inquiryHandoff';
import type { GenieConfig } from './config';
import { idsOf, pricesOf, proofsOf } from './shared/blocks';
import { useCardActions } from './shared/cardActions';
import { buildQuestion, typeModelPrompt } from './shared/conversation';
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
	type FailureOwner,
} from './shared/failure';
import { useFailure } from './shared/useFailure';
import type { DraftLease } from './shared/draftContext';
import type { NativeScope } from './shared/nativeScope';
import type { FailureCursor } from './shared/ownedFailure';
import { useDraftContext } from './shared/useDraftContext';
import {
	completedRequest,
	type RequestWitness,
} from './shared/completedRequest';
import { startDictation, type DictationSession } from './shared/dictation';
import {
	assistantMessage,
	deleteConversation,
	emailConversation,
	listConversations,
	readThread,
	selectConversation,
	sendTurn,
	turnConflictText,
	type ContactBlock,
	type ConversationSummary,
	type SentContact,
	type SentInquiryCard,
	type EmailOutcome,
	type PageContext,
	type Turn,
	type TurnMessage,
} from './api/turn';
import { ACCEPT } from './attachments/prepare';
import { useAttachments } from './attachments/useAttachments';
import { AttachmentCard } from './components/AttachmentCard';
import { AttachmentChips, refusalText } from './components/AttachmentChips';
import { BlockView } from './components/BlockView';
import { Compare } from './components/Compare';
import { InquiryCard, InquirySent } from './components/InquiryCard';
import type { SentInquiry } from './api/inquiry';
import { CopyReply } from './components/CopyReply';
import { ContactCard, ContactSent } from './components/ContactCard';
import { GenieCard } from './components/GenieCard';
import { HelperFooter } from './components/HelperFooter';
import { Reply } from './components/Reply';
import { Transcript } from './components/Transcript';
import {
	AttachIcon,
	BackIcon,
	CloseIcon,
	ExpandIcon,
	HistoryIcon,
	MicIcon,
	NewConversationIcon,
	PanelIcon,
	PlusIcon,
	SendIcon,
	TrashIcon,
} from './components/Icons';
import {
	EmailConversation,
	LinkResult,
	readLinkResult,
} from './components/EmailConversation';
import { VoteButtons } from './components/VoteButtons';
import { verifiedEntryFailure } from './shared/entryFailure';
import { newEntryId } from './shared/entryDraft';
import { useEntryInbox } from './shared/useEntryInbox';
import { useHelperDialog } from './shared/useHelperDialog';
import { useComposerSize } from './shared/useComposerSize';
import { MissingFiles } from './components/MissingFiles';
import { OwnedRecovery } from './components/OwnedRecovery';
import { EntryInbox } from './components/EntryInbox';
import './genie.css';

/** Test seam: the dictation test stubs the constructor (shared/dictation.ts). */
export type { Dictation } from './shared/dictation';

type Phase = 'ask' | 'waiting' | 'error';
type HistoryPhase = 'loading' | 'ready' | 'failed';
/** Where "email this conversation" stands: closed, the guest's address form, on its way, or how it ended. */
type MailPhase = 'idle' | 'form' | 'sending' | EmailOutcome;

/**
 * Under this width the workspace rail is an overlay over the conversation
 * (the prototype's mobile rule, genie.css `@media (max-width: 767px)`), so
 * picking a conversation folds it; wider, it is docked and stays.
 */
const OVERLAY_WIDTH = 768;

/**
 * One lane for restore, switch and ask. It lives outside the component:
 * an enqueue closed over a render would chain the next click onto a tail
 * that render already replaced.
 */
let turnLane: Promise< void > = Promise.resolve();
/**
 * A switch bumps this before its POST. A list fetched for an earlier
 * conversation compares the value it captured and drops itself.
 */
let historyEpoch = 0;

function deferred< T >() {
	let resolve!: ( value: T ) => void;
	const promise = new Promise< T >( ( settle ) => {
		resolve = settle;
	} );
	return { promise, resolve };
}

function enqueue( job: () => Promise< void > ): Promise< void > {
	const queued = turnLane.then( job, job );
	turnLane = queued.then(
		() => undefined,
		() => undefined
	);
	return queued;
}

/** Test seam: a finished lane must not leak into the next mount. */
export function resetTurnLane(): void {
	turnLane = Promise.resolve();
	historyEpoch = 0;
}

/**
 * Root of the Genie app; every `data-linker-app="genie"` mount gets one.
 * @param root0
 * @param root0.config
 */
export function App( { config }: { config: GenieConfig } ) {
	const loadThread = useCallback(
		() =>
			readThread( config.threadUrl, config.restNonce, undefined, {
				restUrl: config.restUrl,
				locale: config.locale,
			} ),
		[ config.threadUrl, config.restNonce, config.restUrl, config.locale ]
	);
	const [ open, setOpen ] = useState( false );
	// The page context every turn carries (#234). The mount sets it, and the
	// design report's "Ask Genie" adds the saved solution's id (#496): it is
	// the solution the customer asked about, for the rest of this conversation.
	// The ref is the live value: an opener sets it and asks in the same tick,
	// before React has re-rendered, and the first turn must carry it too.
	const [ page, setPage ] = useState< PageContext >( config.page );
	const pageRef = useRef( config.page );
	const plannerNonce = useRef< string | undefined >( undefined );
	useEffect( () => {
		const receive = ( event: Event ) => {
			const detail = ( event as CustomEvent ).detail;
			const next = detail?.page;
			if ( detail === null ) {
				pageRef.current = config.page;
				plannerNonce.current = undefined;
				setPage( config.page );
			} else if (
				next &&
				typeof next.planning_project_id === 'string' &&
				/^[a-f0-9]{32}$/.test( next.planning_project_id ) &&
				Number.isSafeInteger( next.planning_revision ) &&
				next.planning_revision > 0
			) {
				pageRef.current = next;
				plannerNonce.current =
					typeof detail.plannerNonce === 'string'
						? detail.plannerNonce
						: undefined;
				setPage( next );
			}
		};
		window.addEventListener( 'linker-genie-planning-context', receive );
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-planning-context-request' )
		);
		return () =>
			window.removeEventListener(
				'linker-genie-planning-context',
				receive
			);
	}, [ config.page ] );
	const handOverSolution = useCallback( ( solution: number ) => {
		const next = { ...pageRef.current, solution_id: solution };
		pageRef.current = next;
		setPage( next );
	}, [] );
	const [ thread, setThread ] = useState< TurnMessage[] >( [] );
	const [ turn, setTurn ] = useState< Turn | null >( null );
	// The contact requests sent from this conversation, each after the answer
	// that showed its card (#243): the history keeps them.
	const [ contacts, setContacts ] = useState< SentContact[] >( [] );
	// The inquiries the confirmation card sent (#250), each after the answer
	// that showed the card, with the record's number and status.
	const [ inquiries, setInquiries ] = useState< SentInquiryCard[] >( [] );
	// Where the shown turn's answer stands in the thread: a sent card belongs
	// there, whatever is asked after it.
	const turnAt = useRef( -1 );
	const [ phase, setPhase ] = useState< Phase >( 'ask' );
	// The request still returns one complete answer. This index only opts the
	// newly received answer into a short local reveal; stored history is instant.
	const [ revealingAt, setRevealingAt ] = useState< number | null >( null );
	const finishReveal = useCallback( () => setRevealingAt( null ), [] );
	const [ input, setInput ] = useState( '' );
	const inputRef = useRef( input );
	inputRef.current = input;
	const entryOwnsComposer = useRef( false );
	const entryRecoveryBlocksSend = useRef< () => boolean >( () => false );
	const blockEntryRecovery = useRef< () => void >( () => undefined );
	const resolveEntryRecovery = useRef< () => void >( () => undefined );
	const verifiedEntryScope = useRef( '' );
	const resetEntryComposer = useRef< () => void >( () => undefined );
	const detachEntryInbox = useRef< () => void >( () => undefined );
	const authorizeEntry = useRef< ( scope?: string ) => Promise< boolean > >(
		async () => true
	);
	const missingEntryFiles = useRef( false );
	const [ voiceError, setVoiceError ] = useState( false );
	const [ history, setHistory ] = useState< ConversationSummary[] >( [] );
	const [ historyPhase, setHistoryPhase ] =
		useState< HistoryPhase >( 'loading' );
	const [ currentId, setCurrentId ] = useState( 0 );
	// The conversation was asked from the home hero (#232): the dock says so
	// above the transcript, until another conversation is opened.
	const [ fromHome, setFromHome ] = useState( false );
	// The rail rides open beside the workspace's column on a wide screen; under
	// 768px it is an overlay that would land on top of the conversation, so it
	// starts closed and the bar's toggle opens it — the prototype's own mobile
	// rule. Read from window.innerWidth rather than a media query, so a jsdom
	// render (1024) keeps the desktop start.
	const [ railOpen, setRailOpen ] = useState(
		config.surface === 'workspace' && window.innerWidth >= OVERLAY_WIDTH
	);
	// The dock's own history view (the live Advisor's `.lia-history`, opened
	// from the header's clock): it replaces the thread, and the header's
	// mark becomes the way back. The workspace keeps its rail instead.
	const [ dockHistory, setDockHistory ] = useState( false );
	useEffect( () => {
		if ( ! open || dockHistory ) {
			finishReveal();
		}
	}, [ open, dockHistory, revealingAt, finishReveal ] );
	// What the visitor attached for the next turn (#236): each file is
	// prepared as it is picked and rides apart from the messages; its name
	// rides in the question, so the thread says what was sent. What the
	// dictation heard lands in the field.
	const attachInput = useRef< HTMLInputElement >( null );
	const { field, ref: composerFieldRef } = useComposerSize(
		input,
		( open || config.surface === 'workspace' ) && ! dockHistory
	);
	const dictation = useRef< DictationSession | null >( null );
	const dictationOwner = useRef< {
		lease: DraftLease;
		owner: FailureOwner;
		identity: NativeScope;
		checkpoint: FailureCursor | null;
		queuedText: string | null;
		queuedInsertion: number;
		ended: boolean;
		pending: number;
	} | null >( null );
	const ownerCleanup = useRef< () => void >( () => undefined );
	const draftContext = useDraftContext( config, () =>
		ownerCleanup.current()
	);
	const files = useAttachments( draftContext );
	const filesRef = useRef( files );
	filesRef.current = files;
	// Why the last turn's files were refused by the proxy, if they were.
	const [ refused, setRefused ] = useState( '' );
	// The stored thread moved while Genie was answering (#373). The question
	// was not stored; it stays in the field.
	const [ conflict, setConflict ] = useState( '' );
	// Opened to send a nameplate photo (the preview card's suggestion): the
	// panel offers the picker, which only a click may open.
	const [ photoPrompt, setPhotoPrompt ] = useState( false );
	const [ filePrompt, setFilePrompt ] = useState( false );
	const [ voicePrompt, setVoicePrompt ] = useState( false );
	// Opened for a parts list (the preview card's suggestion, #251): the
	// picker is offered for a CSV, an Excel file or a photo of the list.
	const [ listPrompt, setListPrompt ] = useState( false );
	const [ dictating, setDictating ] = useState( false );

	const sending = useRef( false );
	const currentThread = useRef< TurnMessage[] >( [] );
	// Only this mounted app's actual send can witness a retry recovery. A
	// matching question in history, another conversation or a reload cannot.
	const requestWitness = useRef<
		( RequestWitness & { epoch: number } ) | null
	>( null );
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
	const stopDictation = useCallback(
		( cancel = true ) => {
			const voice = dictationOwner.current;
			dictationOwner.current = null;
			if ( cancel && voice?.checkpoint && voice.pending > 0 ) {
				// Only this token's exact checkpoint may remove its undisplayed words.
				// Already displayed text, files and reselection names stay editable.
				const canceled = preserveEditor(
					{
						text: inputRef.current,
						uploads: filesRef.current.uploads,
						missing: [
							...editingMissing.current,
							...filesRef.current.picked
								.filter( ( item ) => item.state !== 'ready' )
								.map( ( item ) => item.name ),
						],
					},
					{
						owner: voice.owner,
						identity: voice.identity,
						cursor: voice.checkpoint,
					}
				);
				if (
					canceled?.conflict &&
					draftContext.editor === voice.owner
				) {
					draftContext.releaseEditor();
				}
			}
			const session = dictation.current;
			dictation.current = null;
			session?.stop();
			setDictating( false );
		},
		[ preserveEditor, draftContext ]
	);

	ownerCleanup.current = () => {
		requestWitness.current = null;
		detachEntryInbox.current();
		detachFailure();
		setInput( '' );
		filesRef.current.clear();
		stopDictation( false );
		sending.current = false;
		setPhase( 'ask' );
		setRefused( '' );
		setConflict( '' );
		currentThread.current = [];
		setThread( [] );
		setTurn( null );
		setContacts( [] );
		setInquiries( [] );
		setHistory( [] );
		setCurrentId( 0 );
		setMail( 'idle' );
		setDictating( false );
		setVoiceError( false );
	};
	const editingMissing = useRef( omitted );
	editingMissing.current = omitted;
	useEffect(
		() =>
			draftContext.beforeLeave( () => {
				const pendingVoice = dictationOwner.current;
				if (
					pendingVoice &&
					draftContext.editor === pendingVoice.owner &&
					( pendingVoice.pending > 0 ||
						( ! pendingVoice.ended &&
							! inputRef.current &&
							! filesRef.current.uploads.length &&
							! filesRef.current.picked.length &&
							! editingMissing.current.length ) )
				) {
					// Native dictation has an accepted owner before its first transcript.
					// Revalidation of that empty snapshot is not an explicit clear.
					return;
				}
				preserveEditor( {
					text: inputRef.current,
					uploads: filesRef.current.uploads,
					missing: [
						...editingMissing.current,
						...filesRef.current.picked
							.filter( ( item ) => item.state !== 'ready' )
							.map( ( item ) => item.name ),
					],
				} );
			} ),
		[ draftContext, preserveEditor ]
	);
	useEffect(
		() =>
			draftContext.subscribe( () => {
				const voice = dictationOwner.current;
				if (
					voice &&
					( ! draftContext.owns( voice.lease ) ||
						draftContext.editor !== voice.owner )
				) {
					stopDictation( false );
				}
			} ),
		[ draftContext, stopDictation ]
	);

	// The conversation on screen, for the lane jobs: a delete that clears
	// it must empty the panel, and the state value is a render behind.
	const shownId = useRef( 0 );
	const [ mail, setMail ] = useState< MailPhase >( 'idle' );
	const [ mailTo, setMailTo ] = useState( '' );
	const [ mailLimit, setMailLimit ] = useState( 0 );
	// How a confirmation link this page was opened from ended, if it was.
	const [ linkResult ] = useState( readLinkResult );
	const show = useCallback( ( id: number ) => {
		shownId.current = id;
		setCurrentId( id );
	}, [] );

	const store = storeClient( config.restUrl, undefined, config.restNonce );
	const {
		statusFor: cardStatusFor,
		addToDraft: addCardToDraft,
		addPartsToDraft,
		saveCardSolution,
	} = useCardActions( {
		restUrl: config.restUrl,
		restNonce: config.restNonce,
		locale: config.locale,
		store,
	} );
	const workspace = config.surface === 'workspace';

	const refreshHistory = useCallback( () => {
		const epoch = historyEpoch;
		const lease = draftContext.capture();
		return enqueue( async () => {
			const listed = await listConversations(
				config.conversationsUrl,
				config.restNonce
			);
			// A switch owns the rail now. Applying this list would put the
			// conversation it left back as current.
			if (
				epoch !== historyEpoch ||
				! ( await draftContext.settle( lease ) )
			) {
				return;
			}
			if ( ! listed.ok ) {
				setHistoryPhase( 'failed' );
				return;
			}
			setHistoryPhase( 'ready' );
			setHistory( listed.conversations );
			if ( listed.currentId ) {
				show( listed.currentId );
			}
		} );
	}, [ config.conversationsUrl, config.restNonce, show, draftContext ] );

	// A request is with the team: its card stays after the shown turn's answer.
	const sent = useCallback( ( email: string, receipt: boolean ) => {
		const after = turnAt.current;
		setContacts( ( known ) =>
			known.some( ( card ) => card.after === after )
				? known
				: [ ...known, { after, email, receipt } ]
		);
	}, [] );

	// An inquiry is with the team: its card stays after the shown turn's answer.
	const inquirySent = useCallback( ( inquiry: SentInquiry ) => {
		const after = turnAt.current;
		setInquiries( ( known ) =>
			known.some( ( card ) => card.after === after )
				? known
				: [ ...known, { ...inquiry, after } ]
		);
	}, [] );

	// A reload, or the hero handing the thread over, shows a failed turn
	// again: the error, and for a 502 the question back in the field.
	const applyRecord = useCallback(
		async ( messages: TurnMessage[], resetField = false ) => {
			// A send that is already in flight owns the record. The mount's
			// read can resolve after that send started; reconciling it here
			// would show a failure for a turn that has not failed.
			const hasPendingOwner = () =>
				'pending' === failureState.current.phase;
			if ( hasPendingOwner() ) {
				return;
			}
			const lease = draftContext.capture();
			if ( ! lease ) {
				return;
			}
			const checked = await verifiedEntryFailure(
				config,
				pageFailureStore(),
				draftContext
			);
			if ( ! checked || ! checked.unchanged() || hasPendingOwner() ) {
				if ( ! checked ) {
					blockEntryRecovery.current();
				}
				return;
			}
			if (
				! draftContext.valid( lease ) ||
				checked.identity.scope !== lease?.scope
			) {
				return;
			}
			const record = checked.record;
			resolveEntryRecovery.current();
			if (
				checked.candidate &&
				record?.editing &&
				draftContext.editor?.attempt === record.owner?.attempt &&
				inputRef.current === record.text &&
				JSON.stringify( filesRef.current.uploads ) ===
					JSON.stringify( record.uploads ) &&
				JSON.stringify( editingMissing.current ) ===
					JSON.stringify( record.omitted )
			) {
				ignoreCurrentCandidate( checked.candidate );
				return;
			}
			const reconciled = reconcile( record, messages );
			const sameCurrent =
				failureState.current.draft?.owner?.attempt ===
					checked.candidate?.cursor.owner.attempt &&
				! draftContext.editor &&
				inputRef.current ===
					( reconciled.kind
						? composerFor( reconciled.kind, reconciled.draft! )
								.field
						: record?.text );
			const occupied =
				!! inputRef.current || filesRef.current.picked.length > 0;
			if (
				checked.candidate &&
				reconciled.phase !== 'clear' &&
				( ! record?.entryId || occupied ) &&
				! sameCurrent
			) {
				deferFailure( checked.candidate );
				setOpen( true );
				return;
			}
			const restored = adoptFailure( checked.candidate, reconciled );
			failureState.current = restored;
			if (
				'failed' === restored.phase &&
				restored.draft &&
				restored.kind
			) {
				const composer = composerFor( restored.kind, restored.draft );
				setInput( composer.field );
				placeChips( composer.chips );
				setOmitted( composer.omitted );
				setPhase( 'error' );
				setOpen( true );
				return;
			}
			setOmitted( [] );
			// A mount with no record must not wipe a question the visitor
			// already started typing. A refresh, or a record the server has
			// since answered, clears the field.
			if (
				( resetField || record ) &&
				! entryOwnsComposer.current &&
				! inputRef.current
			) {
				setPhase( 'ask' );
				setInput( '' );
			}
		},
		[
			placeChips,
			failureState,
			setOmitted,
			config,
			draftContext,
			adoptFailure,
			deferFailure,
			ignoreCurrentCandidate,
		]
	);

	const updateEditingMissing = useCallback(
		( names: string[] ) => {
			if ( ! draftContext.capture() ) {
				return;
			}
			setOmitted( names );
			if ( draftContext.editor ) {
				preserveEditor( {
					text: inputRef.current,
					uploads: filesRef.current.uploads,
					missing: names,
				} );
			}
		},
		[ draftContext, preserveEditor, setOmitted ]
	);
	useEffect( () => {
		if ( phase !== 'ask' ) {
			return;
		}
		const ready = new Set( files.uploads.map( ( file ) => file.name ) );
		const names = editingMissing.current.filter(
			( name ) => ! ready.has( name )
		);
		if ( names.length !== editingMissing.current.length ) {
			updateEditingMissing( names );
		}
	}, [ files.uploads, phase, updateEditingMissing ] );

	const restoreOwnedFailure = async () => {
		const candidate = deferredFailure;
		const lease = draftContext.capture();
		const before = inputRef.current;
		const picked = filesRef.current.picked;
		if (
			! candidate ||
			! lease ||
			sending.current ||
			filesRef.current.busy
		) {
			return;
		}
		if (
			! ( await draftContext.authorize( lease ) ) ||
			inputRef.current !== before ||
			filesRef.current.picked !== picked ||
			sending.current ||
			filesRef.current.busy
		) {
			return;
		}
		const displaced =
			before || filesRef.current.uploads.length || omitted.length
				? {
						phase: 'editing' as const,
						kind: null,
						draft: {
							...failureState.current.draft,
							editing: true,
							text: before,
							question:
								buildQuestion(
									before,
									filesRef.current.uploads
								) || omitted.join( '\n' ),
							uploads: filesRef.current.uploads,
							omitted,
						},
					}
				: null;
		const restored = exchangeFailure(
			candidate,
			displaced,
			currentThread.current
		);
		if ( ! restored?.draft ) {
			return;
		}
		resetEntryComposer.current();
		if ( restored.phase === 'editing' ) {
			setInput( restored.draft.text );
			placeChips( restored.draft.uploads );
			setOmitted( restored.draft.omitted );
			setPhase( 'ask' );
			return;
		}
		if ( ! restored.kind ) {
			return;
		}
		const composer = composerFor( restored.kind, restored.draft );
		setInput( composer.field );
		placeChips( composer.chips );
		setOmitted( composer.omitted );
		setPhase( 'error' );
	};

	const showStored = useCallback( async () => {
		await draftContext.verify();
		const lease = draftContext.capture();
		if ( ! lease ) {
			return;
		}
		setRevealingAt( null );
		const stored = await loadThread();
		if ( ! ( await draftContext.settle( lease ) ) ) {
			return;
		}
		currentThread.current = stored.messages;
		setThread( stored.messages );
		setTurn( stored.turn );
		turnAt.current = stored.turn ? stored.messages.length - 1 : -1;
		setContacts( stored.contacts ?? [] );
		setInquiries( stored.inquiries ?? [] );
		await applyRecord( stored.messages, true );
		setMail( 'idle' );
	}, [ loadThread, applyRecord, draftContext ] );

	const previousNativeScope = useRef< string | undefined >( undefined );
	useEffect( () => {
		const scope = draftContext.identity?.scope;
		if (
			scope &&
			previousNativeScope.current &&
			previousNativeScope.current !== scope
		) {
			void enqueue( showStored ).catch( () => undefined );
		}
		if ( scope ) {
			previousNativeScope.current = scope;
		}
	}, [ draftContext, draftContext.identity?.scope, showStored ] );

	const onTurnError = useCallback(
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
				currentThread.current = before;
				if ( returned ) {
					placeChips( draft.uploads );
					setInput( settled.field );
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
				currentThread.current = before;
				setThread( before );
				if ( returned ) {
					setInput( settled.field );
				}
				setRefused( refusalText( refusalReason( settled.reason ) ) );
				setPhase( 'ask' );
				return;
			}
			if ( 'conflict' === settled.action ) {
				const latest = await loadThread();
				if ( ! ( await draftContext.settle( lease ) ) ) {
					return;
				}
				const messages =
					latest.messages.length > 0 ? latest.messages : before;
				currentThread.current = messages;
				setThread( messages );
				setTurn( latest.turn );
				turnAt.current = latest.turn ? messages.length - 1 : -1;
				setContacts( latest.contacts ?? [] );
				setInquiries( latest.inquiries ?? [] );
				draftContext.checkpoint();
				if (
					returnToEditing( {
						text: settled.field,
						uploads: draft.uploads,
						missing: draft.omitted,
					} )
				) {
					setInput( settled.field );
					placeChips( draft.uploads );
				}
				setConflict( turnConflictText() );
				setPhase( 'ask' );
				void refreshHistory();
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
			currentThread.current = view.messages as TurnMessage[];
			setThread( currentThread.current );
			setInput( view.field );
			placeChips( view.chips );
			setPhase( 'error' );
			setOpen( true );
		},
		[
			commitFailure,
			loadThread,
			placeChips,
			refreshHistory,
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
			setInput( draft.text );
			setPhase( 'error' );
		},
		[ draftContext, commitFailure, parkFailure ]
	);

	const ask = useCallback(
		async ( text: string, entryId?: string, entryScope?: string ) => {
			const lease = draftContext.capture();
			if ( ! lease ) {
				return false;
			}
			const uploads = entryId ? [] : files.uploads;
			const question = buildQuestion( text, uploads, listPrompt );
			if (
				! question ||
				entryRecoveryBlocksSend.current() ||
				sending.current ||
				files.busy ||
				( ! entryId &&
					( missingEntryFiles.current ||
						( phase === 'ask' && omitted.length > 0 ) ) )
			) {
				return false;
			}
			const draft: FailureDraft = {
				text,
				question,
				uploads,
				omitted: [],
				...( entryId || entryOwnsComposer.current
					? {
							entryId: entryId ?? newEntryId(),
							entryScope:
								entryScope ?? verifiedEntryScope.current,
						}
					: {} ),
			};
			// Reserve synchronously before entering the shared lane.
			sending.current = true;
			// Before the request leaves: a reload while it is in flight can
			// still put the question back.
			const pending = commitFailure( { type: 'send', draft } );
			if (
				pending.phase !== 'pending' ||
				pending.draft?.question !== question
			) {
				sending.current = false;
				return false;
			}
			requestWitness.current = null;
			setOpen( true );
			setDockHistory( false );
			setPhase( 'waiting' );
			setRevealingAt( null );
			setInput( '' );
			setRefused( '' );
			setConflict( '' );
			setPhotoPrompt( false );
			setFilePrompt( false );
			setVoicePrompt( false );
			setListPrompt( false );
			return enqueue( async () => {
				// The synchronous reservation above covers time spent waiting
				// behind an existing restore/switch as well as the actual send.
				// The dock re-reads before every send, as the hero does. A
				// turn the other tab stored is the base; an empty read (the
				// route failed, and readThread swallows that) keeps the
				// thread already on screen.
				const stored = await loadThread();
				if ( ! ( await draftContext.settle( lease ) ) ) {
					retainUnverifiedTurn( lease, draft );
					if ( draftContext.owns( lease ) ) {
						sending.current = false;
					}
					return;
				}
				let before = currentThread.current;
				if ( stored.messages.length > 0 ) {
					before = stored.messages;
					currentThread.current = stored.messages;
					setThread( stored.messages );
					setTurn( stored.turn );
					turnAt.current = stored.turn
						? stored.messages.length - 1
						: -1;
					setContacts( stored.contacts ?? [] );
					setInquiries( stored.inquiries ?? [] );
				}
				try {
					if (
						! ( await draftContext.authorize( lease ) ) ||
						! ( await authorizeEntry.current(
							draft.entryScope
						) ) ||
						! draftContext.valid( lease )
					) {
						retainUnverifiedTurn( lease, draft );
						return;
					}
					const next: TurnMessage[] = [
						...before,
						{ role: 'user', content: question },
					];
					currentThread.current = next;
					setThread( next );
					const postedPage = pageRef.current;
					const pageWitness = JSON.stringify( postedPage );
					const answer = await sendTurn( {
						turnUrl: config.turnUrl,
						restUrl: config.restUrl,
						nonce: config.restNonce,
						locale: config.locale,
						messages: next,
						page: postedPage,
						plannerNonce: plannerNonce.current,
						uploads,
						onOperation: ( operationId ) => {
							if ( ! draftContext.owns( lease ) ) {
								return;
							}
							requestWitness.current = stored.conversationId
								? {
										conversationId: stored.conversationId,
										operationId,
										epoch: historyEpoch,
										messages: next,
										uploads,
										locale: config.locale,
										page: pageWitness,
									}
								: null;
						},
					} );
					if ( ! ( await draftContext.settle( lease ) ) ) {
						retainUnverifiedTurn( lease, draft );
						if ( draftContext.owns( lease ) ) {
							sending.current = false;
						}
						return;
					}
					if ( ! entryId && ! draftContext.editor ) {
						filesRef.current.clear();
					}
					draftContext.checkpoint();
					commitFailure( { type: 'answered' } );
					requestWitness.current = null;
					const assistant = assistantMessage( answer );
					currentThread.current = next.concat( assistant );
					setThread( currentThread.current );
					turnAt.current = currentThread.current.length - 1;
					setRevealingAt( turnAt.current );
					setTurn( answer );
					setPhase( 'ask' );
					// Enqueue, do not await: the refresh must follow this
					// turn, but holding the lane until it returns would
					// block a switch the visitor starts while it is in flight.
					void refreshHistory();
				} catch ( error ) {
					// A file the proxy refused (Attachments.php) is said as
					// such. A 409 means the other turn was stored and this
					// question was not: it goes back into the field, with
					// its files. A cut stream keeps the question in the
					// thread. A 502 puts it back in the field (#411).
					if ( await draftContext.settle( lease ) ) {
						await onTurnError( error, before, draft, lease );
					} else {
						retainUnverifiedTurn( lease, draft );
					}
				} finally {
					if ( draftContext.owns( lease ) ) {
						sending.current = false;
					}
				}
			} ).then( () => true );
		},
		[
			config,
			loadThread,
			refreshHistory,
			files,
			draftContext,
			listPrompt,
			phase,
			omitted.length,
			commitFailure,
			onTurnError,
			retainUnverifiedTurn,
		]
	);

	// One resend of the failed question. The machine leaves `failed` before
	// this returns, so a second click does not send.
	const retry = useCallback( () => {
		const lease = draftContext.capture();
		if ( ! lease || sending.current || entryRecoveryBlocksSend.current() ) {
			return;
		}
		const opened = openRetry( currentThread.current );
		if ( ! opened ) {
			return;
		}
		const { draft, kind } = opened;
		sending.current = true;
		setOpen( true );
		setDockHistory( false );
		setPhase( 'waiting' );
		setRevealingAt( null );
		setInput( '' );
		setRefused( '' );
		setConflict( '' );
		return enqueue( async () => {
			sending.current = true;
			let before = currentThread.current;
			let payload: ReturnType< typeof payloadOrRestore< TurnMessage > > =
				null;
			try {
				const stored = await loadThread();
				if (
					! ( await draftContext.authorize( lease ) ) ||
					! ( await authorizeEntry.current( draft.entryScope ) ) ||
					! draftContext.valid( lease )
				) {
					retainUnverifiedTurn( lease, draft, kind );
					return;
				}
				if ( stored.messages.length > 0 ) {
					before = stored.messages;
					currentThread.current = stored.messages;
					setTurn( stored.turn );
					turnAt.current = stored.turn
						? stored.messages.length - 1
						: -1;
					setContacts( stored.contacts ?? [] );
					setInquiries( stored.inquiries ?? [] );
				}
				payload = payloadOrRestore( draft, kind, before );
				if ( ! payload ) {
					setPhase( 'error' );
					setInput( 'upstream' === kind ? draft.text : '' );
					return;
				}
				const witness = requestWitness.current;
				if (
					witness &&
					witness.epoch === historyEpoch &&
					completedRequest(
						witness,
						stored,
						payload.question,
						payload.uploads,
						config.locale,
						pageRef.current
					)
				) {
					// readThread appends an assistant only after parseStream saw
					// done. Restore that result instead of paying for a new turn.
					currentThread.current = stored.messages;
					setThread( stored.messages );
					if ( ! draftContext.editor ) {
						filesRef.current.clear();
					}
					draftContext.checkpoint();
					commitFailure( { type: 'answered' } );
					requestWitness.current = null;
					setPhase( 'ask' );
					void refreshHistory();
					return;
				}
				const next = payload.messages;
				currentThread.current = next;
				setThread( next );
				requestWitness.current = null;
				const postedPage = pageRef.current;
				const pageWitness = JSON.stringify( postedPage );
				const answer = await sendTurn( {
					turnUrl: config.turnUrl,
					restUrl: config.restUrl,
					nonce: config.restNonce,
					locale: config.locale,
					messages: next,
					page: postedPage,
					plannerNonce: plannerNonce.current,
					uploads: payload.uploads,
					onOperation: ( operationId ) => {
						if ( ! draftContext.owns( lease ) ) {
							return;
						}
						requestWitness.current = stored.conversationId
							? {
									conversationId: stored.conversationId,
									operationId,
									epoch: historyEpoch,
									messages: next,
									uploads: payload!.uploads,
									locale: config.locale,
									page: pageWitness,
								}
							: null;
					},
				} );
				if ( ! ( await draftContext.settle( lease ) ) ) {
					retainUnverifiedTurn( lease, draft );
					if ( draftContext.owns( lease ) ) {
						sending.current = false;
					}
					return;
				}
				if ( ! draftContext.editor ) {
					filesRef.current.clear();
				}
				draftContext.checkpoint();
				commitFailure( { type: 'answered' } );
				requestWitness.current = null;
				const assistant = assistantMessage( answer );
				currentThread.current = next.concat( assistant );
				setThread( currentThread.current );
				turnAt.current = currentThread.current.length - 1;
				setRevealingAt( turnAt.current );
				setTurn( answer );
				setPhase( 'ask' );
				void refreshHistory();
			} catch ( error ) {
				if ( ! ( await draftContext.settle( lease ) ) ) {
					retainUnverifiedTurn( lease, draft );
					if ( draftContext.owns( lease ) ) {
						sending.current = false;
					}
					return;
				}
				await onTurnError(
					error,
					before,
					payload
						? {
								...draft,
								question: payload.question,
								uploads: payload.uploads,
							}
						: draft,
					lease
				);
			} finally {
				if ( draftContext.owns( lease ) ) {
					sending.current = false;
				}
			}
		} );
	}, [
		config,
		loadThread,
		refreshHistory,
		commitFailure,
		onTurnError,
		openRetry,
		payloadOrRestore,
		draftContext,
		retainUnverifiedTurn,
	] );

	// "Type the model": the way out of a nameplate the customer does not
	// confirm, or one that could not be read.
	const typeModel = useCallback( () => {
		// The model goes where the placeholder stands; the field opens with
		// the words before it, ready for the customer to type the name.
		if ( ! draftContext.acceptEditor() ) {
			return;
		}
		setInput( typeModelPrompt() );
		field.current?.focus();
	}, [ field, draftContext ] );

	// The conversation the browser already has comes back on mount: a reload,
	// or opening Genie on another page of the site, shows the thread instead
	// of an empty panel (docs/specs/13-genie.md).
	useEffect( () => {
		let cancelled = false;
		const pending = deferred< {
			messages: TurnMessage[];
			turn: Turn | null;
			contacts?: SentContact[];
			inquiries?: SentInquiryCard[];
		} >();
		void enqueue( async () => {
			await draftContext.initialized();
			if ( cancelled ) {
				return;
			}
			const lease = draftContext.capture();
			const stored = await Promise.race( [
				loadThread(),
				pending.promise,
			] );
			if ( cancelled || ! ( await draftContext.settle( lease ) ) ) {
				return;
			}
			if ( stored.messages.length > 0 ) {
				currentThread.current = stored.messages;
				setThread( stored.messages );
				setContacts( stored.contacts ?? [] );
				setInquiries( stored.inquiries ?? [] );
				if ( stored.turn ) {
					turnAt.current = stored.messages.length - 1;
					setTurn( stored.turn );
				}
			}
			await applyRecord( stored.messages );
		} )
			.then( () => {
				if ( ! cancelled ) {
					return refreshHistory();
				}
				return undefined;
			} )
			.catch( () => undefined );
		return () => {
			cancelled = true;
			// A superseded mount must not hold the lane. The replacement
			// reads the thread itself.
			pending.resolve( {
				messages: [],
				turn: null,
				contacts: [],
				inquiries: [],
			} );
		};
	}, [ loadThread, refreshHistory, applyRecord, draftContext ] );

	const continueConversation = useCallback(
		( id?: number ) => {
			// Before the job, not inside it: a list already queued behind
			// this switch captured the old epoch and must drop itself.
			historyEpoch += 1;
			stopDictation();
			draftContext.invalidate();
			setInput( '' );
			setOmitted( [] );
			filesRef.current.clear();
			// A switched-to conversation is not the one the hero began.
			setFromHome( false );
			const lease = draftContext.capture();
			return enqueue( async () => {
				try {
					const selected = await selectConversation(
						config.conversationsUrl,
						config.restNonce,
						id
					);
					if ( ! ( await draftContext.settle( lease ) ) ) {
						return;
					}
					// The failed turn belonged to the conversation just left.
					commitFailure( { type: 'abandon' } );
					setHistoryPhase( 'ready' );
					setHistory( selected.conversations );
					show( selected.currentId );
					// Docked, the rail stays where the visitor put it; as an
					// overlay it would hide the conversation just picked.
					if ( window.innerWidth < OVERLAY_WIDTH ) {
						setRailOpen( false );
					}
					setOpen( true );
					resetEntryComposer.current();
					await showStored();
				} catch {
					if ( ! draftContext.valid( lease ) ) {
						return;
					}
					setHistoryPhase( 'failed' );
					setOpen( true );
				}
			} );
		},
		[
			config.conversationsUrl,
			config.restNonce,
			showStored,
			show,
			commitFailure,
			draftContext,
			setOmitted,
			stopDictation,
		]
	);

	// Clearing a conversation (ticket #235): the server deletes it with its
	// thread and answers the list without it. When it was the one on screen,
	// the panel shows what is current now — another conversation, or none.
	const removeConversation = useCallback(
		( id: number ): Promise< boolean > => {
			historyEpoch += 1;
			if ( id === shownId.current ) {
				stopDictation();
				draftContext.invalidate();
				setInput( '' );
				setOmitted( [] );
				filesRef.current.clear();
			}
			// The hero's conversation may be the one being cleared; the
			// origin line follows the conversation, not the dock.
			setFromHome( false );
			const lease = draftContext.capture();
			let removed = false;
			return enqueue( async () => {
				const remaining = await deleteConversation(
					config.conversationsUrl,
					config.restNonce,
					id
				);
				removed = true;
				if ( ! ( await draftContext.settle( lease ) ) ) {
					return;
				}
				setHistoryPhase( 'ready' );
				setHistory( remaining.conversations );
				if ( id !== shownId.current ) {
					return;
				}
				commitFailure( { type: 'abandon' } );
				show( remaining.currentId );
				if ( remaining.currentId > 0 ) {
					await showStored();
					return;
				}
				currentThread.current = [];
				setThread( [] );
				setContacts( [] );
				setInquiries( [] );
				setTurn( null );
				setPhase( 'ask' );
				setMail( 'idle' );
			} ).then(
				() => removed,
				() => removed
			);
		},
		[
			config.conversationsUrl,
			config.restNonce,
			showStored,
			show,
			commitFailure,
			draftContext,
			setOmitted,
			stopDictation,
		]
	);

	// "Email this conversation": a signed-in customer's goes straight to the
	// account's address; a guest names one first.
	const sendByEmail = useCallback(
		async ( address?: string, website = '' ) => {
			setMail( 'sending' );
			const result = await emailConversation(
				config.conversationsUrl,
				config.restNonce,
				shownId.current,
				config.locale,
				address,
				address
					? {
							started: config.mailStarted,
							started_nonce: config.mailStartedNonce,
							website,
						}
					: undefined
			);
			setMailTo( result.to || address || '' );
			setMailLimit( result.limit );
			setMail( result.outcome );
		},
		[
			config.conversationsUrl,
			config.restNonce,
			config.locale,
			config.mailStarted,
			config.mailStartedNonce,
		]
	);

	// The browser's own dictation (the live Advisor's `.lia-voice` and the
	// ChatGPT composer's microphone). No vendor service: where the browser
	// has none, the button says so and stays. The recognition lives for the
	// mount; stopping it on unmount is what a second mount must not inherit.
	const dictate = useCallback( () => {
		if ( dictationOwner.current && ! dictationOwner.current.ended ) {
			stopDictation();
			return;
		}
		setVoiceError( false );
		let insertion = field.current?.selectionStart ?? input.length;
		const lease = draftContext.capture();
		if ( ! lease ) {
			return;
		}
		if ( dictationOwner.current ) {
			stopDictation();
		}
		const owner = draftContext.acceptEditor();
		if ( ! owner ) {
			return;
		}
		const voice = {
			lease,
			owner,
			identity: { ...draftContext.identity! },
			ended: false,
			pending: 0,
			checkpoint: null as FailureCursor | null,
			queuedText: null as string | null,
			queuedInsertion: insertion,
		};
		dictationOwner.current = voice;
		const session = startDictation(
			window,
			config.locale,
			( heard ) => {
				if (
					dictationOwner.current !== voice ||
					! draftContext.owns( lease ) ||
					draftContext.editor !== owner
				) {
					return;
				}
				voice.pending += 1;
				if ( ! draftContext.valid( lease ) ) {
					const text = voice.queuedText ?? inputRef.current;
					const at = Math.min(
						voice.queuedText === null
							? insertion
							: voice.queuedInsertion,
						text.length
					);
					const before = text.slice( 0, at );
					const after = text.slice( at );
					const added = `${ before && ! /\s$/.test( before ) ? ' ' : '' }${ heard }${ after && ! /^\s/.test( after ) ? ' ' : '' }`;
					voice.queuedText = before + added + after;
					voice.queuedInsertion = at + added.length;
					// Acceptance happened at voice start. This write grants no display
					// authority and never takes the principal returned by a later check.
					const saved = preserveEditor(
						{
							text: voice.queuedText,
							uploads: filesRef.current.uploads,
							missing: [
								...editingMissing.current,
								...filesRef.current.picked
									.filter(
										( item ) => item.state !== 'ready'
									)
									.map( ( item ) => item.name ),
							],
						},
						{
							owner,
							identity: voice.identity,
							cursor: voice.checkpoint ?? undefined,
						}
					);
					if ( saved?.conflict ) {
						// A newer accepted revision has superseded this token. Neither
						// its next phrase nor a later blank checkpoint may replace it.
						stopDictation( false );
						if ( draftContext.editor === owner ) {
							draftContext.releaseEditor();
						}
						return;
					}
					if ( saved ) {
						voice.checkpoint = saved.cursor;
					}
				}
				const deliver = ( permitted: boolean ) => {
					voice.pending -= 1;
					if (
						! permitted ||
						dictationOwner.current !== voice ||
						! draftContext.valid( lease ) ||
						draftContext.editor !== owner
					) {
						return;
					}
					// Checkpoints can run before React commits this accepted transcript.
					const text = inputRef.current;
					const at = Math.min( insertion, text.length );
					const before = text.slice( 0, at );
					const after = text.slice( at );
					const added = `${ before && ! /\s$/.test( before ) ? ' ' : '' }${ heard }${ after && ! /^\s/.test( after ) ? ' ' : '' }`;
					insertion = at + added.length;
					inputRef.current = before + added + after;
					setInput( inputRef.current );
					if ( voice.pending === 0 ) {
						voice.queuedText = null;
						voice.checkpoint = null;
					}
				};
				if ( draftContext.valid( lease ) ) {
					deliver( true );
				} else {
					void draftContext.whenVerified( lease ).then( deliver );
				}
			},
			() => {
				if ( dictationOwner.current !== voice ) {
					return;
				}
				// Natural end does not cancel words already awaiting native authority.
				voice.ended = true;
				dictation.current = null;
				if ( draftContext.owns( lease ) ) {
					setDictating( false );
				}
			},
			() => {
				if (
					dictationOwner.current === voice &&
					draftContext.valid( lease )
				) {
					setVoiceError( true );
				}
			}
		);
		if ( ! session || dictationOwner.current !== voice ) {
			if ( dictationOwner.current === voice ) {
				dictationOwner.current = null;
			}
			return;
		}
		dictation.current = voice.ended ? null : session;
		setDictating( ! voice.ended );
	}, [
		config.locale,
		input.length,
		field,
		draftContext,
		stopDictation,
		preserveEditor,
	] );

	useEffect( () => () => stopDictation( false ), [ stopDictation ] );

	const cardIds = idsOf( turn?.blocks ?? [], 'cards' );
	const cardPrices = pricesOf( turn?.blocks ?? [] );
	const cardProofs = proofsOf( turn?.blocks ?? [] );
	const compareIds = idsOf( turn?.blocks ?? [], 'compare' );

	const entryInbox = useEntryInbox( {
		context: draftContext,
		config,
		input,
		setInput,
		files,
		busy: phase === 'waiting',
		ask: ( text, entryId, entryScope ) => ask( text, entryId, entryScope ),
		onRecovery: showStored,
		onComposerClaim: () => {
			entryOwnsComposer.current = true;
		},
		onVerified: ( scope ) => {
			verifiedEntryScope.current = scope;
		},
		onInvalidated: ( scope ) => {
			const record = failureState.current.draft;
			if ( record?.entryScope === scope ) {
				commitFailure( { type: 'abandon' } );
			}
			setPhase( 'ask' );
		},
		onReplace: () => {
			commitFailure( { type: 'abandon' } );
			setPhase( 'ask' );
		},
		onMode: ( mode ) => {
			setPhotoPrompt( mode === 'nameplate' );
			setListPrompt( false );
			setFilePrompt( mode === 'attach' );
			setVoicePrompt( mode === 'voice' );
		},
	} );
	entryOwnsComposer.current = entryInbox.owned.current;
	blockEntryRecovery.current = entryInbox.blockRecovery;
	resolveEntryRecovery.current = entryInbox.resolveRecovery;
	entryRecoveryBlocksSend.current = () => entryInbox.recoveryPending.current;
	authorizeEntry.current = entryInbox.authorize;
	resetEntryComposer.current = entryInbox.resetComposer;
	detachEntryInbox.current = entryInbox.detach;
	missingEntryFiles.current = entryInbox.missing.length > 0;
	const receiveEntry = entryInbox.receive;
	useEffect( () => {
		if ( ! open ) {
			stopDictation();
		}
	}, [ open, stopDictation ] );

	const helperDialog = useHelperDialog( {
		open,
		workspace,
		close: () => {
			if ( dockHistory ) {
				setDockHistory( false );
				requestAnimationFrame( () =>
					field.current?.focus( { preventScroll: true } )
				);
			} else {
				draftContext.checkpoint();
				setOpen( false );
			}
		},
	} );
	const rememberOpener = helperDialog.remember;

	// All page entries go through the dock loader. Ready is emitted only after
	// this listener exists, so even a click while the bundle loads is delivered
	// exactly once. Plain open never creates an unsolicited model turn.
	useEffect( () => {
		function onOpen( event: Event ) {
			setOpen( true );
			setDockHistory( false );
			const detail = (
				event as CustomEvent< {
					entry?: unknown;
					opener?: unknown;
					message?: unknown;
					attach?: unknown;
					refresh?: unknown;
					fromHome?: unknown;
					list?: unknown;
					solution?: unknown;
				} >
			 ).detail;
			rememberOpener( detail?.opener );
			if (
				! open &&
				! detail?.entry &&
				! detail?.message &&
				! detail?.refresh
			) {
				void enqueue( showStored ).catch( () => undefined );
			}
			if ( detail?.entry ) {
				receiveEntry( detail.entry );
				return;
			}
			if (
				detail &&
				typeof detail.solution === 'number' &&
				detail.solution > 0
			) {
				// The design report's "Ask Genie" saved this solution (#496):
				// every later turn of this conversation carries it.
				handOverSolution( detail.solution );
			}
			if ( detail && true === detail.fromHome ) {
				setFromHome( true );
			}
			if ( detail && true === detail.refresh ) {
				// The home hero (#232) wrote the thread while the dock was
				// shut: read it before showing, then deliver any question.
				const message =
					typeof detail.message === 'string' ? detail.message : '';
				void enqueue( showStored )
					.then( () => {
						if ( message ) {
							void ask( message );
						}
					} )
					.catch( () => undefined );
				return;
			}
			if (
				detail &&
				typeof detail.message === 'string' &&
				detail.message
			) {
				setPhotoPrompt( false );
				setListPrompt( false );
				void ask( detail.message );
			} else if ( detail && true === detail.attach ) {
				// The photo suggestion (#236) or the parts-list one (#251): the
				// picker is offered, with the words for the file it expects.
				setPhotoPrompt( true !== detail.list );
				setListPrompt( true === detail.list );
			}
		}
		window.addEventListener( 'linker-genie-open', onOpen );
		return () => window.removeEventListener( 'linker-genie-open', onOpen );
	}, [
		ask,
		showStored,
		handOverSolution,
		receiveEntry,
		rememberOpener,
		open,
	] );

	useEffect( () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-state', { detail: { open } } )
		);
	}, [ open ] );

	useEffect( () => {
		window.dispatchEvent( new CustomEvent( 'linker-genie-ready' ) );
	}, [] );

	const historyView = ! workspace && dockHistory;
	// A conversation with an answer can be emailed; one still waiting for
	// its first answer has nothing to send yet.
	const canEmail =
		currentId > 0 &&
		'waiting' !== phase &&
		thread.some( ( message ) => 'assistant' === message.role );
	// Where a guest's conversations are kept, under the list; a signed-in
	// customer's are in the account and need no note.
	const historyNote =
		config.signedIn || config.retentionDays < 1
			? ''
			: sprintf(
					// translators: %d is the number of days a guest's conversation is kept from its start (Retention::RETENTION_DAYS).
					_n(
						'Each conversation stays in this browser for %d day from its start. Signing in moves all of them to your account.',
						'Each conversation stays in this browser for %d days from its start. Signing in moves all of them to your account.',
						config.retentionDays,
						'linker-tools'
					),
					config.retentionDays
				);
	const german = config.locale === 'de';
	// A browser without speech recognition gets no dead button.
	const canDictate = Boolean(
		window.SpeechRecognition ?? window.webkitSpeechRecognition
	);
	const visible = workspace || open;
	// The inquiry confirmation card's turn (#250): the action the model or the
	// service asked for, and the inquiry it may already have sent.
	const offersInquiry = Boolean(
		turn?.blocks.some(
			( block ) =>
				'action' === block.type && 'send_inquiry' === block.name
		)
	);
	const currentInquiry = inquiries.find(
		( card ) => card.after === turnAt.current
	);
	const inquiryAfterAnswer = currentInquiry ? (
		<InquirySent inquiry={ currentInquiry } />
	) : (
		<InquiryCard
			inquiryUrl={ config.inquiryUrl }
			nonce={ config.restNonce }
			locale={ config.locale }
			page={ page }
			onSent={ inquirySent }
		/>
	);
	// The rendered text and its accepted editor belong together. An old link
	// must not bind that text to a principal verified before React commits.
	const inquiryEditor = draftContext.editor;
	return (
		<section
			ref={ helperDialog.panel }
			tabIndex={ -1 }
			className={ `linker-genie-app${
				workspace ? ' linker-genie-app--workspace' : ''
			}` }
			lang={ config.locale }
			aria-label={ appName() }
		>
			{ /*
			 * The mobile sheet's backdrop (the OpenAI helper's): a tap
			 * off the card folds the dock away. First child, so the
			 * positioned main column paints above it.
			 */ }
			{ ! workspace && open ? (
				<button
					type="button"
					className="linker-genie-dock-mask"
					tabIndex={ -1 }
					aria-hidden="true"
					onClick={ () => {
						setDockHistory( false );
						draftContext.checkpoint();
						setOpen( false );
					} }
				>
					<span className="screen-reader-text">
						{ __( 'Hide', 'linker-tools' ) }
					</span>
				</button>
			) : null }
			{ /* The rail is the workspace's history; the dock's is the
			 * header's history view, so a helper mount carries no rail. */ }
			{ visible && workspace ? (
				<HistoryRail
					open={ railOpen }
					docked={ workspace }
					items={ draftContext.phase === 'ready' ? history : [] }
					currentId={ currentId }
					onOpen={ () => setRailOpen( true ) }
					onClose={ () => setRailOpen( false ) }
					phase={ historyPhase }
					onSelect={ ( id ) => void continueConversation( id ) }
					onNew={ () => void continueConversation() }
					onRetry={ () => void refreshHistory() }
					onDelete={ removeConversation }
					note={ historyNote }
				/>
			) : null }
			{ /*
			 * The rail's scrim, under 768px only, where the rail is an overlay
			 * (prototype `.gp-rail-mask`): the stylesheet shows it, so a wide
			 * screen carries it as display:none rather than not at all.
			 */ }
			{ visible && railOpen ? (
				<button
					type="button"
					className="linker-genie-rail-mask"
					onClick={ () => setRailOpen( false ) }
				>
					<span className="screen-reader-text">
						{ __( 'Close sidebar', 'linker-tools' ) }
					</span>
				</button>
			) : null }
			<div className="linker-genie-app__main">
				<header className="linker-genie-app__bar">
					<div className="linker-genie-app__bar-lead">
						{ /*
						 * The rail's own toggle rides in the rail, which the
						 * workspace can close. Closed, the rail is gone and
						 * the way back stands at the bar's leading edge, the
						 * chat app's own place for it (owner ruling
						 * 2026-10-13).
						 */ }
						{ workspace && ! railOpen ? (
							<button
								type="button"
								className="linker-genie-app__rail-toggle"
								aria-expanded={ railOpen }
								onClick={ () => setRailOpen( true ) }
							>
								<PanelIcon />
								<span className="screen-reader-text">
									{ __( 'Conversations', 'linker-tools' ) }
								</span>
							</button>
						) : null }
						<p className="linker-genie-app__title">{ appName() }</p>
					</div>
					{ ! workspace ? (
						<div className="linker-genie-app__bar-actions">
							{ open ? (
								/*
								 * The open dock's head is the live Advisor's
								 * `.lia-head-btns` row (new conversation, the full
								 * page, the history, closing) as icon buttons — the
								 * owner-approved reference of 2026-10-13
								 * (docs/research/2026-10-12-live-account-and-advisor/).
								 */
								<>
									<button
										type="button"
										className="linker-genie-app__icon"
										aria-label={ __(
											'New conversation',
											'linker-tools'
										) }
										onClick={ () => {
											setDockHistory( false );
											void continueConversation();
										} }
									>
										<PlusIcon />
									</button>
									{ config.workspaceUrl ? (
										<a
											className="linker-genie-app__icon"
											href={ config.workspaceUrl }
											aria-label={ __(
												'Open full page',
												'linker-tools'
											) }
										>
											<ExpandIcon />
										</a>
									) : null }
									<button
										type="button"
										className="linker-genie-app__icon"
										aria-label={
											dockHistory
												? __( 'Back', 'linker-tools' )
												: __(
														'Conversations',
														'linker-tools'
													)
										}
										aria-expanded={ dockHistory }
										onClick={ () =>
											setDockHistory( ! dockHistory )
										}
									>
										{ dockHistory ? (
											<BackIcon />
										) : (
											<HistoryIcon />
										) }
									</button>
									<button
										type="button"
										className="linker-genie-app__icon"
										aria-label={ __(
											'Close',
											'linker-tools'
										) }
										onClick={ () => {
											setDockHistory( false );
											draftContext.checkpoint();
											setOpen( false );
										} }
									>
										<CloseIcon />
									</button>
								</>
							) : (
								/*
								 * The closed bar is a fallback — in the page the
								 * loader hides the whole mount and the bubble opens
								 * the dock — and it is how a jsdom mount opens.
								 */
								<button
									type="button"
									className="linker-genie-app__toggle"
									aria-expanded={ open }
									onClick={ () => setOpen( true ) }
								>
									{ __( 'Open', 'linker-tools' ) }
								</button>
							) }
						</div>
					) : null }
				</header>
				{ visible ? (
					<div className="linker-genie-app__panel">
						{ linkResult ? (
							<LinkResult outcome={ linkResult } />
						) : null }
						{ /* The conversation began in the home hero (#232). */ }
						{ ! workspace && fromHome ? (
							<p className="linker-genie-app__origin">
								{ __(
									'Asked from the homepage',
									'linker-tools'
								) }
							</p>
						) : null }
						{ /*
						 * `.gp-welcome h1`: the empty column opens with its own
						 * line, the prototype's first child of the welcome. It
						 * is not a bar title — the column under the bar is the
						 * one it names. The dock's own welcome stands below.
						 */ }
						{ workspace && thread.length === 0 ? (
							<h1 className="linker-genie-app__welcome-title">
								{ __(
									'Where should we begin?',
									'linker-tools'
								) }
							</h1>
						) : null }
						{ /*
						 * The dock's history view is the live Advisor's
						 * `.lia-history`: the header's clock swaps the
						 * conversation for the list, the chevron swaps back.
						 */ }
						{ historyView && draftContext.phase === 'ready' ? (
							<div className="linker-genie-app__history">
								<HistoryList
									items={ history }
									currentId={ currentId }
									phase={ historyPhase }
									onSelect={ ( id ) => {
										setDockHistory( false );
										void continueConversation( id );
									} }
									onRetry={ () => void refreshHistory() }
									onDelete={ removeConversation }
									note={ historyNote }
								/>
							</div>
						) : null }
						{ /*
						 * The dock's opening state is the live Advisor's
						 * `.lia-welcome`: a centred greeting, one subline and
						 * the page's own example questions.
						 */ }
						{ ! workspace &&
						! historyView &&
						thread.length === 0 ? (
							<div className="linker-genie-app__welcome">
								<p className="linker-genie-app__welcome-greeting">
									{ __(
										'Get help with your solar project',
										'linker-tools'
									) }
								</p>
								<p className="linker-genie-app__welcome-sub">
									{ __(
										'Products, documents and your next step.',
										'linker-tools'
									) }
								</p>
								{ config.prompts.length > 0 ? (
									<div className="linker-genie-app__prompts">
										{ config.prompts.map( ( prompt ) => (
											<button
												key={ prompt }
												type="button"
												className="linker-genie-app__prompt"
												disabled={
													draftContext.phase !==
													'ready'
												}
												onClick={ () => ask( prompt ) }
											>
												{ prompt }
											</button>
										) ) }
									</div>
								) : null }
							</div>
						) : null }
						{ /*
						 * `.gp-messages`: the transcript is the frame's one
						 * scroll box and the composer stands outside it, so
						 * the input is in place however long the thread grows.
						 * The blocks and the cards travel inside it, the way a
						 * prototype message carries them. The dock's welcome and
						 * its history view stand in its place instead.
						 */ }
						{ ! historyView &&
						( workspace || thread.length > 0 ) &&
						draftContext.phase === 'ready' ? (
							<Transcript
								followKey={
									phase === 'waiting'
										? thread.filter(
												( message ) =>
													message.role === 'user'
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
											{ /* `.gp-answer-brand` — the answer's own
											 * label, over its text. The prototype's
											 * "Demo reply" tag is a demo affordance
											 * and is not carried. */ }
											{ 'assistant' === message.role ? (
												<div className="linker-genie-app__answer-brand">
													<span
														className="linker-genie-app__monogram"
														aria-hidden="true"
													>
														G
													</span>
													<span>
														{ __(
															'Genie',
															'linker-tools'
														) }
													</span>
												</div>
											) : null }
											{ 'assistant' === message.role ? (
												<Reply
													text={ message.content }
													locale={ config.locale }
													animate={
														index === revealingAt
													}
													onComplete={ finishReveal }
												/>
											) : (
												message.content
											) }
											{ 'assistant' === message.role ? (
												<div className="linker-genie-answer-actions">
													<CopyReply
														text={ message.content }
													/>
													<VoteButtons
														voteUrl={
															config.voteUrl
														}
														nonce={
															config.restNonce
														}
														turnId={
															message.turnId
														}
													/>
												</div>
											) : null }
											{ contacts
												.filter(
													( card ) =>
														card.after === index
												)
												.slice( 0, 1 )
												.map( ( card ) => (
													<ContactSent
														key={ card.email }
														email={ card.email }
														receipt={
															false !==
															card.receipt
														}
													/>
												) ) }
											{ /* An inquiry sent from an earlier
											 * turn: the card follows that
											 * answer (#250). The last turn's
											 * card stands at the end of the
											 * transcript, where it was sent. */ }
											{ inquiries
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
												) ) }
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
											<div
												className="linker-genie-wait__lines"
												aria-hidden="true"
											>
												<span />
												<span />
												<span />
											</div>
										</li>
									) : null }
								</ol>
								{ /* The turn's text already stands in the thread
								 * item above (assistantMessage carries the text
								 * blocks); rendering the blocks verbatim printed
								 * every answer twice, on the reference instance
								 * and in production alike (seen 2026-10-14).
								 * The blocks own what the thread item cannot
								 * carry: chips, cards, compare, handoff. */ }
								{ /* What Genie read from this turn's files
								 * (#236), with the nameplate's confirmation. */ }
								{ 'waiting' !== phase
									? turn?.attachments?.map( ( card ) => (
											<AttachmentCard
												key={ card.id }
												card={ card }
												onAsk={ ask }
												onTypeModel={ typeModel }
												onPhoto={ () =>
													draftContext.capture() &&
													attachInput.current?.click()
												}
											/>
										) )
									: null }
								{ turn?.blocks
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
											configuratorLinks={
												config.configuratorLinks
											}
											onAsk={ ask }
											parts={ {
												onAsk: ask,
												onAdd: addPartsToDraft,
												onTypeModel: typeModel,
											} }
										/>
									) ) }
								{ turn?.blocks.some(
									( block ) => 'cards' === block.type
								) ? (
									<div className="linker-genie-app__cards">
										{ cardIds.map( ( productId ) => (
											<GenieCard
												key={ productId }
												productId={ productId }
												restUrl={ config.restUrl }
												store={ store }
												locale={ config.locale }
												status={ cardStatusFor(
													productId
												) }
												price={ cardPrices.find(
													( line ) =>
														line.product_id ===
														productId
												) }
												onAdd={ ( id ) =>
													addCardToDraft(
														id,
														cardProofs[ id ]
													)
												}
												onSave={ ( id, title ) =>
													saveCardSolution(
														id,
														title,
														cardProofs[ id ]
													)
												}
											/>
										) ) }
									</div>
								) : null }
								{ turn?.blocks.some(
									( block ) => 'compare' === block.type
								) ? (
									<Compare
										products={ compareIds }
										store={ store }
										locale={ config.locale }
									/>
								) : null }
								{ canEmail ? (
									<EmailConversation
										phase={ mail }
										to={ mailTo }
										limit={ mailLimit }
										onStart={ () => {
											if ( config.signedIn ) {
												void sendByEmail();
												return;
											}
											setMail( 'form' );
										} }
										onCancel={ () => setMail( 'idle' ) }
										onSend={ ( address, website ) => {
											setMailTo( address );
											void sendByEmail(
												address,
												website
											);
										} }
									/>
								) : null }
								{ /* "Let Linker contact me" follows the
								 * answer and its cards (#243). */ }
								{ turn?.blocks
									.filter(
										( block ): block is ContactBlock =>
											'contact' === block.type &&
											! contacts.some(
												( card ) =>
													card.after ===
													turnAt.current
											)
									)
									.slice( 0, 1 )
									.map( ( block ) => (
										<ContactCard
											key={ `${ turn.meta?.turn_id ?? 0 }-${ block.reason }` }
											block={ block }
											contactUrl={ config.contactUrl }
											nonce={ config.restNonce }
											locale={ config.locale }
											page={ page }
											onSent={ sent }
										/>
									) ) }
								{ /* The inquiry confirmation card (#250) follows
								 * the answer too. Once the inquiry is with the
								 * team, the sent card stands here, where the
								 * customer sent it. */ }
								{ offersInquiry ? inquiryAfterAnswer : null }
							</Transcript>
						) : null }
						{ ! historyView ? (
							<>
								{ draftContext.phase !== 'ready' ? (
									<div
										className={
											draftContext.phase === 'loading'
												? 'linker-genie-app__status'
												: 'linker-genie-app__error'
										}
										role="status"
									>
										<p>
											{ draftContext.phase === 'loading'
												? __(
														'One moment…',
														'linker-tools'
													)
												: __(
														'Genie could not load.',
														'linker-tools'
													) }
										</p>
										{ draftContext.phase ===
										'unavailable' ? (
											<button
												type="button"
												className="linker-genie-app__prompt"
												onClick={ () => {
													void draftContext
														.verify()
														.then( async () => {
															await entryInbox.retryRecovery();
															await showStored();
														} )
														.catch(
															() => undefined
														);
												} }
											>
												{ __(
													'Try again',
													'linker-tools'
												) }
											</button>
										) : null }
									</div>
								) : null }
								{ unsaved ||
								( draftContext.identity?.persistent === false &&
									( input || files.picked.length > 0 ) ) ? (
									<p
										className="linker-genie-app__refused"
										role="status"
									>
										{ __(
											'This question could not be saved. It may be lost if you refresh or leave this page.',
											'linker-tools'
										) }
									</p>
								) : null }
								{ phase === 'ask' &&
								draftContext.phase === 'ready' ? (
									<MissingFiles
										names={ omitted }
										remove={ ( name ) =>
											updateEditingMissing(
												omitted.filter(
													( item ) => item !== name
												)
											)
										}
										choose={ () =>
											attachInput.current?.click()
										}
									/>
								) : null }
								<OwnedRecovery
									candidate={
										draftContext.phase === 'ready'
											? deferredFailure
											: null
									}
									restore={ () => {
										void restoreOwnedFailure();
									} }
									busy={ phase === 'waiting' || files.busy }
								/>
								{ draftContext.phase === 'ready' ? (
									<EntryInbox
										inbox={ entryInbox }
										busy={
											phase === 'waiting' || files.busy
										}
										composerOccupied={
											!! input ||
											files.picked.length > 0 ||
											entryInbox.missing.length > 0
										}
									/>
								) : null }
							</>
						) : null }
						{ ! historyView && voiceError ? (
							<p role="alert" className="linker-genie-app__error">
								{ __(
									'Dictation could not start. You can type your question.',
									'linker-tools'
								) }
							</p>
						) : null }
						{ ! historyView && voicePrompt ? (
							<div className="linker-genie-app__photo-prompt">
								{ ! canDictate ? (
									<p>
										{ __(
											'Dictation is not available in this browser. You can type your question.',
											'linker-tools'
										) }
									</p>
								) : null }
								{ canDictate ? (
									<button
										type="button"
										className="linker-genie-app__prompt"
										aria-pressed={ dictating }
										onClick={ dictate }
									>
										{ dictating
											? __(
													'Stop dictation',
													'linker-tools'
												)
											: __( 'Dictate', 'linker-tools' ) }
									</button>
								) : null }
							</div>
						) : null }
						{ /* The picked files, over the composer (#236). */ }
						{ ! historyView ? (
							<AttachmentChips
								picked={
									draftContext.phase === 'ready'
										? files.picked
										: []
								}
								onRemove={ files.remove }
							/>
						) : null }
						{ ! historyView && refused ? (
							<p
								role="alert"
								className="linker-genie-app__refused"
							>
								{ refused }
								{ config.requestPageUrl ? (
									<>
										{ ' ' }
										<a
											href={ config.requestPageUrl }
											onClick={ () => {
												if (
													inquiryEditor &&
													draftContext.editor ===
														inquiryEditor &&
													draftContext.capture()
														?.scope ===
														inquiryEditor.scope &&
													field.current?.value ===
														input
												) {
													rememberInquiry(
														config.requestPageUrl!,
														input,
														inquiryEditor.scope
													);
												}
											} }
										>
											{ __(
												'Send an inquiry',
												'linker-tools'
											) }
										</a>
									</>
								) : null }
							</p>
						) : null }
						{ ! historyView && conflict ? (
							<p role="alert" className="linker-genie-app__error">
								{ conflict }
							</p>
						) : null }
						{ ! historyView &&
						'error' === phase &&
						draftContext.phase === 'ready' ? (
							<>
								<p
									role="alert"
									className="linker-genie-app__error"
								>
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
						{ ! workspace &&
						! historyView &&
						( photoPrompt || listPrompt || filePrompt ) &&
						files.picked.length === 0 ? (
							<div className="linker-genie-app__photo-prompt">
								<p>
									{ filePrompt
										? __( 'Attach a file', 'linker-tools' )
										: null }
									{ ! filePrompt && listPrompt
										? __(
												'Genie checks every line of a parts list against our products. You can use a CSV or Excel (.xlsx) file, or a photo of the list.',
												'linker-tools'
											)
										: null }
									{ ! filePrompt && ! listPrompt
										? __(
												'Genie reads the brand and model from a nameplate photo and checks them against our range.',
												'linker-tools'
											)
										: null }
								</p>
								<button
									type="button"
									className="linker-genie-app__prompt"
									onClick={ () =>
										draftContext.capture() &&
										attachInput.current?.click()
									}
								>
									<AttachIcon />
									{ listPrompt || filePrompt
										? __( 'Choose a file', 'linker-tools' )
										: __(
												'Choose a photo',
												'linker-tools'
											) }
								</button>
							</div>
						) : null }
						{ ! historyView && page.planning_project_id ? (
							<p
								className="linker-genie-app__context-note"
								role="status"
							>
								<strong>{ page.title }</strong>
								{ ' · ' }
								{ page.planning_unsaved
									? __(
											'Save your changes so Genie can read the updated project.',
											'linker-tools'
										)
									: sprintf(
											/* translators: %d is the saved planning input revision. */
											__(
												'Saved project · revision %d',
												'linker-tools'
											),
											page.planning_revision ?? 0
										) }
							</p>
						) : null }
						{ ! historyView ? (
							<form
								className="linker-genie-app__composer"
								onSubmit={ ( event ) => {
									event.preventDefault();
									ask( input );
								} }
							>
								<button
									type="button"
									className="linker-genie-app__attach"
									aria-label={ __(
										'Attach a file',
										'linker-tools'
									) }
									disabled={ draftContext.phase !== 'ready' }
									onClick={ () =>
										draftContext.capture() &&
										attachInput.current?.click()
									}
								>
									<AttachIcon />
								</button>
								<input
									ref={ attachInput }
									type="file"
									accept={ ACCEPT }
									multiple
									hidden
									onChange={ ( event ) => {
										const picked = event.target.files;
										if (
											picked &&
											draftContext.acceptEditor()
										) {
											setRefused( '' );
											files.add( picked );
										}
										// Picking the same file again must
										// fire again.
										event.target.value = '';
									} }
								/>
								<label
									className="screen-reader-text"
									htmlFor="linker-genie-input"
								>
									{ __( 'Ask Genie', 'linker-tools' ) }
								</label>
								<textarea
									ref={ composerFieldRef }
									id="linker-genie-input"
									className="linker-genie-app__input"
									rows={ 1 }
									placeholder={ __(
										'Ask Genie',
										'linker-tools'
									) }
									value={
										draftContext.phase === 'ready'
											? input
											: ''
									}
									disabled={ draftContext.phase !== 'ready' }
									onChange={ ( event ) => {
										if ( ! event.target.value ) {
											stopDictation();
										}
										if ( draftContext.acceptEditor() ) {
											inputRef.current =
												event.target.value;
											setInput( event.target.value );
										}
									} }
									onKeyDown={ ( event ) => {
										// Enter sends, Shift+Enter is a new line:
										// a pasted parts list (#251) needs its
										// newlines, and a one-line question
										// still sends as before.
										if (
											'Enter' === event.key &&
											! event.shiftKey &&
											! event.nativeEvent.isComposing &&
											event.keyCode !== 229
										) {
											event.preventDefault();
											void ask( input );
										}
									} }
								/>
								{ ! workspace && canDictate ? (
									<button
										type="button"
										className="linker-genie-app__mic"
										aria-label={
											dictating
												? __(
														'Stop dictation',
														'linker-tools'
													)
												: __(
														'Dictate',
														'linker-tools'
													)
										}
										aria-pressed={ dictating }
										onClick={ dictate }
									>
										<MicIcon />
									</button>
								) : null }
								<button
									type="submit"
									className="linker-genie-app__send"
									disabled={
										draftContext.phase !== 'ready' ||
										entryInbox.recoveryPending.current ||
										phase === 'waiting' ||
										entryInbox.missing.length > 0 ||
										files.busy ||
										( ! input.trim() &&
											files.uploads.length === 0 )
									}
								>
									<SendIcon />
									<span className="screen-reader-text">
										{ __( 'Send', 'linker-tools' ) }
									</span>
								</button>
							</form>
						) : null }
						{ /* `.gp-disclosure` — the prototype prints it under the
						 * composer, inside the pinned zone. */ }
						{ workspace && config.disclosure && ! historyView ? (
							<p className="linker-genie-app__disclosure">
								{ config.disclosure }
							</p>
						) : null }
						{ /* `.gp-prompts` — the opening questions, under the
						 * composer in the prototype's welcome; the dock carries
						 * them in its own welcome above. */ }
						{ workspace &&
						thread.length === 0 &&
						config.prompts.length > 0 ? (
							<div className="linker-genie-app__prompts">
								{ config.prompts.map( ( prompt ) => (
									<button
										key={ prompt }
										type="button"
										className="linker-genie-app__prompt"
										disabled={
											draftContext.phase !== 'ready'
										}
										onClick={ () => ask( prompt ) }
									>
										{ prompt }
									</button>
								) ) }
							</div>
						) : null }
						{ ! workspace && ! historyView ? (
							<HelperFooter
								german={ german }
								disclosure={ config.disclosure }
							/>
						) : null }
					</div>
				) : null }
			</div>
		</section>
	);

	function appName(): string {
		return __( "Genie - Linker's AI assistant", 'linker-tools' );
	}
}

function HistoryRail( {
	open,
	docked,
	items,
	currentId,
	phase,
	note,
	onOpen,
	onClose,
	onSelect,
	onNew,
	onRetry,
	onDelete,
}: {
	open: boolean;
	docked: boolean;
	items: ConversationSummary[];
	currentId: number;
	phase: HistoryPhase;
	note: string;
	onOpen: () => void;
	onClose: () => void;
	onSelect: ( id: number ) => void;
	onNew: () => void;
	onRetry: () => void;
	onDelete: ( id: number ) => Promise< boolean >;
} ) {
	return (
		<aside
			className={ `linker-genie-rail${
				docked ? ' linker-genie-rail--docked' : ''
			}${ open ? ' is-open' : '' }` }
			aria-label={ __( 'Conversations', 'linker-tools' ) }
		>
			<div className="linker-genie-rail__top">
				<span className="linker-genie-app__monogram" aria-hidden="true">
					G
				</span>
				<span className="linker-genie-rail__brand">
					{ __( 'Genie', 'linker-tools' ) }
				</span>
				<button
					type="button"
					className="linker-genie-rail__toggle"
					aria-expanded={ open }
					onClick={ open ? onClose : onOpen }
				>
					<PanelIcon />
					<span className="screen-reader-text">
						{ open
							? __( 'Close sidebar', 'linker-tools' )
							: __( 'Conversations', 'linker-tools' ) }
					</span>
				</button>
			</div>
			<button
				type="button"
				className="linker-genie-rail__new"
				onClick={ onNew }
			>
				<NewConversationIcon />
				{ __( 'New conversation', 'linker-tools' ) }
			</button>
			<div className="linker-genie-rail__history">
				<HistoryList
					items={ items }
					currentId={ currentId }
					phase={ phase }
					note={ note }
					onSelect={ onSelect }
					onRetry={ onRetry }
					onDelete={ onDelete }
				/>
			</div>
		</aside>
	);
}

/**
 * The conversation list's four states — the rail's, and the dock history
 * view's. Both name the same classes: the list is the one component, the
 * container around it is what differs. Each row can be deleted after a
 * confirm in place (ticket #235); a guest's list says where it is kept.
 * @param root0
 * @param root0.items
 * @param root0.currentId
 * @param root0.phase
 * @param root0.note
 * @param root0.onSelect
 * @param root0.onRetry
 * @param root0.onDelete
 */
function HistoryList( {
	items,
	currentId,
	phase,
	note,
	onSelect,
	onRetry,
	onDelete,
}: {
	items: ConversationSummary[];
	currentId: number;
	phase: HistoryPhase;
	note: string;
	onSelect: ( id: number ) => void;
	onRetry: () => void;
	onDelete: ( id: number ) => Promise< boolean >;
} ) {
	// The row asking "Delete this conversation permanently?", and one whose delete failed.
	const [ confirming, setConfirming ] = useState( 0 );
	const [ failed, setFailed ] = useState( 0 );
	return (
		<>
			<p className="linker-genie-rail__label">
				{ __( 'Conversations', 'linker-tools' ) }
			</p>
			{ 'loading' === phase ? (
				<p
					className="linker-genie-rail__empty"
					role="status"
					aria-live="polite"
				>
					{ __( 'Loading conversations…', 'linker-tools' ) }
				</p>
			) : null }
			{ 'failed' === phase ? (
				<p role="alert" className="linker-genie-rail__empty">
					{ __(
						'Conversations could not be loaded.',
						'linker-tools'
					) }{ ' ' }
					<button type="button" onClick={ onRetry }>
						{ __( 'Try again', 'linker-tools' ) }
					</button>
				</p>
			) : null }
			{ 'ready' === phase && items.length === 0 ? (
				<p className="linker-genie-rail__empty">
					{ __( 'No earlier conversation.', 'linker-tools' ) }
				</p>
			) : null }
			{ 'ready' === phase && items.length > 0 ? (
				<ul className="linker-genie-rail__list">
					{ items.map( ( item ) =>
						confirming === item.id ? (
							<li
								key={ item.id }
								className="linker-genie-rail__confirm"
							>
								<p
									className="linker-genie-rail__confirm-text"
									role={
										failed === item.id ? 'alert' : undefined
									}
								>
									{ failed === item.id
										? __(
												'Not deleted. Try again.',
												'linker-tools'
											)
										: __(
												'Delete this conversation permanently?',
												'linker-tools'
											) }
								</p>
								<div className="linker-genie-rail__confirm-actions">
									<button
										type="button"
										className="linker-genie-rail__confirm-delete"
										onClick={ () => {
											void onDelete( item.id ).then(
												( removed ) => {
													if ( removed ) {
														setConfirming( 0 );
														setFailed( 0 );
														return;
													}
													setFailed( item.id );
												}
											);
										} }
									>
										{ __( 'Delete', 'linker-tools' ) }
									</button>
									<button
										type="button"
										className="linker-genie-rail__confirm-cancel"
										onClick={ () => {
											setConfirming( 0 );
											setFailed( 0 );
										} }
									>
										{ __( 'Cancel', 'linker-tools' ) }
									</button>
								</div>
							</li>
						) : (
							<li
								key={ item.id }
								className="linker-genie-rail__row"
							>
								<button
									type="button"
									className="linker-genie-rail__item"
									aria-current={
										item.id === currentId
											? 'true'
											: undefined
									}
									onClick={ () => onSelect( item.id ) }
								>
									{ item.title }
								</button>
								<button
									type="button"
									className="linker-genie-rail__delete"
									aria-label={
										// translators: %s is the conversation's title (its first message).
										__(
											'Delete conversation: %s',
											'linker-tools'
										).replace( '%s', item.title )
									}
									onClick={ () => {
										setFailed( 0 );
										setConfirming( item.id );
									} }
								>
									<TrashIcon size={ 16 } />
								</button>
							</li>
						)
					) }
				</ul>
			) : null }
			{ note && 'failed' !== phase ? (
				<p className="linker-genie-rail__note">{ note }</p>
			) : null }
		</>
	);
}
