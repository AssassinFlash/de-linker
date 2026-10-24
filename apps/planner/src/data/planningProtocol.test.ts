import test from "node:test";
import assert from "node:assert/strict";
import runJson from "../../tests/fixtures/energy-run.json" with { type: "json" };
import { readRun, readRunPage } from "./planningProtocol.ts";
import { readObject as objectDocument } from "./readProtocol.ts";
import { ApiError } from "./protocol.ts";
import type { JsonObject } from "./protocol.ts";

type MutableObject = { -readonly [P in keyof JsonObject]: JsonObject[P] };
const readObject = (value: unknown): MutableObject =>
	objectDocument(value) as MutableObject;
const original = () => readObject(structuredClone(runJson));
const result = (run: JsonObject) => readObject(run.result);
test("actual managed two-hour result retains frozen identity, source origins and analytic totals", () => {
	const run = readRun(runJson, runJson.project_id, runJson.id);
	assert.equal(readObject(run.result!.metrics).solar_load_kwh, 3.62);
	assert.equal(
		readObject(readObject(run.result!.metrics).solar_autarky).value,
		0.905,
	);
	assert.equal(
		readObject(run.result!.equipment_release).status,
		"not_assessed",
	);
});

test("result mutants cannot be presented as a validated customer result", () => {
	const mutants: ((run: MutableObject) => void)[] = [
		(run) => {
			run.project_id = "f".repeat(32);
		},
		(run) => {
			result(run).revision = 9;
		},
		(run) => {
			result(run).manifest_sha256 = "0".repeat(64);
		},
		(run) => {
			result(run).runtime_sha256 = "0".repeat(64);
		},
		(run) => {
			readObject(result(run).model).eta_charge = 0;
		},
		(run) => {
			readObject(result(run).model).battery_export = "allowed";
		},
		(run) => {
			readObject(result(run).pinned_assets)["gross_load.raw"] = "0".repeat(64);
		},
		(run) => {
			readObject(result(run).verification).checks = [null];
		},
		(run) => {
			readObject(result(run).verification).passed = false;
		},
		(run) => {
			readObject(result(run).profile_interpretation).operating_periods = [{}];
		},
		(run) => {
			readObject(result(run).country_assessment).status = "approved";
		},
		(run) => {
			readObject(result(run).metrics).grid_import_kwh = NaN;
		},
		(run) => {
			readObject(readObject(result(run).metrics).solar_autarky).value = null;
		},
	];
	for (const mutate of mutants) {
		const changed = original();
		mutate(changed);
		assert.throws(
			() => readRun(changed, runJson.project_id),
			(error: unknown) => error instanceof ApiError && error.status === 502,
		);
	}
});

test("mixed or empty load scope keeps its undefined reason and never gains a gross percentage", () => {
	const mixed = original(),
		metrics = readObject(result(mixed).metrics);
	metrics.load_measurement_scope = "mixed";
	metrics.solar_autarky = {
		value: null,
		undefined_reason: "requested_load_scope_is_not_whole_site_gross",
	};
	assert.equal(
		readObject(readRun(mixed, runJson.project_id).result!.metrics)
			.load_measurement_scope,
		"mixed",
	);
	const zero = original(),
		totals = readObject(result(zero).metrics);
	totals.load_demand_kwh = 0;
	totals.pv_generated_ac_kwh = 0;
	totals.solar_autarky = {
		value: null,
		undefined_reason: "gross_load_is_zero",
	};
	totals.pv_input_self_use = {
		value: null,
		undefined_reason: "pv_generation_is_zero",
	};
	assert.equal(
		readObject(
			readObject(readRun(zero, runJson.project_id).result!.metrics)
				.solar_autarky,
		).value,
		null,
	);
});

test("paginated run history validates owner, finite date and actual cursor names", () => {
	const summary = {
		id: runJson.id,
		project_id: runJson.project_id,
		revision: runJson.revision,
		manifest_sha256: runJson.manifest_sha256,
		result_sha256: runJson.result_sha256,
		state: runJson.state,
		is_current: false,
		created_at: 1700000000,
	};
	const next = { before_created_at: summary.created_at, before_id: summary.id };
	assert.deepEqual(
		readRunPage({ items: [summary], next }, runJson.project_id).next,
		next,
	);
	assert.throws(() =>
		readRunPage(
			{ items: [{ ...summary, created_at: 1e30 }], next: null },
			runJson.project_id,
		),
	);
	assert.throws(() =>
		readRunPage(
			{ items: [summary], next: { created_at: 1, run_id: summary.id } },
			runJson.project_id,
		),
	);
});
