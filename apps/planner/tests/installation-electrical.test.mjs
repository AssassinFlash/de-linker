import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom, enter } from "./dom-fixture.mjs";
import {
	CircuitForm,
	CableForm,
} from "../src/components/installation/NetworkForms.tsx";
import { CableReferenceFacts } from "../src/components/installation/CableReferenceFacts.tsx";
import { ElectricalResults } from "../src/components/installation/ElectricalResults.tsx";
import { readElectricalReview } from "../src/domain/installationElectrical.ts";
import { readCableReferences } from "../src/data/cableReferences.ts";
import { emptyInstallation } from "../src/domain/installation.ts";
const sha = "a".repeat(64);
const source = {
	document_id: "fixture",
	document_revision: sha,
	blob_sha256: sha,
	product_id: 9101,
	url: "https://de-linker.com/wp-content/uploads/fixture.pdf",
	page: 1,
	quote: "Synthetic source; no manufacturer claim.",
};
const condition = {
	id: "condition",
	name: "Design current",
	method: "dc_resistive",
	current_a: 20,
	reference_voltage_v: 600,
	direction: "start_to_end",
	conductor_temperature_c: 20,
	frequency_hz: null,
	power_factor: null,
	reactive_direction: null,
	balanced: null,
	sinusoidal: false,
	arrangement: null,
	source_note: "Synthetic condition",
	voltage_limit: { maximum_percent: 1, source_note: "Synthetic limit" },
};
const reference = {
	id: "fixture_cable",
	kind: "cable",
	canonical_product_id: 9101,
	product_revision: sha,
	reference_revision: sha,
	brand: "Synthetic",
	model: "Fixture 6 mm²",
	documents: [{ ...source, product_ids: [9101] }],
	cable_facts: {
		schema_version: 1,
		construction: "single_conductor",
		core_count: 1,
		cross_section_mm2: 6,
		conductor_material: "Fixture copper",
		insulation: "Fixture insulation",
		source,
		parameter_sets: [
			{
				id: "dc_20",
				current_kind: "dc",
				temperature_c: 20,
				frequency_hz: null,
				arrangement: null,
				resistance_ohm_per_km: 3.39,
				reactance_ohm_per_km: null,
				resistance_basis: "maximum",
				source,
			},
		],
	},
};
function fixture() {
	const circuit = {
		id: "circuit",
		name: "Circuit",
		kind: "pv_dc",
		start: { instance_id: "a", port_id: "p" },
		end: { instance_id: "b", port_id: "p" },
		operating_conditions: [structuredClone(condition)],
	};
	const plan = {
		...emptyInstallation(),
		instances: ["a", "b"].map((id) => ({
			id,
			name: id,
			ports: [{ id: "p", name: "Point" }],
		})),
		circuits: [circuit],
		routes: [{ id: "route", name: "Route" }],
		cable_runs: ["dc_positive", "dc_negative"].map((role, i) => ({
			id: "run" + i,
			name: role,
			circuit_id: "circuit",
			route_id: "route",
			construction: "single_conductor",
			core_roles: [role],
			conductor: {
				cross_section_mm2: 6,
				source_note: "Fixture project list",
				cable_reference: { product_id: 9101, product_revision: sha },
			},
		})),
	};
	const cables = plan.cable_runs.map((r) => ({ ...r, quantity: 30 }));
	const row = {
		condition_id: condition.id,
		name: condition.name,
		condition: structuredClone(condition),
		status: "calculated",
		reasons: [],
		segments: plan.cable_runs.map((run) => ({
			run_id: run.id,
			role: run.core_roles[0],
			length_m: 30,
			product_id: 9101,
			product_revision: sha,
			reference_input_id: reference.id,
			parameter_set_id: "dc_20",
			resistance_basis: "maximum",
			resistance_ohm: 0.1017,
			reactance_ohm: null,
			source: structuredClone(source),
		})),
		resistance_basis: "maximum",
		value_basis: "resistance_upper_bound",
		loop_resistance_ohm: 0.2034,
		loop_reactance_ohm: null,
		voltage_drop_v: 4.068,
		voltage_drop_percent: (100 * 4.068) / 600,
		end_minus_start_voltage_v: -4.068,
		conductor_loss_w: 81.36,
		limit: {
			status: "within_declared_limit",
			declared: structuredClone(condition.voltage_limit),
		},
		scope: "conductor_segments_only",
		qualified: false,
	};
	const review = {
		schema_version: 1,
		method: "installation_circuit_steady_conductors_v1",
		qualified: false,
		circuits: [
			{
				circuit_id: circuit.id,
				name: circuit.name,
				status: "reviewed",
				conditions: [row],
			},
		],
	};
	return { plan, cables, review, row };
}
test("electrical reader binds exact conditions, roles, references, quantity, evidence and qualification", () => {
	const f = fixture();
	assert.deepEqual(readElectricalReview(f.review, f.plan, f.cables), f.review);
	for (const mutate of [
		(r) => (r.qualified = true),
		(r) => (r.circuits[0].conditions[0].condition.current_a = 40),
		(r) => (r.circuits[0].conditions[0].qualified = true),
		(r) => (r.circuits[0].conditions[0].segments[0].role = "pe"),
		(r) => (r.circuits[0].conditions[0].segments[0].length_m = 60),
		(r) =>
			(r.circuits[0].conditions[0].segments[0].product_revision = "b".repeat(
				64,
			)),
		(r) =>
			(r.circuits[0].conditions[0].segments[0].source.url =
				"https://external.invalid/claim.pdf"),
		(r) => (r.circuits[0].conditions[0].voltage_drop_v = Infinity),
		(r) => (r.circuits[0].conditions[0].voltage_drop_percent = 99),
		(r) => (r.circuits[0].conditions[0].limit.status = "not_declared"),
	]) {
		const r = structuredClone(f.review);
		mutate(r);
		assert.throws(() => readElectricalReview(r, f.plan, f.cables));
	}
	assert.equal(
		readElectricalReview(undefined, emptyInstallation(), []),
		undefined,
	);
	assert.throws(() => readElectricalReview(undefined, f.plan, f.cables));
});
test("Woo cable reader rejects fake AC conditions, broken document binding and duplicate IDs", () => {
	assert.equal(readCableReferences([reference])[0].canonical_product_id, 9101);
	for (const mutate of [
		(r) => (r.cable_facts.parameter_sets[0].frequency_hz = 50),
		(r) => (r.cable_facts.parameter_sets[0].current_kind = "ac"),
		(r) => (r.cable_facts.source.blob_sha256 = "b".repeat(64)),
		(r) => (r.cable_facts.core_count = 2),
	]) {
		const r = structuredClone(reference);
		mutate(r);
		assert.throws(() => readCableReferences([r]));
	}
	assert.throws(() => readCableReferences([reference, reference]));
});
test("editing preserves all electrical inputs, stale cable revision and historical omission", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const { plan } = fixture();
	let saved;
	const common = {
		locale: "de-DE",
		plan,
		geometry: { sources: [] },
		cancel() {},
		onValidity() {},
		submit(v) {
			saved = v;
			return true;
		},
	};
	const apply = async () =>
		act(async () =>
			document
				.querySelector("form")
				.dispatchEvent(
					new window.Event("submit", { bubbles: true, cancelable: true }),
				),
		);
	await act(async () =>
		root.render(
			React.createElement(CircuitForm, {
				...common,
				circuit: plan.circuits[0],
			}),
		),
	);
	await enter(document.querySelector('[name="name"]'), "Umbenannt");
	await apply();
	assert.deepEqual(saved.operating_conditions, [condition]);
	await act(async () =>
		root.render(
			React.createElement(CableForm, {
				...common,
				cable: plan.cable_runs[0],
				cableReferences: [],
			}),
		),
	);
	await enter(document.querySelector('[name="name"]'), "Leiter");
	await apply();
	assert.deepEqual(saved.core_roles, ["dc_positive"]);
	assert.deepEqual(saved.conductor, plan.cable_runs[0].conductor);
	assert.match(
		document.querySelector('[name="cable_reference"]').textContent,
		/Gespeicherte Referenz/,
	);
	const historical = structuredClone(plan.circuits[0]);
	delete historical.operating_conditions;
	await act(async () =>
		root.render(
			React.createElement(CircuitForm, {
				...common,
				key: "historical",
				circuit: historical,
			}),
		),
	);
	await apply();
	assert.equal(Object.hasOwn(saved, "operating_conditions"), false);
});
test("new conditions have no numerical defaults, decimal comma and failed-input recovery work", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const { plan } = fixture();
	let saved;
	await act(async () =>
		root.render(
			React.createElement(CircuitForm, {
				locale: "de-DE",
				plan,
				geometry: { sources: [] },
				circuit: plan.circuits[0],
				cancel() {},
				onValidity() {},
				submit(v) {
					saved = v;
					return true;
				},
			}),
		),
	);
	await enter(document.querySelector('[name="condition_current"]'), "21,5");
	await act(async () =>
		document
			.querySelector("form")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
	);
	assert.equal(saved.operating_conditions[0].current_a, 21.5);
	saved = undefined;
	const button = (text) =>
		[...document.querySelectorAll("button")].find(
			(b) => b.textContent === text,
		);
	await act(async () => button("Betriebszustand hinzufügen").click());
	const last = [...document.querySelectorAll("fieldset")].at(-1);
	assert.equal(last.querySelector('input[name$="_current"]').value, "");
	await act(async () =>
		document
			.querySelector("form")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
	);
	assert.equal(saved, undefined);
	assert.ok(document.querySelector('[role="alert"]'));
});
test("EN/DE results explain maximum resistance, failures and linked manufacturer source", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const f = fixture();
	for (const [locale, expected] of [
		["en-GB", /Calculated · not qualified/],
		["de-DE", /Berechnet · nicht freigegeben/],
	]) {
		await act(async () =>
			root.render(
				React.createElement(ElectricalResults, { review: f.review, locale }),
			),
		);
		assert.match(document.body.textContent, expected);
		assert.match(
			document.body.textContent,
			locale.startsWith("de")
				? /Obergrenze des vorzeichenbehafteten/
				: /upper bound for the signed/,
		);
		assert.equal(document.querySelector("a").href, source.url + "#page=1");
	}
	for (const status of ["data_insufficient", "method_not_applicable"]) {
		f.row.status = status;
		f.row.reasons = [
			status === "data_insufficient"
				? "cable_conditions_mismatch"
				: "core_roles_not_applicable",
		];
		for (const locale of ["en-GB", "de-DE"]) {
			await act(async () =>
				root.render(
					React.createElement(ElectricalResults, { review: f.review, locale }),
				),
			);
			assert.match(
				document.body.textContent,
				locale.startsWith("de")
					? /Ein vollständiges Stromkreisergebnis liegt nicht vor/
					: /No complete circuit result is available/,
			);
			assert.doesNotMatch(
				document.body.textContent,
				/upper bound for the signed|Obergrenze des vorzeichenbehafteten/,
			);
			assert.equal(document.querySelector("dl"), null);
		}
	}
});

