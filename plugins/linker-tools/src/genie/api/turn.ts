import { genieFetch } from './restFetch';
import { inputBeforeUploads } from '../shared/conversation';
import { keepJobFiles, removeFiles } from '../attachments/turnFiles';
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
 * WordPress dependencies
 */
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { Locale } from '../types';
import type { Upload } from '../attachments/prepare';
import type { SentInquiry } from './inquiry';
import { restoreArtifacts, type ArtifactContext } from './historyArtifacts';

import { resourceFetch } from '../../protection/request';

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
	/** Exact live action proofs, signed by WordPress after current validation. */
	draft_proofs?: Record< string, string >;
	quantities?: Record< string, number >;
}

/** A comparison of two to four products. */
export interface CompareBlock {
	draft_proofs?: Record< string, string >;
	quantities?: Record< string, number >;
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
		| 'open_configurator'
		| 'add_to_draft'
		| 'save_solution'
		| 'view_inquiry'
		// The inquiry confirmation card (#250); the shell renders the card.
		| 'send_inquiry';
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
	document_id?: string;
	document_revision?: string;
	evidence_product_id?: number;
	label: string | null;
	url: string | null;
	/** Original document title, preserved when history UI is localized. */
	sourceTitle?: string;
}

/** Why Genie offers the team's contact (the service's contact.py, #243). */
export type ContactReason = 'asked' | 'service' | 'dissatisfied' | 'repeat';

/**
 * One candidate product of an unclear parts-list row (#251): the model as our
 * titles write it, which a chip sends back, and the product's full title.
 */
export interface PartsCandidate {
	product_id: number;
	label: string;
	name?: string;
}

/** One line of the customer's parts list and what code made of it. */
export interface PartsRow {
	/** The row's position in the list, from 1. */
	line: number;
	text: string;
	quantity: number;
	status: 'matched' | 'uncertain' | 'missing' | 'skipped';
	product_id?: number | null;
	label?: string | null;
	/** The candidates of an uncertain row (at most parts.MAX_OPTIONS). */
	options?: PartsCandidate[];
}

/** The one solution-draft write: every confirmed row, merged by product. */
export interface PartsAdd {
	proof?: string;
	items: { product_id: number; quantity: number }[];
	products: number;
	rows: number;
}

/**
 * The parts list the service matched (#251): its rows, the first unclear row
 * it asks about, and the one add-to-draft action. Written by the service, never
 * by the model.
 */
export interface PartsBlock {
	type: 'parts';
	rows: PartsRow[];
	ask_line?: number | null;
	add?: PartsAdd | null;
	truncated?: boolean;
}

/**
 * "Let Linker contact me": the service adds it after the answer; the shell
 * renders the contact card (components/ContactCard.tsx).
 */
export interface ContactBlock {
	type: 'contact';
	reason: ContactReason;
}

/** Server-owned immutable calculation metadata; the chat model cannot write it. */
export type PlanningSourcesBlock =
	| PlanningSourcesAvailableBlock
	| {
			type: 'planning_sources';
			schema_version: 1;
			status: 'unavailable';
	  };
export interface PlanningSourcesAvailableBlock {
	type: 'planning_sources';
	schema_version: 1;
	status: 'available';
	binding: {
		planning_project_id: string;
		planning_revision: number;
		planning_run_ids: string[];
		runs: {
			id: string;
			revision: number;
			manifest_sha256: string;
			result_sha256: string;
		}[];
	};
	results: { revision: number; groups: CalculationSourceGroup[] }[];
	url: string;
}
export interface CalculationSourceGroup {
	kind: 'pv' | 'energy';
	role: 'selected' | 'baseline' | 'candidate';
	input_quantity?: 'pv_available_ac' | 'pv_available_dc' | null;
	source_scope?: 'whole_reference' | 'selected_dc_group' | null;
	timezone: string | null;
	radiation_database?: string | null;
	meteorological_database?: string | null;
	weather_selection_period?: { start_year: number; end_year: number } | null;
	synthetic_calculation_year?: number | null;
	periods_utc: ( { start_utc: string; end_utc: string } | null )[];
}

