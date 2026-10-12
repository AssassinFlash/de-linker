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
	readThread,
	sendTurn,
	type Block,
	type CardsBlock,
	type CompareBlock,
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
	const sending = useRef( false );
	const currentThread = useRef< TurnMessage[] >( [] );
	const restoring = useRef< Promise< void > >( Promise.resolve() );

	const store = storeClient( config.restUrl );

	const ask = useCallback(
		async ( text: string ) => {
			if ( ! text.trim() || sending.current ) {
				return;
			}
			sending.current = true;
			setOpen( true );
			setPhase( 'waiting' );
			setInput( '' );
			try {
				// An entry can arrive before the saved thread. Append to that
				// history after restore rather than race it or discard it.
				await restoring.current;
				const next: TurnMessage[] = [
					...currentThread.current,
					{ role: 'user', content: text },
				];
				currentThread.current = next;
				setThread( next );
				const answer = await sendTurn(
					config.turnUrl,
					config.restNonce,
					config.locale,
					next,
					{ type: config.pageType }
				);
				const assistant = assistantMessage( answer );
				currentThread.current = next.concat( assistant );
				setThread( currentThread.current );
				setTurn( answer );
				setPhase( 'ask' );
			} catch {
				setPhase( 'error' );
			} finally {
				sending.current = false;
			}
		},
		[ config ]
	);

	// The conversation the browser already has comes back on mount: a reload,
	// or opening Genie on another page of the site, shows the thread instead
	// of an empty panel (docs/specs/13-genie.md).
	useEffect( () => {
		let cancelled = false;
		restoring.current = ( async () => {
			const stored = await readThread(
				config.threadUrl,
				config.restNonce
			);
			if ( cancelled || stored.messages.length === 0 ) {
				return;
			}
			currentThread.current = stored.messages;
			setThread( stored.messages );
			if ( stored.turn ) {
				setTurn( stored.turn );
			}
		} )();
		return () => {
			cancelled = true;
		};
	}, [ config.threadUrl, config.restNonce ] );

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

	return (
		<section
			className="linker-genie-app"
			lang={ config.locale }
			aria-label={ appName() }
		>
			<header className="linker-genie-app__bar">
				<p className="linker-genie-app__title">{ appName() }</p>
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
			</header>
			{ open ? (
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
								{ __( 'Genie is thinking…', 'linker-tools' ) }
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
		</section>
	);

	function appName(): string {
		return __( "Genie - Linker's AI assistant", 'linker-tools' );
	}
}

function idsOf( blocks: Block[], kind: 'cards' | 'compare' ): number[] {
	for ( const block of blocks ) {
		if ( block.type === kind ) {
			return ( block as CardsBlock | CompareBlock ).product_ids;
		}
	}
	return [];
}
