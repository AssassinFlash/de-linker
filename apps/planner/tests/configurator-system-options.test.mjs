import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, until, enter } from "./dom-fixture.mjs";
import german from "../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json" with { type: "json" };

const selection = {
	schema_version: 1,
	inverter_product_id: 101,
	battery_product_id: 201,
	modules_per_stack: 2,
	parallel_stacks: 1,
	accessory_product_ids: [],
	grid_phase: 3,
	operating_mode: "grid_connected",
	pv_dc_kw: 10,
	required_usable_kwh: null,
	required_discharge_ac_kw: null,
	product_revisions: { 101: "a".repeat(64), 201: "b".repeat(64) },
	equipment_use: { inverter: "retain", battery: "new" },
};
const candidates = ["unresolved", "violated"].map((status, index) => ({
	id: String(index + 1).repeat(64),
	assessment_sha256: String(index + 3).repeat(64),
	status,
	violated_checks: index,
	unresolved_checks: 1 - index,
	usable_energy_kwh: index ? 5 : 10,
	selection,
}));
const products = [
	{
		canonical_product_id: 101,
		product_id: 101,
		brand: "Linker",
		model: "Hybrid Actual",
		sku: "INV",
	},
	{
		canonical_product_id: 201,
		product_id: 201,
		brand: "Linker",
		model: "Battery Actual",
		sku: "BAT",
	},
];
const assessment = (candidate) => ({
	equipment_status: candidate.status,
	overall_status: candidate.status,
	selected_products: products,
	provisional_bill_of_materials: [
		{ product_id: 101, quantity: 1 },
		{ product_id: 201, quantity: 2 },
	],
	checks: [
		{
			id: "usable_energy",
			status: candidate.status,
			reason: "cited_usable_energy_and_sales_basis",
			actual: 10,
			required: 8,
			facts: [
				{
					value: 5,
					unit: "kWh",
					source: { url: "https://de-linker.com/uploads/battery.pdf", page: 2 },
				},
			],
		},
	],
	country_assessment: {
		status: "unresolved",
		country_code: null,
		reason: "versioned_country_rules_required",
	},
});
const run = {
	id: "a".repeat(32),
	project_id: "b".repeat(32),
	state: "succeeded",
	result: {
		search: {
			candidates,
			products,
			completion: "budget_exhausted",
		},
	},
};
const currentProducts = products.map((p) => ({
	...p,
	id: p.product_id,
	product_revision: "a".repeat(64),
	device_class: p.sku === "INV" ? "inverters" : "battery-systems",
	figures: {},
	documents:
		p.sku === "BAT"
			? [
					{
						url: "https://de-linker.com/uploads/battery.pdf",
						title: "Battery data",
					},
					{
						url: "https://de-linker.com/uploads/Battery-data.pdf",
						title: "Battery-data.pdf",
					},
				]
			: [],
}));
async function mount(t, props, catalog = currentProducts) {
	const dom = setupDom();
	const cache = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const { createRoot } = await import("react-dom/client");
	const { SystemOptions } =
		await import("../src/components/configurator/SystemOptions.tsx");
	const root = createRoot(dom.element);
	t.after(async () => {
		await dom.dispose(root);
		cache.clear();
	});
	const render = async (next = props) =>
		act(async () =>
			root.render(
				React.createElement(
					QueryClientProvider,
					{ client: cache },
					React.createElement(SystemOptions, {
						...next,
						client: {
							...next.client,
							async query(path, ...args) {
								if (path === "products/current")
									return {
										schema_version: 1,
										provider: "woocommerce",
										products: catalog,
									};
								if (path === "products/cards")
									return {
										cards: products.map((p) => ({
											id: p.product_id,
											label: p.model,
											product_url:
												"https://fixture.invalid/product/" + p.product_id,
										})),
									};
								return next.client.query(path, ...args);
							},
						},
					}),
				),
			),
		);
	await render();
	return render;
}