export type Block =
	| ContactBlock
	| TextBlock
	| AskBlock
	| CompareBlock
	| CardsBlock
	| ActionBlock
	| HandoffBlock
	| DocumentBlock
	| PartsBlock
	| PlanningSourcesBlock;

export interface TurnMeta {
	/** The logged turn; the vote buttons address it. */
	turn_id?: number;
	grounded: boolean;
	fallback: boolean;
	attempts: number;
	failures: string[];
	language: Locale;
}

/**
 * One file the customer attached this turn, as the service read it (#236,
 * services/genie nameplate.card): what it is and, for a nameplate, how it
 * matched our products. The words are the shell's; this carries codes.
 */
export interface AttachmentCard {
	id: string;
	name: string;
	kind: 'nameplate' | 'document' | 'photo' | 'list';
	/** Why nothing could be read: a reason code of the service. */
	failed?: string | null;
	pages?: number | null;
	pages_read?: number | null;
	brand?: string | null;
	model?: string | null;
	product_type?: string | null;
	/** How sure the match is, decided by our product data, never by the model. */
	match?: 'exact' | 'partial' | 'none' | 'unreadable' | null;
	/** The products the customer may confirm, by their model. */
	products?: { product_id: number; label: string }[];
}

export interface Turn {
	meta: TurnMeta | null;
	blocks: Block[];
	/** This turn's files (the stream's `attachment` events). */
	attachments?: AttachmentCard[];
}

/**
 * A turn the proxy refused, with its reason (a WP_Error code such as
 * `linker_genie_attachment_type`).
 */
export class TurnError extends Error {
	constructor(
		readonly status: number,
		readonly code: string
	) {
		super( `turn ${ status } ${ code }` );
	}
}

/**
 * A stream that never sent `done`. Classification is this class. A generic
 * error whose message happens to say the same words is not one.
 */
export class UnfinishedStreamError extends Error {
	constructor() {
		super( 'stream without done' );
		this.name = 'UnfinishedStreamError';
	}
}

/**
 * Bound the dispatched response. It covers the native resource operation
 * window (Protection/Resources.php). The service budget and admission lease
 * stay unchanged (spec 13).
 */
export const TURN_TIMEOUT_MS = 90_000;

/**
 * The commit was refused because the stored thread moved while Genie was
 * answering (#373). The model did answer; the shell must not say it failed.
 *
 * @param error The rejection from sendTurn.
 */
export function isTurnConflict( error: unknown ): boolean {
	return (
		error instanceof TurnError &&
		error.status === 409 &&
		error.code === 'linker_genie_turn_conflict'
	);
}

/**
 * What the shell says on that refusal. The question stays in the field.
 */
export function turnConflictText(): string {
	return __(
		'The conversation changed while Genie was answering. Send your question again.',
		'linker-tools'
	);
}

export interface TurnMessage {
	planning_sources?: PlanningSourcesBlock;
	comparisons?: ( CompareBlock | CardsBlock )[];
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
	/**
	 * The customer's own saved solution (#496), added when the design report's
	 * "Ask Genie" saved it and opened the dock. The service's read-solution
	 * ability checks the owner; a guest's solution has no post and no id.
	 */
	solution_id?: number;
	planning_project_id?: string;
	planning_revision?: number;
	planning_run_ids?: string[];
	planning_unsaved?: boolean;
}

/**
 * A contact request sent from this conversation (#243): the card stays in the
 * history after the answer that showed it (`after`, a message index).
 */
export interface SentContact {
	after: number;
	email: string;
	/** False when the site's receipt cap held the customer's receipt back. */
	receipt?: boolean | null;
}

/**
 * An inquiry sent from the confirmation card (#250): it stays in the history
 * after the answer that showed the card, with the record's number and status.
 */
export interface SentInquiryCard extends SentInquiry {
	/** The message index of the answer that showed the card. */
	after: number;
}

export type { SentInquiry };

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

