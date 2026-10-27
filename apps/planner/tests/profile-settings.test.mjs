import assert from "node:assert/strict";
import test from "node:test";
import React, { act } from "react";
import { setupDom } from "./dom-fixture.mjs";

const mapping = {
	timestamp_column: "recorded_at",
	value_column: "meter_value",
	measurement: "net_import",
	value_kind: "interval_average_kw",
	timestamp_role: "start",
	timezone: "Europe/Oslo",
	origin: "synthetic",
	interval_seconds: 900,
	delimiter: ";",
	decimal: ",",
	end_timestamp_column: null,
	fold_column: null,
	end_fold_column: null,
	offset_rule: "explicit_offset_precedes_naive_timezone",
	within_interval_assumption: "constant_mean_no_new_observations",
};

for (const [name, overrides, expected] of [
	[
		"fixed start intervals",
		{},
		{
			"Value meaning and unit": "Average power over each interval · kW",
			"The timestamp identifies…": "The start of the interval",
			"Interval duration": "15 min",
			"Column delimiter": "Semicolon",
			"Interval end column": "Not used",
		},
	],
	[
		"fractional end intervals and energy values",
		{
			value_kind: "interval_energy_kwh",
			timestamp_role: "end",
			interval_seconds: 6,
			delimiter: "\t",
		},
		{
			"Value meaning and unit": "Energy within each interval · kWh",
			"The timestamp identifies…": "The end of the interval",
			"Interval duration": "0,1 min",
			"Column delimiter": "Tab",
		},
	],
	[
		"separate boundaries with repeated-time columns",
		{
			interval_seconds: null,
			end_timestamp_column: "finished_at",
			fold_column: "start_occurrence",
			end_fold_column: "end_occurrence",
		},
		{
			"Interval boundaries": "Separate start and end columns",
			"Interval end column": "finished_at",
			"Repeated-time column · optional": "start_occurrence",
			"End repeated-time column · optional": "end_occurrence",
		},
	],
]) {
	test(`frozen source settings explain ${name} without changing the command`, async (t) => {
		const dom = setupDom();
		const { createRoot } = await import("react-dom/client");
		const { ProfileImportSettings } =
			await import("../src/components/ProfileImportSettings.tsx");
		const { readImport } = await import("../src/domain/profiles.ts");
		const command = readImport({
			schema_version: 1,
			project_id: "a".repeat(32),
			key: "11111111-1111-4111-8111-111111111111",
			content_base64: btoa("Synthetic fixture"),
			mapping: { ...mapping, ...overrides },
			source_label: "Frozen source",
			rights_note: "Synthetic fixture; permitted private storage",
		});
		Object.freeze(command.mapping);
		Object.freeze(command);
		const before = JSON.stringify(command);
		const root = createRoot(dom.element);
		t.after(() => dom.dispose(root));
		await act(async () =>
			root.render(
				React.createElement(ProfileImportSettings, {
					command,
					locale: "de-DE",
				}),
			),
		);
		const facts = Object.fromEntries(
			[...dom.element.querySelectorAll("dl > div")].map((row) => [
				row.querySelector("dt").textContent,
				row.querySelector("dd").textContent,
			]),
		);
		assert.equal(facts["Source label"], command.source_label);
		assert.equal(facts["Timestamp column"], "recorded_at");
		assert.equal(facts["Value column"], "meter_value");
		assert.equal(
			facts["Measurement point"],
			"Net grid import · negative values mean export",
		);
		assert.equal(facts["Source time zone"], "Europe/Oslo");
		assert.equal(
			facts["Source and permission for permanent private storage"],
			command.rights_note,
		);
		for (const [label, value] of Object.entries(expected))
			assert.equal(facts[label], value, label);
		if (command.mapping.interval_seconds === null)
			assert.ok(!("Interval duration" in facts));
		assert.equal(
			dom.element.querySelectorAll("input,select,textarea,pre").length,
			0,
		);
		assert.equal(JSON.stringify(command), before);
		assert.match(
			dom.element.textContent,
			/explicit UTC offset takes precedence/,
		);
		assert.match(
			dom.element.textContent,
			/constant within each original interval/,
		);
		const { valueKindLabel, timestampRoleLabel } =
			await import("../src/components/ProfileLabels.ts");
		assert.equal(valueKindLabel("unknown_source_kind"), "Not specified");
		assert.equal(timestampRoleLabel("unknown_source_role"), "Not specified");
	});
}
