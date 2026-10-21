/**
 * "Let Linker contact me" (#243): the contact card's route
 * (includes/Genie/ContactRequest.php).
 *
 * GET tells the card what it needs when it appears: a signed start time, the
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

import { resourceFetch } from '../../protection/request';

type Fetch = typeof fetch;

export interface ContactState {
	/** The signed start time the request sends back (FormGuard). */
	started: string;
	/** Its signature. */
	startedNonce: string;
	/** The signed-in customer's address; null for a guest. */
	email: string | null;
	/** The request already with the team, when nothing was said since. */
	sent: { email: string; receipt: boolean } | null;
	/** The team mailbox customers see, named when a request is refused. */
	mailbox: string;
}

/** Why a request did not go out; the card turns each into its sentence. */
export type ContactFailure =
	'email' | 'consent' | 'retry' | 'limited' | 'unavailable';

export type ContactResult =
	| { ok: true; email: string; receipt: boolean }
	| { ok: false; failure: ContactFailure };

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
		const response = await resourceFetch( fetcher, url, {
			credentials: 'same-origin',
			cache: 'no-store',
			headers: { 'X-WP-Nonce': nonce },
		} );
		if ( ! response.ok ) {
			return null;
		}
		const body = ( await response.json() ) as Partial< ContactState > & {
			started_nonce?: unknown;
		};
		return {
			started: typeof body.started === 'string' ? body.started : '',
			startedNonce:
				typeof body.started_nonce === 'string'
					? body.started_nonce
					: '',
			email: typeof body.email === 'string' ? body.email : null,
			sent:
				body.sent && typeof body.sent.email === 'string'
					? {
							email: body.sent.email,
							receipt: false !== body.sent.receipt,
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
 * @param url                   The contact route.
 * @param nonce                 wp_rest nonce.
 * @param request               What the card sends.
 * @param request.email         A guest's address; omitted for a signed-in customer.
 * @param request.website       The honeypot's value (empty for a person).
 * @param request.started       The signed start time readContact() returned.
 * @param request.started_nonce Its signature.
 * @param request.consent       A guest's consent, the site's public doors' own.
 * @param request.reason        Why Genie offered the contact.
 * @param request.locale        The page's language.
 * @param request.page          The page context the turn carried.
 * @param fetcher               Fetch for tests.
 */
export async function sendContact(
	url: string,
	nonce: string,
	request: {
		email?: string;
		website: string;
		started: string;
		started_nonce: string;
		consent?: '1';
		reason: ContactReason;
		locale: Locale;
		page: PageContext;
	},
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< ContactResult > {
	try {
		const response = await resourceFetch( fetcher, url, {
			method: 'POST',
			credentials: 'same-origin',
			cache: 'no-store',
			headers: {
				'Content-Type': 'application/json',
				'X-WP-Nonce': nonce,
			},
			body: JSON.stringify( request ),
		} );
		const body = ( await response.json().catch( () => ( {} ) ) ) as {
			email?: string;
			code?: string;
			receipt?: boolean;
		};
		if ( response.ok ) {
			return {
				ok: true,
				email: body.email ?? request.email ?? '',
				receipt: false !== body.receipt,
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
		return { ok: false, failure: 'unavailable' };
	}
}
