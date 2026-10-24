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

const scenario = () => readScenarioDraft(structuredClone(scenarioJson));
const profiles = () => readSelections(structuredClone(profilesJson));
const refusal = (code: string) => (error: unknown) =>
	error instanceof ApiError && error.status === 422 && error.code === code;

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
