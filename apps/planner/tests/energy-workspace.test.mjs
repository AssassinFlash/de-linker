import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";
import { emptyScenario } from "../src/domain/energyScenario.ts";
import { SimpleEnergySetup } from "../src/components/energy/SimpleEnergySetup.tsx";
import pvOnlyPlantFixture from "./fixtures/plant-pv-only-energy-run.json" with { type: "json" };
import { readRun } from "../src/data/planningProtocol.ts";
import { PlantParameterBasis } from "../src/components/energy/PlantParameterBasis.tsx";
import { RunResult } from "../src/components/energy/RunResult.tsx";
import { RunBasis } from "../src/components/energy/RunBasis.tsx";
import energyInputs from "./fixtures/energy-inputs.json" with { type: "json" };
import { EnergyWorkspace } from "../src/components/energy/EnergyWorkspace.tsx";
import { EnergyError } from "../src/components/energy/EnergyError.tsx";
import {
	editDraft,
	undoDraft,
	redoDraft,
	isDirty,
	projectInputContract,
} from "../src/domain/draft.ts";
import { authoredCalculationInputs } from "../src/domain/currentCalculation.ts";
import { equipmentDraft } from "../src/domain/equipment.ts";
import { plantEnergyDraft } from "../src/domain/plantEnergy.ts";
import { useProjectDraft } from "../src/data/useProjectDraft.ts";
import { PlannerClient } from "../src/data/PlannerClient.ts";
import { ApiError } from "../src/data/protocol.ts";
import scenario from "./fixtures/energy-scenario.json" with { type: "json" };
import selections from "./fixtures/energy-selections.json" with { type: "json" };
import actualRun from "./fixtures/energy-run.json" with { type: "json" };
import plantFixture from "./fixtures/plant-energy-run.json" with { type: "json" };

test("native PV-only plant parameter presentation explicitly has no battery sources", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const run = readRun(pvOnlyPlantFixture.run, pvOnlyPlantFixture.project.id);
	await act(async () =>
		root.render(
			React.createElement(PlantParameterBasis, {
				result: run.result,
				locale: "en-GB",
			}),
		),
	);
	assert.match(dom.element.textContent, /No battery parameters are used/);
	assert.doesNotMatch(
		dom.element.textContent,
		/Connected battery port|Usable storage capacity|Charge efficiency/,
	);
	assert.equal(dom.element.querySelector("details"), null);
});

test("native PV-only plant result shows PV and grid flows without an empty storage table", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const run = readRun(pvOnlyPlantFixture.run, pvOnlyPlantFixture.project.id);
	await act(async () =>
		root.render(
			React.createElement(RunResult, {
				run,
				locale: "en-GB",
				dirty: false,
				confirmedRevision: run.revision,
			}),
		),
	);
	assert.match(dom.element.textContent, /Solar supplied to load/);
	assert.match(dom.element.textContent, /Grid import/);
	assert.match(dom.element.textContent, /no battery storage/);
	assert.doesNotMatch(
		dom.element.textContent,
		/Stored energy by unit|Initial and final stored energy/,
	);
	assert.equal(run.result.equipment_binding.plant.units.length, 2);
	assert.match(dom.element.textContent, /A · a/);
	assert.match(dom.element.textContent, /B · b/);
});

