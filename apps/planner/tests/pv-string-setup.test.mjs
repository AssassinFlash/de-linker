import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { setupDom, enter } from "./dom-fixture.mjs";
import { beginDraft, editDraft, undoDraft } from "../src/domain/draft.ts";
import { PlantPvStringSetup } from "../src/components/equipment/PlantPvStringSetup.tsx";
import { equipmentDraft } from "../src/domain/equipment.ts";
import { readPvPlantStringPlan } from "../src/domain/pvPlantStrings.ts";
import { PvStringSetup } from "../src/components/equipment/PvStringSetup.tsx";
import { panelPoses } from "../src/domain/panelPoses.ts";
import fixture from "./fixtures/index.ts";

async function setup(
	t,
	{
		rows = 2,
		columns = 3,
		secondArray = false,
		secondArrayName = "West array",
		strings = [],
		locale = "en-GB",
	} = {},
) {
	const dom = setupDom();
	const project = structuredClone(fixture.geometric_pv.project);
	const geometry = project.inputs.geometry;
	geometry.roofs[0].boundary_uv = [
		[0, 0],
		[40, 0],
		[40, 40],
		[0, 40],
	];
	geometry.arrays[0] = {
		...geometry.arrays[0],
		rows,
		columns,
		excluded_slots: [],
		name: "East array",
	};
	if (secondArray)
		geometry.arrays.push({
			...geometry.arrays[0],
			id: "second_array",
			name: secondArrayName,
			origin_uv: [20, 0],
		});
	if (typeof strings === "function")
		strings = strings(panelPoses(geometry).filter((pose) => pose.included));
	project.inputs.pv_string_plan = {
		schema_version: 1,
		inverter_product_id: 1,
		minimum_ambient_c: null,
		temperature_source: null,
		strings,
	};
	let current = beginDraft(project),
		api,
		accept = true;
	const { createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	function Harness() {
		const [draft, setDraft] = useState(current);
		api = {
			draft,
			undo() {
				current = undoDraft(current);
				setDraft(current);
			},
			alter(operation) {
				current = editDraft(current, operation(current.history.current));
				setDraft(current);
			},
			setAccept: (value) => {
				accept = value;
			},
		};
		return React.createElement(PvStringSetup, {
			draft,
			inverterId: 1,
			locale,
			disabled: false,
			onValidity() {},
			edit(operation) {
				if (!accept) return false;
				current = editDraft(current, operation(current.history.current));
				setDraft(current);
				return true;
			},
		});
	}
	t.after(() => dom.dispose(root));
	await act(async () => root.render(React.createElement(Harness)));
	return {
		get plan() {
			return current.history.current.pv_string_plan;
		},
		get api() {
			return api;
		},
		modules: panelPoses(geometry).filter((p) => p.included),
	};
}
const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(el) => el.textContent.trim() === text,
	);
const field = (text) =>
	[...document.querySelectorAll("label")]
		.find((el) => el.querySelector("span")?.textContent.trim() === text)
		?.querySelector("input");
const click = async (el) => {
	assert.ok(el);
	await act(async () => el.click());
};

test("available modules identify their actual array even when rows and columns repeat", async (t) => {
	await setup(t, { secondArray: true });
	const choices = [...document.querySelectorAll('input[type="checkbox"]')];
	assert.equal(choices.length, 12);
	assert.match(
		choices[0].closest("label").textContent,
		/Array 1.*East array.*row 1.*module 1/,
	);
	assert.match(
		choices[6].closest("label").textContent,
		/Array 2.*West array.*row 1.*module 1/,
	);
});

