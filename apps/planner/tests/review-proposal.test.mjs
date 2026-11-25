import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { setupDom, deferred } from "./dom-fixture.mjs";
import { useReportLogo } from "../src/components/configurator/ReportLogo.tsx";
import { ReviewProposal as Proposal } from "../src/components/configurator/ReviewProposal.tsx";
import fixture from "./fixtures/index.ts";

function ReviewProposal(props) {
	const branding = useReportLogo(
		props.blocked || props.operations.busy,
		props.runLogo,
	);
	return React.createElement(Proposal, { ...props, branding });
}

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
	const solarTitle = value.run.result.report.sections.find(
		(section) => section.id === "pv-components",
	).title;
	const solarSection = [...document.querySelectorAll(".sc-card")].find(
		(section) => section.querySelector("h2")?.textContent === solarTitle,
	);
	assert.match(
		solarSection.querySelector("table").textContent,
		/Generisches 460-W-PV-Modul/,
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

test("the review overview shows the customer’s actual design inputs", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element),
		value = props(null);
	t.after(() => page.dispose(root));
	value.inputs = {
		known_panel_details: { count: 12, power_w: 430 },
		backup_demand: { load_kw: 3, duration_hours: 2 },
	};
	await act(async () =>
		root.render(React.createElement(ReviewProposal, value)),
	);
	const overview = page.element.querySelector(".sc-report-overview");
	assert.match(overview.textContent, /12/);
	assert.match(overview.textContent, /430 Wp/);
	assert.match(overview.textContent, /3 kW/);
	assert.match(overview.textContent, /2 h/);
	assert.doesNotMatch(overview.textContent, /Canal house/);
});

test("site installation requirements have their own section alongside equipment and panel layout", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element);
	t.after(() => page.dispose(root));
	const value = props(),
		report = value.run.result.report;
	const base = {
		id: "bom",
		title: "Selected equipment",
		paragraphs: [],
		rows: [],
		table: {
			columns: ["Quantity", "Product"],
			rows: [["1", "Selected inverter"]],
		},
	};
	const solar = report.sections.find(
		(section) => section.id === "pv-components",
	);
	report.sections = [
		base,
		{
			...base,
			id: "site-materials",
			title: "Site installation materials",
			table: {
				columns: ["Quantity", "Requirement"],
				rows: [["4", "Mounting rails"]],
			},
		},
		solar,
	];
	await act(async () =>
		root.render(React.createElement(ReviewProposal, value)),
	);
	const areas = [...document.querySelectorAll(".sc-report-table")].filter(
		(section) => !section.closest("dialog"),
	);
	assert.deepEqual(
		areas.map((section) => section.getAttribute("aria-label")),
		[base.title, "Site installation materials", solar.title],
	);
	assert.match(areas[1].textContent, /Mounting rails/);
});
test("the itemised report keeps its CSV with the material rows and identifies the PDF revision", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element),
		value = props();
	t.after(() => page.dispose(root));
	await act(async () =>
		root.render(React.createElement(ReviewProposal, value)),
	);
	const csv = button("Download bill of materials (CSV)");
	assert.ok(
		csv
			?.closest("section")
			?.querySelector(":scope > div > .sc-report-table table"),
		"download is beside the frozen parts it exports",
	);
	assert.equal(
		[...page.element.querySelectorAll("button")].filter(
			(b) => b.textContent === csv.textContent,
		).length,
		1,
	);
	const pdf = button("Download PDF");
	assert.equal(
		pdf.closest("section").querySelector(".sc-report-meta")?.textContent,
		`Revision ${value.run.revision}`,
	);
});

