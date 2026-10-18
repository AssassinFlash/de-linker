/**
 * One turn through the REST proxy: POST, then read the service's SSE events
 * from the answer (docs/specs/13-genie.md).
 *
 * The proxy answers `{ conversation_id, stream }` where `stream` is the
 * service's `text/event-stream` body: `meta`, one `block` per block, `done`.
 * The same reader serves the stored conversation a reload reads back
 * (`readThread`): an answer's text is this module's business in both cases.
 */

/**
 * Internal dependencies
 */
import type { Locale } from '../../configurator/types';

type Fetch = typeof fetch;

/** A text block; its `{fact:ID}` placeholders are already filled server-side. */
export interface TextBlock {
	type: 'text';
	text: string;
	refs: string[];
}

/** One decisive question; the chips are the answer buttons. */
export interface AskBlock {
	type: 'ask';
	field: string;
	options: string[];
}

/**
 * A card's price line, filled by the service from the customer's own product
 * ability (#242): `text` is what the product page prints where the price
 * stands, in the page's language (the price for an approved partner account,
 * otherwise the page's sentence, with `reason` saying why).
 */
export interface CardPrice {
	product_id: number;
	text: string;
	reason?: 'login' | 'pending' | 'restricted' | 'project' | 'unpriced' | null;
}

/**
 * Qualified products; the shell fetches their display data from the Store API,
 * and their price lines come with the block (`prices`).
 */
export interface CardsBlock {
	type: 'cards';
	product_ids: number[];
	prices?: CardPrice[] | null;
}

/** A comparison of two to four products. */
export interface CompareBlock {
	type: 'compare';
	product_ids: number[];
}

/**
 * An allowed action; `args` comes from tool results only, and the grounding
 * refuses any `url` a tool of this turn did not return. The shell links
 * view_inquiry to the account page itself.
 */
export interface ActionBlock {
	type: 'action';
	name:
		'open_configurator' | 'add_to_draft' | 'save_solution' | 'view_inquiry';
	args: Record< string, unknown >;
}

/** Out-of-scope turns; the sentence names the team mailbox. */
export interface HandoffBlock {
	type: 'handoff';
	summary: string;
}

/**
 * A hosted document; the service fills `label` and `url` from the tool
 * results (the model writes only the reference).
 */
export interface DocumentBlock {
	type: 'document';
	ref: string;
	label: string | null;
	url: string | null;
}

/** Why Genie offers the team's contact (the service's contact.py, #243). */
export type ContactReason = 'asked' | 'service' | 'dissatisfied' | 'repeat';

/**
 * "Let Linker contact me": the service adds it after the answer; the shell
 * renders the contact card (components/ContactCard.tsx).
 */
export interface ContactBlock {
	type: 'contact';
	reason: ContactReason;
}

export type Block =
	| ContactBlock
	| TextBlock
	| AskBlock
	| CompareBlock
	| CardsBlock
	| ActionBlock
	| HandoffBlock
	| DocumentBlock;

export interface TurnMeta {
	/** The logged turn; the vote buttons address it. */
	turn_id?: number;
	grounded: boolean;
	fallback: boolean;
	attempts: number;
	failures: string[];
	language: Locale;
}

export interface Turn {
	meta: TurnMeta | null;
	blocks: Block[];
}

export interface TurnMessage {
	role: 'user' | 'assistant';
	content: string;
	/** The logged turn this assistant message came from. */
	turnId?: number;
}

/**
 * The page a turn comes from (includes/Genie/PageContext.php, #234): its
 * type, address and title and the IDs of what it shows. The proxy keeps
 * only these keys and fills a solution draft's products itself.
 */
export interface PageContext {
	type: string;
	url?: string;
	title?: string;
	product_id?: number;
	post_id?: number;
	category_id?: number;
}

/**
 * A contact request sent from this conversation (#243): the card stays in the
 * history after the answer that showed it (`after`, a message index).
 */
