import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { IDBFactory } from "fake-indexeddb";
import { enter, setupDom, until } from "./dom-fixture.mjs";
import fixture from "./fixtures/dc-plant-energy-run.json" with { type: "json" };
import preparation from "./fixtures/index.ts";
import { readPlantDraft } from "../src/domain/equipmentPlant.ts";
import {
	plantEnergyDraft,
	plantEnergyEquipment,
} from "../src/domain/plantEnergy.ts";
import { ApiError } from "../src/data/protocol.ts";
import { authoredCalculationInputs } from "../src/domain/currentCalculation.ts";

async function configurator(t, callbacks = {}) {
	const dom = setupDom();
	globalThis.indexedDB = new IDBFactory();
	const { createRoot } = await import("react-dom/client");
	const { QueryClient, QueryClientProvider } =
		await import("@tanstack/react-query");
	const { default: Configurator } =
		await import("../src/components/configurator/ProjectWorkbench.tsx");
	const { DraftStore } = await import("../src/data/DraftStore.ts");
	const project = structuredClone(fixture.project);
	delete project.inputs.energy_plant;
	callbacks.setup?.(project);
	window.history.replaceState(
		null,
		"",
		`?project=${project.id}${callbacks.search ?? ""}#sc-${callbacks.chapter ?? "energy"}`,
	);
	const scope = "3".repeat(64);
	const session = {
		kind: "guest",
		query_scope: scope,
		claim_pending: false,
		runtime: {
			limits: {
				max_page_size: 30,
				max_json_depth: 32,
				max_body_bytes: 1000000,
			},
			models: {
				plant_dc_replay: "plant_shared_dc_energy_replay_v1",
				comparison: "frozen_energy_comparison_v1",
				report: "planning_report_v1",
			},
		},
	};
	const client = {
		isCurrentScope: (value) => value === scope,
		query: async (path, body) => {
			if (callbacks.query) return callbacks.query(path, body);
			assert.equal(path, "projects/runs");
			return { items: [], next: null };
		},
		send: async (path, raw) => callbacks.send(path, JSON.parse(raw)),
	};
	const cache = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const store = new DraftStore();
	let root = createRoot(dom.element);
	t.after(async () => {
		await dom.dispose(root);
		cache.clear();
		delete globalThis.indexedDB;
	});
	async function render(snapshot = project, reopen = false) {
		if (reopen) {
			await act(async () => root.unmount());
			root = createRoot(dom.element);
			cache.clear();
			window.history.replaceState(
				null,
				"",
				`?project=${snapshot.id}#sc-energy`,
			);
		}
		await act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(Configurator, {
						project: snapshot,
						config: { locale: "en" },
						session,
						client,
						store,
						recheck() {},
						close: () => true,
					}),
				),
			),
		);
	}
	await render();
	const button = (text) =>
		[...dom.element.querySelectorAll("button")].find(
			(b) =>
				(b.textContent.trim() === text ||
					(b.closest(".sc-nav") && b.textContent.trim().endsWith(text))) &&
				!b.closest("[hidden]"),
		);
	const label = (text) =>
		[...dom.element.querySelectorAll("label")].find(
			(label) =>
				label.querySelector("span")?.textContent.trim() === text &&
				!label.closest("[hidden]"),
		);
	const select = (text) => label(text)?.querySelector("select");
	const input = (text) => label(text)?.querySelector("input");
	async function choose(text, value) {
		const field = select(text);
		assert.ok(field, text);
		assert.ok(field.querySelector(`option[value="${value}"]`), value);
		await act(async () => {
			field.value = value;
			field.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	}
	async function click(text) {
		await until(() => button(text) && !button(text).disabled).catch((cause) => {
			throw new Error(
				`${text}: ${[...dom.element.querySelectorAll('[role="alert"]')].map((node) => node.textContent).join(" / ")}`,
				{ cause },
			);
		});
		await act(async () => button(text).click());
	}
	return { dom, project, button, click, choose, select, input, render };
}

function comparisonReply(run, other) {
	const reference = (id) => ({
		run_id: id,
		revision: run.revision,
		coupling: "plant_shared_dc",
		scenario_constraint_status: "satisfied",
		equipment_status: "unresolved",
		equipment_models: ["Fixture converter"],
		source_note: "Fixture input",
		manifest_sha256: run.manifest_sha256,
		result_sha256: run.result_sha256,
		input_sha256: run.manifest.input_sha256,
		runtime_sha256: run.manifest.context.code_sha256,
		numerical_basis_sha256: "c".repeat(64),
		usable_window_kwh: 18,
		modules_per_stack: null,
		parallel_stacks: null,
	});
	return {
		schema_version: 1,
		model: "frozen_energy_comparison_v1",
		project_id: run.project_id,
		baseline: reference(run.id),
		candidate: reference(other),
		conditions_aligned: false,
		equipment_release: "not_established",
		country_release: "not_assessed",
		conditions: [
			"site",
			"periods",
			"demand_sources",
			"pv_weather",
			"time_resolution",
			"operating_requirements",
			"starting_inventory",
			"terminal_requirement",
			"load_scope",
			"calculation_method",
			"scenario_constraints",
			"battery_temperature",
		].map((id) => ({
			id,
			status: id === "battery_temperature" ? "different" : "matched",
		})),
		differences: [
			"storage_parameters",
			"equipment_selection",
			"pv_design",
			"dc_auxiliary",
		].map((id) => ({ id, changed: id === "storage_parameters" })),
		metrics: [
			"load_demand",
			"solar_supply",
			"grid_import",
			"unserved_load",
			"pv_export",
			"stored_final",
			"pv_generation",
			"solar_share",
			"pv_use",
		].map((id) => ({
			id,
			unit: "kWh",
			delta_unit: "kWh",
			baseline: 1,
			candidate: 2,
			baseline_boundary: "ac",
			candidate_boundary: "ac",
			delta: null,
			delta_reason: "conditions_differ",
			baseline_undefined_reason: null,
			candidate_undefined_reason: null,
		})),
	};
}

for (const chapter of ["review", "energy"])
	for (const comparison of [false, true]) {
		test(`a saved Genie ${comparison ? "comparison" : "calculation"} opens the referenced runs from ${chapter} regardless of the current project inputs`, async (t) => {
			const run = fixture.run;
			const other = "1".repeat(32);
			const reads = [];
			const ui = await configurator(t, {
				chapter,
				search: comparison ? `&compare=${run.id},${other}` : `&run=${run.id}`,
				setup(project) {
					project.revision = run.revision + 1;
					delete project.inputs.equipment_plant;
				},
				query(path, body) {
					if (path === "projects/runs") return { items: [], next: null };
					reads.push([path, body]);
					if (path === "runs/compare") return comparisonReply(run, other);
					if (path === "runs/read") return run;
					throw Error(path);
				},
			});
			await until(() =>
				reads.some(
					([path]) => path === (comparison ? "runs/compare" : "runs/read"),
				),
			);
			const [, requested] = reads.find(
				([path]) => path === (comparison ? "runs/compare" : "runs/read"),
			);
			if (comparison) {
				assert.equal(requested.baseline_run_id, run.id);
				assert.equal(requested.candidate_run_id, other);
				await until(() =>
					ui.dom.element.textContent.includes("Fixture converter"),
				);
			} else {
				assert.equal(requested.run_id, run.id);
				await until(
					() =>
						ui.dom.element.querySelector(".sc-run-revision")?.textContent ===
						`Input revision ${run.revision}`,
				);
			}
		});
	}

test("an installer calculates the declared ports, adopts the frozen result, and reopens it", async (t) => {
	let original, saved, run, report;
	let refusals = 0;
	const newerId = "f".repeat(32);
	const reports = [];
	const commands = [];
	const ui = await configurator(t, {
		setup(project) {
			delete project.inputs.pv_plant_string_plan;
			const energy = fixture.project.inputs.energy_plant;
			const setup = plantEnergyDraft(
				project.inputs,
				plantEnergyEquipment(project.inputs),
			);
			project.inputs.energy_plant_setup = {
				...setup,
				ac_pv_converter_ids: ["ac-pv"],
				units: setup.units.map((unit, i) => ({
					...unit,
					reserve_kwh: 0,
					pv_dc_input_unused: false,
					allow_ac_charge: false,
					settings: {
						...unit.settings,
						terminal_policy: "none",
						initial_inventory: {
							pv_kwh: 0,
							grid_kwh: 0,
							initial_unknown_kwh: 0,
							source_note: "Empty fixture inventory",
						},
						dc: {
							...unit.settings.dc,
							pv_converter_id: energy.units[i].pv_converter_id,
							battery_port_id: "BAT1",
							battery_temperature_c: 20,
							source_note: "Synthetic loss scenario",
							losses: {
								eta_bus_to_battery: 1,
								eta_battery_to_bus: 1,
								eta_store_charge: 1,
								eta_store_discharge: 1,
								eta_inverter_forward: 1,
								eta_inverter_reverse: null,
								internal_aux_kw: 0,
								standing_loss_rate_per_hour: 0,
							},
						},
					},
				})),
				schedule: [
					{
						...setup.schedule[0],
						mode: "connected",
						start_utc: "2020-06-21T12:00:00Z",
						end_utc: "2020-06-21T14:00:00Z",
						import_policy: "unlimited",
						export_policy: "limited",
						export_cap_kw: 0,
						pv_enabled: true,
						allow_grid_charge: false,
					},
				],
			};
			project.inputs = authoredCalculationInputs(project.inputs);
			original = saved = project;
		},
		query(path, body) {
			if (path === "projects/read")
				return body.revision === run?.revision ? original : saved;
			if (path === "projects/runs") {
				if (!run) return { items: [], next: null };
				const { manifest, result, error, ...summary } = run;
				return {
					items: [newerId, run.id].map((id, index) => ({
						...summary,
						id,
						task_kind: "plant_shared_dc_energy_replay_v1",
						created_at: 2 - index,
					})),
					next: null,
				};
			}
			if (path === "runs/read")
				return body.run_id === report?.id ? report : run;
			if (path === "runs/inputs")
				return {
					schema_version: 1,
					project_id: saved.id,
					run_id: body.run_id,
					manifest_sha256: run.manifest_sha256,
					inputs: {
						...original.inputs,
						energy_plant: fixture.project.inputs.energy_plant,
					},
				};
			if (path === "runs/compare") {
				assert.equal(body.baseline_run_id, run.id);
				assert.equal(body.candidate_run_id, newerId);
				return comparisonReply(run, newerId);
			}
			throw new Error(path);
		},
		send(path, command) {
			commands.push({ path, command });
			if (path === "runs/calculate") {
				if (++refusals === 1) {
					throw new ApiError(422, "invalid_input", null, null, [
						"energy_plant_setup.schedule[0].start_utc",
					]);
				}
				if (refusals === 2)
					throw new ApiError(422, "evidence_missing", null, {
						constraint_id: "plant_dc_duplicate_pv_source",
					});
				// The corrected UTC spelling changes the authored revision but not the simulated interval.
				original = saved = {
					...saved,
					revision: command.expected_revision + 1,
					input_sha256: "d".repeat(64),
					inputs: command.inputs,
				};
				// Current authored runs pin a separate execution document.
				const assets = {
					...fixture.run.manifest.context.assets,
					resolved_inputs: "7".repeat(64),
				};
				run = {
					...fixture.run,
					revision: saved.revision,
					manifest: {
						...fixture.run.manifest,
						revision: saved.revision,
						input_sha256: saved.input_sha256,
						context: { ...fixture.run.manifest.context, assets },
					},
					result: {
						...fixture.run.result,
						revision: saved.revision,
						input_sha256: saved.input_sha256,
						pinned_assets: assets,
					},
				};
				return { schema_version: 1, project: saved, run };
			}
			if (path === "runs/report") {
				reports.push(command.options);
				report = {
					...fixture.report,
					state: "queued",
					revision: command.expected_revision,
					result: null,
					result_sha256: null,
					manifest: {
						...fixture.report.manifest,
						revision: command.expected_revision,
						input_sha256: saved.input_sha256,
					},
				};
				return report;
			}
			assert.equal(path, "projects/revise");
			saved = {
				...saved,
				revision: saved.revision + 1,
				input_sha256: "e".repeat(64),
				inputs: command.inputs,
			};
			return saved;
		},
	});
	await ui.click("Calculate energy flows");
	await until(() =>
		ui.dom.element.textContent.includes("The scenario could not be accepted."),
	);
	await ui.click("Operation");
	const rejectedStart = ui.input("Start with UTC or offset");
	assert.equal(rejectedStart.getAttribute("aria-invalid"), "true");
	await ui.click("Calculate energy flows");
	await until(() =>
		ui.dom.element.textContent.includes(
			"The same roof PV source cannot also be counted as an additional AC source.",
		),
	);
	const correctedStart = "2020-06-21T12:00:00+00:00";
	await until(() => ui.input("Start with UTC or offset")?.matches(":enabled"));
	await enter(ui.input("Start with UTC or offset"), correctedStart);
	await ui.click("Calculate energy flows");
	await until(() => commands.length === 3);
	const { command } = commands[2];
	assert.equal(
		commands[1].command.inputs.energy_plant_setup.schedule[0].start_utc,
		"2020-06-21T12:00:00Z",
	);
	assert.equal(
		command.inputs.energy_plant_setup.schedule[0].start_utc,
		correctedStart,
	);
	assert.equal(command.inputs.energy_plant, undefined);
	assert.equal(
		command.inputs.profile_selections.selected.pv_reference,
		fixture.project.inputs.profile_selections.selected.pv_reference,
	);
	assert.deepEqual(
		command.inputs.energy_plant_setup.units.map(({ unit_id, settings }) => [
			unit_id,
			settings.dc.pv_converter_id,
			settings.dc.battery_port_id,
		]),
		[
			["a", "converter", "BAT1"],
			["b", "dc-b", "BAT1"],
		],
	);
	await ui.click("Use this calculation in the report");
	await until(() => commands.length === 4);
	assert.equal(saved.inputs.shared_dc_energy_run_id, fixture.run.id);
	await ui.render(saved, true);
	await until(() =>
		ui.dom.element.textContent.includes("Selected for the report"),
	);
	const unitStatuses = [...ui.dom.element.querySelectorAll("summary")].map(
		(node) => node.textContent.trim(),
	);
	assert.ok(
		unitStatuses.some((text) => /^A · .*Further checks required$/.test(text)),
	);
	assert.ok(
		unitStatuses.some((text) => /^B · .*Requirements not met$/.test(text)),
	);
	await ui.choose("Baseline calculation", fixture.run.id);
	await ui.choose("Comparison calculation", newerId);
	await until(() =>
		ui.dom.element.textContent.includes(
			"No differences are shown because the comparison conditions differ or are incomplete.",
		),
	);
	await ui.click("Review & send");
	await ui.click("Generate project report");
	await until(() => reports.length === 1);
	assert.equal(reports[0].energy_run_id, fixture.run.id);
	await ui.render(saved, true);
	await ui.click("Storage");
	assert.equal(ui.input("PV conversion group").value, "converter");
	await enter(ui.input("PV conversion group"), "dc-b");
	await ui.click("Saved calculations");
	assert.equal(ui.button("Use this calculation in the report"), undefined);
	await ui.click("Review & send");
	await ui.click("Generate project report");
	await until(() =>
		ui.dom.element.textContent.includes(
			"A selected result does not match the saved project inputs.",
		),
	);
	assert.equal(reports.length, 1);
});

test("a draft plant selects the native PV preparation as the DC source", async (t) => {
	const run = preparation.pv_run;
	const weather = preparation.weather_run.result.prepared_asset;
	let saved;
	const ui = await configurator(t, {
		setup(project) {
			const plant = readPlantDraft(project.inputs);
			Object.assign(project, structuredClone(preparation.pv_project));
			project.inputs.equipment_plant_setup = plant;
		},
		query(path, body) {
			if (path === "projects/read") return preparation.pv_project;
			if (path === "projects/runs") {
				const { manifest, result, error, ...summary } = run;
				return {
					items: [
						{
							...summary,
							task_kind: "prepare_roof_pv_reference_v1",
							created_at: 1,
						},
					],
					next: null,
				};
			}
			if (path === "runs/read") return run;
			if (path === "assets/read")
				return body.asset_id === weather.id
					? weather
					: run.result.prepared_asset;
			throw new Error(path);
		},
		send(path, command) {
			assert.equal(path, "projects/revise");
			saved = {
				...preparation.pv_project,
				revision: command.expected_revision + 1,
				input_sha256: "e".repeat(64),
				inputs: command.inputs,
			};
			return saved;
		},
	});
	await ui.click("Set up shared DC energy flows");
	await ui.click("Interval sources");
	await ui.click("Weather-based PV reference");
	await ui.click("Use this PV profile");
	await ui.click("Save snapshot");
	await until(() => Boolean(saved));
	assert.deepEqual(saved.inputs.profile_selections.selected, {
		pv_reference: run.result.prepared_asset.id,
	});
});

test("Energy use lets an installer bind the two converters to distinct DC PV groups", async (t) => {
	const ui = await configurator(t);
	await until(() => ui.button("Set up shared DC energy flows"));
	await ui.click("Set up shared DC energy flows");
	await ui.choose("PV connection on this converter", "connected");
	await enter(ui.input("PV conversion group"), "converter");
	await ui.choose("Storage unit", "b");
	await ui.choose("PV connection on this converter", "connected");
	await enter(ui.input("PV conversion group"), "dc-b");
	await ui.choose("Storage unit", "a");
	assert.equal(ui.input("PV conversion group").value, "converter");
	await ui.choose("Storage unit", "b");
	assert.equal(ui.input("PV conversion group").value, "dc-b");
});