test("a brief-only project can retry an unavailable report list and open the frozen PDF", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element),
		value = props(null);
	t.after(() => page.dispose(root));
	const { emptyBrief } = await import("../src/domain/brief.ts");
	value.inputs = {
		brief: { ...emptyBrief(), system_scope: "storage_addition" },
	};
	const saved = props().run;
	const render = () => root.render(React.createElement(ReviewProposal, value));
	const downloaded = [];
	value.client.reportPdf = async (project, asset, _scope, _signal, sha) => {
		downloaded.push([project, asset, sha]);
		return new Blob(["%PDF-"]);
	};
	t.mock.method(window.HTMLAnchorElement.prototype, "click", function () {});
	value.history = {
		items: [],
		selected: null,
		loadFailed: true,
		hasMore: false,
		loadMore() {
			Object.assign(value.history, {
				loadFailed: false,
				items: [
					{ id: saved.id, revision: saved.revision, created_at: 1700000000 },
				],
			});
			render();
		},
		select(id) {
			Object.assign(value.history, { selected: id, run: saved });
			render();
		},
	};
	await act(async () => render());
	const history = () =>
		page.element.querySelector('[aria-label="Calculation history"]');
	assert.ok(
		history()?.querySelector('[role="alert"]'),
		"failed first page must stay visible",
	);
	await act(async () =>
		[...history().querySelectorAll("button")]
			.find((b) => b.textContent === "Try again")
			.click(),
	);
	await act(async () => history().querySelector("button").click());
	await act(async () => button("Download PDF").click());
	assert.deepEqual(downloaded, [
		[
			saved.project_id,
			saved.result.prepared_asset.id,
			saved.result.prepared_asset.content_sha256,
		],
	]);
	assert.equal(button("Add selected products to solution draft"), undefined);
});

for (const historical of [false, true]) {
	test(
		"a panel-only " +
			(historical ? "historical" : "current") +
			" report shows one labeled layout and still offers its files",
		async (t) => {
			const page = setupDom(),
				root = createRoot(page.element);
			t.after(() => page.dispose(root));
			const value = props(),
				report = value.run.result.report;
			const solar = report.sections.find(
				(section) => section.id === "pv-components",
			);
			solar.title = "Solar panel layout";
			solar.table.columns = ["Quantity", "Panel parameters", "Rated power"];
			report.sections = [solar];
			if (historical)
				value.history = {
					items: [],
					selected: value.run.id,
					run: value.run,
					select() {},
				};
			await act(async () =>
				root.render(React.createElement(ReviewProposal, value)),
			);
			const layouts = [...document.querySelectorAll("section")].filter(
				(section) =>
					section.querySelector(":scope > header > :is(h2,h4)")?.textContent ===
						"Solar panel layout" && !section.closest("dialog"),
			);
			assert.equal(layouts.length, 1);
			assert.match(layouts[0].textContent, /Generisches 460-W-PV-Modul/);
			assert.deepEqual(
				[
					...layouts[0].querySelectorAll(
						"tbody tr:first-child td .sc-bom-label",
					),
				].map((e) => e.textContent),
				solar.table.columns,
			);
			assert.ok(button("Download PDF"));
			assert.ok(button("Download bill of materials (CSV)"));
			assert.ok(button("Preview report"));
		},
	);
}

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

test("a report citation keeps the document and exact page pinned to its revision", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element),
		value = props();
	t.after(() => page.dispose(root));
	const link =
		"https://de-linker.com/wp-content/uploads/2026/legacy-manual.pdf#page=37";
	value.run.result.report.sections = [
		{
			id: "pv",
			title: "PV generation",
			paragraphs: [],
			rows: [
				{ label: "Data source", value: "Commissioning manual", href: link },
			],
			table: null,
		},
	];
	await act(async () =>
		root.render(React.createElement(ReviewProposal, value)),
	);
	const source = page.element.querySelector("details .linker-source-card");
	assert.equal(
		source.querySelector("strong").textContent,
		"Commissioning manual",
	);
	assert.equal(source.querySelector("a").href, link);
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
	assert.match(dialog.textContent, /Generisches 460-W-PV-Modul/);
	assert.deepEqual(requested[0]?.slice(0, 3), [
		value.run.project_id,
		asset.id,
		scope,
	]);
	assert.equal(requested[0][4], asset.content_sha256);
	assert.equal(dialog.querySelector("object,embed"), null);
	assert.ok(dialog.querySelector(".sc-report-readable section h3"));
	const pdfLink = dialog.querySelector("a[target='_blank'][href^='blob:']");
	assert.equal(pdfLink.textContent, "Open report PDF");
	assert.equal(pdfLink.rel, "noopener noreferrer");
	await act(async () => button("Close").click());
	assert.equal(dialog.open, false);
	assert.deepEqual(revoked, ["blob:https://fixture.invalid/current-report"]);
});

