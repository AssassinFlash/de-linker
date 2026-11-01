import test from "node:test";
import dcPlant from "../../tests/fixtures/dc-plant-energy-run.json" with { type: "json" };
import assert from "node:assert/strict";
import fixture from "../../tests/fixtures/index.ts";
import {
	readRun,
	runTask,
	RUN_OPERATIONS,
	readPlanningOperation,
} from "./planningProtocol.ts";
import { readProject, readObject } from "./readProtocol.ts";
import { readWeatherStatus, weatherStatusPending } from "./weatherStatus.ts";
import { selectPreparation } from "../domain/preparationSelection.ts";
import { readAsset } from "../domain/profiles.ts";
import { readPreparationWeather } from "./preparationBasis.ts";
import type { JsonObject } from "./protocol.ts";
import { readDirectBeamResult } from "./directBeamResult.ts";
import {
	readBeamWeatherAssets,
	readBeamWeatherPreview,
} from "./directBeamWeather.ts";
import { compileDirectBeam, readDirectBeam } from "../domain/directBeam.ts";
import { readPreparationResult } from "./readPreparationResult.ts";
import {
	GEOMETRIC_PV_MODEL,
	GEOMETRIC_PV_MODEL_V1,
	GEOMETRIC_PV_PURPOSE,
	GEOMETRIC_PV_RESULTS,
	GEOMETRIC_PV_MODEL_SERIES,
	GEOMETRIC_PV_TASK,
} from "../domain/geometricPv.ts";

test("actual geometric witness retains night/daylight, exact source proofs and a separate report role", () => {
	const native = fixture.direct_beam;
	const run = readRun(
		native.run,
		native.project.id,
		native.run.id,
		RUN_OPERATIONS["runs/direct-beam"],
	);
	const result = readDirectBeamResult(
		run.result,
		run as unknown as JsonObject,
		run.manifest,
	);
	assert.equal(result.rows[0]!.modules[0]!.status, "night");
	assert.equal(result.rows[0]!.modules[0]!.fine, null);
	assert.equal(result.rows[1]!.modules[0]!.status, "sampled");
	assert.ok(result.rows[1]!.modules[0]!.fine);
	assert.equal(
		result.rows[1]!.irradiance_at_utc,
		native.run.result.visibility.rows[1]!.irradiance_at_utc,
	);
	const assets = readBeamWeatherAssets(
		native.weather_assets,
		native.project.id,
		0,
		100,
	);
	const preview = readBeamWeatherPreview(
		native.weather_preview,
		native.project.id,
		assets.assets[0]!,
		0,
		100,
	);
	assert.equal(
		preview.weatherDocumentSha256,
		native.run.result.visibility.sources.weather_document_sha256,
	);
	assert.deepEqual(
		compileDirectBeam(
			readDirectBeam(native.project.inputs.direct_beam_visibility),
			native.visibility_limits,
		),
		native.project.inputs.direct_beam_visibility,
	);
	assert.doesNotThrow(() => readRun(native.report_run, native.project.id));
	assert.equal(native.report_options.direct_beam_run_id, run.id);
	const incomplete = structuredClone(native.run) as unknown as {
		manifest: { context: { assets: Record<string, unknown> } };
		result: {
			pinned_assets: Record<string, unknown>;
			dependencies: Record<string, unknown>;
			visibility: { sources: Record<string, unknown> };
		};
	};
	delete incomplete.manifest.context.assets.geometry;
	delete incomplete.result.pinned_assets.geometry;
	delete incomplete.result.dependencies.geometry;
	delete incomplete.result.visibility.sources.geometry_sha256;
	assert.throws(() => readRun(incomplete, native.project.id));
	const changed = structuredClone(native.run);
	changed.result.visibility.rows[1]!.modules[0]!.module_id = "unrelated:0:0";
	assert.throws(() => readRun(changed, native.project.id));
	assert.throws(() =>
		readDirectBeam({
			...native.project.inputs.direct_beam_visibility,
			sampling: { coarse_cells_per_edge: 2, fine_cells_per_edge: 2 },
		}),
	);
});

