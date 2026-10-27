/** Renderer-only rebasing and buffer policy. These limits never decide roof fit. */
import type {
	GeometryDocument,
	PanelPose,
	RoofFace,
	Vec2,
	Vec3,
} from "./geometry.ts";
import { add, dot, scale, toRender, vectorFromRoof } from "./coordinates.ts";
import {
	GeometryPrecisionError,
	requireUvResolution,
} from "./geometryNumerics.ts";
import { panelCornersUVN, panelPositionRelative } from "./panelPoses.ts";

// Internal display policy: at most 10 micrometres of local-coordinate rounding
// on conversion to Float32 buffers. This is not a bound on GPU/survey accuracy.
export const MAX_BUFFER_ROUNDING_M = 1e-5;
// 128 m cells keep each centre near a small local pivot before Float32 conversion.
// A cell is a batching choice, never a maximum roof/array size.
const CELL_M = 128;

export function requireRenderCoordinates(values: readonly number[]): void {
	if (
		values.some(
			(value) =>
				!Number.isFinite(value) ||
				Math.abs(Math.fround(value) - value) > MAX_BUFFER_ROUNDING_M,
		)
	)
		throw new GeometryPrecisionError();
}

export function centredRings(
	boundary: readonly Vec2[],
	holes: readonly (readonly Vec2[])[] = [],
): {
	pivot: Vec2;
	boundary: readonly Vec2[];
	holes: readonly (readonly Vec2[])[];
} {
	const all = [...boundary, ...holes.flat()];
	requireUvResolution(all.flat());
	const us = all.map((point) => point[0]),
		vs = all.map((point) => point[1]);
	const u = Math.min(...us) + (Math.max(...us) - Math.min(...us)) / 2,
		v = Math.min(...vs) + (Math.max(...vs) - Math.min(...vs)) / 2;
	const project = (ring: readonly Vec2[]) => {
		const rounded = new Map<string, string>();
		return ring.map(([x, y]) => {
			const point = [x - u, y - v] as const;
			requireRenderCoordinates(point);
			const key = point.map(Math.fround).join(":"),
				original = point.join(":");
			if (rounded.has(key) && rounded.get(key) !== original)
				throw new GeometryPrecisionError();
			rounded.set(key, original);
			return point;
		});
	};
	return {
		pivot: [u, v],
		boundary: project(boundary),
		holes: holes.map(project),
	};
}

export function panelBatches(
	poses: readonly PanelPose[],
): readonly { key: string; pivot: Vec3; poses: readonly PanelPose[] }[] {
	const batches = new Map<
		string,
		{ key: string; pivot: Vec3; poses: PanelPose[] }
	>();
	for (const pose of poses) {
		const cell = pose.centre_uvn.map((value) => Math.floor(value / CELL_M));
		const key = cell.join(":"),
			pivot = cell.map((value) => (value + 0.5) * CELL_M) as [
				number,
				number,
				number,
			];
		const batch = batches.get(key) ?? { key, pivot, poses: [] };
		batch.poses.push(pose);
		batches.set(key, batch);
		const position = pose.centre_uvn.map(
			(value, index) => value - pivot[index]!,
		);
		if (
			[pose.width_m, pose.length_m, pose.thickness_m].some(
				(value) => Math.fround(value) <= 0,
			)
		)
			throw new GeometryPrecisionError();
		requireRenderCoordinates([
			...position,
			pose.width_m,
			pose.length_m,
			pose.thickness_m,
		]);
	}
	return [...batches.values()];
}

/** Complete scene extent, including the actual extruded obstacle tops. */
export function renderBoundsPoints(
	document: GeometryDocument,
	poses: readonly PanelPose[],
	reference: Vec3,
): readonly Vec3[] {
	const points: Vec3[] = [];
	const append = (roof: RoofFace, point: Vec3) => {
		requireUvResolution(point);
		const relative = add(
			add(roof.origin_enu, scale(reference, -1)),
			vectorFromRoof(roof, point),
		);
		requireUvResolution(relative);
		points.push(toRender(relative));
	};
	for (const roof of document.roofs)
		for (const point of [...roof.boundary_uv, ...roof.holes_uv.flat()])
			append(roof, [...point, 0]);
	for (const pose of poses) {
		const roof = document.roofs.find((roof) => roof.id === pose.roof_id)!;
		panelPositionRelative(pose, roof, reference);
		panelCornersUVN(pose).forEach((point) => append(roof, point));
	}
	for (const object of [...document.obstacles, ...document.keepouts]) {
		const roof = document.roofs.find((roof) => roof.id === object.roof_id)!;
		const offset = add(roof.origin_enu, scale(reference, -1));
		for (const uv of object.footprint_uv) {
			append(roof, [...uv, 0]);
			if ("height_m" in object) {
				const axis = scale(object.extrusion_axis_enu, object.height_m);
				requireUvResolution([
					uv[0] + dot(axis, roof.u_axis_enu),
					uv[1] + dot(axis, roof.v_axis_enu),
				]);
				const top = add(add(offset, vectorFromRoof(roof, [...uv, 0])), axis);
				requireUvResolution(top);
				points.push(toRender(top));
			}
		}
	}
	return points;
}
