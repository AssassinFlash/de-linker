/**
 * Aggregates the campaign #331 JSONL evidence into the overview the ticket
 * asks for: scenario × {cases, pass, defect}, with each case's verdict line
 * and the check names that failed.
 *
 * Usage: node aggregate.mjs > overview.json
 */

import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT =
	process.env.C331_EVIDENCE ??
	`${process.env.HOME}/de-linker-data/campaign-331`;

const scenarios = readdirSync(ROOT, { withFileTypes: true })
	.filter((d) => d.isDirectory() && d.name !== 'probe' && !d.name.startsWith('_'))
	.map((d) => d.name)
	.sort();

const overview = {};
for (const scenario of scenarios) {
	const dir = join(ROOT, scenario);
	/** One case file may hold several cases (browser spec appends per check). */
	const cases = new Map();
	for (const file of readdirSync(dir).filter((f) => f.endsWith('.jsonl'))) {
		for (const line of readFileSync(join(dir, file), 'utf8').split('\n')) {
			if (!line.trim()) {
				continue;
			}
			let entry;
			try {
				entry = JSON.parse(line);
			} catch {
				continue;
			}
			// A case is identified by its verdict line (type omitted by the
			// direct runner, spelled out by the browser spec).
			if (entry.type === 'verdict' || entry.verdict !== undefined) {
				const id = entry.case ?? file.replace(/\.jsonl$/, '');
				cases.set(id, {
					case: id,
					file,
					verdict: entry.verdict,
					criterion: entry.criterion,
					notes: entry.notes ?? entry.detail ?? undefined,
				});
			}
		}
	}
	const list = [...cases.values()];
	overview[scenario] = {
		cases: list.length,
		pass: list.filter((c) => c.verdict === 'pass').length,
		defect: list.filter((c) => c.verdict === 'defect').length,
		detail: list,
	};
}

console.log(JSON.stringify(overview, null, 2));
