import assert from "node:assert/strict";
import test from "node:test";
import type { Vec2 } from "./geometry.ts";
import { reconcileMapVertex } from "./mapRingEdit.ts";
import type { MapRing } from "./mapRingEdit.ts";

function arrangements<T>(points: readonly T[]): T[][] {
	return [points, [...points].reverse()].flatMap((ring) =>
		ring.map((_, at) => [...ring.slice(at), ...ring.slice(0, at)]),
	);
}
function fixture(n = 6): MapRing {
	return {
		metric: Array.from({ length: n }, (_, at) => [at + 0.123456789, at / 7]),
		geographic: Array.from({ length: n }, (_, at) => [at, at * at + 1]),
	};
}

test("every winding/start-index arrangement changes only the one moved metric vertex", () => {
	const before = fixture(),
		changed: Vec2 = [100, 200],
		projected: Vec2 = [123.456, 987.654];
	for (let index = 0; index < before.metric.length; index++) {
		const ring = before.geographic.map((point, at) =>
			at === index ? changed : point,
		);
		for (const after of arrangements(ring)) {
			let projections = 0;
			const result = reconcileMapVertex(
				before,
				after,
				"dragCoordinate",
				(p) => {
					assert.equal(p, changed);
					projections++;
					return projected;
				},
			);
			assert.equal(projections, 1);
			for (let at = 0; at < result.metric.length; at++) {
				assert.equal(
					result.metric[at],
					at === index ? projected : before.metric[at],
				);
				assert.equal(
					result.geographic[at],
					at === index ? changed : before.geographic[at],
				);
			}
		}
	}
});

test("insertions at every edge and reversed winding preserve the canonical first vertex and exact old points", () => {
	const before = fixture(),
		inserted: Vec2 = [100, 200],
		projected: Vec2 = [3.75, 4.25];
	for (let edge = 0; edge < before.metric.length; edge++) {
		const ring = [...before.geographic];
		ring.splice(edge + 1, 0, inserted);
		for (const after of arrangements(ring)) {
			let projections = 0;
			const result = reconcileMapVertex(before, after, "insertMidpoint", () => {
				projections++;
				return projected;
			});
			assert.equal(projections, 1);
			assert.equal(result.metric[edge + 1], projected);
			assert.equal(result.metric[0], before.metric[0]);
			assert.deepEqual(
				result.metric.filter((_, at) => at !== edge + 1),
				before.metric,
			);
			before.metric.forEach((point) =>
				assert.ok(result.metric.includes(point)),
			);
		}
	}
});

test("deletions and no-op winding changes perform no inverse projection", () => {
	const before = fixture();
	const forbidden = () => {
		throw new Error("must not reproject an unchanged point");
	};
	for (const after of arrangements(before.geographic))
		assert.equal(
			reconcileMapVertex(before, after, "dragCoordinate", forbidden),
			before,
		);
	for (let index = 0; index < before.metric.length; index++)
		for (const after of arrangements(
			before.geographic.filter((_, at) => at !== index),
		)) {
			const result = reconcileMapVertex(
				before,
				after,
				"deleteCoordinate",
				forbidden,
			);
			assert.deepEqual(
				result.metric,
				before.metric.filter((_, at) => at !== index),
			);
			result.metric.forEach((point) =>
				assert.ok(before.metric.includes(point)),
			);
		}
});

test("a midpoint insertion followed by a drag still preserves every original UV point", () => {
	const before = fixture(),
		afterInsert = [...before.geographic],
		midpoint: Vec2 = [100, 200],
		dragged: Vec2 = [101, 201];
	afterInsert.splice(2, 0, midpoint);
	const inserted = reconcileMapVertex(
		before,
		[...afterInsert].reverse(),
		"insertMidpoint",
		() => [4, 5],
	);
	const afterDrag = afterInsert.map((point) =>
			point === midpoint ? dragged : point,
		),
		result = reconcileMapVertex(
			inserted,
			[...afterDrag.slice(3), ...afterDrag.slice(0, 3)],
			"dragCoordinate",
			() => [6, 7],
		);
	assert.deepEqual(result.metric[2], [6, 7]);
	before.metric.forEach((point) => assert.ok(result.metric.includes(point)));
});

test("ambiguous display identity, unrelated mutations, crossings and too-small deletion are refused", () => {
	const before = fixture(),
		forbidden = () => {
			throw new Error("refusal must precede projection");
		};
	for (const [after, action] of [
		[[[100, 200], [101, 201], ...before.geographic.slice(2)], "dragCoordinate"],
		[
			[
				before.geographic[0]!,
				before.geographic[2]!,
				before.geographic[1]!,
				...before.geographic.slice(3),
			],
			"dragCoordinate",
		],
		[
			[...before.geographic.slice(0, -1), before.geographic[0]!],
			"dragCoordinate",
		],
		[[...before.geographic, [100, 200]], "dragCoordinate"],
		[before.geographic.slice(0, -1), "insertMidpoint"],
	] as const)
		assert.throws(
			() => reconcileMapVertex(before, after, action, forbidden),
			/map_vertex_/,
		);
	assert.throws(
		() =>
			reconcileMapVertex(
				fixture(3),
				fixture(3).geographic.slice(0, 2),
				"deleteCoordinate",
				forbidden,
			),
		/action_mismatch/,
	);
	assert.throws(
		() =>
			reconcileMapVertex(
				{
					...before,
					geographic: [
						...before.geographic.slice(0, -1),
						before.geographic[0]!,
					],
				},
				before.geographic,
				"dragCoordinate",
				forbidden,
			),
		/identity_ambiguous/,
	);
});

test("the resource-bound ring remains linear in projection work", () => {
	const before = fixture(20_000),
		after = [...before.geographic];
	after[10_000] = [-1, -2];
	let projections = 0;
	const result = reconcileMapVertex(
		before,
		[...after].reverse(),
		"dragCoordinate",
		() => {
			projections++;
			return [1, 2];
		},
	);
	assert.equal(projections, 1);
	assert.equal(result.metric.length, 20_000);
	assert.equal(result.metric[19_999], before.metric[19_999]);
});
