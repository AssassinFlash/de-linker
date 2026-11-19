import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { setupDom, deferred } from "./dom-fixture.mjs";
import { ReviewProposal } from "../src/components/configurator/ReviewProposal.tsx";
import fixture from "./fixtures/index.ts";

const scope = "a".repeat(64);

function reflectNamedFormAction(t) {
	// jsdom omits the browser's named-property lookup for HTMLFormElement.
	const native = Object.getOwnPropertyDescriptor(
		window.HTMLFormElement.prototype,
		"action",
	);
	t.mock.getter(window.HTMLFormElement.prototype, "action", function () {
		return this.elements.namedItem("action") ?? native.get.call(this);
	});
}
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

for (const mode of ["new", "applied", "unapplied", "changed"])
	test(`Review submits or recovers the native inquiry (${mode})`, async (t) => {
		const page = setupDom(),
			root = createRoot(page.element),
			value = props();
		t.after(() => page.dispose(root));
		reflectNamedFormAction(t);
		value.run.result.has_report_only_handoff = true;
		const handoff = "b".repeat(32),
			digest = "e".repeat(64),
			calls = [],
			posts = [];
		const key = crypto.randomUUID(),
			record = {
				path: "draft/apply",
				key,
				resultId: null,
				scope,
				body: JSON.stringify({
					schema_version: 1,
					project_id: value.run.project_id,
					report_run_id: value.run.id,
					expected_revision: value.run.revision,
					expected_draft_sha256: mode === "changed" ? "a".repeat(64) : digest,
					key,
				}),
			};
		if (mode !== "new") value.operations.records = [record];
		value.client.send = async (path, body) => {
			calls.push(path);
			assert.equal(body, record.body);
			return mode === "applied"
				? {
						schema_version: 1,
						state: "applied",
						receipt: {
							schema_version: 1,
							project_id: value.run.project_id,
							report_run_id: value.run.id,
							revision: value.run.revision,
							handoff_id: handoff,
							snapshot_sha256: digest,
							intent_sha256: digest,
							report_only: true,
							items: [],
							draft_urls: {
								en: location.origin + "/en",
								de: location.origin + "/de",
							},
							inquiry_cart_hash: "c".repeat(32),
							inquiry_draft_sha256: "d".repeat(64),
						},
					}
				: { schema_version: 1, state: "not_applied" };
		};
		value.operations.acknowledgeReadback = async (item, id) => {
			assert.equal(item, record);
			assert.equal(id, handoff);
		};
		value.operations.retry = async (item) => {
			assert.equal(item, record);
			calls.push("retry");
			return {
				path: "draft/apply",
				receipt: {
					handoffId: handoff,
					inquiryCartHash: "c".repeat(32),
					inquiryDraftSha256: "d".repeat(64),
				},
			};
		};
		value.operations.discard = async (item) => {
			assert.equal(item, record);
			calls.push("discard");
			value.operations.records = [];
		};
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
						project_title: null,
					},
					{
						product_id: 12,
						label: "Existing draft inverter",
						quantity: 3,
						project_id: "f".repeat(32),
						project_title: "Warehouse roof",
					},
				],
				inquiry_form_html: `<form method="post" action="/wp-admin/admin-post.php"><input type="hidden" name="action" value="linker_inquiry"><input name="name" required>${mode === "changed" ? `<input type="checkbox" name="linker_include_project_notes" value="1" checked><input name="billing_city" value="Berlin"><select name="billing_country"><option>DE</option><option>NL</option></select><input type="hidden" name="linker_project_note_revisions[project]" value="${calls.length}">` : ""}<input name="linker_draft_hash"><input name="linker_planner_draft_sha256"><input name="linker_planner_handoff_id" value="${handoff}"><button type="submit">Send inquiry</button></form>`,
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
		const rows = page.element.querySelectorAll(".sc-draft-transfer tbody tr");
		assert.deepEqual(
			Array.from(rows, (row) =>
				Array.from(row.cells, (cell) => cell.textContent),
			),
			[
				["Existing draft inverter", "Solution draft", "2"],
				["Existing draft inverter", "Warehouse roof", "3"],
			],
		);
		const form = page.element.querySelector("form");
		await act(async () => button("Send inquiry").click());
		assert.equal(calls.length, 1);
		form.elements.name.value = "Installer";
		if (mode === "changed") {
			form.elements.linker_include_project_notes.checked = false;
			form.elements.billing_city.value = "Utrecht";
			form.elements.billing_country.value = "NL";
		}
		await act(async () => button("Send inquiry").click());
		if (mode === "changed") {
			assert.deepEqual(calls, ["draft/inquiry-preview", "draft/read"]);
			assert.equal(posts.length, 0);
			await act(async () => button("Review inquiry again").click());
			assert.equal(
				page.element.querySelector("form").elements.name.value,
				"Installer",
			);
			assert.deepEqual(calls, [
				"draft/inquiry-preview",
				"draft/read",
				"discard",
				"draft/inquiry-preview",
			]);
			await act(async () => button("Send inquiry").click());
			assert.equal(posts.length, 1);
			assert.equal(posts[0].linker_include_project_notes, undefined);
			assert.equal(posts[0].billing_city, "Utrecht");
			assert.equal(posts[0].billing_country, "NL");
			assert.equal(posts[0]["linker_project_note_revisions[project]"], "4");
			return;
		}
		assert.deepEqual(calls, [
			"draft/inquiry-preview",
			...(mode === "new"
				? ["draft/apply"]
				: mode === "applied"
					? ["draft/read"]
					: ["draft/read", "retry"]),
		]);
		assert.deepEqual(posts, [
			{
				action: "linker_inquiry",
				name: "Installer",
				linker_draft_hash: "c".repeat(32),
				linker_planner_draft_sha256: "d".repeat(64),
				linker_planner_handoff_id: handoff,
			},
		]);
	});