/** One turn. The test seams sit on the object, not further positional arguments. */
export interface TurnRequest {
	uploadScope?: string;
	surface?: 'hero' | 'helper' | 'workspace';
	/** Current mounted surface, pre-dispatch cancellation and actual transport stage. */
	owner?: TurnOwner;
	onStage?: ( stage: TurnStage ) => void;
	onStarted?: ( conversationId: number ) => void;
	/** Existing planner guest CSRF proof; never part of page data or logs. */
	plannerNonce?: string;
	/** Proxy route URL. */
	turnUrl: string;
	/** wp_rest nonce. */
	nonce: string;
	/** Page language. */
	locale: Locale;
	/** Thread so far, oldest first. */
	messages: TurnMessage[];
	/** Page context. */
	page: PageContext;
	/** The files of this turn, apart from the messages (#236). */
	uploads?: Upload[];
	/** Actual resource UUID of this send, before the network request leaves. */
	onOperation?: ( id: string ) => void;
	/** Fetch for tests. */
	fetcher?: Fetch;
	/**
	 * Bounds the dispatched request and response body, and a turn that carries
	 * no verification context as a whole.
	 */
	timeoutMs?: number;
}

export interface TurnOwner {
	signal: AbortSignal;
	beforeDispatch: () => Promise< void >;
	onDispatch: () => void;
}

export type TurnStage =
	| 'waiting'
	| 'reading_attachments'
	| 'understanding'
	| 'checking_catalog'
	| 'searching_documents'
	| 'writing_answer'
	| 'verifying_answer';

export interface PendingJob {
	job_id: string;
	conversation_id: number;
	stage: TurnStage;
	started_at: number;
	queued_seconds?: number;
	user_message: string;
	operation_id?: string;
}

type TurnTransport = Pick<
	TurnRequest,
	'turnUrl' | 'nonce' | 'plannerNonce' | 'fetcher' | 'onStage' | 'timeoutMs'
>;

function turnRoute( url: string, suffix: string ): string {
	if ( ! url.includes( '?' ) ) {
		return url.replace( /\/$/, '' ) + '/' + suffix;
	}
	const parsed = new URL( url, window.location.href );
	const route = parsed.searchParams.get( 'rest_route' );
	if ( route ) {
		parsed.searchParams.set(
			'rest_route',
			route.replace( /\/$/, '' ) + '/' + suffix
		);
	} else {
		parsed.pathname = parsed.pathname.replace( /\/$/, '' ) + '/' + suffix;
	}
	return parsed.toString();
}

/**
 * Start and execution share one deadline. Add only the wait measured by the service.
 * @param budget
 * @param external
 * @param attempt
 * @param queuedSeconds
 */
async function withinTurn< T >(
	budget: number,
	external: AbortSignal | undefined,
	attempt: (
		signal: AbortSignal,
		setQueueTime: ( seconds: number ) => void
	) => Promise< T >,
	queuedSeconds = 0
): Promise< T > {
	const controller = new AbortController();
	const cancel = () => controller.abort( external?.reason );
	const aborted = new Promise< never >( ( _, reject ) =>
		controller.signal.addEventListener(
			'abort',
			() => reject( controller.signal.reason ),
			{ once: true }
		)
	);
	if ( external?.aborted ) {
		cancel();
	} else {
		external?.addEventListener( 'abort', cancel, { once: true } );
	}
	const deadline = Date.now() + budget;
	let timeout: ReturnType< typeof setTimeout > | undefined;
	const setQueueTime = ( seconds: number ) => {
		clearTimeout( timeout );
		timeout = setTimeout(
			() =>
				controller.abort(
					new DOMException( 'The turn timed out.', 'AbortError' )
				),
			Math.max( 0, deadline + seconds * 1000 - Date.now() )
		);
	};
	setQueueTime( queuedSeconds );
	try {
		return await Promise.race( [
			aborted,
			attempt( controller.signal, setQueueTime ),
		] );
	} finally {
		clearTimeout( timeout );
		external?.removeEventListener( 'abort', cancel );
	}
}

async function replyBody( response: Response ) {
	if ( ! response.ok ) {
		const refusal = await response.json().catch( () => ( {} ) );
		throw new TurnError(
			response.status,
			typeof refusal?.code === 'string' ? refusal.code : ''
		);
	}
	return response.json();
}

