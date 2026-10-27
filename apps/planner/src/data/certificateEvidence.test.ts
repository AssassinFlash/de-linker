import test from "node:test";
import assert from "node:assert/strict";
import { readCertificateEvidence } from "./certificateEvidence.ts";
import type { PlanningRun } from "./planningProtocol.ts";
import { conditionObligations } from "./equipmentConditionReview.ts";

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

function reviewedSource() {
	const value = source();
	const original = value.documents[0]!;
	return {
		...value,
		condition_review: {
			schema_version: 1,
			method: "literal_device_conditions_v1",
			applicability: "not_assessed",
			devices: ["a", "b"].map((unit_id, index) => ({
				selection_ref: { kind: "plant_unit", unit_id, role: "inverter" },
				product_id: 1,
				product_revision: value.products[0]!.product_revision,
				declared_model: index === 0 ? "Fixture" : null,
				declared_firmware: index === 0 ? "001.02-A" : null,
				source_note: index === 0 ? "Commissioning record" : null,
				woo_model: "Fixture",
				model_identity: {
					status: index === 0 ? "same_text" : "unprovided",
					declared_value: index === 0 ? "Fixture" : null,
					selected_woo_value: "Fixture",
				},
				documents: [
					{
						document_id: original.document_id,
						document_revision: original.document_revision,
						blob_sha256: original.blob_sha256,
						applicability: "not_assessed",
						model: {
							status: "listed",
							compared_value: "Fixture",
							comparison_basis:
								index === 0 ? "project_declared" : "selected_woo_model",
							declared_values: ["Fixture"],
							page: 1,
							reason: "literal_model_list_match",
						},
						firmware: {
							status: index === 0 ? "conflict" : "unresolved",
							compared_value: index === 0 ? "001.02-A" : null,
							declared_value: "01.2-A",
							page: 1,
							reason:
								index === 0
									? "literal_firmware_different"
									: "project_firmware_missing",
						},
						annex: { status: "unresolved", source: null },
					},
				],
			})),
			remaining_obligations: [...conditionObligations],
		},
	};
}

test("condition review keeps literal versions, null observations and per-device file identity without aggregate approval", () => {
	const review = readCertificateEvidence(
		reviewedSource(),
		run,
		null,
		"https://de-linker.com",
	).condition_review!;
	assert.equal(review.devices.length, 2);
	assert.equal(review.devices[0]!.declared_firmware, "001.02-A");
	assert.equal(
		review.devices[0]!.documents[0]!.firmware.declared_value,
		"01.2-A",
	);
	assert.equal(review.devices[0]!.documents[0]!.firmware.status, "conflict");
	assert.equal(review.devices[1]!.declared_model, null);
	assert.equal(
		review.devices[1]!.documents[0]!.model.comparison_basis,
		"selected_woo_model",
	);
	assert.equal(review.applicability, "not_assessed");
	assert.equal(review.devices[0]!.model_identity.status, "same_text");
	assert.equal(review.devices[1]!.model_identity.status, "unprovided");
	const different = reviewedSource();
	different.condition_review.devices[0]!.declared_model = "fixture";
	different.condition_review.devices[0]!.model_identity = {
		status: "different_text",
		declared_value: "fixture",
		selected_woo_value: "Fixture",
	};
	different.condition_review.devices[0]!.documents[0]!.model = {
		...different.condition_review.devices[0]!.documents[0]!.model,
		compared_value: "fixture",
		status: "not_listed",
		reason: "literal_model_not_listed",
	};
	assert.equal(
		readCertificateEvidence(different, run, null, "https://de-linker.com")
			.condition_review!.devices[0]!.model_identity.status,
		"different_text",
		"differing model text remains a reconciliation need rather than a product rejection",
	);
	assert.deepEqual(review.remaining_obligations, conditionObligations);
	assert.equal(
		readCertificateEvidence(source(), run, null, "https://de-linker.com")
			.condition_review,
		undefined,
	);
	for (const change of [
		(s: ReturnType<typeof reviewedSource>) => {
			s.condition_review.devices[0]!.model_identity.selected_woo_value =
				"Other";
		},
		(s: ReturnType<typeof reviewedSource>) => {
			s.condition_review.devices[0]!.documents[0]!.blob_sha256 = "a".repeat(64);
		},
		(s: ReturnType<typeof reviewedSource>) => {
			s.condition_review.devices[0]!.documents[0]!.firmware.status =
				"exact_match";
		},
		(s: ReturnType<typeof reviewedSource>) => {
			s.condition_review.devices[1]!.selection_ref.unit_id = "a";
		},
		(s: ReturnType<typeof reviewedSource>) => {
			s.condition_review.devices[1]!.documents[0]!.model.comparison_basis =
				"project_declared";
		},
		(s: ReturnType<typeof reviewedSource>) => {
			s.condition_review.devices[0]!.documents = [];
		},
		(s: ReturnType<typeof reviewedSource>) => {
			s.condition_review.remaining_obligations.pop();
		},
	]) {
		const value = reviewedSource();
		change(value);
		assert.throws(() =>
			readCertificateEvidence(value, run, null, "https://de-linker.com"),
		);
	}
});
