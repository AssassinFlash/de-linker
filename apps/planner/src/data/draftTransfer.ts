/** Native Woo receipts preserve the report lineage; they never qualify hardware. */
import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

export interface DraftReceipt {
	readonly handoffId: string;
	readonly snapshotSha256: string;
	readonly projectId: string;
	readonly reportRunId: string;
	readonly revision: number;
	readonly urls: Readonly<Record<"en" | "de", string>>;
}
export interface DraftPreview {
	readonly draftSha256: string;
	readonly alreadyPresent: boolean;
	readonly urls: Readonly<Record<"en" | "de", string>>;
	readonly changes: readonly {
		readonly productId: number;
		readonly label: string;
		readonly before: number;
		readonly after: number;
	}[];
}
const hash = (value: unknown, length: number): value is string =>
	typeof value === "string" && new RegExp(`^[a-f0-9]{${length}}$`).test(value);
const count = (value: unknown): value is number =>
	typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
function fail(): never {
	throw new ApiError(502, "invalid_draft_receipt");
}
function lineage(value: unknown, command: JsonObject) {
	const row = readObject(value);
	if (
		row.schema_version !== 1 ||
		row.project_id !== command.project_id ||
		row.report_run_id !== command.report_run_id ||
		row.revision !== command.expected_revision ||
		!hash(row.handoff_id, 32) ||
		!hash(row.snapshot_sha256, 64)
	)
		fail();
	return row;
}
export function readDraftReceipt(
	value: unknown,
	command: JsonObject,
	origin: string,
): DraftReceipt {
	const row = lineage(value, command),
		urls = readObject(row.draft_urls);
	if (
		!hash(row.intent_sha256, 64) ||
		!Array.isArray(row.items) ||
		!row.items.length
	)
		fail();
	const ids = new Set<number>();
	for (const value of row.items) {
		const item = readObject(value);
		if (
			!count(item.id) ||
			item.id === 0 ||
			!count(item.quantity) ||
			item.quantity === 0 ||
			ids.has(item.id)
		)
			fail();
		ids.add(item.id);
	}
	const destinations = readUrls(urls, origin);
	return {
		handoffId: String(row.handoff_id),
		snapshotSha256: String(row.snapshot_sha256),
		projectId: String(row.project_id),
		reportRunId: String(row.report_run_id),
		revision: Number(row.revision),
		urls: destinations,
	};
}
function readUrls(
	urls: JsonObject,
	origin: string,
): Record<"en" | "de", string> {
	const destinations = {} as Record<"en" | "de", string>;
	for (const locale of ["en", "de"] as const) {
		if (typeof urls[locale] !== "string") fail();
		const url = new URL(urls[locale]);
		if (
			url.origin !== origin ||
			url.username ||
			url.password ||
			url.hash ||
			!["http:", "https:"].includes(url.protocol)
		)
			fail();
		destinations[locale] = url.href;
	}
	return destinations;
}
export function readDraftPreview(
	value: unknown,
	command: JsonObject,
	origin: string,
): DraftPreview {
	const row = lineage(value, command);
	if (
		typeof row.already_present !== "boolean" ||
		!hash(row.draft_sha256, 64) ||
		!Array.isArray(row.changes) ||
		!row.changes.length
	)
		fail();
	const ids = new Set<number>();
	const changes = row.changes.map((value) => {
		const change = readObject(value);
		if (
			!count(change.product_id) ||
			change.product_id === 0 ||
			ids.has(change.product_id) ||
			typeof change.label !== "string" ||
			!change.label.trim() ||
			typeof change.before !== "number" ||
			!Number.isFinite(change.before) ||
			change.before < 0 ||
			!count(change.after)
		)
			fail();
		ids.add(change.product_id);
		return {
			productId: change.product_id,
			label: change.label,
			before: change.before,
			after: change.after,
		};
	});
	return {
		draftSha256: String(row.draft_sha256),
		changes,
		alreadyPresent: row.already_present,
		urls: readUrls(readObject(row.draft_urls), origin),
	};
}
