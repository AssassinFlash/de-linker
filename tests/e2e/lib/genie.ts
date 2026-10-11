/**
 * One Genie turn, as the shell sends it (docs/specs/13-genie.md §B).
 *
 * The suite talks to the service directly for the behaviour panel: the
 * question, the page context and whether the customer is signed in are the
 * service's own contract, so a turn can be pinned to an entry exactly and the
 * answer is not entangled with a browser's rendering. The chips, the dock and
 * the SSE handling in the page are separate specs, which drive them through
 * the proxy.
 */

/**
 * Internal dependencies
 */
import { instance } from './instance';

/** A text block; its `{fact:ID}` placeholders are already filled. */
export interface TextBlock {
	type: 'text';
	text: string;
	refs: string[];
}

export interface AskBlock {
	type: 'ask';
	field: string;
	options: string[];
}

export interface CardsBlock {
	type: 'cards';
	product_ids: number[];
}

export interface CompareBlock {
	type: 'compare';
	product_ids: number[];
}

export interface ActionBlock {
	type: 'action';
	name: string;
	args: Record<string, unknown>;
}

export interface HandoffBlock {
	type: 'handoff';
	summary: string;
}

export type Block =
	| TextBlock
	| AskBlock
	| CardsBlock
	| CompareBlock
	| ActionBlock
	| HandoffBlock;

export interface TurnMeta {
	turn_id?: number;
	grounded: boolean;
	fallback: boolean;
	attempts: number;
	failures: string[];
	language: string;
}

export interface Turn {
	/** The raw SSE text, as the archived panel rows keep it. */
	stream: string;
	meta: TurnMeta | null;
	blocks: Block[];
	/** The conversation the turn belongs to. */
	conversationId: string;
}

export type PageContext =
	| { type: 'category' | 'account' | 'other' }
	| { type: 'draft'; draft_ids?: number[] }
	| { type: 'product'; product_id: number };

export interface TurnOptions {
	locale?: 'en' | 'de';
	page?: PageContext;
	conversationId?: string;
	/** The thread so far, oldest first; omitted for a fresh question. */
	messages?: Array<{ role: 'user' | 'assistant'; content: string }>;
	loggedIn?: boolean;
	/** Per-turn wall clock; one real-model turn runs for up to a minute. */
	timeoutMs?: number;
}

/**
 * The ids the catalogue itself classifies as a device class (and, optionally,
 * an application).
 *
 * Used to build a row's *superset* — which products are home inverters, which
 * are batteries — from the site's own engineering feed (`linker/v1/
 * engineering-feed`, the same data the configurator sizes against). What a
 * row is judged on (which of those were the right ones) stays in the row's
 * expectation and with the cascade judge.
 */
export async function catalogueIds(query: {
	device_class: string;
	application?: string;
	application_not?: string;
}): Promise<number[]> {
	const target = instance();
	const response = await fetch(
		`${target.url}/wp-json/linker/v1/engineering-feed`
	);
	if (!response.ok) {
		throw new Error(`the engineering feed answered ${response.status}`);
	}
	const feed = (await response.json()) as {
		products?: Array<{
			id: number;
			device_class?: string;
			application?: string | null;
		}>;
	};
	return (feed.products ?? [])
		.filter((product) => product.device_class === query.device_class)
		.filter(
			(product) =>
				query.application === undefined ||
				product.application === query.application
		)
		.filter(
			(product) =>
				query.application_not === undefined ||
				product.application !== query.application_not
		)
		.map((product) => product.id);
}

/** A conversation id that cannot collide with the browser's cookie-bound one. */
export function conversationId(label: string): string {
	return `e2e-${label}-${Date.now()}`;
}

/**
 * Sends one message to the Genie service and returns the parsed turn.
 */
export async function turn(
	question: string,
	options: TurnOptions = {}
): Promise<Turn> {
	const target = instance();
	const conversation = options.conversationId ?? conversationId('turn');
	const body = {
		conversation_id: conversation,
		messages: [
			...(options.messages ?? []),
			{ role: 'user', content: question },
		],
		locale: options.locale ?? 'en',
		page_context: options.page ?? { type: 'other' },
		user: { logged_in: options.loggedIn ?? false },
	};

	const controller = new AbortController();
	const timer = setTimeout(
		() => controller.abort(),
		options.timeoutMs ?? 180_000
	);
	let stream: string;
	try {
		const response = await fetch(`${target.genieUrl}/turn`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Accept: 'text/event-stream',
			},
			body: JSON.stringify(body),
			signal: controller.signal,
		});
		if (!response.ok) {
			throw new Error(`the Genie service answered ${response.status}`);
		}
		stream = await response.text();
	} finally {
		clearTimeout(timer);
	}

	return { stream, ...parseStream(stream), conversationId: conversation };
}

/** The service's SSE text -> meta and blocks. */
export function parseStream(stream: string): {
	meta: TurnMeta | null;
	blocks: Block[];
} {
	let meta: TurnMeta | null = null;
	const blocks: Block[] = [];
	for (const event of stream.split('\n\n')) {
		const data = /^data: (.+)$/m.exec(event);
		if (!data) {
			continue;
		}
		const payload = JSON.parse(data[1] ?? '{}') as Record<string, unknown>;
		if (typeof payload.turn_id === 'number') {
			meta = payload as unknown as TurnMeta;
		} else if (typeof payload.type === 'string') {
			blocks.push(payload as unknown as Block);
		}
	}
	return { meta, blocks };
}

/** The text the customer reads: text and handoff blocks, in order. */
export function answerText(turnResult: Turn): string {
	return blocksOf(turnResult, 'text')
		.map((block) => (block as TextBlock).text)
		.concat(
			blocksOf(turnResult, 'handoff').map(
				(block) => (block as HandoffBlock).summary
			)
		)
		.join('\n');
}

/** The product ids offered in the turn's cards. */
export function cards(turnResult: Turn): number[] {
	return blocksOf(turnResult, 'cards').flatMap(
		(block) => (block as CardsBlock).product_ids
	);
}

/** The turn's decisive questions. */
export function asks(turnResult: Turn): AskBlock[] {
	return blocksOf(turnResult, 'ask') as AskBlock[];
}

/** The turn's comparison blocks. */
export function compares(turnResult: Turn): CompareBlock[] {
	return blocksOf(turnResult, 'compare') as CompareBlock[];
}

/** The turn's actions. */
export function actions(turnResult: Turn): ActionBlock[] {
	return blocksOf(turnResult, 'action') as ActionBlock[];
}

/** The turn's handoff blocks. */
export function handoffs(turnResult: Turn): HandoffBlock[] {
	return blocksOf(turnResult, 'handoff') as HandoffBlock[];
}

function blocksOf(turnResult: Turn, type: string): Block[] {
	return turnResult.blocks.filter((block) => block.type === type);
}

/**
 * The item one archived row hands the cascade judge: the question, the answer
 * as rendered (text plus the products offered) and — where the row offers
 * candidates — the mechanically built wrong-pick variant, so `better_pick`
 * has a real choice.
 */
export interface JudgeItem {
	question: string;
	answer: string;
	reference: unknown;
	cards: number[];
	answer_a?: string;
	answer_b?: string;
}

/** `text\n\nProducts offered: 1, 2` — the pilot's rendering of a turn. */
export function renderedAnswer(
	turnResult: Turn,
	swap?: { from: number; to: number }
): string {
	const offered = cards(turnResult);
	const variant = swap
		? offered.map((id) => (id === swap.from ? swap.to : id))
		: offered;
	return `${answerText(turnResult)}\n\nProducts offered: ${variant.join(', ')}`;
}
