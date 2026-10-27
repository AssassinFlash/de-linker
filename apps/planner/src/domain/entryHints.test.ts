import test from "node:test";
import assert from "node:assert/strict";
import { readEntryHints, entryInputs } from "./entryHints.ts";
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
