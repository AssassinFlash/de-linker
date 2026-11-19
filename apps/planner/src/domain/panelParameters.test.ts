import assert from "node:assert/strict";
import test from "node:test";
import {
	panelLabel,
	panelFields,
	panelSpecification,
	emptyPanelFields,
} from "./panelParameters.ts";
import {
	isCurrentRoofModule,
	resolveModuleParameters,
} from "./productModules.ts";

test("an empty panel entry stays unknown and cannot place a panel", () => {
	assert.equal(panelSpecification("new-panel", emptyPanelFields()), null);
});
test("roof placement uses the supplied dimensions and watts without manufacturing a temperature coefficient", () => {
	const spec = panelSpecification("new-panel", {
		length: "1860",
		width: "1120",
		thickness: "32",
		power: "437",
		coefficient: "",
	});
	assert.ok(spec);
	assert.equal(spec.length_m, 1.86);
	assert.equal(spec.width_m, 1.12);
	assert.equal(spec.thickness_m, 0.032);
	assert.equal(spec.stc_power_w, 437);
	assert.equal(spec.source.woo, undefined);
	assert.equal(spec.gamma_pdc_per_c, null);
	assert.equal(isCurrentRoofModule(spec), true);
	assert.equal(resolveModuleParameters(spec), undefined);
	assert.equal(panelLabel(spec), "437 Wp · 1860 × 1120 mm");
});
test("a measured temperature coefficient is optional and retains its units", () => {
	const spec = panelSpecification("declared", {
		length: "1855",
		width: "1100",
		thickness: "30",
		power: "440",
		coefficient: "-0.28",
	});
	assert.ok(spec);
	assert.equal(resolveModuleParameters(spec)?.gamma_pdc_per_c, -0.28 / 100);
});

test("electrical values round-trip only when explicitly supplied", () => {
	const values = {
		...emptyPanelFields(),
		length: "1800",
		width: "1100",
		thickness: "32",
		power: "430",
		electrical: {
			voc_v: "42",
			alpha_isc_pct_per_c: "0.04",
			beta_voc_pct_per_c: "-0.25",
			isc_a: "",
			cell_technology: "Mono-Si",
		},
	};
	const spec = panelSpecification("panel", values);
	assert.ok(spec);
	assert.deepEqual(spec.electrical, {
		voc_v: 42,
		alpha_isc_pct_per_c: 0.04,
		beta_voc_pct_per_c: -0.25,
		cell_technology: "Mono-Si",
	});
	assert.deepEqual(panelSpecification("panel", panelFields(spec)), spec);
	assert.equal(
		panelSpecification("panel", { ...values, electrical: { isc_a: "-1" } }),
		null,
	);
});
