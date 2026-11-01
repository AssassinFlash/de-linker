import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupDom, enter, until } from "./dom-fixture.mjs";
import { CableForm } from "../src/components/installation/NetworkForms.tsx";
import { InstallationEditor } from "../src/components/installation/InstallationEditor.tsx";
import { ReferenceCurrentResults } from "../src/components/installation/ReferenceCurrentResults.tsx";
import { readCableReferences } from "../src/data/cableReferences.ts";
import { readInstallation } from "../src/domain/installation.ts";
import { readElectricalReview } from "../src/domain/installationElectrical.ts";
import {
	readReferenceCurrentSegments,
	referenceCurrentContext,
} from "../src/domain/installationReferenceCurrent.ts";
import { emptyGeometry } from "../src/domain/geometryCommands.ts";
import { manualSource } from "../src/domain/geometryEditing.ts";

const sha = "a".repeat(64);
const layings = [
	"single_in_air",
	"single_on_surface",
	"two_touching_on_surface",
];
const ids = [
	"single-in-air-60c-120c",
	"single-on-surface-60c-120c",
	"two-touching-on-surface-60c-120c",
];
function reference(productId, section, values) {
	const source = {
		document_id: "fixture_" + productId,
		document_revision: sha,
		blob_sha256: sha,
		product_id: productId,
		url: "https://de-linker.com/wp-content/uploads/fixture.pdf",
		page: 2,
		quote: "Synthetic fixture for the source-bound table.",
	};
	return {
		id: "fixture_cable_" + productId,
		kind: "cable",
		canonical_product_id: productId,
		product_revision: sha,
		reference_revision: sha,
		brand: "Fixture",
		model: section + " mm²",
		documents: [{ ...source, product_ids: [productId] }],
		cable_facts: {
			schema_version: 1,
			construction: "single_conductor",
			core_count: 1,
			cross_section_mm2: section,
			conductor_material: "Synthetic copper",
			insulation: "Synthetic insulation",
			source,
			parameter_sets: [],
			reference_current_ratings: ids.map((id, i) => ({
				id,
				laying: layings[i],
				ambient_temperature_c: 60,
				rated_conductor_temperature_c: 120,
				current_a: values[i],
				source,
			})),
		},
	};
}
const refs = [
	reference(9101, 4, [55, 52, 44]),
	reference(9102, 6, [70, 67, 57]),
];
const declaration = (index = 0, extra = {}) => ({
	rating_id: ids[index],
	laying: layings[index],
	ambient_temperature_c: 60,
	touching_run_id: null,
	current_path: "single_unbranched",
	conditions_confirmed: true,
	source_note: "Fixture project conditions",
	...extra,
});
const condition = {
	id: "condition",
	name: "Operating current",
	method: "dc_resistive",
	current_a: 55,
	reference_voltage_v: 600,
	direction: "start_to_end",
	conductor_temperature_c: 20,
	frequency_hz: null,
	power_factor: null,
	reactive_direction: null,
	balanced: null,
	sinusoidal: false,
	arrangement: null,
	source_note: "Fixture project input",
	voltage_limit: null,
};
function plan(withCurrent = true) {
	const position = (east_m) => ({ east_m, north_m: 0, height_m: 0 });
	const value = {
		schema_version: 1,
		geometry_sha256: null,
		instances: [
			{
				id: "device",
				name: "Device",
				product_id: null,
				product_revision: null,
				source_id: "survey",
				ports: [
					{ id: "start", name: "Start", position: position(0) },
					{ id: "end", name: "End", position: position(10) },
				],
			},
		],
		circuits: [
			{
				id: "circuit",
				name: "PV circuit",
				kind: "pv_dc",
				start: { instance_id: "device", port_id: "start" },
				end: { instance_id: "device", port_id: "end" },
				operating_conditions: [structuredClone(condition)],
			},
		],
		routes: [
			{
				id: "route",
				name: "Route",
				source_id: "survey",
				points: [position(0), position(10)],
				extra_length_m: 0,
				extra_length_note: "No allowance",
			},
		],
		cable_runs: refs.map((r, i) => ({
			id: "run" + i,
			name: i ? "Negative" : "Positive",
			circuit_id: "circuit",
			route_id: "route",
			construction: "single_conductor",
			core_roles: [i ? "dc_negative" : "dc_positive"],
			conductor: {
				cross_section_mm2: r.cable_facts.cross_section_mm2,
				source_note: "Fixture cable choice",
				cable_reference: {
					product_id: r.canonical_product_id,
					product_revision: sha,
				},
			},
			...(withCurrent ? { reference_current_installation: declaration() } : {}),
		})),
	};
	if (withCurrent)
		for (const run of value.cable_runs) {
			const selected = run.reference_current_installation;
			selected.confirmation_context = referenceCurrentContext(
				value,
				run,
				selected,
			);
		}
	return value;
}
function result() {
	const input = plan(),
		cables = input.cable_runs.map((run) => ({ ...run, quantity: 10 }));
	const drop = 4.664;
	const voltage = {
		condition_id: "condition",
		name: condition.name,
		condition: structuredClone(condition),
		status: "calculated",
		reasons: [],
		segments: input.cable_runs.map((run, i) => ({
			run_id: run.id,
			role: run.core_roles[0],
			length_m: 10,
			product_id: refs[i].canonical_product_id,
			product_revision: sha,
			reference_input_id: refs[i].id,
			parameter_set_id: "rdc20",
			resistance_basis: "maximum",
			resistance_ohm: i ? 0.0339 : 0.0509,
			reactance_ohm: null,
			source: refs[i].cable_facts.source,
		})),
		resistance_basis: "maximum",
		value_basis: "resistance_upper_bound",
		loop_resistance_ohm: 0.0848,
		loop_reactance_ohm: null,
		voltage_drop_v: drop,
		voltage_drop_percent: (100 * drop) / 600,
		end_minus_start_voltage_v: -drop,
		conductor_loss_w: 256.52,
		limit: { status: "not_declared", declared: null },
		scope: "conductor_segments_only",
		qualified: false,
	};
	const current = input.cable_runs.map((run, i) => ({
		circuit_id: "circuit",
		condition_id: "condition",
		run_id: run.id,
		role: run.core_roles[0],
		status: i ? "below_reference" : "equal_reference",
		reasons: [],
		project_current_a: 55,
		reference_current_a:
			refs[i].cable_facts.reference_current_ratings[0].current_a,
		installation: structuredClone(run.reference_current_installation),
		rating: structuredClone(refs[i].cable_facts.reference_current_ratings[0]),
		product_id: refs[i].canonical_product_id,
		product_revision: sha,
		reference_input_id: refs[i].id,
		scope: "single_conductor_reference_only",
		qualified: false,
	}));
	return {
		input,
		cables,
		review: {
			schema_version: 1,
			method: "installation_circuit_steady_conductors_v1",
			qualified: false,
			circuits: [
				{
					circuit_id: "circuit",
					name: "PV circuit",
					status: "reviewed",
					conditions: [voltage],
				},
			],
			reference_current_segments: current,
		},
	};
}
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

