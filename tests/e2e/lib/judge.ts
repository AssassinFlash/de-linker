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
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join } from 'node:path';

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
 * Judges every item in one `score.py` run; returns the verdicts by item id.
 */
export function judgeItems(items: JudgeItem[]): Record<string, Verdict> {
	if (items.length === 0) {
		return {};
	}
	const directory = mkdtempSync(join(tmpdir(), 'linker-e2e-judge-'));
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
				if (item.swapTo !== undefined) {
					const from = item.cards.find((id) => id !== item.swapTo);
					if (from !== undefined) {
						row.swap = { from, to: item.swapTo };
					}
				}
				return JSON.stringify(row);
			})
			.join('\n') + '\n'
	);

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
