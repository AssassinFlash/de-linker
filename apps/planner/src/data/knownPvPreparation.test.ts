import assert from "node:assert/strict";
import test from "node:test";
import fixture from "../../tests/fixtures/known-pv-reference.json" with { type: "json" };
import roofFixture from "../../tests/fixtures/preparation-flow-darwin-arm64.json" with { type: "json" };
import { emptyBrief } from "../domain/brief.ts";
import { emptyScenario } from "../domain/energyScenario.ts";
import { prepareKnownPvForComparison } from "./knownPvPreparation.ts";
import type { JsonObject, Project } from "./protocol.ts";
import type { PlanningRun } from "./planningProtocol.ts";

const project = fixture.project as Project;
const run = fixture.run as PlanningRun;
const asset = fixture.run.result.prepared_asset;

function workflow(
	inputs: JsonObject,
	source: { project: Project; run: PlanningRun; asset: JsonObject } = {
		project,
		run,
		asset,
	},
) {
	const calls: string[] = [];
	const updated = { ...source.project, inputs };
	return {
		calls,
		options: {
			inputs,
			projectId: source.project.id,
			query: async (path: string) => {
				calls.push(path);
				if (path === "assets/read") return source.asset;
				if (path === "projects/read") return source.project;
				throw new Error(path);
			},
			save: async () => {
				calls.push("save");
				return updated;
			},
			start: async () => {
				calls.push("start");
				return source.run;
			},
			signal: new AbortController().signal,
		},
	};
}

test("known PV prepares on the saved revision and supplies a validated source for current-input operations", async () => {
	const { calls, options } = workflow(project.inputs);
	const apply = await prepareKnownPvForComparison(options);
	assert.ok(apply);
	const changed = apply({
		...project.inputs,
		profile_selections: {
			schema_version: 1,
			selected: { gross_load: "a".repeat(32) },
		},
	});
	assert.deepEqual(calls, ["save", "start", "assets/read"]);
	assert.deepEqual(changed.profile_selections, {
		schema_version: 1,
		selected: { gross_load: "a".repeat(32), pv_available_ac: asset.id },
	});
	assert.throws(
		() =>
			apply({
				...project.inputs,
				brief: {
					...(project.inputs.brief as JsonObject),
					site: { ...fixture.project.inputs.brief.site, longitude: 1 },
				},
			}),
		/preparation_source_changed/,
	);
});

test("an existing matching known PV source is reused without another job", async () => {
	const { calls, options } = workflow({
		...project.inputs,
		profile_selections: {
			schema_version: 1,
			selected: { pv_available_ac: asset.id },
		},
	});
	const apply = await prepareKnownPvForComparison(options);
	assert.deepEqual(apply?.(options.inputs), options.inputs);
	assert.deepEqual(calls, ["assets/read", "projects/read"]);
});

test("a refused PVGIS job cannot adopt a profile", async () => {
	const { calls, options } = workflow(project.inputs);
	await assert.rejects(
		prepareKnownPvForComparison({
			...options,
			start: async () => ({ ...run, state: "failed", result: null }),
		}),
		/known_pv_preparation_failed/,
	);
	assert.deepEqual(calls, ["save"]);
});

test("known PV cannot compare disjoint profile years", async () => {
	const { options } = workflow(project.inputs);
	const apply = await prepareKnownPvForComparison(options);
	assert.ok(apply);
	const scenario = emptyScenario();
	assert.throws(
		() =>
			apply({
				...project.inputs,
				energy_scenario: {
					...scenario,
					schedule: [
						{
							...scenario.schedule[0]!,
							pv_enabled: true,
							start_utc: "2026-01-01T00:00:00Z",
							end_utc: "2026-12-31T23:00:00Z",
						},
					],
				},
			}),
		/known_pv_no_common_period/,
	);
});

const roof = {
	project: roofFixture.pvgis_reference_project as Project,
	run: roofFixture.pvgis_reference_run as PlanningRun,
	asset: roofFixture.pvgis_reference_run.result.prepared_asset,
};
const roofInputs = {
	...roof.project.inputs,
	brief: { ...emptyBrief(), system_scope: "new_pv_storage" },
};

test("the native roof run supplies its AC profile and the 20 placed 460 Wp modules", async () => {
	const { calls, options } = workflow(roofInputs, roof);
	const apply = await prepareKnownPvForComparison(options);
	assert.ok(apply);
	const changed = apply(roofInputs);
	assert.deepEqual(calls, ["save", "start", "assets/read"]);
	assert.deepEqual(changed.profile_selections, {
		schema_version: 1,
		selected: { pv_available_ac: roof.asset.id },
	});
	assert.equal((changed.equipment_setup as JsonObject).pv_dc_kw, 9.2);
	const geometry = roofFixture.pvgis_reference_project.inputs.geometry;
	assert.throws(
		() =>
			apply({
				...roofInputs,
				geometry: { ...geometry, arrays: geometry.arrays.slice(1) },
			}),
		/preparation_source_changed/,
	);
});

test("a matching roof curve is reused and another owned AC curve is preserved", async () => {
	const inputs = {
		...roofInputs,
		profile_selections: {
			schema_version: 1,
			selected: { pv_available_ac: roof.asset.id },
		},
	};
	const { calls, options } = workflow(inputs, roof);
	const apply = await prepareKnownPvForComparison(options);
	assert.ok(apply);
	assert.equal((apply(inputs).equipment_setup as JsonObject).pv_dc_kw, 9.2);
	assert.deepEqual(calls, ["assets/read", "projects/read"]);
	const alternate = workflow(inputs, {
		...roof,
		asset: { ...roof.asset, purpose: "pvgis_system_profile_v1" },
	});
	const preserve = await prepareKnownPvForComparison(alternate.options);
	assert.ok(preserve);
	assert.deepEqual(
		preserve(inputs).profile_selections,
		inputs.profile_selections,
	);
	assert.deepEqual(alternate.calls, ["assets/read"]);
});