test("96 modules can be assigned in explicit groups while the customer chooses every MPPT input", async (t) => {
	const r = await setup(t, { rows: 8, columns: 12 });
	await click(button("Select all available modules"));
	await enter(field("Modules to add to this string"), "16");
	await enter(field("MPPT"), "1");
	await enter(field("Inverter input"), "1");
	for (let i = 0; i < 6; i++) {
		if (i) await enter(field("MPPT"), String(i + 1));
		const add = button("Add selected modules to string");
		assert.equal(add.disabled, false);
		await click(add);
		assert.deepEqual(
			r.plan.strings[i].module_ids,
			r.modules.slice(i * 16, (i + 1) * 16).map((p) => p.id),
		);
		assert.equal(r.plan.strings[i].mppt, i + 1);
		assert.equal(r.plan.strings[i].input, 1);
		assert.equal(
			field("MPPT").value,
			String(i + 1),
			"a new MPPT is never inferred",
		);
		assert.equal(button("Add selected modules to string").disabled, true);
	}
	assert.equal(new Set(r.plan.strings.flatMap((s) => s.module_ids)).size, 96);
});

test("editing keeps string identity and its explicit order, and retains changes when applying is refused", async (t) => {
	const r = await setup(t, {
		strings: (modules) => [
			{
				id: "keep",
				mppt: 1,
				input: 1,
				module_ids: [modules[2].id, modules[0].id],
			},
			{ id: "occupied", mppt: 2, input: 1, module_ids: [modules[3].id] },
		],
	});
	const original = structuredClone(r.plan);
	await click(button("Edit string"));
	assert.equal(document.activeElement.textContent, "Edit string 1");
	const checks = [...document.querySelectorAll('input[type="checkbox"]')];
	assert.equal(
		checks[0].disabled,
		false,
		"this string's own modules are editable",
	);
	assert.equal(
		checks[3].disabled,
		true,
		"another string's module stays occupied",
	);
	await enter(field("MPPT"), "2");
	assert.equal(button("Save string changes").disabled, true);
	assert.match(document.body.textContent, /already has a string/);
	await enter(field("MPPT"), "1");
	await click(button("Reverse order"));
	r.api.setAccept(false);
	await click(button("Save string changes"));
	assert.deepEqual(r.plan, original);
	assert.match(document.body.textContent, /selection is still available/);
	assert.equal(button("Save string changes").disabled, false);
	r.api.setAccept(true);
	await click(button("Save string changes"));
	assert.deepEqual(r.plan.strings[0], {
		...original.strings[0],
		module_ids: [...original.strings[0].module_ids].reverse(),
	});
	assert.deepEqual(r.plan.strings[1], original.strings[1]);
	await act(async () => r.api.undo());
	assert.deepEqual(
		r.plan,
		original,
		"the normal project history restores the exact ordered string",
	);
});

test("cancelling a re-edit restores a staged new string rather than changing saved wiring", async (t) => {
	const r = await setup(t, {
		strings: (modules) => [
			{ id: "keep", mppt: 1, input: 1, module_ids: [modules[0].id] },
		],
	});
	await click(document.querySelectorAll('input[type="checkbox"]')[1]);
	await enter(field("MPPT"), "3");
	await enter(field("Inverter input"), "2");
	const original = structuredClone(r.plan);
	await click(button("Edit string"));
	await click(button("Select all available modules"));
	await click(button("Cancel editing"));
	assert.deepEqual(r.plan, original);
	assert.equal(field("MPPT").value, "3");
	assert.equal(field("Inverter input").value, "2");
	assert.equal(
		document.querySelectorAll('input[type="checkbox"]')[1].checked,
		true,
	);
	await click(button("Add selected modules to string"));
	assert.deepEqual(r.plan.strings[1].module_ids, [r.modules[1].id]);
	assert.equal(r.plan.strings[1].mppt, 3);
});