test("historical inputs stay unchanged and new Woo rows require exact sourced evidence", () => {
	const old = plan(false),
		bytes = JSON.stringify(old);
	assert.equal(JSON.stringify(readInstallation(old)), bytes);
	assert.equal(
		Object.hasOwn(
			readInstallation(old).cable_runs[0],
			"reference_current_installation",
		),
		false,
	);
	const withNull = structuredClone(old);
	withNull.cable_runs[0].reference_current_installation = null;
	assert.equal(JSON.stringify(readInstallation(withNull)), bytes);
	const savedWithOldConfirmation = plan();
	delete savedWithOldConfirmation.cable_runs[0].reference_current_installation
		.confirmation_context;
	assert.deepEqual(
		readInstallation(savedWithOldConfirmation),
		savedWithOldConfirmation,
	);
	const explicitNull = structuredClone(savedWithOldConfirmation);
	explicitNull.cable_runs[0].reference_current_installation.confirmation_context =
		null;
	assert.deepEqual(readInstallation(explicitNull), savedWithOldConfirmation);
	assert.equal(readCableReferences(refs).length, 2);
	const historical = structuredClone(refs[0]);
	delete historical.cable_facts.reference_current_ratings;
	assert.equal(
		Object.hasOwn(
			readCableReferences([historical])[0].cable_facts,
			"reference_current_ratings",
		),
		false,
	);
	for (const change of [
		(r) =>
			r.cable_facts.reference_current_ratings.push(
				structuredClone(r.cable_facts.reference_current_ratings[0]),
			),
		(r) =>
			(r.cable_facts.reference_current_ratings[0].source.document_revision =
				"b".repeat(64)),
		(r) => (r.cable_facts.reference_current_ratings[0].current_a = 0),
		(r) => (r.cable_facts.reference_current_ratings[0].laying = "invented"),
	]) {
		const bad = structuredClone(refs[0]);
		change(bad);
		assert.throws(() => readCableReferences([bad]));
	}
});