async function pollTurn(
	request: TurnTransport,
	job: Pick< PendingJob, 'job_id' | 'conversation_id' | 'stage' >,
	signal: AbortSignal,
	setQueueTime: ( seconds: number ) => void
): Promise< Turn > {
	const fetcher = request.fetcher ?? genieFetch;
	const initialPollDelays = [ 600, 600, 900, 900, 900 ];
	let stage = job.stage;
	request.onStage?.( stage );
	for ( let poll = 0; ; poll++ ) {
		signal.throwIfAborted();
		await new Promise< void >( ( resolve ) =>
			setTimeout( resolve, initialPollDelays[ poll ] ?? 1200 )
		);
		signal.throwIfAborted();
		const response = await fetcher(
			turnRoute( request.turnUrl, job.job_id ),
			{
				credentials: 'same-origin',
				cache: 'no-store',
				signal,
				headers: {
					'X-WP-Nonce': request.nonce,
					...( request.plannerNonce
						? { 'X-Linker-Planner-Nonce': request.plannerNonce }
						: {} ),
				},
			}
		);
		const body = await replyBody( response );
		if (
			body.job_id !== job.job_id ||
			body.conversation_id !== job.conversation_id
		) {
			throw new UnfinishedStreamError();
		}
		if ( typeof body.queued_seconds === 'number' ) {
			setQueueTime( body.queued_seconds );
		}
		if ( body.status === 'completed' ) {
			return parseStream( body.stream );
		}
		if ( body.status !== 'running' ) {
			throw new TurnError( body.http_status ?? 503, body.code ?? '' );
		}
		if ( body.stage !== stage ) {
			stage = body.stage;
			request.onStage?.( stage );
		}
	}
}

export function resumeTurn(
	request: TurnTransport,
	job: PendingJob,
	signal?: AbortSignal
): Promise< Turn > {
	const remaining =
		job.started_at * 1000 +
		( request.timeoutMs ?? TURN_TIMEOUT_MS ) -
		Date.now();
	return withinTurn(
		remaining,
		signal,
		( active, setQueueTime ) =>
			pollTurn( request, job, active, setQueueTime ),
		job.queued_seconds ?? 0
	);
}

/**
 * Submit the pending question once; subsequent requests only read that job.
 * @param request
 */
export function sendTurn( request: TurnRequest ): Promise< Turn > {
	const {
		nonce,
		locale,
		messages,
		page,
		uploads = [],
		fetcher = genieFetch,
	} = request;
	return withinTurn(
		request.timeoutMs ?? TURN_TIMEOUT_MS,
		request.owner?.signal,
		async ( signal, setQueueTime ) => {
			const response = await resourceFetch(
				async ( ...args ) => {
					signal.throwIfAborted();
					await request.owner?.beforeDispatch();
					signal.throwIfAborted();
					request.owner?.onDispatch();
					if ( request.surface ) {
						window.linkerTrack?.( 'genie_ask', {
							surface:
								request.surface === 'helper'
									? 'floating'
									: request.surface,
						} );
					}
					return fetcher( ...args );
				},
				turnRoute( request.turnUrl, 'start' ),
				{
					method: 'POST',
					credentials: 'same-origin',
					signal,
					headers: {
						'Content-Type': 'application/json',
						'X-WP-Nonce': nonce,
						...( request.plannerNonce
							? { 'X-Linker-Planner-Nonce': request.plannerNonce }
							: {} ),
					},
					body: JSON.stringify( {
						locale,
						messages: messages.map( ( { role, content } ) => ( {
							role,
							content,
						} ) ),
						page,
						...( uploads.length ? { attachments: uploads } : {} ),
					} ),
				},
				request.onOperation
			);
			const body = await replyBody( response );
			if (
				body.status === 'running' &&
				typeof body.job_id === 'string' &&
				body.conversation_id > 0
			) {
				const question = messages.at( -1 )?.content ?? '';

				await keepJobFiles(
					body.job_id,
					uploads,
					Date.now() + TURN_TIMEOUT_MS,
					inputBeforeUploads( question, uploads ),
					body.stage === 'waiting' ? request.uploadScope : undefined
				);
				request.onStarted?.( body.conversation_id );
				const answer = await pollTurn(
					request,
					body,
					signal,
					setQueueTime
				);
				if ( uploads.length ) {
					await removeFiles( body.job_id ).catch( () => undefined );
				}
				return answer;
			}
			return parseStream( body.stream ?? '' );
		}
	);
}

