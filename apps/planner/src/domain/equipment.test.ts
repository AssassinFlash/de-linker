import assert from "node:assert/strict";
import { test } from "node:test";
import {
	changeEquipment,
	compileEquipment,
	equipmentDraft,
} from "./equipment.ts";
import { beginDraft, editDraft, undoDraft } from "./draft.ts";
import { ApiError } from "../data/protocol.ts";
import type { JsonObject } from "../data/protocol.ts";
import type { EquipmentProduct } from "../data/equipmentProducts.ts";

const products: EquipmentProduct[] = [
	{
		id: 101,
		canonical_product_id: 101,
		product_revision: "6".repeat(64),
		model: "ESS 5K",
		brand: "Linker",
		device_class: "hybrid_inverter",
		figures: { ac_output_kw_nominal: 5 },
	},
	{
		id: 102,
		canonical_product_id: 102,
		product_revision: "7".repeat(64),
		model: "BAT 10",
		brand: "Linker",
		device_class: "battery",
		figures: { module_energy_kwh_usable: 10 },
	},
];

const savedRequirements = {
	schema_version: 1,
	grid_phase: 3,
	operating_mode: "grid_connected",
	pv_dc_kw: 200,
	required_usable_kwh: 61.4,
	required_discharge_ac_kw: 100,
};

const emptySetup = () => ({
	schema_version: 1,
	inverter_product_id: null,
	battery_product_id: null,
	modules_per_stack: null,
	parallel_stacks: null,
	accessory_product_ids: [],
	grid_phase: null,
	operating_mode: null,
	pv_dc_kw: null,
	required_usable_kwh: null,
	required_discharge_ac_kw: null,
});

test("an all-null equipment_setup row falls through to saved requirements", () => {
	const setup = equipmentDraft({
		equipment_setup: emptySetup(),
		equipment_requirements: { ...savedRequirements },
	});
	assert.equal(setup.pv_dc_kw, 200);
	assert.equal(setup.required_usable_kwh, 61.4);
	assert.equal(setup.required_discharge_ac_kw, 100);
	assert.equal(setup.grid_phase, 3);
	assert.equal(setup.operating_mode, "grid_connected");
	assert.equal(setup.inverter_product_id, null);
});

test("a valued equipment_setup row still wins over requirements", () => {
	const row = {
		...emptySetup(),
		pv_dc_kw: 130,
		grid_phase: 1,
	};
	const setup = equipmentDraft({
		equipment_setup: row,
		equipment_requirements: { ...savedRequirements },
	});
	assert.equal(setup.pv_dc_kw, 130);
	assert.equal(setup.grid_phase, 1);
	assert.equal(setup.required_usable_kwh, null);
});

test("editing a backfilled draft keeps the backfilled values", () => {
	const draft = beginDraft({
		id: "1".repeat(32),
		title: "Fixture",
		revision: 2,
		input_sha256: "2".repeat(64),
		inputs: {
			equipment_setup: emptySetup(),
			equipment_requirements: { ...savedRequirements },
		},
	});
	const next = editDraft(
		draft,
		changeEquipment(draft.history.current, { pv_dc_kw: 220 }),
	);
	const changed = next.history.current.equipment_setup as Record<
		string,
		unknown
	>;
	assert.equal(changed.pv_dc_kw, 220);
	assert.equal(changed.required_usable_kwh, 61.4);
	assert.equal(changed.operating_mode, "grid_connected");
	// Undo returns to the unchanged baseline inputs.
	const undone = undoDraft(next);
	assert.deepEqual(undone.history.current.equipment_setup, emptySetup());
});

test("a backfilled draft never carries requirements-only fields into the setup row", () => {
	// `application` belongs to equipment_requirements; the selection schema
	// rejects unknown properties, so a draft that keeps it fails at
	// compileEquipment (measured 2026-11-15 on saved projects).
	const draft = equipmentDraft({
		equipment_requirements: { ...savedRequirements, application: "commercial" },
	});
	assert.equal("application" in draft, false);
	const persisted = changeEquipment(draft, { pv_dc_kw: 220 });
	const row = persisted.equipment_setup as Record<string, unknown>;
	assert.equal("application" in row, false);
	assert.equal(row.pv_dc_kw, 220);
	assert.equal(row.inverter_product_id, null);
});

test("a polluted saved setup row is sanitized before it reaches the selection schema", () => {
	// Rows written before the fix keep `application` in equipment_setup;
	// reopening such a project must still compile a valid selection.
	const row = {
		...emptySetup(),
		inverter_product_id: 101,
		grid_phase: 3,
		operating_mode: "grid_connected" as const,
		application: "commercial",
	};
	const draft = equipmentDraft({ equipment_setup: row });
	assert.equal("application" in draft, false);
	const selection = compileEquipment(draft, products);
	assert.equal(selection.inverter_product_id, 101);
	assert.equal(selection.battery_product_id, null);
	assert.equal(selection.product_revisions["101"], "6".repeat(64));
});

test("an equipment_use plan travels with the setup row into the compiled selection", () => {
	const row = {
		...emptySetup(),
		inverter_product_id: 101,
		battery_product_id: 102,
		grid_phase: 3,
		operating_mode: "grid_connected" as const,
		equipment_use: { inverter: "retain", battery: "replace" },
	};
	const draft = equipmentDraft({ equipment_setup: row });
	assert.deepEqual(draft.equipment_use, {
		inverter: "retain",
		battery: "replace",
	});
	const selection = compileEquipment(draft, products);
	// Retained and replaced parts keep their product identity and revisions;
	// only the purchase list differs.
	assert.equal(selection.inverter_product_id, 101);
	assert.equal(selection.battery_product_id, 102);
	assert.deepEqual(selection.equipment_use, {
		inverter: "retain",
		battery: "replace",
	});
});

test("a battery-less row may only declare a new battery use", () => {
	const row = {
		...emptySetup(),
		inverter_product_id: 101,
		grid_phase: 3,
		operating_mode: "grid_connected" as const,
		equipment_use: { inverter: "new", battery: "new" },
	};
	assert.equal(
		compileEquipment(equipmentDraft({ equipment_setup: row }), products)
			.battery_product_id,
		null,
	);
	for (const battery of ["retain", "replace"] as const) {
		assert.throws(
			() =>
				compileEquipment(
					equipmentDraft({
						equipment_setup: {
							...row,
							equipment_use: { inverter: "new", battery },
						},
					}),
					products,
				),
			(error: unknown) =>
				error instanceof ApiError &&
				error.code === "equipment_selection_incomplete",
		);
	}
});

test("an invalid use plan is rejected like any other invalid row", () => {
	const row = {
		...emptySetup(),
		inverter_product_id: 101,
		grid_phase: 3,
		operating_mode: "grid_connected" as const,
		equipment_use: { inverter: "keep", battery: "new" },
	};
	assert.throws(
		() => equipmentDraft({ equipment_setup: row }),
		(error: unknown) =>
			error instanceof ApiError &&
			error.code === "equipment_selection_incomplete",
	);
});

test("editing a draft keeps its declared use plan", () => {
	const inputs: JsonObject = {
		equipment_setup: {
			...emptySetup(),
			inverter_product_id: 101,
			grid_phase: 3,
			operating_mode: "grid_connected" as const,
			equipment_use: { inverter: "retain", battery: "new" },
		},
	};
	const persisted = changeEquipment(inputs, { pv_dc_kw: 220 });
	const row = persisted.equipment_setup as Record<string, unknown>;
	assert.deepEqual(row.equipment_use, { inverter: "retain", battery: "new" });
	assert.equal(row.pv_dc_kw, 220);
});
