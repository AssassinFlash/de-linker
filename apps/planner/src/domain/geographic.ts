/** Narrow display boundary for the server's explicit WGS84 cart/topocentric
 * operation. Metric geometry stays authoritative. PROJ fixtures independently
 * check these browser formulas; this is not a measurement accuracy claim. */
import type { Vec2, Vec3 } from "./geometry.ts";
import ellipsoid from "../contracts/wgs84-ellipsoid.json" with { type: "json" };
import { cross, dot, sinCosDegrees } from "./coordinates.ts";
import { requireUvResolution } from "./geometryNumerics.ts";
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
			const result: Vec3 = [
				this.reference.longitude_deg,
				z > 0 ? 90 : -90,
				Math.abs(z) - b,
			];
			geodetic(result);
			return result;
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

	/** Geodetic vertical direction at a position, in the fixed anchor ENU. */
	upAt([longitude, latitude]: Vec2): Vec3 {
		geodetic([longitude, latitude, 0]);
		const [slon, clon] = sinCosDegrees(
				longitude - this.reference.longitude_deg,
			),
			[slat, clat] = sinCosDegrees(latitude),
			[slat0, clat0] = sinCosDegrees(this.reference.latitude_deg);
		return [
			clat * slon,
			clat0 * slat - slat0 * clat * clon,
			slat0 * slat + clat0 * clat * clon,
		];
	}
}

/** Map E/N -> the actual declared roof plane -> orthonormal U/V. */
export function horizontalOnRoof(roof: PlaneFrame, [east, north]: Vec2): Vec2 {
	const normal = cross(roof.u_axis_enu, roof.v_axis_enu);
	if (!Number.isFinite(normal[2]) || normal[2] <= 0)
		throw new Error("geographic_roof_projection_invalid");
	const de = east - roof.origin_enu[0],
		dn = north - roof.origin_enu[1],
		u = roof.u_axis_enu,
		v = roof.v_axis_enu,
		uv: Vec2 = [
			(de * v[1] - dn * v[0]) / normal[2],
			(u[0] * dn - u[1] * de) / normal[2],
		];
	finite(uv);
	return uv;
}

/** geodetic_vertical_line_v1. Keep the full zero-height position, intersect its
 * geodetic vertical with the plane, and reject the back-facing/unsupported
 * branch. A negative derived ellipsoid height is allowed; zero is not ground. */
export function geographicOnRoof(
	bridge: GeographicBridge,
	roof: PlaneFrame,
	position: Vec2,
): Vec2 {
	const base = bridge.forward([...position, 0]),
		vertical = bridge.upAt(position),
		u = roof.u_axis_enu,
		v = roof.v_axis_enu,
		normal = cross(u, v),
		denominator = dot(normal, vertical);
	if (!Number.isFinite(denominator) || denominator <= 0)
		throw new Error("geographic_roof_intersection_invalid");
	const relative: Vec3 = [
			base[0] - roof.origin_enu[0],
			base[1] - roof.origin_enu[1],
			base[2] - roof.origin_enu[2],
		],
		uv: Vec2 = [
			dot(cross(v, vertical), relative) / denominator,
			dot(cross(vertical, u), relative) / denominator,
		],
		at = (axis: 0 | 1 | 2) =>
			roof.origin_enu[axis] + u[axis] * uv[0] + v[axis] * uv[1],
		point: Vec3 = [at(0), at(1), at(2)];
	finite([...uv, ...point]);
	// The same accepted binary64 spacing policy applies to both the local chart
	// and the ENU point crossing the geodetic boundary, independently of accuracy.
	requireUvResolution([...uv, ...point]);
	const [longitude, latitude] = bridge.inverse(point),
		returnedVertical = bridge.upAt([longitude, latitude]);
	// Branch/convergence budget only; metric representability is checked above.
	if (
		Math.hypot(
			...vertical.map((value, axis) => value - returnedVertical[axis]!),
		) > 2e-12
	)
		throw new Error("geographic_roof_position_unresolved");
	return uv;
}
