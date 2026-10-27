/** Reconcile one explicit vertex action against its display handle. Library
 * winding/start-index changes never rewrite untouched metric coordinates. */
import type { Vec2 } from "./geometry.ts";

export type MapVertexAction =
	"dragCoordinate" | "insertMidpoint" | "deleteCoordinate";
export interface MapRing {
	readonly metric: readonly Vec2[];
	/** Open display ring, in the same order as metric. Quantisation is display
	 * policy only; these coordinates never replace unchanged metric points. */
	readonly geographic: readonly Vec2[];
}

const key = (point: Vec2) => JSON.stringify(point);
function unique(points: readonly Vec2[]): Map<string, number> {
	const result = new Map<string, number>();
	for (const [index, point] of points.entries()) {
		if (
			point.length !== 2 ||
			!point.every(Number.isFinite) ||
			result.has(key(point))
		)
			throw new Error("map_vertex_identity_ambiguous");
		result.set(key(point), index);
	}
	return result;
}

/** Accept only a cyclic rotation/reversal of the expected indices, in O(n).
 * Every index must remain present exactly once; crossings/permutations are not
 * silently interpreted as a vertex edit. */
function cycle(
	indices: readonly number[],
	expected: readonly number[],
): 1 | -1 {
	if (indices.length !== expected.length || expected.length < 3)
		throw new Error("map_vertex_action_mismatch");
	const position = new Map(expected.map((index, at) => [index, at]));
	if (new Set(indices).size !== indices.length)
		throw new Error("map_vertex_identity_ambiguous");
	let direction: 1 | -1 | null = null;
	for (let at = 0; at < indices.length; at++) {
		const a = position.get(indices[at]!),
			b = position.get(indices[(at + 1) % indices.length]!);
		if (a === undefined || b === undefined)
			throw new Error("map_vertex_action_mismatch");
		const gap = (b - a + expected.length) % expected.length,
			next = gap === 1 ? 1 : gap === expected.length - 1 ? -1 : null;
		if (next === null || (direction !== null && direction !== next))
			throw new Error("map_vertex_action_mismatch");
		direction = next;
	}
	return direction!;
}

export function reconcileMapVertex(
	before: MapRing,
	after: readonly Vec2[],
	action: MapVertexAction,
	/** The old metric point identifies a moved vertex; insertion supplies null. */
	project: (point: Vec2, previous: Vec2 | null) => Vec2,
): MapRing {
	const lookup = unique(before.geographic);
	unique(after);
	if (before.metric.length !== before.geographic.length)
		throw new Error("map_vertex_binding_invalid");
	const n = before.metric.length,
		all = Array.from({ length: n }, (_, index) => index),
		mapping = after.map((point) => lookup.get(key(point)) ?? null),
		unknown = mapping.flatMap((index, at) => (index === null ? [at] : [])),
		present = new Set(mapping.filter((index) => index !== null)),
		missing = all.filter((index) => !present.has(index));
	if (action === "dragCoordinate" && after.length === n) {
		if (unknown.length === 0 && missing.length === 0) {
			cycle(mapping as number[], all);
			return before;
		}
		if (unknown.length !== 1 || missing.length !== 1)
			throw new Error("map_vertex_action_mismatch");
		const target = missing[0]!,
			point = after[unknown[0]!]!,
			indices = mapping.map((index) => index ?? target);
		cycle(indices, all);
		return {
			metric: before.metric.map((uv, at) =>
				at === target ? project(point, before.metric[target]!) : uv,
			),
			geographic: before.geographic.map((value, at) =>
				at === target ? point : value,
			),
		};
	}
	if (
		action === "insertMidpoint" &&
		after.length === n + 1 &&
		unknown.length === 1 &&
		missing.length === 0
	) {
		const at = unknown[0]!,
			direction = cycle(
				mapping.filter((index) => index !== null),
				all,
			),
			previous = mapping[(at + after.length - 1) % after.length]!,
			next = mapping[(at + 1) % after.length]!,
			insertAfter = direction === 1 ? previous : next;
		// Append at the wrap edge, preserving the original first vertex.
		const index = insertAfter + 1,
			point = after[at]!;
		return {
			metric: [
				...before.metric.slice(0, index),
				project(point, null),
				...before.metric.slice(index),
			],
			geographic: [
				...before.geographic.slice(0, index),
				point,
				...before.geographic.slice(index),
			],
		};
	}
	if (
		action === "deleteCoordinate" &&
		after.length === n - 1 &&
		unknown.length === 0 &&
		missing.length === 1
	) {
		const target = missing[0]!;
		cycle(
			mapping as number[],
			all.filter((index) => index !== target),
		);
		return {
			metric: before.metric.filter((_, at) => at !== target),
			geographic: before.geographic.filter((_, at) => at !== target),
		};
	}
	throw new Error("map_vertex_action_mismatch");
}
