import invalidJson from "../../tests/fixtures/energy-invalid.json" with { type: "json" };
import test from "node:test";
import assert from "node:assert/strict";
import scenarioJson from "../../tests/fixtures/energy-scenario.json" with { type: "json" };
import profilesJson from "../../tests/fixtures/energy-selections.json" with { type: "json" };
import inputsJson from "../../tests/fixtures/energy-inputs.json" with { type: "json" };
import {
	emptyScenario,
	readScenarioDraft,
	scenarioParts,
	compileScenario,
	readBatteryParameters,
	readEnergyInputs,
	scenarioInputs,
	invalidateEnergyReplay,
} from "./energyScenario.ts";
import { readSelections } from "./profiles.ts";
import { ApiError } from "../data/protocol.ts";
import plantAcFixture from "../../tests/fixtures/plant-energy-run.json" with { type: "json" };
import { readEquipmentPlant } from "./equipmentPlant.ts";
import { plantEnergyDraft, compilePlantEnergy } from "./plantEnergy.ts";
import dcPlantFixture from "../../tests/fixtures/dc-plant-energy-run.json" with { type: "json" };
import { readObject } from "../data/readProtocol.ts";
import {
	readDcParameters,
	readDcLossScenario,
	restoreDcConditions,
	emptyDcScenario,
	REFERENCE_CAPACITY,
} from "./dcEnergy.ts";
import { DC_LOSS_FIELDS } from "./dcEnergy.ts";

const scenario = () => readScenarioDraft(structuredClone(scenarioJson));

test("DC recovery restores the original capacity choice instead of inheriting the current mode", () => {
	const pool = dcPlantFixture.run.result.parameter_sources.pool;
	const proof = readDcParameters(Object.values(pool)[0]);
	const original = readDcLossScenario(proof.loss_scenario);
	const current = {
		...emptyDcScenario(),
		capacity_window_basis: REFERENCE_CAPACITY as typeof REFERENCE_CAPACITY,
	};
	const restored = restoreDcConditions(current, original);
	assert.equal(Object.hasOwn(restored, "capacity_window_basis"), false);
	assert.equal(
		restoreDcConditions(
			current,
			readDcLossScenario({ ...original, capacity_window_basis: null }),
		).capacity_window_basis,
		null,
	);
	assert.equal(
		restoreDcConditions(
			{ ...current, capacity_window_basis: null },
			readDcLossScenario({
				...original,
				capacity_window_basis: REFERENCE_CAPACITY,
			}),
		).capacity_window_basis,
		REFERENCE_CAPACITY,
	);
});
const profiles = () => readSelections(structuredClone(profilesJson));
const refusal = (code: string) => (error: unknown) =>
	error instanceof ApiError && error.status === 422 && error.code === code;

for (const plantFixture of [plantAcFixture, dcPlantFixture]) {
	test(`joint preparation preserves each native unit asset and refuses a changed equipment binding: ${plantFixture.run.result.kind}`, () => {
		const inputs = plantFixture.project.inputs;
		const plant = readEquipmentPlant(inputs.equipment_plant);
		const original = inputs.energy_plant;
		const empty = plantEnergyDraft(inputs, plant);
		assert.equal(empty.units[0]!.pv_dc_input_unused, null);
		const setup = {
			...empty,
			ac_pv_converter_ids:
				"ac_pv_converter_ids" in original ? original.ac_pv_converter_ids : [],
			schedule: original.schedule.map((p, index) => ({
				...emptyScenario().schedule[0]!,
				...p,
				mode: p.mode as "connected" | "outage",
				id: String(index).repeat(32),
				import_policy:
					p.import_cap_kw === null
						? ("unlimited" as const)
						: ("limited" as const),
				export_policy:
					p.export_cap_kw === null
						? ("unlimited" as const)
						: ("limited" as const),
			})),
			units: empty.units.map((unit) => {
				const saved = original.units.find((u) => u.unit_id === unit.unit_id)!;
				const entry = plantFixture.run.result.parameter_sources.units.find(
					(u) => u.unit_id === unit.unit_id,
				)!;
				const pool = plantFixture.run.result.parameter_sources.pool;
				const proof = readDcParameters(
					readObject(pool)[entry.parameter_sha256],
				);
				const parameters = readObject(proof.loss_scenario);
				return {
					...unit,
					reserve_kwh: saved.reserve_kwh,
					pv_dc_input_unused:
						"pv_converter_id" in saved ? saved.pv_converter_id === null : true,
					allow_ac_charge:
						"allow_ac_charge" in saved ? saved.allow_ac_charge : null,
					settings: readScenarioDraft({
						...unit.settings,
						initial_inventory: {
							pv_kwh: saved.initial_inventory.pv_kwh,
							grid_kwh: saved.initial_inventory.grid_kwh,
							initial_unknown_kwh: saved.initial_inventory.initial_unknown_kwh,
							source_note: saved.initial_inventory.source_note,
						},
						terminal_policy:
							saved.terminal_min_kwh === null ? "none" : "minimum",
						terminal_min_kwh: saved.terminal_min_kwh,
						dc: {
							...unit.settings.dc,
							pv_converter_id:
								"pv_converter_id" in saved ? (saved.pv_converter_id ?? "") : "",
							aux_dc_kw: "aux_dc_kw" in saved ? saved.aux_dc_kw : 0,
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
							equipment_selection: plant.units.find(
								(u) => u.id === unit.unit_id,
							)!.selection,
						},
					}),
				};
			}),
		};
		const profiles = readSelections({
			schema_version: 1,
			selected: {
				gross_load: original.gross_load_asset_id,
				...(original.pv_available_asset_id
					? { pv_available_ac: original.pv_available_asset_id }
					: {}),
				...("pv_reference_asset_id" in original &&
				original.pv_reference_asset_id
					? { pv_reference: original.pv_reference_asset_id }
					: {}),
				aux_ac: original.aux_ac_asset_id,
			},
		});
		assert.deepEqual(compilePlantEnergy(setup, profiles, plant), {
			...original,
			units: original.units.map((u) => ({
				...u,
				initial_inventory: { ...u.initial_inventory, basis: "user_declared" },
			})),
		});
		const changed = {
			...plant,
			units: plant.units.map((u, index) =>
				index === 0
					? {
							...u,
							selection: {
								...u.selection,
								modules_per_stack: u.selection.modules_per_stack! + 1,
							},
						}
					: u,
			),
		};
		assert.throws(
			() => compilePlantEnergy(setup, profiles, changed),
			refusal("battery_not_prepared"),
		);
	});
}