test("confirmation snapshot follows physical values and ignores private or cosmetic text", () => {
	const value = plan(),
		run = value.cable_runs[0],
		selected = run.reference_current_installation;
	assert.deepEqual(selected.confirmation_context, {
		declaration: {
			rating_id: ids[0],
			laying: "single_in_air",
			ambient_temperature_c: 60,
			touching_run_id: null,
			current_path: "single_unbranched",
		},
		run: {
			id: "run0",
			construction: "single_conductor",
			core_roles: ["dc_positive"],
			cross_section_mm2: 4,
			cable_reference: { product_id: 9101, product_revision: sha },
			route: {
				id: "route",
				points: [
					{ east_m: 0, north_m: 0, height_m: 0 },
					{ east_m: 10, north_m: 0, height_m: 0 },
				],
				extra_length_m: 0,
			},
			circuit: {
				id: "circuit",
				kind: "pv_dc",
				start: {
					instance_id: "device",
					port_id: "start",
					product_id: null,
					product_revision: null,
					position: { east_m: 0, north_m: 0, height_m: 0 },
				},
				end: {
					instance_id: "device",
					port_id: "end",
					product_id: null,
					product_revision: null,
					position: { east_m: 10, north_m: 0, height_m: 0 },
				},
			},
		},
		touching_run: null,
	});
	const changed = structuredClone(value);
	changed.routes[0].points[1].height_m = null;
	assert.notDeepEqual(
		referenceCurrentContext(
			changed,
			changed.cable_runs[0],
			changed.cable_runs[0].reference_current_installation,
		),
		selected.confirmation_context,
	);
	const cosmetic = structuredClone(value);
	cosmetic.routes[0].name = "Renamed";
	cosmetic.cable_runs[0].name = "Renamed";
	cosmetic.cable_runs[0].reference_current_installation.source_note =
		"New private note";
	assert.deepEqual(
		referenceCurrentContext(
			cosmetic,
			cosmetic.cable_runs[0],
			cosmetic.cable_runs[0].reference_current_installation,
		),
		selected.confirmation_context,
	);
	const pair = plan();
	pair.cable_runs[0].reference_current_installation = declaration(2, {
		touching_run_id: "run1",
	});
	const originalPair = referenceCurrentContext(
		pair,
		pair.cable_runs[0],
		pair.cable_runs[0].reference_current_installation,
	);
	const movedPeer = structuredClone(pair);
	movedPeer.routes.push({ ...movedPeer.routes[0], id: "other_route" });
	movedPeer.cable_runs[1].route_id = "other_route";
	assert.notDeepEqual(
		referenceCurrentContext(
			movedPeer,
			movedPeer.cable_runs[0],
			movedPeer.cable_runs[0].reference_current_installation,
		),
		originalPair,
	);
	const changedPeer = structuredClone(pair);
	changedPeer.cable_runs[1].conductor.cross_section_mm2 = 10;
	assert.notDeepEqual(
		referenceCurrentContext(
			changedPeer,
			changedPeer.cable_runs[0],
			changedPeer.cable_runs[0].reference_current_installation,
		),
		originalPair,
	);
});