/**
 * One assistant message as the thread shows it: the turn's text.
 *
 * @param turn The parsed turn.
 */
export function assistantMessage( turn: Turn ): TurnMessage {
	const source = turn.blocks.find(
		( block ) => block.type === 'planning_sources'
	);
	return {
		...( source ? { planning_sources: source } : {} ),
		...( turn.blocks.some( ( b ) => b.type === 'compare' )
			? {
					comparisons: turn.blocks
						.filter(
							( b ): b is CompareBlock => b.type === 'compare'
						)
						.map( ( block ) => ( {
							type: 'compare' as const,
							product_ids: block.product_ids,
						} ) ),
				}
			: {} ),
		role: 'assistant',
		content: turn.blocks
			.filter(
				( block ): block is TextBlock | HandoffBlock =>
					block.type === 'text' || block.type === 'handoff'
			)
			.map( ( block ) =>
				block.type === 'handoff' ? block.summary : block.text
			)
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
 * @param threadUrl                         Proxy route that answers `{ conversation_id, messages, stream, contacts, inquiries }`.
 * @param nonce                             wp_rest nonce.
 * @param fetcher                           Fetch for tests.
 * @param artifacts                         Current page context for refreshing stored artifact UI.
 * @param proof                             Existing native owner proof.
 * @param proof.plannerNonce                Current in-memory native nonce.
 * @param proof.allowExistingOwnerBootstrap Explicit history interaction permits one read-only proof refresh.
 * @param proof.onPlannerNonce              Remember refreshed proof in existing app memory.
 */
export async function readThread(
	threadUrl: string,
	nonce: string,
	fetcher: Fetch = genieFetch,
	artifacts?: ArtifactContext,
	proof?: {
		plannerNonce?: string;
		allowExistingOwnerBootstrap?: boolean;
		onPlannerNonce?: ( value: string ) => void;
	}
): Promise< {
	messages: TurnMessage[];
	turn: Turn | null;
	/** The existing proxy identity, when the read returned a real conversation. */
	conversationId?: number;
	/** Trusted completed operation returned by the owned Thread, never inferred. */
	operationId?: string;
	pendingJob?: PendingJob;
	/** Always set here; optional for the callers' own stand-ins. */
	contacts?: SentContact[];
	/** Always set here; optional for the callers' own stand-ins. */
	inquiries?: SentInquiryCard[];
} > {
	const empty = { messages: [], turn: null, contacts: [], inquiries: [] };
	try {
		const destination = artifacts
			? `${ threadUrl }${ threadUrl.includes( '?' ) ? '&' : '?' }locale=${ artifacts.locale }`
			: threadUrl;
		const response = await resourceFetch( fetcher, destination, {
			credentials: 'same-origin',
			// A per-visitor answer: never from the browser's cache.
			cache: 'no-store',
			headers: {
				'X-WP-Nonce': nonce,
				...( proof?.plannerNonce
					? { 'X-Linker-Planner-Nonce': proof.plannerNonce }
					: {} ),
			},
		} );
		if ( ! response.ok ) {
			return empty;
		}
		const stored = ( await response.json() ) as {
			conversation_id?: number;
			operation_id?: string;
			pending_job?: PendingJob;
			messages?: ( TurnMessage & { compare_product_ids?: number[][] } )[];
			stream?: string;
			contacts?: Array< Partial< SentContact > >;
			inquiries?: Array< Partial< SentInquiryCard > >;
		};
		const messages = ( stored.messages ?? [] )
			.filter(
				( message ) =>
					message &&
					( message.role === 'user' ||
						message.role === 'assistant' ) &&
					typeof message.content === 'string'
			)
			.map( ( message ): TurnMessage => ( {
				...( message.role === 'assistant' &&
				message.compare_product_ids?.length
					? {
							comparisons: message.compare_product_ids.map(
								( ids ) => ( {
									type: 'compare',
									product_ids: ids,
								} )
							),
						}
					: {} ),
				role: message.role,
				content: message.content,
				...( message.role === 'assistant' &&
				Number.isSafeInteger( message.turnId ) &&
				( message.turnId ?? 0 ) > 0
					? { turnId: message.turnId }
					: {} ),
				...( message.role === 'assistant' &&
				message.planning_sources?.type === 'planning_sources' &&
				validPlanningSources( message.planning_sources )
					? { planning_sources: message.planning_sources }
					: {} ),
			} ) );
		const identity: { conversationId?: number; pendingJob?: PendingJob } =
			Number.isInteger( stored.conversation_id ) &&
			( stored.conversation_id ?? 0 ) > 0
				? {
						conversationId: stored.conversation_id,
						...( stored.pending_job
							? {
									pendingJob: {
										...stored.pending_job,
										conversation_id:
											stored.conversation_id!,
									},
								}
							: {} ),
					}
				: {};
		if ( messages.length === 0 ) {
			return { ...empty, ...identity };
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
		if (
			turn &&
			identity.conversationId &&
			artifacts &&
			proof?.allowExistingOwnerBootstrap &&
			( messages.some(
				( message ) =>
					message.planning_sources?.status === 'unavailable'
			) ||
				turn.blocks.some(
					( block ) =>
						block.type === 'planning_sources' &&
						block.status === 'unavailable'
				) )
		) {
			// This mode cannot create/reset/claim a Woo owner. A fresh native
			// cookie proof only authorizes the stored references in the reread.
			try {
				const bootstrap = await resourceFetch(
					fetcher,
					`${ artifacts.restUrl.replace( /\/?$/, '/' ) }linker/v1/planner/bootstrap`,
					{
						method: 'POST',
						credentials: 'same-origin',
						cache: 'no-store',
						headers: {
							'Content-Type': 'application/json',
							'X-WP-Nonce': nonce,
						},
						body: JSON.stringify( {
							schema_version: 1,
							existing_owner_only: true,
						} ),
					}
				);
				const session = bootstrap.ok ? await bootstrap.json() : null;
				if (
					session &&
					session.schema_version === 1 &&
					session.cookie_confirmed === true &&
					[ 'guest', 'user' ].includes( session.kind ) &&
					Number.isSafeInteger( session.expires_at ) &&
					session.expires_at > Date.now() / 1000 &&
					typeof session.query_scope === 'string' &&
					/^[a-f0-9]{64}$/.test( session.query_scope ) &&
					typeof session.nonce === 'string' &&
					/^\S{1,128}$/.test( session.nonce )
				) {
					proof.onPlannerNonce?.( session.nonce );
					const restored = await readThread(
						threadUrl,
						nonce,
						fetcher,
						artifacts,
						{ plannerNonce: session.nonce }
					);
					if (
						restored.turn &&
						restored.conversationId === identity.conversationId
					) {
						return restored;
					}
				}
			} catch {
				// Refusal leaves the verified-unavailable hint and original words.
			}
		}
		const historical = messages.flatMap( ( m ) => m.comparisons ?? [] );
		if ( artifacts && ( turn || historical.length ) ) {
			const latestCount = turn?.blocks.length ?? 0;
			const restored = await restoreArtifacts(
				{
					meta: turn?.meta ?? null,
					blocks: [ ...( turn?.blocks ?? [] ), ...historical ],
				},
				artifacts,
				nonce,
				fetcher
			);
			if ( turn ) {
				turn = {
					...turn,
					blocks: restored.blocks.slice( 0, latestCount ),
				};
			}
			let offset = latestCount;
			for ( const msg of messages ) {
				if ( ! msg.comparisons ) {
					continue;
				}
				msg.comparisons = restored.blocks.slice(
					offset,
					offset + msg.comparisons.length
				) as ( CardsBlock | CompareBlock )[];
				offset += msg.comparisons.length;
			}
		}
		return {
			...identity,
			...( typeof stored.operation_id === 'string' &&
			/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
				stored.operation_id
			)
				? { operationId: stored.operation_id }
				: {} ),
			messages: turn
				? [ ...messages, assistantMessage( turn ) ]
				: messages,
			turn,
			contacts: ( stored.contacts ?? [] ).filter(
				( card ): card is SentContact =>
					Number.isInteger( card?.after ) &&
					typeof card?.email === 'string'
			),
			inquiries: ( stored.inquiries ?? [] ).filter(
				( card ): card is SentInquiryCard =>
					Number.isInteger( card?.after ) &&
					Number.isInteger( card?.order ) &&
					typeof card?.number === 'string' &&
					typeof card?.status === 'string'
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
	fetcher: Fetch = genieFetch
): Promise< ConversationList > {
	const failed = { currentId: 0, conversations: [], ok: false };
	try {
		const response = await resourceFetch( fetcher, url, {
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
	fetcher: Fetch = genieFetch
): Promise< ConversationList > {
	const response = await resourceFetch( fetcher, url, {
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
	fetcher: Fetch = genieFetch
): Promise< ConversationList > {
	const response = await resourceFetch( fetcher, `${ url }/${ id }`, {
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
	'pending',
	'invalid',
	'unknown',
	'empty',
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

/** The result of the handoff and its destination. */
export interface EmailResult {
	outcome: EmailOutcome;
	/** The address it concerns (the account's for a signed-in customer). */
	to: string;
}

/** The guest form’s hidden website field. */
export interface EmailGuard {
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
	fetcher: Fetch = genieFetch
): Promise< EmailResult > {
	try {
		const response = await resourceFetch(
			fetcher,
			`${ url }/${ id }/email`,
			{
				method: 'POST',
				credentials: 'same-origin',
				cache: 'no-store',
				headers: {
					'Content-Type': 'application/json',
					...( nonce ? { 'X-WP-Nonce': nonce } : {} ),
				},
				body: JSON.stringify(
					email ? { locale, email, ...guard } : { locale }
				),
			}
		);
		const body = ( await response.json().catch( () => ( {} ) ) ) as {
			status?: string;
			to?: string;
			code?: string;
		};
		return {
			outcome: emailOutcome(
				response.ok
					? body.status
					: ( body.code ?? '' ).replace( /^linker_genie_email_/, '' )
			),
			to: body.to ?? '',
		};
	} catch {
		return { outcome: 'unavailable', to: '' };
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
	fetcher: Fetch = genieFetch
): Promise< boolean > {
	try {
		const response = await resourceFetch(
			fetcher,
			`${ voteUrl }/${ turnId }/vote`,
			{
				method: 'POST',
				credentials: 'same-origin',
				headers: {
					'Content-Type': 'application/json',
					'X-WP-Nonce': nonce,
				},
				body: JSON.stringify( { vote } ),
			}
		);
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
			turn.blocks.push(
				payload?.type === 'planning_sources' &&
					! validPlanningSources( payload )
					? {
							type: 'planning_sources',
							schema_version: 1,
							status: 'unavailable',
						}
					: ( payload as Block )
			);
		} else if ( name[ 1 ] === 'attachment' ) {
			turn.attachments = [
				...( turn.attachments ?? [] ),
				payload as AttachmentCard,
			];
		} else if ( name[ 1 ] === 'done' ) {
			done = true;
		}
	}
	if ( ! done ) {
		throw new UnfinishedStreamError();
	}
	return turn;
}

/**
 * Unknown or malformed source cards cannot contribute dates or destinations.
 * @param raw The received server-owned block.
 */
function validPlanningSources( raw: unknown ): raw is PlanningSourcesBlock {
	const object = ( value: unknown ): value is Record< string, unknown > =>
		!! value && typeof value === 'object' && ! Array.isArray( value );
	const positive = ( value: unknown ): value is number =>
		typeof value === 'number' && Number.isSafeInteger( value ) && value > 0;
	const hash = ( value: unknown ) =>
		typeof value === 'string' && /^[a-f0-9]{64}$/.test( value );
	const id = ( value: unknown ) =>
		typeof value === 'string' && /^[a-f0-9]{32}$/.test( value );
	if (
		object( raw ) &&
		raw.schema_version === 1 &&
		raw.status === 'unavailable'
	) {
		return Object.keys( raw ).every( ( key ) =>
			[ 'type', 'schema_version', 'status' ].includes( key )
		);
	}
	if (
		! object( raw ) ||
		raw.schema_version !== 1 ||
		raw.status !== 'available' ||
		! object( raw.binding ) ||
		! id( raw.binding.planning_project_id ) ||
		! positive( raw.binding.planning_revision ) ||
		! Array.isArray( raw.binding.planning_run_ids ) ||
		! raw.binding.planning_run_ids.every( id ) ||
		! Array.isArray( raw.binding.runs ) ||
		! raw.binding.runs.length ||
		! raw.binding.runs.every(
			( run ) =>
				object( run ) &&
				id( run.id ) &&
				positive( run.revision ) &&
				hash( run.manifest_sha256 ) &&
				hash( run.result_sha256 ) &&
				(
					raw.binding as PlanningSourcesAvailableBlock[ 'binding' ]
				 ).planning_run_ids.includes( run.id as string )
		) ||
		! Array.isArray( raw.results ) ||
		raw.results.length !== raw.binding.runs.length ||
		typeof raw.url !== 'string'
	) {
		return false;
	}
	return raw.results.every( ( result, index ) => {
		if (
			! object( result ) ||
			! positive( result.revision ) ||
			result.revision !==
				( raw.binding as PlanningSourcesAvailableBlock[ 'binding' ] )
					.runs[ index ]?.revision ||
			! Array.isArray( result.groups )
		) {
			return false;
		}
		return result.groups.every( ( group ) => {
			if (
				! object( group ) ||
				! [ 'pv', 'energy' ].includes( group.kind as string ) ||
				! [ 'selected', 'baseline', 'candidate' ].includes(
					group.role as string
				) ||
				! Object.hasOwn( group, 'timezone' ) ||
				! Array.isArray( group.periods_utc )
			) {
				return false;
			}
			if (
				[
					'timezone',
					'radiation_database',
					'meteorological_database',
				].some(
					( key ) =>
						group[ key ] !== undefined &&
						group[ key ] !== null &&
						typeof group[ key ] !== 'string'
				)
			) {
				return false;
			}
			if (
				group.kind === 'pv' &&
				( ! Object.hasOwn( group, 'input_quantity' ) ||
					! Object.hasOwn( group, 'source_scope' ) ||
					! [ null, 'pv_available_ac', 'pv_available_dc' ].includes(
						group.input_quantity as string | null
					) ||
					! [ null, 'whole_reference', 'selected_dc_group' ].includes(
						group.source_scope as string | null
					) )
			) {
				return false;
			}
			if (
				group.synthetic_calculation_year !== undefined &&
				group.synthetic_calculation_year !== null &&
				! positive( group.synthetic_calculation_year )
			) {
				return false;
			}
			const selection = group.weather_selection_period;
			if (
				selection !== undefined &&
				selection !== null &&
				( ! object( selection ) ||
					! positive( selection.start_year ) ||
					! positive( selection.end_year ) ||
					selection.start_year > selection.end_year )
			) {
				return false;
			}
			return group.periods_utc.every(
				( period ) =>
					period === null ||
					( object( period ) &&
						[ 'start_utc', 'end_utc' ].every(
							( key ) =>
								typeof period[ key ] === 'string' &&
								/(?:Z|\+00:00)$/.test(
									period[ key ] as string
								) &&
								Number.isFinite(
									Date.parse( period[ key ] as string )
								)
						) &&
						Date.parse( period.start_utc as string ) <
							Date.parse( period.end_utc as string ) )
			);
		} );
	} );
}

/**
 * A stream the service never finished. The shell shows the failure
 * sentence and does not render the blocks that arrived before `done`.
 *
 * @param error The rejection from parseStream.
 */
export function isUnfinishedStream( error: unknown ): boolean {
	return error instanceof UnfinishedStreamError;
}