for (const kind of ["single", "plant", "pv_only"]) {
	const joint = kind !== "single";
	test(`${kind} source details read the run's frozen inputs and retain owned source hash checks`, async (t) => {
		const dom = setupDom();
		const { createRoot } = await import("react-dom/client");
		const root = createRoot(dom.element);
		const queryClient = new QueryClient({
			defaultOptions: { queries: { retry: false } },
		});
		t.after(async () => {
			await dom.dispose(root);
			queryClient.clear();
		});
		const run =
			kind === "pv_only"
				? readRun(pvOnlyPlantFixture.run, pvOnlyPlantFixture.project.id)
				: joint
					? plantFixture.run
					: actualRun;
		const inputs =
			kind === "pv_only"
				? pvOnlyPlantFixture.execution_inputs
				: joint
					? plantFixture.project.inputs
					: { energy_replay: energyInputs };
		const selected = inputs[joint ? "energy_plant" : "energy_replay"];
		const pins = run.manifest.context.assets;
		const assets = new Map();
		for (const [role, field] of [
			["gross_load", "gross_load_asset_id"],
			["pv_available_ac", "pv_available_asset_id"],
			["critical_load", "critical_load_asset_id"],
			["aux_ac", "aux_ac_asset_id"],
		]) {
			const id = selected[field];
			if (id)
				assets.set(id, {
					id,
					project_id: run.project_id,
					content_sha256: pins[role + ".raw"],
					metadata_sha256: pins[role + ".metadata"],
					media_type: "text/csv",
					purpose: "csv_profile_v1",
					metadata: { provenance: { label: "Frozen " + role } },
				});
		}
		if (!joint)
			assets.set(selected.battery_parameters_asset_id, {
				id: selected.battery_parameters_asset_id,
				project_id: run.project_id,
				content_sha256: pins["battery.raw"],
				metadata_sha256: pins["battery.metadata"],
				media_type: "application/json",
				purpose: "battery_parameters_v1",
				metadata: run.result.battery_parameter_provenance,
			});
		const requests = [];
		const client = {
			isCurrentScope: () => true,
			async query(path, command) {
				requests.push({ path, command });
				if (path === "runs/inputs")
					return {
						schema_version: 1,
						project_id: run.project_id,
						run_id: run.id,
						manifest_sha256: run.manifest_sha256,
						inputs,
					};
				if (path === "assets/read") return assets.get(command.asset_id);
				throw new Error("unexpected source read " + path);
			},
		};
		await act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: queryClient },
					React.createElement(RunBasis, {
						run,
						client,
						session: { query_scope: scope },
						locale: "en-GB",
						recheck() {},
					}),
				),
			),
		);
		await act(async () => document.querySelector("summary").click());
		await until(() => document.querySelector(".sc-run-source-list"));
		assert.equal(requests[0].path, "runs/inputs");
		assert.deepEqual(requests[0].command, {
			schema_version: 1,
			project_id: run.project_id,
			run_id: run.id,
		});
		assert.equal(
			requests.some((row) => row.path === "projects/read"),
			false,
		);
		assert.match(document.body.textContent, /Frozen gross_load/);
		if (kind === "pv_only") {
			assert.match(document.body.textContent, /Frozen pv_available_ac/);
			assert.match(document.body.textContent, /No battery parameters are used/);
			assert.doesNotMatch(
				document.body.textContent,
				/Each storage unit uses|Connected battery port|fixed internal energy window/,
			);
			assert.deepEqual(
				requests
					.filter((row) => row.path === "assets/read")
					.map((row) => row.command.asset_id)
					.sort(),
				[
					inputs.energy_plant.gross_load_asset_id,
					inputs.energy_plant.pv_available_asset_id,
					inputs.energy_plant.aux_ac_asset_id,
				].sort(),
			);
		}
	});
}

const scope = "a".repeat(64);
const json = (value, status = 200) =>
	new Response(JSON.stringify(value), {
		status,
		headers: { "Content-Type": "application/json" },
	});
const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) => node.textContent === text && !node.closest("[hidden]"),
	);
async function click(text) {
	const node = button(text);
	assert.ok(node, text);
	assert.equal(node.disabled, false, text);
	await act(async () => node.click());
}

