import assert from "node:assert/strict";
import test from "node:test";
import imported from "../../../../fixtures/planning/geometry-import-asset.json" with { type: "json" };
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import { readGeometry } from "./validateGeometry.ts";
import {
	startMapFeatureDraft,
	readMapFeatureDraft,
} from "./mapFeatureDraft.ts";
import type { MapFeatureDraft, MapFeatureTarget } from "./mapFeatureDraft.ts";
import {
	appendMapDrawingVertex,
	editMapDrawingVertex,
	mapDrawingDraftCommand,
	mapDrawingReviewTarget,
	mapDrawingVertices,
	readMapDrawingDraft,
} from "./mapDrawingDraft.ts";
import { applyGeometryCommand } from "./geometryCommands.ts";
import { mapPolygon } from "./mapDrawingGeometry.ts";

const geometry = readGeometry(
		imported.metadata.geometry_import.geometry,
		policy,
	),
	roof = geometry.roofs[0]!;
const points = [
	[6.96001, 50.94001],
	[6.96003, 50.94001],
	[6.96003, 50.94003],
	[6.96002, 50.94002],
	[6.96001, 50.94003],
] as const;
function raw(kind: MapFeatureTarget["kind"]): MapFeatureDraft {
	let value = startMapFeatureDraft(imported.project_id, geometry, "de-DE", {
		kind,
		roof_id: roof.id,
	});
	for (const point of points)
		value = appendMapDrawingVertex(value, point) as MapFeatureDraft;
	return {
		...value,
		phase: "staged",
		fields: {
			...value.fields,
			name: kind === "hole" ? "" : "Synthetic feature",
			height: kind === "obstacle" ? "1,25" : "",
			axis: kind === "obstacle" ? "vertical" : "",
			reason: kind === "keepout" ? "Synthetic test-only zone" : "",
			source_confirmed: true,
		},
	};
}
for (const kind of ["hole", "obstacle", "keepout"] as const) {
	test(`${kind} prefix reload, explicit command and independent journal identity preserve source/plane and other objects`, () => {
		let prefix = startMapFeatureDraft(imported.project_id, geometry, "de-DE", {
			kind,
			roof_id: roof.id,
		});
		for (const point of points) {
			const before = prefix.vertices;
			prefix = readMapFeatureDraft(
				JSON.parse(JSON.stringify(appendMapDrawingVertex(prefix, point))),
			);
			assert.deepEqual(prefix.vertices.slice(0, -1), before);
			assert.equal(prefix.fields.source_confirmed, false);
		}
		assert.throws(() => mapDrawingDraftCommand(prefix));
		const draft = raw(kind),
			result = applyGeometryCommand(geometry, mapDrawingDraftCommand(draft));
		assert.deepEqual(result.sources, geometry.sources);
		assert.deepEqual(result.coordinate_system, geometry.coordinate_system);
		assert.deepEqual(result.roofs[0]!.origin_enu, roof.origin_enu);
		assert.deepEqual(result.roofs[0]!.u_axis_enu, roof.u_axis_enu);
		assert.deepEqual(result.roofs[0]!.v_axis_enu, roof.v_axis_enu);
		assert.deepEqual(result.roofs[0]!.boundary_uv, roof.boundary_uv);
		if (kind === "hole") {
			assert.deepEqual(result.roofs[0]!.holes_uv.slice(0, -1), roof.holes_uv);
			assert.equal(result.roofs[0]!.holes_uv.at(-1)!.length, 5);
			assert.deepEqual(result.obstacles, geometry.obstacles);
			assert.deepEqual(result.keepouts, geometry.keepouts);
		} else {
			assert.deepEqual(result.roofs, geometry.roofs);
			const feature =
				kind === "obstacle"
					? result.obstacles.at(-1)!
					: result.keepouts.at(-1)!;
			assert.equal(feature.id, draft.object_id);
			assert.equal(feature.source_id, roof.source_id);
			assert.equal(feature.footprint_uv.length, 5);
			if (kind === "obstacle") {
				assert.equal(result.obstacles.at(-1)!.height_m, 1.25);
				assert.deepEqual(
					result.obstacles.at(-1)!.extrusion_axis_enu,
					[0, 0, 1],
				);
			} else
				assert.equal(
					result.keepouts.at(-1)!.reason,
					"Synthetic test-only zone",
				);
		}
		const prepared = { ...draft, prepared_geometry: result };
		assert.deepEqual(
			readMapDrawingDraft(JSON.parse(JSON.stringify(prepared))),
			prepared,
		);
		const fork = readMapFeatureDraft({ ...draft, key: crypto.randomUUID() });
		assert.deepEqual(
			mapDrawingDraftCommand(fork),
			mapDrawingDraftCommand(draft),
		);
		const target = mapDrawingReviewTarget(draft);
		assert.equal(target.roof, roof.id);
		assert.equal(target.id, kind === "hole" ? roof.id : draft.object_id);
		assert.throws(
			() =>
				applyGeometryCommand(
					{ ...geometry, roofs: [] },
					mapDrawingDraftCommand(draft),
				),
			/frame_changed/,
		);
	});
}
test("a feature vertex edit, prefix continuation and removal invalidate the source declaration and prepared result", () => {
	const draft = raw("obstacle"),
		result = applyGeometryCommand(geometry, mapDrawingDraftCommand(draft));
	const ring = [...draft.vertices];
	ring[1] = [ring[1]![0] + 0.000001, ring[1]![1]];
	const edited = editMapDrawingVertex(
		{ ...draft, prepared_geometry: result },
		mapPolygon([...ring].reverse()),
		"dragCoordinate",
	) as MapFeatureDraft;
	assert.equal(edited.fields.source_confirmed, false);
	assert.equal(edited.prepared_geometry, null);
	assert.equal(edited.object_id, draft.object_id);
	assert.deepEqual(edited.vertices[0], draft.vertices[0]);
	assert.deepEqual(edited.vertices[2], draft.vertices[2]);
	const shorter = mapDrawingVertices(
		draft,
		draft.vertices.slice(0, -1),
	) as MapFeatureDraft;
	assert.equal(shorter.fields.source_confirmed, false);
	assert.equal(shorter.prepared_geometry, null);
	const collecting = { ...shorter, phase: "collecting" as const };
	assert.deepEqual(readMapFeatureDraft(collecting), collecting);
	assert.throws(
		() => appendMapDrawingVertex(collecting, collecting.vertices[0]),
		/duplicate_vertex/,
	);
});
test("strict feature recovery rejects unknown fields, target/source replacement, cross-kind properties and forged prepared output", () => {
	const draft = raw("obstacle"),
		hole = raw("hole"),
		result = applyGeometryCommand(geometry, mapDrawingDraftCommand(draft));
	for (const value of [
		{ ...draft, schema_version: 3.1 },
		{ ...draft, sdk: true },
		{ ...draft, target: { ...draft.target, id: "extra" } },
		{ ...draft, target: { ...draft.target, roof_id: "missing" } },
		{ ...draft, object_id: "keepout_" + "a".repeat(32) },
		{ ...draft, fields: { ...draft.fields, axis: "guessed" } },
		{ ...draft, fields: { ...draft.fields, source_id: "missing" } },
		{ ...draft, fields: { ...draft.fields, name: "x".repeat(4097) } },
		{ ...draft, fields: { ...draft.fields, reason: "unrelated" } },
		{ ...hole, object_id: draft.object_id },
		{ ...hole, fields: { ...hole.fields, name: "hidden" } },
		{ ...draft, phase: "collecting" },
		{ ...draft, prepared_geometry: geometry },
		{
			...draft,
			fields: { ...draft.fields, source_confirmed: false },
			prepared_geometry: result,
		},
	])
		assert.throws(() => readMapFeatureDraft(value));
});
test("obstacle properties require a positive locale-correct height and an explicit direction", () => {
	const draft = raw("obstacle");
	for (const height of ["", "0", "-1", "1.25", "1,2,3", "NaN", "1e309"])
		assert.throws(
			() =>
				mapDrawingDraftCommand({
					...draft,
					fields: { ...draft.fields, height },
				}),
			(error) => (error as { field: string }).field === "height",
		);
	assert.throws(
		() =>
			mapDrawingDraftCommand({
				...draft,
				fields: { ...draft.fields, axis: "" },
			}),
		(error) => (error as { field: string }).field === "axis",
	);
	assert.throws(
		() =>
			mapDrawingDraftCommand({
				...draft,
				fields: { ...draft.fields, axis: "guessed" as "vertical" },
			}),
		(error) => (error as { field: string }).field === "axis",
	);
	const result = applyGeometryCommand(
		geometry,
		mapDrawingDraftCommand({
			...draft,
			fields: { ...draft.fields, axis: "normal" },
		}),
	);
	assert.notDeepEqual(result.obstacles.at(-1)!.extrusion_axis_enu, [0, 0, 1]);
	const restricted = {
		...geometry,
		sources: geometry.sources.map((source) => ({
			...source,
			permissions: { ...source.permissions, export: "prohibited" as const },
		})),
	};
	const next = applyGeometryCommand(
		restricted,
		mapDrawingDraftCommand({ ...draft, before: restricted }),
	);
	assert.deepEqual(next.sources, restricted.sources);
});