test("unfinished draft retains nulls while explicit zero survives preparation", () => {
	const blank = emptyScenario();
	assert.ok(Object.values(blank.battery).every((value) => value === null));
	assert.equal(blank.initial_inventory.pv_kwh, null);
	assert.equal(blank.schedule[0]!.reserve_kwh, null);
	assert.throws(
		() => scenarioParts(blank, profiles()),
		refusal("battery_source_required"),
	);
	assert.deepEqual(compileScenario(scenario(), profiles()), inputsJson);
	assert.equal(
		compileScenario(scenario(), profiles()).initial_inventory.pv_kwh,
		0,
	);
});

test("generated parameter/input contracts refuse coercion, hidden defaults and extra facts", () => {
	const parameters = scenario().battery_binding!.parameters;
	for (const changed of [
		{ ...parameters, eta_charge: 0 },
		{ ...parameters, eta_discharge: 1.001 },
		{ ...parameters, charge_ac_kw: "5" },
		{ ...parameters, guessed_soc: 0.5 },
	])
		assert.throws(() => readBatteryParameters(changed));
	const { internal_aux_kw: _missing, ...missing } = parameters;
	assert.throws(() => readBatteryParameters(missing));
	assert.throws(() =>
		readEnergyInputs({ ...inputsJson, controller: "tariff_optimizer" }),
	);
	assert.throws(() =>
		readEnergyInputs({ ...inputsJson, terminal_min_kwh: -1 }),
	);
	assert.equal(
		readBatteryParameters({ ...parameters, usable_window_kwh: 0 })
			.usable_window_kwh,
		0,
	);
});

test("battery binding belongs to exact parameters and source, and source selection must be explicit", () => {
	const value = scenario();
	assert.throws(
		() =>
			compileScenario({ ...value, source_note: "another basis" }, profiles()),
		refusal("battery_not_prepared"),
	);
	assert.throws(
		() =>
			compileScenario(
				{ ...value, battery: { ...value.battery, usable_window_kwh: 8 } },
				profiles(),
			),
		refusal("battery_not_prepared"),
	);
	assert.throws(
		() =>
			scenarioParts(
				value,
				readSelections({
					schema_version: 1,
					selected: {
						net_import: "f".repeat(32),
						pv_available_ac: "d".repeat(32),
						aux_ac: "e".repeat(32),
					},
				}),
			),
		refusal("scenario_profiles_required"),
	);
	assert.throws(
		() =>
			scenarioParts(
				{
					...value,
					initial_inventory: { ...value.initial_inventory, grid_kwh: null },
				},
				profiles(),
			),
		refusal("initial_inventory_required"),
	);
	assert.throws(
		() =>
			scenarioParts(
				{
					...value,
					initial_inventory: { ...value.initial_inventory, grid_kwh: 6 },
				},
				profiles(),
			),
		refusal("initial_inventory_exceeds_window"),
	);
});

