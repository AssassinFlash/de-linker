import { ApiError } from "./protocol.ts";
import type { JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

export interface ProjectRow {
	readonly id: string;
	readonly title: string;
	readonly revision: number;
	readonly input_sha256: string;
	readonly updated_at: number;
}
export interface ProjectPage {
	readonly items: readonly ProjectRow[];
	readonly next: JsonObject | null;
}
export function readProjectPage(value: unknown, pageSize: number): ProjectPage {
	const data = readObject(value);
	if (!Array.isArray(data.items) || data.items.length > pageSize)
		throw new ApiError(502, "invalid_project_index");
	const items = data.items.map((value) => {
		const item = readObject(value);
		if (
			typeof item.id !== "string" ||
			!/^[a-f0-9]{32}$/.test(item.id) ||
			typeof item.title !== "string" ||
			!item.title ||
			item.title.length > 256 ||
			typeof item.revision !== "number" ||
			!Number.isSafeInteger(item.revision) ||
			item.revision < 1 ||
			typeof item.input_sha256 !== "string" ||
			!/^[a-f0-9]{64}$/.test(item.input_sha256) ||
			typeof item.updated_at !== "number" ||
			!Number.isFinite(item.updated_at)
		)
			throw new ApiError(502, "invalid_project_index");
		return item as unknown as ProjectRow;
	});
	let next: JsonObject | null = null;
	if (data.next !== null) {
		next = readObject(data.next);
		if (
			typeof next.id !== "string" ||
			!/^[a-f0-9]{32}$/.test(next.id) ||
			typeof next.updated_at !== "number" ||
			!Number.isFinite(next.updated_at)
		)
			throw new ApiError(502, "invalid_project_cursor");
	}
	return { items, next };
}