export interface SentContact {
	after: number;
	email: string;
}

/** One row of the history rail. */
export interface ConversationSummary {
	id: number;
	title: string;
	updated: string;
}

export interface ConversationList {
	currentId: number;
	conversations: ConversationSummary[];
	/**
	 * False when the history route failed. An empty list with `ok` is a
	 * visitor who has no earlier conversation; the rail must not say that
	 * when the request itself failed.
	 */
	ok: boolean;
}

/**
 * Sends one message and parses the SSE answer.
 *
 * @param turnUrl  Proxy route URL.
 * @param nonce    wp_rest nonce.
 * @param locale   Page language.
 * @param messages Thread so far, oldest first.
 * @param page     Page context.
 * @param fetcher  Fetch for tests.
 */
export async function sendTurn(
	turnUrl: string,
	nonce: string,
	locale: Locale,
	messages: TurnMessage[],
	page: PageContext,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< Turn > {
	const response = await fetcher( turnUrl, {
		method: 'POST',
		credentials: 'same-origin',
		headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
		body: JSON.stringify( {
			locale,
			messages: messages.map( ( { role, content } ) => ( {
				role,
				content,
			} ) ),
			page,
		} ),
	} );
	if ( ! response.ok ) {
		throw new Error( `turn ${ response.status }` );
	}
	const body = ( await response.json() ) as { stream: string };
	return parseStream( body.stream ?? '' );
}

/**
 * One assistant message as the thread shows it: the turn's text.
 *
 * @param turn The parsed turn.
 */
export function assistantMessage( turn: Turn ): TurnMessage {
	return {
		role: 'assistant',
		content: turn.blocks
			.filter( ( block ): block is TextBlock => block.type === 'text' )
			.map( ( block ) => block.text )
			.join( ' ' ),
		turnId: turn.meta?.turn_id,
	};
}

/**
 * The conversation this browser already has, as the proxy stored it.
 *
 * A reload (or arriving on another page, where the dock mounts again) must
 * not throw the thread away: the proxy keeps the messages of the last
 * answered turn and that turn's stream on the conversation post, and this
 * reads them back in the same shapes a live turn uses.
 *
 * @param threadUrl Proxy route that answers `{ conversation_id, messages, stream, contacts }`.
 * @param nonce     wp_rest nonce.
 * @param fetcher   Fetch for tests.
 */
export async function readThread(
	threadUrl: string,
	nonce: string,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< {
	messages: TurnMessage[];
	turn: Turn | null;
	/** Always set here; optional for the callers' own stand-ins. */
	contacts?: SentContact[];
} > {
	const empty = { messages: [], turn: null, contacts: [] };
	try {
		const response = await fetcher( threadUrl, {
			credentials: 'same-origin',
			// A per-visitor answer: never from the browser's cache.
			cache: 'no-store',
			headers: { 'X-WP-Nonce': nonce },
		} );
		if ( ! response.ok ) {
			return empty;
		}
		const stored = ( await response.json() ) as {
			messages?: TurnMessage[];
			stream?: string;
			contacts?: Array< Partial< SentContact > >;
		};
		const messages = ( stored.messages ?? [] )
			.filter(
				( message ) =>
					message &&
					( message.role === 'user' ||
						message.role === 'assistant' ) &&
					typeof message.content === 'string'
			)
			.map( ( message ) => ( {
				role: message.role,
				content: message.content,
			} ) );
		if ( messages.length === 0 ) {
			return empty;
		}
		let turn: Turn | null = null;
		if ( stored.stream ) {
			try {
				turn = parseStream( stored.stream );
			} catch {
				// A stream the service never finished is not an answer: the
				// thread's words stay, its blocks do not.
				turn = null;
			}
		}
		return {
			messages: turn
				? [ ...messages, assistantMessage( turn ) ]
				: messages,
			turn,
			contacts: ( stored.contacts ?? [] ).filter(
				( card ): card is SentContact =>
					Number.isInteger( card?.after ) &&
					typeof card?.email === 'string'
			),
		};
	} catch {
		return empty;
	}
}

/**
 * The conversations this visitor may continue.
 *
 * An empty answer is an empty rail. This never opens a conversation.
 *
 * @param url     History route.
 * @param nonce   wp_rest nonce.
 * @param fetcher Fetch for tests.
 */
export async function listConversations(
	url: string,
	nonce: string,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< ConversationList > {
	const failed = { currentId: 0, conversations: [], ok: false };
	try {
		const response = await fetcher( url, {
			credentials: 'same-origin',
			cache: 'no-store',
			headers: { 'X-WP-Nonce': nonce },
		} );
		if ( ! response.ok ) {
			return failed;
		}
		const body = ( await response.json() ) as {
			current_id?: number;
			conversations?: ConversationSummary[];
		};
		return {
			currentId: body.current_id ?? 0,
			conversations: ( body.conversations ?? [] ).filter(
				( item ) => item && typeof item.id === 'number' && item.title
			),
			ok: true,
		};
	} catch {
		return failed;
	}
}

/**
 * Continues one conversation, or opens a new one when `id` is omitted.
 *
 * The proxy writes the cookie both surfaces read, so the dock and the
 * workspace share the thread this returns.
 *
 * @param url     History route.
 * @param nonce   wp_rest nonce.
 * @param id      Conversation to continue; omit to open a new one.
 * @param fetcher Fetch for tests.
 */
export async function selectConversation(
	url: string,
	nonce: string,
	id?: number,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< ConversationList > {
	const response = await fetcher( url, {
		method: 'POST',
		credentials: 'same-origin',
		cache: 'no-store',
		headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
		body: JSON.stringify( id ? { id } : {} ),
	} );
	if ( ! response.ok ) {
		throw new Error( `conversation ${ response.status }` );
	}
	const body = ( await response.json() ) as {
		conversation_id?: number;
		conversations?: ConversationSummary[];
	};
	return {
		currentId: body.conversation_id ?? 0,
		conversations: body.conversations ?? [],
		ok: true,
	};
}

/**
 * Clears one of the visitor's conversations and answers the list without it.
 *
 * @param url     History route.
 * @param nonce   wp_rest nonce.
 * @param id      Conversation to clear.
 * @param fetcher Fetch for tests.
 */
export async function deleteConversation(
	url: string,
	nonce: string,
	id: number,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< ConversationList > {
	const response = await fetcher( `${ url }/${ id }`, {
		method: 'DELETE',
		credentials: 'same-origin',
		cache: 'no-store',
		headers: { 'X-WP-Nonce': nonce },
	} );
	if ( ! response.ok ) {
		throw new Error( `delete ${ response.status }` );
	}
	const body = ( await response.json() ) as {
		current_id?: number;
		conversations?: ConversationSummary[];
	};
	return {
		currentId: body.current_id ?? 0,
		conversations: body.conversations ?? [],
		ok: true,
	};
}

/**
 * How an email request, or a confirmation link, ended: the same words as
 * ConversationMail's outcome constants (includes/Genie/ConversationMail.php),
 * one definition on this side. `confirm` is a guest's request: the link went
 * to the typed address.
 */
export const EMAIL_OUTCOMES = [
	'sent',
	'confirm',
	'invalid',
	'unknown',
	'empty',
	'throttled',
	'capped',
	'expired',
	'unavailable',
] as const;
export type EmailOutcome = ( typeof EMAIL_OUTCOMES )[ number ];

/**
 * The outcome a word names, `unavailable` for any other word.
 * @param word
 */
export function emailOutcome( word: unknown ): EmailOutcome {
	return ( EMAIL_OUTCOMES as readonly unknown[] ).includes( word )
		? ( word as EmailOutcome )
		: 'unavailable';
}

/** The answer of an email request: the outcome, where it went, the limit. */
export interface EmailResult {
	outcome: EmailOutcome;
	/** The address it concerns (the account's for a signed-in customer). */
	to: string;
	/** Emails one connection may ask for per hour, named by a refusal. */
	limit: number;
}

/** A guest's bot-guard fields (ConversationMail::passes()). */
export interface EmailGuard {
	started: string;
	started_nonce: string;
	website: string;
}

/**
 * Asks for one conversation by email: a signed-in customer's goes to the
 * account's address (`email` is then left out); a guest's typed address
 * first gets a confirmation link.
 *
 * @param url     History route.
 * @param nonce   wp_rest nonce.
 * @param id      Conversation to send.
 * @param locale  Page language: the email's language.
 * @param email   A guest's address.
 * @param guard   A guest's bot-guard fields.
 * @param fetcher Fetch for tests.
 */
export async function emailConversation(
	url: string,
	nonce: string,
	id: number,
	locale: Locale,
	email?: string,
	guard?: EmailGuard,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< EmailResult > {
	try {
		const response = await fetcher( `${ url }/${ id }/email`, {
			method: 'POST',
			credentials: 'same-origin',
			cache: 'no-store',
			headers: {
				'Content-Type': 'application/json',
				'X-WP-Nonce': nonce,
			},
			body: JSON.stringify(
				email ? { locale, email, ...guard } : { locale }
			),
		} );
		const body = ( await response.json().catch( () => ( {} ) ) ) as {
			status?: string;
			to?: string;
			code?: string;
			data?: { limit?: number };
		};
		return {
			outcome: emailOutcome(
				response.ok
					? body.status
					: ( body.code ?? '' ).replace( /^linker_genie_email_/, '' )
			),
			to: body.to ?? '',
			limit: body.data?.limit ?? 0,
		};
	} catch {
		return { outcome: 'unavailable', to: '', limit: 0 };
	}
}

/**
 * Stores the customer's vote on one logged turn; best effort, a failed vote
 * never disturbs the conversation.
 *
 * @param voteUrl Proxy vote route URL (…/genie/turn).
 * @param nonce   wp_rest nonce.
 * @param turnId  The logged turn the meta carried.
 * @param vote    +1 or -1.
 * @param fetcher Fetch for tests.
 */
export async function sendVote(
	voteUrl: string,
	nonce: string,
	turnId: number,
	vote: 1 | -1,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< boolean > {
	try {
		const response = await fetcher( `${ voteUrl }/${ turnId }/vote`, {
			method: 'POST',
			credentials: 'same-origin',
			headers: {
				'Content-Type': 'application/json',
				'X-WP-Nonce': nonce,
			},
			body: JSON.stringify( { vote } ),
		} );
		return response.ok;
	} catch {
		return false;
	}
}

/**
 * Parses the service's SSE text into one turn. A stream without its `done`
 * event is a broken stream, not a partial answer: the caller shows the retry
 * sentence instead of rendering a turn the service never finished.
 *
 * @param stream SSE text.
 */
export function parseStream( stream: string ): Turn {
	const turn: Turn = { meta: null, blocks: [] };
	let done = false;
	for ( const event of stream.split( '\n\n' ) ) {
		const name = /^event: (.+)$/m.exec( event );
		const data = /^data: (.+)$/m.exec( event );
		if ( ! name || ! data ) {
			continue;
		}
		const payload = JSON.parse( data[ 1 ] );
		if ( name[ 1 ] === 'meta' ) {
			turn.meta = payload as TurnMeta;
		} else if ( name[ 1 ] === 'block' ) {
			turn.blocks.push( payload as Block );
		} else if ( name[ 1 ] === 'done' ) {
			done = true;
		}
	}
	if ( ! done ) {
		throw new Error( 'stream without done' );
	}
	return turn;
}
