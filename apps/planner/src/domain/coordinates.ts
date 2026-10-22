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
