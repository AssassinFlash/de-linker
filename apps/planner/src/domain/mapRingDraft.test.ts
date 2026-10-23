import assert from "node:assert/strict";
import test from "node:test";
import imported from "../../../../fixtures/planning/geometry-import-asset.json" with { type: "json" };
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import { readGeometry } from "./validateGeometry.ts";
import { applyGeometryCommand } from "./geometryCommands.ts";
import {
	mapPolygon,
	quantizeMapPosition,
	bindMapRing,
} from "./mapDrawingGeometry.ts";
import type { MapRingTarget } from "./mapDrawingGeometry.ts";
import {
	readMapDrawingDraft,
	editMapDrawingVertex,
	mapDrawingDraftCommand,
} from "./mapDrawingDraft.ts";
import {
	startMapRingDraft,
	readMapRingDraft,
	mapRingTargets,
} from "./mapRingDraft.ts";

const original = readGeometry(
		imported.metadata.geometry_import.geometry,
		policy,
	),
	roof = original.roofs[0]!,
	source = original.sources[0]!;
// Synthetic input metadata, not a measured accuracy or installation prescription.
const geometry = readGeometry(
	{
		...original,
		sources: original.sources.map((value) =>
			value.id === source.id
				? {
						...value,
						spatial_precision_m: 0.002,
						permissions: { ...value.permissions, export: "prohibited" },
					}
				: value,
		),
		obstacles: [
			{
				id: "map_ring_obstacle",
				name: "Synthetic obstacle",
				source_id: source.id,
				roof_id: roof.id,
				footprint_uv: [
					[0.2, 0.2],
					[0.8, 0.2],
					[0.8, 0.8],
				],
				extrusion_axis_enu: [0, 0, 1],
				height_m: 1.25,
			},
		],
		keepouts: [
			{
				id: "map_ring_keepout",
				name: "Synthetic exclusion",
				source_id: source.id,
				roof_id: roof.id,
				footprint_uv: [
					[1, 1],
					[1.4, 1],
					[1.4, 1.4],
				],
				reason: "Synthetic test constraint",
			},
		],
	},
	policy,
);
const targets: MapRingTarget[] = [
	{ kind: "roof_boundary", roof_id: roof.id },
	{ kind: "roof_hole", roof_id: roof.id, index: 0 },
	{ kind: "obstacle", id: "map_ring_obstacle" },
	{ kind: "keepout", id: "map_ring_keepout" },
];
const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

