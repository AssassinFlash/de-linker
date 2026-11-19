import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { setupDom, deferred } from "./dom-fixture.mjs";
import { ReviewProposal } from "../src/components/configurator/ReviewProposal.tsx";
import fixture from "./fixtures/index.ts";

const scope = "a".repeat(64);
function props(run = structuredClone(fixture.geometric_pv.report_run)) {
	if (run) run.result.has_draft_items = false;
	return {
		project: {
			id: run?.project_id ?? "1".repeat(32),
			title: "Canal house",
			inputs: {},
		},
		inputs: {},
		run,
		client: { isCurrentScope: () => true },
		session: { query_scope: scope },
		operations: { records: [], busy: false },
		locale: "en-GB",
		blocked: false,
		current: true,
		generate() {},
		recheck() {},
	};
}
const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) => node.textContent === text,
	);

test("review shows the report's actual BOM and supports generation before a report exists", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element);
	t.after(() => page.dispose(root));
	const value = props();
	await act(async () =>
		root.render(React.createElement(ReviewProposal, value)),
	);
	assert.match(document.querySelector("table").textContent, /460 Wp/);
	assert.ok(document.querySelector("details"));
	assert.ok(button("Generate report in English"));
	assert.equal(
		document.querySelector('input[type="file"]').accept,
		"image/png,image/jpeg",
	);
	assert.equal(button("Add selected products to solution draft"), undefined);
	let generated = 0;
	await act(async () =>
		root.render(
			React.createElement(ReviewProposal, {
				...value,
				run: null,
				generate: (logo) => {
					assert.equal(logo, null);
					generated++;
				},
			}),
		),
	);
	await act(async () => button("Generate project report").click());
	assert.equal(generated, 1);
});

test("replacing the report aborts its download and releases the next report's controls", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element);
	t.after(() => page.dispose(root));
	const value = props(),
		pending = deferred(),
		calls = [];
	value.client.reportPdf = (...args) => {
		calls.push(args);
		return pending.promise;
	};
	await act(async () =>
		root.render(React.createElement(ReviewProposal, value)),
	);
	await act(async () => button("Download PDF").click());
	assert.equal(button("Download PDF").disabled, true);
	const replacement = structuredClone(value.run);
	replacement.id = "d".repeat(32);
	await act(async () =>
		root.render(
			React.createElement(ReviewProposal, { ...value, run: replacement }),
		),
	);
	assert.equal(calls[0][3].aborted, true);
	assert.equal(button("Download PDF").disabled, false);
	await act(async () =>
		pending.reject(new DOMException("Aborted", "AbortError")),
	);
	assert.equal(document.querySelector("[role=alert]"), null);
});

test("downloads use the report's pinned PDF and CSV and revoke their object URLs", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element);
	t.after(() => page.dispose(root));
	const value = props(),
		calls = [],
		revoked = [];
	const pdf = value.run.result.prepared_asset,
		csv = value.run.result.prepared_attachments.bill_of_materials_csv;
	for (const [file, id, sha] of [
		[pdf, "4", "5"],
		[csv, "6", "7"],
	]) {
		file.reissued_from = { id: file.id, content_sha256: file.content_sha256 };
		file.id = id.repeat(32);
		file.content_sha256 = sha.repeat(64);
	}
	value.client.reportPdf = async (...args) => {
		calls.push(["pdf", ...args]);
		return new Blob(["pdf"]);
	};
	value.client.reportCsv = async (...args) => {
		calls.push(["csv", ...args]);
		return new Blob(["csv"]);
	};
	const create = URL.createObjectURL,
		revoke = URL.revokeObjectURL;
	URL.createObjectURL = () => `blob:report-${calls.length}`;
	URL.revokeObjectURL = (url) => revoked.push(url);
	const click = window.HTMLAnchorElement.prototype.click;
	window.HTMLAnchorElement.prototype.click = function () {};
	t.after(() => {
		URL.createObjectURL = create;
		URL.revokeObjectURL = revoke;
		page.dom.window.HTMLAnchorElement.prototype.click = click;
	});
	await act(async () =>
		root.render(React.createElement(ReviewProposal, value)),
	);
	await act(async () => button("Download PDF").click());
	assert.equal(calls[0][2], pdf.id);
	assert.equal(calls[0][5], pdf.content_sha256);
	await act(async () => button("Download bill of materials (CSV)").click());
	assert.equal(calls[1][2], csv.id);
	assert.equal(
		calls[1][4],
		value.run.result.prepared_attachments.bill_of_materials_csv.content_sha256,
	);
	assert.deepEqual(revoked, ["blob:report-1"]);
	await act(async () => root.render(null));
	assert.deepEqual(revoked, ["blob:report-1", "blob:report-2"]);
});

