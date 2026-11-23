import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom } from "./dom-fixture.mjs";

test("draft quantities retry through Woo while a report line opens its configuration", async (t) => {
	const fixture = setupDom();
	const { createRoot } = await import("react-dom/client");
	const { InquiryBomLine } =
		await import("../src/components/configurator/InquiryBomLine.tsx");
	const root = createRoot(fixture.element);
	t.after(() => fixture.dispose(root));
	const edit = {
		url: "/wp-json/wc/store/v1/cart/update-item",
		nonce: "cart",
		restNonce: "wp",
	};
	const requests = [];
	t.mock.method(globalThis, "fetch", async (url, options) => {
		requests.push([url, options]);
		return { ok: requests.length > 1 };
	});
	const line = { label: "DC cable", quantity: 2, cartKey: "woo-line" };
	const updates = [];
	let refreshed = 0;
	let opened = 0;
	const render = (item) =>
		act(async () =>
			root.render(
				React.createElement(InquiryBomLine, {
					line: item,
					edit,
					pending: false,
					onBusy: (value) => updates.push(value),
					onUpdated: () => refreshed++,
					onEditConfiguration: () => opened++,
				}),
			),
		);
	await render(line);
	const plus = fixture.element.querySelector(
		"button[aria-label='Increase quantity for DC cable']",
	);
	await act(async () => plus.click());
	assert.match(
		fixture.element.querySelector("[role=alert]").textContent,
		/try again/i,
	);
	assert.equal(refreshed, 0);
	await act(async () => plus.click());
	assert.equal(fixture.element.querySelector("[role=alert]"), null);
	assert.equal(refreshed, 1);
	assert.deepEqual(updates, [true, false, true, false]);
	assert.equal(requests[1][0], edit.url);
	assert.deepEqual(JSON.parse(requests[1][1].body), {
		key: "woo-line",
		quantity: 3,
	});
	assert.equal(requests[1][1].headers.Nonce, "cart");
	assert.equal(requests[1][1].headers["X-WP-Nonce"], "wp");
	await render({ ...line, cartKey: null, quantity: 4 });
	assert.match(fixture.element.textContent, /× 4/);
	const buttons = fixture.element.querySelectorAll("button");
	assert.equal(buttons.length, 1);
	assert.equal(buttons[0].textContent, "Adjust equipment quantities");
	await act(async () => buttons[0].click());
	assert.equal(opened, 1);
	assert.equal(requests.length, 2);
});
