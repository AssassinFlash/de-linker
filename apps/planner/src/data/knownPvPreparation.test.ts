import assert from "node:assert/strict";
import test from "node:test";
import fixture from "../../tests/fixtures/known-pv-reference.json" with { type: "json" };
import { emptyScenario } from "../domain/energyScenario.ts";
import { prepareKnownPvForComparison } from "./knownPvPreparation.ts";
import type { JsonObject, Project } from "./protocol.ts";
import type { PlanningRun } from "./planningProtocol.ts";

const project = fixture.project as Project;
const run = fixture.run as PlanningRun;
const asset = fixture.run.result.prepared_asset;

function workflow(inputs: JsonObject) {
	const calls: string[] = [];
	const updated = { ...project, inputs };
	return {
		calls,
		options: {
			inputs,
			projectId: project.id,
			query: async (path: string) => {
				calls.push(path);
				if (path === "assets/read") return asset;
				if (path === "projects/read") return project;
				throw new Error(path);
			},
			save: async () => {
				calls.push("save");
				return updated;
			},
			start: async () => {
				calls.push("start");
				return run;
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
