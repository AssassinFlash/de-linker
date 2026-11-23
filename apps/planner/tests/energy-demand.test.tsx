import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import {
	EnergyDemand,
	changeEnergyGoal,
	energyGoal,
} from "../src/components/configurator/EnergyDemand.tsx";
import { setupDom, enter } from "./dom-fixture.mjs";
import knownPv from "./fixtures/known-pv-reference.json" with { type: "json" };
import { ApiError } from "../src/data/protocol.ts";

const projectId = "1".repeat(32);
test("energy demand edits one project and compares without preparation rituals", async () => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	let inputs = { untouched: "keep" };
	let comparisons = 0;
	let edits = 0;
	const client = { isCurrentScope: () => true };
	const render = () =>
		root.render(
			<EnergyDemand
				projectId={projectId}
				inputs={inputs}
				locale="en"
				disabled={false}
				client={client}
				session={{
					query_scope: "scope",
					runtime: { limits: { max_csv_bytes: 10000, max_page_size: 20 } },
				}}
				recheck={() => {}}
				edit={(operation) => {
					inputs = operation(inputs);
					edits++;
					render();
					return true;
				}}
				compare={() => {
					comparisons++;
				}}
			/>,
		);
	const select = async (label, value) => {
		const input = [...dom.element.querySelectorAll("label")]
			.find((x) => x.textContent.includes(label))
			.querySelector("select");
		await act(async () => {
			input.value = value;
			input.dispatchEvent(new Event("change", { bubbles: true }));
		});
	};
	const field = (label) =>
		[...dom.element.querySelectorAll("label")]
			.find((x) => x.textContent.includes(label))
			.querySelector("input");
	const compare = () =>
		[...dom.element.querySelectorAll("button")].find(
			(x) => x.textContent === "Compare systems",
		);
	try {
		await act(async () => render());
		assert.equal(energyGoal(inputs), "");
		await select("Purpose", "self");
		assert.equal(compare().disabled, true);
		assert.doesNotMatch(
			dom.element.textContent,
			/You can compare equipment now/,
		);
		assert.match(
			dom.element.textContent,
			/Choose a single-phase or three-phase grid connection/,
		);
		await select("Purpose", "backup");
		assert.equal(edits, 2);
		assert.deepEqual(inputs.backup_demand, {
			schema_version: 1,
			load_kw: null,
			duration_hours: null,
		});
		assert.equal(inputs.equipment_setup.required_usable_kwh, null);
		assert.equal(compare().disabled, true);
		await enter(field("Backup load"), "5");
		await enter(field("Required duration"), "6");
		assert.equal(compare().disabled, true);
		inputs = {
			...inputs,
			existing_system: {
				schema_version: 1,
				name: "West barn",
				inverter_power_kw: 7.5,
				keep_inverter: true,
			},
		};
		await act(async () => render());
		assert.equal(compare().disabled, false);
		const { existing_system: _, ...withoutRetention } = inputs;
		inputs = withoutRetention;
		await act(async () => render());
		await select("Grid connection", "3");
		assert.match(dom.element.textContent, /30 kWh/);
		assert.equal(inputs.backup_demand.load_kw, 5);
		assert.equal(inputs.equipment_setup.required_usable_kwh, null);
		assert.equal(inputs.untouched, "keep");
		await act(async () => compare().click());
		assert.equal(comparisons, 1);
		await select("Purpose", "peak");
		assert.equal(energyGoal(inputs), "peak");
		assert.equal(inputs.backup_demand, undefined);
		await enter(field("Target grid import limit"), "12");
		assert.equal(inputs.energy_scenario.schedule[0].import_cap_kw, 12);
		await act(async () => compare().click());
		assert.equal(
			comparisons,
			2,
			"peak comparison remains available without invented sizing",
		);
		await select("Purpose", "self");
		assert.equal(energyGoal(inputs), "self");
		assert.equal(inputs.energy_scenario.schedule[0].import_cap_kw, null);
		assert.equal(inputs.energy_scenario.schedule[0].import_policy, null);
		assert.doesNotMatch(dom.element.textContent, /Prepare|Adopt|Save project/);
	} finally {
		await dom.dispose(root);
	}
});

