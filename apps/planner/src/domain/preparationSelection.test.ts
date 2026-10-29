import assert from "node:assert/strict";
import test from "node:test";
import dcPlant from "../../tests/fixtures/dc-plant-energy-run.json" with { type: "json" };
import fixture from "../../tests/fixtures/preparation-flow.json" with { type: "json" };
import { readRun, RUN_OPERATIONS } from "../data/planningProtocol.ts";
import { ApiError, type JsonObject } from "../data/protocol.ts";
import { readObject, readProject } from "../data/readProtocol.ts";
import { readDcParameters } from "./dcEnergy.ts";
import { DC_LOSS_FIELDS } from "./dcEnergy.ts";
import { emptyScenario, readScenarioDraft } from "./energyScenario.ts";
import {
	applyEquipmentContext,
	equipmentContext,
	readEquipmentPlant,
} from "./equipmentPlant.ts";
import {
	plantEnergyDraft,
	plantEnergyInputs,
	plantEnergyParts,
} from "./plantEnergy.ts";
import { selectPreparation } from "./preparationSelection.ts";
import {
	GEOMETRIC_ROOF_SELECTION,
	geometricRoofAssetId,
	readSelections,
} from "./profiles.ts";
import { scenarioInputs } from "./energyScenario.ts";

const refusal = (code: string) => (error: unknown) =>
	error instanceof ApiError && error.status === 422 && error.code === code;

function geometricAdoption() {
	const native = fixture.geometric_pv;
	const project = readProject(native.project);
	const run = readRun(
		native.run,
		project.id,
		native.run.id,
		RUN_OPERATIONS["runs/geometric-pv"],
	);
	const seeded = {
		...project.inputs,
		profile_selections: {
			schema_version: 1,
			selected: { gross_load: "ab".repeat(16) },
		},
	};
	const adopted = selectPreparation(seeded, run, project, native.profile_asset);
	return { native, project, run, adopted };
}

function dcDraft(inputs: JsonObject = dcPlant.project.inputs) {
	const plant = readEquipmentPlant(inputs.equipment_plant);
	const original = readObject(inputs.energy_plant);
	const empty = plantEnergyDraft(inputs, plant);
	const schedule = original.schedule;
	if (!Array.isArray(schedule) || !Array.isArray(original.units))
		throw new Error("fixture");
	const pool = readObject(dcPlant.run.result.parameter_sources.pool);
	const setup = {
		...empty,
		coupling: "plant_shared_dc" as const,
		ac_pv_converter_ids: original.ac_pv_converter_ids as string[],
		schedule: schedule.map((period, index) => {
			const row = readObject(period);
			return {
				...emptyScenario().schedule[0]!,
				...row,
				mode: row.mode as "connected" | "outage",
				id: String(index).repeat(32),
				import_policy:
					row.import_cap_kw === null
						? ("unlimited" as const)
						: ("limited" as const),
				export_policy:
					row.export_cap_kw === null
						? ("unlimited" as const)
						: ("limited" as const),
			};
		}),
		units: empty.units.map((unit) => {
			const units = original.units;
			if (!Array.isArray(units)) throw new Error("fixture");
			const saved = readObject(
				units.find((value) => readObject(value).unit_id === unit.unit_id),
			);
			const entry = dcPlant.run.result.parameter_sources.units.find(
				(row) => row.unit_id === unit.unit_id,
			)!;
			const proof = readDcParameters(pool[entry.parameter_sha256]);
			const parameters = readObject(proof.loss_scenario);
			return {
				...unit,
				reserve_kwh: saved.reserve_kwh as number,
				pv_dc_input_unused: saved.pv_converter_id === null,
				allow_ac_charge: saved.allow_ac_charge as boolean,
				settings: readScenarioDraft({
					...unit.settings,
					initial_inventory: {
						pv_kwh: readObject(saved.initial_inventory).pv_kwh,
						grid_kwh: readObject(saved.initial_inventory).grid_kwh,
						initial_unknown_kwh: readObject(saved.initial_inventory)
							.initial_unknown_kwh,
						source_note: readObject(saved.initial_inventory).source_note,
					},
					terminal_policy: saved.terminal_min_kwh === null ? "none" : "minimum",
					terminal_min_kwh: saved.terminal_min_kwh,
					dc: {
						...unit.settings.dc!,
						pv_converter_id: (saved.pv_converter_id ?? "") as string,
						aux_dc_kw: saved.aux_dc_kw as number,
						source_note: parameters.source_note as string,
						battery_port_id: parameters.battery_port_id as string,
						losses: Object.fromEntries(
							DC_LOSS_FIELDS.map((key) => [key, parameters[key]]),
						),
					},
				}),
			};
		}),
	};
	return { plant, setup };
}

test("geometry then shared DC drops the whole-roof profile without touching another source", () => {
	const { native, adopted } = geometricAdoption();
	const geometricId = native.profile_asset.id;
	assert.equal(geometricRoofAssetId(adopted), geometricId);
	assert.equal(
		readSelections(adopted.profile_selections).selected.pv_available_ac,
		geometricId,
	);
	assert.equal(
		readSelections(adopted.profile_selections).selected.gross_load,
		"ab".repeat(16),
	);
	const { plant, setup } = dcDraft();
	const switched = plantEnergyInputs(adopted, setup);
	const selected = readSelections(switched.profile_selections).selected;
	assert.equal(selected.pv_available_ac, undefined);
	assert.equal(selected.pv_reference, undefined);
	assert.equal(selected.gross_load, "ab".repeat(16));
	assert.equal(switched[GEOMETRIC_ROOF_SELECTION], undefined);
	assert.equal(switched.energy_replay, undefined);
	const sent = plantEnergyParts(
		setup,
		readSelections({
			schema_version: 1,
			selected: {
				...selected,
				pv_reference: dcPlant.project.inputs.energy_plant.pv_reference_asset_id,
				aux_ac: dcPlant.project.inputs.energy_plant.aux_ac_asset_id,
			},
		}),
		plant,
		switched,
	);
	assert.equal(sent.inputs.pv_available_asset_id, null);
	assert.notEqual(sent.inputs.pv_reference_asset_id, geometricId);
	assert.equal(
		sent.inputs.pv_reference_asset_id,
		dcPlant.project.inputs.energy_plant.pv_reference_asset_id,
	);
});

