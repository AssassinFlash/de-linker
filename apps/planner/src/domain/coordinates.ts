import type { RoofFace, Vec2, Vec3 } from "./geometry.ts";

export const add = (a: Vec3, b: Vec3): Vec3 => [
	a[0] + b[0],
	a[1] + b[1],
	a[2] + b[2],
];
export const scale = (v: Vec3, by: number): Vec3 => [
	v[0] * by,
	v[1] * by,
	v[2] * by,
];
export const dot = (a: Vec3, b: Vec3): number =>
	a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a: Vec3, b: Vec3): Vec3 => [
	a[1] * b[2] - a[2] * b[1],
	a[2] * b[0] - a[0] * b[2],
	a[0] * b[1] - a[1] * b[0],
];

export function pointOnRoof(roof: RoofFace, uv: Vec2): Vec3 {
	return add(
		roof.origin_enu,
		add(scale(roof.u_axis_enu, uv[0]), scale(roof.v_axis_enu, uv[1])),
	);
}

export function roofCoordinates(roof: RoofFace, enu: Vec3): Vec2 {
	const delta = add(enu, scale(roof.origin_enu, -1));
	return [dot(delta, roof.u_axis_enu), dot(delta, roof.v_axis_enu)];
}

/** Right-handed ENU → right-handed Three Y-up. No global DEFAULT_UP mutation. */
export const toRender = ([east, north, up]: Vec3): Vec3 => [east, up, -north];
export const fromRender = ([x, y, z]: Vec3): Vec3 => [x, -z, y];

/** Signed binary64 remainder and exact quadrant values, shared with Python. */
export function sinCosDegrees(degrees: number): readonly [number, number] {
	const reduced = degrees % 360;
	if (reduced === 0) return [0, 1];
	if (reduced === 90 || reduced === -270) return [1, 0];
	if (reduced === -90 || reduced === 270) return [-1, 0];
	if (reduced === 180 || reduced === -180) return [0, -1];
	const radians = (reduced * Math.PI) / 180;
	return [Math.sin(radians), Math.cos(radians)];
}

export function vectorFromRoof(roof: RoofFace, [u, v, n]: Vec3): Vec3 {
	return add(
		scale(roof.u_axis_enu, u),
		add(
			scale(roof.v_axis_enu, v),
			scale(cross(roof.u_axis_enu, roof.v_axis_enu), n),
		),
	);
}
