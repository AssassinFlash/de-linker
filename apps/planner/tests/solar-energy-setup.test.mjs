import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom } from "./dom-fixture.mjs";
import { emptyPeriod } from "../src/domain/energyScenario.ts";
import { OperatingPeriodsForm } from "../src/components/energy/OperatingPeriodsForm.tsx";

test("solar-only operating periods expose grid and PV choices without storage controls", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(OperatingPeriodsForm, {
				periods: [{ ...emptyPeriod(), mode: "connected" }],
				onChange: () => {},
				locale: "en",
				report: () => {},
				useProfileRange: () => {},
				rangeBusy: false,
				hasStorage: false,
			}),
		),
	);
	const text = dom.element.textContent;
	assert.match(text, /PV available in this period/);
	assert.match(text, /Grid import limit/);
	assert.match(text, /Grid export limit/);
	assert.doesNotMatch(text, /Reserved stored energy/);
	assert.doesNotMatch(text, /Grid charging allowed/);
});
