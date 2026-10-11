/**
 * The Jev -> DeepSeek cascade behind every Genie question (#13's pilot
 * criteria, reused: `services/genie/eval/judges`, `turns.TURN_THRESHOLDS`).
 *
 * The driver is `score.py`; this module only hands it the items the run just
 * took and reads the labels back. Every item is one question: the question,
 * the answer as the customer reads it, the cards it offered, and the logged
 * turn whose own ability calls are replayed read-only as the reference.
 */

/**
 * External dependencies
 */
import { execFileSync } from 'node:child_process';
import {
	appendFileSync,
	existsSync,
	mkdirSync,
	readFileSync,
	writeFileSync,
} from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';

/**
 * Internal dependencies
 */
import { instance, REPO_ROOT } from './instance';

export interface JudgeItem {
	/** The item's name in the run (`R1-en`, …). */
	id: string;
	question: string;
	answer: string;
	cards: number[];
	/** The product page the row was asked from, when it ran on one. */
	pageProduct?: number;
	/** The service's logged turn; its tool_calls become the reference. */
	turnId: number;
	/** Replace one offered card with this id for the `better_pick` variant. */
	swapTo?: number;
}

export interface Verdict {
	item: string;
	labels: Record<string, string | null>;
	sources: Record<string, string>;
	/** The confidence Jev reported first, before any escalation. */
	jev: Record<string, { label: string | null; confidence: number | null }>;
	/** The abilities the judged turn actually called. */
	referenceCalls: string[];
	/** Each judge's own words, when it gave any. */
	reasons: Record<string, string | null>;
	turnId: number;
}

/** The judges project: its own uv environment, beside the service's. */
export const JUDGES_DIR = join(REPO_ROOT, 'services/genie/eval/judges');

/** Where the Genie service logs its turns (`GENIE_LOG`, app.py `_log_path()`). */
export function turnLogPath(): string {
	return (
		process.env.GENIE_LOG ??
		join(homedir(), '.cache', 'linker-genie', 'turns.sqlite')
	);
}

/**
 * The run's own judge directory, beside the instance's mail: `<instance>/
 * e2e-judge/<stamp>/` (the stamp is the local time the judging started).
 *
 * It is a persistent location, not a temp directory: the per-item records
 * (`run/summary.json`, `run/jev.jsonl`, `run/deepseek.jsonl`,
 * `run/cascade.jsonl`) stay readable after the run, so a disagreement the
 * suite printed can be read back instead of dying with the process.
 */
export function judgeRunDir(when: Date = new Date()): string {
	const pad = (value: number): string => String(value).padStart(2, '0');
	const stamp =
		`${when.getFullYear()}${pad(when.getMonth() + 1)}${pad(when.getDate())}` +
		`-${pad(when.getHours())}${pad(when.getMinutes())}${pad(when.getSeconds())}`;
	return join(instance().dir, 'e2e-judge', stamp);
}

/**
 * The items the run has collected, on disk.
 *
 * A failed test makes Playwright restart the worker process, which
 * re-evaluates this module: an in-memory list would silently lose every row
 * collected before the failure and the judging step would grade only the tail
 * (measured 2026-10-12: a failure on R10-en left 8 of the run's 19 rows judged,
 * and the coverage gate could not see it because it compared the verdicts
 * against the same shortened list). The file is keyed by the runner process
 * (`process.ppid`, stable across a worker restart), so every worker of one
 * `playwright test` run appends to one list, and a fresh run starts clean.
 */
function collectedPath(): string {
	return join(instance().dir, 'e2e-judge', `collected-${process.ppid}.jsonl`);
}

/** Records one collected item; the id is the key, a later record wins. */
export function collectJudgeItem(item: JudgeItem): void {
	const path = collectedPath();
	mkdirSync(dirname(path), { recursive: true });
	appendFileSync(path, JSON.stringify(item) + '\n');
}

/** Every collected item this run, keyed by id, in first-collection order. */
export function collectedJudgeItems(): JudgeItem[] {
	const path = collectedPath();
	if (!existsSync(path)) {
		return [];
	}
	const byId = new Map<string, JudgeItem>();
	for (const line of readFileSync(path, 'utf8').split('\n')) {
		if (line.trim() === '') {
			continue;
		}
		const item = JSON.parse(line) as JudgeItem;
		byId.set(item.id, item);
	}
	return [...byId.values()];
}

/**
 * Judges every item in one `score.py` run; returns the verdicts by item id.
 */
export function judgeItems(items: JudgeItem[]): Record<string, Verdict> {
	if (items.length === 0) {
		return {};
	}
	const directory = judgeRunDir();
	mkdirSync(directory, { recursive: true });
	const input = join(directory, 'items.jsonl');
	const out = join(directory, 'run');
	writeFileSync(
		input,
		items
			.map((item) => {
				const row: Record<string, unknown> = {
					id: item.id,
					question: item.question,
					answer: item.answer,
					cards: item.cards,
					turn_id: item.turnId,
				};
				if (item.pageProduct !== undefined) {
					row.page_product = item.pageProduct;
				}
				if (item.swapTo !== undefined) {
					// The wrong pick replaces a recommended card: the page's own
					// product is a role of its own (score.py's
					// `answer_with_offers`), so it is never the swapped one.
					const from = item.cards.find(
						(id) => id !== item.swapTo && id !== item.pageProduct
					);
					if (from !== undefined) {
						row.swap = { from, to: item.swapTo };
					}
				}
				return JSON.stringify(row);
			})
			.join('\n') + '\n'
	);
	console.log(`judge records: ${directory}`);

	execFileSync(
		'uv',
		[
			'run',
			'--locked',
			'python',
			'score.py',
			'--items',
			input,
			'--out',
			out,
			'--db',
			turnLogPath(),
			'--wp',
			instance().url,
		],
		{
			cwd: JUDGES_DIR,
			encoding: 'utf8',
			stdio: ['ignore', 'pipe', 'pipe'],
			timeout: 900_000,
		}
	);

	const summary = JSON.parse(
		readFileSync(join(out, 'summary.json'), 'utf8')
	) as Array<{
		item: string;
		turn_id: number;
		labels: Record<string, string | null>;
		sources: Record<string, string>;
		jev: Record<
			string,
			{ label: string | null; confidence: number | null }
		>;
		reference_calls: string[];
		reasons?: Record<string, string | null>;
	}>;

	const verdicts: Record<string, Verdict> = {};
	for (const one of summary) {
		verdicts[one.item] = {
			item: one.item,
			labels: one.labels,
			sources: one.sources,
			jev: one.jev,
			referenceCalls: one.reference_calls,
			reasons: one.reasons ?? {},
			turnId: one.turn_id,
		};
	}
	return verdicts;
}