test("invalid staged quantity stays intact before switching to a saved string", async (t) => {
	for (const [locale, raw] of [
		["en-GB", "1x"],
		["de-DE", ","],
	]) {
		await t.test(locale, async (t) => {
			const r = await setup(t, {
				locale,
				strings: (modules) => [
					{ id: "keep", mppt: 1, input: 1, module_ids: [modules[0].id] },
				],
			});
			const original = structuredClone(r.plan);
			await click(button("Select all available modules"));
			await enter(field("Modules to add to this string"), raw);
			assert.equal(
				field("Modules to add to this string").getAttribute("aria-invalid"),
				"true",
			);
			assert.equal(button("Edit string").disabled, true);
			await click(button("Edit string"));
			assert.equal(field("Modules to add to this string").value, raw);
			assert.equal(
				field("Modules to add to this string").getAttribute("aria-invalid"),
				"true",
			);
			assert.deepEqual(r.plan, original);
			await enter(field("Modules to add to this string"), "2");
			assert.equal(button("Edit string").disabled, false);
			await click(button("Edit string"));
			await click(button("Cancel editing"));
			assert.equal(field("Modules to add to this string").value, "2");
		});
	}
});

test("a roof edit cannot silently drop selected modules or rewrite a string changed elsewhere", async (t) => {
	const r = await setup(t, {
		strings: (modules) => [
			{ id: "keep", mppt: 1, input: 1, module_ids: [modules[0].id] },
		],
	});
	await click(document.querySelectorAll('input[type="checkbox"]')[1]);
	await enter(field("MPPT"), "3");
	await enter(field("Inverter input"), "1");
	await act(async () =>
		r.api.alter((inputs) => ({
			...inputs,
			geometry: {
				...inputs.geometry,
				arrays: inputs.geometry.arrays.map((array) => ({
					...array,
					excluded_slots: ["0:1"],
				})),
			},
		})),
	);
	assert.equal(button("Add selected modules to string").disabled, true);
	assert.match(document.body.textContent, /missing or already assigned/);
	await click(button("Remove unavailable modules from selection"));
	await click(button("Edit string"));
	await act(async () =>
		r.api.alter((inputs) => ({
			...inputs,
			pv_string_plan: {
				...inputs.pv_string_plan,
				strings: inputs.pv_string_plan.strings.map((string) => ({
					...string,
					input: 2,
				})),
			},
		})),
	);
	assert.equal(button("Save string changes").disabled, true);
	assert.match(document.body.textContent, /changed while you were editing/);
	await click(button("Cancel editing"));
	assert.equal(r.plan.strings[0].input, 2);
});

test("row/column ordering and individual moves affect only the reviewed string sequence", async (t) => {
	const r = await setup(t);
	await click(button("Select all available modules"));
	await click(button("Order by columns"));
	await enter(field("MPPT"), "1");
	await enter(field("Inverter input"), "1");
	const firstLabel = document
		.querySelector('[aria-label^="Move "][aria-label$=" later"]')
		.getAttribute("aria-label");
	assert.match(firstLabel, /row 1.*module 1/);
	await click(
		document.querySelector('[aria-label^="Move "][aria-label$=" later"]'),
	);
	await click(button("Add selected modules to string"));
	const order = [3, 0, 1, 4, 2, 5].map((index) => r.modules[index].id);
	assert.deepEqual(r.plan.strings[0].module_ids, order);
});

