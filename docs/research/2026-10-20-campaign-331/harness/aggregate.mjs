/**
 * Aggregates the campaign #331 JSONL evidence into the overview the ticket
 * asks for: scenario × {cases, pass, defect}, with each case's verdict line
 * and the check names that failed.
 *
 * A case id is the stable id (the stamp stripped). A rerun writes a new
 * file with a new stamp; only the greatest stamp is counted, so a second
 * run does not add a second row. Clearing the scenario directory before a
 * rerun is the other half of that, and is written in NOTES.md.
 *
 * Usage: node aggregate.mjs > overview.json
 */

import { readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { stableCaseId, stampOf } from './evidence.mjs';

const ROOT =
	process.env.C331_EVIDENCE ??
	`${process.env.HOME}/de-linker-data/campaign-331`;

/**
 * One row per stable case id: the verdict with the greatest stamp.
 * `rows` is `{ file, entry }[]` in read order.
 */
export function foldCases(rows) {
	const best = new Map();
	for (const row of rows) {
		const entry = row.entry;
		if (!entry || (entry.type !== 'verdict' && entry.verdict === undefined)) {
			continue;
		}
		const id = stableCaseId(entry.case ?? row.file.replace(/\.jsonl$/, ''));
		const stamp = stampOf(entry, row.file);
		const current = best.get(id);
		if (current && stamp < current.stamp) {
			continue;
		}
		if (current && stamp === current.stamp) {
			continue;
		}
		best.set(id, {
			case: id,
			stamp,
			file: row.file,
			verdict: entry.verdict,
			criterion: entry.criterion,
			notes: entry.notes ?? entry.detail ?? undefined,
		});
	}
	return [...best.values()];
}

export function aggregateDirectory(root) {
	const scenarios = readdirSync(root, { withFileTypes: true })
		.filter((entry) => entry.isDirectory() && entry.name !== 'probe' && !entry.name.startsWith('_'))
		.map((entry) => entry.name)
		.sort();
	const overview = {};
	for (const scenario of scenarios) {
		const dir = join(root, scenario);
		const rows = [];
		for (const file of readdirSync(dir).filter((name) => name.endsWith('.jsonl'))) {
			for (const line of readFileSync(join(dir, file), 'utf8').split('\n')) {
				if (!line.trim()) {
					continue;
				}
				try {
					rows.push({ file, entry: JSON.parse(line) });
				} catch {
					// A torn line is skipped; the file stays on disk for the review.
				}
			}
		}
		const list = foldCases(rows);
		overview[scenario] = {
			cases: list.length,
			pass: list.filter((item) => item.verdict === 'pass').length,
			defect: list.filter((item) => item.verdict === 'defect').length,
			detail: list,
		};
	}
	return overview;
}

const invoked =
	process.argv[1] !== undefined &&
	resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invoked) {
	console.log(JSON.stringify(aggregateDirectory(ROOT), null, 2));
}
