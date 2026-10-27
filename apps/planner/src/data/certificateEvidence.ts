import type { PlanningRun } from "./planningProtocol.ts";
import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { documentReference } from "./documentReference.ts";
import { readEquipmentConditionReview } from "./equipmentConditionReview.ts";
import type { EquipmentConditionReview } from "./equipmentConditionReview.ts";

export interface CertificateProduct {
	product_id: number;
	product_revision: string;
	model: string;
	brand: string;
}
export interface CertificateDocument {
	document_id: string;
	document_revision: string;
	blob_sha256: string;
	url: string;
	title: string;
	lang: string;
	product_ids: number[];
	access: {
		status: "available" | "unavailable" | "source_changed";
		url: string | null;
	};
}
export interface CertificateEvidence {
	products: CertificateProduct[];
	documents: CertificateDocument[];
	condition_review?: EquipmentConditionReview;
}

function invalid(): never {
	throw new ApiError(502, "invalid_certificate_evidence");
}
function stringField(row: JsonObject, key: string): string {
	const value = row[key];
	return typeof value === "string" ? value : invalid();
}
function sha(row: JsonObject, key: string): string {
	const value = stringField(row, key);
	return /^[a-f0-9]{64}$/.test(value) ? value : invalid();
}
export function readCertificateEvidence(
	value: unknown,
	run: PlanningRun,
	candidate: { id: string; assessment_sha256: string } | null,
	origin: string,
): CertificateEvidence {
	const row = readObject(value);
	if (
		row.schema_version !== 1 ||
		row.scope !== "associated_product_documents" ||
		row.applicability !== "not_assessed" ||
		row.run_id !== run.id ||
		row.project_id !== run.project_id ||
		row.revision !== run.revision ||
		row.manifest_sha256 !== run.manifest_sha256 ||
		row.candidate_id !== (candidate?.id ?? null) ||
		row.assessment_sha256 !== (candidate?.assessment_sha256 ?? null) ||
		!Array.isArray(row.products) ||
		!Array.isArray(row.documents)
	)
		invalid();
	sha(row, "basis_sha256");
	const ids = new Set<number>();
	const products = row.products.map((value) => {
		const p = readObject(value),
			id = p.product_id;
		if (
			typeof id !== "number" ||
			!Number.isSafeInteger(id) ||
			id < 1 ||
			ids.has(id)
		)
			invalid();
		ids.add(id);
		return {
			product_id: id,
			product_revision: sha(p, "product_revision"),
			model: stringField(p, "model"),
			brand: stringField(p, "brand"),
		};
	});
	const documentIds = new Set<string>();
	const documents = row.documents.map((value) => {
		const d = readObject(value),
			id = stringField(d, "document_id"),
			hash = sha(d, "blob_sha256"),
			access = readObject(d.access);
		documentReference(d);
		if (
			!id ||
			documentIds.has(id) ||
			!Array.isArray(d.product_ids) ||
			!d.product_ids.length
		)
			invalid();
		documentIds.add(id);
		const members = d.product_ids.map((value) =>
			typeof value === "number" && ids.has(value) ? value : invalid(),
		);
		let url: string | null = null;
		if (access.status === "available") {
			if (typeof access.url !== "string") invalid();
			let parsed: URL;
			try {
				parsed = new URL(access.url);
			} catch {
				return invalid();
			}
			if (
				!["http:", "https:"].includes(parsed.protocol) ||
				parsed.origin !== origin ||
				!parsed.pathname.endsWith("/index.php") ||
				parsed.username ||
				parsed.password ||
				parsed.hash ||
				parsed.searchParams.get("linker_document_sha256") !== hash ||
				!parsed.searchParams.get("linker_public_document")
			)
				invalid();
			url = parsed.href;
		} else if (
			!["unavailable", "source_changed"].includes(String(access.status)) ||
			access.url !== null
		)
			invalid();
		return {
			document_id: id,
			document_revision: sha(d, "document_revision"),
			blob_sha256: hash,
			url: stringField(d, "url"),
			title: stringField(d, "title"),
			lang: stringField(d, "lang"),
			product_ids: members,
			access: {
				status: access.status as CertificateDocument["access"]["status"],
				url,
			},
		};
	});
	return {
		products,
		documents,
		...(row.condition_review === undefined
			? {}
			: {
					condition_review: readEquipmentConditionReview(
						row.condition_review,
						products,
						documents,
					),
				}),
	};
}
