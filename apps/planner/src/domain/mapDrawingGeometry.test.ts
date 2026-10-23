import assert from "node:assert/strict";
import test from "node:test";
import imported from "../../../../fixtures/planning/geometry-import-asset.json" with { type: "json" };
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import { readGeometry } from "./validateGeometry.ts";
import { applyGeometryCommand } from "./geometryCommands.ts";
import { beginDraft, editDraft, undoDraft, redoDraft } from "./draft.ts";
import { readObject } from "../data/readProtocol.ts";
import {
	bindMapRing,
	editMapVertex,
	mapPolygon,
	mapRingCommand,
	newMapShapeCommand,
	readMapPolygon,
} from "./mapDrawingGeometry.ts";
import type { MapRingTarget } from "./mapDrawingGeometry.ts";
import type { Vec2 } from "./geometry.ts";

const document = readGeometry(
		imported.metadata.geometry_import.geometry,
		policy,
	),
	roof = document.roofs[0]!;

test("a geographic vertex edit keeps every untouched source value and rejects a changed whole frame", () => {
	const binding = bindMapRing(document, {
			kind: "roof_boundary",
			roof_id: roof.id,
		}),
		changed: Vec2 = [
			binding.ring.geographic[1]![0] + 0.000001,
			binding.ring.geographic[1]![1],
		],
		after = [...binding.ring.geographic];
	after[1] = changed;
	const edited = editMapVertex(
			binding,
			mapPolygon([...after].reverse()),
			"dragCoordinate",
		),
		command = mapRingCommand(edited),
		result = applyGeometryCommand(document, command);
	assert.notDeepEqual(result.roofs[0]!.boundary_uv[1], roof.boundary_uv[1]);
	for (const [at, point] of roof.boundary_uv.entries())
		if (at !== 1) assert.deepEqual(result.roofs[0]!.boundary_uv[at], point);
	assert.deepEqual(result.roofs[0]!.holes_uv, roof.holes_uv);
	assert.deepEqual(result.sources, document.sources);
	assert.deepEqual(result.coordinate_system, document.coordinate_system);
	assert.equal(binding.ring.metric[0], edited.ring.metric[0]);
	assert.throws(
		() =>
			applyGeometryCommand(
				{
					...document,
					coordinate_system: {
						...document.coordinate_system,
						north_reference: "user_declared",
					},
				},
				command,
			),
		/geometry_frame_changed/,
	);
	assert.deepEqual(document, imported.metadata.geometry_import.geometry);
});

test("one grouped edit joins existing project undo/redo without replacing unrelated inputs", () => {
	const binding = bindMapRing(document, {
			kind: "roof_hole",
			roof_id: roof.id,
			index: 0,
		}),
		after = [...binding.ring.geographic];
	after[0] = [after[0]![0] + 0.000001, after[0]![1]];
	const edited = editMapVertex(binding, mapPolygon(after), "dragCoordinate"),
		geometry = applyGeometryCommand(document, mapRingCommand(edited)),
		inputs = {
			geometry: readObject(document),
			custom_project_fact: "keep exact",
		},
		baseline = {
			id: "1".repeat(32),
			title: "Synthetic drawing transaction",
			revision: 3,
			input_sha256: "a".repeat(64),
			inputs,
		},
		draft = beginDraft(baseline),
		next = editDraft(draft, { ...inputs, geometry: readObject(geometry) });
	assert.equal(next.history.past.length, 1);
	assert.equal(next.history.current.custom_project_fact, "keep exact");
	assert.deepEqual(undoDraft(next).history.current, inputs);
	assert.deepEqual(
		redoDraft(undoDraft(next)).history.current.geometry,
		geometry,
	);
	assert.throws(
		() =>
			applyGeometryCommand(
				{ ...document, roofs: [{ ...roof, holes_uv: [] }] },
				mapRingCommand(edited),
			),
		/geometry_frame_changed/,
	);
});

