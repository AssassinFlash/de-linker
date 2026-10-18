/**
 * "Let Linker contact me" (#243, docs/specs/13-genie.md goal 6): the card the
 * service's contact block becomes.
 *
 * A signed-in customer is never asked for an address: the card names the
 * account's and sends with one click. A guest leaves an email address; the
 * route guards it as a public form (a hidden honeypot field and a signed
 * start time the card fetches when it appears). The card promises a reply
 * within one business day (AGENTS.md 2026-10-09) and says Genie keeps
 * answering: the offer never mutes the assistant. Copy review:
 * docs/acceptance/2026-10-18/243/copy-review.md.
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
import {
	readContact,
	sendContact,
	type ContactFailure,
	type ContactState,
} from '../api/contact';
import type { ContactBlock, PageContext } from '../api/turn';

type Phase = 'loading' | 'ready' | 'sending' | 'sent';

export interface ContactCardProps {
	block: ContactBlock;
	contactUrl: string;
	nonce: string;
	locale: Locale;
	page: PageContext;
	/**
	 * The request is with the team (sent now, or found sent when the card
	 * appeared): the conversation keeps the sent card in its history.
	 */
	onSent?: ( email: string, receipt: boolean ) => void;
	/** Fetch for tests. */
	fetcher?: typeof fetch;
}

/**
 * The sent card: the confirmation a request is with the team. It stays in the
 * conversation's history after the answer that offered it, on later turns and
 * after a reload (review round 1 of #243).
 *
 * @param props         The card.
 * @param props.email   Where the team replies.
 * @param props.receipt False when the site's receipt cap held the receipt back.
 */
export function ContactSent( {
	email,
	receipt = true,
}: {
	email: string;
	receipt?: boolean;
} ) {
	return (
		<section className="linker-genie-contact">
			<p className="linker-genie-contact__title">
				{ __( 'Your request is with the Linker team', 'linker-tools' ) }
			</p>
			<p className="linker-genie-contact__text">{ replyText( email ) }</p>
			{ receipt ? null : (
				<p className="linker-genie-contact__text">
					{ __(
						'We have not sent a confirmation email.',
						'linker-tools'
					) }
				</p>
			) }
			<p className="linker-genie-contact__text">
				{ __(
					'Genie keeps answering your questions in the meantime.',
					'linker-tools'
				) }
			</p>
		</section>
	);
}

/**
 * Why the request did not go out. A refused request must not dead-end: the
 * customer asked for a person, so the team mailbox is named when it is known.
 *
 * @param failure Why.
 * @param mailbox The team mailbox customers see, '' when unknown.
 */
function failureText( failure: ContactFailure, mailbox: string ): string {
	if ( 'email' === failure ) {
		return __( 'Please enter a valid email address.', 'linker-tools' );
	}
	if ( 'consent' === failure ) {
		return __(
			'Please agree to the use of your details for the reply.',
			'linker-tools'
		);
	}
	if ( 'retry' === failure ) {
		return __( 'Sending did not work. Please try again.', 'linker-tools' );
	}
	if ( mailbox ) {
		return sprintf(
			/* translators: %s: the team mailbox, e.g. sales@de-linker.com. */
			__(
				'Genie cannot pass on your request right now. Please try again later or write to %s.',
				'linker-tools'
			),
			mailbox
		);
	}
	return __(
		'Genie cannot pass on your request right now. Please try again later.',
		'linker-tools'
	);
}

/**
 * The reply rule, the same sentence before and after sending.
 *
 * @param email Where the team replies.
 */
function replyText( email: string ): string {
	return sprintf(
		/* translators: %s: the email address the team replies to. */
		__( 'The team replies to %s within one business day.', 'linker-tools' ),
		email
	);
}