test("actual managed weather and complete-year PV publication are consumed as their own task kinds", () => {
	for (const [raw, path] of [
		[fixture.weather_run, "runs/weather"],
		[fixture.pv_run, "runs/pv"],
	] as const) {
		const run = readRun(raw, raw.project_id, raw.id, RUN_OPERATIONS[path]);
		assert.equal(runTask(run), RUN_OPERATIONS[path]);
		assert.ok(run.result?.prepared_asset);
		assert.throws(() =>
			readRun(
				{ ...raw, state: "queued", result: null, result_sha256: null },
				raw.project_id,
				raw.id,
				RUN_OPERATIONS["runs/energy"],
			),
		);
	}
	assert.equal(
		readAsset(fixture.pv_run.result.prepared_asset, fixture.pv_run.project_id)
			.purpose,
		"pvlib_reference_profile_v1",
	);
});

test("preparation replies cannot substitute frozen identity, asset binding, summary or assessment", () => {
	for (const original of [fixture.weather_run, fixture.pv_run]) {
		const mutations: ((
			run: typeof fixture.weather_run | typeof fixture.pv_run,
		) => void)[] = [
			(run) => {
				run.result.runtime_sha256 = "0".repeat(64);
			},
			(run) => {
				run.result.prepared_asset.project_id = "0".repeat(32);
			},
			(run) => {
				run.result.dependencies.prepared_asset_content = "0".repeat(64);
			},
			(run) => {
				run.manifest.context.models.task = "different_task";
			},
			(run) => {
				run.result.pinned_assets.runtime_bundle = "0".repeat(64);
			},
		];
		for (const mutate of mutations) {
			const changed = structuredClone(original);
			mutate(changed);
			assert.throws(() => readRun(changed, original.project_id));
		}
	}
	const pv = structuredClone(fixture.pv_run);
	pv.result.near_shading_assessment.status = "approved";
	assert.throws(() => readRun(pv, pv.project_id));
	const weather = structuredClone(fixture.weather_run);
	weather.result.weather_summary.latitude_deg = 200;
	assert.throws(() => readRun(weather, weather.project_id));
});

test("exact run commands accept a revision and reject browser provider controls", () => {
	for (const path of [
		"runs/energy",
		"runs/weather",
		"runs/pv",
		"runs/pvgis-reference",
		"runs/direct-beam",
		"runs/geometric-pv",
	] as const) {
		const command = {
			schema_version: 1,
			project_id: fixture.weather_run.project_id,
			expected_revision: 2,
			key: crypto.randomUUID(),
		};
		assert.deepEqual(
			readPlanningOperation(path, JSON.stringify(command)),
			command,
		);
		assert.throws(() =>
			readPlanningOperation(
				path,
				JSON.stringify({
					...command,
					provider_url: "https://elsewhere.invalid",
				}),
			),
		);
	}
});

test("the native geometric PV profile retains the complete weather axis and is explicitly adopted only as AC", () => {
	const native = fixture.geometric_pv;
	const project = readProject(native.project);
	const run = readRun(
		native.run,
		project.id,
		native.run.id,
		RUN_OPERATIONS["runs/geometric-pv"],
	);
	assert.equal(readObject(run.result?.profile_summary).interval_count, 8760);
	assert.equal(
		readAsset(native.profile_asset, project.id).purpose,
		"geometric_pv_reference_profile_v1",
	);
	const inputs = selectPreparation(
		project.inputs,
		run,
		project,
		native.profile_asset,
	);
	assert.deepEqual(readObject(inputs.profile_selections).selected, {
		pv_available_ac: native.profile_asset.id,
	});
	assert.equal(project.inputs.profile_selections, undefined);
	assert.throws(
		() =>
			selectPreparation(
				{ ...project.inputs, energy_scenario: { coupling: "shared_dc" } },
				run,
				project,
				native.profile_asset,
			),
		/pvgis_reference_dc_conflict/,
	);
	assert.doesNotThrow(() => readRun(native.report_run, project.id));
	const changed = structuredClone(native.project.inputs);
	changed.geometric_pv_preparation.weather_asset_id = "0".repeat(32);
	assert.throws(() =>
		selectPreparation(changed, run, project, native.profile_asset),
	);
	for (const modify of [
		(value: typeof native.run.result) => {
			value.scope.diffuse_policy = "fully_shaded";
		},
		(value: typeof native.run.result) => {
			value.profile_summary.interval_count = 2;
		},
		(value: typeof native.run.result) => {
			value.prepared_asset.metadata.weather.start_utc =
				"2023-06-01T00:00:00+00:00";
		},
		(value: typeof native.run.result) => {
			value.near_shading_assessment.status = "approved";
		},
	]) {
		const changedRun = structuredClone(native.run);
		modify(changedRun.result);
		assert.throws(() => readRun(changedRun, project.id));
	}
});

