import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import imported from "../../../../fixtures/planning/geometry-import-asset.json" with { type: "json" };
import flat from "../../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import { readGeometry } from "./validateGeometry.ts";
import { emptyGeometry } from "./geometryCommands.ts";
import { panelPoses } from "./panelPoses.ts";
import { geographicMapGeometry } from "./mapGeometry.ts";

const original = JSON.parse(
	readFileSync(
		new URL(
			"../../../../fixtures/planning/source-roof-wgs84.geojson",
			import.meta.url,
		),
		"utf8",
	),
) as { geometry: { coordinates: number[][][] } };

test("map rings recover the actual retained original including every opening without editing metric geometry", () => {
	const document = readGeometry(
			imported.metadata.geometry_import.geometry,
			policy,
		),
		before = JSON.stringify(document),
		view = geographicMapGeometry(document),
		roof = view.collection.features[0]!;
	assert.equal(roof.geometry.type, "Polygon");
	if (roof.geometry.type !== "Polygon")
		throw new Error("Expected roof polygon");
	assert.equal(
		roof.geometry.coordinates.length,
		original.geometry.coordinates.length,
	);
	for (const [index, ring] of roof.geometry.coordinates.entries()) {
		const source = original.geometry.coordinates[index]!;
		assert.equal(ring.length, source.length);
		for (const [vertex, point] of ring.entries()) {
			// Arithmetic inverse parity only, not survey/source accuracy.
			assert.ok(Math.abs(point[0]! - source[vertex]![0]!) < 2e-11);
			assert.ok(Math.abs(point[1]! - source[vertex]![1]!) < 2e-11);
		}
		assert.deepEqual(ring[0], ring.at(-1));
		assert.notEqual(ring[0], ring.at(-1), "closing position must be a copy");
	}
	assert.equal(JSON.stringify(document), before);
	roof.geometry.coordinates[0]![0]![0] = 0;
	assert.equal(
		JSON.stringify(document),
		before,
		"renderer mutations cannot edit inputs",
	);
	assert.equal(document.sources[0]!.spatial_precision_m, null);
});

test("map overlays retain opaque object identity, excluded modules and actual extrusion extent", () => {
	const base = readGeometry(structuredClone(flat), policy),
		document = {
			...base,
			coordinate_system: {
				...base.coordinate_system,
				north_reference: "true_north" as const,
				anchor: {
					latitude_deg: 50.94,
					longitude_deg: 6.96,
					source_id: base.sources[0]!.id,
					datum: "EPSG:4326" as const,
				},
			},
			arrays: base.arrays.map((array) => ({
				...array,
				excluded_slots: ["0:0"],
			})),
		},
		poses = panelPoses(document),
		view = geographicMapGeometry(document, poses),
		modules = view.collection.features.filter(
			(f) => f.properties.kind === "module",
		);
	assert.equal(modules.length, poses.length);
	assert.equal(
		modules.filter((f) => !f.properties.included).length,
		document.arrays.length,
	);
	for (const feature of modules) {
		assert.equal(feature.geometry.type, "MultiPolygon");
		if (feature.geometry.type !== "MultiPolygon")
			throw new Error("Expected cuboid");
		assert.equal(feature.geometry.coordinates.length, 6);
		assert.ok(poses.some((pose) => pose.id === feature.properties.object_id));
	}
	const obstacle = {
		id: "opaque:obstacle:with:colons",
		name: "Synthetic extrusion for map extent",
		roof_id: document.roofs[0]!.id,
		source_id: document.sources[0]!.id,
		footprint_uv: [
			[1, 1],
			[2, 1],
			[2, 2],
			[1, 2],
		] as const,
		extrusion_axis_enu: [1, 0, 0] as const,
		height_m: 300,
	};
	const extended = geographicMapGeometry({
		...document,
		obstacles: [...document.obstacles, obstacle],
	});
	assert.ok(extended.bounds![1][0] > view.bounds![1][0]);
	const item = extended.collection.features.find(
		(f) => f.properties.object_id === obstacle.id,
	)!;
	assert.equal(item.properties.kind, "obstacle");
	assert.equal(item.geometry.type, "MultiPolygon");
	assert.equal(item.geometry.coordinates.length, 6);
	assert.deepEqual(
		geographicMapGeometry({
			...document,
			arrays: [...document.arrays].reverse(),
		})
			.collection.features.filter((f) => f.properties.kind === "module")
			.map((f) => f.id)
			.sort(),
		modules.map((f) => f.id).sort(),
	);
});

test("map does not invent geographic north, clamp polar positions or turn empty bounds into zero geometry", () => {
	const empty = emptyGeometry();
	assert.throws(
		() => geographicMapGeometry(empty),
		/geographic_reference_required/,
	);
	const referenced = {
		...empty,
		coordinate_system: {
			...empty.coordinate_system,
			north_reference: "true_north" as const,
			anchor: {
				latitude_deg: 60.1699,
				longitude_deg: 24.9384,
				source_id: "source",
				datum: "EPSG:4326" as const,
			},
		},
	};
	assert.deepEqual(geographicMapGeometry(referenced), {
		collection: { type: "FeatureCollection", features: [] },
		centre: [24.9384, 60.1699],
		bounds: null,
	});
	assert.throws(
		() =>
			geographicMapGeometry({
				...referenced,
				coordinate_system: {
					...referenced.coordinate_system,
					north_reference: "user_declared",
				},
			}),
		/geographic_reference_required/,
	);
	assert.throws(
		() =>
			geographicMapGeometry({
				...referenced,
				coordinate_system: {
					...referenced.coordinate_system,
					anchor: { ...referenced.coordinate_system.anchor, latitude_deg: 86 },
				},
			}),
		/projection_latitude_unsupported/,
	);
});

test("a dateline crossing keeps a short display extent without changing original positions", () => {
	const original = readGeometry(
			imported.metadata.geometry_import.geometry,
			policy,
		),
		document = {
			...original,
			coordinate_system: {
				...original.coordinate_system,
				anchor: {
					...original.coordinate_system.anchor!,
					longitude_deg: 179.999999,
				},
			},
		},
		before = JSON.stringify(document),
		view = geographicMapGeometry(document);
	assert.ok(view.bounds![1][0] > 180);
	assert.ok(view.bounds![1][0] - view.bounds![0][0] < 0.001);
	assert.equal(JSON.stringify(document), before);
});
