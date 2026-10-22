/** Editable document history; selection, camera and remote-query state stay out. */
export interface History<T> {
	current: T;
	past: readonly T[];
	future: readonly T[];
	serial: number;
}

export function newHistory<T>(current: T): History<T> {
	return { current, past: [], future: [], serial: 0 };
}

export function change<T>(
	history: History<T>,
	next: T,
	maxEntries: number,
): History<T> {
	if (!Number.isSafeInteger(maxEntries) || maxEntries < 1)
		throw new Error("invalid_history_policy");
	if (next === history.current) return history;
	return {
		current: next,
		past: [...history.past, history.current].slice(-maxEntries),
		future: [],
		serial: history.serial + 1,
	};
}

export function undo<T>(history: History<T>): History<T> {
	const current = history.past.at(-1);
	if (current === undefined) return history;
	return {
		current,
		past: history.past.slice(0, -1),
		future: [history.current, ...history.future],
		serial: history.serial + 1,
	};
}

export function redo<T>(history: History<T>): History<T> {
	const current = history.future[0];
	if (current === undefined) return history;
	return {
		current,
		past: [...history.past, history.current],
		future: history.future.slice(1),
		serial: history.serial + 1,
	};
}
