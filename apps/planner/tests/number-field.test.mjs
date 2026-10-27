import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { setupDom, enter } from "./dom-fixture.mjs";
import { NumberField } from "../src/components/NumberField.tsx";

test("numeric input keeps locally entered syntax through parent echoes and resets for external values or locale", async (t) => {
	const dom = setupDom();
	let number;
	function Harness() {
		const [value, setValue] = useState(12.5),
			[locale, setLocale] = useState("en-GB"),
			[valid, setValid] = useState(true);
		number = value;
		return React.createElement(
			React.Fragment,
			null,
			React.createElement(NumberField, {
				label: "Value",
				unit: "",
				value,
				locale,
				onChange: setValue,
				onValidity: setValid,
			}),
			React.createElement(
				"button",
				{ onClick: () => setLocale("de-DE") },
				"German",
			),
			React.createElement(
				"button",
				{ onClick: () => setValue(12.5) },
				"Restore",
			),
			React.createElement("button", { disabled: !valid }, "Save"),
		);
	}
	const { createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	await act(async () => root.render(React.createElement(Harness)));
	const input = document.querySelector("input"),
		buttons = [...document.querySelectorAll("button")];
	await enter(input, "-0.");
	assert.equal(input.value, "-0.");
	assert.ok(Object.is(number, -0));
	await enter(input, "-0.29");
	assert.equal(input.value, "-0.29");
	assert.equal(number, -0.29);
	await act(async () => buttons[0].click());
	assert.equal(input.value, "-0,29");
	await enter(input, "2,50");
	assert.equal(input.value, "2,50");
	assert.equal(number, 2.5);
	await enter(input, "-");
	assert.equal(buttons[2].disabled, true);
	await act(async () => buttons[1].click());
	assert.equal(input.value, "12,5");
	assert.equal(buttons[2].disabled, false);
});