test("grid policies and outage coverage are choices, with no browser rounding of instants", () => {
	const value = scenario(),
		period = value.schedule[0]!;
	const withPeriod = (patch: object) =>
		readScenarioDraft({ ...value, schedule: [{ ...period, ...patch }] });
	assert.throws(
		() => scenarioParts(withPeriod({ mode: null }), profiles()),
		refusal("operating_period_incomplete"),
	);
	assert.throws(
		() =>
			scenarioParts(
				withPeriod({ import_policy: "limited", import_cap_kw: null }),
				profiles(),
			),
		refusal("grid_cap_required"),
	);
	assert.equal(
		compileScenario(
			withPeriod({ import_policy: "limited", import_cap_kw: 0 }),
			profiles(),
		).schedule[0]!.import_cap_kw,
		0,
	);
	assert.throws(
		() =>
			scenarioParts(
				withPeriod({ start_utc: "2024-03-30T23:00:00" }),
				profiles(),
			),
		refusal("period_offset_required"),
	);
	const micro = "2024-03-30T23:00:00.000001Z";
	assert.equal(
		compileScenario(withPeriod({ start_utc: micro }), profiles()).schedule[0]!
			.start_utc,
		micro,
	);
	assert.throws(
		() => scenarioParts(withPeriod({ mode: "outage" }), profiles()),
		refusal("operating_period_incomplete"),
	);
	const critical = readSelections({
		schema_version: 1,
		selected: { ...profiles().selected, critical_load: "f".repeat(32) },
	});
	const outage = compileScenario(
		withPeriod({
			mode: "outage",
			import_policy: null,
			export_policy: null,
			allow_grid_charge: null,
		}),
		critical,
	).schedule[0]!;
	assert.deepEqual(
		[outage.import_cap_kw, outage.export_cap_kw, outage.allow_grid_charge],
		[0, 0, false],
	);
	assert.throws(
		() =>
			compileScenario(
				withPeriod({ mode: "outage", allow_grid_charge: true }),
				critical,
			),
		refusal("outage_grid_charge"),
	);
	// An infeasible reserve is a declared constraint for backend evaluation, not
	// an invented frontend engineering limit that suppresses the scenario.
	assert.equal(
		compileScenario(withPeriod({ reserve_kwh: 9 }), profiles()).schedule[0]!
			.reserve_kwh,
		9,
	);
});

test("editing settings or source selection invalidates the effective replay but preserves unrelated inputs", () => {
	const original = {
		brief: { name: "retained" },
		energy_replay: inputsJson,
		energy_scenario: scenario(),
	};
	const changed = scenarioInputs(original, {
		...scenario(),
		terminal_policy: "minimum",
		terminal_min_kwh: 2,
	});
	assert.equal(changed.energy_replay, undefined);
	assert.deepEqual(changed.brief, original.brief);
	assert.equal(invalidateEnergyReplay(original).energy_replay, undefined);
	assert.equal(original.energy_replay, inputsJson);
	assert.throws(() => readScenarioDraft({ ...scenario(), unknown: 42 }));
	assert.throws(() =>
		readScenarioDraft({
			...scenario(),
			schedule: [...scenario().schedule, ...scenario().schedule],
		}),
	);
});

test("the shared negative contract fixtures fail in the browser without coercion", () => {
	for (const item of invalidJson) {
		const value: Record<string, unknown> = {
			...(item.target === "parameters"
				? scenario().battery_binding!.parameters
				: inputsJson),
			...item.set,
		};
		for (const key of item.delete) delete value[key];
		assert.throws(() =>
			item.target === "parameters"
				? readBatteryParameters(value)
				: readEnergyInputs(value),
		);
	}
});

test("DC preparation binds Woo equipment and losses without manual device limits", () => {
	const equipment = {
		schema_version: 1,
		inverter_product_id: 4107,
		battery_product_id: 2090,
	};
	const base = scenario();
	const dc = readScenarioDraft({
		...base,
		coupling: "shared_dc",
		battery_binding: null,
		dc: {
			source_note:
				"Explicit shared-DC loss scenario; no hardware performance approval.",
			pv_converter_id: "roof-group",
			battery_port_id: "battery-1",
			aux_dc_kw: 0,
			losses: {
				eta_bus_to_battery: 0.98,
				eta_battery_to_bus: 0.97,
				eta_store_charge: 0.99,
				eta_store_discharge: 0.99,
				eta_inverter_forward: 0.96,
				eta_inverter_reverse: null,
				internal_aux_kw: 0,
				standing_loss_rate_per_hour: 0,
			},
		},
	});
	assert.throws(
		() => scenarioParts(dc, profiles()),
		refusal("dc_equipment_required"),
	);
	const parts = scenarioParts(dc, profiles(), equipment);
	assert.equal(parts.parameters.model, "constant_window_shared_dc_bus_v1");
	assert.equal(parts.parameters.usable_window_kwh, undefined);
	assert.equal(parts.inputs.aux_dc_kw, 0);
	assert.equal(parts.parameters.source_note, dc.dc!.source_note);
	assert.notEqual(parts.parameters.source_note, dc.source_note);
	const bound = readScenarioDraft({
		...dc,
		battery_binding: {
			asset_id: "a".repeat(32),
			parameters: parts.parameters,
			source_note: dc.dc!.source_note,
			equipment_selection: equipment,
		},
	});
	const replay = compileScenario(bound, profiles(), equipment);
	assert.equal(replay.coupling, "shared_dc");
	assert.equal(replay.pv_converter_id, "roof-group");
	assert.throws(
		() =>
			compileScenario(bound, profiles(), {
				...equipment,
				battery_product_id: 2091,
			}),
		refusal("battery_not_prepared"),
	);
	assert.deepEqual(compileScenario(base, profiles()), inputsJson);
});
