/**
 * The Genie panel: one thread, the blocks of the current turn, and the
 * actions the customer can run on a card (docs/specs/13-genie.md). The pieces
 * live in ./components/, the API clients in ./api/.
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
import { saveSolution } from '../configurator/api/solutions';
import type { CardState } from '../shared/ProductCard';
import type { GenieConfig } from './config';
import {
	assistantMessage,
	listConversations,
	readThread,
	selectConversation,
	sendTurn,
	type Block,
	type CardsBlock,
	type CompareBlock,
	type ConversationSummary,
	type Turn,
	type TurnMessage,
} from './api/turn';
import { BlockView } from './components/BlockView';
import { Compare } from './components/Compare';
import { GenieCard } from './components/GenieCard';
import { VoteButtons } from './components/VoteButtons';
import './genie.css';

interface CardItem {
	productId: number;
	status: { state: CardState; text: string };
}

type Phase = 'ask' | 'waiting' | 'error';
type HistoryPhase = 'ready' | 'failed';

/**
 * One lane for restore, switch and ask. It lives outside the component:
 * an enqueue closed over a render would chain the next click onto a tail
 * that render already replaced.
 */
let turnLane: Promise< void > = Promise.resolve();

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
	const [ phase, setPhase ] = useState< Phase >( 'ask' );
	const [ input, setInput ] = useState( '' );
	const [ cards, setCards ] = useState< CardItem[] >( [] );
	const [ history, setHistory ] = useState< ConversationSummary[] >( [] );
	const [ historyPhase, setHistoryPhase ] =
		useState< HistoryPhase >( 'ready' );
	const [ currentId, setCurrentId ] = useState( 0 );
	const [ railOpen, setRailOpen ] = useState(
		config.surface === 'workspace'
	);
	const sending = useRef( false );
	const currentThread = useRef< TurnMessage[] >( [] );

	const store = storeClient( config.restUrl );
	const workspace = config.surface === 'workspace';

	const refreshHistory = useCallback( async () => {
		const listed = await listConversations(
			config.conversationsUrl,
			config.restNonce
		);
		if ( ! listed.ok ) {
			setHistoryPhase( 'failed' );
			return;
		}
		setHistoryPhase( 'ready' );
		setHistory( listed.conversations );
		if ( listed.currentId ) {
			setCurrentId( listed.currentId );
		}
	}, [ config.conversationsUrl, config.restNonce ] );

	const showStored = useCallback( async () => {
		const stored = await readThread( config.threadUrl, config.restNonce );
		currentThread.current = stored.messages;
		setThread( stored.messages );
		setTurn( stored.turn );
		setPhase( 'ask' );
		setInput( '' );
	}, [ config.threadUrl, config.restNonce ] );

	const ask = useCallback(
		async ( text: string ) => {
			const question = text.trim();
			if ( ! question || sending.current ) {
				return;
			}
			setOpen( true );
			setPhase( 'waiting' );
			setInput( '' );
			return enqueue( async () => {
				// Claim the composer only once this ask is the lane's head.
				// Setting it before the queue would drop a history click that
				// arrives while a switch is still resolving.
				sending.current = true;
				try {
					// The lane already ran the mount restore and any switch,
					// so the ref is the conversation this ask belongs to.
					const next: TurnMessage[] = [
						...currentThread.current,
						{ role: 'user', content: question },
					];
					currentThread.current = next;
					setThread( next );
					const answer = await sendTurn(
						config.turnUrl,
						config.restNonce,
						config.locale,
						next,
						{
							type: config.pageType,
							...( config.productId > 0
								? { product_id: config.productId }
								: {} ),
						}
					);
					const assistant = assistantMessage( answer );
					currentThread.current = next.concat( assistant );
					setThread( currentThread.current );
					setTurn( answer );
					setPhase( 'ask' );
					void refreshHistory();
				} catch {
					setPhase( 'error' );
				} finally {
					sending.current = false;
				}
			} );
		},
		[ config, refreshHistory ]
	);

	// The conversation the browser already has comes back on mount: a reload,
	// or opening Genie on another page of the site, shows the thread instead
	// of an empty panel (docs/specs/13-genie.md).
	useEffect( () => {
		let cancelled = false;
		const pending = deferred< {
			messages: TurnMessage[];
			turn: Turn | null;
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
				if ( stored.turn ) {
					setTurn( stored.turn );
				}
			}
			await refreshHistory();
		} ).catch( () => undefined );
		return () => {
			cancelled = true;
			// A superseded mount must not hold the lane. The replacement
			// reads the thread itself.
			pending.resolve( { messages: [], turn: null } );
		};
	}, [ config.threadUrl, config.restNonce, refreshHistory ] );

	const continueConversation = useCallback(
		( id?: number ) =>
			enqueue( async () => {
				try {
					const selected = await selectConversation(
						config.conversationsUrl,
						config.restNonce,
						id
					);
					setHistoryPhase( 'ready' );
					setHistory( selected.conversations );
					setCurrentId( selected.currentId );
					setRailOpen( false );
					setOpen( true );
					await showStored();
				} catch {
					setHistoryPhase( 'failed' );
					setOpen( true );
				}
			} ),
		[ config.conversationsUrl, config.restNonce, showStored ]
	);

	const cardIds = idsOf( turn?.blocks ?? [], 'cards' );
	const compareIds = idsOf( turn?.blocks ?? [], 'compare' );

	// All page entries go through the dock loader. Ready is emitted only after
	// this listener exists, so even a click while the bundle loads is delivered
	// exactly once. Plain open never creates an unsolicited model turn.
	useEffect( () => {
		function onOpen( event: Event ) {
			setOpen( true );
			const detail = ( event as CustomEvent< { message?: unknown } > )
				.detail;
			if ( detail && typeof detail.message === 'string' ) {
				void ask( detail.message );
			}
		}
		window.addEventListener( 'linker-genie-open', onOpen );
		return () => window.removeEventListener( 'linker-genie-open', onOpen );
	}, [ ask ] );

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

	const visible = workspace || open;
	return (
		<section
			className={ `linker-genie-app${
				workspace ? ' linker-genie-app--workspace' : ''
			}` }
			lang={ config.locale }
			aria-label={ appName() }
		>
			{ visible ? (
				<HistoryRail
					open={ railOpen }
					docked={ workspace }
					items={ history }
					currentId={ currentId }
					onOpen={ () => setRailOpen( true ) }
					onClose={ () => setRailOpen( false ) }
					failed={ 'failed' === historyPhase }
					onSelect={ ( id ) => void continueConversation( id ) }
					onNew={ () => void continueConversation() }
					onRetry={ () => void refreshHistory() }
				/>
			) : null }
			<div className="linker-genie-app__main">
				<header className="linker-genie-app__bar">
					<p className="linker-genie-app__title">{ appName() }</p>
					<div className="linker-genie-app__bar-actions">
						{ ! workspace && config.workspaceUrl ? (
							<a
								className="linker-genie-app__full"
								href={ config.workspaceUrl }
							>
								{ __( 'Open full page', 'linker-tools' ) }
							</a>
						) : null }
						{ ! workspace ? (
							<button
								type="button"
								className="linker-genie-app__toggle"
								aria-expanded={ open }
								onClick={ () => setOpen( ! open ) }
							>
								{ open
									? __( 'Hide', 'linker-tools' )
									: __( 'Open', 'linker-tools' ) }
							</button>
						) : null }
					</div>
				</header>
				{ visible ? (
					<div className="linker-genie-app__panel">
						{ config.disclosure ? (
							<p className="linker-genie-app__disclosure">
								{ config.disclosure }
							</p>
						) : null }
						<ol className="linker-genie-app__thread">
							{ thread.map( ( message, index ) => (
								<li
									key={ index }
									className={ `linker-genie-app__message linker-genie-app__message--${ message.role }` }
								>
									{ message.content }
									{ 'assistant' === message.role ? (
										<VoteButtons
											voteUrl={ config.voteUrl }
											nonce={ config.restNonce }
											turnId={ message.turnId }
										/>
									) : null }
								</li>
							) ) }
							{ 'waiting' === phase ? (
								<li className="linker-genie-app__message linker-genie-app__message--assistant">
									{ __(
										'Genie is thinking…',
										'linker-tools'
									) }
								</li>
							) : null }
						</ol>
						{ 'error' === phase ? (
							<p role="alert" className="linker-genie-app__error">
								{ __(
									'Genie did not answer. Please try again.',
									'linker-tools'
								) }
							</p>
						) : null }
						{ turn?.blocks.map( ( block, index ) => (
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
													item.productId === productId
											)?.status ?? {
												state: 'idle',
												text: '',
											}
										}
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
						{ thread.length === 0 && config.prompts.length > 0 ? (
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
						<form
							className="linker-genie-app__composer"
							onSubmit={ ( event ) => {
								event.preventDefault();
								ask( input );
							} }
						>
							<label
								className="screen-reader-text"
								htmlFor="linker-genie-input"
							>
								{ __( 'Ask Genie', 'linker-tools' ) }
							</label>
							<input
								id="linker-genie-input"
								className="linker-genie-app__input"
								value={ input }
								onChange={ ( event ) =>
									setInput( event.target.value )
								}
							/>
							<button
								type="submit"
								className="linker-genie-app__send"
							>
								{ __( 'Send', 'linker-tools' ) }
							</button>
						</form>
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
	failed,
	onOpen,
	onClose,
	onSelect,
	onNew,
	onRetry,
}: {
	open: boolean;
	docked: boolean;
	items: ConversationSummary[];
	currentId: number;
	failed: boolean;
	onOpen: () => void;
	onClose: () => void;
	onSelect: ( id: number ) => void;
	onNew: () => void;
	onRetry: () => void;
} ) {
	return (
		<aside
			className={ `linker-genie-rail${
				docked ? ' linker-genie-rail--docked' : ''
			}${ open ? ' is-open' : '' }` }
			aria-label={ __( 'Conversations', 'linker-tools' ) }
		>
			<div className="linker-genie-rail__top">
				<button
					type="button"
					className="linker-genie-rail__toggle"
					aria-expanded={ open }
					onClick={ open ? onClose : onOpen }
				>
					{ open
						? __( 'Close sidebar', 'linker-tools' )
						: __( 'Conversations', 'linker-tools' ) }
				</button>
				<button
					type="button"
					className="linker-genie-rail__new"
					onClick={ onNew }
				>
					{ __( 'New conversation', 'linker-tools' ) }
				</button>
			</div>
			{ failed ? (
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
			{ ! failed && items.length === 0 ? (
				<p className="linker-genie-rail__empty">
					{ __( 'No earlier conversation.', 'linker-tools' ) }
				</p>
			) : null }
			{ ! failed && items.length > 0 ? (
				<ul className="linker-genie-rail__list">
					{ items.map( ( item ) => (
						<li key={ item.id }>
							<button
								type="button"
								className="linker-genie-rail__item"
								aria-current={
									item.id === currentId ? 'true' : undefined
								}
								onClick={ () => onSelect( item.id ) }
							>
								{ item.title }
							</button>
						</li>
					) ) }
				</ul>
			) : null }
		</aside>
	);
}

function idsOf( blocks: Block[], kind: 'cards' | 'compare' ): number[] {
	for ( const block of blocks ) {
		if ( block.type === kind ) {
			return ( block as CardsBlock | CompareBlock ).product_ids;
		}
	}
	return [];
}
