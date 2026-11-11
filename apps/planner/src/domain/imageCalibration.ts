/** Two-point image calibration: one recorded uniform scale, never a survey.
 *
 * The precedent is the map/workbench dossier: keep the original's hash and
 * pixel size, let the customer pick two points and declare their real length
 * (m_per_pixel = L / d_pixel), declare the drawing type and the pixel-Y
 * relation to the engineering axes, and verify the scale with a second,
 * independent span. A single uniform scale cannot rectify a perspective
 * photograph or a non-uniform scaling, so such a source stays reference-only.
 * Pixel positions, zoom or camera scale never own an engineering length.
 */
import type { Source, Vec2 } from "./geometry.ts";
import { sinCosDegrees } from "./coordinates.ts";

export type CalibrationView =
	"horizontal_plan" | "roof_slope_elevation" | "perspective_photo";

export interface CalibrationImage {
	media_type: "image/png" | "image/jpeg" | "image/webp";
	pixel_width: number;
	pixel_height: number;
}

export interface CalibrationPoints {
	first: Vec2;
	second: Vec2;
}

export interface CalibrationCheck {
	points: CalibrationPoints;
	declared_length_m: number;
	residual_ratio: number;
	status: "within_tolerance" | "exceeds_tolerance";
}

export interface ImageCalibration {
	schema_version: 1;
	method: "two_point_uniform_scale_v1";
	view: CalibrationView;
	image: CalibrationImage;
	control_points: CalibrationPoints;
	known_length_m: number;
	m_per_pixel: number;
	/** Compass bearing, clockwise from project north, of the direction drawn
	 * down the page. It is the roof's down-slope bearing, so the face keeps the
	 * documented frame (U cross-slope, V down-slope) and no second angle is
	 * invented. Declaring 0 means the drawing's page-down faces project north. */
	downslope_bearing_deg: number;
	check: CalibrationCheck | null;
	check_tolerance_ratio: number;
	/** The pitch whose one cosine turned a horizontal plan into slope lengths. */
	applied_pitch_deg: number | null;
	measurement_status: "usable_uniform_scale" | "reference_only";
	note: string;
}

/** Arithmetic-support tolerance between browser and server binary64 work; a
 * recorded scale is only meaningful to the source's own declared precision. */
export const SCALE_RELATIVE_TOLERANCE = 1e-9;
export const RESIDUAL_ABSOLUTE_TOLERANCE = 1e-12;

export function pixelDistance(first: Vec2, second: Vec2): number {
	return Math.hypot(second[0] - first[0], second[1] - first[1]);
}

/** `L / d_pixel`; the two points must differ so the scale stays defined. */
export function scaleFromControlPoints(
	points: CalibrationPoints,
	knownLength: number,
): number {
	const distance = pixelDistance(points.first, points.second);
	if (!Number.isFinite(distance) || distance <= 0)
		throw new Error("calibration_points_coincide");
	if (!Number.isFinite(knownLength) || knownLength <= 0)
		throw new Error("calibration_length_invalid");
	return knownLength / distance;
}

/** |measured - declared| / declared for an independent span. */
export function checkResidual(
	points: CalibrationPoints,
	declaredLength: number,
	mPerPixel: number,
): number {
	const measured = pixelDistance(points.first, points.second) * mPerPixel;
	return Math.abs(measured - declaredLength) / declaredLength;
}

export function measurementStatus(
	view: CalibrationView,
	check: CalibrationCheck | null,
): ImageCalibration["measurement_status"] {
	if (view === "perspective_photo" || check === null) return "reference_only";
	return check.status === "within_tolerance"
		? "usable_uniform_scale"
		: "reference_only";
}

