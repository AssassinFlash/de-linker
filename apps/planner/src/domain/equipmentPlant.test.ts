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
import type { Project } from "../data/protocol.ts";

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
