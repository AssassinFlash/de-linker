/**
 * Unit tests for the #331 harness: the SSE parser, the clients' evidence
 * (redaction, cookies, headers), and the verdict checks (product resolution,
 * structure, rerun folding).
 *
 * Run: node --test harness.test.mjs
 */

import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { foldCases } from './aggregate.mjs';
import {
	hasNextStep,
	hasRequiredTypes,
	mentionsProduct,
	structuresMatch,
	switchedStructureOk,
} from './assertions.mjs';
import { CookieJar } from './cookies.mjs';
import { ProxyClient, ServiceClient } from './client.mjs';
import {
	evidenceRoot,
	record,
	responseNote,
	scanDirectory,
	selectedHeaders,
	tokenShapes,
	verdict,
} from './evidence.mjs';
import { provenanceFields } from './grounding.mjs';
import { parseStream } from './sse.mjs';

const TOKEN = 'ab'.repeat(32);

function tempEvidence() {
	const root = mkdtempSync(join(tmpdir(), 'c331-'));
	process.env.C331_EVIDENCE = root;
	return root;
}

test('parseStream keeps meta, blocks and done, and skips a torn event', () => {
	const parsed = parseStream(
		'event: meta\ndata: {"language":"en","route":"products"}\n\n' +
			'event: block\ndata: {"type":"text","text":"These fit.","refs":[]}\n\n' +
			'event: block\ndata: {"type":"cards","product_ids":[1,2]}\n\n' +
			'event: done\ndata: {"ok":true}\n\n' +
			'event: block\ndata: {not json}\n\n'
	);
	assert.equal(parsed.meta.language, 'en');
	assert.deepEqual(
		parsed.blocks.map((block) => block.type),
		['text', 'cards']
	);
	assert.equal(parsed.done, true);
	assert.equal(parsed.events.length, 4);
});

test('parseStream of an empty body is not done and has no blocks', () => {
	const parsed = parseStream('');
	assert.equal(parsed.done, false);
	assert.deepEqual(parsed.blocks, []);
	assert.equal(parsed.meta, null);
});

test('a case header that carried the service token is written without a token-shaped value', () => {
	const root = tempEvidence();
	try {
		const written = record('s1-topic-switch', 's1-en-example', {
			type: 'case',
			targets: {
				wp: 'http://127.0.0.1:9165',
				genie: 'http://127.0.0.1:9167',
				token: TOKEN,
			},
			note: `leaked ${TOKEN} in a string`,
		});
		assert.equal(written.targets.token, '[redacted]');
		assert.equal(written.note, 'leaked [redacted] in a string');
		const file = join(root, 's1-topic-switch', 's1-en-example.jsonl');
		const text = readFileSync(file, 'utf8');
		assert.deepEqual(tokenShapes(text), []);
		assert.equal(text.includes(TOKEN), false);
		assert.deepEqual(scanDirectory(root), []);
	} finally {
		rmSync(root, { recursive: true, force: true });
		delete process.env.C331_EVIDENCE;
	}
});

test('scanDirectory fails a file that still holds a token-shaped value and skips the token file', () => {
	const root = tempEvidence();
	try {
		writeFileSync(join(root, 'service-token.txt'), TOKEN);
		const dir = join(root, 's2-anaphora');
		// record() refuses a token, so the leftover is written as raw bytes,
		// the way the historical JSONL was.
		mkdirSync(dir);
		writeFileSync(join(dir, 'old.jsonl'), JSON.stringify({ token: TOKEN }) + '\n');
		const hits = scanDirectory(root);
		assert.equal(hits.length, 1);
		assert.equal(hits[0].count, 1);
	} finally {
		rmSync(root, { recursive: true, force: true });
		delete process.env.C331_EVIDENCE;
	}
});

test('two headers in a row are both redacted', () => {
	const root = tempEvidence();
	try {
		record('s0', 'one', { token: TOKEN, other: 'cd'.repeat(32) });
		record('s0', 'two', { note: TOKEN });
		assert.deepEqual(scanDirectory(root), []);
		assert.equal(evidenceRoot(), root);
	} finally {
		rmSync(root, { recursive: true, force: true });
		delete process.env.C331_EVIDENCE;
	}
});

