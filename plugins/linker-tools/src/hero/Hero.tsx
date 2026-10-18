/**
 * The conversation the home hero unfolds in place (ticket #232, variant B):
 * the header the owner specified, the shared thread (session.ts), the #236
 * attachment cards, and the answer's cards in a four-column grid (two on a
 * phone).
 *
 * The page's own textarea stays the follow-up field: this component renders
 * above it, inside `.hero-dialog`, and the controller wires Enter, the send
 * button and the capsules to the bridge this component registers.
 */

/**
 * WordPress dependencies
 */
import { useCallback, useEffect, useRef, useState } from '@wordpress/element';
import { __, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { saveSolution } from '../configurator/api/solutions';
import { storeClient } from '../configurator/api/store';
import type { CardState } from '../shared/ProductCard';
import {
	TurnError,
	type Block,
	type CardPrice,
	type CardsBlock,
	type CompareBlock,
	type Turn,
	type TurnMessage,
} from '../genie/api/turn';
import { useAttachments } from '../genie/attachments/useAttachments';
import { AttachmentCard } from '../genie/components/AttachmentCard';
import {
	AttachmentChips,
	refusalText,
} from '../genie/components/AttachmentChips';
import { BlockView } from '../genie/components/BlockView';
import { Compare } from '../genie/components/Compare';
import { GenieCard } from '../genie/components/GenieCard';
import { Reply } from '../genie/components/Reply';
import { Transcript } from '../genie/components/Transcript';
import type { GenieConfig } from '../genie/config';
import { HeroSession } from './session';

/** The controller's way into the conversation while it is unfolded. */
export interface HeroBridge {
	/**
	 * Asks a question; picked files are prepared first and sent with it.
	 *
	 * @param text  The question (empty when the files are the question).
	 * @param files The files just picked, if any.
	 */
	ask: ( text: string, files?: ArrayLike< File > ) => void;
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
	/** Opens the page's file picker ('photo' for the nameplate button). */
	requestPicker: ( kind: 'photo' | 'file' ) => void;
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
	requestPicker,
}: HeroConversationProps ) {
	const [ thread, setThread ] = useState< TurnMessage[] >( [] );
	const [ turn, setTurn ] = useState< Turn | null >( null );
	const [ phase, setPhase ] = useState< Phase >( 'ask' );
	const [ refused, setRefused ] = useState( '' );
	const [ pendingSend, setPendingSend ] = useState< {
		text: string;
	} | null >( null );
	const [ cardStates, setCardStates ] = useState<
		{ productId: number; status: { state: CardState; text: string } }[]
	>( [] );
	const sending = useRef( false );
	const files = useAttachments();
	// The bridge is registered once; the refs keep it calling the latest
	// render's send and file state.
	const filesRef = useRef( files );
	filesRef.current = files;
	const sendRef = useRef< ( text: string ) => void >( () => undefined );
	const [ store ] = useState( () => storeClient( config.restUrl ) );
	const locale = config.locale;

	// The conversation the browser already has: the dock's thread, or what
	// the hero itself asked before it was folded and unfolded again.
	useEffect( () => {
		let cancelled = false;
		void session.load().then( ( stored ) => {
			if ( ! cancelled ) {
				setThread( stored.messages );
				setTurn( stored.turn );
			}
		} );
		return () => {
			cancelled = true;
		};
	}, [ session ] );

	useEffect( () => {
		onConversation( thread.length > 0 );
	}, [ thread.length, onConversation ] );

	const send = useCallback(
		async ( text: string ) => {
			const picked = filesRef.current.uploads;
			const question = [
				text.trim(),
				...picked.map( ( upload ) =>
					// translators: %s is the name of a file the visitor attached.
					__( 'Attached: %s', 'linker-tools' ).replace(
						'%s',
						upload.name
					)
				),
			]
				.filter( ( part ) => part !== '' )
				.join( '\n' );
			if ( ! question || sending.current || filesRef.current.busy ) {
				return;
			}
			sending.current = true;
			setRefused( '' );
			setPhase( 'waiting' );
			setPrompt( '' );
			let shown: TurnMessage[] = [];
			try {
				// Read first, so the dock's thread is part of this question
				// and the proxy records the whole conversation (session.ts).
				await session.load();
				shown = [
					...session.messages,
					{ role: 'user', content: question },
				];
				setThread( shown );
				const result = await session.ask( question, picked );
				filesRef.current.clear();
				setThread( result.messages );
				setTurn( result.answer );
				setPhase( 'ask' );
			} catch ( error ) {
				// A file the proxy refused is said as such and the question
				// goes back into the field; anything else is no answer, and
				// the question stays so the error has something to stand under.
				const reason =
					error instanceof TurnError &&
					error.code.startsWith( 'linker_genie_attachment_' )
						? error.code.slice( 'linker_genie_attachment_'.length )
						: '';
				if ( reason ) {
					setThread( session.messages );
					setPrompt( text );
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
					setThread( shown );
					setPhase( 'error' );
				}
			} finally {
				sending.current = false;
			}
		},
		[ session, setPrompt ]
	);
	sendRef.current = send;

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
				setPendingSend( { text } );
				filesRef.current.add( picked );
				return;
			}
			void sendRef.current( text );
		},
		[]
	);

	useEffect( () => {
		onReady( { ask: bridgeAsk } );
	}, [ onReady, bridgeAsk ] );

	function cardStatus( productId: number, state: CardState, text: string ) {
		setCardStates( ( items ) => {
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
		cardStatus( productId, 'pending', __( 'Adding…', 'linker-tools' ) );
		await store.addAll( [ { productId, quantity: 1 } ], ( id, state ) =>
			cardStatus(
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
	}

	async function saveCardSolution( productId: number, title: string ) {
		cardStatus( productId, 'pending', __( 'Saving…', 'linker-tools' ) );
		try {
			await saveSolution( config.restUrl, config.restNonce, {
				kind: 'residential',
				title,
				input: {
					locale,
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
			cardStatus(
				productId,
				'added',
				__( 'Saved to your account.', 'linker-tools' )
			);
		} catch {
			cardStatus(
				productId,
				'retry',
				__( 'Not saved. Try again.', 'linker-tools' )
			);
		}
	}

	const blocks: Block[] = turn?.blocks ?? [];
	const cardIds = idsOf( blocks, 'cards' );
	const compareIds = idsOf( blocks, 'compare' );
	const cardPrices = pricesOf( blocks );
	const hasCompare = blocks.some( ( block ) => 'compare' === block.type );
	const hasCards = blocks.some( ( block ) => 'cards' === block.type );

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
			{ thread.length > 0 ? (
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
					{ 'error' === phase ? (
						<p role="alert" className="linker-genie-app__error">
							{ __(
								'Genie did not answer. Please try again.',
								'linker-tools'
							) }
						</p>
					) : null }
					{ 'waiting' !== phase
						? turn?.attachments?.map( ( card ) => (
								<AttachmentCard
									key={ card.id }
									card={ card }
									onAsk={ ( message ) =>
										bridgeAsk( message )
									}
									onTypeModel={ () => {
										setPrompt(
											sprintf(
												// translators: %s stays empty: the customer types the model after the words.
												__(
													'My device is the %s',
													'linker-tools'
												),
												''
											)
										);
										focusPrompt();
									} }
									onPhoto={ () => requestPicker( 'photo' ) }
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
								onAsk={ ( message ) => bridgeAsk( message ) }
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
									status={
										cardStates.find(
											( item ) =>
												item.productId === productId
										)?.status ?? {
											state: 'idle',
											text: '',
										}
									}
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
				</Transcript>
			) : null }
			<AttachmentChips
				picked={ files.picked }
				onRemove={ files.remove }
			/>
			{ refused ? (
				<p role="alert" className="linker-genie-app__refused">
					{ refused }
				</p>
			) : null }
		</div>
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

/**
 * The product ids of the turn's card or comparison block.
 *
 * @param blocks The turn's blocks.
 * @param kind   Which block.
 */
function idsOf( blocks: Block[], kind: 'cards' | 'compare' ): number[] {
	for ( const block of blocks ) {
		if ( block.type === kind ) {
			return ( block as CardsBlock | CompareBlock ).product_ids;
		}
	}
	return [];
}
