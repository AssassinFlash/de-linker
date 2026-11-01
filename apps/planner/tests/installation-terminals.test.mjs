import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, enter, until } from "./dom-fixture.mjs";
import {
	CircuitForm,
	InstanceForm,
} from "../src/components/installation/NetworkForms.tsx";
import { TerminalResults } from "../src/components/installation/TerminalResults.tsx";
import { InstallationEditor } from "../src/components/installation/InstallationEditor.tsx";
import { emptyGeometry } from "../src/domain/geometryCommands.ts";
import { manualSource } from "../src/domain/geometryEditing.ts";
import {
	emptyInstallation,
	readInstallation,
} from "../src/domain/installation.ts";
import {
	terminalCandidates,
	readTerminalAssessment,
} from "../src/domain/installationTerminals.ts";

const revision = "a".repeat(64),
	otherRevision = "b".repeat(64),
	documentRevision = "c".repeat(64);
const source = {
	document_id: "fixture-document",
	document_revision: documentRevision,
	blob_sha256: "d".repeat(64),
	product_id: 1958,
	url: "https://de-linker.com/wp-content/uploads/fixture.pdf",
	page: 23,
	quote: "Synthetic terminal evidence for this browser fixture.",
};
const fact = (id, terminal, use) => ({
	id,
	basis: "manufacturer_terminal_map",
	label: { en: id, de: id + " DE" },
	specification: {
		terminal_domain: "communication",
		terminals: [terminal],
		terminal_use: use,
	},
	source,
});
const external = fact("external", "COM1", "external_communication"),
	internal = fact("internal", "COM2", "internal_communication");
const product = {
	id: 1958,
	canonical_product_id: 1958,
	product_revision: revision,
	brand: "Fixture",
	model: "Battery",
	device_class: "battery",
	figures: {},
	installation_facts: { status: "documented", items: [external, internal] },
};
const binding = (fact, instanceId) => ({
	instance_id: instanceId,
	product_id: 1958,
	product_revision: revision,
	fact_id: fact.id,
	terminal: fact.specification.terminals[0],
	document_id: source.document_id,
	document_revision: documentRevision,
});
const point = (id, terminal_binding) => ({
	id,
	name: id,
	position: { east_m: 0, north_m: 0, height_m: null },
	...(terminal_binding === undefined ? {} : { terminal_binding }),
});
const instance = {
	id: "device",
	name: "Fixture battery",
	product_id: 1958,
	product_revision: revision,
	source_id: "survey",
	ports: [point("p", binding(external, "device")), point("q")],
};
const circuit = {
	id: "network",
	name: "Network",
	kind: "control",
	start: { instance_id: "device", port_id: "p" },
	end: { instance_id: "device", port_id: "q" },
};
const geometry = { sources: [{ id: "survey", note: "Fixture survey" }] };
async function choose(element, value) {
	await act(async () => {
		element.value = value;
		element.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
}
async function apply() {
	await act(async () =>
		document
			.querySelector("form")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
	);
}

test("terminal choices come from documented manufacturer maps with explicit source", () => {
	const extra = [
		{
			...external,
			id: "text-only",
			basis: "manufacturer_included_per_sales_unit",
		},
		{
			...external,
			id: "empty",
			specification: { terminal_domain: "communication", terminals: [] },
		},
		{
			...external,
			id: "missing-source",
			source: { ...source, document_revision: "" },
		},
	];
	const p = {
		...product,
		installation_facts: {
			status: "documented",
			items: [...product.installation_facts.items, ...extra],
		},
	};
	assert.deepEqual(
		terminalCandidates(p, "device").map((c) => c.binding.terminal),
		["COM1", "COM2"],
	);
	assert.deepEqual(
		terminalCandidates(
			{ ...p, installation_facts: { status: "unresolved", items: [external] } },
			"device",
		),
		[],
	);
	assert.deepEqual(
		terminalCandidates(
			{
				...p,
				installation_facts: {
					status: "documented",
					items: [external, { ...external, source: null }],
				},
			},
			"device",
		),
		[],
	);
});

test("device edits preserve stale and omitted bindings; selections can be corrected or cleared", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const stale = {
			...binding(external, "device"),
			document_revision: otherRevision,
		},
		old = { ...instance, ports: [point("p", stale), point("q")] },
		plan = { ...emptyInstallation(), instances: [old], circuits: [circuit] };
	let saved;
	const render = async (device, products = [product], key = "device") =>
		act(async () =>
			root.render(
				React.createElement(InstanceForm, {
					key,
					instance: device,
					products,
					plan,
					geometry,
					locale: "en-GB",
					cancel() {},
					onValidity() {},
					submit(value) {
						saved = value;
						return true;
					},
				}),
			),
		);
	await render(old);
	await apply();
	assert.equal(JSON.stringify(saved), JSON.stringify(old));
	await enter(document.querySelector('[name="name"]'), "Renamed");
	await apply();
	assert.deepEqual(saved.ports[0].terminal_binding, stale);
	assert.equal(Object.hasOwn(saved.ports[1], "terminal_binding"), false);
	assert.equal(saved.ports[1].name, "q");
	assert.match(document.body.textContent, /Saved selection.*COM1/);
	assert.match(document.body.textContent, /Saved source/);
	await choose(document.querySelector('[name="pterminal"]'), "candidate:1");
	await choose(document.querySelector('[name="qterminal"]'), "candidate:0");
	await apply();
	assert.deepEqual(
		saved.ports[0].terminal_binding,
		binding(internal, "device"),
	);
	assert.deepEqual(
		saved.ports[1].terminal_binding,
		binding(external, "device"),
	);
	await render(old, [], "unavailable");
	assert.match(document.body.textContent, /No documented terminal choices/);
	await apply();
	assert.deepEqual(saved.ports[0].terminal_binding, stale);
	await choose(document.querySelector('[name="pterminal"]'), "none");
	await apply();
	assert.equal(Object.hasOwn(saved.ports[0], "terminal_binding"), false);
	assert.equal(Object.hasOwn(saved.ports[1], "terminal_binding"), false);
});

test("circuit communication use is optional, editable and limited to control", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const plan = {
		...emptyInstallation(),
		instances: [instance],
		circuits: [circuit],
	};
	let saved;
	const render = async (row, key) =>
		act(async () =>
			root.render(
				React.createElement(CircuitForm, {
					key,
					circuit: row,
					plan,
					geometry,
					locale: "de-DE",
					cancel() {},
					onValidity() {},
					submit(value) {
						saved = value;
						return true;
					},
				}),
			),
		);
	await render(circuit, "historical");
	await apply();
	assert.equal(Object.hasOwn(saved, "communication_use"), false);
	await choose(
		document.querySelector('[name="communication_use"]'),
		"external_communication",
	);
	await apply();
	assert.equal(saved.communication_use, "external_communication");
	assert.match(document.body.textContent, /Externe Kommunikation/);
	await render(
		{ ...circuit, communication_use: "external_communication" },
		"selected",
	);
	await choose(document.querySelector('[name="kind"]'), "ac");
	await apply();
	assert.equal(saved.kind, "ac");
	assert.equal(Object.hasOwn(saved, "communication_use"), false);
	await render({ ...circuit, communication_use: null }, "null");
	await apply();
	assert.equal(saved.communication_use, null);
});

