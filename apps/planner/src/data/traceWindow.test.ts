import test from "node:test";
import assert from "node:assert/strict";
import { readTraceWindow, traceCsv } from "./traceWindow.ts";
import { readRun } from "./planningProtocol.ts";
import original from "../../tests/fixtures/energy-run.json" with { type: "json" };

test("an exact bounded window remains bound to its saved run and CSV values", () => {
	const run = readRun(original, original.project_id),
		count = Number(run.result!.interval_count),
		row = {
			interval_index: 0,
			start_utc: "2023-01-01T00:00:00+00:00",
			end_utc: "2023-01-01T01:00:00+00:00",
			load_kw: 2,
			pv_kw: 1,
			charge_kw: 0,
			discharge_kw: 0.25,
			import_kw: 0.75,
			export_kw: 0,
			stored_kwh: 1.2345678901234567,
		};
	const value = {
		schema_version: 1,
		run_id: run.id,
		manifest_sha256: run.manifest_sha256,
		trace_sha256: run.result!.trace_sha256,
		interval_count: count,
		offset: 0,
		rows: [row],
		next_offset: count > 1 ? 1 : null,
	};
	const page = readTraceWindow(value, run, 0, 1);
	assert.equal(page.rows[0]!.stored_kwh, row.stored_kwh);
	for (const changed of [
		{ ...value, trace_sha256: "0".repeat(64) },
		{ ...value, rows: [{ ...row, interval_index: 1 }] },
		{ ...value, rows: [row, row] },
	])
		assert.throws(() => readTraceWindow(changed, run, 0, 1));
	const csv = traceCsv(page, [
		"start_utc",
		"end_utc",
		"Last (kW)",
		"PV (kW)",
		"Laden (kW)",
		"Entladen (kW)",
		"Netzbezug (kW)",
		"Netzeinspeisung (kW)",
		"Speicher (kWh)",
	]);
	assert.ok(csv.includes('"1.2345678901234567"'));
	assert.equal(csv.split("\r\n").length, 3);
	assert.ok(csv.includes(row.start_utc));
});
