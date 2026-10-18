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
import { saveSolution } from '../configurator/api/solutions';
import type { CardState } from '../shared/ProductCard';
import type { GenieConfig } from './config';
import {
	assistantMessage,
	deleteConversation,
	emailConversation,
	listConversations,
	readThread,
	selectConversation,
	sendTurn,
	TurnError,
	type Block,
	type CardPrice,
	type CardsBlock,
	type CompareBlock,
	type ContactBlock,
	type ConversationSummary,
	type SentContact,
	type SentInquiryCard,
	type EmailOutcome,
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
import './genie.css';

interface CardItem {
	productId: number;
	status: { state: CardState; text: string };
}

/**
 * The browser's own speech recognition, structurally — lib.dom's
 * SpeechRecognition is what the engine ships; the constructor and the three
 * events the dictation button uses. `webkitSpeechRecognition` is the same
 * interface under its prefixed name.
 */
interface Dictation {
	lang: string;
	onresult:
		| ( ( event: {
				results: ArrayLike< ArrayLike< { transcript: string } > >;
		  } ) => void )
		| null;
	onend: ( () => void ) | null;
	onerror: ( () => void ) | null;
	start: () => void;
	stop: () => void;
}

/** Test seam: the dictation test stubs the constructor. */
export type { Dictation };

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

declare global {
	interface Window {
		SpeechRecognition?: new () => Dictation;
		webkitSpeechRecognition?: new () => Dictation;
	}
}

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
	const [ open, setOpen ] = useState( false );
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
	const [ cards, setCards ] = useState< CardItem[] >( [] );
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
	const field = useRef< HTMLInputElement >( null );
	const recognition = useRef< Dictation | null >( null );
	const files = useAttachments();
	// Why the last turn's files were refused by the proxy, if they were.
	const [ refused, setRefused ] = useState( '' );
	// Opened to send a nameplate photo (the preview card's suggestion): the
	// panel offers the picker, which only a click may open.
	const [ photoPrompt, setPhotoPrompt ] = useState( false );
	const [ dictating, setDictating ] = useState( false );
	const sending = useRef( false );
	const currentThread = useRef< TurnMessage[] >( [] );
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

	const store = storeClient( config.restUrl );
	const workspace = config.surface === 'workspace';

	const refreshHistory = useCallback( () => {
		const epoch = historyEpoch;
		return enqueue( async () => {
			const listed = await listConversations(
				config.conversationsUrl,
				config.restNonce
			);
			// A switch owns the rail now. Applying this list would put the
			// conversation it left back as current.
			if ( epoch !== historyEpoch ) {
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
	}, [ config.conversationsUrl, config.restNonce, show ] );

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

	const showStored = useCallback( async () => {
		setRevealingAt( null );
		const stored = await readThread( config.threadUrl, config.restNonce );
		currentThread.current = stored.messages;
		setThread( stored.messages );
		setTurn( stored.turn );
		turnAt.current = stored.turn ? stored.messages.length - 1 : -1;
		setContacts( stored.contacts ?? [] );
		setInquiries( stored.inquiries ?? [] );
		setPhase( 'ask' );
		setInput( '' );
		setMail( 'idle' );
	}, [ config.threadUrl, config.restNonce ] );

	const ask = useCallback(
		async ( text: string ) => {
			const uploads = files.uploads;
			const question = [
				text.trim(),
				...uploads.map( ( upload ) =>
					// translators: %s is the name of a file the visitor attached.
					__( 'Attached: %s', 'linker-tools' ).replace(
						'%s',
						upload.name
					)
				),
			]
				.filter( ( part ) => part !== '' )
				.join( '\n' );
			if ( ! question || sending.current || files.busy ) {
				return;
			}
			setOpen( true );
			setDockHistory( false );
			setPhase( 'waiting' );
			setRevealingAt( null );
			setInput( '' );
			setRefused( '' );
			setPhotoPrompt( false );
			files.clear();
			return enqueue( async () => {
				// Claim the composer only once this ask is the lane's head.
				// Setting it before the queue would drop a history click that
				// arrives while a switch is still resolving.
				sending.current = true;
				// The lane already ran the mount restore and any switch, so the
				// ref is the conversation this ask belongs to.
				const before = currentThread.current;
				try {
					const next: TurnMessage[] = [
						...before,
						{ role: 'user', content: question },
					];
					currentThread.current = next;
					setThread( next );
					const answer = await sendTurn(
						config.turnUrl,
						config.restNonce,
						config.locale,
						next,
						config.page,
						uploads
					);
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
					// such; anything else is Genie not answering.
					const reason =
						error instanceof TurnError &&
						error.code.startsWith( 'linker_genie_attachment_' )
							? error.code.slice(
									'linker_genie_attachment_'.length
								)
							: '';
					if ( reason ) {
						// Nothing was sent: the question leaves the thread and
						// goes back into the field, to send again without
						// the file or later.
						currentThread.current = before;
						setThread( before );
						setInput( text );
						setRefused(
							refusalText(
								reason === 'throttled' ||
									reason === 'count' ||
									reason === 'size' ||
									reason === 'type'
									? reason
									: 'unreadable'
							)
						);
						setPhase( 'ask' );
					} else {
						setPhase( 'error' );
					}
				} finally {
					sending.current = false;
				}
			} );
		},
		[ config, refreshHistory, files ]
	);

	// "Type the model": the way out of a nameplate the customer does not
	// confirm, or one that could not be read.
	const typeModel = useCallback( () => {
		// The model goes where the placeholder stands; the field opens with
		// the words before it, ready for the customer to type the name.
		setInput(
			sprintf(
				// translators: %s stays empty: the customer types the model after the words.
				__( 'My device is the %s', 'linker-tools' ),
				''
			)
		);
		field.current?.focus();
	}, [] );

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
			const stored = await Promise.race( [
				readThread( config.threadUrl, config.restNonce ),
				pending.promise,
			] );
			if ( cancelled ) {
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
	}, [ config.threadUrl, config.restNonce, refreshHistory ] );

	const continueConversation = useCallback(
		( id?: number ) => {
			// Before the job, not inside it: a list already queued behind
			// this switch captured the old epoch and must drop itself.
			historyEpoch += 1;
			// A switched-to conversation is not the one the hero began.
			setFromHome( false );
			return enqueue( async () => {
				try {
					const selected = await selectConversation(
						config.conversationsUrl,
						config.restNonce,
						id
					);
					setHistoryPhase( 'ready' );
					setHistory( selected.conversations );
					show( selected.currentId );
					// Docked, the rail stays where the visitor put it; as an
					// overlay it would hide the conversation just picked.
					if ( window.innerWidth < OVERLAY_WIDTH ) {
						setRailOpen( false );
					}
					setOpen( true );
					await showStored();
				} catch {
					setHistoryPhase( 'failed' );
					setOpen( true );
				}
			} );
		},
		[ config.conversationsUrl, config.restNonce, showStored, show ]
	);

	// Clearing a conversation (ticket #235): the server deletes it with its
	// thread and answers the list without it. When it was the one on screen,
	// the panel shows what is current now — another conversation, or none.
	const removeConversation = useCallback(
		( id: number ): Promise< boolean > => {
			historyEpoch += 1;
			// The hero's conversation may be the one being cleared; the
			// origin line follows the conversation, not the dock.
			setFromHome( false );
			let removed = false;
			return enqueue( async () => {
				const remaining = await deleteConversation(
					config.conversationsUrl,
					config.restNonce,
					id
				);
				removed = true;
				setHistoryPhase( 'ready' );
				setHistory( remaining.conversations );
				if ( id !== shownId.current ) {
					return;
				}
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
		[ config.conversationsUrl, config.restNonce, showStored, show ]
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
		const SpeechRecognition =
			window.SpeechRecognition ?? window.webkitSpeechRecognition;
		if ( ! SpeechRecognition ) {
			return;
		}
		if ( dictating && recognition.current ) {
			recognition.current.stop();
			return;
		}
		const session = new SpeechRecognition();
		session.lang = config.locale === 'de' ? 'de-DE' : 'en-US';
		session.onresult = ( event ) => {
			const heard = event.results[ 0 ]?.[ 0 ]?.transcript ?? '';
			if ( heard ) {
				setInput( ( current ) =>
					current ? `${ current } ${ heard }` : heard
				);
			}
		};
		session.onend = () => setDictating( false );
		session.onerror = () => setDictating( false );
		recognition.current = session;
		setDictating( true );
		session.start();
	}, [ config.locale, dictating ] );

	// The mount's own cleanup, not a reaction to a render; the ref is the
	// one thing the deps rule treats as stable, so the list stays empty.
	useEffect( () => () => recognition.current?.stop(), [] );

	const cardIds = idsOf( turn?.blocks ?? [], 'cards' );
	const cardPrices = pricesOf( turn?.blocks ?? [] );
	const compareIds = idsOf( turn?.blocks ?? [], 'compare' );

	// All page entries go through the dock loader. Ready is emitted only after
	// this listener exists, so even a click while the bundle loads is delivered
	// exactly once. Plain open never creates an unsolicited model turn.
	useEffect( () => {
		function onOpen( event: Event ) {
			setOpen( true );
			setDockHistory( false );
			const detail = (
				event as CustomEvent< {
					message?: unknown;
					attach?: unknown;
					refresh?: unknown;
					fromHome?: unknown;
				} >
			 ).detail;
			if ( detail && true === detail.fromHome ) {
				setFromHome( true );
			}
			if ( detail && true === detail.refresh ) {
				// The home hero (#232) wrote the thread while the dock was
				// shut: read it before showing, then deliver any question.
				const message =
					typeof detail.message === 'string' ? detail.message : '';
				void showStored().then( () => {
					if ( message ) {
						void ask( message );
					}
				} );
				return;
			}
			if (
				detail &&
				typeof detail.message === 'string' &&
				detail.message
			) {
				void ask( detail.message );
			} else if ( detail && true === detail.attach ) {
				setPhotoPrompt( true );
			}
		}
		window.addEventListener( 'linker-genie-open', onOpen );
		return () => window.removeEventListener( 'linker-genie-open', onOpen );
	}, [ ask, showStored ] );

	useEffect( () => {
		window.dispatchEvent(
			new CustomEvent( 'linker-genie-state', { detail: { open } } )
		);
	}, [ open ] );

	useEffect( () => {
		window.dispatchEvent( new CustomEvent( 'linker-genie-ready' ) );
	}, [] );

	function onCardStatus( productId: number, state: CardState, text: string ) {
		setCards( ( items ) => {
			const found = items.some(
				( item ) => item.productId === productId
			);
			return found
				? items.map( ( item ) =>
						item.productId === productId
							? { ...item, status: { state, text } }
							: item
					)
				: [ ...items, { productId, status: { state, text } } ];
		} );
	}

	async function addCardToDraft( productId: number ) {
		onCardStatus( productId, 'pending', __( 'Adding…', 'linker-tools' ) );
		const complete = await store.addAll(
			[ { productId, quantity: 1 } ],
			( id, state ) =>
				onCardStatus(
					id,
					state,
					{
						pending: __( 'Adding…', 'linker-tools' ),
						added: __( 'In your solution draft.', 'linker-tools' ),
						unverified: __(
							'Sent, but the draft does not show it yet. Please check.',
							'linker-tools'
						),
						retry: __( 'Not added. Try again.', 'linker-tools' ),
					}[ state ]
				)
		);
		void complete;
	}

	async function saveCardSolution( productId: number, title: string ) {
		onCardStatus( productId, 'pending', __( 'Saving…', 'linker-tools' ) );
		try {
			await saveSolution( config.restUrl, config.restNonce, {
				kind: 'residential',
				title,
				input: {
					locale: config.locale,
					plz: '',
					annual_kwh: 0,
					pv_kwp: 0,
					phase: 3,
					backup: 'none',
					heat_pump: false,
					electric_vehicle: false,
				},
				lines: [ { productId, quantity: 1 } ],
			} );
			onCardStatus(
				productId,
				'added',
				__( 'Saved to your account.', 'linker-tools' )
			);
		} catch {
			onCardStatus(
				productId,
				'retry',
				__( 'Not saved. Try again.', 'linker-tools' )
			);
		}
	}

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
			page={ config.page }
			onSent={ inquirySent }
		/>
	);
	return (
		<section
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
					onClick={ () => {
						setDockHistory( false );
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
					items={ history }
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
						{ historyView ? (
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
						( workspace || thread.length > 0 ) ? (
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
								{ 'error' === phase ? (
									<p
										role="alert"
										className="linker-genie-app__error"
									>
										{ __(
											'Genie did not answer. Please try again.',
											'linker-tools'
										) }
									</p>
								) : null }
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
											onAsk={ ask }
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
												status={
													cards.find(
														( item ) =>
															item.productId ===
															productId
													)?.status ?? {
														state: 'idle',
														text: '',
													}
												}
												price={ cardPrices.find(
													( line ) =>
														line.product_id ===
														productId
												) }
												onAdd={ addCardToDraft }
												onSave={ saveCardSolution }
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
											page={ config.page }
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
						{ /* The picked files, over the composer (#236). */ }
						{ ! workspace && ! historyView ? (
							<AttachmentChips
								picked={ files.picked }
								onRemove={ files.remove }
							/>
						) : null }
						{ ! workspace && ! historyView && refused ? (
							<p
								role="alert"
								className="linker-genie-app__refused"
							>
								{ refused }
							</p>
						) : null }
						{ ! workspace &&
						! historyView &&
						photoPrompt &&
						files.picked.length === 0 ? (
							<div className="linker-genie-app__photo-prompt">
								<p>
									{ __(
										'Genie reads the brand and model from a nameplate photo and checks them against our range.',
										'linker-tools'
									) }
								</p>
								<button
									type="button"
									className="linker-genie-app__prompt"
									onClick={ () =>
										attachInput.current?.click()
									}
								>
									<AttachIcon />
									{ __( 'Choose a photo', 'linker-tools' ) }
								</button>
							</div>
						) : null }
						{ ! historyView ? (
							<form
								className="linker-genie-app__composer"
								onSubmit={ ( event ) => {
									event.preventDefault();
									ask( input );
								} }
							>
								{ ! workspace ? (
									/*
									 * The Advisor composer's `.lia-vision-button`:
									 * the attach entry. A photo (HEIC too) or a PDF
									 * is prepared as it is picked and sent with the
									 * turn; Genie reads it (#236).
									 */
									<>
										<button
											type="button"
											className="linker-genie-app__attach"
											aria-label={ __(
												'Attach a file',
												'linker-tools'
											) }
											onClick={ () =>
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
												const picked =
													event.target.files;
												if ( picked ) {
													setRefused( '' );
													files.add( picked );
												}
												// Picking the same file again must
												// fire again.
												event.target.value = '';
											} }
										/>
									</>
								) : null }
								<label
									className="screen-reader-text"
									htmlFor="linker-genie-input"
								>
									{ __( 'Ask Genie', 'linker-tools' ) }
								</label>
								<input
									ref={ field }
									id="linker-genie-input"
									className="linker-genie-app__input"
									placeholder={ __(
										'Ask Genie',
										'linker-tools'
									) }
									value={ input }
									onChange={ ( event ) =>
										setInput( event.target.value )
									}
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
										phase === 'waiting' ||
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

/**
 * The price lines of the turn's cards, as the service filled them (#242).
 *
 * @param blocks The turn's blocks.
 */
function pricesOf( blocks: Block[] ): CardPrice[] {
	for ( const block of blocks ) {
		if ( 'cards' === block.type ) {
			return block.prices ?? [];
		}
	}
	return [];
}

function idsOf( blocks: Block[], kind: 'cards' | 'compare' ): number[] {
	for ( const block of blocks ) {
		if ( block.type === kind ) {
			return ( block as CardsBlock | CompareBlock ).product_ids;
		}
	}
	return [];
}
