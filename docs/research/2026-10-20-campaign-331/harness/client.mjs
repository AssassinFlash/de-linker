/**
 * One client for both faces of a Genie turn (campaign #331):
 *
 * - `ServiceClient` talks to the Genie service directly (`POST /turn`), the way
 *   tests/e2e/lib/genie.ts does for the behaviour panel: arbitrary
 *   conversation ids, no WordPress state. Used for the answer-shape battery
 *   (topic switch, anaphora, mid-thread language, repeats, handoff rules).
 * - `ProxyClient` talks to the WordPress REST proxy
 *   (`linker-ai/v1/genie/turn|conversation|conversations`) with a cookie jar,
 *   the way the dock does: the conversation is the cookie's post, the thread
 *   is written by the proxy (last turn wins — the concurrency battery reads
 *   exactly that). Used for persistence and concurrency cases.
 *
 * Both parse the service's SSE into meta + blocks. Every case the runners
 * write is JSONL under ~/de-linker-data/campaign-331/.
 */

import { appendFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';

export const EVIDENCE_ROOT =
	process.env.C331_EVIDENCE ??
	`${process.env.HOME}/de-linker-data/campaign-331`;

/**
 * The instance this harness ran against. The shared service token comes from
 * the environment, or from a one-line file (C331_TOKEN_FILE) under the
 * evidence root — never from the repository.
 */
export function envTargets() {
	const tokenFile =
		process.env.C331_TOKEN_FILE ?? `${EVIDENCE_ROOT}/service-token.txt`;
	let token = process.env.C331_TOKEN ?? '';
	if (!token) {
		try {
			token = readFileSync(tokenFile, 'utf8').trim();
		} catch {
			token = '';
		}
	}
	const targets = {
		wp: process.env.C331_WP ?? 'http://127.0.0.1:9165',
		genie: process.env.C331_GENIE ?? 'http://127.0.0.1:9167',
		token,
	};
	if (!targets.token) {
		throw new Error(
			`the shared service token is required: set C331_TOKEN or write it to ${tokenFile}`
		);
	}
	return targets;
}

/** The SSE text -> { meta, blocks, events } (tests/e2e/lib/genie.ts shape). */
export function parseStream(stream) {
	let meta = null;
	const blocks = [];
	const events = [];
	for (const event of stream.split('\n\n')) {
		const name = /^event: (.+)$/m.exec(event)?.[1];
		const data = /^data: (.+)$/m.exec(event)?.[1];
		if (!name || !data) {
			continue;
		}
		events.push({ event: name, data: JSON.parse(data) });
		const payload = events.at(-1).data;
		if (name === 'meta') {
			meta = payload;
		} else if (name === 'block') {
			blocks.push(payload);
		}
	}
	return { meta, blocks, events, done: events.some((e) => e.event === 'done') };
}

/** The text the customer reads (text blocks joined), per assistantMessage(). */
export function answerText(blocks) {
	return blocks
		.filter((b) => b.type === 'text')
		.map((b) => b.text)
		.join('\n');
}

export function cardsOf(blocks) {
	return blocks
		.filter((b) => b.type === 'cards')
		.flatMap((b) => b.product_ids);
}

export function contactOf(blocks) {
	return blocks.find((b) => b.type === 'contact') ?? null;
}

export function handoffOf(blocks) {
	return blocks.find((b) => b.type === 'handoff') ?? null;
}

/** One JSONL evidence line, written and returned. */
export function record(scenario, file, entry) {
	const path = `${EVIDENCE_ROOT}/${scenario}/${file}.jsonl`;
	mkdirSync(dirname(path), { recursive: true });
	appendFileSync(path, JSON.stringify(entry) + '\n');
	return entry;
}

/** Raw artefacts (SSE text, thread dumps) beside the JSONL. */
export function artefact(scenario, name, body) {
	const path = `${EVIDENCE_ROOT}/${scenario}/${name}`;
	mkdirSync(dirname(path), { recursive: true });
	writeFileSync(path, typeof body === 'string' ? body : JSON.stringify(body, null, 2));
	return path;
}

/**
 * Direct-service client. `conversationId` stays stable across one case so the
 * service's own turn log (repeat-offer bookkeeping) sees one conversation.
 */
export class ServiceClient {
	constructor({ genie, token } = envTargets()) {
		this.genie = genie;
		this.token = token;
	}

	async turn({ conversationId, messages, locale = 'en', page = { type: 'other' }, timeoutMs = 180_000 }) {
		const body = {
			conversation_id: conversationId,
			messages,
			locale,
			page_context: page,
			user: { logged_in: false },
		};
		const controller = new AbortController();
		const timer = setTimeout(() => controller.abort(), timeoutMs);
		const started = Date.now();
		let stream;
		let status = 0;
		try {
			const response = await fetch(`${this.genie}/turn`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Accept: 'text/event-stream',
					'X-Linker-Service-Token': this.token,
				},
				body: JSON.stringify(body),
				signal: controller.signal,
			});
			status = response.status;
			stream = await response.text();
		} finally {
			clearTimeout(timer);
		}
		return {
			request: body,
			status,
			durationMs: Date.now() - started,
			stream,
			...parseStream(stream),
		};
	}
}

