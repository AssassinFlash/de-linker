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
		rotationDeg: 0,
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

test("pixel y is down and a plan converts its horizontal run to slope once", () => {
	// The image's top-left pixel is UV (0, 0); V points up the drawing.
	const flat = plan({ pitchDeg: 0 });
	const [u, v] = pixelToUv([400, 400], flat);
	assert.ok(Math.abs(u - 8) < 1e-9, String(u));
	assert.ok(Math.abs(v + 8) < 1e-9, String(v));

	// A 60 degree roof: the same 300 px (6 m) horizontal run is 12 m of slope.
	const steep = plan({ pitchDeg: 60 });
	const steepBase = pixelToUv([100, 700], steep)[1];
	const [, steepTop] = pixelToUv([100, 400], steep);
	assert.ok(
		Math.abs(steepTop - steepBase - 12) < 1e-9,
		String(steepTop - steepBase),
	);

	// A slope elevation drawing states slope lengths already: no second cosine.
	const elevation = plan({ view: "roof_slope_elevation" });
	assert.equal(elevation.applied_pitch_deg, null);
	// Pixel V of a slope drawing: 300 px above the baseline is 6 m of slope.
	const baseline = pixelToUv([100, 700], elevation)[1];
	const [, drawn] = pixelToUv([100, 400], elevation);
	assert.ok(Math.abs(drawn - baseline - 6) < 1e-9, String(drawn - baseline));
});

test("rotation turns image right into the roof face U direction", () => {
	const turned = plan({ rotationDeg: 90 });
	// 300 px right of the origin becomes 6 m along -V after a quarter turn.
	const [u, v] = pixelToUv([300, 0], turned);
	assert.ok(Math.abs(u) < 1e-9, String(u));
	assert.ok(Math.abs(v + 6) < 1e-9, String(v));
	const [across, along] = pixelToUv([600, 400], turned);
	assert.ok(Math.abs(across + 8) < 1e-9, String(across));
	assert.ok(Math.abs(along + 12) < 1e-9, String(along));
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
		rotationDeg: 0,
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