test('selected headers match the production probe and do not copy cf-ray', () => {
	const headers = {
		get(name) {
			const values = {
				'content-type': 'application/json; charset=UTF-8',
				server: 'LiteSpeed',
				'cf-ray': 'abcd1234',
			};
			return values[name] ?? null;
		},
	};
	assert.deepEqual(selectedHeaders(headers), {
		'content-type': 'application/json; charset=UTF-8',
		'cache-control': undefined,
		server: 'LiteSpeed',
		'x-powered-by': undefined,
		'cf-ray': 'present',
	});
	const note = responseNote({
		url: 'http://127.0.0.1:9167/turn',
		status: 200,
		headers,
	});
	assert.equal(note.finalUrl, 'http://127.0.0.1:9167/turn');
	assert.equal(JSON.stringify(note).includes('abcd1234'), false);
});

test('the cookie jar stores, joins, and drops a cleared or expired cookie', () => {
	const jar = new CookieJar();
	const response = {
		headers: {
			getSetCookie: () => [
				'linker_guest=abc; Path=/',
				'empty=; Path=/',
				'gone=old; Expires=Thu, 01 Jan 1970 00:00:00 GMT',
			],
		},
	};
	jar.keep(response);
	assert.equal(jar.header(), 'linker_guest=abc');
	jar.keep({
		headers: {
			getSetCookie: () => ['linker_guest=; Path=/'],
		},
	});
	assert.equal(jar.header(), '');
});

test('ServiceClient records the final URL and selected headers and not the token', async () => {
	let seen = null;
	const client = new ServiceClient({
		genie: 'http://genie.test',
		token: TOKEN,
		fetchImpl: async (url, init) => {
			seen = { url, init };
			return {
				url: 'http://genie.test/turn',
				status: 200,
				headers: {
					get(name) {
						return name === 'content-type' ? 'text/event-stream' : null;
					},
				},
				async text() {
					return (
						'event: meta\ndata: {"language":"en"}\n\n' +
						'event: block\ndata: {"type":"text","text":"Hi","refs":[]}\n\n' +
						'event: done\ndata: {"ok":true}\n\n'
					);
				},
			};
		},
	});
	const turn = await client.turn({
		conversationId: 'c',
		messages: [{ role: 'user', content: 'Hi' }],
	});
	assert.equal(seen.init.headers['X-Linker-Service-Token'], TOKEN);
	assert.equal(turn.finalUrl, 'http://genie.test/turn');
	assert.equal(turn.headers['content-type'], 'text/event-stream');
	assert.equal(turn.done, true);
	assert.equal(JSON.stringify(turn).includes(TOKEN), false);
});

test('ProxyClient keeps the cookie and records the final URL', async () => {
	const client = new ProxyClient({
		wp: 'http://wp.test',
		fetchImpl: async () => ({
			url: 'http://wp.test/wp-json/linker-ai/v1/genie/turn',
			status: 200,
			headers: {
				get: () => null,
				getSetCookie: () => ['wordpress_logged_in=secret; Path=/'],
			},
			async json() {
				return {
					conversation_id: 9,
					stream:
						'event: block\ndata: {"type":"text","text":"Ok","refs":[]}\n\n' +
						'event: done\ndata: {"ok":true}\n\n',
				};
			},
		}),
	});
	const turn = await client.turn({
		messages: [{ role: 'user', content: 'Hi' }],
	});
	assert.equal(turn.conversationId, 9);
	assert.equal(turn.finalUrl, 'http://wp.test/wp-json/linker-ai/v1/genie/turn');
	assert.equal(client.jar.header(), 'wordpress_logged_in=secret');
	assert.equal(JSON.stringify(turn).includes('secret'), false);
});

test('verdict names pass or defect and strips the stamp from the case id', () => {
	assert.deepEqual(verdict('s2-en-its-warranty-20261019092144', true, 'named', 'note'), {
		type: 'verdict',
		case: 's2-en-its-warranty',
		verdict: 'pass',
		criterion: 'named',
		notes: 'note',
	});
	assert.equal(verdict('s3-de-to-en', false, 'structure').verdict, 'defect');
});

test('the word warranty does not resolve "it"; the model or the card does', () => {
	const product = { id: 4107, model: 'H2-10K-T3', sku: 'DLK-SAJ-H210KT3' };
	assert.equal(
		mentionsProduct('The warranty is ten years.', [], product),
		false
	);
	assert.equal(
		mentionsProduct('The H2-10K-T3 warranty is ten years.', [], product),
		true
	);
	assert.equal(
		mentionsProduct('See the card.', [{ type: 'cards', product_ids: [4107] }], product),
		true
	);
	assert.equal(
		mentionsProduct('SKU DLK-SAJ-H210KT3 is covered.', [], product),
		true
	);
});