/** Engine parity: the same refusals as `ImageCalibration.recorded_scale`. */
export function checkCalibration(value: ImageCalibration): void {
	const { image, control_points: points } = value;
	const inside = ([x, y]: Vec2) =>
		x >= 0 && x <= image.pixel_width && y >= 0 && y <= image.pixel_height;
	if (!value.note.trim()) throw new Error("calibration_note_required");
	for (const point of [points.first, points.second])
		if (!inside(point)) throw new Error("calibration_point_outside_image");
	const expected = scaleFromControlPoints(points, value.known_length_m);
	if (
		Math.abs(value.m_per_pixel - expected) >
		SCALE_RELATIVE_TOLERANCE * expected
	)
		throw new Error("calibration_scale_mismatch");
	if (value.check !== null) {
		for (const point of [value.check.points.first, value.check.points.second])
			if (!inside(point)) throw new Error("calibration_point_outside_image");
		const residual = checkResidual(
			value.check.points,
			value.check.declared_length_m,
			value.m_per_pixel,
		);
		if (
			Math.abs(value.check.residual_ratio - residual) >
			RESIDUAL_ABSOLUTE_TOLERANCE
		)
			throw new Error("calibration_residual_mismatch");
		const status =
			residual <= value.check_tolerance_ratio
				? "within_tolerance"
				: "exceeds_tolerance";
		if (value.check.status !== status)
			throw new Error("calibration_check_status_mismatch");
	}
	if (value.view === "horizontal_plan") {
		if (value.applied_pitch_deg === null)
			throw new Error("calibration_pitch_required");
	} else if (value.applied_pitch_deg !== null)
		throw new Error("calibration_pitch_not_applicable");
	if (value.measurement_status !== measurementStatus(value.view, value.check))
		throw new Error("calibration_status_mismatch");
}

export function buildCalibration({
	view,
	image,
	controlPoints,
	knownLength,
	downslopeBearingDeg,
	checkPoints,
	checkLength,
	checkToleranceRatio,
	pitchDeg,
	note,
}: {
	view: CalibrationView;
	image: CalibrationImage;
	controlPoints: CalibrationPoints;
	knownLength: number;
	downslopeBearingDeg: number;
	checkPoints: CalibrationPoints | null;
	checkLength: number | null;
	checkToleranceRatio: number;
	pitchDeg: number | null;
	note: string;
}): ImageCalibration {
	const mPerPixel = scaleFromControlPoints(controlPoints, knownLength);
	let check: CalibrationCheck | null = null;
	if (checkPoints !== null && checkLength !== null) {
		const residual = checkResidual(checkPoints, checkLength, mPerPixel);
		check = {
			points: checkPoints,
			declared_length_m: checkLength,
			residual_ratio: residual,
			status:
				residual <= checkToleranceRatio
					? "within_tolerance"
					: "exceeds_tolerance",
		};
	}
	const appliedPitch = view === "horizontal_plan" ? pitchDeg : null;
	const value: ImageCalibration = {
		schema_version: 1,
		method: "two_point_uniform_scale_v1",
		view,
		image,
		control_points: controlPoints,
		known_length_m: knownLength,
		m_per_pixel: mPerPixel,
		downslope_bearing_deg: downslopeBearingDeg,
		check,
		check_tolerance_ratio: checkToleranceRatio,
		applied_pitch_deg: appliedPitch,
		measurement_status: measurementStatus(view, check),
		note,
	};
	checkCalibration(value);
	return value;
}

/**
 * A drawing states the roof's own two directions: the page's right edge is
 * cross-slope (U) and the page's down direction is down-slope (V), because the
 * declared bearing already places the page on site. A horizontal plan's
 * horizontal run becomes slope length once, through the declared pitch, so a
 * slope drawing is never converted twice. Cross-slope length is true length in
 * a plan and is not scaled by the pitch.
 */
export function pixelToUv([x, y]: Vec2, calibration: ImageCalibration): Vec2 {
	const scale = calibration.m_per_pixel,
		u = x * scale,
		down = y * scale;
	if (calibration.view !== "horizontal_plan") return [u, down];
	const pitch = calibration.applied_pitch_deg ?? 0,
		[, horizontal] = sinCosDegrees(pitch);
	if (!(horizontal > 0)) throw new Error("calibration_pitch_unsupported");
	return [u, down / horizontal];
}

export function pixelRingToUv(
	ring: readonly Vec2[],
	calibration: ImageCalibration,
): readonly Vec2[] {
	return ring.map((point) => pixelToUv(point, calibration));
}

/** A perspective photograph or a failing independent span cannot measure. */
export function metricRing(
	calibration: ImageCalibration,
	ring: readonly Vec2[],
): readonly Vec2[] | null {
	if (calibration.measurement_status !== "usable_uniform_scale") return null;
	return pixelRingToUv(ring, calibration);
}

export function calibratedSource(
	source: Source,
	calibration: ImageCalibration,
	referenceSha256: string | null,
	note: string,
): Source {
	return {
		...source,
		kind: "user_drawing",
		reference_sha256: referenceSha256,
		calibration,
		calibration_note: note,
	};
}