test("shared DC then geometry is refused before the roof profile is adopted", () => {
	const { project, run, native } = geometricAdoption();
	const reference = "cd".repeat(16);
	assert.throws(
		() =>
			selectPreparation(
				{
					...project.inputs,
					profile_selections: {
						schema_version: 1,
						selected: { pv_reference: reference },
					},
				},
				run,
				project,
				native.profile_asset,
			),
		refusal("pvgis_reference_dc_conflict"),
	);
	assert.throws(
		() =>
			selectPreparation(
				{
					...project.inputs,
					energy_plant_setup: { coupling: "plant_shared_dc", units: [] },
				},
				run,
				project,
				native.profile_asset,
			),
		refusal("pvgis_reference_dc_conflict"),
	);
	assert.equal(project.inputs.profile_selections, undefined);
});

test("adopting a shared DC reference drops a different geometric roof asset", () => {
	const geometricId = fixture.geometric_pv.profile_asset.id;
	const run = readRun(fixture.pv_run, fixture.pv_run.project_id);
	const historical = readProject(fixture.pv_project);
	const asset = readObject(fixture.pv_run.result.prepared_asset);
	assert.notEqual(asset.id, geometricId);
	const joint = selectPreparation(
		{
			...historical.inputs,
			equipment_plant: dcPlant.project.inputs.equipment_plant,
			profile_selections: {
				schema_version: 1,
				selected: {
					pv_available_ac: geometricId,
					gross_load: "ab".repeat(16),
				},
			},
			[GEOMETRIC_ROOF_SELECTION]: {
				schema_version: 1,
				asset_id: geometricId,
			},
		},
		run,
		historical,
		asset,
	);
	const chosen = readSelections(joint.profile_selections).selected;
	assert.equal(chosen.pv_reference, asset.id);
	assert.equal(chosen.pv_available_ac, undefined);
	assert.equal(chosen.gross_load, "ab".repeat(16));
	assert.equal(joint[GEOMETRIC_ROOF_SELECTION], undefined);
	const { plant, setup } = dcDraft();
	const sent = plantEnergyParts(
		setup,
		readSelections({
			schema_version: 1,
			selected: {
				...chosen,
				aux_ac: dcPlant.project.inputs.energy_plant.aux_ac_asset_id,
			},
		}),
		plant,
		joint,
	);
	assert.equal(sent.inputs.pv_available_asset_id, null);
	assert.equal(sent.inputs.pv_reference_asset_id, asset.id);
	assert.throws(
		() =>
			plantEnergyParts(
				setup,
				readSelections({
					schema_version: 1,
					selected: {
						gross_load: "ab".repeat(16),
						aux_ac: "cd".repeat(16),
						pv_reference: asset.id,
						pv_available_ac: geometricId,
					},
				}),
				plant,
				{
					[GEOMETRIC_ROOF_SELECTION]: {
						schema_version: 1,
						asset_id: geometricId,
					},
				},
			),
		refusal("plant_dc_duplicate_pv_source"),
	);
});

test("coupling and equipment context changes clear only the recorded geometric roof", () => {
	const { adopted, native } = geometricAdoption();
	const geometricId = native.profile_asset.id;
	const external = "ef".repeat(16);
	const replaced = {
		...adopted,
		profile_selections: {
			schema_version: 1,
			selected: {
				gross_load: "ab".repeat(16),
				pv_available_ac: external,
			},
		},
	};
	const { setup } = dcDraft();
	const keptExternal = plantEnergyInputs(replaced, setup);
	assert.equal(
		readSelections(keptExternal.profile_selections).selected.pv_available_ac,
		external,
	);
	assert.equal(keptExternal[GEOMETRIC_ROOF_SELECTION], undefined);
	const single = scenarioInputs(adopted, {
		...emptyScenario(),
		coupling: "shared_dc",
	});
	assert.equal(
		readSelections(single.profile_selections).selected.pv_available_ac,
		undefined,
	);
	assert.equal(
		readSelections(single.profile_selections).selected.gross_load,
		"ab".repeat(16),
	);
	const unchanged = applyEquipmentContext(adopted, equipmentContext(adopted));
	assert.equal(
		readSelections(unchanged.profile_selections).selected.pv_available_ac,
		geometricId,
	);
	const withReplay = {
		...adopted,
		energy_plant: {
			coupling: "plant_shared_dc",
			pv_available_asset_id: geometricId,
			pv_reference_asset_id: "cd".repeat(16),
		},
	};
	const switched = applyEquipmentContext(
		withReplay,
		equipmentContext(dcPlant.project.inputs),
	);
	assert.equal(
		readSelections(switched.profile_selections).selected.pv_available_ac,
		undefined,
	);
	assert.equal(
		readSelections(switched.profile_selections).selected.gross_load,
		"ab".repeat(16),
	);
	assert.equal(switched.energy_plant, undefined);
	assert.equal(switched[GEOMETRIC_ROOF_SELECTION], undefined);
	assert.equal(
		switched.equipment_plant,
		dcPlant.project.inputs.equipment_plant,
	);
});