test("each result is bound to its saved run and stays independent from voltage drop", () => {
	const f = result(),
		read = readElectricalReview(f.review, f.input, f.cables);
	assert.deepEqual(
		read.reference_current_segments.map((x) => x.status),
		["equal_reference", "below_reference"],
	);
	assert.equal(read.circuits[0].conditions[0].voltage_drop_v, 4.664);
	for (const change of [
		(r) => r.reference_current_segments.reverse(),
		(r) => (r.reference_current_segments[0].qualified = true),
		(r) => (r.reference_current_segments[0].reference_current_a = 999),
		(r) => (r.reference_current_segments[0].status = "below_reference"),
		(r) =>
			(r.reference_current_segments[0].rating.source.url =
				"https://invalid.example/data.pdf"),
		(r) =>
			(r.reference_current_segments[0].installation.current_path = "unknown"),
		(r) =>
			(r.reference_current_segments[0].rating.rated_conductor_temperature_c = 20),
	]) {
		const bad = structuredClone(f.review);
		change(bad);
		assert.throws(() => readElectricalReview(bad, f.input, f.cables));
	}
	const pending = structuredClone(f);
	pending.input.cable_runs[0].reference_current_installation.conditions_confirmed = false;
	Object.assign(pending.review.reference_current_segments[0], {
		status: "not_evaluated",
		reasons: ["installation_conditions_not_confirmed"],
		project_current_a: null,
		reference_current_a: null,
		installation: structuredClone(
			pending.input.cable_runs[0].reference_current_installation,
		),
	});
	const accepted = readElectricalReview(
		pending.review,
		pending.input,
		pending.cables,
	);
	assert.equal(accepted.reference_current_segments[0].status, "not_evaluated");
	assert.equal(accepted.circuits[0].conditions[0].voltage_drop_v, 4.664);
	const above = structuredClone(f.review);
	above.reference_current_segments[0].rating.current_a = 50;
	above.reference_current_segments[0].reference_current_a = 50;
	above.reference_current_segments[0].status = "above_reference";
	assert.equal(
		readElectricalReview(above, f.input, f.cables).reference_current_segments[0]
			.status,
		"above_reference",
	);
});

test("a touching-pair comparison rejects one-sided or different-cable declarations", () => {
	const f = result();
	f.input.cable_runs[1].conductor = structuredClone(
		f.input.cable_runs[0].conductor,
	);
	for (const [index, run] of f.input.cable_runs.entries()) {
		run.reference_current_installation = declaration(2, {
			touching_run_id: "run" + (1 - index),
		});
		run.reference_current_installation.confirmation_context =
			referenceCurrentContext(f.input, run, run.reference_current_installation);
		Object.assign(f.review.reference_current_segments[index], {
			installation: structuredClone(run.reference_current_installation),
			rating: structuredClone(refs[0].cable_facts.reference_current_ratings[2]),
			product_id: 9101,
			reference_input_id: refs[0].id,
			reference_current_a: 44,
			status: "above_reference",
		});
	}
	assert.equal(
		readReferenceCurrentSegments(f.review.reference_current_segments, f.input)
			.length,
		2,
	);
	for (const peerContext of ["missing", "stale"]) {
		const unconfirmedPeer = structuredClone(f.input);
		const peer = unconfirmedPeer.cable_runs[1].reference_current_installation;
		if (peerContext === "missing") peer.confirmation_context = null;
		else peer.confirmation_context.declaration.rating_id = "old-rating";
		const invalidPeerRows = structuredClone(
			f.review.reference_current_segments,
		);
		invalidPeerRows[1].installation = structuredClone(peer);
		Object.assign(invalidPeerRows[1], {
			status: "not_evaluated",
			reasons: ["confirmation_context_changed"],
			project_current_a: null,
			reference_current_a: null,
		});
		assert.throws(() =>
			readReferenceCurrentSegments(invalidPeerRows, unconfirmedPeer),
		);
		Object.assign(invalidPeerRows[0], {
			status: "not_evaluated",
			reasons: ["touching_pair_mismatch"],
			project_current_a: null,
			reference_current_a: null,
		});
		assert.equal(
			readReferenceCurrentSegments(invalidPeerRows, unconfirmedPeer).length,
			2,
		);
	}
	const oneSided = structuredClone(f.input);
	oneSided.cable_runs[1].reference_current_installation.touching_run_id = null;
	assert.throws(() =>
		readReferenceCurrentSegments(f.review.reference_current_segments, oneSided),
	);
	const differentCable = structuredClone(f.input);
	differentCable.cable_runs[1].conductor.cable_reference.product_id = 9102;
	assert.throws(() =>
		readReferenceCurrentSegments(
			f.review.reference_current_segments,
			differentCable,
		),
	);
});

