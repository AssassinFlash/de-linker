import test from "node:test";
import assert from "node:assert/strict";
import fixture from "../../tests/fixtures/preparation-flow.json" with { type: "json" };
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

test("all three exact run commands accept a revision and reject browser provider controls", () => {
	for (const path of ["runs/energy", "runs/weather", "runs/pv"] as const) {
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

test("weather observations distinguish acquisition, local publication and independent cleanup", () => {
	const runId = fixture.weather_run.id;
	const complete = readWeatherStatus(fixture.weather_status, runId);
	assert.equal(complete.acquisitionState, "captured");
	assert.equal(weatherStatusPending(complete), false);
	const pending = readWeatherStatus(
		{
			...fixture.weather_status,
			task_state: "cancelled",
			cleanup: { state: "queued", attempt: 0, max_attempts: 2, error: null },
		},
		runId,
	);
	assert.equal(weatherStatusPending(pending), true);
	assert.throws(() =>
		readWeatherStatus({ ...fixture.weather_status, observation: null }, runId),
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
