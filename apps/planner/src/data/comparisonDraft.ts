import type { JsonObject } from "./protocol.ts";

const key = "linker-comparison-draft";

export interface ComparisonDraft {
	id: string;
	scope: string;
	source: string;
	title: string;
	scene?: "new" | "known" | "retrofit" | "commercial" | null;
	inputs: JsonObject | null;
	useHints: boolean;
	languageUrl?: string;
	usePvAddress?: boolean;
	carriedProduct?: boolean;
}

export function hasComparisonDraft(): boolean {
	try {
		const saved = JSON.parse(window.sessionStorage.getItem(key) ?? "null");
		return Boolean(
			saved?.id &&
			(saved.id === window.history.state?.[key] ||
				saved.languageUrl === window.location.href),
		);
	} catch {
		return false;
	}
}

export function readComparisonDraft(
	scope: string,
	source: string,
): ComparisonDraft | null {
	try {
		const saved = JSON.parse(window.sessionStorage.getItem(key) ?? "null");
		if (
			saved?.scope === scope &&
			saved.source === source &&
			(saved.id === window.history.state?.[key] ||
				saved.languageUrl === window.location.href)
		)
			return saved;
	} catch {
		// Browsers which restrict tab storage can still use the open form.
	}
	return null;
}

export function writeComparisonDraft(
	draft: ComparisonDraft,
	languageUrl?: string,
): void {
	window.sessionStorage.setItem(key, JSON.stringify({ ...draft, languageUrl }));
	if (window.history.state?.[key] !== draft.id)
		window.history.replaceState(
			{ ...window.history.state, [key]: draft.id },
			"",
		);
}

export function forgetComparisonDraft(draft: ComparisonDraft): void {
	try {
		const saved = JSON.parse(window.sessionStorage.getItem(key) ?? "null");
		if (saved?.id === draft.id) window.sessionStorage.removeItem(key);
	} catch {
		// The completed request no longer depends on writable tab storage.
	}
}
