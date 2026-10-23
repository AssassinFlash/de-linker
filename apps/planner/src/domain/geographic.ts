/** Narrow display boundary for the server's explicit WGS84 cart/topocentric
 * operation. Metric geometry stays authoritative. PROJ fixtures independently
 * check these browser formulas; this is not a measurement accuracy claim. */
import type { Vec2, Vec3 } from "./geometry.ts";
import ellipsoid from "../contracts/wgs84-ellipsoid.json" with { type: "json" };
import { cross, dot, roofCoordinates, sinCosDegrees } from "./coordinates.ts";
import type { PlaneFrame } from "./geometry.ts";

export interface GeographicReference {
	schema_version: 1;
	method: "wgs84_cart_topocentric_v1";
	longitude_deg: number;
	latitude_deg: number;
	ellipsoid_height_m: number;
	height_basis: "known_wgs84_ellipsoid" | "zero_height_horizontal_convention";
}

function finite(values: readonly number[]): void {
	if (
		!values.every(
			(v) => Number.isFinite(v) && Math.abs(v) <= Number.MAX_SAFE_INTEGER,
		)
	)
		throw new Error("geographic_numeric_support");
}
function geodetic([longitude, latitude, height]: Vec3): void {
	finite([longitude, latitude, height]);
	if (longitude < -180 || longitude > 180 || latitude < -90 || latitude > 90)
		throw new Error("geographic_position_invalid");
}
const a = ellipsoid.semi_major_axis_m,
	f = 1 / ellipsoid.inverse_flattening,
	e2 = f * (2 - f),
	b = a * (1 - f);

function ecef(point: Vec3): Vec3 {
	geodetic(point);
	const [slon, clon] = sinCosDegrees(point[0]),
		[slat, clat] = sinCosDegrees(point[1]),
		n = a / Math.sqrt(1 - e2 * slat * slat);
	return [
		(n + point[2]) * clat * clon,
		(n + point[2]) * clat * slon,
		(n * (1 - e2) + point[2]) * slat,
	];
}

export class GeographicBridge {
	readonly reference: Readonly<GeographicReference>;
	private readonly origin: Vec3;
	private readonly east: Vec3;
	private readonly north: Vec3;
	private readonly up: Vec3;

	constructor(reference: GeographicReference) {
		if (
			reference.schema_version !== 1 ||
			reference.method !== "wgs84_cart_topocentric_v1" ||
			(reference.height_basis !== "known_wgs84_ellipsoid" &&
				reference.height_basis !== "zero_height_horizontal_convention") ||
			(reference.height_basis === "zero_height_horizontal_convention" &&
				reference.ellipsoid_height_m !== 0)
		)
			throw new Error("geographic_reference_invalid");
		this.reference = Object.freeze({ ...reference });
		this.origin = ecef([
			reference.longitude_deg,
			reference.latitude_deg,
			reference.ellipsoid_height_m,
		]);
		const [slon, clon] = sinCosDegrees(reference.longitude_deg),
			[slat, clat] = sinCosDegrees(reference.latitude_deg);
		this.east = [-slon, clon, 0];
		this.north = [-slat * clon, -slat * slon, clat];
		this.up = [clat * clon, clat * slon, slat];
	}

	forward(point: Vec3): Vec3 {
		if (
			this.reference.height_basis === "zero_height_horizontal_convention" &&
			point[2] !== 0
		)
			throw new Error("geographic_horizontal_height_invalid");
		const cart = ecef(point),
			delta: Vec3 = [
				cart[0] - this.origin[0],
				cart[1] - this.origin[1],
				cart[2] - this.origin[2],
			];
		const result: Vec3 = [
			dot(delta, this.east),
			dot(delta, this.north),
			dot(delta, this.up),
		];
		finite(result);
		return result;
	}

	/** Full ENU inverse. A horizontal-only caller must retain its curvature Up;
	 * substituting a roof's relative elevation would change the declared datum. */
	inverse(point: Vec3): Vec3 {
		finite(point);
		const cart = (axis: 0 | 1 | 2) =>
			this.origin[axis] +
			this.east[axis] * point[0] +
			this.north[axis] * point[1] +
			this.up[axis] * point[2];
		const x = cart(0),
			y = cart(1),
			z = cart(2);
		const p = Math.hypot(x, y);
		if (p === 0) {
			if (z === 0) throw new Error("geographic_inverse_undefined");
			return [this.reference.longitude_deg, z > 0 ? 90 : -90, Math.abs(z) - b];
		}
		let latitude = Math.atan2(z, p * (1 - e2)),
			converged = false;
		// Numerical iteration budget; no survey/engineering tolerance is implied.
		for (let step = 0; step < 16; step++) {
			const sin = Math.sin(latitude),
				n = a / Math.sqrt(1 - e2 * sin * sin),
				next = Math.atan2(z + e2 * n * sin, p);
			if (Math.abs(next - latitude) <= Number.EPSILON * 2) {
				latitude = next;
				converged = true;
				break;
			}
			latitude = next;
		}
		if (!converged) throw new Error("geographic_inverse_unresolved");
		const sin = Math.sin(latitude),
			cos = Math.cos(latitude),
			n = a / Math.sqrt(1 - e2 * sin * sin),
			height = Math.abs(cos) > 0.5 ? p / cos - n : z / sin - n * (1 - e2),
			result: Vec3 = [
				(Math.atan2(y, x) * 180) / Math.PI,
				(latitude * 180) / Math.PI,
				height,
			];
		geodetic(result);
		return result;
	}
}

/** Map E/N -> the actual declared roof plane -> orthonormal U/V. */
export function horizontalOnRoof(roof: PlaneFrame, [east, north]: Vec2): Vec2 {
	const normal = cross(roof.u_axis_enu, roof.v_axis_enu);
	if (!Number.isFinite(normal[2]) || normal[2] <= 0)
		throw new Error("geographic_roof_projection_invalid");
	const up =
			(dot(normal, roof.origin_enu) - normal[0] * east - normal[1] * north) /
			normal[2],
		uv = roofCoordinates(roof, [east, north, up]);
	finite([up, ...uv]);
	return uv;
}