test("two inverter editors keep independent selections, destinations and occupied module ownership", async (t) => {
	const dom = setupDom();
	const project = structuredClone(fixture.geometric_pv.project);
	project.inputs.geometry.arrays[0].columns = 3;
	const modules = panelPoses(project.inputs.geometry).filter(
		(pose) => pose.included,
	);
	const units = [1, 2].map((id) => ({
		id: `unit_${id}`,
		name: `Inverter ${id}`,
		inputs: {
			equipment_setup: { ...equipmentDraft({}), inverter_product_id: id },
		},
	}));
	const plan = (index) => ({
		schema_version: 1,
		inverter_product_id: index + 1,
		minimum_ambient_c: null,
		temperature_source: null,
		strings: [
			{ id: `s_${index}`, mppt: 1, input: 1, module_ids: [modules[index].id] },
		],
	});
	project.inputs.pv_plant_string_plan = {
		schema_version: 1,
		units: units.map((unit, index) => ({
			unit_id: unit.id,
			inverter_instance_id: null,
			plan: plan(index),
		})),
	};
	let current = beginDraft(project),
		changeUnit;
	const { createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	function Harness() {
		const [draft, setDraft] = useState(current),
			[index, setIndex] = useState(0);
		changeUnit = setIndex;
		return React.createElement(PlantPvStringSetup, {
			draft,
			unit: units[index],
			units,
			locale: "en-GB",
			disabled: false,
			onValidity() {},
			edit(operation) {
				current = editDraft(current, operation(current.history.current));
				setDraft(current);
				return true;
			},
		});
	}
	t.after(() => dom.dispose(root));
	await act(async () => root.render(React.createElement(Harness)));
	let checks = [...document.querySelectorAll('input[type="checkbox"]')];
	assert.equal(checks[1].disabled, true);
	assert.match(
		checks[1].closest("label").textContent,
		/Assigned to system Inverter 2/,
	);
	await click(checks[2]);
	await enter(field("MPPT"), "2");
	await enter(field("Inverter input"), "3");
	await act(async () => changeUnit(1));
	checks = [...document.querySelectorAll('input[type="checkbox"]')];
	assert.equal(
		checks[2].checked,
		false,
		"an uncommitted selection does not move to another inverter",
	);
	assert.equal(field("MPPT").value, "");
	assert.equal(field("Inverter input").value, "");
	assert.equal(checks[0].disabled, true);
	assert.match(
		checks[0].closest("label").textContent,
		/Assigned to system Inverter 1/,
	);
	await click(button("Edit string"));
	assert.equal(checks[1].disabled, false);
	await click(button("Reverse order"));
	await enter(field("Inverter input"), "2");
	const before = structuredClone(
		current.history.current.pv_plant_string_plan.units[0],
	);
	await click(button("Save string changes"));
	const saved = readPvPlantStringPlan(
		current.history.current.pv_plant_string_plan,
	);
	assert.deepEqual(
		saved.units.find((unit) => unit.unit_id === units[0].id),
		before,
	);
	const updated = saved.units.find((unit) => unit.unit_id === units[1].id);
	assert.equal(updated.plan.inverter_product_id, 2);
	assert.equal(updated.plan.strings[0].id, "s_1");
	assert.equal(updated.plan.strings[0].input, 2);
	assert.deepEqual(updated.plan.strings[0].module_ids, [modules[1].id]);
});

test("duplicate array names retain distinct bulk actions and target module identities", async (t) => {
	const r = await setup(t, {
		secondArray: true,
		secondArrayName: "East array",
	});
	const actions = [
		...document.querySelectorAll(
			'[aria-label^="Select available modules in "]',
		),
	];
	assert.match(actions[0].getAttribute("aria-label"), /Array 1.*East array/);
	assert.match(actions[1].getAttribute("aria-label"), /Array 2.*East array/);
	await click(actions[1]);
	await enter(field("MPPT"), "1");
	await enter(field("Inverter input"), "1");
	await click(button("Add selected modules to string"));
	assert.deepEqual(
		r.plan.strings[0].module_ids,
		r.modules.slice(6).map((pose) => pose.id),
	);
});

test("removing the edited string or wiring plan leaves no stale destination or editor", async (t) => {
	const r = await setup(t, {
		strings: (modules) => [
			{ id: "keep", mppt: 1, input: 1, module_ids: [modules[0].id] },
		],
	});
	await click(button("Edit string"));
	await click(button("Remove string"));
	assert.equal(button("Save string changes"), undefined);
	assert.equal(r.plan.strings.length, 0);
	await enter(field("MPPT"), "4");
	await enter(field("Inverter input"), "2");
	await click(button("Remove wiring plan"));
	assert.equal(r.plan, undefined);
	await click(button("Set up PV strings"));
	assert.equal(field("MPPT").value, "");
	assert.equal(field("Inverter input").value, "");
	assert.equal(button("Add selected modules to string").disabled, true);
});
