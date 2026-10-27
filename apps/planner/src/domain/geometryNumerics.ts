import policy from "../contracts/geometry-numerics.json" with { type: "json" };
import type { GeometryDocument } from "./geometry.ts";

/** Actual binary64 spacing; this is not a measurement/fitting tolerance. */
export function numberResolution(value: number): number {
	const data = new DataView(new ArrayBuffer(8));
	data.setFloat64(0, Math.abs(value));
	const exponent = (data.getUint32(0) >>> 20) & 0x7ff;
	return exponent === 0 ? Number.MIN_VALUE : 2 ** (exponent - 1023 - 52);
}

export class GeometryPrecisionError extends Error {
	constructor() {
		super("geometry_numeric_resolution_unsupported");
		this.name = "GeometryPrecisionError";
	}
}

export function requireUvResolution(values: readonly number[]): void {
	if (
		values.some((value) => numberResolution(value) > policy.max_uv_resolution_m)
	)
		throw new GeometryPrecisionError();
}

export function geometryUvResolution(document: GeometryDocument): number {
	let resolution = 0;
	const visit = (point: readonly number[]) => {
		for (const value of point)
			resolution = Math.max(resolution, numberResolution(value));
	};
	for (const roof of document.roofs)
		for (const ring of [roof.boundary_uv, ...roof.holes_uv])
			ring.forEach(visit);
	document.arrays.forEach((array) => visit(array.origin_uv));
	[...document.obstacles, ...document.keepouts].forEach((object) =>
		object.footprint_uv.forEach(visit),
	);
	return resolution;
}
