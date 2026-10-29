import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, enter } from "./dom-fixture.mjs";
import {
	CableForm,
	RouteForm,
} from "../src/components/installation/NetworkForms.tsx";
import { PvStringLinks } from "../src/components/installation/PvStringLinks.tsx";
import { InstallationEditor } from "../src/components/installation/InstallationEditor.tsx";
import { emptyGeometry } from "../src/domain/geometryCommands.ts";
import { manualSource } from "../src/domain/geometryEditing.ts";
import {
	acknowledgeSave,
	beginDraft,
	editDraft,
	prepareSave,
} from "../src/domain/draft.ts";
import {
	emptyInstallation,
	readInstallation,
	readInstallationReview,
} from "../src/domain/installation.ts";

test("staged route coordinates survive insertion and removal of another vertex", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	let saved;
	const route = {
		id: "path",
		name: "Fixture route",
		source_id: "survey",
		points: [
			{ east_m: 0, north_m: 0, height_m: 1 },
			{ east_m: 6, north_m: 8, height_m: 5 },
		],
		extra_length_m: 2,
		extra_length_note: "Explicit fixture",
	};
	const geometry = emptyGeometry();
	geometry.sources = [{ id: "survey", note: "Synthetic drawing" }];
	await act(async () =>
		root.render(
			React.createElement(RouteForm, {
				locale: "de-DE",
				geometry,
				plan: emptyInstallation(),
				route,
				cancel() {},
				onValidity() {},
				submit(value) {
					saved = value;
					return true;
				},
			}),
		),
	);
	const form = document.querySelector("form");
	const original = [...form.querySelectorAll("fieldset input")];
	await enter(original[0], "1,25");
	await enter(original[2], "2,5");
	const button = (text) =>
		[...form.querySelectorAll("button")].find((b) => b.textContent === text);
	await act(async () => button("Add route point").click());
	assert.equal(form.querySelectorAll("fieldset").length, 3);
	assert.equal(original[0].value, "1,25");
	assert.equal(original[2].value, "2,5");
	const middle = form.querySelectorAll("fieldset")[1];
	await act(async () => middle.querySelector("button").click());
	assert.equal(form.querySelectorAll("fieldset").length, 2);
	assert.equal(original[0].value, "1,25");
	await act(async () =>
		form.dispatchEvent(
			new window.Event("submit", { bubbles: true, cancelable: true }),
		),
	);
	assert.equal(saved.points[0].east_m, 1.25);
	assert.equal(saved.points[0].height_m, 2.5);
	assert.equal(saved.points[1].east_m, 6);
});