test("a real typical profile is imported and selected for the same project", async () => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	let inputs = changeEnergyGoal(knownPv.project.inputs, "self");
	inputs.energy_scenario.schedule[0].start_utc = "2026-01-01T00:00:00Z";
	inputs.energy_scenario.schedule[0].end_utc = "2027-01-01T00:00:00Z";
	const calls = [];
	const asset = {
		id: "2".repeat(32),
		project_id: projectId,
		content_sha256: "a".repeat(64),
		metadata_sha256: "b".repeat(64),
		media_type: "application/json",
		purpose: "csv_profile_v1",
		metadata: {},
	};
	const client = {
		isCurrentScope: () => true,
		query: async (path, body) => {
			calls.push({ path, body });
			if (path === "profiles/standard" || path === "assets/read") return asset;
			return {
				schema_version: 1,
				evaluation_scope: "profile_interpretation",
				project_id: projectId,
				asset_id: asset.id,
				content_sha256: asset.content_sha256,
				metadata_sha256: asset.metadata_sha256,
				measurement: "gross_load",
				source: {},
				transformations: [],
				summary: {
					start_utc: "2019-12-31T23:00:00Z",
					end_utc: "2020-12-31T23:00:00Z",
					interval_count: 35040,
					covered_seconds: 31536000,
					span_seconds: 31536000,
					gap_seconds: 0,
					gap_count: 0,
					energy_kwh: 6000,
					min_interval_mean_kw: 0.1,
					max_interval_mean_kw: 3,
					native_max_interval_seconds: 900,
					effective_max_interval_seconds: 900,
					reconstructed_means: false,
				},
				rows: [
					{
						interval_index: 0,
						start_utc: "2019-12-31T23:00:00Z",
						end_utc: "2019-12-31T23:15:00Z",
						interval_mean_kw: 1,
					},
					{
						interval_index: 1,
						start_utc: "2019-12-31T23:15:00Z",
						end_utc: "2019-12-31T23:30:00Z",
						interval_mean_kw: 3,
					},
				],
				first_gaps: [],
				gaps_truncated: false,
				next_offset: null,
			};
		},
	};
	const render = () =>
		root.render(
			<EnergyDemand
				projectId={projectId}
				inputs={inputs}
				locale="en"
				disabled={false}
				client={client}
				session={{
					query_scope: "scope",
					runtime: { limits: { max_csv_bytes: 10000, max_page_size: 20 } },
				}}
				recheck={() => {}}
				edit={(operation) => {
					inputs = operation(inputs);
					render();
					return true;
				}}
				compare={() => {}}
			/>,
		);
	const field = (label) =>
		[...dom.element.querySelectorAll("label")]
			.find((x) => x.textContent.includes(label))
			.querySelector("input");
	try {
		await act(async () => render());
		await enter(field("Annual electricity use"), "6000");
		const select = dom.element.querySelector('select[name="load-pattern"]');
		await act(async () => {
			select.value = "H0";
			select.dispatchEvent(new Event("change", { bubbles: true }));
		});
		await enter(field("Time zone"), "Europe/Berlin");
		await act(async () =>
			[...dom.element.querySelectorAll("button")]
				.find((x) => x.textContent === "Use this load profile")
				.click(),
		);
		assert.equal(calls[0].path, "profiles/standard");
		assert.equal(calls[0].body.project_id, projectId);
		assert.equal(calls[0].body.annual_kwh, 6000);
		assert.equal(inputs.profile_selections.selected.gross_load, asset.id);
		assert.match(dom.element.textContent, /6,000 kWh/);
		const curve = dom.element.querySelector(
			'[role="img"][aria-label="Electricity demand"]',
		);
		assert.ok(curve, "the selected load source has a visible demand chart");
		assert.match(curve.textContent, /3 kW/);
		const interval = dom.element.querySelector(
			'time[datetime="2019-12-31T23:15:00Z"]',
		);
		assert.ok(interval);
		assert.match(interval.textContent, /23:15/);
		assert.doesNotMatch(interval.textContent, /T23/);
		assert.match(interval.closest("tr").textContent, /3$/);
		assert.match(
			dom.element.querySelector("figure").textContent,
			/23:00.+23:30.*UTC/,
		);
		assert.equal(calls[0].body.year, 2020);
		assert.equal(
			inputs.energy_scenario.schedule[0].start_utc,
			"2019-12-31T23:00:00Z",
		);
		assert.equal(
			inputs.energy_scenario.schedule[0].end_utc,
			"2020-12-31T23:00:00Z",
		);
		await act(async () => {
			for (const [label, value] of [
				["Purpose", "peak"],
				["Grid connection", "3"],
			]) {
				const field = [...dom.element.querySelectorAll("label")]
					.find((node) => node.querySelector("span")?.textContent === label)
					.querySelector("select");
				field.value = value;
				field.dispatchEvent(new Event("change", { bubbles: true }));
			}
		});
		const compare = [...dom.element.querySelectorAll("button")].find(
			(button) => button.textContent === "Compare systems",
		);
		assert.equal(compare.disabled, true);
		await enter(field("Target grid import limit"), "0");
		assert.equal(compare.disabled, false, "an explicit zero is a valid target");
	} finally {
		await dom.dispose(root);
	}
});