async function energyRig(
	t,
	{
		joint = false,
		dc = false,
		delay = false,
		delayRange = false,
		invalidDates = false,
		hardware = false,
		pvOnly = false,
		newPlant = false,
		scopeSwitch = false,
	} = {},
) {
	const dom = setupDom();
	const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const plant = plantFixture.project.inputs.equipment_plant;
	const baseInputs = joint
		? {
				equipment_plant_setup: {
					schema_version: 1,
					requirements: {
						...plant.requirements,
						...(newPlant || scopeSwitch ? { pv_dc_kw: 10 } : {}),
					},
					units: plant.units.map((unit) => ({
						id: unit.id,
						name: unit.name,
						inputs: {
							equipment_setup: {
								...equipmentDraft({ equipment_selection: unit.selection }),
								...(newPlant || scopeSwitch
									? {
											pv_dc_kw: 5,
											battery_product_id: null,
											modules_per_stack: null,
											parallel_stacks: null,
										}
									: {}),
							},
						},
					})),
					parallel_groups: [],
				},
				energy_plant_setup: {
					...plantEnergyDraft({ equipment_plant: plant }, plant),
					coupling: dc ? "plant_shared_dc" : "plant_ac",
				},
				profile_selections: selections,
			}
		: {
				energy_scenario: {
					...scenario,
					coupling: dc ? "shared_dc" : "independent_ac",
				},
				equipment_setup: {
					...equipmentDraft({}),
					...(hardware ? { inverter_product_id: 101 } : {}),
				},
				profile_selections: selections,
			};
	if (newPlant) delete baseInputs.energy_plant_setup;
	const project = {
		id: actualRun.project_id,
		title: "Current energy inputs",
		revision: 1,
		input_sha256: "b".repeat(64),
		inputs: authoredCalculationInputs({
			...baseInputs,
			...(scopeSwitch
				? {
						brief: { system_scope: "new_pv_storage" },
						geometric_roof_ac_selection: {
							schema_version: 1,
							asset_id: selections.selected.pv_available_ac,
						},
						profile_selections: {
							...selections,
							selected: {
								...selections.selected,
								pv_reference: "f".repeat(32),
							},
						},
					}
				: pvOnly
					? { brief: { system_scope: "pv_only" } }
					: {}),
		}),
	};
	const session = {
		schema_version: 1,
		kind: "guest",
		cookie_confirmed: true,
		expires_at: 2000000000,
		query_scope: scope,
		nonce: "abcdefghij",
		claim_pending: false,
		runtime: {
			schema_version: 1,
			runtime_sha256: actualRun.manifest.context.code_sha256,
			models: {
				...actualRun.manifest.context.models,
				plant_replay: "plant_ac_energy_replay_v1",
				plant_dc_replay: "plant_shared_dc_energy_replay_v1",
				...(invalidDates ? { report: "planning_report_v1" } : {}),
			},
			limits: {
				max_body_bytes: 16777216,
				max_csv_bytes: 8388608,
				max_page_size: 100,
				max_json_depth: 32,
			},
		},
	};
	const gate = deferred(),
		requests = [];
	let run, draftApi, durable;
	const store = {
		async read() {
			return null;
		},
		async candidates() {
			return [];
		},
		async write(_scope, draft) {
			durable = structuredClone(draft);
		},
	};
	const client = new PlannerClient({
		baseUrl: "https://fixture.invalid/api/",
		nonceUrl: "https://fixture.invalid/nonce",
		origin: "https://fixture.invalid",
		fetch: async (url, request) => {
			const path = new URL(url).pathname;
			if (path === "/nonce") return new Response("abcdefghij");
			if (path.endsWith("/bootstrap")) return json(session);
			const operation = path.split("/rpc/")[1],
				command = JSON.parse(request.body);
			requests.push({ operation, command, body: request.body });
			if (operation === "assets/read" || operation === "profiles/preview") {
				const role = Object.keys(selections.selected).find(
					(role) => selections.selected[role] === command.asset_id,
				);
				assert.ok(role, "selected profile asset");
				const asset = {
					id: command.asset_id,
					project_id: project.id,
					content_sha256: actualRun.manifest.context.assets[role + ".raw"],
					metadata_sha256:
						actualRun.manifest.context.assets[role + ".metadata"],
					media_type: "text/csv",
					purpose: "csv_profile_v1",
					metadata: {},
				};
				if (operation === "assets/read") return json(asset);
				if (delayRange) await gate.promise;
				return json({
					schema_version: 1,
					evaluation_scope: "profile_interpretation",
					project_id: project.id,
					asset_id: asset.id,
					content_sha256: asset.content_sha256,
					metadata_sha256: asset.metadata_sha256,
					measurement: role,
					source: { origin: "synthetic" },
					transformations: [],
					summary: {
						start_utc: "2024-03-30T23:00:00Z",
						end_utc: "2024-03-31T01:00:00Z",
						interval_count: 2,
						covered_seconds: 7200,
						span_seconds: 7200,
						gap_seconds: 0,
						gap_count: 0,
						energy_kwh: 2,
						min_interval_mean_kw: 1,
						max_interval_mean_kw: 1,
						native_max_interval_seconds: 3600,
						effective_max_interval_seconds: 3600,
						reconstructed_means: false,
					},
					rows: [],
					first_gaps: [],
					gaps_truncated: false,
					next_offset: null,
				});
			}
			if (operation === "products/current")
				return json({
					schema_version: 1,
					provider: "woocommerce",
					products: [
						{
							id: 101,
							canonical_product_id: 101,
							product_revision: "6".repeat(64),
							model: "Declared converter",
							brand: "Fixture",
							device_class: "hybrid_inverter",
							figures: {},
						},
					],
					dc_battery_ports: { 101: ["authored-port"] },
					cable_references: [],
					figure_projection_version: 2,
					compatibility_origin: "woocommerce",
				});
			if (operation === "projects/runs") return json({ items: [], next: null });
			if (operation === "runs/read") return json(run);
			if (operation !== "runs/calculate")
				return json({ error: { code: "not_found" } });
			if (invalidDates) {
				const prefix = joint ? "energy_plant_setup" : "energy_scenario";
				return json(
					{
						error: {
							code: "invalid_input",
							fields: [
								prefix + ".schedule[0].start_utc",
								prefix + ".schedule[0].end_utc",
							],
						},
					},
					422,
				);
			}
			const solarScope = command.inputs.brief?.system_scope === "pv_only";
			const kind = joint
				? dc && !solarScope
					? "plant_shared_dc_energy_replay_v1"
					: "plant_ac_energy_replay_v1"
				: dc && !solarScope
					? "shared_dc_energy_replay_v1"
					: "single_ac_energy_replay_v1";
			run = {
				...actualRun,
				revision: 2,
				state: "queued",
				result: null,
				result_sha256: null,
				manifest: {
					...actualRun.manifest,
					revision: 2,
					context: {
						...actualRun.manifest.context,
						parameters: { kind },
						models: { replay: kind },
					},
				},
			};
			if (delay) await gate.promise;
			return json({
				schema_version: 1,
				project: {
					...project,
					revision: 2,
					input_sha256: run.manifest.input_sha256,
					inputs: command.inputs,
				},
				run,
			});
		},
	});
	await client.bootstrap();
	function Harness() {
		draftApi = useProjectDraft(project, session, client, store, () => {});
		if (!draftApi.draft) return null;
		const { draft, update } = draftApi;
		return React.createElement(
			React.Fragment,
			null,
			scopeSwitch
				? React.createElement(
						"select",
						{
							"aria-label": "System scope",
							value: draft.history.current.brief.system_scope,
							onChange: (event) =>
								update((current) =>
									editDraft(current, {
										...current.history.current,
										brief: {
											...current.history.current.brief,
											system_scope: event.target.value,
										},
									}),
								),
						},
						React.createElement(
							"option",
							{ value: "new_pv_storage" },
							"PV and storage",
						),
						React.createElement("option", { value: "pv_only" }, "PV only"),
					)
				: null,
			React.createElement(
				"label",
				null,
				"Project note",
				React.createElement("textarea", {
					"aria-label": "Project note",
					value: draft.history.current.note ?? "",
					onChange: (event) =>
						update((current) =>
							editDraft(current, {
								...current.history.current,
								note: event.target.value,
							}),
						),
				}),
			),
			React.createElement(
				"button",
				{
					onClick: () => update(undoDraft),
					disabled: !draft.history.past.length,
				},
				"Undo",
			),
			React.createElement(
				"button",
				{
					onClick: () => update(redoDraft),
					disabled: !draft.history.future.length,
				},
				"Redo",
			),
			React.createElement(EnergyWorkspace, {
				draft,
				client,
				session,
				locale: "en-GB",
				blocked: false,
				active: true,
				acknowledgeProject: draftApi.acknowledgeProject,
				flush: draftApi.flush,
				recheck() {},
				onValidity() {},
				openProfiles() {},
				edit(operation) {
					update((current) =>
						editDraft(current, operation(current.history.current)),
					);
					return true;
				},
			}),
		);
	}
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: queryClient },
				React.createElement(Harness),
			),
		),
	);
	t.after(async () => {
		gate.resolve();
		await dom.dispose(root);
		queryClient.clear();
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else delete globalThis.indexedDB;
	});
	await until(
		() =>
			button("Calculate energy flows") &&
			!button("Calculate energy flows").disabled,
	);
	return {
		requests,
		gate,
		get draft() {
			return draftApi.draft;
		},
		get durable() {
			return durable;
		},
	};
}

