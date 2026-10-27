import assert from "node:assert/strict";
import { test } from "node:test";
import { beginDraft, editDraft, undoDraft } from "./draft.ts";
import { equipmentDraft } from "./equipment.ts";
import { adoptPlantCandidate, compilePlantSearch } from "./plantSearch.ts";
import {
	applyEquipmentContext,
	beginPlant,
	compilePlant,
	equipmentContext,
	factoryPlant,
	plantInputs,
	readEquipmentPlant,
	readPlantDraft,
	singleSystem,
} from "./equipmentPlant.ts";
import type { EquipmentProduct } from "../data/equipmentProducts.ts";
import type { JsonObject, Project } from "../data/protocol.ts";
import {
	changeDeviceCondition,
	conditionBindingMatches,
	equipmentConditionTargets,
	readEquipmentConditionInputs,
	removeDeviceCondition,
} from "./equipmentConditionInputs.ts";

// Identity-only publication fixtures; no product performance or release facts.
const products: EquipmentProduct[] = [1, 2].map((id) => ({
	id,
	product_revision: String(id).repeat(64),
	brand: "Fixture",
	model: String(id),
	device_class: "fixture",
	figures: {},
}));
const original = {
	site: { country_code: "DE" },
	equipment_setup: {
		...equipmentDraft({}),
		inverter_product_id: 1,
		grid_phase: 3,
		operating_mode: "grid_connected",
		required_usable_kwh: 0,
		required_discharge_ac_kw: 0,
	},
};
const start = () =>
	beginPlant(original, { id: "a", name: "A" }, { id: "b", name: "B" });
function configured() {
	const draft = readPlantDraft(start());
	return {
		...draft,
		units: draft.units.map((u) => ({
			...u,
			inputs: {
				equipment_setup: {
					...equipmentDraft(u.inputs),
					inverter_product_id: 1,
				},
			},
		})),
		parallel_groups: [
			{
				id: "ac",
				unit_ids: ["a", "b"],
				controller_product_id: 2,
				control_network: "lan" as const,
			},
		],
	};
}

test("multi-system editing preserves project history, pins current Woo identities and invalidates preparation", () => {
	const initial: Project = {
		id: "a".repeat(32),
		title: "Fixture",
		revision: 1,
		input_sha256: "b".repeat(64),
		inputs: original,
	};
	const inputs = start();
	assert.equal(
		beginPlant(inputs, { id: "c", name: "C" }, { id: "d", name: "D" }),
		inputs,
	);
	assert.deepEqual(
		undoDraft(editDraft(beginDraft(initial), inputs)).history.current,
		original,
	);
	const setup = configured(),
		compiled = compilePlant(setup, products);
	assert.equal(
		compiled.units[0]!.selection.product_revisions["1"],
		products[0]!.product_revision,
	);
	assert.equal(
		compiled.parallel_groups[0]!.controller_revision,
		products[1]!.product_revision,
	);
	const edited = plantInputs({ ...inputs, equipment_plant: compiled }, setup);
	assert.equal(edited.equipment_plant, undefined);
	const returned = singleSystem(
		plantInputs(edited, {
			...setup,
			units: [setup.units[0]!],
			parallel_groups: [],
		}),
	);
	assert.equal(equipmentDraft(returned).grid_phase, 3);
	assert.equal(returned.equipment_plant_setup, undefined);
	const switched = applyEquipmentContext(
		{
			...inputs,
			energy_plant: { coupling: "plant_ac" },
			energy_replay: { coupling: "independent_ac" },
		},
		equipmentContext(returned),
	);
	assert.equal(switched.energy_plant, undefined);
	assert.equal(switched.energy_replay, undefined);
	assert.deepEqual(
		applyEquipmentContext(
			{ ...original, site: { country_code: "FR" } },
			equipmentContext(inputs),
		).site,
		{ country_code: "FR" },
	);
});

