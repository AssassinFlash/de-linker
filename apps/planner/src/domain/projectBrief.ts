import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { emptyBrief, readBrief } from "./brief.ts";
import { entryInputs } from "./entryHints.ts";
import type { EntryHints, ProductEntryField } from "./entryHints.ts";

export interface ProjectBriefSource extends JsonObject {
	readonly schema_version: 1;
	readonly brief_id: string;
	readonly revision: string;
	readonly text: string;
	readonly source_path: string;
}

/** A URL identifies a staged project brief; it never carries customer text. */
export function projectBriefId(params: URLSearchParams): string | null {
	if (
		params.has("project") ||
		params.has("saved_solution") ||
		!params.has("brief")
	)
		return null;
	const values = params.getAll("brief");
	if (values.length !== 1 || !/^[a-f0-9]{32}$/.test(values[0]!)) return "";
	return values[0]!;
}

export function readProjectBriefSource(
	value: unknown,
	briefId: string,
): ProjectBriefSource {
	const data = readObject(value);
	if (
		data.schema_version !== 1 ||
		data.brief_id !== briefId ||
		typeof data.revision !== "string" ||
		!/^[a-f0-9]{64}$/.test(data.revision) ||
		typeof data.text !== "string" ||
		data.text.trim().length === 0 ||
		Array.from(data.text).length > 4096 ||
		typeof data.source_path !== "string" ||
		!data.source_path.startsWith("/") ||
		data.source_path.startsWith("//")
	)
		throw new ApiError(502, "invalid_project_brief_source");
	return data as ProjectBriefSource;
}

/**
 * Plain customer text is preserved verbatim in brief.project_note.
 * No sizing numbers, phase, backup, postcode or equipment IDs are inferred from it.
 */
export function projectBriefInputs(
	noteText: string,
	hints: EntryHints | null,
	sourceNote: string,
	product: { id: number; field: ProductEntryField } | null = null,
): JsonObject {
	// The project note is the customer's own text only. A carried backup hint
	// stays a structured input (operating_mode), never a sentence inside it.
	const base = hints
		? entryInputs(hints, sourceNote, "", product)
		: { brief: emptyBrief() };
	const brief = readBrief(base.brief);
	return {
		...base,
		brief: {
			...brief,
			project_note: noteText,
		},
	};
}

export function installerEntryHref(
	sourcePath: string | null | undefined,
	locale: string,
): string {
	const isDe = locale.toLowerCase().startsWith("de");
	if (
		typeof sourcePath === "string" &&
		sourcePath.startsWith("/") &&
		!sourcePath.startsWith("//") &&
		!sourcePath.includes("?") &&
		!sourcePath.includes("#")
	) {
		if (isDe && sourcePath.startsWith("/de/")) return sourcePath;
		if (!isDe && !sourcePath.startsWith("/de/")) return sourcePath;
	}
	return isDe ? "/de/fuer-installateur/" : "/for-installer/";
}