test("a retained inverter report can be attached to an inquiry without a product selection", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element);
	t.after(() => page.dispose(root));
	const value = props();
	value.run.result.has_report_only_handoff = true;
	await act(async () =>
		root.render(React.createElement(ReviewProposal, value)),
	);
	assert.ok(button("Attach report to inquiry"));
	assert.equal(button("Add selected products to solution draft"), undefined);
});

test("an unusable optional logo can be removed and the project report generated", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element),
		generated = [];
	t.after(() => page.dispose(root));
	await act(async () =>
		root.render(
			React.createElement(ReviewProposal, {
				...props(null),
				generate: (logo) => generated.push(logo),
			}),
		),
	);
	const field = document.querySelector('input[type="file"]');
	Object.defineProperty(field, "files", {
		value: [new window.File(["logo"], "logo.gif", { type: "image/gif" })],
	});
	await act(async () =>
		field.dispatchEvent(new window.Event("change", { bubbles: true })),
	);
	assert.match(
		document.querySelector("[role=alert]").textContent,
		/could not be used/,
	);
	await act(async () => button("Remove logo").click());
	await act(async () => button("Generate project report").click());
	assert.deepEqual(generated, [null]);
});

test("report preview opens the complete pinned report and its original PDF", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element);
	t.after(() => page.dispose(root));
	const value = props(),
		asset = value.run.result.prepared_asset,
		file = new Blob(["%PDF-verified"], { type: "application/pdf" }),
		requested = [],
		revoked = [];
	value.client.reportPdf = async (...args) => {
		requested.push(args);
		return file;
	};
	const create = URL.createObjectURL,
		revoke = URL.revokeObjectURL;
	URL.createObjectURL = (blob) => {
		assert.equal(blob, file);
		return "blob:https://fixture.invalid/current-report";
	};
	URL.revokeObjectURL = (url) => revoked.push(url);
	t.after(() => {
		URL.createObjectURL = create;
		URL.revokeObjectURL = revoke;
	});
	await act(async () =>
		root.render(React.createElement(ReviewProposal, value)),
	);
	const dialog = document.querySelector("dialog");
	assert.ok(dialog);
	// JSDOM does not implement native dialog opening and closing.
	dialog.showModal = () => {
		dialog.open = true;
	};
	dialog.close = () => {
		dialog.open = false;
		dialog.dispatchEvent(new window.Event("close"));
	};
	assert.equal(dialog.open, false);
	await act(async () => button("Preview report").click());
	assert.equal(dialog.open, true);
	assert.match(dialog.textContent, /460 Wp/);
	assert.deepEqual(requested[0]?.slice(0, 3), [
		value.run.project_id,
		asset.id,
		scope,
	]);
	assert.equal(requested[0][4], asset.content_sha256);
	const pdfLink = dialog.querySelector("a[target='_blank'][href^='blob:']");
	assert.equal(pdfLink.textContent, "Open report PDF");
	assert.equal(pdfLink.rel, "noopener noreferrer");
	await act(async () => button("Close").click());
	assert.equal(dialog.open, false);
	assert.deepEqual(revoked, ["blob:https://fixture.invalid/current-report"]);
});
