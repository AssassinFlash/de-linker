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
 * write is JSONL under ~/de-linker-data/campaign-331/. The service token is
 * read here and sent on the direct client's request. It is never written
 * into a case header (`evidence.mjs` redacts before the write).
 */

import { readFileSync } from 'node:fs';

import { CookieJar } from './cookies.mjs';
import { evidenceRoot, responseNote } from './evidence.mjs';
import {
	answerText,
	cardsOf,
	contactOf,
	handoffOf,
	parseStream,
} from './sse.mjs';
import { TURN_TIMEOUT_MS } from './timing.mjs';

export {
	answerText,
	cardsOf,
	contactOf,
	handoffOf,
	parseStream,
};
export {
	artefact,
	record,
	responseNote,
	selectedHeaders,
	transcriptEntry,
	verdict,
} from './evidence.mjs';

/**
 * The instance this harness ran against. The shared service token comes from
 * the environment, or from a one-line file (C331_TOKEN_FILE) under the
 * evidence root — never from the repository.
 */
export function envTargets() {
	const root = evidenceRoot();
	const tokenFile = process.env.C331_TOKEN_FILE ?? `${root}/service-token.txt`;
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

/**
 * What a case header may say about the targets. The token is present or
 * absent, never its value.
 */
export function publicTargets(targets = envTargets()) {
	return {
		wp: targets.wp,
		genie: targets.genie,
		token: targets.token ? '[redacted]' : '',
	};
}

/**
 * Direct-service client. `conversationId` stays stable across one case so the
 * service's own turn log (repeat-offer bookkeeping) sees one conversation.
 *
 * `timeoutMs` defaults to TURN_TIMEOUT_MS (timing.mjs): the e2e panel's
 * 180 s abort, not the proxy's 60 s.
 */
export class ServiceClient {
	constructor({ genie, token, fetchImpl } = envTargets()) {
		this.genie = genie;
		this.token = token;
		this.fetchImpl = fetchImpl ?? fetch;
	}

	async turn({
		conversationId,
		messages,
		locale = 'en',
		page = { type: 'other' },
		timeoutMs = TURN_TIMEOUT_MS,
	}) {
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
		let stream = '';
		let status = 0;
		let note = { finalUrl: null, status: 0, headers: null };
		try {
			const response = await this.fetchImpl(`${this.genie}/turn`, {
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
			note = responseNote(response);
			stream = await response.text();
		} finally {
			clearTimeout(timer);
		}
		return {
			request: body,
			status,
			durationMs: Date.now() - started,
			stream,
			finalUrl: note.finalUrl,
			headers: note.headers,
			...parseStream(stream),
		};
	}
}

/**
 * WordPress proxy client with a cookie jar: what the dock's fetch
 * (credentials: same-origin) does, minus the browser.
 */
export class ProxyClient {
	constructor({ wp, fetchImpl } = envTargets()) {
		this.wp = wp;
		this.fetchImpl = fetchImpl ?? fetch;
		this.jar = new CookieJar();
	}

	/** wp-json route helpers. */
	url(path) {
		return `${this.wp}/wp-json/linker-ai/v1/${path}`;
	}

	async fetch(path, { method = 'GET', body } = {}) {
		const response = await this.fetchImpl(this.url(path), {
			method,
			headers: {
				...(body ? { 'Content-Type': 'application/json' } : {}),
				...(this.jar.header() ? { Cookie: this.jar.header() } : {}),
			},
			body: body ? JSON.stringify(body) : undefined,
		});
		this.jar.keep(response);
		return response;
	}

	/** POST /genie/turn with the thread, as sendTurn() builds it. */
	async turn({ messages, locale = 'en', page = { type: 'other' } }) {
		const started = Date.now();
		const response = await this.fetch('genie/turn', {
			method: 'POST',
			body: { locale, messages, page },
		});
		const note = responseNote(response);
		const json = response.status === 200 ? await response.json() : null;
		const stream = json?.stream ?? '';
		return {
			status: response.status,
			conversationId: json?.conversation_id ?? null,
			durationMs: Date.now() - started,
			request: { messages, locale, page },
			stream,
			finalUrl: note.finalUrl,
			headers: note.headers,
			...parseStream(stream),
		};
	}

	async conversation() {
		const response = await this.fetch('genie/conversation');
		const note = responseNote(response);
		return { ...note, body: await response.json() };
	}

	async list() {
		const response = await this.fetch('genie/conversations');
		const note = responseNote(response);
		return { ...note, body: await response.json() };
	}

	async select(id) {
		const response = await this.fetch('genie/conversations', {
			method: 'POST',
			body: id ? { id } : {},
		});
		const note = responseNote(response);
		return { ...note, body: await response.json() };
	}
}
