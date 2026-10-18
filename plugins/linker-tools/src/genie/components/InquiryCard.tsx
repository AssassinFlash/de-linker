/**
 * The inquiry confirmation card (#250, docs/specs/13-genie.md goal 5).
 *
 * Genie drafts the inquiry; this card shows every line that will be sent — the
 * solution draft's products and quantities, the message, whether #244's
 * conversation summary goes with it, and the one-business-day reply promise —
 * and only its Send button sends. The route is the one writer (InquiryRequest);
 * the model cannot send, and a model sentence claiming it did is refused by the
 * service's grounding (A8).
 *
 * A guest gives the request page's own required details (name, reply address,
 * consent); a signed-in customer's come from the account. When the draft is
 * empty the card says so and names the request page, where the draft and the
 * message are prefilled: it never invents a line. Copy review:
 * docs/acceptance/2026-10-18/250/copy-review.md.
 */

/**
 * WordPress dependencies
 */
import { useEffect, useId, useRef, useState } from '@wordpress/element';
import { __, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { Locale } from '../../configurator/types';
import type { PageContext } from '../api/turn';
import {
	readInquiry,
	sendInquiry,
	type InquiryFailure,
	type InquiryState,
	type SentInquiry,
} from '../api/inquiry';

type Phase = 'loading' | 'ready' | 'sending';

/**
 * The four inquiry statuses, in the page's language (the slugs are the record's
 * own; AGENTS.md §3 fixes the German words).
 *
 * @param status WooCommerce status without the `wc-` prefix.
 */
export function statusLabel( status: string ): string {
	switch ( status ) {
		case 'inquiry-received':
			return __( 'Inquiry received', 'linker-tools' );
		case 'proforma-issued':
			return __( 'Proforma invoice issued', 'linker-tools' );
		case 'completed':
			return __( 'Completed', 'linker-tools' );
		case 'cancelled':
			return __( 'Cancelled', 'linker-tools' );
		case 'pending':
			return __( 'Not sent', 'linker-tools' );
		default:
			return '';
	}
}

/**
 * The sent inquiry: the card's own confirmation, and the record of an inquiry
 * the conversation keeps after later turns and a reload.
 *
 * @param props         The sent inquiry.
 * @param props.inquiry The record's number, status and address.
 */
export function InquirySent( { inquiry }: { inquiry: SentInquiry } ) {
	const label = statusLabel( inquiry.status );
	return (
		<section className="linker-genie-inquiry linker-genie-inquiry--sent">
			<p className="linker-genie-inquiry__title">
				{ __( 'Your inquiry is with the Linker team', 'linker-tools' ) }
			</p>
			<p className="linker-genie-inquiry__status">
				{ label
					? sprintf(
							/* translators: 1: inquiry number, 2: the inquiry's status. */
							__( 'Inquiry #%1$s · %2$s', 'linker-tools' ),
							inquiry.number,
							label
						)
					: sprintf(
							/* translators: %s: inquiry number. */
							__( 'Inquiry #%s', 'linker-tools' ),
							inquiry.number
						) }
			</p>
			<p className="linker-genie-inquiry__text">
				{ __(
					'The team replies within one business day.',
					'linker-tools'
				) }
			</p>
			{ inquiry.receipt ? null : (
				<p className="linker-genie-inquiry__text">
					{ __(
						'We have not sent a confirmation email.',
						'linker-tools'
					) }
				</p>
			) }
			{ inquiry.url ? (
				<p className="linker-genie-inquiry__text">
					<a
						className="linker-genie-inquiry__link"
						href={ inquiry.url }
					>
						{ __( 'View your inquiry', 'linker-tools' ) }
					</a>
				</p>
			) : null }
			<p className="linker-genie-inquiry__text">
				{ __(
					'Genie keeps answering your questions in the meantime.',
					'linker-tools'
				) }
			</p>
		</section>
	);
}

/**
 * Why the inquiry did not go out, and where the customer can still send it.
 *
 * @param failure Why.
 * @param pageUrl The request page, '' when the route named none.
 */
function failureText( failure: InquiryFailure, pageUrl: string ): string {
	switch ( failure ) {
		case 'name':
			return __( 'Please add your name.', 'linker-tools' );
		case 'email':
			return __(
				'Please add an email address we can reply to.',
				'linker-tools'
			);
		case 'consent':
			return __(
				'Please agree to the use of your details for the reply.',
				'linker-tools'
			);
		case 'changed':
			return __(
				'Your solution draft changed. Check the lines and send the inquiry again.',
				'linker-tools'
			);
		case 'empty':
			return __(
				'Add a product to your solution draft or write a message.',
				'linker-tools'
			);
		case 'limited':
			return __(
				'Genie cannot send an inquiry right now. Please use the inquiry page.',
				'linker-tools'
			);
		case 'refused':
			return __(
				'The inquiry could not be sent. Please check your solution draft on the inquiry page.',
				'linker-tools'
			);
		case 'unavailable':
			// The same sentence as the limit: either way the page is the way out.
			return __(
				'Genie cannot send an inquiry right now. Please use the inquiry page.',
				'linker-tools'
			);
		default:
			return pageUrl
				? __(
						'Sending did not work. Please try again, or use the inquiry page.',
						'linker-tools'
					)
				: __(
						'Sending did not work. Please try again.',
						'linker-tools'
					);
	}
}

export interface InquiryCardProps {
	inquiryUrl: string;
	nonce: string;
	locale: Locale;
	/** The page the card stands on (kept with the conversation's note). */
	page?: PageContext;
	/** The inquiry is with the team: the conversation keeps the sent card. */
	onSent?: ( inquiry: SentInquiry ) => void;
	/** Fetch for tests. */
	fetcher?: typeof fetch;
}

export function InquiryCard( {
	inquiryUrl,
	nonce,
	locale,
	page,
	onSent,
	fetcher,
}: InquiryCardProps ) {
	const [ phase, setPhase ] = useState< Phase >( 'loading' );
	const [ state, setState ] = useState< InquiryState | null >( null );
	const [ name, setName ] = useState( '' );
	const [ email, setEmail ] = useState( '' );
	const [ company, setCompany ] = useState( '' );
	const [ message, setMessage ] = useState( '' );
	const [ attach, setAttach ] = useState( true );
	const [ consent, setConsent ] = useState( false );
	const [ trap, setTrap ] = useState( '' );
	const [ sent, setSent ] = useState< SentInquiry | null >( null );
	const [ failure, setFailure ] = useState< InquiryFailure | null >( null );
	const nameField = useId();
	const emailField = useId();
	const companyField = useId();
	const messageField = useId();
	const summaryField = useId();
	const consentField = useId();
	const notify = useRef( onSent );
	notify.current = onSent;

	useEffect( () => {
		let live = true;
		readInquiry( inquiryUrl, nonce, locale, fetcher ).then( ( read ) => {
			if ( ! live ) {
				return;
			}
			setState( read );
			if ( ! read ) {
				setFailure( 'unavailable' );
				setPhase( 'ready' );
				return;
			}
			setName( read.account?.name ?? '' );
			setEmail( read.account?.email ?? '' );
			setCompany( read.account?.company ?? '' );
			setMessage( read.message );
			setAttach( '' !== read.summary );
			if ( read.sent ) {
				setSent( read.sent );
				notify.current?.( read.sent );
			}
			setPhase( 'ready' );
		} );
		return () => {
			live = false;
		};
	}, [ inquiryUrl, nonce, locale, fetcher ] );

	const account = state?.account ?? null;
	const lines = state?.lines ?? [];
	const empty = 0 === lines.length && '' === message.trim();

	async function submit( event: { preventDefault: () => void } ) {
		event.preventDefault();
		if ( 'ready' !== phase || ! state ) {
			return;
		}
		setFailure( null );
		if ( empty ) {
			setFailure( 'empty' );
			return;
		}
		if ( ! account ) {
			if ( '' === name.trim() ) {
				setFailure( 'name' );
				return;
			}
			if ( '' === email.trim() ) {
				setFailure( 'email' );
				return;
			}
			if ( ! consent ) {
				setFailure( 'consent' );
				return;
			}
		}
		setPhase( 'sending' );
		const result = await sendInquiry(
			inquiryUrl,
			nonce,
			{
				...( account
					? {}
					: {
							name: name.trim(),
							email: email.trim(),
							company: company.trim(),
							...( consent ? { consent: '1' as const } : {} ),
						} ),
				message: message.trim(),
				attachSummary: attach && '' !== state.summary,
				lines: state.linesDigest,
				website: trap,
				started: state.started,
				started_nonce: state.startedNonce,
				locale,
				...( page ? { page } : {} ),
			},
			fetcher
		);
		if ( result.ok ) {
			setSent( result.inquiry );
			setPhase( 'ready' );
			notify.current?.( result.inquiry );
			return;
		}
		setFailure( result.failure );
		setPhase( 'ready' );
		if ( 'changed' === result.failure ) {
			// The card shows the draft that moved, so the next send is the new
			// one; the customer's message stays as typed.
			const again = await readInquiry(
				inquiryUrl,
				nonce,
				locale,
				fetcher
			);
			if ( again ) {
				setState( again );
				if ( again.sent ) {
					setSent( again.sent );
					notify.current?.( again.sent );
				}
			}
		}
	}

	if ( sent ) {
		return <InquirySent inquiry={ sent } />;
	}

	const sending = 'sending' === phase;
	const loading = 'loading' === phase;
	const canSend = ! loading && ! sending && ! empty;

	// One live region for the card's life: the move to the sent card is
	// announced (a region mounted together with its content is not).
	return (
		<section
			className="linker-genie-inquiry"
			aria-live="polite"
			aria-busy={ loading || sending }
		>
			<p className="linker-genie-inquiry__title">
				{ __( 'Your inquiry', 'linker-tools' ) }
			</p>
			<p className="linker-genie-inquiry__text">
				{ __(
					'Check the details and send the inquiry to the Linker team.',
					'linker-tools'
				) }
			</p>
			{ lines.length > 0 ? (
				<>
					<p className="linker-genie-inquiry__label">
						{ __( 'Products and quantities', 'linker-tools' ) }
					</p>
					<ul className="linker-genie-inquiry__lines">
						{ lines.map( ( line ) => (
							<li
								key={ line.product_id }
								className="linker-genie-inquiry__line"
							>
								<span className="linker-genie-inquiry__product">
									{ line.url ? (
										<a href={ line.url }>{ line.name }</a>
									) : (
										line.name
									) }
									{ line.sku ? (
										<small className="linker-genie-inquiry__sku">
											{ line.sku }
										</small>
									) : null }
								</span>
								<span className="linker-genie-inquiry__quantity">
									{ sprintf(
										/* translators: %d: quantity of a product in the solution draft. */
										__( '× %d', 'linker-tools' ),
										line.quantity
									) }
								</span>
								<span
									className="linker-genie-inquiry__price"
									dangerouslySetInnerHTML={ {
										__html: line.price_html,
									} }
								/>
							</li>
						) ) }
					</ul>
				</>
			) : (
				<p className="linker-genie-inquiry__text linker-genie-inquiry__empty">
					{ __(
						'No products in your solution draft.',
						'linker-tools'
					) }
				</p>
			) }
			<label
				className="linker-genie-inquiry__label"
				htmlFor={ messageField }
			>
				{ __( 'Message', 'linker-tools' ) }
			</label>
			<textarea
				id={ messageField }
				className="linker-genie-inquiry__message"
				rows={ 4 }
				maxLength={ 5000 }
				value={ message }
				onChange={ ( event ) => setMessage( event.target.value ) }
			/>
			{ '' !== ( state?.summary ?? '' ) ? (
				<div className="linker-genie-inquiry__summary">
					<div className="linker-genie-inquiry__switch">
						<input
							id={ summaryField }
							type="checkbox"
							checked={ attach }
							onChange={ ( event ) =>
								setAttach( event.target.checked )
							}
						/>
						<label htmlFor={ summaryField }>
							{ __(
								'Attach the conversation summary',
								'linker-tools'
							) }
						</label>
					</div>
					<details className="linker-genie-inquiry__details">
						<summary>
							{ __( 'Read the summary', 'linker-tools' ) }
						</summary>
						<p>{ state?.summary }</p>
					</details>
				</div>
			) : null }
			{ account ? null : (
				<div className="linker-genie-inquiry__fields">
					<label
						className="linker-genie-inquiry__field"
						htmlFor={ nameField }
					>
						<span>{ __( 'Name', 'linker-tools' ) }</span>
						<input
							id={ nameField }
							type="text"
							autoComplete="name"
							maxLength={ 190 }
							value={ name }
							onChange={ ( event ) =>
								setName( event.target.value )
							}
							aria-invalid={ 'name' === failure }
						/>
					</label>
					<label
						className="linker-genie-inquiry__field"
						htmlFor={ emailField }
					>
						<span>{ __( 'Reply email', 'linker-tools' ) }</span>
						<input
							id={ emailField }
							type="email"
							autoComplete="email"
							maxLength={ 190 }
							value={ email }
							onChange={ ( event ) =>
								setEmail( event.target.value )
							}
							aria-invalid={ 'email' === failure }
						/>
					</label>
					<label
						className="linker-genie-inquiry__field"
						htmlFor={ companyField }
					>
						<span>
							{ __( 'Company (optional)', 'linker-tools' ) }
						</span>
						<input
							id={ companyField }
							type="text"
							autoComplete="organization"
							maxLength={ 190 }
							value={ company }
							onChange={ ( event ) =>
								setCompany( event.target.value )
							}
						/>
					</label>
					<div className="linker-genie-inquiry__consent">
						<input
							id={ consentField }
							type="checkbox"
							checked={ consent }
							onChange={ ( event ) =>
								setConsent( event.target.checked )
							}
							aria-invalid={ 'consent' === failure }
						/>
						<label htmlFor={ consentField }>
							{ __(
								'I agree that my details may be used to respond to this message.',
								'linker-tools'
							) }
						</label>
					</div>
				</div>
			) }
			{ /* The honeypot: people never see it, bots fill it in. */ }
			<div className="linker-genie-inquiry__trap" aria-hidden="true">
				<input
					type="text"
					name="website"
					tabIndex={ -1 }
					autoComplete="off"
					value={ trap }
					onChange={ ( event ) => setTrap( event.target.value ) }
				/>
			</div>
			{ empty ? (
				<p className="linker-genie-inquiry__hint">
					{ __(
						'Add a product to your solution draft or write a message.',
						'linker-tools'
					) }
				</p>
			) : null }
			<div className="linker-genie-inquiry__actions">
				<button
					type="button"
					className="linker-genie-inquiry__send"
					disabled={ ! canSend }
					onClick={ submit }
				>
					{ sending
						? __( 'Sending…', 'linker-tools' )
						: __( 'Send inquiry', 'linker-tools' ) }
				</button>
				{ state?.pageUrl ? (
					<a
						className="linker-genie-inquiry__edit"
						href={ state.pageUrl }
					>
						{ __( 'Open the inquiry page', 'linker-tools' ) }
					</a>
				) : null }
			</div>
			<p className="linker-genie-inquiry__promise">
				{ __( 'We reply within one business day.', 'linker-tools' ) }
			</p>
			{ failure ? (
				<p role="alert" className="linker-genie-inquiry__error">
					{ failureText( failure, state?.pageUrl ?? '' ) }
				</p>
			) : null }
		</section>
	);
}