const scenarioField = (label) =>
	[...document.querySelectorAll("label")]
		.find(
			(node) =>
				!node.closest("[hidden]") &&
				node.querySelector("span")?.childNodes[0]?.textContent.trim() === label,
		)
		?.querySelector("input,select");
async function chooseScenario(label, value) {
	await act(async () => {
		const select = scenarioField(label);
		assert.ok(select, label);
		select.value = value;
		select.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
}

for (const joint of [false, true]) {
	test(`${joint ? "plant" : "single"} scenario chapters show one editor and preserve edits across navigation and undo`, async (t) => {
		const rig = await energyRig(t, { joint });
		assert.ok(
			!scenarioField("Start with UTC or offset"),
			"Operating periods belong to the Operation chapter",
		);
		assert.equal(document.querySelectorAll(".sc-scenario-steps").length, 1);
		assert.equal(
			document.querySelector(".sc-scenario-steps").closest("details"),
			null,
		);
		await click("03Operation");
		const periods = [
			...document.querySelectorAll('input[name$="start_utc"]'),
		].filter((node) => !node.closest("[hidden]"));
		assert.equal(periods.length, 1);
		assert.equal(scenarioField("System connection"), undefined);
		await enter(
			scenarioField("Start with UTC or offset"),
			"2024-03-30T22:00:00Z",
		);
		await click("02Starting state");
		assert.ok(
			!scenarioField("Start with UTC or offset"),
			"Operating periods belong to the Operation chapter",
		);
		await click("03Operation");
		assert.equal(
			scenarioField("Start with UTC or offset").value,
			"2024-03-30T22:00:00Z",
		);
		await click("Undo");
		assert.equal(
			scenarioField("Start with UTC or offset").value,
			rig.draft.baseline.inputs[
				joint ? "energy_plant_setup" : "energy_scenario"
			].schedule[0].start_utc,
		);
	});

	test(`${joint ? "plant" : "single"} shared profile range preserves reserve and grid cap edits made while previews are pending`, async (t) => {
		const rig = await energyRig(t, { joint, delayRange: true });
		const key = joint ? "energy_plant_setup" : "energy_scenario";
		await click("03Operation");
		await enter(scenarioField("Start with UTC or offset"), "");
		await enter(scenarioField("End with UTC or offset"), "");
		assert.equal(scenarioField("Start with UTC or offset").value, "");
		await click("Use the shared profile range");
		await until(() =>
			rig.requests.some((row) => row.operation === "profiles/preview"),
		);
		await chooseScenario("Grid import limit", "limited");
		await enter(scenarioField("Import cap"), "3");
		await chooseScenario("Grid export limit", "limited");
		await enter(scenarioField("Export cap"), "2");
		if (joint) await click("02Starting state");
		await enter(scenarioField("Reserved stored energy"), "1");
		if (joint) await click("03Operation");
		await act(async () => rig.gate.resolve());
		await until(() => button("Use the shared profile range"));
		const setup = rig.draft.history.current[key];
		assert.equal(setup.schedule[0].start_utc, "2024-03-30T23:00:00Z");
		assert.equal(setup.schedule[0].end_utc, "2024-03-31T01:00:00Z");
		assert.equal(
			joint ? setup.units[0].reserve_kwh : setup.schedule[0].reserve_kwh,
			1,
		);
		assert.equal(setup.schedule[0].import_cap_kw, 3);
		assert.equal(setup.schedule[0].export_cap_kw, 2);
		await click("Calculate energy flows");
		await until(() => rig.draft.baseline.revision === 2);
		assert.deepEqual(
			rig.requests.find((row) => row.operation === "runs/calculate").command
				.inputs[key],
			authoredCalculationInputs({ [key]: setup })[key],
		);
	});
}

test("single operation keeps goal shortcuts and multiple periods in one editor", async (t) => {
	const rig = await energyRig(t);
	await click("03Operation");
	assert.equal(document.querySelectorAll('input[name$="start_utc"]').length, 1);
	await chooseScenario("Operating goal", "backup");
	assert.equal(
		rig.draft.history.current.energy_scenario.schedule[0].mode,
		"outage",
	);
	await click("Add operating period");
	assert.equal(document.querySelectorAll('input[name$="start_utc"]').length, 2);
	assert.ok(!scenarioField("Operating goal"));
	assert.ok(scenarioField("Operating strategy"));
	await click("01Storage");
	assert.ok(!scenarioField("Start with UTC or offset"));
	await click("03Operation");
	assert.equal(document.querySelectorAll('input[name$="start_utc"]').length, 2);
	assert.equal(
		rig.draft.history.current.energy_scenario.schedule[0].mode,
		"outage",
	);
});

test("an untouched new plant can apply its first shared profile range", async (t) => {
	const rig = await energyRig(t, {
		joint: true,
		pvOnly: true,
		newPlant: true,
		delayRange: true,
	});
	assert.equal(rig.draft.history.current.energy_plant_setup, undefined);
	await click("02Operation");
	await click("Use the shared profile range");
	await until(() =>
		rig.requests.some((row) => row.operation === "profiles/preview"),
	);
	await act(async () => rig.gate.resolve());
	await until(() => button("Use the shared profile range"));
	assert.equal(
		rig.draft.history.current.energy_plant_setup?.schedule[0].start_utc,
		"2024-03-30T23:00:00Z",
	);
	assert.equal(
		rig.draft.history.current.energy_plant_setup?.schedule[0].end_utc,
		"2024-03-31T01:00:00Z",
	);
});

for (const joint of [false, true]) {
	for (const boundary of ["start_utc", "end_utc"]) {
		test(`${joint ? "plant" : "single"} pending shared profile range blocks calculation and retains a user-edited ${boundary}`, async (t) => {
			const rig = await energyRig(t, { joint, delayRange: true });
			const key = joint ? "energy_plant_setup" : "energy_scenario";
			await click("03Operation");
			await enter(scenarioField("Start with UTC or offset"), "");
			await enter(scenarioField("End with UTC or offset"), "");
			await click("Use the shared profile range");
			await until(() =>
				rig.requests.some((row) => row.operation === "profiles/preview"),
			);
			assert.equal(button("Calculate energy flows").disabled, true);
			await act(async () => button("Calculate energy flows").click());
			assert.equal(
				rig.requests.some((row) => row.operation === "runs/calculate"),
				false,
			);
			const value = "2024-03-31T00:00:00Z";
			await enter(
				scenarioField(
					boundary === "start_utc"
						? "Start with UTC or offset"
						: "End with UTC or offset",
				),
				value,
			);
			await act(async () => rig.gate.resolve());
			await until(() => button("Use the shared profile range"));
			assert.equal(rig.draft.history.current[key].schedule[0][boundary], value);
			assert.equal(
				rig.draft.history.current[key].schedule[0][
					boundary === "start_utc" ? "end_utc" : "start_utc"
				],
				"",
			);
			assert.equal(
				rig.requests.some((row) => row.operation === "runs/calculate"),
				false,
			);
		});
	}
}

for (const joint of [false, true]) {
	for (const pvOnly of [false, true]) {
		test(`${joint ? "plant" : "single"} ${pvOnly ? "PV-only" : "storage"} rejected dates reveal and highlight the authored timestamp fields`, async (t) => {
			const rig = await energyRig(t, { joint, pvOnly, invalidDates: true });
			await click("Calculate energy flows");
			await until(() =>
				document.querySelector('input[aria-invalid="true"][name$="start_utc"]'),
			);
			const start = document.querySelector(
				'input[aria-invalid="true"][name$="start_utc"]',
			);
			const end = document.querySelector(
				'input[aria-invalid="true"][name$="end_utc"]',
			);
			assert.ok(end);
			await until(() => document.activeElement === start);
			assert.equal(start.closest("[hidden]"), null);
			const details = start.closest("details");
			if (details) assert.equal(details.open, true);
			assert.match(
				document.getElementById(start.getAttribute("aria-describedby"))
					.textContent,
				/date and time with Z or a UTC offset.*end must be after the start/,
			);
			assert.doesNotMatch(
				document.body.textContent,
				/energy_scenario\.schedule|energy_plant_setup\.schedule/,
			);
			assert.equal(rig.draft.baseline.revision, 1);
			assert.equal(document.querySelector(".sc-run-result"), null);
			await click("Planning report");
			assert.equal(
				button("Planning report").getAttribute("aria-pressed"),
				"true",
			);
			await click("Scenario settings");
			await enter(start, "2024-03-30T23:30:00Z");
			await until(
				() =>
					!document.querySelector(
						'input[aria-invalid="true"][name$="start_utc"]',
					),
			);
		});
	}
}

test("a new PV-only plant with positive PV starts at the AC source and its first ordinary schedule edit stays AC", async (t) => {
	const rig = await energyRig(t, { joint: true, pvOnly: true, newPlant: true });
	assert.equal(
		rig.draft.history.current.energy_plant_setup,
		undefined,
		"no AC coupling was seeded into this project",
	);
	const sources = document.querySelector(".sc-scenario-sources");
	assert.match(sources.textContent, /Available PV output · AC/);
	assert.doesNotMatch(sources.textContent, /Roof PV source/);
	const field = (label) =>
		[...document.querySelectorAll("label")]
			.find(
				(node) =>
					!node.closest("[hidden]") &&
					node.querySelector("span")?.textContent === label,
			)
			?.querySelector("input,select");
	await click("02Operation");
	await enter(field("Start with UTC or offset"), "2024-03-30T23:00:00Z");
	assert.equal(
		rig.draft.history.current.energy_plant_setup.coupling,
		"plant_ac",
	);
	await enter(field("End with UTC or offset"), "2024-03-31T01:00:00Z");
	for (const [label, value] of [
		["Grid condition", "connected"],
		["PV available in this period", "true"],
		["Grid import limit", "unlimited"],
		["Grid export limit", "unlimited"],
	])
		await act(async () => {
			field(label).value = value;
			field(label).dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	await click("Calculate energy flows");
	await until(() => rig.draft.baseline.revision === 2);
	const command = rig.requests.find(
		(row) => row.operation === "runs/calculate",
	).command;
	assert.equal(
		command.inputs.equipment_plant_setup.units[0].inputs.equipment_setup
			.pv_dc_kw,
		5,
	);
	assert.equal(command.inputs.energy_plant_setup.coupling, "plant_ac");
	assert.equal(
		command.inputs.profile_selections.selected.pv_available_ac,
		selections.selected.pv_available_ac,
	);
});

for (const joint of [false, true])
	for (const editDates of [false, true]) {
		test(`${joint ? "plant" : "single"} retained shared DC switches to PV-only AC source interpretation ${editDates ? "with a date edit" : "without changing declarations"}`, async (t) => {
			const rig = await energyRig(t, { joint, dc: true, scopeSwitch: true });
			const key = joint ? "energy_plant_setup" : "energy_scenario";
			const original = structuredClone(rig.draft.history.current);
			const select = document.querySelector('[aria-label="System scope"]');
			await act(async () => {
				select.value = "pv_only";
				select.dispatchEvent(new window.Event("change", { bubbles: true }));
			});
			const sources = document.querySelector(".sc-scenario-sources");
			assert.match(sources.textContent, /Available PV output · AC/);
			assert.doesNotMatch(sources.textContent, /Roof PV source/);
			if (editDates) {
				await click("02Operation");
				const start = [...document.querySelectorAll("label")]
					.find(
						(node) =>
							!node.closest("[hidden]") &&
							node.querySelector("span")?.textContent ===
								"Start with UTC or offset",
					)
					.querySelector("input");
				await enter(start, "2024-03-30T22:00:00Z");
			}
			assert.equal(
				rig.draft.history.current[key].coupling,
				original[key].coupling,
			);
			assert.deepEqual(
				rig.draft.history.current.profile_selections,
				original.profile_selections,
			);
			assert.deepEqual(
				rig.draft.history.current.geometric_roof_ac_selection,
				original.geometric_roof_ac_selection,
			);
			if (!joint)
				assert.deepEqual(
					rig.draft.history.current[key].battery,
					original[key].battery,
				);
			await click("Calculate energy flows");
			await until(() => rig.draft.baseline.revision === 2);
			const command = rig.requests.find(
				(row) => row.operation === "runs/calculate",
			).command;
			assert.equal(command.inputs.brief.system_scope, "pv_only");
			assert.equal(command.inputs[key].coupling, original[key].coupling);
			if (joint)
				assert.deepEqual(command.inputs[key].units, original[key].units);
			assert.deepEqual(
				command.inputs.profile_selections,
				original.profile_selections,
			);
		});
	}

for (const joint of [false, true]) {
	test(`${joint ? "plant" : "single"} PV-only workspace edits solar periods and calculates without storage controls`, async (t) => {
		const rig = await energyRig(t, { joint, pvOnly: true });
		const heading = [...document.querySelectorAll("h3")].find(
			(node) =>
				!node.closest("[hidden]") &&
				node.textContent === "Solar-only energy flows",
		);
		assert.ok(heading);
		const visibleHeadings = [...document.querySelectorAll("h3,summary")]
			.filter((node) => !node.closest("[hidden]"))
			.map((node) => node.textContent);
		assert.equal(visibleHeadings.includes("Storage parameters"), false);
		assert.equal(
			visibleHeadings.includes("Advanced storage and operating settings"),
			false,
		);
		const fieldset = heading.closest("fieldset");
		assert.equal(
			fieldset.textContent.includes("Reserved stored energy"),
			false,
		);
		assert.equal(fieldset.textContent.includes("Grid charging allowed"), false);
		const aux = [...fieldset.querySelectorAll("input")].find((input) =>
			document
				.getElementById(input.getAttribute("aria-labelledby"))
				?.textContent.startsWith("Constant AC auxiliary demand"),
		);
		// The retained fixture has an auxiliary profile; its choice remains owned.
		assert.equal(aux, undefined);
		assert.ok(!scenarioField("Start with UTC or offset"));
		await click("02Operation");
		const period = [...fieldset.querySelectorAll("label")]
			.find(
				(label) =>
					label.querySelector("span")?.textContent ===
					"Start with UTC or offset",
			)
			.querySelector("input");
		await enter(period, "2024-03-30T22:00:00Z");
		await click("Calculate energy flows");
		await until(() => rig.draft.baseline.revision === 2);
		const command = rig.requests.find(
			(row) => row.operation === "runs/calculate",
		).command;
		const declared =
			command.inputs[joint ? "energy_plant_setup" : "energy_scenario"];
		assert.equal(command.inputs.brief.system_scope, "pv_only");
		assert.equal(declared.schedule[0].start_utc, "2024-03-30T22:00:00Z");
		assert.equal(command.inputs.energy_replay, undefined);
		assert.equal(command.inputs.energy_plant, undefined);
	});
}

test("DC editing uses the current authored converter before any prepared selection exists", async (t) => {
	const rig = await energyRig(t, { dc: true, hardware: true });
	const port = () =>
		[...document.querySelectorAll("label")]
			.find(
				(label) =>
					label.querySelector("span")?.textContent === "Connected battery port",
			)
			?.querySelector("select");
	await until(() => port()?.querySelector('option[value="authored-port"]'));
	assert.equal(port().disabled, false);
	await act(async () => {
		port().value = "authored-port";
		port().dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.equal(
		rig.draft.history.current.energy_scenario.dc.battery_port_id,
		"authored-port",
	);
	assert.equal(rig.draft.history.current.equipment_selection, undefined);
});

for (const joint of [false, true])
	for (const dc of [false, true]) {
		test(`${joint ? "plant" : "single"} ${dc ? "DC" : "AC"} calculation submits current declarations without preparation or a save command`, async (t) => {
			const rig = await energyRig(t, { joint, dc });
			assert.equal(button("Prepare scenario settings"), undefined);
			await enter(
				document.querySelector('[aria-label="Project note"]'),
				"Edited before calculation",
			);
			await click("Calculate energy flows");
			await until(() => rig.draft.baseline.revision === 2);
			const mutations = rig.requests.filter((row) =>
				[
					"runs/calculate",
					"battery/scenario",
					"projects/revise",
					"runs/energy",
				].includes(row.operation),
			);
			assert.deepEqual(
				mutations.map((row) => row.operation),
				["runs/calculate"],
			);
			assert.equal(
				mutations[0].command.inputs.note,
				"Edited before calculation",
			);
			assert.equal(mutations[0].command.expected_revision, 1);
			assert.equal(mutations[0].command.input_contract, projectInputContract);
			assert.equal(isDirty(rig.draft), false);
			if (joint) assert.ok(rig.draft.history.current.equipment_plant_setup);
			assert.equal("energy_replay" in rig.draft.history.current, false);
		});
	}

test("a late calculation acknowledgement persists the captured baseline and preserves later edits, undo and redo", async (t) => {
	const rig = await energyRig(t, { delay: true });
	const note = document.querySelector('[aria-label="Project note"]');
	await enter(note, "Submitted");
	await click("Calculate energy flows");
	await until(() =>
		rig.requests.some((row) => row.operation === "runs/calculate"),
	);
	await enter(note, "Edited while calculating");
	await click("Undo");
	await click("Redo");
	rig.gate.resolve();
	await until(
		() =>
			rig.draft.baseline.revision === 2 && rig.durable?.baseline.revision === 2,
	);
	assert.equal(rig.draft.baseline.inputs.note, "Submitted");
	assert.equal(rig.draft.history.current.note, "Edited while calculating");
	assert.equal(isDirty(rig.draft), true);
	await click("Undo");
	assert.equal(rig.draft.history.current.note, "Submitted");
	assert.equal(isDirty(rig.draft), false);
	await click("Redo");
	assert.equal(rig.draft.history.current.note, "Edited while calculating");
});

test("a missing wiring assessment directs the customer to equipment and stale report input to recalculation", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(EnergyError, {
				error: new ApiError(422, "report_wiring_check_required"),
				openEquipment() {},
			}),
		),
	);
	assert.match(dom.element.textContent, /saved PV strings/);
	assert.equal(dom.element.querySelector("button").textContent, "Equipment");
	let opened = false;
	await act(async () =>
		root.render(
			React.createElement(EnergyError, {
				error: new ApiError(422, "report_inputs_changed"),
				openScenario() {
					opened = true;
				},
			}),
		),
	);
	assert.match(
		dom.element.textContent,
		/does not match the saved project inputs/,
	);
	await click("Recalculate energy");
	assert.equal(opened, true);
});

test("choosing an operating goal preserves unknown assumptions and manually declared physical values", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	let next;
	const render = async (value) =>
		act(async () =>
			root.render(
				React.createElement(SimpleEnergySetup, {
					value,
					storageOnly: false,
					hasAuxiliaryProfile: false,
					hasEquipment: true,
					chooseEquipment() {},
					locale: "en-GB",
					disabled: false,
					onChange(value) {
						next = value;
					},
					onValidity() {},
					useProfileRange() {},
					rangeBusy: false,
				}),
			),
		);
	const choose = async () =>
		act(async () => {
			const goal = [...document.querySelectorAll("label")]
				.find((label) => label.textContent.startsWith("Operating goal"))
				.querySelector("select");
			goal.value = "peak";
			goal.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	const unknown = emptyScenario();
	await render(unknown);
	await choose();
	assert.deepEqual(next.battery, unknown.battery);
	assert.deepEqual(next.initial_inventory, unknown.initial_inventory);
	assert.equal(next.source_note, "");
	assert.equal(next.aux_ac_kw ?? null, null);
	assert.equal(next.terminal_policy, null);
	assert.equal(next.schedule[0].reserve_kwh, null);
	assert.equal(next.schedule[0].export_policy, null);
	assert.equal(next.schedule[0].export_cap_kw, null);
	assert.equal(next.schedule[0].allow_grid_charge, null);
	assert.equal(next.schedule[0].pv_enabled, null);
	const manual = {
		...scenario,
		source_note: "My measured losses",
		initial_inventory: {
			pv_kwh: 1,
			grid_kwh: 2,
			initial_unknown_kwh: 3,
			source_note: "Read from commissioning record",
		},
		aux_ac_kw: 0.12,
		battery: {
			...scenario.battery,
			internal_aux_kw: 0.03,
			standing_loss_rate_per_hour: 0.001,
		},
	};
	await render(manual);
	await choose();
	assert.deepEqual(next.battery, manual.battery);
	assert.deepEqual(next.initial_inventory, manual.initial_inventory);
	assert.equal(next.source_note, manual.source_note);
	assert.equal(next.aux_ac_kw, 0.12);
	assert.equal(next.terminal_policy, manual.terminal_policy);
	assert.equal(next.schedule[0].reserve_kwh, manual.schedule[0].reserve_kwh);
	assert.equal(
		next.schedule[0].export_policy,
		manual.schedule[0].export_policy,
	);
	assert.equal(
		next.schedule[0].export_cap_kw,
		manual.schedule[0].export_cap_kw,
	);
});

test("changing the simple operating goal preserves an auxiliary profile and its declared PV availability", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { SimpleEnergySetup } =
		await import("../src/components/energy/SimpleEnergySetup.tsx");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	let next;
	await act(async () =>
		root.render(
			React.createElement(SimpleEnergySetup, {
				value: scenario,
				storageOnly: false,
				hasAuxiliaryProfile: true,
				locale: "en-GB",
				disabled: false,
				onChange(value) {
					next = value;
				},
				onValidity() {},
				useProfileRange() {},
				rangeBusy: false,
			}),
		),
	);
	await act(async () => {
		const goal = [...document.querySelectorAll("label")]
			.find((label) => label.textContent.startsWith("Operating goal"))
			.querySelector("select");
		goal.value = "backup";
		goal.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.equal(next.aux_ac_kw, scenario.aux_ac_kw);
	assert.equal(next.schedule[0].pv_enabled, scenario.schedule[0].pv_enabled);
	assert.equal(next.schedule[0].allow_grid_charge, false);
	assert.equal(next.schedule[0].mode, "outage");
});
