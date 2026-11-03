import assert from "node:assert/strict";
import { test } from "node:test";
import { changeEquipment, equipmentDraft } from "./equipment.ts";
import { beginDraft, editDraft, undoDraft } from "./draft.ts";

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
	const changed = next.history.current.equipment_setup as Record<string, unknown>;
	assert.equal(changed.pv_dc_kw, 220);
	assert.equal(changed.required_usable_kwh, 61.4);
	assert.equal(changed.operating_mode, "grid_connected");
	// Undo returns to the unchanged baseline inputs.
	const undone = undoDraft(next);
	assert.deepEqual(undone.history.current.equipment_setup, emptySetup());
});
