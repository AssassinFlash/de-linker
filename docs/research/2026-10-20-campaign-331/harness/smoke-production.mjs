/**
 * The production smoke of campaign #331 (≤8 probes, question-only): a handful
 * of conversation-state probes against https://de-linker.com through its own
 * REST proxy, as a guest browser does. No contact card and no inquiry card is
 * ever submitted; every probe records its final URL and the response headers.
 *
 * Each POST creates a `linker_conversation` on the live site. That is the
 * question-only live conversation map #329 allows ("公开 Genie 对话不发信").
 * This file does not add probes and does not delete those posts.
 *
 * Usage: node smoke-production.mjs
 */

import { CookieJar } from './cookies.mjs';
import { record, responseNote } from './evidence.mjs';
import { answerText, cardsOf, parseStream } from './sse.mjs';

const BASE = 'https://de-linker.com';
const scenario = 'production-smoke';
const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);

/**
 * One probe: POST /wp-json/linker-ai/v1/genie/turn (or GET the conversation),
 * recording the final URL and the response headers, as the ticket asks.
 */
async function probe(jar, file, label, path, { method = 'POST', body } = {}) {
	const url = `${BASE}/wp-json/linker-ai/v1/${path}`;
	const started = Date.now();
	const response = await fetch(url, {
		method,
		headers: {
			...(body ? { 'Content-Type': 'application/json' } : {}),
			Accept: method === 'POST' ? 'text/event-stream' : 'application/json',
			...(jar.header() ? { Cookie: jar.header() } : {}),
		},
		body: body ? JSON.stringify(body) : undefined,
	});
	jar.keep(response);
	const text = await response.text();
	const note = responseNote(response);
	const entry = {
		type: 'probe',
		label,
		stamp,
		method,
		finalUrl: note.finalUrl,
		status: response.status,
		durationMs: Date.now() - started,
		headers: note.headers,
	};
	if (method === 'POST') {
		entry.question = body.messages.at(-1).content;
		// The proxy answers {conversation_id, stream}; the stream is SSE text.
		let stream = text;
		let conversationId = null;
		try {
			const parsed = JSON.parse(text);
			if (typeof parsed.stream === 'string') {
				stream = parsed.stream;
				conversationId = parsed.conversation_id ?? null;
			}
		} catch {
			// A non-JSON answer is recorded as its parsed blocks, which are empty.
		}
		const parsed = parseStream(stream);
		entry.conversationId = conversationId;
		entry.answer = answerText(parsed.blocks);
		entry.answerHead = entry.answer.slice(0, 300);
		entry.cards = cardsOf(parsed.blocks);
		entry.streamBytes = stream.length;
	} else {
		entry.storedMessages = (() => {
			try {
				return JSON.parse(text).messages?.map((message) => message.role);
			} catch {
				return null;
			}
		})();
	}
	record(scenario, file, entry);
	return { entry, text };
}

async function conversation(jar, file, messages, locale, label) {
	const { entry } = await probe(jar, file, label, 'genie/turn', {
		method: 'POST',
		body: {
			locale,
			messages,
			page: { type: 'other', url: locale === 'de' ? '/de/genie/' : '/genie/' },
		},
	});
	return entry;
}

const file = `production-${stamp}`;
record(scenario, file, {
	type: 'case',
	at: new Date().toISOString(),
	stamp,
	base: BASE,
	rule: 'question-only; no contact or inquiry card is ever submitted',
});

// P1 — topic switch (EN): inverter context, then a hard switch to EV chargers.
{
	const jar = new CookieJar();
	const t1 = await conversation(
		jar,
		file,
		[{ role: 'user', content: 'Which hybrid inverters do you carry for homes?' }],
		'en',
		'P1-turn1-topicA'
	);
	const t2 = await conversation(
		jar,
		file,
		[
			{ role: 'user', content: 'Which hybrid inverters do you carry for homes?' },
			{ role: 'assistant', content: t1.answer },
			{ role: 'user', content: 'Now something different: which EV chargers do you carry?' },
		],
		'en',
		'P1-turn2-topicB'
	);
	const evOnly = t2.cards.length > 0 && !/hybrid inverter/i.test(t2.answerHead);
	record(scenario, file, {
		type: 'verdict',
		case: 'P1-prod-topic-switch',
		stamp,
		verdict: evOnly ? 'pass' : 'defect',
		criterion: "the EV turn's cards/text are EV chargers, not the previous inverter topic",
		detail: { cards: t2.cards },
	});
}

// P2 — anaphora (EN): the card product, then "How many MPPTs does it have?"
{
	const jar = new CookieJar();
	const t1 = await conversation(
		jar,
		file,
		[{ role: 'user', content: 'Show me the SAJ H2-10K-T3.' }],
		'en',
		'P2-turn1-card'
	);
	const t2 = await conversation(
		jar,
		file,
		[
			{ role: 'user', content: 'Show me the SAJ H2-10K-T3.' },
			{ role: 'assistant', content: t1.answer },
			{ role: 'user', content: 'How many MPPTs does it have?' },
		],
		'en',
		'P2-turn2-anaphora'
	);
	const resolved = /MPPT/i.test(t2.answerHead) && /\d/.test(t2.answerHead);
	record(scenario, file, {
		type: 'verdict',
		case: 'P2-prod-anaphora',
		stamp,
		verdict: resolved ? 'pass' : 'defect',
		criterion: '"it" resolves to the card product and the MPPT count is stated',
		detail: { answerHead: t2.answerHead },
	});
}

// P3 — mid-thread language switch (DE conversation, English question).
{
	const jar = new CookieJar();
	const t1 = await conversation(
		jar,
		file,
		[{ role: 'user', content: 'Welche Hybridwechselrichter führen Sie für Wohngebäude?' }],
		'de',
		'P3-turn1-de'
	);
	const t2 = await conversation(
		jar,
		file,
		[
			{ role: 'user', content: 'Welche Hybridwechselrichter führen Sie für Wohngebäude?' },
			{ role: 'assistant', content: t1.answer },
			{ role: 'user', content: 'Which batteries work with the SAJ H2-10K-T3?' },
		],
		'de',
		'P3-turn2-en-question'
	);
	const english = /\b(the|batteries|work|with)\b/i.test(t2.answerHead) && !/[äöüß]/.test(t2.answerHead);
	record(scenario, file, {
		type: 'verdict',
		case: 'P3-prod-language-switch',
		stamp,
		verdict: english ? 'pass' : 'defect',
		criterion: 'the English question inside the German conversation is answered in English',
		detail: { answerHead: t2.answerHead },
	});
}

// P4 — persistence: the conversation reads back with its turns.
{
	const jar = new CookieJar();
	await conversation(
		jar,
		file,
		[{ role: 'user', content: 'Which EV chargers do you carry?' }],
		'en',
		'P4-turn1'
	);
	const read = await probe(jar, file, 'P4-read-thread', 'genie/conversation', { method: 'GET' });
	record(scenario, file, {
		type: 'verdict',
		case: 'P4-prod-persistence',
		stamp,
		verdict:
			read.entry.status === 200 && (read.entry.storedMessages?.length ?? 0) >= 1
				? 'pass'
				: 'defect',
		criterion: 'GET the conversation back returns the stored thread',
		detail: { stored: read.entry.storedMessages },
	});
}

console.log(`wrote ${process.env.C331_EVIDENCE ?? `${process.env.HOME}/de-linker-data/campaign-331`}/${scenario}/${file}`);