test("a queued preparation acknowledgement must already bind the declared task model", () => {
	for (const original of [fixture.weather_run, fixture.pv_run]) {
		const changed = {
			...structuredClone(original),
			state: "queued",
			result: null,
			result_sha256: null,
		};
		changed.manifest.context.models.task = "different_task";
		assert.throws(() => readRun(changed, original.project_id));
	}
});

test("internally consistent source substitutions still fail their frozen task-role bindings", () => {
	const weather = structuredClone(fixture.weather_run),
		alternate = "0".repeat(64);
	weather.result.dependencies.acquisition_plan = alternate;
	weather.result.prepared_asset.metadata.dependencies.acquisition_plan =
		alternate;
	assert.throws(() => readRun(weather, weather.project_id));
	const pv = structuredClone(fixture.pv_run);
	pv.result.dependencies.prepared_asset_content = alternate;
	pv.result.prepared_asset.content_sha256 = alternate;
	assert.throws(() => readRun(pv, pv.project_id));
});

test("removing required source roles from every agreeing map cannot make them optional", () => {
	const weather = readObject(structuredClone(fixture.weather_run));
	const context = readObject(readObject(weather.manifest).context);
	const result = readObject(weather.result);
	const without = (value: JsonObject, key: string): JsonObject =>
		Object.fromEntries(Object.entries(value).filter(([name]) => name !== key));
	const changed = {
		...weather,
		manifest: {
			...readObject(weather.manifest),
			context: {
				...context,
				assets: without(readObject(context.assets), "weather_acquisition.plan"),
			},
		},
		result: {
			...result,
			pinned_assets: without(
				readObject(result.pinned_assets),
				"weather_acquisition.plan",
			),
			dependencies: without(
				readObject(result.dependencies),
				"acquisition_plan",
			),
			prepared_asset: {
				...readObject(result.prepared_asset),
				metadata: {
					...readObject(readObject(result.prepared_asset).metadata),
					dependencies: without(
						readObject(
							readObject(readObject(result.prepared_asset).metadata)
								.dependencies,
						),
						"acquisition_plan",
					),
				},
			},
		},
	};
	assert.throws(() => readRun(changed, fixture.weather_run.project_id));
	const pv = structuredClone(fixture.pv_run);
	delete (
		pv.manifest.context.assets as Partial<typeof pv.manifest.context.assets>
	)["weather.metadata"];
	delete (pv.result.pinned_assets as Partial<typeof pv.result.pinned_assets>)[
		"weather.metadata"
	];
	assert.throws(() => readRun(pv, pv.project_id));
});

test("explicit weather selection preserves concurrent edits and rejects changed request/source proofs", () => {
	const run = readRun(fixture.weather_run, fixture.weather_run.project_id),
		historical = readProject(fixture.weather_project),
		asset = readObject(fixture.weather_run.result.prepared_asset),
		inputs: JsonObject = {
			...historical.inputs,
			user_note: "Changed while the job completed",
		};
	const selected = selectPreparation(inputs, run, historical, asset);
	assert.equal(selected.user_note, inputs.user_note);
	assert.equal(readObject(selected.pv_preparation).weather_asset_id, asset.id);
	assert.equal(inputs.pv_preparation, undefined);
	const withoutRequest = { ...inputs };
	delete withoutRequest.weather_acquisition;
	assert.throws(() =>
		selectPreparation(withoutRequest, run, historical, asset),
	);
	assert.throws(() =>
		selectPreparation(
			{
				...inputs,
				weather_acquisition: {
					...readObject(inputs.weather_acquisition),
					request: {},
				},
			},
			run,
			historical,
			asset,
		),
	);
	assert.throws(() =>
		selectPreparation(
			inputs,
			run,
			{ ...historical, input_sha256: "0".repeat(64) },
			asset,
		),
	);
	assert.throws(() =>
		selectPreparation(inputs, run, historical, {
			...asset,
			content_sha256: "0".repeat(64),
		}),
	);
});