test("a third circuit claiming contact blocks both isolated and paired comparisons", () => {
	for (const paired of [false, true]) {
		const f = result();
		if (paired) {
			f.input.cable_runs[1].conductor = structuredClone(
				f.input.cable_runs[0].conductor,
			);
			for (const [index, run] of f.input.cable_runs.entries())
				run.reference_current_installation = declaration(2, {
					touching_run_id: "run" + (1 - index),
				});
			for (const [index, run] of f.input.cable_runs.entries()) {
				run.reference_current_installation.confirmation_context =
					referenceCurrentContext(
						f.input,
						run,
						run.reference_current_installation,
					);
				Object.assign(f.review.reference_current_segments[index], {
					installation: structuredClone(run.reference_current_installation),
					rating: structuredClone(
						refs[0].cable_facts.reference_current_ratings[2],
					),
					product_id: 9101,
					reference_input_id: refs[0].id,
					reference_current_a: 44,
					status: "above_reference",
				});
			}
		}
		const evaluated = structuredClone(f.review.reference_current_segments);
		f.input.circuits.push({
			...structuredClone(f.input.circuits[0]),
			id: "other_circuit",
		});
		const foreign = structuredClone(f.input.cable_runs[0]);
		foreign.id = "third_run";
		foreign.circuit_id = "other_circuit";
		foreign.reference_current_installation = declaration(2, {
			touching_run_id: "run0",
		});
		f.input.cable_runs.push(foreign);
		const rows = f.review.reference_current_segments;
		for (const index of paired ? [0, 1] : [0])
			Object.assign(rows[index], {
				status: "not_evaluated",
				reasons: ["touching_pair_mismatch"],
				project_current_a: null,
				reference_current_a: null,
			});
		rows.push({
			...structuredClone(rows[0]),
			circuit_id: "other_circuit",
			run_id: "third_run",
			installation: structuredClone(foreign.reference_current_installation),
			rating: structuredClone(refs[0].cable_facts.reference_current_ratings[2]),
		});
		assert.equal(readReferenceCurrentSegments(rows, f.input).length, 3);
		for (const index of paired ? [0, 1] : [0]) {
			const forged = structuredClone(rows);
			forged[index] = evaluated[index];
			assert.throws(() => readReferenceCurrentSegments(forged, f.input));
		}
	}
});

test("explicit EN/DE table choice preserves entered values during invalid-input recovery", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	for (const [locale, index, expected] of [
		["en-GB", 0, "55 A"],
		["de-DE", 1, "70 A"],
	]) {
		const input = plan(false);
		let saved;
		await act(async () =>
			root.render(
				React.createElement(CableForm, {
					key: locale,
					locale,
					geometry: { sources: [] },
					plan: input,
					cable: input.cable_runs[index],
					cableReferences: refs,
					cancel() {},
					onValidity() {},
					submit(value) {
						saved = value;
						return true;
					},
				}),
			),
		);
		const field = (name) =>
			document.querySelector("form").elements.namedItem(name);
		assert.equal(field("reference_current_rating").value, "");
		assert.match(
			field("reference_current_rating").textContent,
			new RegExp(expected),
		);
		await choose(field("reference_current_rating"), "current:" + ids[0]);
		assert.equal(field("reference_current_path").value, "");
		assert.equal(field("reference_current_confirmed").checked, false);
		await choose(field("reference_current_path"), "single_unbranched");
		await enter(field("reference_current_note"), "Recorded conditions");
		await act(async () => field("reference_current_confirmed").click());
		await enter(
			field("cross_section"),
			locale.startsWith("de") ? "1,abc" : "1.abc",
		);
		await apply();
		assert.equal(saved, undefined);
		assert.ok(document.querySelector('[role="alert"]'));
		assert.equal(field("reference_current_note").value, "Recorded conditions");
		assert.equal(field("reference_current_rating").value, "current:" + ids[0]);
		assert.equal(field("reference_current_confirmed").checked, false);
		await enter(
			field("cross_section"),
			String(refs[index].cable_facts.cross_section_mm2),
		);
		assert.equal(field("reference_current_confirmed").checked, false);
		await act(async () => field("reference_current_confirmed").click());
		await apply();
		const { confirmation_context, ...actual } =
			saved.reference_current_installation;
		assert.deepEqual(
			actual,
			declaration(0, { source_note: "Recorded conditions" }),
		);
		const working = {
			...input,
			cable_runs: input.cable_runs.map((run) =>
				run.id === saved.id ? saved : run,
			),
		};
		assert.deepEqual(
			confirmation_context,
			referenceCurrentContext(
				working,
				saved,
				saved.reference_current_installation,
			),
		);
		assert.equal(
			input.circuits[0].operating_conditions[0].conductor_temperature_c,
			20,
		);
		assert.match(
			document.body.textContent,
			locale.startsWith("de")
				? /kein vor Ort gemessener Wert/
				: /not a measured site temperature/,
		);
	}
});

