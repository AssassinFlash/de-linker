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
	assert.match(
		document.querySelector("table").textContent,
		/Trina Solar TSM-460NEG9R.28/,
	);
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
	assert.equal(calls[0][5], value.run.result.prepared_asset.content_sha256);
	await act(async () => button("Download bill of materials (CSV)").click());
	assert.equal(
		calls[1][4],
		value.run.result.prepared_attachments.bill_of_materials_csv.content_sha256,
	);
	assert.deepEqual(revoked, ["blob:report-1"]);
	await act(async () => root.render(null));
	assert.deepEqual(revoked, ["blob:report-1", "blob:report-2"]);
});

test("review submits the reviewed report and contact fields through one native inquiry action", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element),
		value = props();
	t.after(() => page.dispose(root));
	value.run.result.has_report_only_handoff = true;
	const handoff = "b".repeat(32),
		digest = "e".repeat(64),
		calls = [],
		posts = [];
	value.client.origin = location.origin;
	value.client.query = async (path, command) => {
		calls.push(path);
		return {
			schema_version: 1,
			project_id: command.project_id,
			report_run_id: command.report_run_id,
			revision: command.expected_revision,
			handoff_id: handoff,
			snapshot_sha256: digest,
			draft_sha256: digest,
			draft_urls: {
				en: location.origin + "/en/inquiry",
				de: location.origin + "/de/anfrage",
			},
			report_only: true,
			already_present: false,
			changes: [],
			inquiry_lines: [
				{
					product_id: 12,
					label: "Existing draft inverter",
					quantity: 2,
					project_id: null,
				},
			],
			inquiry_form_html: `<form method="post" action="/wp-admin/admin-post.php"><input name="name" required><input name="linker_draft_hash"><input name="linker_planner_draft_sha256"><input name="linker_planner_handoff_id" value="${handoff}"><button type="submit">Send inquiry</button></form>`,
		};
	};
	value.operations.start = async (path, fields) => {
		calls.push(path);
		assert.equal(fields.expected_draft_sha256, digest);
		return {
			path,
			receipt: {
				handoffId: handoff,
				inquiryCartHash: "c".repeat(32),
				inquiryDraftSha256: "d".repeat(64),
			},
		};
	};
	window.HTMLFormElement.prototype.submit = function () {
		posts.push(Object.fromEntries(new window.FormData(this)));
	};
	await act(async () =>
		root.render(React.createElement(ReviewProposal, value)),
	);
	assert.deepEqual(calls, ["draft/inquiry-preview"]);
	assert.match(page.element.textContent, /Existing draft inverter/);
	const form = page.element.querySelector("form");
	await act(async () => button("Send inquiry").click());
	assert.equal(calls.length, 1);
	form.elements.name.value = "Installer";
	await act(async () => button("Send inquiry").click());
	assert.deepEqual(calls, ["draft/inquiry-preview", "draft/apply"]);
	assert.deepEqual(posts, [
		{
			name: "Installer",
			linker_draft_hash: "c".repeat(32),
			linker_planner_draft_sha256: "d".repeat(64),
			linker_planner_handoff_id: handoff,
		},
	]);
});
