import { readDcParameters } from "../domain/dcEnergy.ts";
import dcRunJson from "../../tests/fixtures/dc-energy-run.json" with { type: "json" };
import plantRunJson from "../../tests/fixtures/plant-energy-run.json" with { type: "json" };
import { readTraceWindow } from "./traceWindow.ts";
import test from "node:test";
import assert from "node:assert/strict";
import runJson from "../../tests/fixtures/energy-run.json" with { type: "json" };
import roofRunJson from "../../tests/fixtures/roof-energy-run.json" with { type: "json" };
import { readRun, readRunPage } from "./planningProtocol.ts";
import { readPlanningReport, readReportResult } from "./planningReport.ts";
import { readObject as objectDocument } from "./readProtocol.ts";
import { ApiError } from "./protocol.ts";
import type { JsonObject } from "./protocol.ts";

type MutableObject = { -readonly [P in keyof JsonObject]: JsonObject[P] };
const readObject = (value: unknown): MutableObject =>
	objectDocument(value) as MutableObject;
const original = () => readObject(structuredClone(runJson));
const result = (run: JsonObject) => readObject(run.result);

test("native joint result retains named parameter proofs, unit trace and the shared report consumer", () => {
	const run = readRun(
		plantRunJson.run,
		plantRunJson.run.project_id,
		undefined,
		"single_ac_energy_replay_v1",
	);
	assert.equal(run.result!.kind, "plant_ac_energy_replay_v1");
	const trace = readTraceWindow(plantRunJson.trace, run, 0, 2, "a");
	assert.equal(trace.rows[0]!.unit!.unit_id, "a");
	assert.equal(trace.rows[1]!.unit!.after.pv_kwh, 0);
	assert.throws(() => readTraceWindow(plantRunJson.trace, run, 0, 2, "b"));
	assert.doesNotThrow(() => readRun(plantRunJson.report, run.project_id));
	const counterfeit = structuredClone(plantRunJson.run);
	counterfeit.result.parameter_sources.units[0]!.parameter_sha256 = "0".repeat(
		64,
	);
	assert.throws(() => readRun(counterfeit, run.project_id));
});
test("report output keeps serialized fields mandatory and old column layout optional", () => {
	const report = {
		title: "Contract fixture",
		subtitle: "Serialized output",
		generated_at: "2026-10-25T00:00:00Z",
		locale: "en",
		sections: [
			{
				id: "checks",
				title: "Checks",
				paragraphs: [],
				rows: [],
				table: { columns: ["Check", "Status"], rows: [] },
			},
		],
	};
	assert.doesNotThrow(() => readPlanningReport(report));
	assert.doesNotThrow(() =>
		readPlanningReport({
			...report,
			sections: [
				{
					...report.sections[0],
					table: { ...report.sections[0]!.table, column_weights: [1, 2] },
				},
			],
		}),
	);
	const missing = readObject(structuredClone(report));
	delete readObject((missing.sections as JsonObject[])[0]).paragraphs;
	assert.throws(
		() => readPlanningReport(missing),
		(error: unknown) => error instanceof ApiError && error.status === 502,
	);
	const methodSection = {
		...report.sections[0],
		id: "pv-iv-model",
		rows: [
			{
				label: "Fitting method",
				value: "Batzelis",
				href: "https://pvlib-python.readthedocs.io/en/v0.16.1/reference/generated/pvlib.ivtools.sdm.fit_desoto_batzelis.html",
			},
		],
	};
	assert.doesNotThrow(() =>
		readPlanningReport({ ...report, sections: [methodSection] }),
	);
	for (const section of [
		{ ...methodSection, id: "checks" },
		{
			...methodSection,
			rows: [{ ...methodSection.rows[0], href: "https://example.com/method" }],
		},
	])
		assert.throws(() => readPlanningReport({ ...report, sections: [section] }));
	const sha = "a".repeat(64),
		modelSha = "b".repeat(64),
		materialsSha = "c".repeat(64),
		run = { project_id: "project", revision: 1, manifest_sha256: sha },
		pinned = { "report.source": sha },
		manifest = {
			input_sha256: sha,
			context: { assets: pinned, code_sha256: sha },
		},
		dependencies = { report_source: sha, report_model: modelSha },
		legacy = {
			...run,
			kind: "planning_report_v1",
			input_sha256: sha,
			runtime_sha256: sha,
			pinned_assets: pinned,
			report_sha256: modelSha,
			report,
			source_runs: [],
			prepared_asset: {
				project_id: "project",
				media_type: "application/pdf",
				purpose: "planning_report_pdf_v1",
				content_sha256: sha,
				metadata: { dependencies },
			},
		};
	assert.doesNotThrow(() => readReportResult(legacy, run, manifest));
	const pairedDependencies = { ...dependencies, materials_model: materialsSha },
		paired = {
			...legacy,
			materials_sha256: materialsSha,
			has_draft_items: true,
			prepared_asset: {
				...legacy.prepared_asset,
				metadata: { dependencies: pairedDependencies },
			},
			prepared_attachments: {
				bill_of_materials_csv: {
					id: "csv",
					project_id: "project",
					purpose: "planning_materials_csv_v1",
					media_type: "text/csv",
					content_sha256: sha,
					metadata_sha256: sha,
					metadata: { dependencies: pairedDependencies, locale: "en" },
				},
			},
			dependencies: {
				...pairedDependencies,
				"prepared_attachment.bill_of_materials_csv.content": sha,
				"prepared_attachment.bill_of_materials_csv.metadata": sha,
			},
		};
	assert.doesNotThrow(() => readReportResult(paired, run, manifest));
	const v2 = structuredClone(paired);
	v2.prepared_attachments.bill_of_materials_csv.purpose =
		"planning_materials_csv_v2";
	assert.doesNotThrow(() => readReportResult(v2, run, manifest));
	const v3 = structuredClone(v2);
	v3.prepared_attachments.bill_of_materials_csv.purpose =
		"planning_materials_csv_v3";
	assert.doesNotThrow(() => readReportResult(v3, run, manifest));
	assert.throws(() =>
		readReportResult({ ...paired, materials_sha256: sha }, run, manifest),
	);
});
test("actual managed two-hour result retains frozen identity, source origins and analytic totals", () => {
	const run = readRun(runJson, runJson.project_id, runJson.id);
	assert.equal(readObject(run.result!.metrics).solar_load_kwh, 3.62);
	assert.equal(
		readObject(readObject(run.result!.metrics).solar_autarky).value,
		0.905,
	);
	assert.equal(
		readObject(run.result!.equipment_release).status,
		"not_assessed",
	);
});

