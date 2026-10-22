/**
 * "Email me this conversation" under the transcript (ticket #235,
 * docs/specs/13-genie.md goal 7, acceptance A12): a signed-in customer's goes
 * is saved for automatic checks; a guest types the address and gets a
 * confirmation link there first. The outcome stays in place as a status line.
 */

/**
 * WordPress dependencies
 */
import { useState } from '@wordpress/element';
import { __, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { emailOutcome, type EmailOutcome } from '../api/turn';
import { MailIcon } from './Icons';

type Phase = 'idle' | 'form' | 'sending' | EmailOutcome;

/**
 * @param root0
 * @param root0.phase    Where the request stands.
 * @param root0.to       The address it concerns.
 * @param root0.limit    Emails per hour, named when the limit is reached.
 * @param root0.onStart  The action button.
 * @param root0.onCancel The guest form's cancel.
 * @param root0.onSend   The guest form's send: the typed address and the honeypot.
 */
export function EmailConversation( {
	phase,
	to,
	limit,
	onStart,
	onCancel,
	onSend,
}: {
	phase: Phase;
	to: string;
	limit: number;
	onStart: () => void;
	onCancel: () => void;
	onSend: ( address: string, website: string ) => void;
} ) {
	const [ address, setAddress ] = useState( to );
	// The honeypot: hidden from people, so only a bot fills it.
	const [ website, setWebsite ] = useState( '' );
	const status = statusText( phase, to, limit );
	return (
		<div className="linker-genie-app__email">
			{ 'form' === phase || 'invalid' === phase ? (
				<form
					className="linker-genie-app__email-form"
					onSubmit={ ( event ) => {
						event.preventDefault();
						onSend( address.trim(), website );
					} }
				>
					<label
						className="linker-genie-app__email-label"
						htmlFor="linker-genie-email"
					>
						{ __( 'Your email address', 'linker-tools' ) }
					</label>
					<div className="linker-genie-app__email-row">
						<input
							id="linker-genie-email"
							className="linker-genie-app__email-input"
							type="email"
							autoComplete="email"
							required
							value={ address }
							onChange={ ( event ) =>
								setAddress( event.target.value )
							}
						/>
						<div hidden aria-hidden="true">
							<input
								type="text"
								name="website"
								tabIndex={ -1 }
								autoComplete="off"
								value={ website }
								onChange={ ( event ) =>
									setWebsite( event.target.value )
								}
							/>
						</div>
						<button
							type="submit"
							className="linker-genie-app__email-send"
						>
							{ __( 'Send email', 'linker-tools' ) }
						</button>
						<button
							type="button"
							className="linker-genie-app__email-cancel"
							onClick={ onCancel }
						>
							{ __( 'Cancel', 'linker-tools' ) }
						</button>
					</div>
				</form>
			) : (
				<button
					type="button"
					className="linker-genie-app__email-start"
					disabled={ 'sending' === phase || 'pending' === phase }
					onClick={ onStart }
				>
					<MailIcon size={ 16 } />
					{ __( 'Email me this conversation', 'linker-tools' ) }
				</button>
			) }
			{ status ? (
				<p
					className="linker-genie-app__email-status"
					role={
						'sent' === phase ||
						'confirm' === phase ||
						'pending' === phase ||
						'sending' === phase
							? 'status'
							: 'alert'
					}
				>
					{ status }
				</p>
			) : null }
		</div>
	);
}

/**
 * The status line of one phase, '' when there is none.
 *
 * @param phase Where the request stands.
 * @param to    The address it concerns.
 * @param limit Emails per hour one connection may ask for.
 */
function statusText( phase: Phase, to: string, limit: number ): string {
	switch ( phase ) {
		case 'idle':
		case 'form':
			return '';
		case 'sending':
			return __( 'Sending…', 'linker-tools' );
		case 'pending':
			return __(
				'Your email request is saved and awaiting automatic checks. You do not need to submit it again.',
				'linker-tools'
			);
		case 'sent':
			// The Outbox sends at once or queues for the next free slot, so
			// "on its way" rather than "sent".
			return sprintf(
				// translators: %s is the email address the conversation goes to.
				__( 'Your email to %s is on its way.', 'linker-tools' ),
				to
			);
		case 'confirm':
			return sprintf(
				// translators: %s is the email address the confirmation link went to.
				__(
					'A confirmation link is on its way to %s.',
					'linker-tools'
				),
				to
			);
		case 'invalid':
			return __( 'Please enter a valid email address.', 'linker-tools' );
		case 'throttled':
			return sprintf(
				// translators: %d is how many emails one connection may ask for per hour (ConversationMail::LIMIT).
				__(
					'This connection has reached the limit of %d emails per hour. Please try again later.',
					'linker-tools'
				),
				limit
			);
		case 'capped':
			return __(
				"Today's email limit has been reached. Please try again tomorrow.",
				'linker-tools'
			);
		default:
			return __(
				'The email could not be sent. Please try again.',
				'linker-tools'
			);
	}
}

/**
 * The page a confirmation link opens says how it went: the link's handler
 * (ConversationMail::handle_link()) adds `genie_email=<outcome>` to Genie's
 * page. The argument is read once and taken out of the address, so a reload
 * does not say it again.
 */
export function readLinkResult(): EmailOutcome | null {
	const params = new URLSearchParams( window.location.search );
	const word = params.get( 'genie_email' );
	if ( null === word ) {
		return null;
	}
	params.delete( 'genie_email' );
	const query = params.toString();
	window.history.replaceState(
		window.history.state,
		'',
		`${ window.location.pathname }${ query ? `?${ query }` : '' }${
			window.location.hash
		}`
	);
	return emailOutcome( word );
}

/**
 * The notice of a confirmation link's outcome.
 *
 * @param outcome         How the link ended.
 * @param outcome.outcome
 */
export function LinkResult( { outcome }: { outcome: EmailOutcome } ) {
	return (
		<p
			className="linker-genie-app__notice"
			role={
				'sent' === outcome || 'pending' === outcome ? 'status' : 'alert'
			}
		>
			{ linkResultText( outcome ) }
		</p>
	);
}

/**
 * The words of one link outcome.
 *
 * @param outcome How the link ended.
 */
function linkResultText( outcome: EmailOutcome ): string {
	switch ( outcome ) {
		case 'pending':
			return __(
				'Your email request is saved and awaiting automatic checks. You do not need to submit it again.',
				'linker-tools'
			);
		case 'sent':
			return __(
				'Email address confirmed. The conversation is on its way.',
				'linker-tools'
			);
		case 'expired':
			return __(
				'This link has expired or has already been used.',
				'linker-tools'
			);
		case 'capped':
			return __(
				"Today's email limit has been reached. Please try again tomorrow.",
				'linker-tools'
			);
		default:
			return __(
				'The email could not be sent. Please try again.',
				'linker-tools'
			);
	}
}