test("a declared cross-section is entered as a pair, omitted when open, and read back from the frozen revision", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const geometry = emptyGeometry();
	geometry.sources = [{ id: "survey", note: "Synthetic drawing" }];
	const plan = {
		...emptyInstallation(),
		instances: [
			{
				id: "a",
				name: "Inverter",
				product_id: null,
				product_revision: null,
				source_id: "survey",
				ports: [
					{
						id: "p",
						name: "PV +",
						position: { east_m: 0, north_m: 0, height_m: 1 },
					},
					{
						id: "q",
						name: "PV −",
						position: { east_m: 6, north_m: 0, height_m: 1 },
					},
				],
			},
		],
		circuits: [
			{
				id: "pv1",
				name: "Roof circuit",
				kind: "pv_dc",
				start: { instance_id: "a", port_id: "p" },
				end: { instance_id: "a", port_id: "q" },
			},
		],
		routes: [
			{
				id: "path",
				name: "Roof route",
				source_id: "survey",
				points: [
					{ east_m: 0, north_m: 0, height_m: 1 },
					{ east_m: 6, north_m: 0, height_m: 1 },
				],
				extra_length_m: 0,
				extra_length_note: "No allowance",
			},
		],
	};
	let saved,
		valid = true;
	const render = async (cable) =>
		act(async () =>
			root.render(
				React.createElement(CableForm, {
					locale: "de-DE",
					geometry,
					plan,
					cable,
					cancel() {},
					onValidity(value) {
						valid = value;
					},
					submit(value) {
						saved = value;
						return true;
					},
				}),
			),
		);
	const form = () => document.querySelector("form");
	const field = (name) => form().elements.namedItem(name);
	const apply = async () =>
		act(async () =>
			form().dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
		);
	await render(null);
	await enter(field("name"), "DC string 1");
	field("circuit").value = "pv1";
	field("route").value = "path";
	field("construction").value = "single_conductor";
	// Left empty, the specification stays open and the key is never written:
	// an explicit null would move the frozen input hash of an old project.
	await apply();
	assert.equal(saved.name, "DC string 1");
	assert.equal(Object.hasOwn(saved, "conductor"), false);
	// The reader keeps the absence: a stored run stays byte-identical.
	assert.equal(
		Object.hasOwn(
			readInstallation({ ...plan, cable_runs: [saved] }).cable_runs[0],
			"conductor",
		),
		false,
	);
	// Half a declaration is refused rather than guessed from the other half.
	await render(null);
	await enter(field("name"), "DC string 1");
	field("circuit").value = "pv1";
	field("route").value = "path";
	field("construction").value = "single_conductor";
	await enter(field("cross_section"), "6");
	const before = saved;
	await apply();
	assert.equal(saved, before);
	assert.equal(valid, false);
	assert.match(
		document.body.textContent,
		/declare the cross-section|leave both empty/i,
	);
	await enter(field("cross_section"), "");
	await enter(field("conductor_note"), "Project cable list");
	await apply();
	assert.equal(saved, before);
	assert.equal(valid, false);
	// Both halves together are one frozen declaration the reader keeps verbatim.
	await render(null);
	await enter(field("name"), "DC string 1");
	field("circuit").value = "pv1";
	field("route").value = "path";
	field("construction").value = "single_conductor";
	await enter(field("cross_section"), "6");
	await enter(field("conductor_note"), "Project cable list");
	await apply();
	assert.deepEqual(saved.conductor, {
		cross_section_mm2: 6,
		source_note: "Project cable list",
	});
	const stored = {
		...plan,
		cable_runs: [saved],
	};
	assert.deepEqual(readInstallation(stored).cable_runs[0].conductor, {
		cross_section_mm2: 6,
		source_note: "Project cable list",
	});
	// Re-opening the stored run shows the declaration instead of an empty form.
	await render(readInstallation(stored).cable_runs[0]);
	assert.equal(field("cross_section").value, "6");
	assert.equal(field("conductor_note").value, "Project cable list");
	assert.equal(valid, true);
});

