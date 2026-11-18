import assert from "node:assert/strict";
import { test } from "node:test";
import { readEquipmentSearchResult } from "./equipmentSearch.ts";
import type { Json, JsonObject } from "./protocol.ts";

function fixture() {
	const pinned = { "woo.equipment_inputs": "a".repeat(64) },
		runtime = "b".repeat(64);
	const run = {
		project_id: "project",
		revision: 2,
		manifest_sha256: "c".repeat(64),
	};
	const manifest = {
		input_sha256: "d".repeat(64),
		context: { code_sha256: runtime, assets: pinned },
	};
	const result: JsonObject = {
		schema: 1,
		kind: "search_woo_equipment_v1",
		project_id: "project",
		revision: 2,
		input_sha256: manifest.input_sha256,
		manifest_sha256: run.manifest_sha256,
		runtime_sha256: runtime,
		pinned_assets: pinned,
		search: {
			completion: "exhausted_supported_domain",
			work_used: 1,
			work_budget: 100,
			qualified_count: 0,
			ranking: "not_performed_before_qualification",
			products: [],
			coverage: {
				template: "one_converter_one_external_battery_assembly",
				gaps: {},
			},
			demand: {
				model: "profile_physical_bounds_v1",
				controller: "self_consumption_with_reserve_v1",
				horizon_start_utc: "2026-01-01T00:00:00Z",
				horizon_end_utc: "2026-01-01T04:00:00Z",
				interval_count: 4,
				completion: "complete",
				work_used: 4,
				work_budget: 100,
				baseline: {
					load_kwh: 8,
					pv_available_kwh: 8,
					direct_pv_use_kwh: 4,
					grid_import_kwh: 4,
					grid_export_kwh: 4,
					peak_grid_import_kw: 2,
					over_target_kwh: 0,
				},
			},
			candidates: [
				{
					id: "e".repeat(64),
					assessment_sha256: "f".repeat(64),
					status: "unresolved",
					violated_checks: 0,
					unresolved_checks: 1,
					usable_energy_kwh: 3,
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
						required_usable_kwh: null,
						required_discharge_ac_kw: null,
						product_revisions: { "1": "a".repeat(64), "2": "b".repeat(64) },
					},
					demand: {
						status: "bounded",
						reason: "optimistic_profile_bound",
						basis:
							"optimistic_full_initial_storage_lossless_upper_bound_not_dispatch",
						additional_pv_use_upper_kwh: 3,
						peak_import_lower_bound_kw: null,
						missing_facts: ["initial_stored_energy"],
						source_facts: [],
					},
				},
			],
		},
	};
	return { run, manifest, result };
}

test("bounded candidate results preserve physical-bound semantics", () => {
	const { run, manifest, result } = fixture();
	assert.equal(readEquipmentSearchResult(result, run, manifest), result);
});

for (const malformed of [-1, Number.NaN, 5, "3"]) {
	test(`reject malformed or impossible solar benefit bound ${malformed}`, () => {
		const { run, manifest, result } = fixture();
		const search = result.search as JsonObject;
		const candidate = (search.candidates as JsonObject[])[0]!;
		(candidate.demand as Record<string, Json>).additional_pv_use_upper_kwh =
			malformed;
		assert.throws(() => readEquipmentSearchResult(result, run, manifest));
	});
}

test("shared DC can retain equipment candidates when site AC metrics are unknown", () => {
	const { run, manifest, result } = fixture();
	const search = result.search as JsonObject;
	const summary = search.demand as JsonObject;
	const baseline = summary.baseline as Record<string, Json>;
	for (const key of Object.keys(baseline)) {
		if (key !== "load_kwh") baseline[key] = null;
	}
	const candidate = (search.candidates as JsonObject[])[0]!;
	const demand = candidate.demand as Record<string, Json>;
	demand.status = "unresolved";
	demand.reason = "profile_topology_evidence_missing";
	demand.additional_pv_use_upper_kwh = null;
	demand.missing_facts = ["project_pv_output_through_assigned_dc_converters"];
	assert.equal(readEquipmentSearchResult(result, run, manifest), result);
	demand.additional_pv_use_upper_kwh = 0;
	assert.throws(() => readEquipmentSearchResult(result, run, manifest));
});

test("bounded result cannot masquerade as verified replay", () => {
	const { run, manifest, result } = fixture();
	const candidate = (
		(result.search as JsonObject).candidates as JsonObject[]
	)[0]!;
	(candidate.demand as Record<string, Json>).status = "satisfied";
	assert.throws(() => readEquipmentSearchResult(result, run, manifest));
});