test("leading AC maximum-resistance calculation cannot claim absolute voltage-limit compliance", () => {
	const f = fixture();
	const c = f.plan.circuits[0];
	c.kind = "ac";
	Object.assign(c.operating_conditions[0], {
		method: "ac_two_wire",
		frequency_hz: 50,
		power_factor: 0.8,
		reactive_direction: "leading",
		sinusoidal: true,
		arrangement: "fixture_trefoil",
	});
	f.plan.cable_runs.forEach(
		(r, i) => (r.core_roles = [i ? "neutral" : "line"]),
	);
	f.row.condition = structuredClone(c.operating_conditions[0]);
	f.row.segments.forEach((s, i) => {
		s.role = i ? "neutral" : "line";
		s.reactance_ohm = 0.0024;
	});
	f.row.loop_reactance_ohm = 0.0048;
	f.row.voltage_drop_v = 20 * (0.2034 * 0.8 - 0.0048 * Math.sqrt(1 - 0.8 ** 2));
	f.row.voltage_drop_percent = (100 * f.row.voltage_drop_v) / 600;
	f.row.end_minus_start_voltage_v = -f.row.voltage_drop_v;
	f.row.limit.status = "not_evaluated";
	f.row.limit.reason = "resistance_upper_bound_not_absolute_drop_bound";
	assert.ok(readElectricalReview(f.review, f.plan, f.cables));
	f.row.limit.status = "within_declared_limit";
	assert.throws(() => readElectricalReview(f.review, f.plan, f.cables));
});
test("a calculated reply must contain complete current path and finite results", () => {
	const f = fixture();
	for (const mutate of [
		(r) => (r.segments = []),
		(r) => r.segments.pop(),
		(r) => (r.loop_resistance_ohm = Infinity),
		(r) => (r.conductor_loss_w = null),
	]) {
		const r = structuredClone(f.review);
		mutate(r.circuits[0].conditions[0]);
		assert.throws(() => readElectricalReview(r, f.plan, f.cables));
	}
});
test("explicit current Woo cable selection replaces stale reference without altering declaration", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const { plan } = fixture();
	let saved;
	const current = structuredClone(reference);
	current.product_revision = current.reference_revision = "b".repeat(64);
	await act(async () =>
		root.render(
			React.createElement(CableForm, {
				locale: "en-GB",
				plan,
				geometry: { sources: [] },
				cable: plan.cable_runs[0],
				cableReferences: [current],
				cancel() {},
				onValidity() {},
				submit(v) {
					saved = v;
					return true;
				},
			}),
		),
	);
	const select = document.querySelector('[name="cable_reference"]');
	await act(async () => {
		select.value = "9101:" + current.product_revision;
		select.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await act(async () =>
		document
			.querySelector("form")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
	);
	assert.equal(
		saved.conductor.cable_reference.product_revision,
		current.product_revision,
	);
	assert.equal(saved.conductor.cross_section_mm2, 6);
	assert.deepEqual(saved.core_roles, ["dc_positive"]);
});

test("empty cable brand/model stays valid and renders a nonblank localized reference identity", async (t) => {
	const unnamed = { ...structuredClone(reference), brand: "", model: "" };
	assert.equal(readCableReferences([unnamed])[0].canonical_product_id, 9101);
	for (const field of ["brand", "model"]) {
		assert.throws(() => readCableReferences([{ ...unnamed, [field]: null }]));
	}
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const { plan } = fixture();
	for (const locale of ["en-GB", "de-DE"]) {
		const expected = locale.startsWith("de")
			? "Kabelreferenz fixture_cable · Produkt 9101"
			: "Cable reference fixture_cable · Product 9101";
		await act(async () =>
			root.render(
				React.createElement(CableForm, {
					locale,
					plan,
					geometry: { sources: [] },
					cable: plan.cable_runs[0],
					cableReferences: [unnamed],
					cancel() {},
					onValidity() {},
					submit() {
						return true;
					},
				}),
			),
		);
		const option = document.querySelector(
			'[name="cable_reference"] option[value="9101:' + sha + '"]',
		);
		assert.equal(option.textContent, expected);
		assert.equal(document.querySelector("h4").textContent, expected);
		await act(async () =>
			root.render(
				React.createElement(CableReferenceFacts, {
					reference: { ...unnamed, brand: " ", model: "Actual model" },
					locale,
				}),
			),
		);
		assert.equal(document.querySelector("h4").textContent, "Actual model");
	}
});

test("21 A electrical results use six significant localized digits without changing frozen values", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const f = fixture();
	f.row.condition.current_a = 21;
	f.row.voltage_drop_v = 5.3424000000000005;
	f.row.conductor_loss_w = 112.19040000000001;
	const frozen = structuredClone(f.review);
	for (const [locale, drop, loss] of [
		["en-GB", "5.3424 V", "112.19 W"],
		["de-DE", "5,3424 V", "112,19 W"],
	]) {
		await act(async () =>
			root.render(
				React.createElement(ElectricalResults, { review: f.review, locale }),
			),
		);
		assert.ok(document.body.textContent.includes(drop));
		assert.ok(document.body.textContent.includes(loss));
		assert.doesNotMatch(
			document.body.textContent,
			/5[.,]3424000000000005|112[.,]19040000000001/,
		);
	}
	assert.deepEqual(f.review, frozen);
});

