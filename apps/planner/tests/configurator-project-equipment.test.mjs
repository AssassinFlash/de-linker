import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until, enter } from "./dom-fixture.mjs";
import { authoredDiscoveryInputs } from "../src/domain/currentCalculation.ts";
import {
	entryInputs,
	placedProduct,
	readEntryHints,
} from "../src/domain/entryHints.ts";

const scope = "project-equipment";
const catalog = {
	schema_version: 1,
	provider: "woocommerce",
	figure_projection_version: 2,
	compatibility_origin: "woocommerce",
	products: [
		{
			id: 101,
			canonical_product_id: 101,
			product_revision: "a".repeat(64),
			device_class: "inverters",
			model: "Existing 10K",
			brand: "Linker",
			figures: { ac_output_kw_nominal: 10 },
		},
		{
			id: 201,
			canonical_product_id: 201,
			product_revision: "b".repeat(64),
			device_class: "battery-systems",
			model: "Existing Pack",
			brand: "Linker",
			figures: { module_energy_kwh_usable: 3 },
		},
	],
};

const field = (label, root = document) =>
	[...root.querySelectorAll("label")]
		.find((item) => item.firstElementChild.textContent === label)
		?.querySelector("input, select");
const button = (name, root = document) =>
	[...root.querySelectorAll("button")].find(
		(item) => item.textContent === name,
	);
async function choose(label, value, root) {
	const select = field(label, root);
	assert.ok(select, label);
	await act(async () => {
		select.value = value;
		select.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
}
async function mount(t, initial) {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { ProjectEquipment } =
		await import("../src/components/configurator/ProjectEquipment.tsx");
	const { ProjectDetails } =
		await import("../src/components/configurator/ProjectDetails.tsx");
	const root = createRoot(dom.element);
	const cache = new QueryClient();
	let current = initial;
	const client = {
		isCurrentScope: (value) => value === scope,
		async query(path, body, receivedScope) {
			assert.equal(path, "products/current");
			assert.equal(receivedScope, scope);
			return catalog;
		},
	};
	function Harness() {
		const [inputs, setInputs] = useState(initial);
		function edit(operation) {
			current = operation(current);
			setInputs(current);
			return true;
		}
		return React.createElement(ProjectDetails, {
			inputs,
			config: { locale: "en", countries: {} },
			disabled: false,
			edit,
			existingEquipment: React.createElement(ProjectEquipment, {
				inputs,
				client,
				scope,
				disabled: false,
				edit,
			}),
		});
	}
	t.after(async () => {
		await dom.dispose(root);
		cache.clear();
	});
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: cache },
				React.createElement(Harness),
			),
		),
	);
	return () => authoredDiscoveryInputs(current);
}

test("existing equipment is declared through the current product data and carried into named systems", async (t) => {
	const current = await mount(t, {});
	await until(() =>
		field("Inverter or integrated storage system")?.querySelector(
			'option[value="101"]',
		),
	);
	await act(async () => document.querySelector("summary").click());
	assert.equal(document.querySelector("details").open, true);
	assert.ok(
		field("Inverter use").querySelector('option[value="retain"]').disabled,
	);
	await choose("Inverter or integrated storage system", "101");
	await choose("Inverter use", "retain");
	await choose("Battery or storage system", "201");
	await choose("Battery use", "retain");
	await enter(field("Modules per stack"), "3");
	await enter(field("Parallel stacks"), "2");
	assert.equal(current().equipment_setup.inverter_product_id, 101);
	assert.equal(current().equipment_setup.battery_product_id, 201);
	assert.deepEqual(current().equipment_setup.equipment_use, {
		inverter: "retain",
		battery: "retain",
	});
	await act(async () => button("Multiple systems").click());
	assert.equal(current().equipment_setup, undefined);
	const plant = current().equipment_plant_setup;
	assert.equal(plant.units.length, 2);
	assert.equal(plant.units[0].inputs.equipment_setup.inverter_product_id, 101);
	assert.equal(plant.units[0].inputs.equipment_setup.battery_product_id, 201);
	assert.equal(plant.units[0].inputs.equipment_setup.modules_per_stack, 3);
	assert.equal(plant.units[0].inputs.equipment_setup.parallel_stacks, 2);
	assert.deepEqual(plant.units[0].inputs.equipment_setup.equipment_use, {
		inverter: "retain",
		battery: "retain",
	});
	assert.equal(plant.units[1].inputs.equipment_setup.inverter_product_id, null);
	assert.ok(button("Single system").disabled);
	const units = [...document.querySelectorAll("fieldset[data-project-system]")];
	const capacity = (unit) => field("Allocated PV nameplate rating (kWp)", unit);
	assert.ok(capacity(units[0]));
	await enter(capacity(units[0]), "13.8");
	await enter(capacity(units[1]), "9.2");
	assert.deepEqual(
		current().equipment_plant_setup.units.map(
			(u) => u.inputs.equipment_setup.pv_dc_kw,
		),
		[13.8, 9.2],
	);
	await enter(field("System name", units[1]), "Annex");
	assert.equal(current().equipment_plant_setup.units[1].name, "Annex");
	await act(async () => button("Remove system", units[1]).click());
	await act(async () => button("Single system").click());
	assert.equal(current().equipment_plant_setup, undefined);
	assert.equal(current().equipment_setup.battery_product_id, 201);
	assert.equal(current().equipment_setup.equipment_use.inverter, "retain");
});