test("each endpoint reads its own documented evidence and independent domain/use result", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const device = {
			...instance,
			ports: [
				point("p", binding(external, "device")),
				point("q", binding(internal, "device")),
			],
		},
		declared = { ...circuit, communication_use: "external_communication" },
		plan = readInstallation({
			...emptyInstallation(),
			instances: [device],
			circuits: [declared],
		}),
		result = {
			schema_version: 1,
			scope: "manufacturer_one_end_mapping",
			qualified: false,
			circuits: [
				{
					circuit_id: circuit.id,
					name: circuit.name,
					kind: circuit.kind,
					communication_use: declared.communication_use,
					endpoints: [
						{
							side: "start",
							instance_id: "device",
							port_id: "p",
							status: "documented",
							binding: binding(external, "device"),
							fact: external,
							domain_status: "matches",
							use_status: "matches",
						},
						{
							side: "end",
							instance_id: "device",
							port_id: "q",
							status: "documented",
							binding: binding(internal, "device"),
							fact: internal,
							domain_status: "matches",
							use_status: "mismatch",
						},
					],
				},
			],
		};
	assert.deepEqual(readTerminalAssessment(result, plan), result);
	for (const mutate of [
		(r) => (r.qualified = true),
		(r) => (r.circuits[0].endpoints[1].use_status = "matches"),
		(r) => (r.circuits[0].endpoints[1].binding = binding(external, "device")),
		(r) =>
			(r.circuits[0].endpoints[0].fact.source.document_revision =
				otherRevision),
	]) {
		const modified = structuredClone(result);
		mutate(modified);
		assert.throws(() => readTerminalAssessment(modified, plan));
	}
	const staleBinding = {
		...binding(external, "device"),
		document_revision: otherRevision,
	};
	const stalePlan = readInstallation({
		...plan,
		instances: [
			{ ...device, ports: [point("p", staleBinding), device.ports[1]] },
		],
	});
	const staleReply = structuredClone(result);
	Object.assign(staleReply.circuits[0].endpoints[0], {
		binding: staleBinding,
		status: "document_changed",
		fact: null,
		domain_status: "not_assessed",
		use_status: "not_assessed",
	});
	assert.deepEqual(readTerminalAssessment(staleReply, stalePlan), staleReply);
	await act(async () =>
		root.render(
			React.createElement(TerminalResults, {
				review: staleReply,
				plan: stalePlan,
				locale: "en-GB",
			}),
		),
	);
	assert.match(document.body.textContent, /Manufacturer document changed/);
	assert.match(document.body.textContent, /Saved source reference/);
	for (const [locale, expected] of [
		["en-GB", /does not establish compatibility/i],
		["de-DE", /weder die Kompatibilität/i],
	]) {
		await act(async () =>
			root.render(
				React.createElement(TerminalResults, { review: result, plan, locale }),
			),
		);
		assert.match(document.body.textContent, expected);
		assert.match(document.body.textContent, /COM1/);
		assert.match(document.body.textContent, /COM2/);
		assert.equal(document.querySelectorAll("article").length, 2);
		assert.equal(document.querySelectorAll('a[href*="fixture.pdf"]').length, 2);
	}
	assert.equal(
		readTerminalAssessment(undefined, emptyInstallation()),
		undefined,
	);
});

