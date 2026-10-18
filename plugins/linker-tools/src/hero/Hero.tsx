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
import type { SentInquiry } from '../genie/api/inquiry';
import {
	assistantMessage,
	type Block,
	type ContactBlock,
	type SentContact,
	type SentInquiryCard,
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
import { ContactCard, ContactSent } from '../genie/components/ContactCard';
import { GenieCard } from '../genie/components/GenieCard';
import { InquiryCard, InquirySent } from '../genie/components/InquiryCard';
import { Reply } from '../genie/components/Reply';
import { Transcript } from '../genie/components/Transcript';
import type { GenieConfig } from '../genie/config';
import { idsOf, pricesOf } from '../genie/shared/blocks';
import { useCardActions } from '../genie/shared/cardActions';
import {
	attachmentRefusalReason,
	buildQuestion,
	typeModelPrompt,
} from '../genie/shared/conversation';
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
	/** Opens the page's file picker. */
	requestPicker: () => void;
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
	const closeRef = useRef< HTMLButtonElement >( null );
	const files = useAttachments();
	// The bridge is registered once; the refs keep it calling the latest
	// render's send and file state.
	const filesRef = useRef( files );
	filesRef.current = files;
	const sendRef = useRef< ( text: string ) => void >( () => undefined );
	const [ store ] = useState( () => storeClient( config.restUrl ) );
	const {
		statusFor,
		addToDraft: addCardToDraft,
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
		let cancelled = false;
		void session
			.load()
			.then( ( stored ) => {
				if ( ! cancelled ) {
					setThread( stored.messages );
					setTurn( stored.turn );
					setContacts( stored.contacts ?? [] );
					setInquiries( stored.inquiries ?? [] );
					turnAt.current = stored.turn
						? stored.messages.length - 1
						: -1;
				}
			} )
			.catch( () => undefined );
		return () => {
			cancelled = true;
		};
	}, [ session ] );

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

	const send = useCallback(
		async ( text: string ) => {
			const picked = filesRef.current.uploads;
			const question = buildQuestion( text, picked );
			if ( ! question || sending.current || filesRef.current.busy ) {
				return;
			}
			sending.current = true;
			setRefused( '' );
			setLive( '' );
			setPhase( 'waiting' );
			setPrompt( '' );
			let shown: TurnMessage[] = [];
			try {
				shown = [
					...session.messages,
					{ role: 'user', content: question },
				];
				setThread( shown );
				// session.ask re-reads the shared thread before it sends, so
				// a dock turn is neither lost nor overwritten (session.ts).
				const result = await session.ask( question, picked );
				filesRef.current.clear();
				setThread( result.messages );
				setTurn( result.answer );
				setContacts( result.contacts ?? [] );
				setInquiries( result.inquiries ?? [] );
				turnAt.current = result.messages.length - 1;
				setLive( assistantMessage( result.answer ).content );
				setPhase( 'ask' );
			} catch ( error ) {
				// A file the proxy refused is said as such and the question
				// goes back into the field; anything else is no answer, and
				// the question stays so the error has something to stand under.
				const reason = attachmentRefusalReason( error );
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
				{ live }
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
										setPrompt( typeModelPrompt() );
										focusPrompt();
									} }
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
