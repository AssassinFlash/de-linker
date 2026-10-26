import test from "node:test";
import assert from "node:assert/strict";
import {
	readSavedSolutionSource,
	savedSolutionHints,
	savedSolutionId,
	savedSolutionInputs,
} from "./savedSolution.ts";
import { readBrief } from "./brief.ts";
import { equipmentDraft } from "./equipment.ts";

test("old inputs remain traceable without inferring gross load, location or current equipment", () => {
	const source = readSavedSolutionSource(
		{
			schema_version: 1,
			solution_id: 45,
			title: "Previous project",
			kind: "residential",
			input: {
				locale: "de",
				plz: "50667",
				annual_kwh: 4500,
				pv_kwp: 10.5,
				phase: 3,
				backup: "needed",
				heat_pump: true,
				electric_vehicle: false,
				future_setting: { unchanged: true },
			},
			recorded_items: [{ product_id: 1946, quantity: 1 }],
			source_sha256: "a".repeat(64),
		},
		45,
	);
	const hints = savedSolutionHints(source);
	const inputs = savedSolutionInputs(
		source,
		hints,
		"Original annual figure",
		"Accessory request",
	);
	const brief = readBrief(inputs.brief);
	assert.equal(brief.annual_load.kwh, null);
	assert.equal(brief.site.country_code, null);
	assert.equal(brief.site.latitude, null);
	assert.equal(brief.project_use, "residential");
	assert.equal(hints.invalid, true);
	assert.equal(equipmentDraft(inputs).inverter_product_id, null);
	assert.equal(equipmentDraft(inputs).pv_dc_kw, 10.5);
	assert.deepEqual(
		(inputs.saved_solution_reference as Record<string, unknown>).input,
		source.input,
	);
	const complete = { ...source, input: { ...source.input, heat_pump: false } };
	assert.equal(savedSolutionHints(complete).annualKwh, 4500);
	const unknown = savedSolutionHints({ ...complete, kind: "unknown" });
	assert.equal(unknown.annualKwh, null);
	assert.equal(unknown.pvKw, null);
	assert.equal(unknown.invalid, true);
	assert.equal(
		savedSolutionHints({
			...complete,
			kind: "commercial",
			input: { annual_kwh: {}, phase: true },
		}).invalid,
		true,
	);
	assert.equal(savedSolutionId(new URLSearchParams("saved_solution=45")), 45);
	assert.equal(
		savedSolutionId(new URLSearchParams("saved_solution=45&saved_solution=46")),
		0,
	);
	assert.equal(
		savedSolutionId(new URLSearchParams("saved_solution=45&project=owned")),
		null,
	);
});