test("CSV uses customer mapping and a refused import can be corrected", async () => {
	const dom = setupDom();
	const { createRoot } = await import("react-dom/client");
	const root = createRoot(dom.element);
	let inputs = changeEnergyGoal({}, "peak");
	const calls = [];
	let refuse = true;
	const asset = {
		id: "3".repeat(32),
		project_id: projectId,
		content_sha256: "a".repeat(64),
		metadata_sha256: "b".repeat(64),
		media_type: "application/json",
		purpose: "csv_profile_v1",
		metadata: {},
	};
	const client = {
		isCurrentScope: () => true,
		query: async (path, body) => {
			calls.push({ path, body });
			if (path === "profiles/inspect")
				return {
					schema_version: 1,
					evaluation_scope: "csv_structure_only",
					content_sha256: "a".repeat(64),
					delimiter: ";",
					columns: ["time", "load"],
					record_count: 2,
					rows: [{ line: 2, cells: ["2026-01-01T00:00:00Z", "5"] }],
					rows_truncated: false,
				};
			if (path === "profiles/csv") {
				if (refuse) throw new ApiError(422, "invalid_input");
				return asset;
			}
			if (path === "assets/read") return asset;
			return {
				schema_version: 1,
				evaluation_scope: "profile_interpretation",
				project_id: projectId,
				asset_id: asset.id,
				content_sha256: asset.content_sha256,
				metadata_sha256: asset.metadata_sha256,
				measurement: "gross_load",
				source: {},
				transformations: [],
				summary: {
					start_utc: "2026-01-01T00:00:00Z",
					end_utc: "2026-01-01T02:00:00Z",
					interval_count: 2,
					covered_seconds: 7200,
					span_seconds: 7200,
					gap_seconds: 0,
					gap_count: 0,
					energy_kwh: 10,
					min_interval_mean_kw: 5,
					max_interval_mean_kw: 5,
					native_max_interval_seconds: 3600,
					effective_max_interval_seconds: 3600,
					reconstructed_means: false,
				},
				rows: [],
				first_gaps: [],
				gaps_truncated: false,
				next_offset: null,
			};
		},
	};
	const render = () =>
		root.render(
			<EnergyDemand
				projectId={projectId}
				inputs={inputs}
				locale="en"
				disabled={false}
				client={client}
				session={{
					query_scope: "scope",
					runtime: { limits: { max_csv_bytes: 10000, max_page_size: 20 } },
				}}
				coordinatesInvalid
				recheck={() => {}}
				edit={(operation) => {
					inputs = operation(inputs);
					render();
					return true;
				}}
				compare={() => {}}
			/>,
		);
	const control = (label, tag) =>
		[...dom.element.querySelectorAll("label")]
			.find((x) => x.textContent.includes(label))
			.querySelector(tag);
	const choose = async (label, value) => {
		const input = control(label, "select");
		await act(async () => {
			input.value = value;
			input.dispatchEvent(new Event("change", { bubbles: true }));
		});
	};
	const click = async (label) =>
		act(async () =>
			[...dom.element.querySelectorAll("button")]
				.find((x) => x.textContent === label)
				.click(),
		);
	try {
		await act(async () => render());
		const input = control("CSV file", "input");
		const meter = {
			name: "meter.csv",
			size: 13,
			arrayBuffer: async () =>
				new TextEncoder().encode("time;load\nx;y").buffer,
		};
		const drop = new Event("drop", { bubbles: true, cancelable: true });
		Object.defineProperty(drop, "dataTransfer", { value: { files: [meter] } });
		await act(async () => input.closest("label").dispatchEvent(drop));
		assert.equal(drop.defaultPrevented, true);
		assert.match(input.closest("label").textContent, /meter\.csv/);
		await click("Read CSV columns");
		await enter(control("Time zone", "input"), "Europe/Berlin");
		await choose("Timestamp column", "time");
		await choose("Consumption column", "load");
		await choose("Values represent", "interval_average_kw");
		await choose("Timestamp marks", "start");
		await enter(control("Interval length", "input"), "60");
		await choose("Decimal separator", ".");
		await choose("Data source", "measured");
		await enter(
			control("Source and permission", "textarea"),
			"Our own meter export",
		);
		await click("Use CSV consumption");
		assert.match(
			dom.element.querySelector('[role="alert"]').textContent,
			/Check the profile columns, units and time interval/,
		);
		assert.equal(inputs.profile_selections, undefined);
		const button = [...dom.element.querySelectorAll("button")].find(
			(x) => x.textContent === "Use CSV consumption",
		);
		assert.equal(
			button.disabled,
			false,
			"known pre-publication refusal allows corrected input",
		);
		refuse = false;
		await click("Use CSV consumption");
		const command = calls.find((x) => x.path === "profiles/csv").body;
		assert.equal(command.project_id, projectId);
		assert.equal(command.mapping.measurement, "gross_load");
		assert.equal(command.mapping.interval_seconds, 3600);
		assert.equal(command.mapping.timezone, "Europe/Berlin");
		assert.equal(inputs.profile_selections.selected.gross_load, asset.id);
		assert.equal(
			inputs.energy_scenario.schedule[0].start_utc,
			"2026-01-01T00:00:00Z",
		);
		assert.equal(
			inputs.energy_scenario.schedule[0].end_utc,
			"2026-01-01T02:00:00Z",
		);
		assert.equal(inputs.energy_scenario.battery.eta_charge, null);
	} finally {
		await dom.dispose(root);
	}
});