test('S3 structure requires text and cards, a next step, and no contact card', () => {
	const pairing = [
		{ type: 'text', text: 'These batteries pair.' },
		{ type: 'cards', product_ids: [1] },
		{ type: 'document', ref: 'compat.document.1.0' },
	];
	assert.equal(hasRequiredTypes(pairing, ['text', 'cards']), true);
	assert.equal(hasNextStep(pairing), true);
	assert.equal(switchedStructureOk(pairing, true), true);
	assert.equal(
		switchedStructureOk([{ type: 'text', text: 'No card and no question.' }], true),
		false
	);
	const vacuous = [{ type: 'text', text: 'x' }];
	// The old check was `length > 0 && done && (contact === null || true)`.
	// A text-only done turn must now fail.
	assert.equal(vacuous.length > 0 && true, true);
	assert.equal(switchedStructureOk(vacuous, true), false);
});

test('EN and DE twins match on block types and card sets', () => {
	const en = [
		{ type: 'text', text: 'Batteries.' },
		{ type: 'cards', product_ids: [2, 1] },
		{ type: 'document', ref: 'a' },
	];
	const de = [
		{ type: 'text', text: 'Batterien.' },
		{ type: 'document', ref: 'b' },
		{ type: 'cards', product_ids: [1, 2] },
	];
	const same = structuresMatch(en, de);
	assert.equal(same.typesEqual, true);
	assert.equal(same.cardsEqual, true);
	const drifted = structuresMatch(en, [
		{ type: 'text', text: 'Only text?' },
	]);
	assert.equal(drifted.typesEqual, false);
	assert.equal(drifted.cardsEqual, false);
});

test('a rerun does not add a second overview row for the same case', () => {
	const older = {
		file: 's1-en-inverter-to-ev-20261019092144.jsonl',
		entry: {
			type: 'verdict',
			case: 's1-en-inverter-to-ev-20261019092144',
			verdict: 'pass',
			criterion: 'old',
		},
	};
	const newer = {
		file: 's1-en-inverter-to-ev-20261019120000.jsonl',
		entry: {
			verdict: 'defect',
			case: 's1-en-inverter-to-ev-20261019120000',
			criterion: 'new',
		},
	};
	const folded = foldCases([older, newer, older]);
	assert.equal(folded.length, 1);
	assert.equal(folded[0].case, 's1-en-inverter-to-ev');
	assert.equal(folded[0].verdict, 'defect');
	assert.equal(folded[0].stamp, '20261019120000');
});

test('provenance records the snapshot id and the git revision', () => {
	const fields = provenanceFields(
		JSON.stringify({
			name: '20261019-1409',
			taken: '2026-10-19T06:21:25+00:00',
			loaded: '2026-10-19T09:11:18+00:00',
		}),
		'62b7616ef058bea7a246bc92ef40deb186954e8e'
	);
	assert.equal(fields.snapshot, '20261019-1409');
	assert.equal(fields.git_rev, '62b7616ef058bea7a246bc92ef40deb186954e8e');
	assert.equal(provenanceFields(null, null).snapshot, null);
});

test('the drivers no longer carry the no-op checks', () => {
	const names = [
		'scenarios-direct.mjs',
		'scenarios-proxy.mjs',
		'smoke-production.mjs',
		'client.mjs',
	];
	const banned = ['|| true', 'slice(0, 0)', 'looksGerman', 'looksEnglish', 'serializedOrMerged', 'bodyHead'];
	for (const name of names) {
		const text = readFileSync(new URL(`./${name}`, import.meta.url), 'utf8');
		for (const phrase of banned) {
			assert.equal(text.includes(phrase), false, `${name} still has ${phrase}`);
		}
	}
	const direct = readFileSync(new URL('./scenarios-direct.mjs', import.meta.url), 'utf8');
	assert.equal(direct.includes('4107'), false);
	const browser = readFileSync(new URL('./browser.spec.ts', import.meta.url), 'utf8');
	assert.equal(browser.includes('function record'), false);
	assert.equal(browser.includes('homeStorageIds'), false);
	assert.equal(browser.includes('180_000'), false);
	assert.equal(browser.includes('70_000'), false);
	assert.equal(browser.includes('finally'), true);
	assert.equal(browser.includes('writeVerdict'), true);
});