test("touching conductors require separate explicit reciprocal declarations", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const input = plan(false);
	input.cable_runs[1].conductor = structuredClone(
		input.cable_runs[0].conductor,
	);
	let saved;
	const render = async (index) =>
		act(async () =>
			root.render(
				React.createElement(CableForm, {
					key: index,
					locale: "en-GB",
					geometry: { sources: [] },
					plan: input,
					cable: input.cable_runs[index],
					cableReferences: refs,
					cancel() {},
					onValidity() {},
					submit(value) {
						saved = value;
						return true;
					},
				}),
			),
		);
	for (const index of [0, 1]) {
		await render(index);
		const field = (name) =>
			document.querySelector("form").elements.namedItem(name);
		assert.equal(field("reference_current_rating").value, "");
		await choose(field("reference_current_rating"), "current:" + ids[2]);
		assert.equal(field("reference_current_touching").value, "");
		await choose(field("reference_current_touching"), "run" + (1 - index));
		await choose(field("reference_current_path"), "single_unbranched");
		await enter(field("reference_current_note"), "Confirmed pair");
		await act(async () => field("reference_current_confirmed").click());
		await apply();
		const { confirmation_context, ...actual } =
			saved.reference_current_installation;
		assert.deepEqual(
			actual,
			declaration(2, {
				touching_run_id: "run" + (1 - index),
				source_note: "Confirmed pair",
			}),
		);
		const working = {
			...input,
			cable_runs: input.cable_runs.map((run) =>
				run.id === saved.id ? saved : run,
			),
		};
		assert.deepEqual(
			confirmation_context,
			referenceCurrentContext(
				working,
				saved,
				saved.reference_current_installation,
			),
		);
		if (!index)
			assert.equal(
				Object.hasOwn(input.cable_runs[1], "reference_current_installation"),
				false,
			);
		input.cable_runs[index] = saved;
	}
});

test("material changes require new confirmation without losing the saved selection or note", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	for (const [name, value] of [
		["route", "other_route"],
		["circuit", "other_circuit"],
		["construction", "multicore_cable"],
		["reference_current_path", "unknown"],
		["reference_current_rating", "current:" + ids[1]],
		["reference_current_touching", "run2"],
	]) {
		const input = plan();
		input.routes.push({
			...input.routes[0],
			id: "other_route",
			name: "Other route",
		});
		input.circuits.push({
			...input.circuits[0],
			id: "other_circuit",
			name: "Other circuit",
		});
		input.cable_runs.push({
			...input.cable_runs[1],
			id: "run2",
			name: "Other conductor",
		});
		if (name === "reference_current_touching")
			input.cable_runs[0].reference_current_installation = declaration(2, {
				touching_run_id: "run1",
			});
		if (name === "reference_current_touching") {
			const run = input.cable_runs[0];
			run.reference_current_installation.confirmation_context =
				referenceCurrentContext(input, run, run.reference_current_installation);
		}
		let saved;
		await act(async () =>
			root.render(
				React.createElement(CableForm, {
					key: name,
					locale: "en-GB",
					geometry: { sources: [] },
					plan: input,
					cable: input.cable_runs[0],
					cableReferences: refs,
					cancel() {},
					onValidity() {},
					submit(v) {
						saved = v;
						return true;
					},
				}),
			),
		);
		const field = (key) =>
			document.querySelector("form").elements.namedItem(key);
		assert.equal(field("reference_current_confirmed").checked, true);
		await choose(field(name), value);
		assert.equal(field("reference_current_confirmed").checked, false, name);
		assert.match(
			document.body.textContent,
			/Review the current project conditions and confirm them again/,
		);
		assert.equal(
			field("reference_current_note").value,
			"Fixture project conditions",
		);
		await apply();
		assert.equal(
			saved.reference_current_installation.conditions_confirmed,
			false,
		);
		await act(async () => field("reference_current_confirmed").click());
		await apply();
		assert.equal(
			saved.reference_current_installation.conditions_confirmed,
			true,
		);
	}
});