test("native roof result binds the generated series to model inputs and retained weather", () => {
	const run = readRun(roofRunJson, roofRunJson.project_id, roofRunJson.id);
	assert.equal(run.result!.interval_count, 8760);
	assert.deepEqual(run.result, roofRunJson.result);
	for (const field of ["input_bundle_sha256", "weather_original_sha256"]) {
		const changed = readObject(structuredClone(roofRunJson));
		const interpretation = readObject(result(changed).profile_interpretation);
		const periods = interpretation.operating_periods as readonly JsonObject[];
		const profiles = readObject(periods[0]!.profiles);
		const source = readObject(readObject(profiles.pv_available_ac).source);
		readObject(source.details)[field] = "0".repeat(64);
		assert.throws(
			() => readRun(changed, roofRunJson.project_id),
			(error: unknown) => error instanceof ApiError && error.status === 502,
		);
	}
});

test("the selected-equipment panel accepts only the bound scenario and validated assessment", () => {
	// Transport-only synthetic binding over the existing real energy document;
	// these two IDs are not product data or a manufacturer-performance fixture.
	const bound = original(),
		output = result(bound),
		model = readObject(output.model),
		context = readObject(readObject(bound.manifest).context),
		pinned = readObject(output.pinned_assets);
	pinned["woo.equipment_inputs"] = "c".repeat(64);
	pinned["equipment.selection"] = "d".repeat(64);
	context.assets = { ...pinned };
	readObject(context.models).equipment_envelope =
		"selected_woo_scenario_envelope_v1";
	const check = (
		id: string,
		status = "unresolved",
		required: number | null = null,
	): JsonObject => ({
		id,
		status,
		reason: "synthetic_transport_contract",
		facts: [],
		actual: null,
		required,
	});
	output.equipment_binding = {
		schema_version: 1,
		model: "selected_woo_scenario_envelope_v1",
		selection_sha256: pinned["equipment.selection"],
		scenario_model: { ...model },
		performance_status: "not_established_by_scenario_envelope",
		selection: {
			schema_version: 1,
			inverter_product_id: 1,
			battery_product_id: 2,
			modules_per_stack: 1,
			parallel_stacks: 1,
			accessory_product_ids: [],
			grid_phase: 3,
			operating_mode: "grid_connected",
			pv_dc_kw: null,
			required_usable_kwh: 5,
			required_discharge_ac_kw: 5,
			product_revisions: { "1": "a".repeat(64), "2": "b".repeat(64) },
		},
		assessment: {
			equipment_status: "unresolved",
			overall_status: "unresolved",
			country_assessment: { status: "unresolved" },
			provisional_bill_of_materials: [],
			selected_products: [
				{ product_id: 1, product_revision: "a".repeat(64) },
				{ product_id: 2, product_revision: "b".repeat(64) },
			],
			checks: [
				check("usable_energy", "unresolved", model.usable_window_kwh as number),
				check(
					"continuous_battery_ac_output",
					"unresolved",
					model.discharge_ac_kw as number,
				),
				check(
					"continuous_battery_ac_charge",
					"unresolved",
					model.charge_ac_kw as number,
				),
				check("scenario_operating_mode"),
				check("scenario_parameter_basis"),
				check("scenario_model_domain"),
			],
		},
	};
	assert.doesNotThrow(() => readRun(bound, runJson.project_id));
	for (const mutate of [
		(binding: MutableObject) => {
			binding.selection_sha256 = "e".repeat(64);
		},
		(binding: MutableObject) => {
			readObject(binding.scenario_model).usable_window_kwh = 900;
		},
		(binding: MutableObject) => {
			readObject(binding.assessment).checks = [];
		},
		(binding: MutableObject) => {
			const products = readObject(binding.assessment)
				.selected_products as JsonObject[];
			readObject(products[0]).product_revision = "f".repeat(64);
		},
	]) {
		const changed = readObject(structuredClone(bound));
		mutate(readObject(result(changed).equipment_binding));
		assert.throws(
			() => readRun(changed, runJson.project_id),
			(error: unknown) => error instanceof ApiError && error.status === 502,
		);
	}
});

