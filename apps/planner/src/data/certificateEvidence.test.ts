import test from "node:test";
import assert from "node:assert/strict";
import { readCertificateEvidence } from "./certificateEvidence.ts";
import type { PlanningRun } from "./planningProtocol.ts";

const run: PlanningRun = {
	id: "a".repeat(32),
	project_id: "b".repeat(32),
	revision: 3,
	state: "succeeded",
	is_current: true,
	manifest_sha256: "c".repeat(64),
	result_sha256: "d".repeat(64),
	manifest: {},
	result: null,
	error: null,
	task_kind: "qualify_woo_equipment_v1",
};
const source = () => ({
	schema_version: 1,
	scope: "associated_product_documents",
	applicability: "not_assessed",
	run_id: run.id,
	project_id: run.project_id,
	revision: 3,
	manifest_sha256: run.manifest_sha256,
	basis_sha256: "e".repeat(64),
	candidate_id: null,
	assessment_sha256: null,
	products: [
		{
			product_id: 1,
			product_revision: "f".repeat(64),
			model: "Fixture",
			brand: "Fixture",
		},
	],
	documents: [
		{
			document_id: "document",
			document_revision: "1".repeat(64),
			blob_sha256: "2".repeat(64),
			url: "https://de-linker.com/wp-content/uploads/fixture.pdf",
			title: "Recorded certificate",
			lang: "en",
			product_ids: [1],
			access: {
				status: "available",
				url:
					"https://de-linker.com/index.php?linker_public_document=fixture.pdf&linker_document_sha256=" +
					"2".repeat(64),
			},
		},
	],
});

test("certificate metadata keeps its result and exact native file version", () => {
	assert.equal(
		readCertificateEvidence(source(), run, null, "https://de-linker.com")
			.documents[0]?.blob_sha256,
		"2".repeat(64),
	);
	for (const change of [
		(s: ReturnType<typeof source>) => {
			s.run_id = "x".repeat(32);
		},
		(s: ReturnType<typeof source>) => {
			s.documents[0]!.product_ids = [9];
		},
		(s: ReturnType<typeof source>) => {
			s.documents[0]!.access.url = s.documents[0]!.access.url.replace(
				"https://de-linker.com",
				"https://other.example",
			);
		},
		(s: ReturnType<typeof source>) => {
			s.documents[0]!.access.url = s.documents[0]!.access.url.replace(
				"2".repeat(64),
				"3".repeat(64),
			);
		},
	]) {
		const value = source();
		change(value);
		assert.throws(() =>
			readCertificateEvidence(value, run, null, "https://de-linker.com"),
		);
	}
});

test("a current unavailable source cannot retain an actionable link", () => {
	const value = source();
	value.documents[0]!.access.status = "unavailable";
	assert.throws(() =>
		readCertificateEvidence(value, run, null, "https://de-linker.com"),
	);
	const unavailable = {
		...value,
		documents: value.documents.map((d) => ({
			...d,
			access: { status: "unavailable", url: null },
		})),
	};
	assert.equal(
		readCertificateEvidence(unavailable, run, null, "https://de-linker.com")
			.documents[0]?.access.url,
		null,
	);
});
