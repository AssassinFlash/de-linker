import assert from "node:assert/strict";
import test from "node:test";
import {
	beginDraft,
	editDraft,
	isDirty,
	undoDraft,
	redoDraft,
} from "./draft.ts";
import {
	authoredCalculationInputs,
	acknowledgeCalculation,
} from "./currentCalculation.ts";
import type { Project } from "../data/protocol.ts";

import {
	authoredDiscoveryInputs,
	projectEquipmentScope,
} from "./currentCalculation.ts";
import { equipmentDraft } from "./equipment.ts";

test("a plant uses its shared operating mode to check all selected inverters", () => {
	const unit = (id: string, operating_mode: string | null) => ({
		id,
		name: id,
		inputs: {
			equipment_setup: {
				...equipmentDraft({}),
				inverter_product_id: 4107,
				operating_mode,
			},
		},
	});
	const plant = (mode: string | null, localMode: string | null) => ({
		equipment_plant_setup: {
			schema_version: 1,
			requirements: { operating_mode: mode },
			units: [unit("main", "grid_connected"), unit("annex", localMode)],
			parallel_groups: [],
		},
	});
	assert.equal(projectEquipmentScope(plant("grid_connected", null)), "system");
	assert.equal(
		projectEquipmentScope(plant(null, "grid_connected")),
		"products",
	);
});

test("equipment discovery preserves explicit application and promotes only missing legacy filters", () => {
	const hardware = {
		schema_version: 1,
		inverter_product_id: 42,
		product_revisions: { "42": "revision" },
	};
	const legacy = {
		schema_version: 1,
		application: "commercial",
		grid_phase: 3,
	};
	assert.deepEqual(
		authoredDiscoveryInputs({
			equipment_selection: hardware,
			equipment_requirements: legacy,
		}),
		{
			equipment_selection: hardware,
			equipment_setup: {
				schema_version: 1,
				inverter_product_id: 42,
				application: "commercial",
			},
		},
	);
	const inputs = {
		equipment_plant_requirements: { old: true },
		energy_replay: { old: true },
		equipment_plant_setup: {
			units: [
				{
					id: "a",
					inputs: {
						equipment_setup: { application: null },
						equipment_requirements: legacy,
					},
				},
				{
					id: "b",
					inputs: {
						equipment_setup: { application: "residential" },
						equipment_requirements: legacy,
					},
				},
			],
		},
	};
	assert.deepEqual(authoredDiscoveryInputs(inputs), {
		equipment_plant_setup: {
			units: [
				{ id: "a", inputs: { equipment_setup: { application: null } } },
				{
					id: "b",
					inputs: { equipment_setup: { application: "residential" } },
				},
			],
		},
	});
	assert.equal(
		inputs.equipment_plant_setup.units[0]!.inputs.equipment_requirements,
		legacy,
	);
});

const project: Project = {
	id: "1".repeat(32),
	title: "Current input calculation",
	revision: 1,
	input_sha256: "2".repeat(64),
	inputs: { note: "first" },
};

test("calculation captures authored inputs without making execution projections editable", () => {
	const inputs = {
		brief: { project_note: "Keep my project" },
		energy_scenario: {
			battery: { usable_window_kwh: 12 },
			battery_binding: { asset_id: "old" },
		},
		energy_replay: { battery_parameters_asset_id: "old" },
		energy_plant: { units: [] },
		energy_plant_setup: {
			units: [
				{
					id: "a",
					settings: {
						source_note: "Declared losses",
						battery_binding: { asset_id: "old-unit" },
					},
				},
			],
		},
		profile_selections: { selected: { gross_load: "my-load" } },
	};
	const captured = authoredCalculationInputs(inputs);
	assert.deepEqual(captured, {
		brief: inputs.brief,
		energy_scenario: { battery: { usable_window_kwh: 12 } },
		energy_plant_setup: {
			units: [{ id: "a", settings: { source_note: "Declared losses" } }],
		},
		profile_selections: inputs.profile_selections,
	});
	assert.equal(inputs.energy_scenario.battery_binding.asset_id, "old");
	assert.deepEqual(authoredCalculationInputs(captured), captured);
});

test("calculation acknowledgement preserves edits made after the captured input and their undo history", () => {
	let draft = editDraft(beginDraft(project), { note: "calculate this" });
	const submitted = authoredCalculationInputs(draft.history.current);
	draft = editDraft(draft, { note: "keep editing" });
	const accepted: Project = {
		...project,
		revision: 2,
		input_sha256: "3".repeat(64),
		inputs: submitted,
	};
	const next = acknowledgeCalculation(draft, 1, submitted, accepted);
	assert.equal(next.baseline, accepted);
	assert.equal(next.history.current.note, "keep editing");
	assert.equal(isDirty(next), true);
	assert.equal(undoDraft(next).history.current.note, "calculate this");
	assert.equal(redoDraft(undoDraft(next)).history.current.note, "keep editing");
});

test("an accepted calculation clears obsolete execution state without adding an editing step", () => {
	const prior = {
		...project,
		inputs: {
			note: "first",
			energy_scenario: { battery_binding: null },
			energy_replay: { old: true },
		},
	};
	const draft = beginDraft(prior);
	const submitted = authoredCalculationInputs(draft.history.current);
	const accepted = {
		...project,
		revision: 2,
		input_sha256: "3".repeat(64),
		inputs: submitted,
	};
	const next = acknowledgeCalculation(draft, 1, submitted, accepted);
	assert.equal(isDirty(next), false);
	assert.equal(next.history.serial, draft.history.serial);
	assert.equal(next.history.past.length, 0);
});

test("unchanged inputs can calculate at the existing revision; late receipts cannot roll back a newer project", () => {
	const draft = beginDraft(project);
	assert.equal(
		isDirty(acknowledgeCalculation(draft, 1, project.inputs, project)),
		false,
	);
	const newer = beginDraft({
		...project,
		revision: 3,
		input_sha256: "4".repeat(64),
		inputs: { note: "newer" },
	});
	assert.equal(
		acknowledgeCalculation(newer, 1, project.inputs, {
			...project,
			revision: 2,
		}),
		newer,
	);
	assert.throws(() =>
		acknowledgeCalculation(draft, 1, project.inputs, {
			...project,
			id: "9".repeat(32),
		}),
	);
	assert.throws(() =>
		acknowledgeCalculation(draft, 1, project.inputs, {
			...project,
			inputs: { note: "not my request" },
		}),
	);
});