test("a preliminary review exports PDF and materials on demand from the same project revision", async (t) => {
	const { InquiryExportBar } =
		await import("../src/components/configurator/InquiryExportBar.tsx");
	const page = setupDom(),
		root = createRoot(page.element),
		value = props(),
		prepared = [],
		downloads = [];
	t.after(() => page.dispose(root));
	const run = value.run;
	value.project.revision = run.revision;
	const client = {
		isCurrentScope: () => true,
		async reportPdf(project, asset) {
			downloads.push([project, asset]);
			return new Blob(["pdf"]);
		},
		async reportCsv(project, asset) {
			downloads.push([project, asset]);
			return new Blob(["csv"]);
		},
	};
	const anchors = window.HTMLAnchorElement.prototype;
	const click = anchors.click;
	anchors.click = () => {};
	t.after(() => {
		anchors.click = click;
	});
	await act(async () =>
		root.render(
			React.createElement(InquiryExportBar, {
				project: value.project,
				client,
				scope,
				locale: run.result.report.locale,
				logo: null,
				logoField: null,
				blocked: false,
				prepare: async (logo) => {
					prepared.push(logo);
					return run;
				},
			}),
		),
	);
	assert.deepEqual(prepared, []);
	await act(async () => button("Download PDF").click());
	await act(async () => button("Download bill of materials (CSV)").click());
	assert.deepEqual(prepared, [null]);
	assert.deepEqual(downloads, [
		[run.project_id, run.result.prepared_asset.id],
		[run.project_id, run.result.prepared_attachments.bill_of_materials_csv.id],
	]);
});

test("the first PDF download after picking a logo uses the new branded file", async (t) => {
	const { until } = await import("./dom-fixture.mjs");
	const page = setupDom(),
		root = createRoot(page.element),
		value = props(),
		logos = [],
		downloads = [];
	t.after(() => page.dispose(root));
	value.project.revision = value.run.revision;
	const branded = structuredClone(value.run);
	branded.id = "e".repeat(32);
	branded.result.prepared_asset.id = "b".repeat(32);
	value.client.reportPdf = async (_project, asset) => {
		downloads.push(asset);
		return new Blob(["pdf"]);
	};
	const lastReader = globalThis.FileReader;
	globalThis.FileReader = window.FileReader;
	const anchors = window.HTMLAnchorElement.prototype;
	const click = anchors.click;
	anchors.click = () => {};
	t.after(() => {
		globalThis.FileReader = lastReader;
		anchors.click = click;
	});
	await act(async () =>
		root.render(
			React.createElement(ReviewProposal, {
				...value,
				inquiry: React.createElement("form"),
				prepareExport: async (logo) => {
					logos.push(logo);
					return branded;
				},
			}),
		),
	);
	const input = document.querySelector('input[type="file"]');
	Object.defineProperty(input, "files", {
		value: [new window.File(["mark"], "mark.png", { type: "image/png" })],
	});
	await act(async () =>
		input.dispatchEvent(new window.Event("change", { bubbles: true })),
	);
	await until(() => button("Remove logo"));
	await act(async () => button("Download PDF").click());
	assert.deepEqual(logos, ["data:image/png;base64,bWFyaw=="]);
	assert.deepEqual(downloads, [branded.result.prepared_asset.id]);
	await act(async () =>
		root.render(
			React.createElement(ReviewProposal, {
				...value,
				run: branded,
				inquiry: React.createElement("form"),
				prepareExport: async (logo) => {
					logos.push(logo);
					return value.run;
				},
			}),
		),
	);
	await act(async () => button("Remove logo").click());
	await act(async () => button("Download PDF").click());
	assert.deepEqual(logos, ["data:image/png;base64,bWFyaw==", null]);
	assert.deepEqual(downloads, [
		branded.result.prepared_asset.id,
		value.run.result.prepared_asset.id,
	]);
});

