import {
	readEquipmentConditionInputs,
	conditionDeviceKey,
} from "../domain/equipmentConditionInputs.ts";
import type { DeviceConditionInput } from "../domain/equipmentConditionInputs.ts";
import type {
	CertificateDocument,
	CertificateProduct,
} from "./certificateEvidence.ts";
import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

export const conditionObligations = [
	"document_scope",
	"other_pages_and_reports",
	"annex_conditions",
	"hardware_and_configuration",
	"operating_mode",
	"country_and_dso_settings",
	"standard_edition_and_transition",
	"issuer_current_status",
	"project_grid_assessment",
	"dso_permission",
] as const;
export type ConditionObligation = (typeof conditionObligations)[number];
export interface ModelReview extends JsonObject {
	status: "listed" | "not_listed" | "unresolved";
	compared_value: string | null;
	comparison_basis: "project_declared" | "selected_woo_model";
	declared_values: string[] | null;
	page: 1 | null;
	reason: string;
}
export interface FirmwareReview extends JsonObject {
	status: "exact_match" | "conflict" | "unresolved";
	compared_value: string | null;
	declared_value: string | null;
	page: 1 | null;
	reason: string;
}
export interface ConditionDocumentReview extends JsonObject {
	document_id: string;
	document_revision: string;
	blob_sha256: string;
	applicability: "not_assessed";
	model: ModelReview;
	firmware: FirmwareReview;
	annex: { status: "unresolved"; source: JsonObject | null };
}
export interface DeviceConditionReview extends DeviceConditionInput {
	woo_model: string;
	model_identity: {
		status: "unprovided" | "same_text" | "different_text";
		declared_value: string | null;
		selected_woo_value: string;
	};
	documents: ConditionDocumentReview[];
}
export interface EquipmentConditionReview {
	schema_version: 1;
	method: "literal_device_conditions_v1";
	applicability: "not_assessed";
	devices: DeviceConditionReview[];
	remaining_obligations: ConditionObligation[];
}
function invalid(): never {
	throw new ApiError(502, "invalid_certificate_evidence");
}
const nullableString = (value: unknown): value is string | null =>
	value === null || typeof value === "string";
const page = (value: unknown) => value === 1 || value === null;
const modelReasons = new Set([
	"model_field_unresolved",
	"project_model_unresolved",
	"literal_model_list_match",
	"literal_model_not_listed",
]);
const firmwareReasons = new Set([
	"firmware_field_unresolved",
	"project_firmware_missing",
	"project_firmware_unresolved",
	"literal_firmware_equal",
	"literal_firmware_different",
]);

