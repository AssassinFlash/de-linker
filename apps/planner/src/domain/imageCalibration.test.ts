import assert from "node:assert/strict";
import { test } from "node:test";
import {
	buildCalibration,
	checkCalibration,
	checkResidual,
	metricRing,
	measurementStatus,
	pixelDistance,
	pixelToUv,
	scaleFromControlPoints,
	type CalibrationPoints,
	type ImageCalibration,
} from "./imageCalibration.ts";
import { emptyGeometry } from "./geometryCommands.ts";
import { roofPlane } from "./geometryEditing.ts";
import { sinCosDegrees } from "./coordinates.ts";
import { applyGeometryCommand } from "./geometryCommands.ts";
import geometryPolicy from "../contracts/geometry-policy.json" with { type: "json" };
import { readGeometry } from "./validateGeometry.ts";

/** A 1200x800 plan drawing whose 300 px span is declared as 6 m. */
const IMAGE = {
	media_type: "image/png" as const,
	pixel_width: 1200,
	pixel_height: 800,
};
const CONTROL: CalibrationPoints = { first: [100, 700], second: [400, 700] };
const CHECK: CalibrationPoints = { first: [100, 100], second: [700, 100] };

function plan(overrides: Partial<Parameters<typeof buildCalibration>[0]> = {}) {
	return buildCalibration({
		view: "horizontal_plan",
		image: IMAGE,
		controlPoints: CONTROL,
		knownLength: 6,
		downslopeBearingDeg: 0,
		checkPoints: CHECK,
		checkLength: 12,
		checkToleranceRatio: 0.01,
		pitchDeg: 0,
		note: "Synthetic fixture drawing; not a survey.",
		...overrides,
	});
}

test("two point scale follows L / d_pixel", () => {
	assert.equal(pixelDistance(CONTROL.first, CONTROL.second), 300);
	assert.equal(scaleFromControlPoints(CONTROL, 6), 0.02);
	assert.equal(plan().m_per_pixel, 0.02);
});

test("coincident control points cannot define a scale", () => {
	assert.throws(
		() => scaleFromControlPoints({ first: [10, 10], second: [10, 10] }, 5),
		/calibration_points_coincide/,
	);
	assert.throws(
		() => scaleFromControlPoints(CONTROL, 0),
		/calibration_length_invalid/,
	);
});

test("a second independent span verifies the scale", () => {
	const calibration = plan();
	assert.ok(calibration.check);
	assert.equal(calibration.check.declared_length_m, 12);
	assert.equal(calibration.check.status, "within_tolerance");
	assert.equal(calibration.check.residual_ratio, 0);
	assert.equal(calibration.measurement_status, "usable_uniform_scale");
	// 600 px * 0.02 = 12 m; a 5 % shorter declaration fails the same span.
	assert.ok(checkResidual(CHECK, 11.4, 0.02) > 0.01);
});

test("a failing second span keeps the source reference only", () => {
	const calibration = plan({ checkLength: 9 });
	assert.equal(calibration.check?.status, "exceeds_tolerance");
	assert.equal(calibration.measurement_status, "reference_only");
	assert.equal(
		metricRing(calibration, [
			[0, 0],
			[300, 0],
			[300, 300],
		]),
		null,
	);
});

test("a perspective photograph never measures engineering length", () => {
	const calibration = plan({ view: "perspective_photo" });
	assert.equal(calibration.applied_pitch_deg, null);
	assert.equal(calibration.measurement_status, "reference_only");
	assert.equal(
		metricRing(calibration, [
			[0, 0],
			[300, 0],
			[300, 300],
		]),
		null,
	);
	// The arithmetic is still retained for the record.
	assert.equal(calibration.m_per_pixel, 0.02);
});

test("a missing independent span keeps the source reference only", () => {
	const calibration = plan({ checkPoints: null, checkLength: null });
	assert.equal(calibration.check, null);
	assert.equal(calibration.measurement_status, "reference_only");
	assert.equal(
		measurementStatus("roof_slope_elevation", calibration.check),
		"reference_only",
	);
});

test("the page's right edge is cross-slope and page-down is down-slope", () => {
	// The face frame is the measured roof's own: V runs down-slope, so a point
	// further down the page has a larger V. 300 px at 0.02 m/px is 6 m.
	const flat = plan({ pitchDeg: 0 });
	const [u, v] = pixelToUv([400, 400], flat);
	assert.ok(Math.abs(u - 8) < 1e-9, String(u));
	assert.ok(Math.abs(v - 8) < 1e-9, String(v));

	// A 60 degree plan: 6 m of horizontal run (300 px) is 12 m of slope length.
	const steep = plan({ pitchDeg: 60 });
	const [, slope] = pixelToUv([100, 300], steep);
	assert.ok(Math.abs(slope - 12) < 1e-9, String(slope));

	// A slope elevation drawing states slope lengths already: no second cosine.
	const elevation = plan({ view: "roof_slope_elevation" });
	assert.equal(elevation.applied_pitch_deg, null);
	const [, drawn] = pixelToUv([100, 300], elevation);
	assert.ok(Math.abs(drawn - 6) < 1e-9, String(drawn));
});

