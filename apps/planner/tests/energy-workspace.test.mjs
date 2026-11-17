import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IDBFactory } from "fake-indexeddb";
import { setupDom, until, enter, deferred } from "./dom-fixture.mjs";
import { EnergyWorkspace } from "../src/components/energy/EnergyWorkspace.tsx";
import {
	EnergyError,
	energyErrorText,
} from "../src/components/energy/EnergyError.tsx";
import {
	beginDraft,
	editDraft,
	undoDraft,
	prepareSave,
	acknowledgeSave,
} from "../src/domain/draft.ts";
import { ApiError } from "../src/data/protocol.ts";
import scenario from "./fixtures/energy-scenario.json" with { type: "json" };
import selections from "./fixtures/energy-selections.json" with { type: "json" };
import actualRun from "./fixtures/energy-run.json" with { type: "json" };
import plantFixture from "./fixtures/plant-energy-run.json" with { type: "json" };
import { plantEnergyDraft } from "../src/domain/plantEnergy.ts";
import { DC_LOSS_FIELDS } from "../src/domain/dcEnergy.ts";

function preparedPlantInputs() {
	const { equipment_plant: plant, energy_plant: original } =
		plantFixture.project.inputs;
	const empty = plantEnergyDraft({ equipment_plant: plant }, plant);
	const setup = {
		...empty,
		schedule: scenario.schedule,
		units: empty.units.map((unit) => {
			const saved = original.units.find((u) => u.unit_id === unit.unit_id);
			const source = plantFixture.run.result.parameter_sources.units.find(
				(u) => u.unit_id === unit.unit_id,
			);
			const parameters =
				plantFixture.run.result.parameter_sources.pool[source.parameter_sha256]
					.loss_scenario;
			return {
				...unit,
				reserve_kwh: 0,
				pv_dc_input_unused: true,
				allow_ac_charge: false,
				settings: {
					...scenario,
					dc: {
						...unit.settings.dc,
						pv_converter_id: "",
						aux_dc_kw: 0,
						source_note: parameters.source_note,
						battery_port_id: parameters.battery_port_id,
						battery_temperature_c: parameters.battery_temperature_c,
						losses: Object.fromEntries(
							DC_LOSS_FIELDS.map((k) => [k, parameters[k]]),
						),
					},
					battery_binding: {
						asset_id: saved.battery_parameters_asset_id,
						parameters,
						source_note: parameters.source_note,
						equipment_selection: plant.units.find((u) => u.id === unit.unit_id)
							.selection,
					},
				},
			};
		}),
	};
	return {
		equipment_plant: plant,
		energy_plant_setup: setup,
		profile_selections: selections,
	};
}