test("result mutants cannot be presented as a validated customer result", () => {
	const mutants: ((run: MutableObject) => void)[] = [
		(run) => {
			run.project_id = "f".repeat(32);
		},
		(run) => {
			result(run).revision = 9;
		},
		(run) => {
			result(run).manifest_sha256 = "0".repeat(64);
		},
		(run) => {
			result(run).runtime_sha256 = "0".repeat(64);
		},
		(run) => {
			readObject(result(run).model).eta_charge = 0;
		},
		(run) => {
			readObject(result(run).model).battery_export = "allowed";
		},
		(run) => {
			readObject(result(run).pinned_assets)["gross_load.raw"] = "0".repeat(64);
		},
		(run) => {
			readObject(result(run).verification).checks = [null];
		},
		(run) => {
			readObject(result(run).verification).passed = false;
		},
		(run) => {
			readObject(result(run).profile_interpretation).operating_periods = [{}];
		},
		(run) => {
			readObject(result(run).country_assessment).status = "approved";
		},
		(run) => {
			readObject(result(run).metrics).grid_import_kwh = NaN;
		},
		(run) => {
			readObject(readObject(result(run).metrics).solar_autarky).value = null;
		},
	];
	for (const mutate of mutants) {
		const changed = original();
		mutate(changed);
		assert.throws(
			() => readRun(changed, runJson.project_id),
			(error: unknown) => error instanceof ApiError && error.status === 502,
		);
	}
});

