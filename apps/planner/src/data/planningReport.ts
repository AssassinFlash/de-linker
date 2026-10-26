import Ajv2020 from "ajv/dist/2020.js";
import reportSchema from "../contracts/planning-report.schema.json" with { type: "json" };
import optionsSchema from "../contracts/planning-report-options.schema.json" with { type: "json" };
import type { JsonObject } from "./protocol.ts";
import type { PlanningRun } from "./planningProtocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { sameJson } from "../domain/draft.ts";

export const REPORT_TASK = "planning_report_v1";
export interface ReportOptions extends JsonObject {
	locale: "en" | "de";
	energy_run_id: string | null;
	pv_run_id: string | null;
	equipment_run_id: string | null;
	logo: string | null;
	comparison?: { baseline_run_id: string; candidate_run_id: string } | null;
	include_installation?: boolean;
}
export interface ReportRow {
	label: string;
	value: string;
	href: string | null;
}
export interface ReportSection {
	id: string;
	title: string;
	rows: ReportRow[];
	paragraphs: string[];
	table: {
		columns: string[];
		rows: string[][];
		column_weights?: number[] | null;
	} | null;
}
export interface PlanningReport {
	title: string;
	subtitle: string;
	generated_at: string;
	locale: "en" | "de";
	sections: ReportSection[];
}
const ajv = new Ajv2020({ strict: true, strictNumbers: true });
const validateReport = ajv.compile<PlanningReport>(reportSchema);
const validateOptions = ajv.compile<ReportOptions>(optionsSchema);
const hash = (value: unknown): value is string =>
	typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const pvModelMethods = new Set([
	"https://pvlib-python.readthedocs.io/en/v0.16.1/reference/generated/pvlib.ivtools.sdm.fit_desoto_batzelis.html",
	"https://pvlib-python.readthedocs.io/en/v0.16.1/reference/generated/pvlib.ivtools.sdm.fit_desoto.html",
	"https://pvlib-python.readthedocs.io/en/v0.16.1/reference/generated/pvlib.pvsystem.calcparams_desoto.html",
]);
export function readReportOptions(value: unknown): ReportOptions {
	if (!validateOptions(value))
		throw new ApiError(422, "invalid_report_options");
	return value;
}
export function readPlanningReport(value: unknown): PlanningReport {
	if (
		!validateReport(value) ||
		!Number.isFinite(Date.parse(value.generated_at))
	)
		throw new ApiError(502, "invalid_planning_report");
	for (const section of value.sections) {
		const weights = section.table?.column_weights;
		if (
			weights != null &&
			(weights.length !== section.table!.columns.length ||
				weights.some((weight) => !Number.isFinite(weight) || weight <= 0))
		)
			throw new ApiError(502, "invalid_planning_report");
		if (
			section.table?.rows.some(
				(row) => row.length !== section.table!.columns.length,
			)
		)
			throw new ApiError(502, "invalid_planning_report");
		for (const row of section.rows)
			if (row.href) {
				let url: URL;
				try {
					url = new URL(row.href);
				} catch {
					throw new ApiError(502, "invalid_planning_report");
				}
				const methodReference =
					section.id === "pv-iv-model" && pvModelMethods.has(url.href);
				if (
					(url.origin !== "https://de-linker.com" && !methodReference) ||
					url.username ||
					url.password
				)
					throw new ApiError(502, "invalid_planning_report");
			}
	}
	return value;
}
export function readReportResult(
	value: unknown,
	run: JsonObject,
	manifest: JsonObject,
): JsonObject {
	const result = readObject(value),
		context = readObject(manifest.context),
		pinned = readObject(result.pinned_assets),
		asset = readObject(result.prepared_asset),
		metadata = readObject(asset.metadata),
		dependencies = readObject(metadata.dependencies);
	if (
		result.kind !== REPORT_TASK ||
		result.project_id !== run.project_id ||
		result.revision !== run.revision ||
		result.input_sha256 !== manifest.input_sha256 ||
		result.manifest_sha256 !== run.manifest_sha256 ||
		result.runtime_sha256 !== context.code_sha256 ||
		!sameJson(pinned, context.assets) ||
		!hash(result.report_sha256) ||
		!hash(pinned["report.source"]) ||
		asset.project_id !== run.project_id ||
		asset.media_type !== "application/pdf" ||
		asset.purpose !== "planning_report_pdf_v1" ||
		!hash(asset.content_sha256) ||
		dependencies.report_model !== result.report_sha256 ||
		dependencies.report_source !== pinned["report.source"] ||
		!Array.isArray(result.source_runs)
	)
		throw new ApiError(502, "invalid_planning_report");
	readPlanningReport(result.report);
	if (
		result.materials_sha256 !== undefined ||
		result.prepared_attachments !== undefined
	) {
		const csv = readObject(
				readObject(result.prepared_attachments).bill_of_materials_csv,
			),
			csvMetadata = readObject(csv.metadata),
			csvDependencies = readObject(csvMetadata.dependencies),
			resultDependencies = readObject(result.dependencies);
		if (
			!hash(result.materials_sha256) ||
			typeof result.has_draft_items !== "boolean" ||
			typeof csv.id !== "string" ||
			!csv.id ||
			csv.project_id !== run.project_id ||
			(csv.purpose !== "planning_materials_csv_v1" &&
				csv.purpose !== "planning_materials_csv_v2" &&
				csv.purpose !== "planning_materials_csv_v3") ||
			csv.media_type !== "text/csv" ||
			!hash(csv.content_sha256) ||
			!hash(csv.metadata_sha256) ||
			!sameJson(csvDependencies, dependencies) ||
			dependencies.materials_model !== result.materials_sha256 ||
			resultDependencies.materials_model !== result.materials_sha256 ||
			resultDependencies[
				"prepared_attachment.bill_of_materials_csv.content"
			] !== csv.content_sha256 ||
			resultDependencies[
				"prepared_attachment.bill_of_materials_csv.metadata"
			] !== csv.metadata_sha256 ||
			csvMetadata.locale !== readObject(result.report).locale
		)
			throw new ApiError(502, "invalid_planning_report");
	}
	return result;
}
export function reportFromRun(run: PlanningRun): PlanningReport {
	if (!run.result) throw new ApiError(502, "invalid_planning_report");
	return readPlanningReport(run.result.report);
}