async function energyRig(t, inputs) {
	const dom = setupDom();
	const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	window.history.replaceState(
		null,
		"",
		`?project=${actualRun.project_id}#lp-calculations`,
	);
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	t.after(async () => {
		await dom.dispose(root);
		queryClient.clear();
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else delete globalThis.indexedDB;
	});
	let current = beginDraft({
		id: actualRun.project_id,
		title: "Energy transition fixture",
		revision: 1,
		input_sha256: "b".repeat(64),
		inputs,
	});
	const client = {
		isCurrentScope: () => true,
		async query(path) {
			if (path === "projects/runs") return { items: [], next: null };
			throw new ApiError(404, "not_found");
		},
		async send(path, serialized) {
			assert.equal(path, "battery/scenario");
			const body = JSON.parse(serialized);
			return {
				id: "c".repeat(32),
				project_id: actualRun.project_id,
				content_sha256: "d".repeat(64),
				metadata_sha256: "e".repeat(64),
				media_type: "application/json",
				purpose: "battery_parameters_v1",
				metadata: {
					retention: "permanent",
					provenance: {
						basis: "user_explicit_scenario_not_equipment_release",
						label: body.source_note,
					},
					derived_from_revision: body.expected_revision,
					...(body.equipment_unit_id
						? { equipment_unit_id: body.equipment_unit_id }
						: {}),
					dependencies: {
						dc_prepared_parameters: "f".repeat(64),
						dc_woo_inputs: "a".repeat(64),
					},
				},
			};
		},
	};
	function Harness() {
		const [draft, setDraft] = useState(current);
		return React.createElement(
			React.Fragment,
			null,
			React.createElement(
				"button",
				{
					onClick() {
						current = beginDraft({
							...current.baseline,
							revision: current.baseline.revision + 1,
							inputs: current.history.current,
						});
						setDraft(current);
					},
				},
				"Confirm saved revision",
			),
			React.createElement(EnergyWorkspace, {
				draft,
				client,
				locale: "en-GB",
				blocked: false,
				active: true,
				session: {
					query_scope: "a".repeat(64),
					runtime: {
						models: {
							...actualRun.manifest.context.models,
							plant_replay: "plant_ac_energy_replay_v1",
							plant_dc_replay: "plant_shared_dc_energy_replay_v1",
						},
						limits: {
							max_json_depth: 32,
							max_body_bytes: 16777216,
							max_page_size: 100,
						},
					},
				},
				recheck() {},
				onValidity() {},
				openProfiles() {},
				edit(operation) {
					current = editDraft(current, operation(current.history.current));
					setDraft(current);
					return true;
				},
				async flush() {
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
	await until(
		() =>
			button("Prepare scenario settings") &&
			!button("Prepare scenario settings").disabled,
	);
	return {
		get inputs() {
			return current.history.current;
		},
	};
}

async function choose(label, value) {
	await act(async () => {
		const field = control(label);
		assert.ok(field, label);
		field.value = value;
		field.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
}

for (const joint of [false, true]) {
	test(`switching ${joint ? "plant" : "single"} peak shaving to shared DC can prepare without hidden AC choices`, async (t) => {
		const inputs = preparedPlantInputs();
		if (joint) {
			inputs.energy_plant_setup = {
				...inputs.energy_plant_setup,
				controller: "proportional_peak_shaving_v1",
				aux_ac_kw: 0,
			};
		} else {
			inputs.equipment_selection = inputs.equipment_plant.units[0].selection;
			inputs.energy_scenario = {
				...scenario,
				dc: {
					...inputs.energy_plant_setup.units[0].settings.dc,
					pv_converter_id: "roof-group",
				},
			};
			delete inputs.equipment_plant;
			delete inputs.energy_plant_setup;
		}
		const rig = await energyRig(t, inputs);
		if (!joint) {
			await choose("Operating goal", "peak");
			await act(async () => enter(control("Grid import cap"), "2"));
		}
		await choose(
			joint ? "PV connection for this plant" : "System connection",
			joint ? "plant_shared_dc" : "shared_dc",
		);
		await click("Confirm saved revision");
		await click("Prepare scenario settings");
		await until(() => rig.inputs[joint ? "energy_plant" : "energy_replay"]);
		const replay = rig.inputs[joint ? "energy_plant" : "energy_replay"];
		assert.ok(replay, document.querySelector('[role="alert"]')?.textContent);
		assert.equal(replay.coupling, joint ? "plant_shared_dc" : "shared_dc");
		assert.equal(replay.aux_ac_asset_id, selections.selected.aux_ac);
		assert.equal(replay.aux_ac_kw, undefined);
		assert.equal(
			replay.controller,
			joint
				? "local_dc_then_proportional_ac_self_consumption_v1"
				: "self_consumption_with_reserve_v1",
		);
	});
}

for (const joint of [false, true]) {
	test(`storage-only ${joint ? "plant" : "single"} preparation rejects PV-origin starting inventory`, async (t) => {
		const inputs = joint
			? preparedPlantInputs()
			: { energy_scenario: structuredClone(scenario) };
		inputs.brief = { system_scope: "storage_only" };
		inputs.profile_selections = {
			schema_version: 1,
			selected: {
				gross_load: selections.selected.gross_load,
				aux_ac: selections.selected.aux_ac,
			},
		};
		const states = joint
			? inputs.energy_plant_setup.units.map((u) => u.settings)
			: [inputs.energy_scenario];
		for (const state of states)
			state.initial_inventory = { ...state.initial_inventory, pv_kwh: 1 };
		const rig = await energyRig(t, inputs);
		await click("Prepare scenario settings");
		await until(
			() =>
				rig.inputs[joint ? "energy_plant" : "energy_replay"] ||
				document.querySelector('[role="alert"]'),
		);
		assert.equal(
			rig.inputs[joint ? "energy_plant" : "energy_replay"],
			undefined,
		);
		assert.match(
			document.querySelector('[role="alert"]').textContent,
			/PV-origin/,
		);
	});
	test(`PV ${joint ? "plant" : "single"} preparation still needs a source when any period enables generation`, async (t) => {
		const inputs = joint
			? preparedPlantInputs()
			: { energy_scenario: structuredClone(scenario) };
		inputs.profile_selections = {
			schema_version: 1,
			selected: {
				gross_load: selections.selected.gross_load,
				aux_ac: selections.selected.aux_ac,
			},
		};
		const setup = inputs[joint ? "energy_plant_setup" : "energy_scenario"];
		setup.schedule = [
			{
				...scenario.schedule[0],
				pv_enabled: false,
				end_utc: "2024-03-31T00:00:00Z",
			},
			{
				...scenario.schedule[0],
				id: "b".repeat(32),
				start_utc: "2024-03-31T00:00:00Z",
				pv_enabled: true,
			},
		];
		const rig = await energyRig(t, inputs);
		await click("Prepare scenario settings");
		await until(() => document.querySelector('[role="alert"]'));
		assert.match(
			document.querySelector('[role="alert"]').textContent,
			/Select the missing interval sources/,
		);
		assert.equal(
			rig.inputs[joint ? "energy_plant" : "energy_replay"],
			undefined,
		);
	});
	for (const keepPvSelection of [false, true])
		test(`PV ${joint ? "plant" : "single"} backup prepares without generation while retaining PV-origin starting energy (retained PV selection: ${keepPvSelection})`, async (t) => {
			const inputs = joint
				? preparedPlantInputs()
				: { energy_scenario: structuredClone(scenario) };
			inputs.profile_selections = {
				schema_version: 1,
				selected: {
					gross_load: selections.selected.gross_load,
					critical_load: "d".repeat(32),
					aux_ac: selections.selected.aux_ac,
					...(keepPvSelection ? { pv_available_ac: "e".repeat(32) } : {}),
				},
			};
			if (joint) {
				inputs.energy_plant_setup.schedule = scenario.schedule.map((p) => ({
					...p,
					mode: "outage",
					pv_enabled: false,
				}));
				inputs.energy_plant_setup.units = inputs.energy_plant_setup.units.map(
					(u) => ({
						...u,
						settings: {
							...u.settings,
							initial_inventory: { ...u.settings.initial_inventory, pv_kwh: 1 },
						},
					}),
				);
			} else {
				inputs.energy_scenario.initial_inventory.pv_kwh = 1;
			}
			const rig = await energyRig(t, inputs);
			if (!joint) await choose("Operating goal", "backup");
			assert.doesNotMatch(
				document.querySelector(".lp-scenario-sources").textContent,
				/Available PV output/,
			);
			assert.match(
				document.querySelector(".lp-scenario-sources").textContent,
				/Critical load/,
			);
			await click("Prepare scenario settings");
			await until(
				() =>
					rig.inputs[joint ? "energy_plant" : "energy_replay"] ||
					document.querySelector('[role="alert"]'),
			);
			const replay = rig.inputs[joint ? "energy_plant" : "energy_replay"];
			assert.ok(replay, document.querySelector('[role="alert"]')?.textContent);
			assert.equal(replay.pv_available_asset_id, null);
			assert.equal(
				rig.inputs.profile_selections.selected.pv_available_ac,
				keepPvSelection ? "e".repeat(32) : undefined,
			);
			assert.ok(replay.schedule.every((p) => !p.pv_enabled));
			for (const state of joint ? replay.units : [replay])
				assert.equal(state.initial_inventory.pv_kwh, 1);
		});
}

const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) =>
			(node.getAttribute("aria-label") ?? node.textContent) === text &&
			!node.closest("[hidden]"),
	);
const control = (text) =>
	[...document.querySelectorAll("label")]
		.find((label) => label.querySelector("span")?.textContent.startsWith(text))
		?.querySelector("input,textarea,select");
const click = async (text) => {
	const node = button(text);
	assert.ok(node, "missing control " + text);
	assert.equal(node.disabled, false, "disabled " + text);
	await act(async () => node.click());
};

test("a missing saved-wiring assessment has a specific explanation and the native equipment entry", async (t) => {
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
	assert.match(
		dom.element.textContent,
		/select that completed result under Equipment checks/,
	);
	assert.equal(dom.element.querySelector("button").textContent, "Equipment");
	await act(async () =>
		root.render(
			React.createElement(EnergyError, {
				error: new ApiError(422, "report_inputs_changed"),
			}),
		),
	);
	assert.match(
		dom.element.textContent,
		/does not match the saved project inputs/,
	);
	assert.equal(dom.element.querySelector("button"), null);
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
	const recalculate = dom.element.querySelector("button");
	assert.equal(recalculate.textContent, "Recalculate energy");
	await act(async () => recalculate.click());
	assert.equal(opened, true);
});

test("changing the simple operating goal preserves an auxiliary profile and does not assume island PV", async (t) => {
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
		const goal = control("Operating goal");
		goal.value = "backup";
		goal.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.equal(next.aux_ac_kw, null);
	assert.equal(next.schedule[0].pv_enabled, false);
	assert.equal(next.schedule[0].allow_grid_charge, false);
	assert.equal(next.schedule[0].mode, "outage");
});

test("storage-only customers prepare peak shaving without PV or auxiliary CSV", async (t) => {
	const dom = setupDom();
	const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	window.history.replaceState(
		null,
		"",
		`?project=${actualRun.project_id}#lp-calculations`,
	);
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	t.after(async () => {
		await dom.dispose(root);
		queryClient.clear();
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else delete globalThis.indexedDB;
	});
	let current = beginDraft({
		id: actualRun.project_id,
		title: "Storage only",
		revision: 1,
		input_sha256: "b".repeat(64),
		inputs: {
			brief: { system_scope: "storage_only" },
			energy_scenario: { ...scenario, aux_ac_kw: 0 },
			profile_selections: {
				schema_version: 1,
				selected: { gross_load: selections.selected.gross_load },
			},
		},
	});
	const session = {
		query_scope: "a".repeat(64),
		runtime: {
			models: actualRun.manifest.context.models,
			limits: {
				max_json_depth: 32,
				max_body_bytes: 16777216,
				max_page_size: 100,
			},
		},
	};
	const client = {
		isCurrentScope: () => true,
		async query(path) {
			if (path === "projects/runs") return { items: [], next: null };
			throw new ApiError(404, "not_found");
		},
		async send() {
			assert.fail("existing battery source should be reused");
		},
	};
	function Harness() {
		const [draft, setDraft] = useState(current);
		return React.createElement(EnergyWorkspace, {
			draft,
			session,
			client,
			locale: "en-GB",
			blocked: false,
			active: true,
			recheck() {},
			onValidity() {},
			openProfiles() {},
			edit(operation) {
				current = editDraft(current, operation(current.history.current));
				setDraft(current);
				return true;
			},
			async flush() {
				return true;
			},
		});
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
	await until(() => control("Operating goal"));
	await act(async () => {
		const goal = control("Operating goal");
		goal.value = "peak";
		goal.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await act(async () => enter(control("Grid import cap"), "2"));
	const grid = [...document.querySelectorAll('input[type="checkbox"]')].find(
		(input) =>
			input
				.closest("label")
				.textContent.includes("Allow grid charging below this cap"),
	);
	await act(async () => grid.click());
	await until(
		() =>
			button("Prepare scenario settings") &&
			!button("Prepare scenario settings").disabled,
	);
	await click("Prepare scenario settings");
	await until(() => current.history.current.energy_replay);
	const replay = current.history.current.energy_replay;
	assert.equal(replay.pv_available_asset_id, null);
	assert.equal(replay.aux_ac_asset_id, null);
	assert.equal(replay.aux_ac_kw, 0);
	assert.equal(replay.controller, "peak_shaving_with_reserve_v1");
	assert.equal(replay.schedule[0].allow_grid_charge, true);
	assert.equal(replay.schedule[0].pv_enabled, false);
	assert.equal(replay.schedule[0].import_cap_kw, 2);
	assert.match(document.body.textContent, /no PV generation or roof required/);
});

test("actual scenario controls retain raw input, require confirmed save, use one frozen revision, and preserve edits from a late preparation response", async (t) => {
	const dom = setupDom(),
		previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
	window.requestAnimationFrame = (callback) => window.setTimeout(callback, 0);
	window.cancelAnimationFrame = (frame) => window.clearTimeout(frame);
	let lastRevealed;
	window.HTMLElement.prototype.scrollIntoView = function () {
		lastRevealed = this;
	};
	Object.defineProperty(globalThis, "indexedDB", {
		value: new IDBFactory(),
		configurable: true,
	});
	window.history.replaceState(
		null,
		"",
		`?project=${actualRun.project_id}#lp-calculations`,
	);
	const scope = "a".repeat(64),
		project = {
			id: actualRun.project_id,
			title: "Synthetic component workflow",
			revision: 1,
			input_sha256: "b".repeat(64),
			inputs: {
				profile_selections: selections,
				energy_scenario: { ...scenario, battery_binding: null },
			},
		};
	const session = {
		query_scope: scope,
		runtime: {
			models: actualRun.manifest.context.models,
			limits: {
				max_json_depth: 32,
				max_body_bytes: 16777216,
				max_page_size: 100,
			},
		},
	};
	const requests = [],
		queryClient = new QueryClient({
			defaultOptions: { queries: { retry: false } },
		});
	let setter,
		current = beginDraft(project),
		gate = null,
		serverRun = null;
	const assetFor = (body, index) => ({
		id: String(index).repeat(32),
		project_id: project.id,
		content_sha256: "c".repeat(64),
		metadata_sha256: "d".repeat(64),
		media_type: "application/json",
		purpose: "battery_parameters_v1",
		metadata: {
			retention: "permanent",
			provenance: {
				basis: "user_explicit_scenario_not_equipment_release",
				label: body.source_note,
			},
		},
	});
	const client = {
		isCurrentScope: (value) => value === scope,
		async send(path, serialized) {
			const body = JSON.parse(serialized);
			requests.push({ path, body, serialized });
			if (path === "battery/scenario") {
				if (gate) await gate.promise;
				return assetFor(body, requests.filter((x) => x.path === path).length);
			}
			if (path === "runs/energy") {
				// Component transport fixture, not a simulated numerical engine.
				serverRun = {
					...actualRun,
					state: "queued",
					result: null,
					result_sha256: null,
					error: null,
					revision: body.expected_revision,
					manifest: { ...actualRun.manifest, revision: body.expected_revision },
				};
				return serverRun;
			}
			throw new Error("Unexpected mutation " + path);
		},
		async query(path) {
			if (path === "projects/runs")
				return {
					items: serverRun
						? [
								{
									id: serverRun.id,
									project_id: project.id,
									revision: serverRun.revision,
									manifest_sha256: serverRun.manifest_sha256,
									result_sha256: serverRun.result_sha256,
									state: serverRun.state,
									is_current: true,
									created_at: 1700000000,
								},
							]
						: [],
					next: null,
				};
			if (path === "runs/read") return serverRun;
			if (path === "runs/cancel") {
				serverRun = { ...serverRun, state: "cancelled" };
				return serverRun;
			}
			throw new ApiError(404, "not_found");
		},
	};
	function edit(operation) {
		try {
			current = editDraft(current, operation(current.history.current));
			setter(current);
			return true;
		} catch {
			return false;
		}
	}
	function Harness() {
		const [draft, setDraft] = useState(current);
		setter = setDraft;
		return React.createElement(
			React.Fragment,
			null,
			React.createElement(
				"button",
				{
					onClick: () => {
						current = prepareSave(current, crypto.randomUUID(), {
							maxDepth: 32,
							maxBytes: 16777216,
						});
						const intent = current.pending;
						current = acknowledgeSave(current, intent, {
							...project,
							revision: intent.expectedRevision + 1,
							input_sha256: "e".repeat(64),
							inputs: intent.inputs,
						});
						setter(current);
					},
				},
				"Confirm project save fixture",
			),
			React.createElement(EnergyWorkspace, {
				draft,
				edit,
				flush: async () => true,
				session,
				client,
				recheck: () => {},
				locale: "en-US",
				blocked: false,
				active: true,
				onValidity: () => {},
				openProfiles: () => {},
			}),
		);
	}
	const { createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(async () => {
		await dom.dispose(root);
		queryClient.clear();
		if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
		else delete globalThis.indexedDB;
	});
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: queryClient },
				React.createElement(Harness),
			),
		),
	);
	await until(
		() =>
			button("Prepare scenario settings") &&
			!button("Prepare scenario settings").disabled,
	);
	const sourceNote = control("Source or assumption for storage parameters");
	await enter(sourceNote, "");
	button("Prepare scenario settings").focus();
	await click("Prepare scenario settings");
	assert.ok(
		document.activeElement ===
			document.querySelector('.lp-focus-target[tabindex="-1"]'),
		"the error receives focus from the explicit preparation action",
	);
	assert.match(
		document.activeElement.textContent,
		/storage parameters need a source/,
	);
	assert.equal(
		requests.length,
		0,
		"an incomplete scenario creates no parameter asset",
	);
	await act(async () => {
		current = undoDraft(current);
		setter(current);
	});
	assert.equal(
		document.querySelector('[role="alert"]'),
		null,
		"Undo clears validation feedback for the superseded inputs",
	);
	const charge = control("AC charging power");
	await enter(charge, "unfinished");
	assert.equal(charge.getAttribute("aria-invalid"), "true");
	assert.equal(button("03Operation").disabled, true);
	await act(async () =>
		charge.dispatchEvent(
			new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
		),
	);
	await enter(charge, "7");
	await click("02Starting state");
	await click("01Storage");
	assert.equal(
		control("AC charging power"),
		charge,
		"hidden sections retain the same real input node",
	);
	assert.equal(charge.value, "7");
	await click("Prepare scenario settings");
	await until(() => current.history.current.energy_replay !== undefined);
	assert.equal(requests.length, 1);
	assert.equal(requests[0].body.parameters.charge_ac_kw, 7);
	assert.equal(
		button("Calculate saved scenario").disabled,
		true,
		"prepared unsaved inputs cannot start a job",
	);
	await click("Confirm project save fixture");
	await until(() => !button("Calculate saved scenario").disabled);
	await act(async () => {
		button("Calculate saved scenario").click();
		button("Calculate saved scenario")?.click();
	});
	await until(
		() => document.querySelector(".lp-run-result h3")?.textContent === "Queued",
	);
	await until(
		() =>
			document.activeElement ===
			document.querySelector('.lp-run-result h3[tabindex="-1"]'),
	);
	assert.ok(
		document.activeElement ===
			document.querySelector('.lp-run-result h3[tabindex="-1"]'),
		"the newly selected calculation is revealed after the long setup form collapses",
	);
	assert.ok(
		lastRevealed === document.querySelector(".lp-run-heading"),
		"result status and input revision are revealed together",
	);
	assert.equal(requests.filter((x) => x.path === "runs/energy").length, 1);
	assert.equal(requests.at(-1).body.expected_revision, 2);
	assert.equal(new URL(location.href).searchParams.get("run"), actualRun.id);
	await click("Cancel calculation");
	await until(
		() =>
			document.querySelector(".lp-run-result h3")?.textContent ===
			"Calculation cancelled",
	);
	await click("Scenario settings");
	assert.equal(new URL(location.href).searchParams.get("run"), null);
	await enter(control("AC charging power"), "8");
	gate = deferred();
	await click("Prepare scenario settings");
	await until(
		() => requests.filter((x) => x.path === "battery/scenario").length === 2,
	);
	await act(async () => {
		current = undoDraft(current);
		setter(current);
	});
	const restored = structuredClone(current.history.current);
	await act(async () => gate.resolve());
	await until(() =>
		document
			.querySelector(".lp-notice")
			?.textContent.includes("inputs changed before preparation finished"),
	);
	assert.deepEqual(
		current.history.current,
		restored,
		"late asset response cannot overwrite the restored scenario",
	);
	assert.equal(current.history.current.energy_scenario.battery.charge_ac_kw, 7);
});

test("a user-initiated calculation blocked by the readiness guard explains itself", () => {
	const previousWindow = globalThis.window;
	globalThis.window = {
		wp: { i18n: { __: (message) => message, sprintf: () => "" } },
	};
	try {
		// The pipeline's silent skip stays silent; a visitor's click on an
		// enabled button must surface why nothing started (production
		// 2026-11-07: "Check saved equipment selection" did nothing
		// observable).
		assert.match(
			energyErrorText(new ApiError(409, "inputs_not_ready")),
			/not ready to calculate yet/,
		);
	} finally {
		if (previousWindow) globalThis.window = previousWindow;
		else delete globalThis.window;
	}
});
