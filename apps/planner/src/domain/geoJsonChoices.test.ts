import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { geoJsonChoices } from "./geoJsonChoices.ts";
import { roofPlaneAtVertex } from "./geometryEditing.ts";
import { GeographicBridge, geographicOnRoof } from "./geographic.ts";
import type { GeographicReference } from "./geographic.ts";

const raw = readFileSync(
	new URL(
		"../../../../fixtures/planning/source-roof-wgs84.geojson",
		import.meta.url,
	),
);
const encoded = (value: unknown) => btoa(JSON.stringify(value));

test("selection exposes actual features and polygon parts while retaining holes", () => {
	const source = JSON.parse(raw.toString()),
		shape = source.geometry;
	const content = encoded({
		type: "FeatureCollection",
		features: [
			{ type: "Feature", geometry: { type: "Point", coordinates: [1, 2] } },
			{
				...source,
				geometry: {
					type: "MultiPolygon",
					coordinates: [shape.coordinates, shape.coordinates],
				},
			},
		],
	});
	const choices = geoJsonChoices(content);
	assert.deepEqual(
		choices.map((choice) => [
			choice.featureIndex,
			choice.polygonIndex,
			choice.openingCount,
		]),
		[
			[1, 0, 1],
			[1, 1, 1],
		],
	);
	assert.deepEqual(choices[0]!.firstPoint, [6.96, 50.94]);
	assert.equal(choices[0]!.vertexCount, 10);
});

test("inspection refuses third coordinates, projected CRS, unclosed rings and invalid UTF-8 without repairing bytes", () => {
	for (const modify of [
		(value: { crs?: unknown; geometry: { coordinates: number[][][] } }) => {
			value.crs = {};
		},
		(value: { crs?: unknown; geometry: { coordinates: number[][][] } }) => {
			value.geometry.coordinates[0]![0]!.push(12);
		},
		(value: { crs?: unknown; geometry: { coordinates: number[][][] } }) => {
			value.geometry.coordinates[0]!.pop();
		},
	]) {
		const value = JSON.parse(raw.toString());
		modify(value);
		assert.throws(() => geoJsonChoices(encoded(value)));
	}
	assert.throws(() => geoJsonChoices(btoa(String.fromCharCode(255))));
});

test("a declared relative height stays on the selected geodetic vertex away from the origin", () => {
	const reference: GeographicReference = {
		schema_version: 1,
		method: "wgs84_cart_topocentric_v1",
		longitude_deg: 6.96,
		latitude_deg: 50.94,
		ellipsoid_height_m: 0,
		height_basis: "zero_height_horizontal_convention",
	};
	const bridge = new GeographicBridge(reference),
		vertex = [7.0, 51.0] as const;
	for (const height of [-5, 0, 15]) {
		const plane = roofPlaneAtVertex(reference, vertex, 30, 180, height);
		assert.equal(plane.origin_enu[2], height);
		const position = bridge.inverse(plane.origin_enu);
		assert.ok(Math.abs(position[0] - vertex[0]) < 1e-12);
		assert.ok(Math.abs(position[1] - vertex[1]) < 1e-12);
		const uv = geographicOnRoof(bridge, plane, vertex);
		assert.ok(Math.hypot(...uv) < 1e-8);
	}
});