test("manufacturer and result revision hashes wrap without losing exact text", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	for (const view of [
		React.createElement(CableReferenceFacts, { reference, locale: "de-DE" }),
		React.createElement(ElectricalResults, {
			review: fixture().review,
			locale: "de-DE",
		}),
	]) {
		await act(async () => root.render(view));
		const codes = [...document.querySelectorAll("code")];
		assert.ok(codes.length >= 2);
		for (const code of codes) {
			assert.equal(code.textContent, sha);
			assert.equal(code.querySelectorAll("wbr").length, 7);
		}
	}
});

test("cable core counts use singular and plural labels in EN and DE", async (t) => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	for (const [locale, singular, plural] of [
		["en-GB", "1 core", "5 cores"],
		["de-DE", "1 Ader", "5 Adern"],
	]) {
		await act(async () =>
			root.render(
				React.createElement(CableReferenceFacts, { reference, locale }),
			),
		);
		assert.ok(document.querySelector("h4 + p").textContent.includes(singular));
		assert.doesNotMatch(
			document.querySelector("h4 + p").textContent,
			/1 cores|1 Adern/,
		);
		const multicore = {
			...reference,
			cable_facts: {
				...reference.cable_facts,
				construction: "multicore_cable",
				core_count: 5,
			},
		};
		await act(async () =>
			root.render(
				React.createElement(CableReferenceFacts, {
					reference: multicore,
					locale,
				}),
			),
		);
		assert.ok(document.querySelector("h4 + p").textContent.includes(plural));
	}
});
