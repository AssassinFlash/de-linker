import assert from "node:assert/strict";
import { test } from "node:test";
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import { emptyGeometry } from "./geometryCommands.ts";
import { readGeometry } from "./validateGeometry.ts";
import {
	DEFAULT_MODULE_TIER,
	MODULE_TIERS,
	moduleSpecFromTier,
	tierFor,
} from "./moduleTiers.ts";

const MILLIMETRES: readonly (readonly [number, number, number])[] = [
	[400, 1722, 1134],
	[450, 1762, 1134],
	[500, 1960, 1134],
	[550, 2278, 1134],
	[600, 2384, 1303],
];

test("five tiers cover the expected power classes with unique identities", () => {
	assert.deepEqual(
		MODULE_TIERS.map((tier) => tier.stc_power_w),
		[400, 450, 500, 550, 600],
	);
	assert.equal(
		new Set(MODULE_TIERS.map((tier) => tier.id)).size,
		MODULE_TIERS.length,
	);
	for (const [power, length, width] of MILLIMETRES) {
		const tier = MODULE_TIERS.find((item) => item.stc_power_w === power)!;
		assert.equal(
			Math.round(tier.length_m * 1000),
			length,
			`${power} Wp length`,
		);
		assert.equal(Math.round(tier.width_m * 1000), width, `${power} Wp width`);
	}
});

test("the default tier is 450 Wp and every tier resolves to itself", () => {
	assert.equal(DEFAULT_MODULE_TIER.stc_power_w, 450);
	for (const tier of MODULE_TIERS)
		assert.equal(tierFor(tier.stc_power_w), tier);
	assert.equal(tierFor(450), DEFAULT_MODULE_TIER);
	// The 450 tier keeps the footprint of the reference module this list
	// replaces (1762 × 1134 mm, 460 Wp), so reopening a draft moves only the
	// nameplate power and leaves the saved roof layout unchanged.
	assert.equal(Math.round(DEFAULT_MODULE_TIER.length_m * 1000), 1762);
	assert.equal(Math.round(DEFAULT_MODULE_TIER.width_m * 1000), 1134);
});

test("a nearby declared power resolves to the nearest tier", () => {
	// The retired 460 Wp reference module and other off-tier nameplates.
	assert.equal(tierFor(460).stc_power_w, 450);
	assert.equal(tierFor(437).stc_power_w, 450);
	assert.equal(tierFor(428).stc_power_w, 450);
	assert.equal(tierFor(380).stc_power_w, 400);
	assert.equal(tierFor(620).stc_power_w, 600);
	assert.equal(tierFor(Number.NaN), DEFAULT_MODULE_TIER);
	assert.equal(tierFor(0), DEFAULT_MODULE_TIER);
	assert.equal(tierFor(-10), DEFAULT_MODULE_TIER);
});

test("planning values stay physically plausible and internally consistent", () => {
	for (const tier of MODULE_TIERS) {
		const watts = tier.stc_power_w,
			label = `${watts} Wp`;
		for (const value of [
			tier.length_m,
			tier.width_m,
			tier.thickness_m,
			tier.voc_v,
			tier.vmp_v,
			tier.isc_a,
			tier.imp_a,
		])
			assert.ok(Number.isFinite(value) && value > 0, `${label} positive`);
		assert.ok(tier.length_m > tier.width_m, `${label} portrait orientation`);
		assert.ok(tier.voc_v > tier.vmp_v, `${label} Voc above Vmp`);
		assert.ok(tier.isc_a > tier.imp_a, `${label} Isc above Imp`);
		assert.ok(
			Math.abs(tier.vmp_v * tier.imp_a - watts) <= 3,
			`${label} MPP product`,
		);
		assert.ok(
			tier.gamma_pdc_per_c < -0.002 && tier.gamma_pdc_per_c > -0.005,
			`${label} temperature coefficient`,
		);
	}
});

test("a tier never pretends to be a maintained product or a datasheet", () => {
	for (const tier of MODULE_TIERS) {
		assert.equal(tier.source.kind, "declared_reference");
		assert.match(tier.source.source_note, /unverified planning assumption/);
		assert.match(tier.source.source_note, /not a Linker product/);
		const spec = moduleSpecFromTier(tier, tier.id);
		assert.equal(spec.source.kind, "user_declared");
		assert.equal(spec.source.woo, undefined);
		assert.equal(spec.source.url, null);
		assert.equal(spec.source.document_sha256, null);
		assert.match(spec.source.note, /^declared_reference/);
		assert.deepEqual(
			readGeometry({ ...emptyGeometry(), module_specs: [spec] }, policy)
				.module_specs,
			[spec],
		);
	}
});

test("the projection keeps the declared identity and dimensions", () => {
	const spec = moduleSpecFromTier(DEFAULT_MODULE_TIER, "module_abc");
	assert.equal(spec.id, "module_abc");
	assert.equal(spec.stc_power_w, 450);
	assert.equal(spec.length_m, 1.762);
	assert.equal(spec.width_m, 1.134);
	assert.equal(spec.model, DEFAULT_MODULE_TIER.model);
});
