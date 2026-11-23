/** Native Woo receipts preserve the report lineage; they never qualify hardware. */
import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

export interface DraftReceipt {
	readonly active?: boolean;
	readonly handoffId: string;
	readonly snapshotSha256: string;
	readonly projectId: string;
	readonly reportRunId: string;
	readonly revision: number;
	readonly urls: Readonly<Record<"en" | "de", string>>;
	readonly inquiryUrls: Readonly<Record<"en" | "de", string>> | null;
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
	readonly inquiryUrls: Readonly<Record<"en" | "de", string>> | null;
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
		(row.active !== undefined && typeof row.active !== "boolean") ||
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
	return {
		...(row.active === undefined ? {} : { active: row.active }),
		handoffId: String(row.handoff_id),
		snapshotSha256: String(row.snapshot_sha256),
		projectId: String(row.project_id),
		reportRunId: String(row.report_run_id),
		revision: Number(row.revision),
		urls: destinations,
		inquiryUrls: readInquiryUrls(row, origin),
	};
}
function readInquiryUrls(row: JsonObject, origin: string) {
	return row.inquiry_urls === undefined
		? null
		: readUrls(readObject(row.inquiry_urls), origin);
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
		inquiryUrls: readInquiryUrls(row, origin),
	};
}

function inquiryProduct(row: JsonObject) {
	return {
		productUrl: typeof row.product_url === "string" ? row.product_url : null,
		imageUrl: typeof row.image_url === "string" ? row.image_url : null,
		highlight: typeof row.highlight === "string" ? row.highlight : null,
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
		return {
			...inquiryProduct(line),
			sku: typeof line.sku === "string" ? line.sku : null,
			availability:
				line.availability === "in-stock" || line.availability === "unavailable"
					? line.availability
					: null,
			cartKey: typeof line.cart_key === "string" ? line.cart_key : null,
			productId: line.product_id,
			projectId: line.project_id,
			label: line.label,
			quantity: line.quantity,
			projectTitle:
				line.project_id !== null && typeof line.project_title === "string"
					? line.project_title
					: null,
		};
	});
	const readRows = <T>(field: string, read: (row: JsonObject) => T): T[] => {
		const raw = row[field];
		if (raw === undefined) return [];
		if (!Array.isArray(raw)) fail();
		return raw.map((value) => read(readObject(value)));
	};
	const edit = row.inquiry_draft_edit
		? readObject(row.inquiry_draft_edit)
		: null;
	return {
		lines,
		draftEdit:
			edit &&
			typeof edit.url === "string" &&
			typeof edit.nonce === "string" &&
			typeof edit.rest_nonce === "string"
				? { url: edit.url, nonce: edit.nonce, restNonce: edit.rest_nonce }
				: null,
		form: row.inquiry_form_html,
		facts: readRows(
			"inquiry_project_facts",
			({ label, value }): [string, string] => {
				if (typeof label !== "string" || typeof value !== "string") fail();
				return [label, value];
			},
		),
		changes: readRows("inquiry_changes", (change) => {
			if (
				!count(change.product_id) ||
				!change.product_id ||
				typeof change.label !== "string" ||
				!change.label.trim() ||
				typeof change.before !== "number" ||
				!Number.isFinite(change.before) ||
				change.before <= 0 ||
				!count(change.after) ||
				change.before === change.after
			)
				fail();
			return {
				...inquiryProduct(change),
				productId: change.product_id,
				label: change.label,
				before: change.before,
				after: change.after,
			};
		}),
		conflicts: readRows("inquiry_phase_conflicts", (conflict) => {
			const { unit, actual, required } = conflict;
			if (
				(unit !== null && (typeof unit !== "string" || !unit.trim())) ||
				(actual !== 1 && actual !== 3) ||
				(required !== 1 && required !== 3) ||
				actual === required
			)
				fail();
			return { unit, actual, required };
		}),
	};
}