test("missing or changed physical snapshots stay unchanged until the user explicitly reconfirms", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	for (const mode of ["missing", "changed_route"]) {
		const input = plan(),
			cable = input.cable_runs[0];
		if (mode === "missing")
			delete cable.reference_current_installation.confirmation_context;
		else input.routes[0].points[1].east_m = 11;
		const original = structuredClone(cable.reference_current_installation);
		let saved;
		await act(async () =>
			root.render(
				React.createElement(CableForm, {
					key: mode,
					locale: "en-GB",
					geometry: { sources: [] },
					plan: input,
					cable,
					cableReferences: refs,
					cancel() {},
					onValidity() {},
					submit(v) {
						saved = v;
						return true;
					},
				}),
			),
		);
		const field = (name) =>
			document.querySelector("form").elements.namedItem(name);
		assert.equal(field("reference_current_confirmed").checked, false);
		assert.match(
			document.body.textContent,
			/Review the current project conditions and confirm them again/,
		);
		await enter(field("name"), "Renamed");
		await apply();
		assert.deepEqual(saved.reference_current_installation, original);
		await act(async () => field("reference_current_confirmed").click());
		await apply();
		const working = {
			...input,
			cable_runs: input.cable_runs.map((run) =>
				run.id === saved.id ? saved : run,
			),
		};
		assert.deepEqual(
			saved.reference_current_installation.confirmation_context,
			referenceCurrentContext(
				working,
				saved,
				saved.reference_current_installation,
			),
		);
	}
});

test("changing a reconfirmed cross-section back to its original value invalidates confirmation", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element),
		input = plan();
	t.after(() => dom.dispose(root));
	let saved;
	await act(async () =>
		root.render(
			React.createElement(CableForm, {
				locale: "en-GB",
				geometry: { sources: [] },
				plan: input,
				cable: input.cable_runs[0],
				cableReferences: refs,
				cancel() {},
				onValidity() {},
				submit(v) {
					saved = v;
					return true;
				},
			}),
		),
	);
	const field = (name) =>
		document.querySelector("form").elements.namedItem(name);
	await enter(field("cross_section"), "6");
	assert.equal(field("reference_current_confirmed").checked, false);
	await act(async () => field("reference_current_confirmed").click());
	assert.equal(field("reference_current_confirmed").checked, true);
	await enter(field("cross_section"), "4");
	assert.equal(field("reference_current_confirmed").checked, false);
	await apply();
	assert.equal(
		saved.reference_current_installation.conditions_confirmed,
		false,
	);
});

test("name, source note and equivalent decimal formatting preserve a valid confirmation", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const input = plan(),
		cable = input.cable_runs[0];
	let saved;
	await act(async () =>
		root.render(
			React.createElement(CableForm, {
				locale: "de-DE",
				geometry: { sources: [] },
				plan: input,
				cable,
				cableReferences: refs,
				cancel() {},
				onValidity() {},
				submit(v) {
					saved = v;
					return true;
				},
			}),
		),
	);
	const field = (name) =>
		document.querySelector("form").elements.namedItem(name);
	assert.equal(field("reference_current_confirmed").checked, true);
	await enter(field("name"), "Neuer Name");
	await enter(field("cross_section"), "4,0");
	await enter(field("reference_current_note"), "Andere Notiz");
	assert.equal(field("reference_current_confirmed").checked, true);
	await apply();
	assert.equal(saved.reference_current_installation.conditions_confirmed, true);
	assert.deepEqual(
		saved.reference_current_installation.confirmation_context,
		cable.reference_current_installation.confirmation_context,
	);
});

test("stale selections survive unrelated edits and need explicit replacement or clearing", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const input = plan(),
		cable = input.cable_runs[0];
	let saved;
	const render = async (key, available) =>
		act(async () =>
			root.render(
				React.createElement(CableForm, {
					key,
					locale: "de-DE",
					geometry: { sources: [] },
					plan: input,
					cable,
					cableReferences: available,
					cancel() {},
					onValidity() {},
					submit(value) {
						saved = value;
						return true;
					},
				}),
			),
		);
	await render("stale", []);
	let field = (name) => document.querySelector("form").elements.namedItem(name);
	await enter(field("name"), "Umbenannt");
	await apply();
	assert.deepEqual(
		saved.reference_current_installation,
		cable.reference_current_installation,
	);
	await choose(field("reference_current_rating"), "");
	await apply();
	assert.equal(Object.hasOwn(saved, "reference_current_installation"), false);
	const fresh = structuredClone(refs[0]);
	fresh.product_revision = fresh.reference_revision = "b".repeat(64);
	saved = undefined;
	await render("replacement", [fresh]);
	field = (name) => document.querySelector("form").elements.namedItem(name);
	await choose(field("cable_reference"), "9101:" + fresh.product_revision);
	await apply();
	assert.equal(saved, undefined);
	assert.ok(document.querySelector('[role="alert"]'));
	await choose(field("reference_current_rating"), "current:" + ids[0]);
	assert.equal(field("reference_current_confirmed").checked, false);
	await act(async () => field("reference_current_confirmed").click());
	await apply();
	assert.equal(
		saved.conductor.cable_reference.product_revision,
		fresh.product_revision,
	);
	assert.equal(saved.reference_current_installation.rating_id, ids[0]);
});