test("generating with the chosen logo then downloading PDF and CSV creates only one report", async (t) => {
	const { until } = await import("./dom-fixture.mjs");
	const page = setupDom(),
		root = createRoot(page.element),
		value = props(),
		created = [],
		downloads = [];
	t.after(() => page.dispose(root));
	value.project.revision = value.run.revision;
	value.locale = value.run.result.report.locale;
	const oldReader = globalThis.FileReader;
	globalThis.FileReader = window.FileReader;
	const anchor = window.HTMLAnchorElement.prototype,
		click = anchor.click;
	anchor.click = () => {};
	t.after(() => {
		globalThis.FileReader = oldReader;
		anchor.click = click;
	});
	const generate = (data) => {
		created.push(data);
		return value.run;
	};
	value.client.reportPdf = async (_project, id) => {
		downloads.push(id);
		return new Blob(["pdf"]);
	};
	value.client.reportCsv = async (_project, id) => {
		downloads.push(id);
		return new Blob(["csv"]);
	};
	await act(async () =>
		root.render(
			React.createElement(ReviewProposal, { ...value, run: null, generate }),
		),
	);
	const input = document.querySelector('input[type="file"]');
	Object.defineProperty(input, "files", {
		value: [new window.File(["mark"], "logo.png", { type: "image/png" })],
	});
	await act(async () =>
		input.dispatchEvent(new window.Event("change", { bubbles: true })),
	);
	await until(() => button("Remove logo"));
	await act(async () => button("Generate project report").click());
	const review = () =>
		React.createElement(ReviewProposal, {
			...value,
			inquiry: React.createElement("form"),
			runLogo: created[0],
			prepareExport: async (logo) => generate(logo),
		});
	await act(async () => root.render(review()));
	await act(async () => button("Download PDF").click());
	await act(async () => button("Download bill of materials (CSV)").click());
	assert.deepEqual(created, ["data:image/png;base64,bWFyaw=="]);
	assert.deepEqual(downloads, [
		value.run.result.prepared_asset.id,
		value.run.result.prepared_attachments.bill_of_materials_csv.id,
	]);
	await act(async () =>
		root.render(React.createElement("section", null, "Fine-tune")),
	);
	await act(async () => root.render(review()));
	await act(async () => button("Download PDF").click());
	await act(async () => button("Download bill of materials (CSV)").click());
	assert.deepEqual(created, ["data:image/png;base64,bWFyaw=="]);
	assert.deepEqual(downloads.slice(2), [
		value.run.result.prepared_asset.id,
		value.run.result.prepared_attachments.bill_of_materials_csv.id,
	]);
	assert.equal(
		document.querySelector(".sc-report-logo img")?.getAttribute("src"),
		created[0],
	);
	await act(async () => button("Remove logo").click());
	await act(async () => button("Download PDF").click());
	assert.deepEqual(created, ["data:image/png;base64,bWFyaw==", null]);
});

test("a guest can add a first selection to the draft from the inquiry review", async (t) => {
	const page = setupDom(),
		root = createRoot(page.element),
		value = props();
	t.after(() => page.dispose(root));
	value.run.result.has_draft_items = true;
	await act(async () =>
		root.render(
			React.createElement(ReviewProposal, {
				...value,
				inquiry: React.createElement("form"),
			}),
		),
	);
	const add = button("Add to solution draft");
	assert.ok(add);
	assert.equal(add.disabled, false);
	assert.equal(
		add.closest("details"),
		null,
		"the reviewed equipment action is visible immediately",
	);
	await act(async () =>
		root.render(
			React.createElement(ReviewProposal, {
				...value,
				inquiry: React.createElement("form"),
				recoverTransfer: true,
			}),
		),
	);
	assert.ok(add.isConnected, "an in-flight transfer keeps its mounted writer");
	await act(async () =>
		root.render(
			React.createElement(ReviewProposal, {
				...value,
				inquiry: React.createElement("form"),
			}),
		),
	);
	assert.equal(
		!add.closest("details"),
		true,
		"the confirmed receipt stays visible",
	);
});