test("every existing ring restores paired coordinates and applies only its explicit target with original source/plane facts", () => {
	for (const target of targets) {
		const start = startMapRingDraft(
			imported.project_id,
			geometry,
			"de-DE",
			target,
		);
		assert.equal(start.source_confirmed, false);
		assert.throws(() => mapDrawingDraftCommand(start), /confirmation_required/);
		assert.deepEqual(readMapDrawingDraft(copy(start)), start);
		const ring = [...start.vertices];
		ring[1] = quantizeMapPosition([ring[1]![0] + 0.000001, ring[1]![1]]);
		const edited = editMapDrawingVertex(
			start,
			mapPolygon([...ring].reverse()),
			"dragCoordinate",
		);
		assert.equal(edited.schema_version, 2);
		if (edited.schema_version !== 2) throw new Error("unexpected operation");
		const restored = readMapRingDraft(
				copy({ ...edited, source_confirmed: true }),
			),
			command = mapDrawingDraftCommand(restored),
			result = applyGeometryCommand(geometry, command),
			actual = bindMapRing(result, target).ring.metric;
		for (const [index, value] of start.metric_vertices.entries())
			if (index !== 1) assert.deepEqual(actual[index], value);
		assert.notDeepEqual(actual[1], start.metric_vertices[1]);
		assert.deepEqual(result.sources, geometry.sources);
		assert.equal(result.sources[0]!.permissions.export, "prohibited");
		assert.deepEqual(result.coordinate_system, geometry.coordinate_system);
		assert.deepEqual(result.roofs[0]!.origin_enu, roof.origin_enu);
		assert.deepEqual(result.roofs[0]!.u_axis_enu, roof.u_axis_enu);
		assert.deepEqual(result.roofs[0]!.v_axis_enu, roof.v_axis_enu);
		assert.deepEqual(result.arrays, geometry.arrays);
		if (target.kind !== "roof_hole")
			assert.deepEqual(result.roofs[0]!.holes_uv, roof.holes_uv);
		if (target.kind !== "roof_boundary")
			assert.deepEqual(result.roofs[0]!.boundary_uv, roof.boundary_uv);
		if (target.kind !== "obstacle")
			assert.deepEqual(result.obstacles, geometry.obstacles);
		else {
			assert.deepEqual(result.obstacles[0]!.extrusion_axis_enu, [0, 0, 1]);
			assert.equal(result.obstacles[0]!.height_m, 1.25);
		}
		if (target.kind !== "keepout")
			assert.deepEqual(result.keepouts, geometry.keepouts);
		else assert.equal(result.keepouts[0]!.reason, "Synthetic test constraint");
		assert.throws(
			() =>
				applyGeometryCommand(
					{
						...geometry,
						sources: geometry.sources.map((value) => ({
							...value,
							calibration_note: "changed input",
						})),
					},
					command,
				),
			/frame_changed/,
		);
	}
	assert.deepEqual(original, imported.metadata.geometry_import.geometry);
});
test("insert/move/remove recovery retains original metric points and resets the source declaration on a new change", () => {
	const start = {
		...startMapRingDraft(imported.project_id, geometry, "en-GB", targets[1]!),
		source_confirmed: true,
	};
	const midpoint = quantizeMapPosition([
		(start.vertices[0]![0] + start.vertices[1]![0]) / 2,
		(start.vertices[0]![1] + start.vertices[1]![1]) / 2,
	]);
	let draft = editMapDrawingVertex(
		start,
		mapPolygon([start.vertices[0]!, midpoint, ...start.vertices.slice(1)]),
		"insertMidpoint",
	);
	assert.equal(draft.schema_version, 2);
	if (draft.schema_version !== 2) throw new Error("unexpected operation");
	assert.equal(draft.source_confirmed, false);
	draft = readMapRingDraft(copy(draft));
	const moved = [...draft.vertices];
	moved[1] = quantizeMapPosition([moved[1]![0] + 0.000001, moved[1]![1]]);
	draft = readMapRingDraft(
		copy(editMapDrawingVertex(draft, mapPolygon(moved), "dragCoordinate")),
	);
	draft = readMapRingDraft(
		copy(
			editMapDrawingVertex(
				draft,
				mapPolygon(draft.vertices.filter((_, index) => index !== 1)),
				"deleteCoordinate",
			),
		),
	);
	assert.deepEqual(draft.vertices, start.vertices);
	assert.deepEqual(draft.metric_vertices, start.metric_vertices);
	assert.deepEqual(
		applyGeometryCommand(
			geometry,
			mapDrawingDraftCommand({ ...draft, source_confirmed: true }),
		),
		geometry,
	);
});
test("untrusted rings reject unrelated metric pairs, changed targets and forged prepared-result cleanup proofs", () => {
	const start = startMapRingDraft(
		imported.project_id,
		geometry,
		"de-DE",
		targets[0]!,
	);
	const ring = [...start.vertices];
	ring[0] = quantizeMapPosition([ring[0]![0] + 0.000001, ring[0]![1]]);
	const draft = editMapDrawingVertex(start, mapPolygon(ring), "dragCoordinate");
	if (draft.schema_version !== 2) throw new Error("unexpected operation");
	const valid = { ...draft, source_confirmed: true },
		result = applyGeometryCommand(geometry, mapDrawingDraftCommand(valid));
	assert.deepEqual(
		readMapRingDraft(copy({ ...valid, prepared_geometry: result }))
			.prepared_geometry,
		result,
	);
	for (const bad of [
		{ ...draft, phase: "collecting" },
		{ ...draft, target: { ...draft.target, extra: "not admitted" } },
		{ ...draft, target: { kind: "roof_hole", roof_id: roof.id, index: 9000 } },
		{
			...draft,
			metric_vertices: [[12345, 67890], ...draft.metric_vertices.slice(1)],
		},
		{
			...draft,
			vertices: [
				draft.vertices[0],
				draft.vertices[0],
				...draft.vertices.slice(2),
			],
		},
		{ ...valid, prepared_geometry: geometry },
		{ ...draft, prepared_geometry: result },
		{ ...draft, source_confirmed: "yes" },
	])
		assert.throws(() => readMapDrawingDraft(copy(bad)));
});
test("a separate ring copy keeps the edited object's identity and selection offers only real rings", () => {
	const draft = {
			...startMapRingDraft(imported.project_id, geometry, "en-GB", targets[3]!),
			source_confirmed: true,
		},
		fork = readMapRingDraft(copy({ ...draft, key: crypto.randomUUID() }));
	assert.notEqual(fork.key, draft.key);
	assert.deepEqual(fork.target, draft.target);
	assert.deepEqual(mapDrawingDraftCommand(fork), mapDrawingDraftCommand(draft));
	assert.equal(
		mapRingTargets(geometry, roof.id).length,
		roof.holes_uv.length + 1,
	);
	assert.deepEqual(mapRingTargets(geometry, "map_ring_obstacle"), [targets[2]]);
	assert.deepEqual(mapRingTargets(geometry, "map_ring_keepout"), [targets[3]]);
	assert.deepEqual(mapRingTargets(geometry, null), []);
	assert.deepEqual(mapRingTargets(geometry, "unknown"), []);
});
