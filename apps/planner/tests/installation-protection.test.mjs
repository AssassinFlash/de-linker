import assert from "node:assert/strict";
import test from "node:test";
import React, { act, useState } from "react";
import { setupDom, enter } from "./dom-fixture.mjs";
import { InstallationProtection } from "../src/components/installation/InstallationProtection.tsx";
const assessment = () => ({
	id: "assessment",
	circuit_id: "ac",
	protection_material_id: "breaker",
	operating_condition_id: "normal",
	scenario: "Normal supply fault",
	fault_range: null,
	breaking: null,
	disconnection: null,
	thermal: [],
	confirmed_context_sha256: null,
});
function fixture() {
	const end = (instance_id) => ({ instance_id, port_id: "port" }),
		condition = {
			id: "normal",
			name: "Normal supply",
			reference_voltage_v: 400,
			current_a: 40,
		};
	return {
		schema_version: 1,
		geometry_sha256: null,
		instances: ["a", "b", "other"].map((id) => ({
			id,
			name: id,
			product_id: null,
			product_revision: null,
			source_id: "survey",
			ports: [],
		})),
		circuits: [
			{
				id: "ac",
				name: "Supply",
				kind: "ac",
				start: end("a"),
				end: end("b"),
				operating_conditions: [
					condition,
					{ ...condition, id: "island", name: "Island supply" },
				],
			},
			{
				id: "pe",
				name: "Independent PE",
				kind: "protective_earth",
				start: end("b"),
				end: end("a"),
			},
			{
				id: "wrong",
				name: "Other PE",
				kind: "protective_earth",
				start: end("a"),
				end: end("other"),
			},
		],
		routes: [],
		cable_runs: [
			{
				id: "live",
				name: "Supply cable",
				circuit_id: "ac",
				route_id: "r",
				construction: "multicore_cable",
				core_roles: ["l1", "unused"],
				conductor: { cross_section_mm2: 16, source_note: "Recorded cable" },
			},
			{
				id: "earth",
				name: "Separate PE cable",
				circuit_id: "pe",
				route_id: "p",
				construction: "single_conductor",
				core_roles: ["pe", "line"],
				conductor: { cross_section_mm2: 10, source_note: "Recorded PE" },
			},
			{
				id: "unrelated",
				name: "Unrelated cable",
				circuit_id: "wrong",
				route_id: "x",
				construction: "single_conductor",
				core_roles: ["pe"],
			},
		],
		materials: [
			{
				id: "breaker",
				name: "Recorded breaker",
				kind: "protection",
				circuit_id: "ac",
				quantity: 1,
				unit: "piece",
				specification: "Recorded AC device",
				source_note: "Existing source",
			},
			{
				id: "global",
				name: "Unbound protection",
				kind: "protection",
				circuit_id: null,
				quantity: 1,
				unit: "piece",
				specification: "Other",
				source_note: "Other",
			},
			{
				id: "two",
				name: "Two protection items",
				kind: "protection",
				circuit_id: "ac",
				quantity: 2,
				unit: "piece",
				specification: "Other",
				source_note: "Other",
			},
			{
				id: "mount",
				name: "Mounting rail",
				kind: "mounting",
				circuit_id: null,
				quantity: 1,
				unit: "piece",
				specification: "Other",
				source_note: "Other",
			},
		],
	};
}
const hash = "a".repeat(64),
	unassessed = () => ({
		status: "not_assessed",
		measured: null,
		maximum: null,
		reason: null,
	});
