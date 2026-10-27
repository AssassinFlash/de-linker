import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom, enter } from "./dom-fixture.mjs";
import { RouteForm } from "../src/components/installation/NetworkForms.tsx";
import { emptyGeometry } from "../src/domain/geometryCommands.ts";
import {
	emptyInstallation,
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
					circuit_name: "AC",
					route_name: "Route",
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