test("mixed or empty load scope keeps its undefined reason and never gains a gross percentage", () => {
	const mixed = original(),
		metrics = readObject(result(mixed).metrics);
	metrics.load_measurement_scope = "mixed";
	metrics.solar_autarky = {
		value: null,
		undefined_reason: "requested_load_scope_is_not_whole_site_gross",
	};
	assert.equal(
		readObject(readRun(mixed, runJson.project_id).result!.metrics)
			.load_measurement_scope,
		"mixed",
	);
	const zero = original(),
		totals = readObject(result(zero).metrics);
	totals.load_demand_kwh = 0;
	totals.pv_generated_ac_kwh = 0;
	totals.solar_autarky = {
		value: null,
		undefined_reason: "gross_load_is_zero",
	};
	totals.pv_input_self_use = {
		value: null,
		undefined_reason: "pv_generation_is_zero",
	};
	assert.equal(
		readObject(
			readObject(readRun(zero, runJson.project_id).result!.metrics)
				.solar_autarky,
		).value,
		null,
	);
});

test("paginated run history validates owner, finite date and actual cursor names", () => {
	const summary = {
		id: runJson.id,
		project_id: runJson.project_id,
		revision: runJson.revision,
		manifest_sha256: runJson.manifest_sha256,
		result_sha256: runJson.result_sha256,
		state: runJson.state,
		is_current: false,
		created_at: 1700000000,
	};
	const next = { before_created_at: summary.created_at, before_id: summary.id };
	assert.deepEqual(
		readRunPage({ items: [summary], next }, runJson.project_id).next,
		next,
	);
	assert.throws(() =>
		readRunPage(
			{ items: [{ ...summary, created_at: 1e30 }], next: null },
			runJson.project_id,
		),
	);
	assert.throws(() =>
		readRunPage(
			{ items: [summary], next: { created_at: 1, run_id: summary.id } },
			runJson.project_id,
		),
	);
});

test("saved DC worker result and trace preserve their equipment and measurement-stage bindings", () => {
	const run = readRun(
		dcRunJson.run,
		dcRunJson.run.project_id,
		undefined,
		"single_ac_energy_replay_v1",
	);
	assert.equal(run.result!.kind, "shared_dc_energy_replay_v1");
	assert.equal(
		run.result!.metrics && readObject(run.result!.metrics).pv_generated_ac_kwh,
		undefined,
	);
	const trace = readTraceWindow(dcRunJson.trace, run, 0, 2);
	assert.equal(trace.measurement_boundaries!.charge, "battery_DC_terminal");
	assert.throws(() =>
		readTraceWindow(
			{
				...trace,
				measurement_boundaries: {
					...trace.measurement_boundaries,
					pv: "PV_AC",
				},
			},
			run,
			0,
			2,
		),
	);

	const capability = readObject(
		structuredClone(run.result!.prepared_dc_parameters),
	);
	const facts = readObject(capability.source_facts);
	const cited = readObject(
		Object.values(facts).find(
			(v) => v && typeof v === "object" && Object.hasOwn(v, "value"),
		),
	);
	const source = readObject(cited.source),
		field = "battery_grid_charging_supported";
	facts[`${source.product_id}.${field}`] = {
		...cited,
		value: "not_supported",
		raw_value: "not_supported",
		unit: null,
		source: { ...source, figure_key: field },
	};
	assert.doesNotThrow(() => readDcParameters(capability));
	for (const change of [
		(p: MutableObject) => {
			readObject(p.loss_scenario).eta_inverter_forward = 0.5;
		},
		(p: MutableObject) => {
			readObject(
				readObject(
					Object.values(readObject(p.source_facts)).find(
						(v) => typeof v === "object" && v && Object.hasOwn(v, "value"),
					),
				).source,
			).url = "https://user:password@de-linker.com/manual.pdf";
		},
		(p: MutableObject) => {
			readObject(
				readObject(
					Object.values(readObject(p.source_facts)).find(
						(v) => typeof v === "object" && v && Object.hasOwn(v, "value"),
					),
				).source,
			).page = "invalid";
		},
	]) {
		const mutant = readObject(structuredClone(dcRunJson.run));
		change(readObject(result(mutant).prepared_dc_parameters));
		assert.throws(() => readRun(mutant, dcRunJson.run.project_id));
	}
	const wrong = readObject(structuredClone(dcRunJson.run));
	readObject(result(wrong).model).parameters_source_sha256 = "0".repeat(64);
	assert.throws(() => readRun(wrong, dcRunJson.run.project_id));
});
