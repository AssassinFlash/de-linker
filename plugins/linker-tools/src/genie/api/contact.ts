/**
 * "Let Linker contact me" (#243): the contact card's route
 * (includes/Genie/ContactRequest.php).
 *
 * GET tells the card what it needs when it appears: the conversation revision, the
 * signed-in customer's address (never asked again) and whether this
 * conversation's request is already with the team, and the team mailbox
 * customers see (for a refusal). POST passes the
 * conversation on to the team.
 */

/**
 * Internal dependencies
 */
import type { Locale } from '../../configurator/types';
import type { ContactReason, PageContext } from './turn';

type Fetch = typeof fetch;

export interface ContactState {
	source: string;
	/** The signed-in customer's address; null for a guest. */
	email: string | null;
	/** The request already with the team, when nothing was said since. */
	sent: { email: string; receipt: boolean | null } | null;
	/** The team mailbox customers see, named when a request is refused. */
	mailbox: string;
}

/** Why a request did not go out; the card turns each into its sentence. */
export type ContactFailure =
	'email' | 'consent' | 'retry' | 'limited' | 'unavailable';

export type ContactResult =
	| { ok: true; email: string; receipt: boolean | null }
	| { ok: false; failure: ContactFailure; unconfirmed?: true };

/**
 * The card's state from the route; null when the route cannot be read.
 *
 * @param url     The contact route.
 * @param nonce   wp_rest nonce.
 * @param fetcher Fetch for tests.
 */
export async function readContact(
	url: string,
	nonce: string,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< ContactState | null > {
	try {
		const response = await fetcher( url, {
			credentials: 'same-origin',
			cache: 'no-store',
			headers: nonce ? { 'X-WP-Nonce': nonce } : undefined,
		} );
		if ( ! response.ok ) {
			return null;
		}
		const body = ( await response.json() ) as Partial< ContactState >;
		return {
			source: typeof body.source === 'string' ? body.source : '',
			email: typeof body.email === 'string' ? body.email : null,
			sent:
				body.sent && typeof body.sent.email === 'string'
					? {
							email: body.sent.email,
							receipt:
								typeof body.sent.receipt === 'boolean'
									? body.sent.receipt
									: null,
						}
					: null,
			mailbox: typeof body.mailbox === 'string' ? body.mailbox : '',
		};
	} catch {
		return null;
	}
}

/**
 * Sends the request to the team.
 *
 * @param url             The contact route.
 * @param nonce           wp_rest nonce.
 * @param request         What the card sends.
 * @param request.source  The stored conversation revision the customer reviewed.
 * @param request.email   A guest's address; omitted for a signed-in customer.
 * @param request.website The honeypot's value (empty for a person).
 * @param request.consent A guest's consent, the site's public doors' own.
 * @param request.reason  Why Genie offered the contact.
 * @param request.locale  The page's language.
 * @param request.page    The page context the turn carried.
 * @param fetcher         Fetch for tests.
 */
export async function sendContact(
	url: string,
	nonce: string,
	request: {
		source: string;
		'cf-turnstile-response'?: string;
		email?: string;
		website: string;
		consent?: '1';
		reason: ContactReason;
		locale: Locale;
		page: PageContext;
	},
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< ContactResult > {
	try {
		const response = await fetcher( url, {
			method: 'POST',
			credentials: 'same-origin',
			cache: 'no-store',
			headers: {
				'Content-Type': 'application/json',
				...( nonce ? { 'X-WP-Nonce': nonce } : {} ),
			},
			body: JSON.stringify( request ),
		} );
		const body = ( await response.json().catch( () => ( {} ) ) ) as {
			sent?: boolean;
			email?: string;
			code?: string;
			receipt?: boolean | null;
		};
		if ( response.ok ) {
			if (
				body.sent !== true ||
				typeof body.email !== 'string' ||
				! body.email
			) {
				return { ok: false, failure: 'unavailable', unconfirmed: true };
			}
			return {
				ok: true,
				email: body.email,
				receipt:
					typeof body.receipt === 'boolean' ? body.receipt : null,
			};
		}
		const failures: Record< string, ContactFailure > = {
			linker_genie_contact_email: 'email',
			linker_genie_contact_consent: 'consent',
			linker_genie_contact_retry: 'retry',
			linker_genie_contact_limited: 'limited',
		};
		return {
			ok: false,
			failure: failures[ body.code ?? '' ] ?? 'unavailable',
		};
	} catch {
		return { ok: false, failure: 'unavailable', unconfirmed: true };
	}
}
