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

/** Qualified products; the shell fetches their display data from the Store API. */
export interface CardsBlock {
	type: 'cards';
	product_ids: number[];
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

export type Block =
	| TextBlock
	| AskBlock
	| CompareBlock
	| CardsBlock
	| ActionBlock
	| HandoffBlock;

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

export interface PageContext {
	type: string;
	product_id?: number;
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
 * @param threadUrl Proxy route that answers `{ conversation_id, messages, stream }`.
 * @param nonce     wp_rest nonce.
 * @param fetcher   Fetch for tests.
 */
export async function readThread(
	threadUrl: string,
	nonce: string,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): Promise< { messages: TurnMessage[]; turn: Turn | null } > {
	const empty = { messages: [], turn: null };
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
		};
	} catch {
		return empty;
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