test("hole/obstacle/keep-out handles touch only their explicitly bound footprint", () => {
	const extended = readGeometry(
		{
			...document,
			obstacles: [
				{
					id: "opaque_obstacle",
					name: "Synthetic raised object",
					source_id: roof.source_id,
					roof_id: roof.id,
					footprint_uv: [
						[1, 1],
						[2, 1],
						[2, 2],
						[1, 2],
					],
					height_m: 2.75,
					extrusion_axis_enu: [0.6, 0, 0.8],
				},
			],
			keepouts: [
				{
					id: "opaque_keepout",
					name: "Synthetic exclusion",
					source_id: roof.source_id,
					roof_id: roof.id,
					footprint_uv: [
						[3, 3],
						[4, 3],
						[4, 4],
						[3, 4],
					],
					reason: "Recorded test requirement",
				},
			],
		},
		policy,
	);
	for (const target of [
		{ kind: "roof_hole", roof_id: roof.id, index: 0 },
		{ kind: "obstacle", id: "opaque_obstacle" },
		{ kind: "keepout", id: "opaque_keepout" },
	] satisfies MapRingTarget[]) {
		const binding = bindMapRing(extended, target),
			after = [...binding.ring.geographic];
		after[1] = [after[1]![0] + 0.0000001, after[1]![1]];
		const result = applyGeometryCommand(
			extended,
			mapRingCommand(
				editMapVertex(binding, mapPolygon(after), "dragCoordinate"),
			),
		);
		assert.deepEqual(result.sources, extended.sources);
		assert.equal(result.obstacles[0]!.height_m, 2.75);
		assert.deepEqual(result.obstacles[0]!.extrusion_axis_enu, [0.6, 0, 0.8]);
		assert.equal(result.keepouts[0]!.reason, "Recorded test requirement");
		if (target.kind !== "roof_hole")
			assert.deepEqual(result.roofs, extended.roofs);
		if (target.kind !== "obstacle")
			assert.deepEqual(result.obstacles, extended.obstacles);
		if (target.kind !== "keepout")
			assert.deepEqual(result.keepouts, extended.keepouts);
	}
});

test("new shapes need explicit physical fields and use a real sloped plane without deleting original holes", () => {
	const binding = bindMapRing(document, {
			kind: "roof_hole",
			roof_id: roof.id,
			index: 0,
		}),
		polygon = mapPolygon(binding.ring.geographic),
		newRoof = {
			kind: "roof" as const,
			identity: {
				id: "roof_drawn",
				name: "Synthetic sloped drawn face",
				source_id: roof.source_id,
			},
			pitch_deg: (Math.atan2(3, 4) * 180) / Math.PI,
			bearing_deg: 123,
			first_vertex_height_m: 8.125,
		},
		withRoof = applyGeometryCommand(
			document,
			newMapShapeCommand(document, newRoof, polygon),
		);
	assert.equal(withRoof.roofs[1]!.origin_enu[2], 8.125);
	assert.ok(Math.abs(withRoof.roofs[1]!.v_axis_enu[2] + 0.6) < 1e-12);
	assert.deepEqual(withRoof.roofs[0], roof);
	const withHole = applyGeometryCommand(
		document,
		newMapShapeCommand(document, { kind: "hole", roof_id: roof.id }, polygon),
	);
	assert.equal(withHole.roofs[0]!.holes_uv.length, roof.holes_uv.length + 1);
	assert.deepEqual(withHole.roofs[0]!.holes_uv[0], roof.holes_uv[0]);
	for (const pitch of [NaN, -1, 90])
		assert.throws(
			() =>
				newMapShapeCommand(document, { ...newRoof, pitch_deg: pitch }, polygon),
			/plane_invalid/,
		);
	assert.throws(
		() =>
			newMapShapeCommand(
				document,
				{ ...newRoof, identity: { ...newRoof.identity, source_id: "missing" } },
				polygon,
			),
		/source_missing/,
	);
	assert.throws(
		() =>
			newMapShapeCommand(
				document,
				{ ...newRoof, first_vertex_height_m: NaN },
				polygon,
			),
		/plane_invalid/,
	);
});

