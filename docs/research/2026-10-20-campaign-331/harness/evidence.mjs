/**
 * JSONL evidence for campaign #331.
 *
 * A case header used to embed `targets`, and `targets.token` is the Genie
 * service token (`secrets.token_hex(32)`, 64 hex characters;
 * tools/local/src/linker_local/services.py). Every value is redacted before
 * it is written. The token file under the evidence root stays; it is how
 * the driver authenticates, and it is not a case header.
 */

import { appendFileSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

import { answerText } from './sse.mjs';

/** 64 hex characters: the shared service token's shape, and nothing shorter. */
export function tokenShapePattern() {
	return /[0-9a-fA-F]{64}/g;
}

const SECRET_KEY =
	/^(token|secret|password|authorization|cookie|set-cookie|x-linker-service-token)$/i;

/**
 * Response headers the production probes keep (smoke-production's probe
 * record). `cf-ray` is recorded as present or absent: the ray id is not
 * part of the verdict, and it is not copied out.
 */
export const HEADER_NAMES = [
	'content-type',
	'cache-control',
	'server',
	'x-powered-by',
	'cf-ray',
];

export function evidenceRoot() {
	return (
		process.env.C331_EVIDENCE ??
		`${process.env.HOME}/de-linker-data/campaign-331`
	);
}

/** The case id without a trailing `-YYYYMMDDHHMMSS` stamp. */
export function stableCaseId(caseId) {
	return String(caseId ?? '').replace(/-\d{14}$/, '');
}

/** Stamp from an entry, else the 14 digits at the end of a file name. */
export function stampOf(entry, file) {
	if (entry && entry.stamp !== undefined && entry.stamp !== null && entry.stamp !== '') {
		return String(entry.stamp);
	}
	const match = String(file ?? '').match(/(\d{14})(?:\.jsonl)?$/);
	return match ? match[1] : '';
}

function headerGet(headers, name) {
	if (!headers) {
		return undefined;
	}
	if (typeof headers.get === 'function') {
		return headers.get(name) ?? undefined;
	}
	const wanted = name.toLowerCase();
	for (const [key, value] of Object.entries(headers)) {
		if (key.toLowerCase() === wanted) {
			return value;
		}
	}
	return undefined;
}

/** The production probe's header selection, for every driver. */
export function selectedHeaders(headers) {
	const ray = headerGet(headers, 'cf-ray');
	return {
		'content-type': headerGet(headers, 'content-type'),
		'cache-control': headerGet(headers, 'cache-control'),
		server: headerGet(headers, 'server'),
		'x-powered-by': headerGet(headers, 'x-powered-by'),
		'cf-ray': ray ? 'present' : undefined,
	};
}

/** finalUrl + the selected headers of one response. */
export function responseNote(response) {
	return {
		finalUrl: response?.url ?? null,
		status: response?.status ?? null,
		headers: selectedHeaders(response?.headers),
	};
}

/**
 * Replace a secret field and any token-shaped string.
 * `seen` breaks a cyclic object; evidence entries are acyclic, the guard
 * is there so a caller's mistake cannot recurse forever.
 */
export function redact(value, seen = new WeakSet()) {
	if (typeof value === 'string') {
		return value.replace(tokenShapePattern(), '[redacted]');
	}
	if (Array.isArray(value)) {
		return value.map((item) => redact(item, seen));
	}
	if (value && typeof value === 'object') {
		if (seen.has(value)) {
			return null;
		}
		seen.add(value);
		const out = {};
		for (const [key, item] of Object.entries(value)) {
			out[key] = SECRET_KEY.test(key) && item ? '[redacted]' : redact(item, seen);
		}
		return out;
	}
	return value;
}

/** Token-shaped substrings. A non-empty result is a failed scan. */
export function tokenShapes(text) {
	return String(text ?? '').match(tokenShapePattern()) ?? [];
}

/** One JSONL evidence line. The written bytes are redacted first. */
export function record(scenario, file, entry) {
	const safe = redact(entry);
	const path = `${evidenceRoot()}/${scenario}/${file}.jsonl`;
	mkdirSync(dirname(path), { recursive: true });
	const line = JSON.stringify(safe);
	if (tokenShapes(line).length > 0) {
		throw new Error(`refusing to write a token-shaped value to ${path}`);
	}
	appendFileSync(path, line + '\n');
	return safe;
}

/** Raw artefacts (thread dumps) beside the JSONL. Strings are redacted too. */
export function artefact(scenario, name, body) {
	const path = `${evidenceRoot()}/${scenario}/${name}`;
	mkdirSync(dirname(path), { recursive: true });
	const safe = typeof body === 'string' ? redact(body) : JSON.stringify(redact(body), null, 2);
	if (tokenShapes(safe).length > 0) {
		throw new Error(`refusing to write a token-shaped value to ${path}`);
	}
	writeFileSync(path, safe);
	return path;
}

/**
 * Walk a directory and report files whose text contains a token-shaped
 * value. `service-token.txt` is the driver's own secret and is skipped.
 */
export function scanDirectory(root) {
	const hits = [];
	const walk = (dir) => {
		for (const entry of readdirSync(dir, { withFileTypes: true })) {
			const path = join(dir, entry.name);
			if (entry.isDirectory()) {
				walk(path);
				continue;
			}
			if (!entry.isFile() || entry.name === 'service-token.txt') {
				continue;
			}
			const count = tokenShapes(readFileSync(path, 'utf8')).length;
			if (count > 0) {
				hits.push({ file: path, count });
			}
		}
	};
	walk(root);
	return hits;
}

/** Pass/fail note. `caseId` is the stable id; put the stamp in `extra`. */
export function verdict(caseId, passed, criterion, notes, extra = {}) {
	return {
		type: 'verdict',
		case: stableCaseId(caseId),
		verdict: passed ? 'pass' : 'defect',
		criterion,
		notes,
		...extra,
	};
}

/**
 * One turn: the question, the answer, the meta, the duration, and where
 * the response actually came from.
 */
export function transcriptEntry(step, question, turn) {
	return {
		step,
		sentAt: new Date().toISOString(),
		question,
		durationMs: turn.durationMs,
		status: turn.status,
		finalUrl: turn.finalUrl ?? null,
		headers: turn.headers ?? null,
		meta: turn.meta,
		answer: answerText(turn.blocks),
		blocks: turn.blocks,
	};
}