test("switching to solar makes excluding backup demand and retained storage an explicit choice", async (t) => {
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const { equipmentDraft } = await import("../src/domain/equipment.ts");
	const current = await mount(t, {
		brief: { ...emptyBrief(), system_scope: "new_pv_storage" },
		backup_demand: { schema_version: 1, load_kw: 5, duration_hours: 4 },
		equipment_setup: {
			...equipmentDraft({}),
			inverter_product_id: 101,
			battery_product_id: 201,
			modules_per_stack: 3,
			parallel_stacks: 2,
			grid_phase: 3,
			operating_mode: "backup",
			required_usable_kwh: 30,
			required_discharge_ac_kw: 6,
			equipment_use: { inverter: "retain", battery: "retain" },
		},
	});
	await choose("Planned system", "pv_only");
	assert.equal(current().brief.system_scope, "new_pv_storage");
	assert.equal(current().backup_demand.load_kw, 5);
	assert.equal(field("Battery or storage system").value, "201");
	await act(async () => button("Switch to solar and exclude storage").click());
	assert.equal(current().brief.system_scope, "pv_only");
	assert.equal(current().backup_demand, undefined);
	assert.deepEqual(current().equipment_setup, {
		...equipmentDraft({}),
		inverter_product_id: 101,
		grid_phase: 3,
		operating_mode: "grid_connected",
		equipment_use: { inverter: "retain", battery: "new" },
	});
	assert.equal(field("Battery or storage system"), undefined);
});

test("changing to storage requires confirmation before removing active PV wiring", async (t) => {
	const { emptyBrief } = await import("../src/domain/brief.ts");
	const plan = {
		schema_version: 1,
		inverter_product_id: 101,
		minimum_ambient_c: null,
		temperature_source: null,
		strings: [{ id: "s", mppt: 1, input: 1, module_ids: ["module_1"] }],
	};
	const current = await mount(t, {
		brief: { ...emptyBrief(), system_scope: "new_pv_storage" },
		pv_string_plan: plan,
		shared_dc_energy_run_id: "b".repeat(32),
	});
	await choose("Planned system", "storage_only");
	assert.equal(current().brief.system_scope, "new_pv_storage");
	assert.deepEqual(current().pv_string_plan, plan);
	await act(async () => button("Keep current system").click());
	assert.deepEqual(current().pv_string_plan, plan);
	assert.equal(current().shared_dc_energy_run_id, "b".repeat(32));
	await choose("Planned system", "storage_only");
	await act(async () =>
		button("Switch to storage and remove PV wiring").click(),
	);
	assert.equal(current().brief.system_scope, "storage_only");
	assert.equal(current().pv_string_plan, undefined);
	assert.equal(current().shared_dc_energy_run_id, undefined);
});

test("a product from an entry link is visible and can be replaced or cleared", async (t) => {
	const hints = readEntryHints(
		new URLSearchParams("step=equipment&product_id=101"),
	);
	const initial = entryInputs(
		hints,
		"",
		"",
		placedProduct(catalog.products, 101),
	);
	const current = await mount(t, initial);
	await until(
		() =>
			field("Inverter or integrated storage system")?.selectedOptions[0]
				?.textContent === "Linker Existing 10K",
	);
	assert.equal(document.querySelector("details").open, false);
	assert.match(document.body.textContent, /Linker Existing 10K/);
	await act(async () => document.querySelector("summary").click());
	assert.equal(current().equipment_setup.inverter_product_id, 101);
	await choose("Inverter use", "replace");
	assert.equal(current().equipment_setup.equipment_use.inverter, "replace");
	await choose("Inverter or integrated storage system", "");
	assert.equal(current().equipment_setup.inverter_product_id, null);
	assert.equal(current().equipment_setup.equipment_use, null);
});

test("the declaration survives discovery and the model is only needed for compatibility", async (t) => {
	const current = await mount(t, {});
	assert.equal(document.querySelector("details").open, false);
	const check = (label) =>
		[...document.querySelectorAll("label")]
			.find((item) => item.textContent.trim() === label)
			.querySelector("input[type=checkbox]");
	await act(async () => check("There is an existing system").click());
	await enter(field("Existing system name"), "West barn");
	await enter(field("Existing inverter power (kW)"), "7.5");
	await act(async () => check("Keep the existing inverter").click());
	assert.deepEqual(current().existing_system, {
		schema_version: 1,
		name: "West barn",
		inverter_power_kw: 7.5,
		keep_inverter: true,
	});
	assert.equal(current().equipment_setup, undefined);
	assert.match(
		document.body.textContent,
		/Confirm its model to check equipment compatibility/,
	);
	await act(async () => check("There is an existing system").click());
	assert.equal(current().existing_system, undefined);
});
