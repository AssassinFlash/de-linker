/** A coordinate keeps its datum's notation: a German reader still pastes 48.14. */
import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { setupDom, enter } from "./dom-fixture.mjs";
import { NumberField } from "../src/components/NumberField.tsx";

test("a point-or-comma field accepts the point a map shows, and still refuses two marks", async (t) => {
	const dom = setupDom();
	let number;
	function Harness() {
		const [value, setValue] = useState(null),
			[valid, setValid] = useState(true);
		number = value;
		return React.createElement(
			React.Fragment,
			null,
			React.createElement(NumberField, {
				label: "Latitude",
				unit: "°",
				value,
				locale: "de-DE",
				min: -90,
				max: 90,
				notation: "point-or-comma",
				onChange: setValue,
				onValidity: setValid,
			}),
			React.createElement("button", { disabled: !valid }, "Save"),
		);
	}
	const { createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	await act(async () => root.render(React.createElement(Harness)));
	const input = document.querySelector("input"),
		save = document.querySelector("button");

	// The map link the customer copies carries a point; the German interface
	// must not report a format error for it.
	await enter(input, "48.1689");
	assert.equal(number, 48.1689);
	assert.equal(save.disabled, false);
	assert.equal(input.getAttribute("aria-invalid"), "false");

	// The German reader's own comma reads the same value.
	await enter(input, "48,1689");
	assert.equal(number, 48.1689);
	assert.equal(save.disabled, false);

	// Two marks are grouping, not two decimal marks: refused rather than guessed.
	await enter(input, "1.234,5");
	assert.equal(save.disabled, true);
	assert.equal(input.getAttribute("aria-invalid"), "true");

	// Empty means "not provided", which the brief stores as null.
	await enter(input, "48.1689");
	await enter(input, "");
	assert.equal(number, null);
	assert.equal(save.disabled, false);
	assert.equal(document.querySelector(".lp-field-error"), null);
});

test("a locale field keeps its own declared mark, so the fix stays scoped to coordinates", async (t) => {
	const dom = setupDom();
	let number;
	function Harness() {
		const [value, setValue] = useState(null),
			[valid, setValid] = useState(true);
		number = value;
		return React.createElement(
			React.Fragment,
			null,
			React.createElement(NumberField, {
				label: "Annual consumption",
				unit: "kWh",
				value,
				locale: "de-DE",
				min: 0,
				onChange: setValue,
				onValidity: setValid,
			}),
			React.createElement("button", { disabled: !valid }, "Save"),
		);
	}
	const { createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	await act(async () => root.render(React.createElement(Harness)));
	const input = document.querySelector("input"),
		save = document.querySelector("button");

	await enter(input, "380000");
	assert.equal(number, 380000);
	assert.equal(save.disabled, false);
	// The German interface keeps rejecting the point here: this field is not a
	// datum whose notation belongs to a source document.
	await enter(input, "1.5");
	assert.equal(save.disabled, true);
});