test("solar-only options show the inverter without battery sizing or adjustments", async (t) => {
	const solar = {
		...candidates[0],
		usable_energy_kwh: null,
		selection: {
			...selection,
			battery_product_id: null,
			modules_per_stack: null,
			parallel_stacks: null,
		},
	};
	const solarRun = {
		...run,
		result: { search: { ...run.result.search, candidates: [solar] } },
	};
	await mount(t, {
		run: solarRun,
		solarOnly: true,
		scope: "scope",
		locale: "en",
		selectedId: solar.id,
		comparison: { run: solarRun, candidate: solar },
		client: {
			isCurrentScope: () => true,
			query: async () => ({
				run_id: run.id,
				candidate_id: solar.id,
				assessment_sha256: solar.assessment_sha256,
				assessment: {
					...assessment(solar),
					checks: [],
					selected_products: [products[0]],
					provisional_bill_of_materials: [{ product_id: 101, quantity: 1 }],
				},
			}),
		},
	});
	assert.match(document.body.textContent, /Inverter model/);
	assert.match(document.body.textContent, /Compare with the saved version/);
	assert.doesNotMatch(
		document.body.textContent,
		/Usable capacity to confirm|Usable battery capacity|Battery model|Battery stacks|Battery modules per stack/,
	);
});