test("malformed rings, unknown references, collapsed display handles and unsupported precision remain explicit refusals", () => {
	for (const geometry of [
		{
			type: "Polygon",
			coordinates: [
				[
					[0, 0],
					[1, 0],
					[1, 1],
					[0, 1],
				],
			],
		},
		{
			type: "Polygon",
			coordinates: [
				[
					[0, 0],
					[1, 0],
					[1, NaN],
					[0, 0],
				],
			],
		},
		{
			type: "Polygon",
			coordinates: [
				[
					[0, 0],
					[1, 0],
					[1, 86],
					[0, 0],
				],
			],
		},
		{
			type: "Polygon",
			coordinates: [
				[
					[0, 0],
					[1, 0],
					[1, 1],
					[0, 0],
				],
				[[0, 0]],
			],
		},
	])
		assert.throws(() => readMapPolygon(geometry), /map_drawing_/);
	assert.throws(
		() =>
			bindMapRing(document, { kind: "roof_hole", roof_id: roof.id, index: 99 }),
		/target_missing/,
	);
	assert.throws(
		() =>
			bindMapRing(
				{
					...document,
					coordinate_system: {
						...document.coordinate_system,
						north_reference: "unreferenced",
					},
				},
				{ kind: "roof_boundary", roof_id: roof.id },
			),
		/geographic_reference_required/,
	);
	assert.throws(
		() =>
			bindMapRing(
				{
					...document,
					roofs: [
						{
							...roof,
							boundary_uv: [
								[0, 0],
								[1e-12, 0],
								[1, 1],
							],
						},
					],
				},
				{ kind: "roof_boundary", roof_id: roof.id },
			),
		/identity_ambiguous/,
	);
	assert.throws(
		() =>
			bindMapRing(
				{
					...document,
					roofs: [
						{
							...roof,
							boundary_uv: [
								[1e14, 0],
								[1e14 + 20, 0],
								[1e14 + 20, 20],
							],
						},
					],
				},
				{ kind: "roof_boundary", roof_id: roof.id },
			),
		/resolution_unsupported/,
	);
});

test("new obstacle and keep-out commands retain their explicit source, height, axis and requirement", () => {
	const binding = bindMapRing(document, {
			kind: "roof_hole",
			roof_id: roof.id,
			index: 0,
		}),
		polygon = mapPolygon(binding.ring.geographic),
		obstacle = {
			id: "new_obstacle",
			name: "Synthetic drawn obstacle",
			source_id: roof.source_id,
			roof_id: roof.id,
			height_m: 2.75,
			extrusion_axis_enu: [0.6, 0, 0.8] as const,
		},
		keepout = {
			id: "new_keepout",
			name: "Synthetic drawn exclusion",
			source_id: roof.source_id,
			roof_id: roof.id,
			reason: "Recorded test requirement",
		},
		withObstacle = applyGeometryCommand(
			document,
			newMapShapeCommand(
				document,
				{ kind: "obstacle", value: obstacle },
				polygon,
			),
		),
		withKeepout = applyGeometryCommand(
			document,
			newMapShapeCommand(
				document,
				{ kind: "keepout", value: keepout },
				polygon,
			),
		);
	assert.deepEqual(withObstacle.obstacles[0], {
		...obstacle,
		footprint_uv: withObstacle.obstacles[0]!.footprint_uv,
	});
	assert.deepEqual(withKeepout.keepouts[0], {
		...keepout,
		footprint_uv: withKeepout.keepouts[0]!.footprint_uv,
	});
	assert.deepEqual(withObstacle.roofs, document.roofs);
	assert.deepEqual(withKeepout.roofs, document.roofs);
	assert.throws(
		() =>
			newMapShapeCommand(
				document,
				{ kind: "obstacle", value: { ...obstacle, height_m: 0 } },
				polygon,
			),
		/invalid_geometry_document/,
	);
	assert.throws(
		() =>
			newMapShapeCommand(
				document,
				{
					kind: "obstacle",
					value: { ...obstacle, extrusion_axis_enu: [0, 0, 0] },
				},
				polygon,
			),
		/invalid_unit_axis/,
	);
});