/**
 * WordPress proxy client with a cookie jar: what the dock's fetch
 * (credentials: same-origin) does, minus the browser.
 */
export class ProxyClient {
	constructor({ wp } = envTargets()) {
		this.wp = wp;
		this.cookies = new Map();
	}

	/** wp-json route helpers. */
	url(path) {
		return `${this.wp}/wp-json/linker-ai/v1/${path}`;
	}

	cookieHeader() {
		return [...this.cookies].map(([k, v]) => `${k}=${v}`).join('; ');
	}

	keepCookies(response) {
		for (const raw of response.headers.getSetCookie?.() ?? []) {
			const [pair] = raw.split(';');
			const eq = pair.indexOf('=');
			const name = pair.slice(0, eq).trim();
			const value = pair.slice(eq + 1).trim();
			// A cleared cookie (empty value, past expiry) leaves the jar.
			if (value === '' || /expires=Thu, 01 Jan 1970/.test(raw)) {
				this.cookies.delete(name);
			} else {
				this.cookies.set(name, value);
			}
		}
	}

	async fetch(path, { method = 'GET', body } = {}) {
		const response = await fetch(this.url(path), {
			method,
			headers: {
				...(body ? { 'Content-Type': 'application/json' } : {}),
				...(this.cookies.size ? { Cookie: this.cookieHeader() } : {}),
			},
			body: body ? JSON.stringify(body) : undefined,
		});
		this.keepCookies(response);
		return response;
	}

	/** POST /genie/turn with the thread, as sendTurn() builds it. */
	async turn({ messages, locale = 'en', page = { type: 'other' } }) {
		const started = Date.now();
		const response = await this.fetch('genie/turn', {
			method: 'POST',
			body: { locale, messages, page },
		});
		const status = response.status;
		const json = status === 200 ? await response.json() : null;
		const stream = json?.stream ?? '';
		return {
			status,
			conversationId: json?.conversation_id ?? null,
			durationMs: Date.now() - started,
			request: { messages, locale, page },
			stream,
			...parseStream(stream),
		};
	}

	async conversation() {
		const response = await this.fetch('genie/conversation');
		return { status: response.status, body: await response.json() };
	}

	async list() {
		const response = await this.fetch('genie/conversations');
		return { status: response.status, body: await response.json() };
	}

	async select(id) {
		const response = await this.fetch('genie/conversations', {
			method: 'POST',
			body: id ? { id } : {},
		});
		return { status: response.status, body: await response.json() };
	}
}

/**
 * A turn transcript entry: the question verbatim, the answer verbatim, the
 * meta the service put on the wire, and how long the turn took.
 */
export function transcriptEntry(step, question, turn) {
	return {
		step,
		sentAt: new Date().toISOString(),
		question,
		durationMs: turn.durationMs,
		status: turn.status,
		meta: turn.meta,
		answer: answerText(turn.blocks),
		blocks: turn.blocks,
	};
}

/** Simple pass/fail note with the criterion it was judged by. */
export function verdict(caseId, passed, criterion, notes) {
	return {
		case: caseId,
		verdict: passed ? 'pass' : 'defect',
		criterion,
		notes,
	};
}

/**
 * Is the text German? Decided on the closed-class words a German sentence
 * cannot avoid (Sie-form verbs, articles, pronouns) plus umlauts; the runner
 * reads the answers themselves for the judgement, this is the mechanical
 * first read.
 */
export function looksGerman(text) {
	const german = [
		/\b(der|die|das|den|dem|ein|eine|einen|und|oder|ist|sind|hat|haben|mit|für|von|zu|im|am|auf)\b/i,
		/\b(sie|ich|wir|nicht|bitte|danke|welche|kann|müssen|sollen|wird|werden|hat|passen|führen)\b/i,
		/[äöüß]/,
	];
	return german.filter((pattern) => pattern.test(text)).length >= 2;
}

export function looksEnglish(text) {
	const english = [
		/\b(the|a|an|and|or|is|are|has|have|with|for|of|to|in|on)\b/i,
		/\b(you|your|we|our|can|will|which|what|please|carry|offer)\b/i,
	];
	return english.filter((pattern) => pattern.test(text)).length >= 2;
}