test("system cards use real candidate data, inspect evidence and select without mutating the candidate", async (t) => {
	const calls = [],
		selected = [];
	const client = {
		isCurrentScope: () => true,
		async query(path, body) {
			calls.push({ path, body });
			const candidate = candidates.find((c) => c.id === body.candidate_id);
			return {
				run_id: run.id,
				candidate_id: candidate.id,
				assessment_sha256: candidate.assessment_sha256,
				assessment: assessment(candidate),
			};
		},
	};
	const props = {
		run,
		client,
		scope: "scope",
		locale: "en-GB",
		disabled: false,
		selectedId: null,
		onSelect: async (c) => selected.push(c),
	};
	const render = await mount(t, props);
	await until(() => document.body.textContent.includes("Retained on site"));
	assert.equal(document.querySelectorAll(".sc-package").length, 2);
	assert.match(
		document.querySelector(".sc-package").textContent,
		/Linker Hybrid Actual/,
	);
	assert.match(document.querySelector(".sc-package").textContent, /10 kWh/);
	assert.match(document.body.textContent, /Search incomplete/);
	const overview = document.querySelector('[aria-label="System layout"]');
	assert.ok(overview, "the equipment option has a labelled system layout");
	assert.match(overview.textContent, /Solar capacity.*10 kWp/);
	assert.match(overview.textContent, /Inverter model.*Linker Hybrid Actual/);
	assert.match(overview.textContent, /Battery model.*Linker Battery Actual/);
	assert.doesNotMatch(overview.textContent, /Example/);
	const materials = [...document.querySelectorAll(".sc-equipment")];
	assert.ok(
		materials.some(
			(row) =>
				/Hybrid Actual/.test(row.textContent) &&
				/Retained on site/.test(row.textContent) &&
				/1/.test(row.textContent),
		),
	);
	assert.ok(
		materials.some(
			(row) =>
				/Battery Actual/.test(row.textContent) &&
				/New equipment/.test(row.textContent) &&
				/2/.test(row.textContent),
		),
	);
	await act(async () =>
		document.querySelector(".sc-selection-evidence > summary").click(),
	);
	await until(() => document.querySelector(".linker-source-card a"));
	assert.equal(
		document
			.querySelector(
				'a[href="https://de-linker.com/uploads/battery.pdf#page=2"]',
			)
			?.textContent.includes("2"),
		true,
	);
	const use = () =>
		[...document.querySelectorAll("button")].find(
			(b) => b.textContent === "Use this configuration",
		);
	await act(async () => use().click());
	assert.deepEqual(selected, [candidates[0]]);
	assert.equal(calls[0].path, "equipment/candidates/read");
	await render({ ...props, selectedId: candidates[0].id, disabled: true });
	assert.ok(
		[...document.querySelectorAll("button")].find(
			(b) => b.textContent === "Selected",
		).disabled,
	);
	const filter = document.querySelector("select");
	await act(async () => {
		filter.value = "violated";
		filter.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.equal(document.querySelectorAll(".sc-package").length, 1);
	await enter(document.querySelector('input[type="search"]'), "not a model");
	assert.equal(document.querySelectorAll(".sc-package").length, 0);
	assert.match(document.body.textContent, /No configurations match/);
});

test("selection evidence groups duplicate references by model and opens the cited PDF page", async (t) => {
	const item = candidates[0];
	const base = assessment(item);
	const citation = {
		url: "https://de-linker.com/uploads/Battery-data.pdf",
		page: 3,
		product_id: 201,
	};
	base.checks[0].facts = [{ value: 5, unit: "kWh", source: citation }];
	base.checks[0].documents = [citation, { ...citation, page: 11 }];
	await mount(t, {
		solarOnly: false,
		run,
		scope: "scope",
		locale: "en",
		selectedId: item.id,
		client: {
			isCurrentScope: () => true,
			query: async () => ({
				run_id: run.id,
				candidate_id: item.id,
				assessment_sha256: item.assessment_sha256,
				assessment: base,
			}),
		},
	});
	await until(() => document.body.textContent.includes("Retained on site"));
	await act(async () =>
		document.querySelector(".sc-selection-evidence > summary").click(),
	);
	await until(() => document.querySelector(".linker-source-card a"));
	const source = [...document.querySelectorAll("article")].find((card) =>
		card.textContent.includes("Battery-data.pdf"),
	);
	assert.ok(source, "readers can identify the source file");
	assert.match(source.textContent, /Battery Actual/);
	assert.deepEqual(
		[...source.querySelectorAll("a")].map((a) => a.href),
		[citation.url + "#page=3", citation.url + "#page=11"],
	);
});

test("withdrawn evidence keeps its identity and never links to replacement bytes", async (t) => {
	const item = candidates[0];
	const original = assessment(item);
	const citation = original.checks[0].facts[0].source;
	Object.assign(citation, {
		product_id: 201,
		document_id: "battery-doc",
		blob_sha256: "a".repeat(64),
	});
	await mount(
		t,
		{
			run,
			client: {
				isCurrentScope: () => true,
				query: async () => ({
					run_id: run.id,
					candidate_id: item.id,
					assessment_sha256: item.assessment_sha256,
					assessment: original,
				}),
			},
			scope: "scope",
			locale: "en",
			solarOnly: false,
			selectedId: item.id,
		},
		[],
	);
	await until(() => document.querySelector(".sc-selection-evidence > summary"));
	await act(async () =>
		document.querySelector(".sc-selection-evidence > summary").click(),
	);
	await until(() =>
		document
			.querySelector(".linker-source-card")
			?.textContent.includes("This document is currently unavailable."),
	);
	assert.match(
		document.querySelector(".linker-source-card").textContent,
		/Battery Actual/,
	);
	assert.equal(document.querySelector(".linker-source-card a"), null);
});

test("shared plant materials keep one merged quantity and distinguish same-model retained and new units", async (t) => {
	const first = {
		...selection,
		equipment_use: { inverter: "retain", battery: "retain" },
	};
	const second = {
		...selection,
		equipment_use: { inverter: "new", battery: "replace" },
	};
	const candidate = {
		...candidates[0],
		plant: {
			schema_version: 1,
			requirements: {},
			units: [
				{ id: "existing", name: "Existing system", selection: first },
				{ id: "extension", name: "Extension", selection: second },
			],
			parallel_groups: [],
		},
	};
	delete candidate.selection;
	const rootAssessment = {
		...assessment(candidate),
		model: "woo_multi_converter_plant_v1",
		checks: [
			{
				id: "plant:backup_runtime",
				status: "unresolved",
				reason:
					"backup_duration_requires_starting_energy_and_documented_losses",
				facts: [],
				actual: { usable_energy_kwh: 45, discharge_upper_bound_kw: 8 },
				required: { load_kw: 7, duration_hours: 6, ac_load_energy_kwh: 42 },
			},
		],
		provisional_bill_of_materials: [
			{ product_id: 101, quantity: 2 },
			{ product_id: 201, quantity: 4 },
		],
		systems: [
			{
				id: "existing",
				name: "Existing system",
				selection: first,
				assessment: assessment(candidate),
			},
			{
				id: "extension",
				name: "Extension",
				selection: second,
				assessment: assessment(candidate),
			},
		],
	};
	const client = {
		isCurrentScope: () => true,
		async query() {
			return {
				run_id: run.id,
				candidate_id: candidate.id,
				assessment_sha256: candidate.assessment_sha256,
				assessment: rootAssessment,
			};
		},
	};
	await mount(t, {
		run: {
			...run,
			result: { search: { ...run.result.search, candidates: [candidate] } },
		},
		client,
		scope: "plant",
		locale: "en-GB",
		disabled: false,
		selectedId: null,
		onSelect: async () => {},
	});
	await until(() => document.querySelectorAll(".sc-equipment").length === 2);
	const inverter = document.querySelector(".sc-equipment");
	assert.match(
		inverter.textContent,
		/Existing system · Retained on site · × 1/,
	);
	assert.match(inverter.textContent, /Extension · New equipment · × 1/);
	assert.equal(
		inverter.querySelector(".linker-product-card__qty").textContent,
		"× 2",
	);
	assert.match(
		document.querySelectorAll(".sc-equipment")[1].textContent,
		/Replacement equipment/,
	);
	assert.match(document.body.textContent, /Whole-site backup/);
	assert.match(document.body.textContent, /Backup load7 kW/);
	assert.match(document.body.textContent, /Backup power upper bound8 kW/);
});

test("backup comparison shows the closest evidence-supported options first and keeps every candidate reachable", async (t) => {
	const options = [
		[13.5, "violated"],
		[13.5, "violated"],
		[18, "violated"],
		[22.5, "unresolved"],
		[27, "unresolved"],
		[null, "unresolved"],
	].map(([usable_energy_kwh, status], index) => ({
		...candidates[0],
		id: String(index + 1).repeat(64),
		usable_energy_kwh,
		status,
	}));
	const client = {
		isCurrentScope: () => true,
		async query(_path, body) {
			const item = options.find((option) => option.id === body.candidate_id);
			return {
				run_id: run.id,
				candidate_id: item.id,
				assessment_sha256: item.assessment_sha256,
				assessment: assessment(item),
			};
		},
	};
	await mount(t, {
		run: {
			...run,
			result: {
				search: {
					...run.result.search,
					candidates: options,
					backup_demand: {
						load_kw: 5,
						duration_hours: 4,
						ac_load_energy_kwh: 20,
					},
				},
			},
		},
		client,
		scope: "backup-fit",
		locale: "en-GB",
		disabled: false,
		selectedId: null,
		onSelect: async () => {},
	});
	const cards = () => [...document.querySelectorAll(".sc-package")];
	const capacities = () =>
		cards().map(
			(card) => card.querySelector(".sc-package-capacity strong").textContent,
		);
	assert.deepEqual(capacities(), [
		"22.5 kWh",
		"27 kWh",
		"Usable capacity to confirm",
	]);
	assert.match(cards()[0].textContent, /2.5 kWh capacity margin before losses/);
	assert.match(cards()[0].textContent, /Backup duration to confirm/);
	assert.match(cards()[0].textContent, /1 stack × 2 battery modules/);
	assert.match(document.body.textContent, /5 kW × 4 h = 20 kWh/);
	assert.match(document.body.textContent, /Some checks are still open/);
	const pager = document.querySelector('nav[aria-label="Configurations"]');
	assert.ok(pager.classList.contains("sc-actions"));
	await act(async () => pager.querySelectorAll("button")[1].click());
	assert.deepEqual(capacities(), ["18 kWh", "13.5 kWh", "13.5 kWh"]);
	assert.match(cards()[0].textContent, /2 kWh below the backup load energy/);
	assert.equal(options[0].usable_energy_kwh, 13.5);
});

test("initial comparison shows three options and more keeps the service order", async (t) => {
	const options = Array.from({ length: 7 }, (_, index) => ({
		...candidates[0],
		id: String(index + 1).repeat(64),
		usable_energy_kwh: index + 1,
	}));
	const client = {
		isCurrentScope: () => true,
		async query(path, body) {
			const candidate = options.find((c) => c.id === body.candidate_id);
			return {
				run_id: run.id,
				candidate_id: candidate.id,
				assessment_sha256: candidate.assessment_sha256,
				assessment: assessment(candidate),
			};
		},
	};
	await mount(t, {
		run: {
			...run,
			result: { search: { ...run.result.search, candidates: options } },
		},
		client,
		scope: "pages",
		locale: "en-GB",
		disabled: false,
		selectedId: options[0].id,
		onSelect: async () => {},
	});
	const cards = () => [...document.querySelectorAll(".sc-package")];
	assert.equal(cards().length, 3);
	assert.deepEqual(
		cards().map(
			(card) => card.querySelector(".sc-package-capacity strong").textContent,
		),
		["1 kWh", "2 kWh", "3 kWh"],
	);
	assert.equal(cards()[0].dataset.selected, "true");
	assert.equal(cards()[0].hasAttribute("aria-pressed"), false);
	await act(async () =>
		[...document.querySelectorAll("button")]
			.find((button) => button.textContent === "More configurations")
			.click(),
	);
	assert.deepEqual(
		cards().map(
			(card) => card.querySelector(".sc-package-capacity strong").textContent,
		),
		["4 kWh", "5 kWh", "6 kWh"],
	);
});

test("save a selected configuration, adjust its assembly and restore the comparison", async (t) => {
	const options = candidates.map((candidate, index) => ({
		...candidate,
		selection: { ...candidate.selection, modules_per_stack: index + 2 },
	}));
	const selected = [];
	const snapshots = [];
	const client = {
		isCurrentScope: () => true,
		async query(_path, body) {
			const item = options.find((option) => option.id === body.candidate_id);
			return {
				run_id: run.id,
				candidate_id: item.id,
				assessment_sha256: item.assessment_sha256,
				assessment: assessment(item),
			};
		},
	};
	const props = {
		run: {
			...run,
			result: { search: { ...run.result.search, candidates: options } },
		},
		client,
		scope: "comparison",
		locale: "en-GB",
		disabled: false,
		selectedId: options[0].id,
		comparison: null,
		onSaveComparison: (snapshot) => snapshots.push(snapshot),
		onSelect: async (item) => selected.push(item),
	};
	const render = await mount(t, props);
	const button = (label) =>
		[...document.querySelectorAll("button")].find(
			(item) => item.textContent === label,
		);
	const change = async (label, value) =>
		act(async () => {
			const input = [...document.querySelectorAll("label")]
				.find((item) => item.querySelector("span")?.textContent === label)
				?.querySelector("select");
			assert.ok(input, label);
			input.value = value;
			input.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	await until(() => document.body.textContent.includes("Retained on site"));
	await act(async () => button("Save a comparison").click());
	assert.equal(snapshots.length, 1);
	await render({ ...props, comparison: snapshots[0] });
	await change("Battery modules per stack", "3");
	await until(() => selected.length > 0);
	assert.deepEqual(selected, [options[1]]);
	await render({
		...props,
		selectedId: options[1].id,
		comparison: snapshots[0],
	});
	const table = document.querySelector("table");
	assert.match(table.textContent, /Saved version.*Current/);
	assert.match(table.textContent, /10 kWh.*5 kWh/);
	await act(async () => button("Use saved version").click());
	assert.deepEqual(selected, [options[1], options[0]]);
});

test("unverified detail cannot be selected and a failed detail read can be retried", async (t) => {
	let attempts = 0,
		selected = 0;
	const client = {
		isCurrentScope: () => true,
		async query() {
			attempts++;
			if (attempts === 1) throw new Error("unavailable");
			return {
				run_id: run.id,
				candidate_id: candidates[0].id,
				assessment_sha256: candidates[0].assessment_sha256,
				assessment: assessment(candidates[0]),
			};
		},
	};
	await mount(t, {
		run,
		client,
		scope: "retry",
		locale: "en-GB",
		disabled: false,
		selectedId: null,
		onSelect: async () => selected++,
	});
	await until(() => document.querySelector('[role="alert"]'));
	const useFirst = () => document.querySelector(".sc-package button");
	assert.equal(useFirst().disabled, true);
	await act(async () =>
		[...document.querySelectorAll("button")]
			.find((b) => b.textContent === "Try again")
			.click(),
	);
	await until(() => !useFirst().disabled);
	assert.equal(attempts, 2);
	assert.equal(selected, 0);
});

test("demand comparison labels optimistic bounds and the actual profile horizon", async (t) => {
	const candidate = {
		...candidates[0],
		demand: {
			status: "bounded",
			reason: "optimistic_profile_bound",
			basis:
				"optimistic_full_initial_storage_lossless_upper_bound_not_dispatch",
			additional_pv_use_upper_kwh: 3,
			peak_import_lower_bound_kw: 140.1,
			missing_facts: [],
			source_facts: [],
		},
	};
	const demand = {
		model: "profile_physical_bounds_v1",
		controller: "peak_shaving_with_reserve_v1",
		peak_target_kw: 190,
		horizon_start_utc: "2020-01-01T00:00:00+00:00",
		horizon_end_utc: "2020-01-01T04:00:00+00:00",
		baseline: {
			load_kwh: 8,
			pv_available_kwh: 8,
			direct_pv_use_kwh: 4,
			grid_import_kwh: 4,
			grid_export_kwh: 4,
			peak_grid_import_kw: 194.1,
			over_target_kwh: 1.025,
		},
	};
	const client = {
		isCurrentScope: () => true,
		async query() {
			return {
				run_id: run.id,
				candidate_id: candidate.id,
				assessment_sha256: candidate.assessment_sha256,
				assessment: assessment(candidate),
			};
		},
	};
	const props = {
		run: {
			...run,
			result: {
				search: { ...run.result.search, demand, candidates: [candidate] },
			},
		},
		client,
		scope: "bounds",
		locale: "en-GB",
		disabled: false,
		selectedId: null,
		onSelect: async () => {},
	};
	const render = await mount(t, props);
	assert.match(
		document.querySelector(".sc-package").textContent,
		/Additional solar use, upper bound/,
	);
	assert.match(document.querySelector(".sc-package").textContent, /3 kWh/);
	assert.match(
		document.querySelector(".sc-package").textContent,
		/Grid import peak, lower bound/,
	);
	assert.match(document.body.textContent, /Target grid import limit\s*190 kW/);
	assert.match(
		document.body.textContent,
		/Grid import peak without storage\s*194\.1 kW/,
	);
	assert.match(document.querySelector(".sc-package").textContent, /140\.1 kW/);
	assert.match(
		document.querySelector(".sc-package").textContent,
		/Further checks required/,
	);
	assert.match(document.body.textContent, /2020/);
	assert.match(document.body.textContent, /lossless/);
	assert.match(
		document.body.textContent,
		/Only surplus solar energy stored during this period counts towards the upper bound/,
	);
	assert.match(
		document.body.textContent,
		/The lower bound assumes a full battery at the start/,
	);
	assert.equal(document.body.textContent.includes("simulated savings"), false);

	window.wp.i18n.__ = (message) =>
		german.locale_data.messages[message]?.[0] ?? message;
	await render({ ...props, locale: "de-DE" });
	assert.match(
		document.body.textContent,
		/Gewünschte Netzbezugsgrenze\s*190 kW/,
	);
	assert.match(
		document.body.textContent,
		/Netzbezugsspitze ohne Speicher\s*194,1 kW/,
	);
	assert.match(
		document.querySelector(".sc-package").textContent,
		/Untergrenze der Netzbezugsspitze:\s*140,1 kW/,
	);
	assert.match(
		document.querySelector(".sc-package").textContent,
		/Weitere Prüfung erforderlich/,
	);
	assert.match(
		document.body.textContent,
		/Die Untergrenze setzt einen zu Beginn voll geladenen Speicher/,
	);
	const { peak_target_kw: _, ...profile } = demand;
	const selfUse = {
		...props,
		run: {
			...run,
			result: {
				search: {
					...run.result.search,
					demand: {
						...profile,
						controller: "self_consumption_with_reserve_v1",
						baseline: { ...demand.baseline, over_target_kwh: null },
					},
					candidates: [
						{
							...candidate,
							demand: { ...candidate.demand, peak_import_lower_bound_kw: null },
						},
					],
				},
			},
		},
	};
	await render({ ...selfUse, locale: "de-DE" });
	assert.match(
		document.body.textContent,
		/Nur in diesem Zeitraum gespeicherte PV-Überschüsse zählen zur Obergrenze/,
	);
	assert.doesNotMatch(document.body.textContent, /zu Beginn voll/);
	window.wp.i18n.__ = (message) => message;
	await render(selfUse);
	assert.match(
		document.body.textContent,
		/Only surplus solar energy stored during this period counts towards the upper bound/,
	);
	assert.doesNotMatch(document.body.textContent, /full battery/);
});

test("retaining an unverified inverter shows the measured baseline without a candidate", async (t) => {
	const retained = {
		...run,
		result: {
			retained_inverter: {
				existing_system: {
					schema_version: 1,
					name: "West barn",
					inverter_power_kw: 7.5,
					keep_inverter: true,
				},
				requirements: {
					schema_version: 1,
					grid_phase: null,
					operating_mode: null,
					pv_dc_kw: null,
					required_usable_kwh: 15,
					required_discharge_ac_kw: null,
				},
				profile_baseline: {
					model: "profile_physical_bounds_v1",
					controller: "self_consumption_with_reserve_v1",
					horizon_start_utc: "2024-03-30T23:00:00+00:00",
					horizon_end_utc: "2024-03-31T01:00:00+00:00",
					interval_count: 2,
					baseline: {
						load_kwh: 4,
						pv_available_kwh: 4,
						direct_pv_use_kwh: 2,
						grid_import_kwh: 2,
						grid_export_kwh: 2,
						peak_grid_import_kw: 2,
						over_target_kwh: 0,
					},
				},
			},
		},
	};
	await mount(t, {
		run: retained,
		client: {
			isCurrentScope: () => true,
			query: () => assert.fail("no equipment candidate"),
		},
		scope: "retained",
		locale: "en",
		disabled: false,
		selectedId: null,
		onSelect: async () => assert.fail("no substitute"),
	});
	assert.match(document.body.textContent, /West barn · 7.5 kW/);
	assert.match(document.body.textContent, /Electricity use4 kWh/);
	assert.match(document.body.textContent, /Grid import without storage2 kWh/);
	assert.equal(document.querySelectorAll(".sc-package").length, 0);
});

test("an 11.09 kWp project compares the nearest cited AC ratings before paging, without promising grid approval", async (t) => {
	const options = [25, 30, 20, 12, 10].map((kw, i) => ({
		...candidates[0],
		id: String(i + 1).repeat(64),
		nominal_ac_kw: kw,
		usable_energy_kwh: kw,
		selection: { ...selection, pv_dc_kw: 11.09 },
	}));
	const client = {
		isCurrentScope: () => true,
		query: async (_path, body) => {
			const c = options.find((row) => row.id === body.candidate_id);
			return {
				run_id: run.id,
				candidate_id: c.id,
				assessment_sha256: c.assessment_sha256,
				assessment: assessment(c),
			};
		},
	};
	await mount(t, {
		run: {
			...run,
			result: { search: { ...run.result.search, candidates: options } },
		},
		client,
		scope: "fit",
		locale: "en",
		disabled: false,
		selectedId: null,
		onSelect: async () => {},
	});
	assert.deepEqual(
		Array.from(
			document.querySelectorAll(".sc-package-capacity strong"),
			(n) => n.textContent,
		),
		["12 kWh", "10 kWh", "20 kWh"],
	);
	assert.doesNotMatch(
		document.body.textContent,
		/None of the configurations found|Electrical checks passed/,
	);
});