test("a horizontal plan never scales the cross-slope length", () => {
	// The pitch lengthens only the run up the slope; the same drawing's width
	// stays true length, which is what a plan actually shows.
	const steep = plan({ pitchDeg: 60 });
	const [u, v] = pixelToUv([300, 600], steep);
	assert.ok(Math.abs(u - 6) < 1e-9, String(u));
	assert.ok(Math.abs(v - 24) < 1e-9, String(v));
});

test("the declared bearing places the drawing, and the face keeps its frame", () => {
	// A drawing whose page-down faces south: the face's down-slope direction is
	// south, so its V axis points at -N with the pitch's cosine.
	const south = plan({ downslopeBearingDeg: 180 });
	const plane = roofPlane(
		south.applied_pitch_deg ?? 0,
		south.downslope_bearing_deg,
		[0, 0, 0],
	);
	assert.ok(Math.abs(plane.u_axis_enu[0] + 1) < 1e-9);
	assert.ok(Math.abs(plane.v_axis_enu[1] + 1) < 1e-9);
	// The mapping itself carries no second rotation: page-down is the slope run.
	const [u, v] = pixelToUv([300, 300], south);
	assert.ok(Math.abs(u - 6) < 1e-9, String(u));
	assert.ok(Math.abs(v - 6) < 1e-9, String(v));
});

test("the recorded arithmetic is refused when it contradicts its evidence", () => {
	const calibration = plan();
	const altered = (change: (value: ImageCalibration) => void) => {
		const copy = structuredClone(calibration);
		change(copy);
		return copy;
	};
	assert.throws(
		() => checkCalibration(altered((v) => (v.m_per_pixel = 0.021))),
		/calibration_scale_mismatch/,
	);
	assert.throws(
		() =>
			checkCalibration(altered((v) => (v.control_points.second = [5000, 700]))),
		/calibration_point_outside_image/,
	);
	assert.throws(
		() => checkCalibration(altered((v) => (v.check!.residual_ratio = 0.5))),
		/calibration_residual_mismatch/,
	);
	assert.throws(
		() =>
			checkCalibration(altered((v) => (v.check!.status = "exceeds_tolerance"))),
		/calibration_check_status_mismatch/,
	);
	assert.throws(
		() =>
			checkCalibration(
				altered((v) => (v.measurement_status = "reference_only")),
			),
		/calibration_status_mismatch/,
	);
	assert.throws(
		() => checkCalibration(altered((v) => (v.note = " "))),
		/calibration_note_required/,
	);
	const slope = plan({ view: "roof_slope_elevation" });
	const withPitch = structuredClone(slope);
	withPitch.applied_pitch_deg = 20;
	assert.throws(
		() => checkCalibration(withPitch),
		/calibration_pitch_not_applicable/,
	);
});

test("a horizontal plan requires its conversion pitch", () => {
	assert.throws(() => plan({ pitchDeg: null }), /calibration_pitch_required/);
	const slope = buildCalibration({
		view: "roof_slope_elevation",
		image: IMAGE,
		controlPoints: CONTROL,
		knownLength: 6,
		downslopeBearingDeg: 0,
		checkPoints: null,
		checkLength: null,
		checkToleranceRatio: 0.01,
		pitchDeg: 35,
		note: "Slope elevation drawing.",
	});
	assert.equal(slope.applied_pitch_deg, null);
});

test("calibration is optional source precision inside the design document", () => {
	const base = emptyGeometry();
	assert.equal(readGeometry(base, geometryPolicy).sources.length, 0);
	const source = {
		id: "source_calibrated",
		kind: "user_drawing" as const,
		note: "Owner's roof plan",
		rights_note: "Owner drawing; retaining and deriving permitted",
		reference_url: null,
		reference_sha256: null,
		acquired_at_utc: null,
		spatial_precision_m: 0.05,
		calibration_note: "Two-point scale from a 6 m facade span.",
		calibration: plan(),
		rights_basis: "user_attestation" as const,
		permissions: {
			derive: "permitted" as const,
			retain: "permitted" as const,
			export: "unknown" as const,
		},
	};
	const withCalibration = applyGeometryCommand(base, {
		type: "put_source",
		before: null,
		value: source,
	});
	assert.deepEqual(
		readGeometry(withCalibration, geometryPolicy).sources[0]?.calibration,
		source.calibration,
	);
	// A revision saved before this field existed omits it and still validates.
	const { calibration: _omitted, ...legacy } = source;
	const without = applyGeometryCommand(base, {
		type: "put_source",
		before: null,
		value: legacy,
	});
	assert.equal(
		readGeometry(without, geometryPolicy).sources[0]?.calibration,
		undefined,
	);
});

test("a calibrated face is a frame the ordinary roof form can edit", () => {
	// The face uses the documented constructor, so pitch and bearing are
	// recoverable and the customer can still edit boundary, openings and
	// clearances after calibrating a drawing.
	const plane = roofPlane(37, 205, [3, 4, 5]);
	assert.equal(plane.u_axis_enu[2], 0);
	assert.ok(plane.v_axis_enu[2] < 0);
	const [su, cu] = sinCosDegrees(205),
		[sv, cv] = sinCosDegrees(37);
	assert.ok(Math.abs(plane.u_axis_enu[0] - cu) < 1e-12);
	assert.ok(Math.abs(plane.u_axis_enu[1] + su) < 1e-12);
	assert.ok(Math.abs(plane.v_axis_enu[2] + sv) < 1e-12);
	assert.ok(Math.abs(plane.v_axis_enu[1] - cu * cv) < 1e-12);
});
