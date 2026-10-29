import test from "node:test";
import assert from "node:assert/strict";
import {
	readEntryHints,
	entryInputs,
	productEntryField,
	placedProduct,
} from "./entryHints.ts";
import { readBrief } from "./brief.ts";
import { equipmentDraft } from "./equipment.ts";

test("historical sizing link becomes reviewed project inputs without assuming a country or approved system", () => {
	const hints = readEntryHints(
		new URLSearchParams(
			"annual_kwh=4500&pv_kwp=10.5&phase=3&backup=needed_accessory_ok&plz=50667&step=roof",
		),
	)!;
	const inputs = entryInputs(
		hints,
		"Carried from link",
		"Accessories permitted",
	);
	const brief = readBrief(inputs.brief),
		equipment = equipmentDraft(inputs);
	assert.equal(brief.annual_load.kwh, 4500);
	assert.equal(brief.annual_load.basis, "user_estimate");
	assert.equal(brief.site.location_label, "50667");
	assert.equal(brief.site.country_code, null);
	assert.equal(equipment.pv_dc_kw, 10.5);
	assert.equal(equipment.grid_phase, 3);
	assert.equal(equipment.operating_mode, "backup");
	assert.equal(equipment.inverter_product_id, null);
	assert.equal(hints.roof, true);
	assert.equal(hints.invalid, false);
});

test("ambiguous and invalid link values are rejected individually and cannot overwrite an existing project", () => {
	const params = new URLSearchParams(
		"pv_kwp=10&pv_kwp=20&annual_kwh=-1&phase=3&plz=broken",
	);
	const hints = readEntryHints(params)!;
	assert.equal(hints.pvKw, null);
	assert.equal(hints.annualKwh, null);
	assert.equal(hints.postalCode, null);
	assert.equal(hints.phase, 3);
	assert.equal(hints.invalid, true);
	params.set("project", "owned-project");
	assert.equal(readEntryHints(params), null);
	assert.equal(readEntryHints(new URLSearchParams()), null);
});

test("a product link is a proposed equipment input, not a roof result or an approval", () => {
	const hints = readEntryHints(
		new URLSearchParams("step=equipment&product=1946"),
	)!;
	assert.equal(hints.equipment, true);
	assert.equal(hints.productId, 1946);
	assert.equal(hints.roof, false);
	assert.equal(hints.invalid, false);
	const inverter = entryInputs(hints, "link", "accessory", {
		id: 1946,
		field: "inverter",
	});
	assert.equal(inverter.equipment_selection, undefined);
	assert.equal(
		(inverter.equipment_setup as { inverter_product_id: number })
			.inverter_product_id,
		1946,
	);
	assert.equal(
		(inverter.equipment_setup as { product_revisions?: unknown })
			.product_revisions,
		undefined,
	);
	const battery = entryInputs(hints, "link", "accessory", {
		id: 1954,
		field: "battery",
	});
	assert.equal(
		(battery.equipment_setup as { battery_product_id: number })
			.battery_product_id,
		1954,
	);
	const accessory = entryInputs(hints, "link", "accessory", {
		id: 2100,
		field: "accessory",
	});
	assert.deepEqual(
		(accessory.equipment_setup as { accessory_product_ids: number[] })
			.accessory_product_ids,
		[2100],
	);
});

test("device class places a current product; unknown classes are not inverters", () => {
	const figures = { ac_output_kw_nominal: { value: 5 } };
	assert.equal(
		productEntryField({ device_class: "inverters", figures: {} }),
		"inverter",
	);
	assert.equal(
		productEntryField({ device_class: "home-storage", figures: {} }),
		"battery",
	);
	assert.equal(
		productEntryField({ device_class: "battery-systems", figures: {} }),
		"battery",
	);
	assert.equal(
		productEntryField({ device_class: "all-in-one-systems", figures }),
		"inverter",
	);
	assert.equal(
		productEntryField({ device_class: "all-in-one-systems", figures: {} }),
		null,
	);
	assert.equal(
		productEntryField({ device_class: "accessories", figures: {} }),
		"accessory",
	);
	assert.equal(
		productEntryField({ device_class: "ems-monitoring", figures: {} }),
		"accessory",
	);
	assert.equal(
		productEntryField({ device_class: "ev-chargers", figures }),
		"accessory",
	);
	assert.equal(productEntryField({ device_class: "unknown", figures }), null);
	assert.equal(productEntryField({ device_class: "meters", figures }), null);
	assert.equal(
		placedProduct([{ id: 1946, device_class: "unknown", figures }], 1946),
		null,
	);
	assert.deepEqual(
		placedProduct([{ id: 1946, device_class: "inverters", figures: {} }], 1946),
		{ id: 1946, field: "inverter" },
	);
	assert.equal(
		placedProduct([{ id: 1946, device_class: "inverters", figures: {} }], 999),
		null,
	);
});

test("equipment without a valid product is not a route, and a stray product is refused", () => {
	const equipment = readEntryHints(new URLSearchParams("step=equipment"))!;
	assert.equal(equipment.equipment, false);
	assert.equal(equipment.productId, null);
	assert.equal(equipment.invalid, true);
	const stray = readEntryHints(new URLSearchParams("step=roof&product=1946"))!;
	assert.equal(stray.roof, true);
	assert.equal(stray.equipment, false);
	assert.equal(stray.productId, null);
	assert.equal(stray.invalid, true);
	const broken = readEntryHints(
		new URLSearchParams("step=equipment&product=1946&product=1947"),
	)!;
	assert.equal(broken.equipment, false);
	assert.equal(broken.productId, null);
	assert.equal(broken.invalid, true);
	const malformed = readEntryHints(
		new URLSearchParams("step=equipment&product=nope"),
	)!;
	assert.equal(malformed.equipment, false);
	assert.equal(malformed.invalid, true);
	assert.equal(
		readEntryHints(new URLSearchParams("step=result"))!.invalid,
		true,
	);
	const zero = readEntryHints(new URLSearchParams("step=equipment&product=0"))!;
	assert.equal(zero.equipment, false);
	assert.equal(zero.invalid, true);
});