/** The UI accepts only comparisons bound to this frozen product/document projection. */
export function readEquipmentConditionReview(
	value: unknown,
	products: CertificateProduct[],
	documents: CertificateDocument[],
): EquipmentConditionReview {
	const row = readObject(value);
	if (
		row.schema_version !== 1 ||
		row.method !== "literal_device_conditions_v1" ||
		row.applicability !== "not_assessed" ||
		!Array.isArray(row.devices) ||
		!Array.isArray(row.remaining_obligations) ||
		row.remaining_obligations.length !== conditionObligations.length ||
		new Set(row.remaining_obligations).size !== conditionObligations.length ||
		!conditionObligations.every((id) =>
			(row.remaining_obligations as unknown[]).includes(id),
		)
	)
		invalid();
	const deviceKeys = new Set<string>();
	const devices = row.devices.map((value) => {
		const d = readObject(value);
		let observation: DeviceConditionInput;
		try {
			observation = readEquipmentConditionInputs({
				schema_version: 1,
				devices: [
					{
						selection_ref: d.selection_ref,
						product_id: d.product_id,
						product_revision: d.product_revision,
						declared_model: d.declared_model,
						declared_firmware: d.declared_firmware,
						source_note: d.source_note,
					},
				],
			}).devices[0]!;
		} catch {
			return invalid();
		}
		const product = products.find(
				(p) => p.product_id === observation.product_id,
			),
			key = conditionDeviceKey(observation);
		if (
			!product ||
			product.product_revision !== observation.product_revision ||
			product.model !== d.woo_model ||
			!Array.isArray(d.documents) ||
			deviceKeys.has(key)
		)
			invalid();
		deviceKeys.add(key);
		const identity = readObject(d.model_identity);
		const identityStatus: DeviceConditionReview["model_identity"]["status"] =
			observation.declared_model === null
				? "unprovided"
				: observation.declared_model === product.model
					? "same_text"
					: "different_text";
		if (
			identity.status !== identityStatus ||
			identity.declared_value !== observation.declared_model ||
			identity.selected_woo_value !== product.model
		)
			invalid();
		const documentIds = new Set<string>();
		const reviewed = d.documents.map((value) => {
			const doc = readObject(value),
				original = documents.find(
					(source) => source.document_id === doc.document_id,
				),
				model = readObject(doc.model),
				firmware = readObject(doc.firmware),
				annex = readObject(doc.annex);
			if (
				!original ||
				!original.product_ids.includes(observation.product_id) ||
				doc.document_revision !== original.document_revision ||
				doc.blob_sha256 !== original.blob_sha256 ||
				doc.applicability !== "not_assessed" ||
				documentIds.has(original.document_id)
			)
				invalid();
			documentIds.add(original.document_id);
			const comparedModel = observation.declared_model ?? product.model;
			if (
				!["listed", "not_listed", "unresolved"].includes(
					String(model.status),
				) ||
				model.compared_value !== comparedModel ||
				model.comparison_basis !==
					(observation.declared_model === null
						? "selected_woo_model"
						: "project_declared") ||
				!page(model.page) ||
				!modelReasons.has(String(model.reason)) ||
				!(
					model.declared_values === null ||
					(Array.isArray(model.declared_values) &&
						model.declared_values.every((v) => typeof v === "string"))
				)
			)
				invalid();
			if (
				model.status !== "unresolved" &&
				(model.page !== 1 ||
					!Array.isArray(model.declared_values) ||
					(model.status === "listed") !==
						model.declared_values.includes(comparedModel))
			)
				invalid();
			if (
				(model.status === "listed") !==
					(model.reason === "literal_model_list_match") ||
				(model.status === "not_listed") !==
					(model.reason === "literal_model_not_listed")
			)
				invalid();
			if (
				!["exact_match", "conflict", "unresolved"].includes(
					String(firmware.status),
				) ||
				firmware.compared_value !== observation.declared_firmware ||
				!nullableString(firmware.declared_value) ||
				!page(firmware.page) ||
				!firmwareReasons.has(String(firmware.reason))
			)
				invalid();
			if (
				firmware.status !== "unresolved" &&
				(firmware.page !== 1 ||
					typeof firmware.compared_value !== "string" ||
					typeof firmware.declared_value !== "string" ||
					(firmware.status === "exact_match") !==
						(firmware.compared_value === firmware.declared_value))
			)
				invalid();
			if (
				(firmware.status === "exact_match") !==
					(firmware.reason === "literal_firmware_equal") ||
				(firmware.status === "conflict") !==
					(firmware.reason === "literal_firmware_different")
			)
				invalid();
			if (
				annex.status !== "unresolved" ||
				(annex.source !== null &&
					(typeof annex.source !== "object" || Array.isArray(annex.source)))
			)
				invalid();
			return {
				document_id: original.document_id,
				document_revision: original.document_revision,
				blob_sha256: original.blob_sha256,
				applicability: "not_assessed" as const,
				model: model as unknown as ModelReview,
				firmware: firmware as unknown as FirmwareReview,
				annex: {
					status: "unresolved" as const,
					source: annex.source === null ? null : readObject(annex.source),
				},
			};
		});
		if (
			reviewed.length !==
			documents.filter((doc) =>
				doc.product_ids.includes(observation.product_id),
			).length
		)
			invalid();
		return {
			...observation,
			woo_model: product.model,
			model_identity: {
				status: identityStatus,
				declared_value: observation.declared_model,
				selected_woo_value: product.model,
			},
			documents: reviewed,
		};
	});
	return {
		schema_version: 1,
		method: "literal_device_conditions_v1",
		applicability: "not_assessed",
		devices,
		remaining_obligations: row.remaining_obligations as ConditionObligation[],
	};
}
