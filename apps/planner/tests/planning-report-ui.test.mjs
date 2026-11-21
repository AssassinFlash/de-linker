import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { createRoot } from "react-dom/client";
import { setupDom, deferred } from "./dom-fixture.mjs";
import { PlanningReportResult } from "../src/components/energy/PlanningReportResult.tsx";
import fixture from "./fixtures/index.ts";

const scope = "a".repeat(64);

for (const locale of ["en-GB", "de-DE"]) {
	test(`${locale}: an outdated report stays downloadable but is labelled before its results`, async (t) => {
		const page = setupDom(),
			root = createRoot(page.element);
		const nativeTranslate = window.wp.i18n.__;
		window.wp.i18n.__ = (message, domain) =>
			locale.startsWith("de") &&
			message === "This report describes an earlier version of the project."
				? "Dieser Bericht beschreibt einen früheren Projektstand."
				: nativeTranslate(message, domain);
		t.after(() => page.dispose(root));
		const run = structuredClone(fixture.geometric_pv.report_run);
		run.result.has_draft_items = false;
		let changeCurrent;
		function Harness() {
			const [current, setCurrent] = useState(true);
			changeCurrent = setCurrent;
			return React.createElement(PlanningReportResult, {
				run,
				scope,
				locale,
				current,
				blocked: false,
				client: { isCurrentScope: () => true },
				operations: {},
				recheck() {},
			});
		}
		await act(async () => root.render(React.createElement(Harness)));
		assert.equal(document.querySelector("[data-report-outdated]"), null);
		await act(async () => changeCurrent(false));
		const notice = document.querySelector("[data-report-outdated]");
		assert.ok(notice, "an energy-only report also needs a stale-input notice");
		assert.match(
			notice.textContent,
			locale.startsWith("de") ? /früheren Projektstand/ : /earlier version/,
		);
		assert.ok(
			notice.compareDocumentPosition(
				document.querySelector(".sc-run-heading"),
			) & window.Node.DOCUMENT_POSITION_FOLLOWING,
		);
		assert.equal(
			[...document.querySelectorAll("button")].find(
				(button) => button.textContent === "Download PDF",
			).disabled,
			false,
		);
		await act(async () => changeCurrent(true));
		assert.equal(document.querySelector("[data-report-outdated]"), null);
	});
}

test("changing report during a download releases the new report's download button", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element);
	t.after(() => page.dispose(root));
	const pending = deferred(),
		calls = [];
	const first = structuredClone(fixture.geometric_pv.report_run);
	first.result.has_draft_items = false;
	const second = structuredClone(first);
	second.id = "d".repeat(32);
	second.result.prepared_asset.id = "e".repeat(32);
	let replace;
	const client = {
		isCurrentScope: () => true,
		reportPdf(...args) {
			calls.push(args);
			return pending.promise;
		},
	};
	function Harness() {
		const [run, setRun] = useState(first);
		replace = setRun;
		return React.createElement(PlanningReportResult, {
			run,
			client,
			scope,
			locale: "en-GB",
			current: true,
			blocked: false,
			operations: {},
			recheck() {},
		});
	}
	await act(async () => root.render(React.createElement(Harness)));
	await act(async () =>
		[...document.querySelectorAll("button")]
			.find((button) => button.textContent === "Download PDF")
			.click(),
	);
	assert.equal(
		[...document.querySelectorAll("button")].find(
			(button) => button.textContent === "Download PDF",
		).disabled,
		true,
	);
	await act(async () => replace(second));
	assert.equal(calls[0][3].aborted, true);
	assert.equal(
		[...document.querySelectorAll("button")].find(
			(button) => button.textContent === "Download PDF",
		).disabled,
		false,
	);
	await act(async () =>
		pending.reject(new DOMException("Aborted", "AbortError")),
	);
	assert.equal(document.querySelector("[role=alert]"), null);
});