export function ContactCard( {
	block,
	contactUrl,
	nonce,
	locale,
	page,
	onSent,
	fetcher,
}: ContactCardProps ) {
	const [ phase, setPhase ] = useState< Phase >( 'loading' );
	const [ state, setState ] = useState< ContactState | null >( null );
	const [ email, setEmail ] = useState( '' );
	const [ trap, setTrap ] = useState( '' );
	const [ sentTo, setSentTo ] = useState( '' );
	const [ receipt, setReceipt ] = useState( true );
	const [ consent, setConsent ] = useState( false );
	const [ failure, setFailure ] = useState< ContactFailure | null >( null );
	const field = useId();
	const consentField = useId();
	// The latest callback, read when the card's state arrives.
	const notify = useRef( onSent );
	notify.current = onSent;

	useEffect( () => {
		let live = true;
		readContact( contactUrl, nonce, fetcher ).then( ( read ) => {
			if ( ! live ) {
				return;
			}
			setState( read );
			if ( read?.sent ) {
				setSentTo( read.sent.email );
				setReceipt( read.sent.receipt );
				setPhase( 'sent' );
				notify.current?.( read.sent.email, read.sent.receipt );
				return;
			}
			setPhase( 'ready' );
			if ( ! read ) {
				setFailure( 'unavailable' );
			}
		} );
		return () => {
			live = false;
		};
	}, [ contactUrl, nonce, fetcher ] );

	const account = state?.email ?? null;
	const proactive =
		'dissatisfied' === block.reason || 'repeat' === block.reason;

	async function submit( event: { preventDefault: () => void } ) {
		event.preventDefault();
		if ( 'ready' !== phase ) {
			return;
		}
		setFailure( null );
		setPhase( 'sending' );
		const result = await sendContact(
			contactUrl,
			nonce,
			{
				...( account
					? {}
					: {
							email: email.trim(),
							...( consent ? { consent: '1' as const } : {} ),
						} ),
				website: trap,
				started: state?.started ?? '',
				started_nonce: state?.startedNonce ?? '',
				reason: block.reason,
				locale,
				page,
			},
			fetcher
		);
		if ( result.ok ) {
			setSentTo( result.email );
			setReceipt( result.receipt );
			setPhase( 'sent' );
			onSent?.( result.email, result.receipt );
			return;
		}
		setFailure( result.failure );
		setPhase( 'ready' );
	}

	const sent = 'sent' === phase;
	let title: string = __( 'Let the Linker team contact you', 'linker-tools' );
	if ( sent ) {
		title = __( 'Your request is with the Linker team', 'linker-tools' );
	} else if ( proactive ) {
		title = __(
			'Should someone from the Linker team get in touch?',
			'linker-tools'
		);
	}
	let text: string = __(
		'Leave your email address and the team replies within one business day.',
		'linker-tools'
	);
	if ( sent ) {
		text = replyText( sentTo );
	} else if ( account ) {
		text = replyText( account );
	}

	// One live region for the card's life, so the change to "sent" is
	// announced (a region mounted together with its content is not).
	return (
		<section className="linker-genie-contact" aria-live="polite">
			<p className="linker-genie-contact__title">{ title }</p>
			<p className="linker-genie-contact__text">{ text }</p>
			{ sent && ! receipt ? (
				<p className="linker-genie-contact__text">
					{ __(
						'We have not sent a confirmation email.',
						'linker-tools'
					) }
				</p>
			) : null }
			{ sent ? (
				<p className="linker-genie-contact__text">
					{ __(
						'Genie keeps answering your questions in the meantime.',
						'linker-tools'
					) }
				</p>
			) : (
				<form
					className="linker-genie-contact__form"
					onSubmit={ submit }
					noValidate
				>
					{ account ? null : (
						<>
							<label
								className="linker-genie-contact__label"
								htmlFor={ field }
							>
								{ __( 'Your email address', 'linker-tools' ) }
							</label>
							<input
								id={ field }
								className="linker-genie-contact__email"
								type="email"
								autoComplete="email"
								required
								value={ email }
								onChange={ ( event ) =>
									setEmail( event.target.value )
								}
								aria-invalid={ 'email' === failure }
							/>
							{ /* The consent the site's public doors ask a guest
							 * for (#246); an account's customer gave it. */ }
							<div className="linker-genie-contact__consent">
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
						</>
					) }
					{ /* The honeypot: people never see it, bots fill it in. */ }
					<div
						className="linker-genie-contact__trap"
						aria-hidden="true"
					>
						<input
							type="text"
							name="website"
							tabIndex={ -1 }
							autoComplete="off"
							value={ trap }
							onChange={ ( event ) =>
								setTrap( event.target.value )
							}
						/>
					</div>
					<button
						type="submit"
						className="linker-genie-contact__send"
						disabled={ 'ready' !== phase }
					>
						{ 'sending' === phase
							? __( 'Sending…', 'linker-tools' )
							: __( 'Contact me', 'linker-tools' ) }
					</button>
				</form>
			) }
			{ failure ? (
				<p role="alert" className="linker-genie-contact__error">
					{ failureText( failure, state?.mailbox ?? '' ) }
				</p>
			) : null }
		</section>
	);
}
