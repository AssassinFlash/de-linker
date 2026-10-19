/**
 * The persistence-and-concurrency battery of campaign #331 against the
 * WordPress proxy (what the dock talks to), no browser: two turns in flight
 * on one conversation at the same time, and what the stored thread keeps.
 *
 * Dossier §1.16 says the service has no per-conversation serialization:
 * `Proxy::turn` records the request's whole thread (Thread::record), so the
 * later-finishing turn replaces the earlier one's record wholesale. This
 * script produces the evidence either way: both SSE answers, what each
 * carried, and what `GET /genie/conversation` keeps afterwards.
 *
 * Usage: node scenarios-proxy.mjs
 */

import { answerText, parseStream } from './sse.mjs';
import {
	ProxyClient,
	artefact,
	cardsOf,
	envTargets,
	publicTargets,
	record,
	transcriptEntry,
	verdict,
} from './client.mjs';

const targets = envTargets();
const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);

/**
 * One concurrency case: a base turn first (so the conversation exists with a
 * settled thread), then two turns posted at the same millisecond on top of
 * that same base thread — the state two tabs (or tab + hero) would each
 * believe is current.
 */
async function concurrentTurns(lang) {
	const scenario = 's8-concurrency';
	const file = `s8-${lang}-proxy-concurrent-${stamp}`;
	const de = lang === 'de';
	record(scenario, file, {
		type: 'case',
		at: new Date().toISOString(),
		description: de
			? 'Zwei gleichzeitige Runden auf einer Konversation über den Proxy: behält der gespeicherte Faden beide?'
			: 'Two simultaneous turns on one conversation through the proxy: does the stored thread keep both?',
		stamp,
		targets: publicTargets(targets),
	});

	const client = new ProxyClient(targets);
	const baseQuestion = de
		? 'Welche Hybridwechselrichter führen Sie für Wohngebäude?'
		: 'Which hybrid inverters do you carry for homes?';
	const base = await client.turn({
		messages: [{ role: 'user', content: baseQuestion }],
		locale: lang,
	});
	record(scenario, file, {
		type: 'turn',
		step: 'base',
		...transcriptEntry(1, baseQuestion, base),
		conversationId: base.conversationId,
	});
	if (base.status !== 200) {
		record(
			scenario,
			file,
			verdict(file, false, 'the base turn must answer', `status ${base.status}`)
		);
		return { passed: false };
	}

	// The stored thread the two racing turns both build on, as the dock would
	// hold it: the question, the answer's text, and (for this race) each tab
	// appending its own question on top.
	const baseAnswer = answerText(base.blocks);
	const baseThread = [
		{ role: 'user', content: baseQuestion },
		...(baseAnswer ? [{ role: 'assistant', content: baseAnswer }] : []),
	];
	const qa = de
		? 'Welche Wallboxen führen Sie?'
		: 'Which EV chargers do you carry?';
	const qb = de
		? 'Welche Heim-Speicherbatterien führen Sie?'
		: 'Which home storage batteries do you carry?';
	const messagesA = [...baseThread, { role: 'user', content: qa }];
	const messagesB = [...baseThread, { role: 'user', content: qb }];

	const started = Date.now();
	const [a, b] = await Promise.all([
		client.turn({ messages: messagesA, locale: lang }),
		client.turn({ messages: messagesB, locale: lang }),
	]);
	record(scenario, file, {
		type: 'turn',
		step: 'race-A',
		question: qa,
		startedOffsetMs: 0,
		...transcriptEntry(2, qa, a),
	});
	record(scenario, file, {
		type: 'turn',
		step: 'race-B',
		question: qb,
		...transcriptEntry(2, qb, b),
	});

	const after = await client.conversation();
	artefact(scenario, `${file}-after.json`, after.body);
	record(scenario, file, {
		type: 'read',
		finalUrl: after.finalUrl,
		status: after.status,
		headers: after.headers,
	});
	const kept = after.body.messages ?? [];
	const keptQuestions = kept
		.filter((m) => m.role === 'user')
		.map((m) => m.content);
	const streamText = answerText(parseStream(after.body.stream ?? '').blocks);
	const bothAnswered = a.status === 200 && b.status === 200;
	const bothKept =
		keptQuestions.includes(qa) && keptQuestions.includes(qb);
	record(scenario, file, {
		type: 'check',
		name: 'what the stored thread kept of the two racing turns',
		bothAnswered,
		keptQuestions,
		storedAnswerHead: streamText.slice(0, 200),
		lost:
			bothKept
				? []
				: [qa, qb].filter((q) => !keptQuestions.includes(q)),
		detail: {
			durations: { a: a.durationMs, b: b.durationMs },
			cardsA: cardsOf(a.blocks),
			cardsB: cardsOf(b.blocks),
			baseAnswerKept: kept.some((m) => m.content === baseAnswer),
		},
	});

	const passed = bothAnswered && bothKept;
	record(
		scenario,
		file,
		verdict(
			file,
			passed,
			bothKept
				? 'both racing turns survive in the stored thread (serialized or merged server-side)'
				: 'both turns answered (SSE 200) but the stored thread kept only one racing turn — the other turn is lost from history (last-write-wins, dossier §1.16)',
			`kept=${JSON.stringify(keptQuestions)}`
		)
	);
	return { passed, bothAnswered, bothKept, lost: [qa, qb].filter((q) => !keptQuestions.includes(q)) };
}

const summary = [];
for (const lang of ['en', 'de']) {
	console.log(`[c331] s8 proxy concurrency ${lang} …`);
	try {
		summary.push({ name: `s8-${lang}-proxy-concurrent`, ...(await concurrentTurns(lang)) });
	} catch (error) {
		summary.push({ name: `s8-${lang}-proxy-concurrent`, error: String(error) });
		console.error(error);
	}
}
artefact('.', `summary-proxy-${stamp}.json`, summary);
console.log(JSON.stringify(summary, null, 2));
