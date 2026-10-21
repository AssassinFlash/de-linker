/**
 * The inquiry confirmation card (#250): its route
 * (includes/Genie/InquiryRequest.php).
 *
 * GET states what the card would send — the solution draft's lines as the
 * request page shows them, the message (#244's note), the conversation summary,
 * whether this conversation's inquiry is already with the team, and the request
 * page for a draft that cannot send. POST sends exactly the card's lines through
 * the same Woo pipeline as the request page.
 */

/**
 * Internal dependencies
 */
import type { Locale } from '../../configurator/types';
import type { PageContext } from './turn';

import { resourceFetch } from '../../protection/request';

type Fetch = typeof fetch;

/** One line of the solution draft, as the request page lists it. */
export interface InquiryLine {
	product_id: number;
	name: string;
	sku: string;
	quantity: number;
	/** Woo's own price line, under the site's price rule (CARD surface). */
	price_html: string;
	url: string;
}

/** The signed-in customer's details; null for a guest. */
export interface InquiryAccount {
	email: string;
	name: string;
	company: string;
}

/** An inquiry the card sent, read from the record. */
export interface SentInquiry {
	order: number;
	number: string;
	/** The Woo status without the `wc-` prefix (InquiryRequest::STATUSES). */
	status: string;
	receipt: boolean;
	email: string;
	/** The account's inquiry view, or a guest's receipt. */
	url: string;
}

export interface InquiryState {
	conversation: number;
	/** The signed start time the send returns (FormGuard). */
	started: string;
	startedNonce: string;
	account: InquiryAccount | null;
	lines: InquiryLine[];
	/** The lines the card showed: a draft that moved is refused. */
	linesDigest: string;
	/** The message the card starts with (#244's note). */
	message: string;
	/** The conversation summary, '' when there is none. */
	summary: string;
	/** This conversation's inquiry, when nothing was said since it went out. */
	sent: SentInquiry | null;
	/** The request page, in the card's language (prefilled draft and message). */
	pageUrl: string;
}

/** Why the inquiry did not go out; the card turns each into its sentence. */
export type InquiryFailure =
	| 'name'
	| 'email'
	| 'consent'
	| 'retry'
	| 'changed'
	| 'empty'
	| 'refused'
	| 'limited'
	| 'unavailable';

export type InquiryResult =
	{ ok: true; inquiry: SentInquiry } | { ok: false; failure: InquiryFailure };

function sent( raw: unknown ): SentInquiry | null {
	if ( ! raw || typeof raw !== 'object' ) {
		return null;
	}
	const value = raw as Record< string, unknown >;
	if (
		typeof value.number !== 'string' ||
		typeof value.status !== 'string'
	) {
		return null;
	}
	return {
		order: Number( value.order ) || 0,
		number: value.number,
		status: value.status,
		receipt: false !== value.receipt,
		email: typeof value.email === 'string' ? value.email : '',
		url: typeof value.url === 'string' ? value.url : '',
	};
}

/**
 * The card's state from the route; null when the route cannot be read.
 *
 * @param url     The inquiry route.
 * @param nonce   wp_rest nonce.
 * @param locale  The page's language.
 * @param fetcher Fetch for tests.
 */