test("plant qualification rejects crossed ownership and inconsistent product revisions", () => {
	const compiled = compilePlant(configured(), products);
	for (const mutate of [
		(p: typeof compiled) => {
			p.units[1]!.selection.product_revisions["1"] = "3".repeat(64);
		},
		(p: typeof compiled) => {
			p.parallel_groups[0]!.unit_ids = ["a", "missing"];
		},
		(p: typeof compiled) => {
			p.units[0]!.name = " ";
		},
	]) {
		const candidate = structuredClone(compiled);
		mutate(candidate);
		assert.throws(() => readEquipmentPlant(candidate));
	}
});

test("factory counts are applied on preparation without editing saved history or multiplying sales units", () => {
	const raw = configured();
	const ready = factoryPlant(raw, {
		"1": {
			sales_unit_kind: "battery_system",
			fixed_modules_per_stack: 11,
			documents: [{ url: "https://de-linker.com/fixture.pdf", page: 2 }],
		},
	});
	// The synthetic publication identifies the battery separately from converter.
	const withBattery = {
		...raw,
		units: raw.units.map((u) => ({
			...u,
			inputs: {
				equipment_setup: {
					...equipmentDraft(u.inputs),
					battery_product_id: 1,
					inverter_product_id: 2,
					parallel_stacks: 1,
				},
			},
		})),
	};
	const prepared = factoryPlant(withBattery, {
		"1": {
			sales_unit_kind: "battery_system",
			fixed_modules_per_stack: 11,
			documents: [{ url: "https://de-linker.com/fixture.pdf", page: 2 }],
		},
	});
	assert.equal(equipmentDraft(prepared.units[0]!.inputs).modules_per_stack, 11);
	assert.equal(equipmentDraft(prepared.units[0]!.inputs).parallel_stacks, 1);
	assert.equal(
		equipmentDraft(withBattery.units[0]!.inputs).modules_per_stack,
		null,
	);
	assert.equal(equipmentDraft(ready.units[0]!.inputs).modules_per_stack, null);
});

test("plant search prepares demand without hardware and adopts one whole candidate without losing unrelated edits", () => {
	const base = configured();
	const complete = {
		...base,
		units: base.units.map((unit) => ({
			...unit,
			inputs: {
				equipment_setup: {
					...equipmentDraft(unit.inputs),
					required_usable_kwh: 0,
					required_discharge_ac_kw: 0,
				},
			},
		})),
	};
	const hardware = compilePlant(complete, products);
	const unselected = {
		...complete,
		units: complete.units.map((unit) => ({
			...unit,
			inputs: {
				equipment_setup: {
					...equipmentDraft(unit.inputs),
					inverter_product_id: null,
				},
			},
		})),
	};
	const plan = compilePlantSearch(unselected);
	assert.equal(plan.units.length, 2);
	assert.equal(plan.units[0]!.requirements.required_usable_kwh, 0);
	assert.throws(() => compilePlant(unselected, products));
	const current = {
		...plantInputs(original, unselected),
		equipment_plant_requirements: plan,
		site: { country_code: "FR" },
	};
	const choice = {
		run_id: "a".repeat(32),
		candidate_id: "b".repeat(64),
		assessment_sha256: "c".repeat(64),
	};
	const adopted = adoptPlantCandidate(current, hardware, products, choice);
	assert.deepEqual(adopted.site, { country_code: "FR" });
	assert.deepEqual(adopted.equipment_candidate, choice);
	assert.deepEqual(adopted.equipment_plant, hardware);
	assert.equal(
		readPlantDraft(adopted).parallel_groups[0]!.control_network,
		"lan",
	);
	const networkChanged = readPlantDraft(current);
	networkChanged.parallel_groups[0]!.control_network = "rs485";
	assert.throws(() =>
		adoptPlantCandidate(
			plantInputs(current, networkChanged),
			hardware,
			products,
			choice,
		),
	);
	assert.equal(adopted.equipment_plant_requirements, undefined);
	assert.equal(
		equipmentDraft(readPlantDraft(current).units[0]!.inputs)
			.inverter_product_id,
		null,
	);
	assert.equal(
		equipmentDraft(readPlantDraft(adopted).units[0]!.inputs)
			.inverter_product_id,
		1,
	);
	assert.throws(() =>
		adoptPlantCandidate(current, hardware, products.slice(0, 1), choice),
	);
	const changed = readPlantDraft(current);
	changed.units[0]!.inputs = {
		equipment_setup: {
			...equipmentDraft(changed.units[0]!.inputs),
			required_usable_kwh: 1,
		},
	};
	assert.throws(() =>
		adoptPlantCandidate(
			plantInputs(current, changed),
			hardware,
			products,
			choice,
		),
	);
});

