/**
 * One turn through the REST proxy: POST, then read the service's SSE events
 * from the answer (docs/specs/13-genie.md).
 *
 * The proxy answers `{ conversation_id, stream }` where `stream` is the
 * service's `text/event-stream` body: `meta`, one `block` per block, `done`.
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