test("reference-current results render both statuses and cited table conditions in EN and DE", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element);
	t.after(() => dom.dispose(root));
	const f = result();
	for (const [locale, expected] of [
		["en-GB", /Equal to the listed current/],
		["de-DE", /Entspricht dem Tabellenwert/],
	]) {
		await act(async () =>
			root.render(
				React.createElement(ReferenceCurrentResults, {
					review: f.review,
					cables: f.cables,
					locale,
				}),
			),
		);
		assert.match(document.body.textContent, expected);
		assert.match(document.body.textContent, /55 A/);
		assert.match(document.body.textContent, /70 A/);
		assert.match(document.body.textContent, /60 °C/);
		assert.match(document.body.textContent, /120 °C/);
		assert.equal(document.querySelectorAll('a[href$="#page=2"]').length, 2);
	}
});

test("installation editor submits both saved declarations and displays independent current and voltage results", async (t) => {
	const dom = setupDom(),
		{ createRoot } = await import("react-dom/client"),
		root = createRoot(dom.element),
		cache = new QueryClient();
	t.after(async () => {
		cache.clear();
		await dom.dispose(root);
	});
	const f = result(),
		geo = emptyGeometry();
	geo.sources = [
		manualSource("survey", "Synthetic survey", "Fixture permission"),
	];
	let current = f.input;
	const calls = [],
		savedInputs = { installation: current };
	const client = {
		isCurrentScope: () => true,
		async query(path, body) {
			if (path === "products/current")
				return {
					schema_version: 1,
					provider: "woocommerce",
					compatibility_origin: "woocommerce",
					figure_projection_version: 2,
					products: [],
					cable_references: refs,
				};
			assert.equal(path, "installation/review");
			calls.push(structuredClone(body));
			return {
				schema_version: 1,
				method: "installation_route_takeoff_v1",
				project_id: "project",
				project_revision: 2,
				qualified: false,
				geometry_sha256: sha,
				prepared_inputs: { ...body.installation, geometry_sha256: sha },
				cables: body.installation.cable_runs.map((run) => ({
					id: run.id,
					name: run.name,
					circuit_id: run.circuit_id,
					circuit_name: "PV circuit",
					route_id: run.route_id,
					route_name: "Route",
					construction: run.construction,
					conductor: run.conductor,
					specification: "declared",
					quantity: 10,
					unit: "m",
					plan_length_m: 10,
					route_length_m: 10,
					extra_length_m: 0,
					extra_length_note: "No allowance",
					reasons: [],
				})),
				electrical: f.review,
			};
		},
	};
	function Harness() {
		const [value, setValue] = React.useState(current);
		return React.createElement(InstallationEditor, {
			inputs: { installation: value },
			savedInputs,
			savedRevision: 2,
			geometry: geo,
			client,
			session: { query_scope: sha },
			projectId: "project",
			locale: "en-GB",
			sceneModuleUrl: null,
			onValidity() {},
			editGeometry() {
				return false;
			},
			change(next) {
				current = next;
				setValue(next);
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
	const button = [...document.querySelectorAll("button")].find(
		(item) => item.textContent === "Review routes and circuit conditions",
	);
	assert.ok(button && !button.disabled);
	await act(async () => button.click());
	await until(() =>
		document.body.textContent.includes("Equal to the listed current"),
	);
	assert.deepEqual(
		calls[0].installation.cable_runs.map(
			(run) => run.reference_current_installation,
		),
		f.input.cable_runs.map((run) => run.reference_current_installation),
	);
	assert.match(document.body.textContent, /Below the listed current/);
	assert.match(document.body.textContent, /4\.664 V/);
});