test("device observations retain exact versions and distinct plant nodes through Draft undo and editable preparation", () => {
	const plant = compilePlant(configured(), products);
	const inputs: JsonObject = {
		...plantInputs(start(), configured()),
		equipment_plant: plant,
	};
	const targets = equipmentConditionTargets(inputs, products);
	const a = targets.find(
		(d) =>
			d.selection_ref.kind === "plant_unit" && d.selection_ref.unit_id === "a",
	)!;
	const b = targets.find(
		(d) =>
			d.selection_ref.kind === "plant_unit" && d.selection_ref.unit_id === "b",
	)!;
	assert.equal(a.product_id, b.product_id);
	assert.equal(
		targets.filter((d) => d.selection_ref.kind === "plant_controller").length,
		1,
	);
	assert.equal(
		inputs.equipment_condition_inputs,
		undefined,
		"reading old input never adds an optional object",
	);
	let observed = changeDeviceCondition(
		inputs,
		a,
		{ declared_firmware: "001.02-A", source_note: "  commissioning record  " },
		products,
	);
	observed = changeDeviceCondition(
		observed,
		b,
		{ declared_firmware: "01.2-A" },
		products,
	);
	const declarations = readEquipmentConditionInputs(
		observed.equipment_condition_inputs,
	);
	assert.equal(
		declarations.devices[0]!.declared_model,
		null,
		"Woo reference is never copied as an observation",
	);
	assert.equal(declarations.devices[0]!.declared_firmware, "001.02-A");
	assert.equal(
		declarations.devices[0]!.source_note,
		"  commissioning record  ",
	);
	assert.equal(declarations.devices[1]!.declared_firmware, "01.2-A");
	const editable = plantInputs(observed, readPlantDraft(observed));
	assert.deepEqual(
		editable.equipment_condition_inputs,
		observed.equipment_condition_inputs,
	);
	assert.equal(
		conditionBindingMatches(
			declarations.devices[0]!,
			equipmentConditionTargets(editable, products)[0]!,
		),
		true,
	);
	assert.deepEqual(
		equipmentContext(editable).equipment_condition_inputs,
		declarations,
	);
	const changedRevision = products.map((p) =>
		p.id === a.product_id ? { ...p, product_revision: "a".repeat(64) } : p,
	);
	assert.equal(
		conditionBindingMatches(
			declarations.devices[0]!,
			equipmentConditionTargets(editable, changedRevision)[0]!,
		),
		false,
	);
	assert.throws(
		() =>
			changeDeviceCondition(
				editable,
				equipmentConditionTargets(editable, changedRevision)[0]!,
				{ source_note: "new" },
				changedRevision,
			),
		/product_evidence_changed/,
	);
	assert.throws(() =>
		readEquipmentConditionInputs({
			schema_version: 1,
			devices: [declarations.devices[0], declarations.devices[0]],
		}),
	);
	const cleared = changeDeviceCondition(
		observed,
		a,
		{ declared_firmware: " " },
		products,
	);
	assert.equal(
		readEquipmentConditionInputs(cleared.equipment_condition_inputs).devices[0]!
			.declared_firmware,
		null,
	);
	assert.equal(
		readEquipmentConditionInputs(
			removeDeviceCondition(observed, declarations.devices[0]!)
				.equipment_condition_inputs,
		).devices.length,
		1,
	);
	const project: Project = {
		id: "a".repeat(32),
		title: "Fixture",
		revision: 1,
		input_sha256: "b".repeat(64),
		inputs,
	};
	assert.deepEqual(
		undoDraft(editDraft(beginDraft(project), observed)).history.current,
		inputs,
	);
});
