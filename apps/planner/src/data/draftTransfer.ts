/** Native Woo receipts preserve the report lineage; they never qualify hardware. */
import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

export interface DraftReceipt {
	readonly inquiryCartHash?: string;
	readonly inquiryDraftSha256?: string;
	readonly handoffId: string;
	readonly snapshotSha256: string;
	readonly projectId: string;
	readonly reportRunId: string;
	readonly revision: number;
	readonly urls: Readonly<Record<"en" | "de", string>>;
}
export interface DraftPreview {
	readonly draftSha256: string;
	readonly phaseConflicts: readonly {
		readonly unit: string | null;
		readonly actual: 1 | 3;
		readonly required: 1 | 3;
	}[];
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
		(row.items.length === 0) !== (row.report_only === true)
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
	const cart = row.inquiry_cart_hash,
		fingerprint = row.inquiry_draft_sha256;
	if (
		(cart !== undefined || fingerprint !== undefined) &&
		((cart !== "" && !hash(cart, 32)) || !hash(fingerprint, 64))
	)
		fail();
	return {
		...(typeof cart === "string" && typeof fingerprint === "string"
			? { inquiryCartHash: cart, inquiryDraftSha256: fingerprint }
			: {}),
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
		(row.changes.length === 0 && row.report_only !== true)
	)
		fail();
	const ids = new Set<number>();
	const changes = row.changes.map((value) => {
		const change = readObject(value);
		if (
			(row.report_only === true && change.after !== 0) ||
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
	const conflicts = row.phase_conflicts;
	if (conflicts !== undefined && !Array.isArray(conflicts)) fail();
	const readConflict = (value: unknown, legacy = false) => {
		const check = readObject(value);
		const unit = legacy ? null : check.unit;
		const { actual, required } = check;
		if (
			(unit !== null && (typeof unit !== "string" || !unit.trim())) ||
			(actual !== 1 && actual !== 3) ||
			(required !== 1 && required !== 3) ||
			actual === required
		)
			fail();
		return { unit, actual, required } as const;
	};
	return {
		draftSha256: String(row.draft_sha256),
		phaseConflicts:
			conflicts !== undefined
				? conflicts.map((value) => readConflict(value))
				: row.phase_conflict === undefined
					? []
					: [readConflict(row.phase_conflict, true)],
		changes,
		alreadyPresent: row.already_present,
		urls: readUrls(readObject(row.draft_urls), origin),
	};
}

export function readInquiryPreview(
	value: unknown,
	command: JsonObject,
	origin: string,
) {
	const preview = readDraftPreview(value, command, origin),
		row = readObject(value);
	return {
		...preview,
		handoffId: String(row.handoff_id),
		...readInquiryForm(row),
	};
}
export function readInquiryForm(value: unknown) {
	const row = readObject(value);
	if (
		row.schema_version !== 1 ||
		typeof row.inquiry_form_html !== "string" ||
		!row.inquiry_form_html.trim() ||
		!Array.isArray(row.inquiry_lines)
	)
		fail();
	const lines = row.inquiry_lines.map((value) => {
		const line = readObject(value);
		if (
			!count(line.product_id) ||
			!line.product_id ||
			typeof line.quantity !== "number" ||
			!Number.isFinite(line.quantity) ||
			line.quantity <= 0 ||
			typeof line.label !== "string" ||
			!line.label.trim() ||
			(line.project_id !== null && !hash(line.project_id, 32))
		)
			fail();
		return { label: line.label, quantity: line.quantity };
	});
	return {
		lines,
		form: row.inquiry_form_html,
	};
}