test("saved string links opt in explicitly, retain stale declarations and bind reviewed identities", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const revision = "a".repeat(64),
		plan = {
			...emptyInstallation(),
			instances: [
				{
					id: "inverter",
					name: "Inverter",
					product_id: 6506,
					product_revision: revision,
					source_id: "survey",
					ports: [
						{
							id: "pv",
							name: "PV connection",
							position: { east_m: 0, north_m: 0, height_m: 1 },
						},
					],
				},
				{
					id: "roof",
					name: "Roof",
					product_id: null,
					product_revision: null,
					source_id: "survey",
					ports: [
						{
							id: "end",
							name: "String end",
							position: { east_m: 1, north_m: 0, height_m: 1 },
						},
					],
				},
			],
			circuits: [
				{
					id: "pv1",
					name: "Roof circuit",
					kind: "pv_dc",
					start: { instance_id: "inverter", port_id: "pv" },
					end: { instance_id: "roof", port_id: "end" },
				},
			],
		},
		strings = {
			schema_version: 1,
			inverter_product_id: 6506,
			minimum_ambient_c: null,
			temperature_source: null,
			strings: [
				{ id: "s1", mppt: 1, input: 1, module_ids: ["m1"] },
				{ id: "s2", mppt: 2, input: 1, module_ids: ["m2"] },
			],
		};
	assert.equal(Object.hasOwn(readInstallation(plan), "pv_string_links"), false);
	let current, update, valid;
	const writes = [];
	const validity = (value) => {
		valid = value;
	};
	function Harness(props) {
		const [value, setValue] = React.useState(plan);
		current = value;
		update = setValue;
		return React.createElement(PvStringLinks, {
			plan: value,
			savedInstallation: props.installation,
			savedStrings: props.strings,
			stringPlanChanged: props.changed ?? false,
			review: null,
			locale: "en",
			disabled: false,
			onValidity: validity,
			change(next) {
				writes.push(next);
				setValue(next);
				return true;
			},
		});
	}
	const render = async (savedStrings, installation, changed = false) =>
		act(async () =>
			root.render(
				React.createElement(Harness, {
					strings: savedStrings,
					installation,
					changed,
				}),
			),
		);
	const button = (text) =>
		[...document.querySelectorAll("button")].find(
			(b) => b.textContent === text,
		);
	const choose = async (select, value) =>
		act(async () => {
			select.value = value;
			select.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	await render(strings, plan);
	assert.equal(writes.length, 0);
	await act(async () => document.querySelector("input[type=checkbox]").click());
	assert.deepEqual(current.pv_string_links, []);
	await act(async () => button("Link string to circuit").click());
	assert.equal(valid, false);
	assert.equal(button("Apply changes").disabled, true);
	assert.deepEqual(
		[...document.querySelectorAll("select")].map((s) => s.value),
		["", ""],
	);
	await choose(document.querySelectorAll("select")[0], "s1");
	await choose(document.querySelectorAll("select")[1], "pv1");
	await act(async () =>
		document
			.querySelector("form")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
	);
	assert.deepEqual(current.pv_string_links, [
		{ string_id: "s1", circuit_id: "pv1" },
	]);
	assert.equal(valid, true);
	assert.equal(document.querySelector("input[type=checkbox]").disabled, true);
	const linked = structuredClone(current),
		prepared = { ...linked, geometry_sha256: revision },
		endpoints = [
			{
				side: "start",
				instance_id: "inverter",
				port_id: "pv",
				product_id: 6506,
				product_revision: revision,
			},
			{
				side: "end",
				instance_id: "roof",
				port_id: "end",
				product_id: null,
				product_revision: null,
			},
		],
		response = {
			schema_version: 1,
			method: "installation_route_takeoff_v1",
			project_id: "project",
			project_revision: 2,
			qualified: false,
			geometry_sha256: revision,
			input_sha256: "b".repeat(64),
			prepared_inputs: prepared,
			cables: [],
			pv_string_reconciliation: {
				schema_version: 1,
				scope: "declared_project_identity_only",
				qualified: false,
				pv_string_plan_sha256: "c".repeat(64),
				installation_input_sha256: "b".repeat(64),
				geometry_sha256: revision,
				plan_status: "available",
				rows: [
					{
						string_id: "s1",
						mppt: 1,
						input: 1,
						circuit_id: "pv1",
						status: "linked",
						endpoints,
						cable_runs: [],
						// A circuit without a recorded run: no run, so nothing to
						// declare a cross-section for.
						closure: {
							conductor: "not_recorded",
							quantity: "not_recorded",
							recorded: false,
							approval: "not_assessed",
						},
						reasons: ["cable_runs_missing"],
					},
					{
						string_id: "s2",
						mppt: 2,
						input: 1,
						circuit_id: null,
						status: "unlinked",
						endpoints: [],
						cable_runs: [],
						closure: {
							conductor: "not_recorded",
							quantity: "not_recorded",
							recorded: false,
							approval: "not_assessed",
						},
						reasons: [],
					},
				],
			},
		};
	assert.equal(
		readInstallationReview(response, linked, "project", strings, 2)
			.pv_string_reconciliation.rows[1].status,
		"unlinked",
	);
	for (const corrupt of [
		(value) => {
			delete value.project_revision;
		},
		(value) => {
			value.project_revision = 1;
		},
		(value) => {
			value.pv_string_reconciliation.rows[0].endpoints[0].product_revision =
				"d".repeat(64);
		},
		(value) => {
			value.pv_string_reconciliation.rows[1].status = "linked";
		},
		(value) => {
			value.pv_string_reconciliation.rows[0].cable_runs = [{ quantity: 2 }];
		},
		(value) => {
			value.pv_string_reconciliation.installation_input_sha256 = "e".repeat(64);
		},
		// A reply may not claim more than the frozen runs support.
		(value) => {
			value.pv_string_reconciliation.rows[0].closure.conductor = "declared";
		},
		(value) => {
			value.pv_string_reconciliation.rows[0].closure.recorded = true;
		},
		(value) => {
			value.pv_string_reconciliation.rows[0].closure.approval = "assessed";
		},
		(value) => {
			delete value.pv_string_reconciliation.rows[1].closure;
		},
	]) {
		const wrong = structuredClone(response);
		corrupt(wrong);
		assert.throws(() =>
			readInstallationReview(wrong, linked, "project", strings, 2),
		);
	}
	assert.throws(() =>
		readInstallation({
			...linked,
			pv_string_links: [
				...linked.pv_string_links,
				{ string_id: "s2", circuit_id: "pv1" },
			],
		}),
	);
	// Saved-source changes are explicit. They never rewrite a retained link.
	const renamed = { ...strings, strings: [...strings.strings].reverse() },
		newPlan = {
			...current,
			circuits: [{ ...plan.circuits[0], name: "Renamed circuit" }],
		};
	await act(async () => update(newPlan));
	await render(renamed, newPlan);
	assert.deepEqual(current.pv_string_links, linked.pv_string_links);
	assert.match(document.body.textContent, /Renamed circuit/);
	const stale = {
			...current,
			circuits: [{ ...plan.circuits[0], id: "pv2", name: "New saved circuit" }],
		},
		onlySecond = { ...strings, strings: [strings.strings[1]] },
		writesBeforeStale = writes.length;
	await act(async () => update(stale));
	await render(onlySecond, stale);
	assert.equal(writes.length, writesBeforeStale);
	assert.deepEqual(current.pv_string_links, linked.pv_string_links);
	assert.match(document.body.textContent, /Missing PV string: s1/);
	assert.match(document.body.textContent, /Missing circuit: pv1/);
	await act(async () => button("Edit").click());
	assert.deepEqual(
		[...document.querySelectorAll("select")].map((s) => s.value),
		["s1", "pv1"],
	);
	assert.equal(button("Apply changes").disabled, true);
	await choose(document.querySelectorAll("select")[0], "s2");
	await choose(document.querySelectorAll("select")[1], "pv2");
	await render(onlySecond, stale, true);
	assert.equal(button("Apply changes").disabled, true);
	await render(onlySecond, stale);
	await act(async () =>
		document
			.querySelector("form")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
	);
	assert.deepEqual(current.pv_string_links, [
		{ string_id: "s2", circuit_id: "pv2" },
	]);
	await act(async () => button("Remove link").click());
	assert.deepEqual(current.pv_string_links, []);
	await act(async () => document.querySelector("input[type=checkbox]").click());
	assert.equal(Object.hasOwn(current, "pv_string_links"), false);

	// The accepted preview survives saving its geometry-bound installation, but
	// remains tied to the exact project, scope and relevant saved inputs.
	const cache = new QueryClient(),
		geometry = emptyGeometry(),
		scope = "f".repeat(64),
		requests = [];
	t.after(() => cache.clear());
	let currentScope = scope,
		editorDraft = beginDraft({
			id: "project",
			title: "Synthetic installation",
			revision: 2,
			input_sha256: revision,
			inputs: { installation: linked, pv_string_plan: strings },
		}),
		updateEditor;
	const client = {
		isCurrentScope: (value) => value === currentScope,
		async query(path, body, queryScope) {
			if (path === "products/current")
				return { schema_version: 1, provider: "woocommerce", products: [] };
			assert.equal(path, "installation/review");
			requests.push({ body, queryScope });
			return structuredClone(response);
		},
	};
	function EditorHarness(props) {
		const [draft, setDraft] = React.useState(editorDraft);
		updateEditor = setDraft;
		return React.createElement(InstallationEditor, {
			inputs: draft.history.current,
			savedInputs: draft.baseline.inputs,
			savedRevision: draft.baseline.revision,
			geometry: props.geometry,
			client,
			session: { query_scope: props.scope },
			projectId: props.projectId,
			locale: "en",
			sceneModuleUrl: null,
			onValidity: validity,
			editGeometry: () => false,
			change(value) {
				editorDraft = editDraft(editorDraft, {
					...editorDraft.history.current,
					installation: value,
				});
				setDraft(editorDraft);
				return true;
			},
		});
	}
	const renderEditor = async (overrides = {}) =>
			act(async () =>
				root.render(
					React.createElement(
						QueryClientProvider,
						{ client: cache },
						React.createElement(EditorHarness, {
							projectId: "project",
							scope,
							geometry,
							...overrides,
						}),
					),
				),
			),
		preview = () => document.querySelector("table.lp-data-table");
	await renderEditor();
	assert.equal(preview(), null);
	await act(async () => button("Review routes and string links").click());
	assert.equal(requests.length, 1);
	assert.equal(requests[0].body.expected_revision, 2);
	assert.equal(requests[0].queryScope, scope);
	assert.equal(preview().querySelectorAll("tbody tr").length, 2);
	assert.deepEqual(editorDraft.history.current.installation, prepared);
	editorDraft = prepareSave(editorDraft, crypto.randomUUID(), {
		maxDepth: 32,
		maxBytes: 16777216,
	});
	const intent = editorDraft.pending;
	editorDraft = acknowledgeSave(editorDraft, intent, {
		...editorDraft.baseline,
		revision: 3,
		input_sha256: "d".repeat(64),
		inputs: intent.inputs,
	});
	await act(async () => updateEditor(editorDraft));
	assert.equal(preview().querySelectorAll("tbody tr").length, 2);
	assert.equal(requests.length, 1);
	const saved = editorDraft;
	const replaceDraft = async (value) =>
		act(async () => {
			editorDraft = value;
			updateEditor(value);
		});
	await replaceDraft({
		...saved,
		baseline: { ...saved.baseline, revision: 1 },
	});
	assert.equal(preview(), null);
	await replaceDraft(saved);
	await renderEditor({ projectId: "another-project" });
	assert.equal(preview(), null);
	currentScope = "e".repeat(64);
	await renderEditor({ scope: currentScope });
	assert.equal(preview(), null);
	currentScope = scope;
	await renderEditor({
		geometry: {
			...geometry,
			sources: [
				manualSource("survey", "Changed drawing", "Fixture permission"),
			],
		},
	});
	assert.equal(preview(), null);
	await renderEditor();
	await replaceDraft(
		editDraft(saved, {
			...saved.history.current,
			installation: { ...prepared, pv_string_links: [] },
		}),
	);
	assert.equal(preview(), null);
	const changedStrings = { ...strings, temperature_source: "Changed source" },
		changedInputs = {
			...saved.baseline.inputs,
			pv_string_plan: changedStrings,
		};
	await replaceDraft({
		...editDraft(saved, changedInputs),
		baseline: { ...saved.baseline, revision: 4, inputs: changedInputs },
	});
	assert.equal(preview(), null);
	await replaceDraft(saved);
	assert.equal(preview().querySelectorAll("tbody tr").length, 2);
	assert.equal(requests.length, 1);
});

test("every conductor closure state is readable from the frozen runs, never from the reply", () => {
	const revision = "a".repeat(64),
		sha = "b".repeat(64),
		instance = {
			id: "inverter",
			name: "Inverter",
			product_id: 6506,
			product_revision: revision,
			source_id: "survey",
			ports: [
				{
					id: "p",
					name: "PV +",
					position: { east_m: 0, north_m: 0, height_m: 1 },
				},
				{
					id: "q",
					name: "PV −",
					position: { east_m: 1, north_m: 0, height_m: 1 },
				},
			],
		},
		endpoint = {
			id: "roof",
			name: "String end",
			product_id: null,
			product_revision: null,
			source_id: "survey",
			ports: [
				{
					id: "q",
					name: "String end",
					position: { east_m: 1, north_m: 0, height_m: 1 },
				},
			],
		},
		circuit = {
			id: "pv1",
			name: "Roof circuit",
			kind: "pv_dc",
			start: { instance_id: "inverter", port_id: "p" },
			end: { instance_id: "roof", port_id: "q" },
		},
		route = {
			id: "path",
			name: "Roof route",
			source_id: "survey",
			points: [instance.ports[0].position, endpoint.ports[0].position],
			extra_length_m: 0,
			extra_length_note: "No allowance",
		},
		run = (id, conductor) => ({
			id,
			name: id,
			circuit_id: "pv1",
			route_id: "path",
			construction: "single_conductor",
			...(conductor ? { conductor } : {}),
		}),
		six = { cross_section_mm2: 6, source_note: "Project cable list" },
		review = (cableRuns) => {
			const input = readInstallation({
					...emptyInstallation(),
					geometry_sha256: null,
					instances: [instance, endpoint],
					circuits: [circuit],
					routes: [route],
					cable_runs: cableRuns,
					pv_string_links: [{ string_id: "s1", circuit_id: "pv1" }],
				}),
				recorded = cableRuns.map((run) => ({
					...run,
					// The service reports the declaration explicitly, including
					// its absence; only the saved inputs omit the key.
					conductor: run.conductor ?? null,
					circuit_name: "Roof circuit",
					route_name: "Roof route",
					unit: "m",
					quantity: 16,
					plan_length_m: 10,
					route_length_m: 14,
					extra_length_m: 2,
					reasons: [],
					specification: run.conductor ? "declared" : "open",
				}));
			return {
				input,
				response: {
					schema_version: 1,
					method: "installation_route_takeoff_v1",
					project_id: "project",
					project_revision: 2,
					qualified: false,
					geometry_sha256: sha,
					input_sha256: "c".repeat(64),
					prepared_inputs: { ...input, geometry_sha256: sha },
					cables: recorded,
				},
			};
		};
	const states = [
		// One declared section across every recorded run of the circuit.
		{
			runs: [run("a", six), run("b", six)],
			conductor: "declared",
			recorded: true,
		},
		// A run without its own specification is a gap, not a contradiction.
		{
			runs: [run("a", six), run("b")],
			conductor: "unconfirmed",
			recorded: false,
		},
		// Two different sections are a real conflict, never a silent choice.
		{
			runs: [run("a", six), run("b", { ...six, cross_section_mm2: 10 })],
			conductor: "conflicting",
			recorded: false,
		},
		{ runs: [], conductor: "not_recorded", recorded: false },
	];
	for (const state of states) {
		const { input, response } = review(state.runs),
			closure = {
				conductor: state.conductor,
				quantity: state.runs.length ? "confirmed" : "not_recorded",
				recorded: state.recorded,
				approval: "not_assessed",
			};
		const accepted = readInstallationReview(
			{
				...response,
				pv_string_reconciliation: {
					schema_version: 1,
					scope: "declared_project_identity_only",
					qualified: false,
					pv_string_plan_sha256: "d".repeat(64),
					installation_input_sha256: "c".repeat(64),
					geometry_sha256: sha,
					plan_status: "available",
					rows: [
						{
							string_id: "s1",
							mppt: 1,
							input: 1,
							circuit_id: "pv1",
							status: "linked",
							endpoints: [
								{
									side: "start",
									instance_id: "inverter",
									port_id: "p",
									product_id: 6506,
									product_revision: revision,
								},
								{
									side: "end",
									instance_id: "roof",
									port_id: "q",
									product_id: null,
									product_revision: null,
								},
							],
							cable_runs: response.cables,
							closure,
							reasons: state.runs.length ? [] : ["cable_runs_missing"],
						},
					],
				},
			},
			input,
			"project",
			{
				schema_version: 1,
				inverter_product_id: 6506,
				strings: [{ id: "s1", mppt: 1, input: 1, module_ids: ["m"] }],
			},
			2,
		);
		assert.equal(
			accepted.pv_string_reconciliation.rows[0].closure.conductor,
			state.conductor,
		);
		assert.equal(
			accepted.pv_string_reconciliation.rows[0].closure.approval,
			"not_assessed",
		);
	}
});

test("installation preview reader keeps unknown length and refuses invented reasons or invalid totals", () => {
	const input = emptyInstallation();
	input.instances = [
		{
			id: "device",
			name: "Site",
			product_id: null,
			product_revision: null,
			source_id: "survey",
			ports: [
				{
					id: "a",
					name: "A",
					position: { east_m: 0, north_m: 0, height_m: null },
				},
				{
					id: "b",
					name: "B",
					position: { east_m: 1, north_m: 0, height_m: null },
				},
			],
		},
	];
	input.circuits = [
		{
			id: "ac",
			name: "AC",
			kind: "ac",
			start: { instance_id: "device", port_id: "a" },
			end: { instance_id: "device", port_id: "b" },
		},
	];
	input.routes = [
		{
			id: "path",
			name: "Route",
			source_id: "survey",
			points: input.instances[0].ports.map((p) => p.position),
			extra_length_m: 0,
			extra_length_note: "No allowance",
		},
	];
	input.cable_runs = [
		{
			id: "cable",
			name: "Cable",
			circuit_id: "ac",
			route_id: "path",
			construction: "multicore_cable",
		},
	];
	const sha = "a".repeat(64),
		response = {
			schema_version: 1,
			method: "installation_route_takeoff_v1",
			project_id: "project",
			qualified: false,
			geometry_sha256: sha,
			prepared_inputs: { ...input, geometry_sha256: sha },
			cables: [
				{
					id: "cable",
					name: "Cable",
					circuit_id: "ac",
					route_id: "path",
					route_name: "Route",
					circuit_name: "AC",
					construction: "multicore_cable",
					conductor: null,
					specification: "open",
					unit: "m",
					quantity: null,
					plan_length_m: 1,
					route_length_m: null,
					extra_length_m: 0,
					reasons: ["height_missing"],
				},
			],
		};
	assert.equal(
		readInstallationReview(response, input, "project").cables[0].quantity,
		null,
	);
	for (const patch of [
		{ reasons: ["guessed"] },
		{ reasons: [], quantity: 0 },
		{ reasons: [], quantity: Infinity },
		// The reported status and the frozen declaration must agree.
		{ specification: "declared" },
		{ conductor: { cross_section_mm2: 6, source_note: "Invented" } },
	]) {
		assert.throws(() =>
			readInstallationReview(
				{ ...response, cables: [{ ...response.cables[0], ...patch }] },
				input,
				"project",
			),
		);
	}
});