test("a brief-only project can download an older report or explicitly inquire about its direction", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element),
		value = props(null);
	t.after(() => page.dispose(root));
	const { emptyBrief } = await import("../src/domain/brief.ts");
	value.inputs = {
		brief: { ...emptyBrief(), system_scope: "storage_addition" },
	};
	const earlier = props().run;
	const calls = [];
	value.client.origin = location.origin;
	value.client.query = async (path) => {
		calls.push(path);
		return {
			schema_version: 1,
			inquiry_lines: [],
			inquiry_form_html:
				'<form method="post" action="/wp-admin/admin-post.php"><textarea name="message"></textarea></form>',
		};
	};
	value.client.reportPdf = async (id, asset) => {
		assert.equal(id, earlier.project_id);
		assert.equal(asset, earlier.result.prepared_asset.id);
		return new Blob(["pdf"]);
	};
	let downloaded;
	t.mock.method(window.HTMLAnchorElement.prototype, "click", function () {
		downloaded = this.download;
	});
	const render = () => root.render(React.createElement(ReviewProposal, value));
	value.history = {
		items: [],
		selected: null,
		hasMore: true,
		loadMore: () => {
			value.history.items = [
				{ id: earlier.id, revision: earlier.revision, created_at: 1700000000 },
			];
			value.history.hasMore = false;
			render();
		},
		select: (id) => {
			value.history.selected = id;
			value.history.run = earlier;
			render();
		},
	};
	await act(async () => render());
	assert.ok(button("Earlier calculations"));
	await act(async () => button("Earlier calculations").click());
	const history = page.element.querySelector(
		'[aria-label="Calculation history"]',
	);
	await act(async () => history.querySelector("button").click());
	await act(async () => button("Download PDF").click());
	assert.match(downloaded, /\.pdf$/);
	value.preliminary = true;
	await act(async () => render());
	assert.ok(page.element.querySelector(".sc-draft-transfer form textarea"));
	assert.match(
		page.element.textContent,
		/Planned system: Storage for existing PV/,
	);
	assert.deepEqual(calls, ["inquiry/form"]);
});

for (const saved of [false, true])
	test(`an installer can send a preliminary direction with the original cart (saved Genie solution: ${saved})`, async (t) => {
		const page = setupDom(),
			root = createRoot(page.element),
			value = props(null);
		t.after(() => page.dispose(root));
		reflectNamedFormAction(t);
		const { emptyBrief } = await import("../src/domain/brief.ts");
		value.inputs = {
			brief: {
				...emptyBrief(),
				system_scope: saved ? "storage_addition" : "pv_only",
			},
		};
		if (saved)
			value.inputs.saved_solution_reference = {
				schema_version: 1,
				authority: "historical_user_input",
				solution_id: 45,
				title: "Saved equipment",
				kind: "genie",
				input: {},
				source_sha256: "a".repeat(64),
				recorded_items: [
					{ product_id: 4107, quantity: 2 },
					{ product_id: 1946, quantity: 4 },
				],
			};
		value.project.inputs = value.inputs;
		value.client.origin = location.origin;
		const calls = [];
		value.client.query = async (path) => {
			calls.push(path);
			const action =
				calls.length === 1
					? saved
						? "https://["
						: "https://example.invalid/wp-admin/admin-post.php"
					: "/wp-admin/admin-post.php";
			return {
				schema_version: 1,
				inquiry_lines: saved
					? [
							{
								product_id: 12,
								label: "Draft inverter",
								quantity: 1,
								project_id: null,
								project_title: null,
							},
						]
					: [],
				inquiry_form_html: `<form method="post" action="${action}"><input type="hidden" name="action" value="linker_inquiry"><textarea name="message" maxlength="5000"></textarea><button type="submit">Send inquiry</button></form>`,
			};
		};
		await act(async () =>
			root.render(React.createElement(ReviewProposal, value)),
		);
		assert.ok(button("Load inquiry form again"));
		assert.doesNotMatch(page.element.textContent, /could not be sent/);
		await act(async () => button("Load inquiry form again").click());
		const form = page.element.querySelector("form");
		form.querySelector("textarea").value = "Please call me back.";
		const direction = saved
			? "Planned system: Storage for existing PV"
			: "Planned system: Solar";
		assert.ok(page.element.textContent.includes(direction));
		assert.deepEqual(
			Array.from(page.element.querySelectorAll("tbody tr"), (row) =>
				Array.from(row.cells, (cell) => cell.textContent),
			),
			saved ? [["Draft inverter", "1"]] : [],
		);
		let message;
		form.addEventListener(
			"submit",
			(event) => {
				if (!event.defaultPrevented)
					message = new window.FormData(form).get("message");
				event.preventDefault();
			},
			{ once: true },
		);
		await act(async () => button("Send inquiry").click());
		assert.equal(message, `${direction}\n\nPlease call me back.`);
		assert.deepEqual(calls, ["inquiry/form", "inquiry/form"]);
		assert.equal(button("Generate project report"), undefined);
	});
