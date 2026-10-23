import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { GeographicBridge, horizontalOnRoof } from "./geographic.ts";
import type { GeographicReference } from "./geographic.ts";
import type { RoofFace, Vec3 } from "./geometry.ts";

const fixture = JSON.parse(
	readFileSync(
		new URL(
			"../../../../fixtures/planning/geographic-proj-reference.json",
			import.meta.url,
		),
		"utf8",
	),
) as {
	cases: {
		name: string;
		reference: GeographicReference;
		points: { geodetic: Vec3; enu: Vec3; inverse: Vec3 }[];
	}[];
};
const close = (
	actual: readonly number[],
	expected: readonly number[],
	tolerances: readonly number[],
) => {
	actual.forEach((value, axis) =>
		assert.ok(
			Math.abs(value - expected[axis]!) <= tolerances[axis]!,
			`${axis}: ${value} != ${expected[axis]}`,
		),
	);
};

test("browser ECEF/ENU matches frozen independent PROJ positions and full inverse", () => {
	for (const { reference, points } of fixture.cases) {
		const bridge = new GeographicBridge(reference);
		for (const point of points) {
			// Arithmetic parity budgets, never site/measurement accuracy.
			close(bridge.forward(point.geodetic), point.enu, [2e-8, 2e-8, 2e-8]);
			close(bridge.inverse(point.enu), point.inverse, [1e-11, 1e-11, 2e-8]);
		}
	}
});

test("horizontal-only zero is explicit and never an inferred measured height", () => {
	const reference: GeographicReference = {
			...fixture.cases[0]!.reference,
			ellipsoid_height_m: 0,
			height_basis: "zero_height_horizontal_convention",
		},
		bridge = new GeographicBridge(reference);
	assert.throws(() => bridge.forward([7, 51, 4]), /horizontal_height/);
	assert.throws(
		() => new GeographicBridge({ ...reference, ellipsoid_height_m: 4 }),
		/reference_invalid/,
	);
	for (const point of [
		[200, 0, 0],
		[0, 91, 0],
		[NaN, 0, 0],
	] as Vec3[])
		assert.throws(() => bridge.forward(point));
	assert.throws(() => bridge.inverse([0, Infinity, 0]));
	const before = bridge.forward([6.9601, 50.9401, 0]);
	reference.longitude_deg = 10;
	assert.deepEqual(bridge.forward([6.9601, 50.9401, 0]), before);
});

test("horizontal footprint is lifted onto a 3-4-5 plane before roof UV projection", () => {
	const roof: RoofFace = {
		id: "roof",
		name: "Synthetic 3-4-5 plane",
		source_id: "source",
		origin_enu: [2, 3, 10],
		u_axis_enu: [1, 0, 0],
		v_axis_enu: [0, 0.8, -0.6],
		boundary_uv: [
			[0, 0],
			[10, 0],
			[10, 10],
			[0, 10],
		],
		holes_uv: [],
	};
	close(horizontalOnRoof(roof, [5, 7]), [3, 5], [1e-12, 1e-12]);
	assert.throws(
		() => horizontalOnRoof({ ...roof, v_axis_enu: [0, 0, -1] }, [5, 7]),
		/projection_invalid/,
	);
});