test("editor selects current Woo terminals, submits their bindings and reads both ends", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	const cache = new QueryClient();
	t.after(async () => {
		cache.clear();
		await dom.dispose(root);
	});
	const geo = emptyGeometry();
	geo.sources = [
		manualSource("survey", "Fixture survey", "Fixture permission"),
	];
	const stale = {
		...binding(external, "device"),
		document_revision: otherRevision,
	};
	let current = {
		...emptyInstallation(),
		instances: [{ ...instance, ports: [point("p", stale), point("q")] }],
		circuits: [circuit],
	};
	const baseline = { installation: current },
		calls = [];
	const client = {
		isCurrentScope: () => true,
		async query(path, body) {
			if (path === "products/current")
				return {
					schema_version: 1,
					provider: "woocommerce",
					compatibility_origin: "woocommerce",
					figure_projection_version: 2,
					products: [product],
				};
			assert.equal(path, "installation/review");
			calls.push(structuredClone(body));
			const plan = body.installation,
				saved = plan.circuits[0];
			return {
				schema_version: 1,
				method: "installation_route_takeoff_v1",
				project_id: "project",
				project_revision: 2,
				qualified: false,
				geometry_sha256: revision,
				prepared_inputs: { ...plan, geometry_sha256: revision },
				cables: [],
				terminal_assessment: {
					schema_version: 1,
					scope: "manufacturer_one_end_mapping",
					qualified: false,
					circuits: [
						{
							circuit_id: saved.id,
							name: saved.name,
							kind: saved.kind,
							communication_use: saved.communication_use,
							endpoints: [external, internal].map((f, index) => ({
								side: index === 0 ? "start" : "end",
								instance_id: "device",
								port_id: index === 0 ? "p" : "q",
								status: "documented",
								binding: plan.instances[0].ports[index].terminal_binding,
								fact: f,
								domain_status: "matches",
								use_status: index === 0 ? "matches" : "mismatch",
							})),
						},
					],
				},
			};
		},
	};
	function Harness() {
		const [plan, setPlan] = React.useState(current);
		return React.createElement(InstallationEditor, {
			inputs: { installation: plan },
			savedInputs: baseline,
			savedRevision: 2,
			geometry: geo,
			client,
			session: { query_scope: revision },
			projectId: "project",
			locale: "en-GB",
			sceneModuleUrl: null,
			onValidity() {},
			editGeometry() {
				return false;
			},
			change(value) {
				current = value;
				setPlan(value);
				return true;
			},
		});
	}
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: cache },
				React.createElement(Harness),
			),
		),
	);
	await until(
		() => !document.body.textContent.includes("Loading current product"),
	);
	const section = (heading) =>
		[...document.querySelectorAll("section")].find(
			(s) => s.querySelector("h3")?.textContent === heading,
		);
	const click = async (button) => act(async () => button.click());
	await click(
		[
			...section("Physical devices and site connections").querySelectorAll(
				"button",
			),
		].find((b) => b.textContent === "Edit"),
	);
	assert.match(document.body.textContent, /Saved selection.*COM1/);
	await choose(document.querySelector('[name="pterminal"]'), "candidate:0");
	await choose(document.querySelector('[name="qterminal"]'), "candidate:1");
	await apply();
	await click(
		[...section("Circuits").querySelectorAll("button")].find(
			(b) => b.textContent === "Edit",
		),
	);
	await choose(
		document.querySelector('[name="communication_use"]'),
		"external_communication",
	);
	await apply();
	const reviewButton = [...document.querySelectorAll("button")].find(
		(b) => b.textContent === "Review installation",
	);
	assert.equal(reviewButton.disabled, false);
	await click(reviewButton);
	await until(() =>
		document.body.textContent.includes("Manufacturer terminal mapping"),
	);
	assert.equal(calls.length, 1);
	assert.equal(
		calls[0].installation.instances[0].ports[0].terminal_binding.terminal,
		"COM1",
	);
	assert.equal(
		calls[0].installation.instances[0].ports[1].terminal_binding.terminal,
		"COM2",
	);
	assert.equal(
		calls[0].installation.circuits[0].communication_use,
		"external_communication",
	);
	const output = section("Manufacturer terminal mapping"),
		ends = output.querySelectorAll("article");
	assert.equal(ends.length, 2);
	assert.match(ends[0].textContent, /COM1.*Matches declared use/);
	assert.match(ends[1].textContent, /COM2.*Does not match declared use/);
	assert.match(output.textContent, /does not establish compatibility/i);
});