test("PV selection preserves load edits, invalidates prepared energy and refuses changed roofs/models", () => {
	const run = readRun(fixture.pv_run, fixture.pv_run.project_id),
		historical = readProject(fixture.pv_project),
		asset = readObject(fixture.pv_run.result.prepared_asset),
		inputs = {
			...historical.inputs,
			user_note: "Different load source",
			energy_replay: { previous: "old" },
		};
	const selected = selectPreparation(inputs, run, historical, asset);
	assert.equal(selected.user_note, inputs.user_note);
	assert.equal(selected.energy_replay, undefined);
	assert.equal(
		readObject(readObject(selected.profile_selections).selected)
			.pv_available_ac,
		asset.id,
	);
	assert.ok(typeof asset.id === "string");
	const joint = selectPreparation(
		{
			...inputs,
			equipment_plant: dcPlant.project.inputs.equipment_plant,
			profile_selections: {
				schema_version: 1,
				selected: { pv_available_ac: asset.id },
			},
		},
		run,
		historical,
		asset,
	);
	const chosen = readObject(readObject(joint.profile_selections).selected);
	assert.equal(chosen.pv_reference, asset.id);
	assert.equal(chosen.pv_available_ac, undefined);
	assert.equal(joint.user_note, inputs.user_note);

	assert.throws(() =>
		selectPreparation({ ...inputs, geometry: {} }, run, historical, asset),
	);
	assert.throws(() =>
		selectPreparation({ ...inputs, pv_generation: {} }, run, historical, asset),
	);
	assert.throws(() =>
		selectPreparation(
			{
				...inputs,
				pv_preparation: { schema_version: 1, weather_asset_id: "0".repeat(32) },
			},
			run,
			historical,
			asset,
		),
	);
});

test("weather observations distinguish local download and validated publication", () => {
	const runId = fixture.weather_run.id;
	const complete = readWeatherStatus(fixture.weather_status, runId);
	assert.equal(complete.acquisitionState, "captured");
	assert.equal(weatherStatusPending(complete), false);
	const pending = readWeatherStatus(
		{
			...fixture.weather_status,
			task_state: "running",
			acquisition_state: "fetching",
			capture_sha256: null,
		},
		runId,
	);
	assert.equal(weatherStatusPending(pending), true);
	assert.throws(() =>
		readWeatherStatus(
			{ ...fixture.weather_status, capture_sha256: null },
			runId,
		),
	);
	assert.throws(() =>
		readWeatherStatus(
			{ ...fixture.weather_status, task_state: "guessed" },
			runId,
		),
	);
	assert.throws(() =>
		readWeatherStatus(fixture.weather_status, "0".repeat(32)),
	);
});

test("source presentation joins actual PVGIS databases to the weather asset used by the frozen task", () => {
	for (const original of [fixture.weather_run, fixture.pv_run]) {
		const run = readRun(original, original.project_id),
			originalWeather = fixture.weather_run.result.prepared_asset;
		const metadata = readPreparationWeather(originalWeather, run);
		const details = readObject(
			readObject(readObject(metadata.weather).source).details,
		);
		assert.equal(details.radiation_database, "PVGIS-SARAH3");
		assert.equal(details.meteo_database, "ERA5");
		const changed = structuredClone(originalWeather);
		changed.metadata_sha256 = "0".repeat(64);
		assert.throws(() => readPreparationWeather(changed, run));
		const foreign = { ...originalWeather, project_id: "0".repeat(32) };
		assert.throws(() => readPreparationWeather(foreign, run));
	}
});