export async function readInquiry(
	url: string,
	nonce: string,
	locale: Locale,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< InquiryState | null > {
	try {
		const response = await fetcher(
			`${ url }${ url.includes( '?' ) ? '&' : '?' }locale=${ locale }`,
			{
				credentials: 'same-origin',
				cache: 'no-store',
				headers: { 'X-WP-Nonce': nonce },
			}
		);
		if ( ! response.ok ) {
			return null;
		}
		const body = ( await response.json() ) as Record< string, unknown >;
		const account = body.account as Record< string, unknown > | null;
		const lines = Array.isArray( body.lines )
			? ( body.lines as Array< Record< string, unknown > > ).map(
					( line ) => ( {
						product_id: Number( line.product_id ) || 0,
						name: typeof line.name === 'string' ? line.name : '',
						sku: typeof line.sku === 'string' ? line.sku : '',
						quantity: Number( line.quantity ) || 0,
						price_html:
							typeof line.price_html === 'string'
								? line.price_html
								: '',
						url: typeof line.url === 'string' ? line.url : '',
					} )
				)
			: [];
		return {
			conversation: Number( body.conversation ) || 0,
			started: typeof body.started === 'string' ? body.started : '',
			startedNonce:
				typeof body.started_nonce === 'string'
					? body.started_nonce
					: '',
			account:
				account && typeof account.email === 'string'
					? {
							email: account.email,
							name:
								typeof account.name === 'string'
									? account.name
									: '',
							company:
								typeof account.company === 'string'
									? account.company
									: '',
						}
					: null,
			lines,
			linesDigest:
				typeof body.lines_digest === 'string' ? body.lines_digest : '',
			message: typeof body.message === 'string' ? body.message : '',
			summary: typeof body.summary === 'string' ? body.summary : '',
			sent: sent( body.sent ),
			pageUrl: typeof body.page_url === 'string' ? body.page_url : '',
		};
	} catch {
		return null;
	}
}

/**
 * Sends the card's inquiry.
 *
 * @param url                   The inquiry route.
 * @param nonce                 wp_rest nonce.
 * @param request               What the card sends.
 * @param request.name          A guest's name; omitted for a signed-in customer.
 * @param request.email         A guest's reply address.
 * @param request.company       A guest's company, optional.
 * @param request.message       The message the card showed.
 * @param request.attachSummary Whether #244's conversation summary goes with it.
 * @param request.lines         The draft's digest the card showed.
 * @param request.website       The honeypot's value (empty for a person).
 * @param request.started       The signed start time readInquiry() returned.
 * @param request.started_nonce Its signature.
 * @param request.consent       A guest's consent, the site's public doors' own.
 * @param request.locale        The page's language.
 * @param request.page          The page context the turn carries (the note keeps it).
 * @param fetcher               Fetch for tests.
 */
export async function sendInquiry(
	url: string,
	nonce: string,
	request: {
		name?: string;
		email?: string;
		company?: string;
		message: string;
		attachSummary: boolean;
		lines: string;
		website: string;
		started: string;
		started_nonce: string;
		consent?: '1';
		locale: Locale;
		page?: PageContext;
	},
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< InquiryResult > {
	try {
		const response = await resourceFetch( fetcher, url, {
			method: 'POST',
			credentials: 'same-origin',
			cache: 'no-store',
			headers: {
				'Content-Type': 'application/json',
				'X-WP-Nonce': nonce,
			},
			body: JSON.stringify( {
				name: request.name ?? '',
				email: request.email ?? '',
				company: request.company ?? '',
				message: request.message,
				attach_summary: request.attachSummary ? '1' : '',
				lines: request.lines,
				website: request.website,
				started: request.started,
				started_nonce: request.started_nonce,
				consent: request.consent ?? '',
				locale: request.locale,
				...( request.page ? { page: request.page } : {} ),
			} ),
		} );
		const body = ( await response.json().catch( () => null ) ) as {
			sent?: unknown;
			inquiry?: unknown;
			code?: unknown;
		} | null;
		if ( response.ok && body && true === body.sent ) {
			const inquiry = sent( body.inquiry );
			if ( inquiry ) {
				return { ok: true, inquiry };
			}
		}
		return {
			ok: false,
			failure: failure( response.status, body?.code ),
		};
	} catch {
		return { ok: false, failure: 'retry' };
	}
}

/**
 * The route's refusal as the card's own failure kind (its error codes).
 *
 * @param status HTTP status.
 * @param code   The route's error code, when the body carries one.
 */
function failure( status: number, code: unknown ): InquiryFailure {
	if ( typeof code === 'string' ) {
		const name = code.replace( /^linker_genie_inquiry_/, '' );
		if (
			'name' === name ||
			'email' === name ||
			'consent' === name ||
			'changed' === name ||
			'empty' === name ||
			'limited' === name ||
			'retry' === name ||
			'refused' === name ||
			'unavailable' === name
		) {
			return name;
		}
	}
	if ( 409 === status ) {
		return 'changed';
	}
	if ( 429 === status ) {
		return 'limited';
	}
	if ( 503 === status ) {
		return 'unavailable';
	}
	return 'retry';
}