const review = (
	confirmation_status = "confirmation_required",
	context = hash,
) => ({
	assessments: [
		{
			id: "assessment",
			circuit_id: "ac",
			protection_material_id: "breaker",
			scenario: "Normal supply fault",
			confirmation_context_sha256: context,
			confirmation_status,
			breaking: unassessed(),
			disconnection: unassessed(),
			thermal: [],
		},
	],
});
function button(text, scope = document) {
	const b = [...scope.querySelectorAll("button")].find(
		(b) => b.textContent.trim() === text,
	);
	assert.ok(b, "Missing button " + text);
	return b;
}
const click = async (b) => act(async () => b.click());
async function choose(name, value) {
	await act(async () => {
		const e = document.querySelector(`[name="${name}"]`);
		assert.ok(e, name);
		e.value = value;
		e.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
}
async function fill(values) {
	for (const [name, value] of Object.entries(values))
		await enter(document.querySelector(`[name="${name}"]`), String(value));
}
const submit = async () =>
	act(async () =>
		document
			.querySelector("form")
			.dispatchEvent(
				new window.Event("submit", { bubbles: true, cancelable: true }),
			),
	);
const section = (name) =>
	[...document.querySelectorAll("h5")].find((e) => e.textContent === name)
		.parentElement;
async function mount(plan = fixture(), locale = "en") {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	let current,
		valid,
		accept = true,
		setReview,
		setDisabled;
	function validity(v) {
		valid = v;
	}
	function Harness() {
		const [value, setValue] = useState(plan),
			[result, updateReview] = useState(undefined),
			[disabled, updateDisabled] = useState(false);
		current = value;
		setReview = updateReview;
		setDisabled = updateDisabled;
		return React.createElement(InstallationProtection, {
			plan: value,
			review: result,
			locale,
			disabled,
			onValidity: validity,
			change: (next) => {
				if (!accept) return false;
				setValue(next);
				return true;
			},
		});
	}
	await act(async () => root.render(React.createElement(Harness)));
	return {
		get plan() {
			return current;
		},
		get valid() {
			return valid;
		},
		reject() {
			accept = false;
		},
		async review(value) {
			await act(async () => setReview(value));
		},
		async disable(value) {
			await act(async () => setDisabled(value));
		},
		async dispose() {
			await dom.dispose(root);
		},
	};
}

test("staged conditions preserve existing circuit data and reject an inverted fault range without losing input", async () => {
	const h = await mount();
	try {
		const runs = structuredClone(h.plan.cable_runs);
		await click(button("Add protection condition"));
		assert.equal(h.valid, false);
		await choose("circuit", "ac");
		assert.equal(document.querySelector('[name="material"]').options.length, 2);
		await choose("material", "breaker");
		await choose("condition", "normal");
		await fill({ scenario: "Normal supply fault" });
		await submit();
		const row = h.plan.protection_assessments[0];
		assert.equal(row.protection_material_id, "breaker");
		assert.equal(row.operating_condition_id, "normal");
		assert.equal(row.fault_range, null);
		assert.equal(row.breaking, null);
		assert.deepEqual(row.thermal, []);
		assert.deepEqual(h.plan.cable_runs, runs);
		assert.equal(h.valid, true);
		await click(button("Add evidence", section("Fault-current range")));
		await fill({
			minimum_fault_a: 2000,
			maximum_fault_a: 1000,
			source_note: "Project calculation",
		});
		await submit();
		assert.equal(h.plan.protection_assessments[0].fault_range, null);
		assert.equal(
			document.querySelector('[name="minimum_fault_a"]').value,
			"2000",
		);
		assert.match(
			document.body.textContent,
			/minimum fault current must not exceed/,
		);
		assert.equal(h.valid, false);
		await fill({ maximum_fault_a: 3000 });
		await submit();
		assert.equal(
			h.plan.protection_assessments[0].fault_range.maximum_fault_a,
			3000,
		);
		assert.equal(h.plan.protection_assessments[0].breaking, null);
		await click(button("Add protection condition"));
		await choose("circuit", "ac");
		await choose("material", "breaker");
		await choose("condition", "island");
		await fill({ scenario: "Island supply fault" });
		await submit();
		assert.deepEqual(
			h.plan.protection_assessments.map((x) => x.operating_condition_id),
			["normal", "island"],
		);
	} finally {
		await h.dispose();
	}
});

test("German thermal evidence selects recorded cores including only the same-device independent PE", async () => {
	const p = fixture();
	p.protection_assessments = [assessment()];
	p.cable_runs.push({
		...p.cable_runs[0],
		id: "missing_section",
		name: "No declared section",
		conductor: null,
	});
	const h = await mount(p, "de-DE");
	try {
		await click(button("Adernachweis hinzufügen"));
		let options = [...document.querySelector('[name="core"]').options];
		assert.equal(options.length, 3);
		assert.match(
			options.map((x) => x.textContent).join(" "),
			/Separate PE cable · PE · 10 mm²/,
		);
		assert.ok(!options.some((x) => /Unrelated|UNUSED/.test(x.textContent)));
		await choose("core", JSON.stringify(["earth", "pe"]));
		await fill({
			maximum_let_through_a2s: "0",
			coverage_min_fault_a: 100,
			coverage_max_fault_a: 3000,
			maximum_clear_s: "0,2",
			k_a_sqrt_s_per_mm2: 115,
			k_source_note: "Leiterdaten",
			let_through_source_note: "Herstellerkennlinie",
		});
		await submit();
		assert.deepEqual(h.plan.protection_assessments[0].thermal, []);
		assert.equal(
			document.querySelector('[name="maximum_let_through_a2s"]').value,
			"0",
		);
		assert.equal(
			document.querySelector('[name="maximum_let_through_a2s"]').validity.valid,
			false,
		);
		await fill({ maximum_let_through_a2s: "2000,5" });
		await submit();
		const row = h.plan.protection_assessments[0].thermal[0];
		assert.equal(row.run_id, "earth");
		assert.equal(row.core_role, "pe");
		assert.equal(row.maximum_let_through_a2s, 2000.5);
		assert.equal(row.maximum_clear_s, 0.2);
		assert.equal(h.plan.cable_runs[1].conductor.cross_section_mm2, 10);
		await click(button("Adernachweis hinzufügen"));
		assert.equal(document.querySelector('[name="core"]').options.length, 2);
		await click(button("Cancel properties"));
		await click(button("Adernachweis bearbeiten"));
		assert.equal(
			document.querySelector('[name="maximum_let_through_a2s"]').value,
			"2000,5",
		);
		await click(button("Cancel properties"));
		await click(button("Adernachweis entfernen"));
		assert.deepEqual(h.plan.protection_assessments[0].thermal, []);
	} finally {
		await h.dispose();
	}
});

test("server context confirmation is unavailable without a hash and any evidence edit clears it", async () => {
	const p = fixture();
	p.protection_assessments = [assessment()];
	const h = await mount(p);
	try {
		const label = "Confirm this condition and these sources";
		assert.equal(button(label).disabled, true);
		await h.review(review("context_unavailable", null));
		assert.equal(button(label).disabled, true);
		await h.review(review());
		await click(button(label));
		assert.equal(
			h.plan.protection_assessments[0].confirmed_context_sha256,
			hash,
		);
		await click(button("Add evidence", section("Breaking capacity")));
		await fill({
			capacity_a: 6000,
			rated_voltage_v: 400,
			source_note: "AC manufacturer data",
		});
		await choose("current_kind", "ac");
		await submit();
		assert.equal(
			h.plan.protection_assessments[0].confirmed_context_sha256,
			null,
		);
		await h.review(review("context_changed", "b".repeat(64)));
		assert.match(document.body.textContent, /context changed/);
		await click(button(label));
		assert.equal(
			h.plan.protection_assessments[0].confirmed_context_sha256,
			"b".repeat(64),
		);
		const checked = review("confirmed", "b".repeat(64));
		checked.assessments[0].breaking = {
			status: "within_declared_values",
			measured: 3000,
			maximum: 6000,
			reason: null,
		};
		checked.assessments[0].disconnection = {
			status: "outside_declared_values",
			measured: 0.5,
			maximum: 0.4,
			reason: null,
		};
		await h.review(checked);
		assert.match(document.body.textContent, /3000 A ≤ 6000 A/);
		assert.match(document.body.textContent, /0.5 s > 0.4 s/);
		assert.equal(button(label).disabled, true);
		await click(button("Remove evidence", section("Breaking capacity")));
		assert.equal(h.plan.protection_assessments[0].breaking, null);
		assert.equal(
			h.plan.protection_assessments[0].confirmed_context_sha256,
			null,
		);
	} finally {
		await h.dispose();
	}
});

test("a rejected apply keeps staged input and disabled state blocks mutations", async () => {
	const p = fixture();
	p.protection_assessments = [assessment()];
	const h = await mount(p);
	try {
		await click(button("Edit condition"));
		await fill({ scenario: "Unfinished corrected scenario" });
		h.reject();
		await submit();
		assert.equal(
			document.querySelector('[name="scenario"]').value,
			"Unfinished corrected scenario",
		);
		assert.equal(
			h.plan.protection_assessments[0].scenario,
			"Normal supply fault",
		);
		assert.equal(h.valid, false);
		assert.equal(button("Add protection condition").disabled, true);
		await h.disable(true);
		assert.equal(document.querySelector("fieldset").disabled, true);
		assert.equal(button("Apply properties").disabled, true);
		await click(button("Cancel properties"));
		assert.equal(h.valid, true);
		assert.equal(button("Remove condition").disabled, true);
	} finally {
		await h.dispose();
	}
});
