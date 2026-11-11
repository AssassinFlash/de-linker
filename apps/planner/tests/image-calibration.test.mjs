import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { act } from "react";
import { setupDom } from "./dom-fixture.mjs";
import {
	applyGeometryCommand,
	emptyGeometry,
} from "../src/domain/geometryCommands.ts";
import geometryPolicy from "../src/contracts/geometry-policy.json" with { type: "json" };
import { readGeometry } from "../src/domain/validateGeometry.ts";

const DRAWING_WIDTH = 1200;
const DRAWING_HEIGHT = 800;

function button(text) {
	const result = [...document.querySelectorAll("button")].find(
		(element) => element.textContent.trim() === text,
	);
	assert.ok(result, `Missing button ${text}`);
	return result;
}
async function click(element) {
	await act(async () => element.click());
}
async function clickText(text) {
	await click(button(text));
}
async function typeInto(name, value) {
	const field = document.querySelector(`[name="${name}"]`);
	assert.ok(field, `Missing field ${name}`);
	await act(async () => {
		const type =
			field instanceof window.HTMLTextAreaElement
				? window.HTMLTextAreaElement
				: window.HTMLInputElement;
		const setter = Object.getOwnPropertyDescriptor(type.prototype, "value").set;
		setter.call(field, value);
		field.dispatchEvent(new window.Event("input", { bubbles: true }));
	});
}
async function submit() {
	const form = document.querySelector("form");
	assert.ok(form);
	await act(async () => {
		form.dispatchEvent(
			new window.Event("submit", { bubbles: true, cancelable: true }),
		);
	});
}
/** A click at a pixel of the calibration surface, using its own reported box. */
async function mark(x, y) {
	const svg = document.querySelector(".lp-plan-svg");
	assert.ok(svg);
	// jsdom has no layout: give the surface the image's own aspect at 2 CSS px
	// per image pixel, so the meet-scale mapping is exercised exactly.
	svg.getBoundingClientRect = () => ({
		width: DRAWING_WIDTH * 2,
		height: DRAWING_HEIGHT * 2,
		left: 0,
		top: 0,
		right: DRAWING_WIDTH * 2,
		bottom: DRAWING_HEIGHT * 2,
		x: 0,
		y: 0,
		toJSON() {},
	});
	await act(async () => {
		svg.dispatchEvent(
			new window.MouseEvent("click", {
				bubbles: true,
				cancelable: true,
				clientX: x * 2,
				clientY: y * 2,
			}),
		);
	});
}
async function chooseDrawing() {
	const input = document.querySelector('input[type="file"]');
	assert.ok(input);
	const file = new window.File(
		[new Uint8Array([137, 80, 78, 71])],
		"roof-plan.png",
		{
			type: "image/png",
		},
	);
	await act(async () => {
		Object.defineProperty(input, "files", {
			value: [file],
			configurable: true,
		});
		input.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	// createImageBitmap is a browser decoder; the fixture supplies its result.
	await act(async () => {
		await new Promise((resolve) => setTimeout(resolve, 0));
	});
}

const originalCreate = globalThis.createImageBitmap,
	originalUrl = globalThis.URL;

async function mount({ locale = "en-GB" } = {}) {
	const fixture = setupDom();
	globalThis.URL = {
		...originalUrl,
		createObjectURL: () => "blob:fixture/drawing",
		revokeObjectURL: () => {},
	};
	globalThis.createImageBitmap = async () => ({
		width: DRAWING_WIDTH,
		height: DRAWING_HEIGHT,
		close() {},
	});
	const { createRoot } = await import("react-dom/client");
	const { ImageCalibrationWorkspace } =
		await import("../src/components/design/ImageCalibrationWorkspace.tsx");
	const root = createRoot(fixture.element);
	let current = emptyGeometry(),
		edits = 0,
		activity = null;
	const { useState } = React;
	function Harness() {
		const [geometry, setGeometry] = useState(emptyGeometry());
		return React.createElement(ImageCalibrationWorkspace, {
			geometry,
			roofId: null,
			locale,
			disabled: false,
			onActivity: (open) => {
				activity = open;
			},
			commit(command) {
				try {
					current = applyGeometryCommand(geometry, command);
				} catch {
					return false;
				}
				edits++;
				setGeometry(current);
				return true;
			},
		});
	}
	await act(async () => {
		root.render(React.createElement(Harness));
	});
	return {
		fixture,
		root,
		geometry: () => readGeometry(current, geometryPolicy),
		edits: () => edits,
		activity: () => activity,
	};
}

test("a two-point scale and a traced outline become one calibrated roof", async (t) => {
	const harness = await mount();
	t.after(async () => {
		await act(async () => harness.root.unmount());
		harness.fixture.dom.window.close();
		globalThis.createImageBitmap = originalCreate;
		globalThis.URL = originalUrl;
	});
	await clickText("Calibrate a roof image");
	assert.equal(harness.activity(), true);
	await chooseDrawing();
	assert.match(
		document.querySelector(".lp-file-name").textContent,
		/roof-plan\.png/,
	);
	await typeInto("roof", "Calibrated roof");
	await submit();

	// Step 2 - the scale span, its real length, and the independent check span.
	await mark(100, 700);
	await mark(400, 700);
	await typeInto("length", "6");
	await clickText("Check span (0 of 2)");
	await mark(100, 100);
	await mark(700, 100);
	await typeInto("check_length", "12");
	await submit();
	// Step 3 - the roof outline on the same image, then the source declaration.
	assert.equal(document.querySelector("h3").textContent, "Outline");
	await clickText("Roof outline (0 points)");
	await mark(100, 100);
	await mark(700, 100);
	await mark(700, 700);
	await mark(100, 700);
	await typeInto("rights", "Owner drawing; deriving and retaining permitted");
	await typeInto("precision", "0.05");
	await act(async () => {
		document.querySelector('[name="retention"]').checked = true;
		document
			.querySelector('[name="retention"]')
			.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	const review = document.querySelector(".lp-import-review");
	assert.ok(review, "the review is shown before the outline is added");
	assert.match(review.textContent, /Roof-plane area/);
	// 600 x 600 px at 0.02 m/px is a 12 m x 12 m outline.
	assert.match(review.textContent, /144/);
	await submit();

	assert.ok(harness.edits() >= 1, "one history step");
	const geometry = harness.geometry();
	assert.equal(geometry.roofs.length, 1);
	const source = geometry.sources[0];
	assert.ok(source);
	assert.ok(source.calibration, "the calibration stays with the source");
	assert.equal(source.calibration.method, "two_point_uniform_scale_v1");
	assert.equal(source.calibration.view, "horizontal_plan");
	assert.equal(source.calibration.image.pixel_width, DRAWING_WIDTH);
	assert.equal(source.calibration.m_per_pixel, 0.02);
	assert.equal(source.calibration.check.residual_ratio, 0);
	assert.equal(source.calibration.measurement_status, "usable_uniform_scale");
	assert.equal(
		source.calibration_note,
		"Two-point scale from the drawing; not a survey.",
	);
	assert.equal(source.spatial_precision_m, 0.05);
	const roof = geometry.roofs[0];
	assert.equal(roof.source_id, source.id);
	assert.equal(roof.name, "Calibrated roof");
	// The drawing datum puts the outline's own lower-left corner at UV (0, 0);
	// the first traced point is its upper-left corner, 12 m up-slope.
	assert.deepEqual(roof.boundary_uv[0], [0, 12]);
	assert.deepEqual(roof.boundary_uv[2], [12, 0]);
	assert.equal(roof.boundary_uv.length, 4);
	assert.equal(harness.activity(), false);
});

test("a perspective photo is refused as an engineering measurement", async (t) => {
	const harness = await mount();
	t.after(async () => {
		await act(async () => harness.root.unmount());
		harness.fixture.dom.window.close();
		globalThis.createImageBitmap = originalCreate;
		globalThis.URL = originalUrl;
	});
	await clickText("Calibrate a roof image");
	await chooseDrawing();
	await typeInto("roof", "Photo roof");
	await act(async () => {
		const select = document.querySelector('[name="view"]');
		Object.getOwnPropertyDescriptor(
			window.HTMLSelectElement.prototype,
			"value",
		).set.call(select, "perspective_photo");
		select.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await submit();
	await mark(100, 700);
	await mark(400, 700);
	await typeInto("length", "6");
	// The independent span is optional; the photo is reference-only either way.
	await act(async () => {
		document.querySelector('[name="withCheck"]').click();
	});
	await submit();
	assert.equal(document.querySelector("h3").textContent, "Outline");
	await clickText("Roof outline (0 points)");
	await mark(100, 100);
	await mark(700, 100);
	await mark(700, 700);
	await mark(100, 700);
	await typeInto("rights", "Owner photo; reference only");
	await act(async () => {
		document.querySelector('[name="retention"]').checked = true;
		document
			.querySelector('[name="retention"]')
			.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.match(
		document.querySelector(".lp-import-review").textContent,
		/Reference only/,
	);
	await submit();
	const calibration = harness.geometry().sources[0]?.calibration;
	assert.ok(calibration);
	assert.equal(calibration.view, "perspective_photo");
	assert.equal(calibration.measurement_status, "reference_only");
	assert.equal(calibration.applied_pitch_deg, null);
});

test("the declared tolerance default follows the page language", async (t) => {
	const harness = await mount({ locale: "de-DE" });
	t.after(async () => {
		await act(async () => harness.root.unmount());
		harness.fixture.dom.window.close();
		globalThis.createImageBitmap = originalCreate;
		globalThis.URL = originalUrl;
	});
	// The fixture's i18n returns msgids unchanged; only the locale formatting
	// differs, which is what this test is about.
	await clickText("Calibrate a roof image");
	await chooseDrawing();
	await typeInto("roof", "Deutsch");
	await submit();
	// A German field's default must be a decimal comma; "0.01" would parse as
	// one thousandth and be refused by the same field.
	const tolerance = document.querySelector('[name="tolerance"]');
	assert.ok(tolerance);
	assert.equal(tolerance.defaultValue, "0,01");
});

test("the scale needs two distinct points and a positive length", async (t) => {
	const harness = await mount();
	t.after(async () => {
		await act(async () => harness.root.unmount());
		harness.fixture.dom.window.close();
		globalThis.createImageBitmap = originalCreate;
		globalThis.URL = originalUrl;
	});
	await clickText("Calibrate a roof image");
	await chooseDrawing();
	await typeInto("roof", "Incomplete roof");
	await submit();
	await mark(300, 300);
	await mark(300, 300);
	await typeInto("length", "6");
	await submit();
	assert.equal(harness.edits(), 0);
	assert.match(
		document.querySelector(".lp-notice").textContent,
		/The scale could not be recorded|Complete this field|Mark both ends/,
	);
});