test("geometric preparation requires the frozen executor generation to match the result model", () => {
	const sha = "a".repeat(64);
	const assetId = "b".repeat(32);
	const packet = (model: string, generation: string) => {
		const item = GEOMETRIC_PV_RESULTS.find((row) => row.model === model);
		assert.ok(item);
		const summary = {
			start_utc: "2023-01-01T00:00:00+00:00",
			end_utc: "2023-01-01T01:00:00+00:00",
			interval_count: 1,
			energy_kwh: 1,
			measurement: "pv_available_ac",
			origin: "modelled",
			model_role: item.role,
			reconstructed_means: true,
		};
		const children = {
			"model.inputs": sha,
			"model.witness": sha,
			"project.parameters": sha,
			"weather.metadata": sha,
			"weather.raw": sha,
			"woo.module_inputs": sha,
			...(model === GEOMETRIC_PV_MODEL_SERIES
				? { "woo.equipment_inputs": sha }
				: {}),
		};
		const assets = {
			runtime_bundle: sha,
			"weather.raw": sha,
			"weather.metadata": sha,
			"woo.module_inputs": sha,
			...(model === GEOMETRIC_PV_MODEL_SERIES
				? { "woo.equipment_inputs": sha }
				: {}),
		};
		return {
			run: {
				state: "succeeded",
				result_sha256: sha,
				project_id: "project",
				revision: 1,
				manifest_sha256: sha,
			},
			manifest: {
				input_sha256: sha,
				context: {
					code_sha256: sha,
					models: { task: GEOMETRIC_PV_TASK, generation },
					assets,
				},
			},
			result: {
				schema: 1,
				kind: GEOMETRIC_PV_TASK,
				model,
				project_id: "project",
				revision: 1,
				input_sha256: sha,
				manifest_sha256: sha,
				runtime_sha256: sha,
				pinned_assets: assets,
				dependencies: {
					...children,
					prepared_asset_content: sha,
					prepared_asset_metadata: sha,
				},
				prepared_asset: {
					id: assetId,
					project_id: "project",
					media_type: "application/json",
					content_sha256: sha,
					metadata_sha256: sha,
					purpose: GEOMETRIC_PV_PURPOSE,
					metadata: {
						retention: "permanent",
						schema: 1,
						profile_type: GEOMETRIC_PV_PURPOSE,
						derived_from_revision: 1,
						geometry_sha256: sha,
						parameters_sha256: sha,
						dependencies: children,
						interpretation: summary,
						weather: {
							interval_count: 1,
							start_utc: summary.start_utc,
							end_utc: summary.end_utc,
							weather_document_sha256: sha,
						},
					},
				},
				profile_summary: summary,
				scope: {
					diffuse_policy: item.diffuse,
					thermal_policy: "sapm_from_module_mean_poa_v1",
					electrical_policy:
						model === GEOMETRIC_PV_MODEL_SERIES
							? "whole_module_forward_series_iv_single_string_per_tracker_v1"
							: "uniform_module_pvwatts_independent_mpp_sum_v1",
				},
				equipment_release: { status: "not_assessed" },
				country_assessment: { status: "not_assessed" },
				near_shading_assessment: { status: item.shading },
			},
		};
	};
	for (const model of [
		GEOMETRIC_PV_MODEL_V1,
		GEOMETRIC_PV_MODEL,
		GEOMETRIC_PV_MODEL_SERIES,
	]) {
		const matched = packet(model, model);
		assert.equal(
			readPreparationResult(
				matched.result,
				matched.run,
				matched.manifest,
				GEOMETRIC_PV_TASK,
			).model,
			model,
		);
	}
	const mismatched = packet(GEOMETRIC_PV_MODEL, GEOMETRIC_PV_MODEL_V1);
	assert.throws(() =>
		readPreparationResult(
			mismatched.result,
			mismatched.run,
			mismatched.manifest,
			GEOMETRIC_PV_TASK,
		),
	);
});
