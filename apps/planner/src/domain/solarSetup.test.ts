import test from "node:test";
import type { GeometryDocument } from "./geometry.ts";
import assert from "node:assert/strict";
import fixture from "../../tests/fixtures/preparation-flow.json" with { type: "json" };
import { ApiError } from "../data/protocol.ts";
import {
	readSolarSetup,
	solarInputs,
	compileWeather,
	compilePv,
	alignPv,
	prepareWeatherInputs,
	preparePvInputs,
	emptyConverter,
	checkPvWeather,
} from "./solarSetup.ts";

const inputs = () => structuredClone(fixture.pv_project.inputs);
const refusal = (code: string) => (error: unknown) =>
	error instanceof ApiError && error.code === code;

test("solar drafts retain incomplete explicit choices without inventing parameter values", () => {
	const blank = readSolarSetup({});
	assert.equal(blank.weather.request.latitude_deg, null);
	assert.equal(blank.weather.request.use_terrain_horizon, null);
	assert.equal(blank.weather.interpretation.synthetic_energy_year, null);
	assert.deepEqual(blank.pv.arrays, []);
	assert.throws(
		() => compileWeather(blank.weather),
		refusal("weather_parameters_incomplete"),
	);
	assert.throws(
		() => compilePv(blank.pv, inputs().geometry),
		refusal("pv_parameters_incomplete"),
	);
	assert.deepEqual(readSolarSetup({ solar_setup: blank }), blank);
	assert.equal(emptyConverter().eta_nominal, null);
});

test("PV preflight requires a selected source and compares the effective weather request with roof coordinates", () => {
	const original = inputs();
	assert.doesNotThrow(() => checkPvWeather(original));
	assert.throws(
		() => checkPvWeather({ ...original, pv_preparation: {} }),
		refusal("pv_weather_required"),
	);
	assert.throws(
		() =>
			checkPvWeather({
				...original,
				pv_preparation: {
					...(original.pv_preparation as object),
					unexpected: true,
				},
			}),
		refusal("pv_weather_required"),
	);
	assert.throws(
		() =>
			checkPvWeather({
				...original,
				weather_acquisition: {
					...readSolarSetup(original).weather,
					request: {
						...readSolarSetup(original).weather.request,
						latitude_deg: 51,
					},
				},
			}),
		refusal("pv_weather_location_mismatch"),
	);
	const setup = readSolarSetup(original);
	// An unprepared draft weather choice is not the source selected for this run.
	assert.doesNotThrow(() =>
		checkPvWeather({
			...original,
			solar_setup: {
				...setup,
				weather: {
					...setup.weather,
					request: { ...setup.weather.request, latitude_deg: 51 },
				},
			},
		}),
	);
});

test("actual published worker fixture compiles identically, without model defaults or rounding", () => {
	const original = inputs(),
		setup = readSolarSetup(original);
	assert.deepEqual(compileWeather(setup.weather), original.weather_acquisition);
	assert.deepEqual(
		compilePv(setup.pv, original.geometry),
		original.pv_generation,
	);
	assert.deepEqual(
		prepareWeatherInputs(original).weather_acquisition,
		original.weather_acquisition,
	);
	assert.deepEqual(
		preparePvInputs(original).pv_generation,
		original.pv_generation,
	);
});

test("draft version, identities, constants, structure and numeric types stay strict", () => {
	const setup = readSolarSetup(inputs());
	for (const solar_setup of [
		{ ...setup, schema_version: 2 },
		{ ...setup, unexpected: 1 },
		{ ...setup, weather: { ...setup.weather, schema_version: null } },
		{
			...setup,
			weather: {
				...setup.weather,
				request: { ...setup.weather.request, schema_version: 2 },
			},
		},
		{
			...setup,
			weather: {
				...setup.weather,
				request: { ...setup.weather.request, api_version: "5.2" },
			},
		},
		{
			...setup,
			weather: {
				...setup.weather,
				request: { ...setup.weather.request, latitude_deg: "52.52" },
			},
		},
		{
			...setup,
			pv: { ...setup.pv, arrays: [{ ...setup.pv.arrays[0], array_id: "" }] },
		},
		{
			...setup,
			pv: {
				...setup.pv,
				modules: [{ ...setup.pv.modules[0], gamma_pdc_per_c: Infinity }],
			},
		},
	])
		assert.throws(() => readSolarSetup({ solar_setup }));
});

test("weather preparation checks year order, integer/range constraints and non-leap output axis", () => {
	const value = readSolarSetup(inputs()).weather;
	assert.throws(
		() =>
			compileWeather({
				...value,
				request: { ...value.request, start_year: 2024, end_year: 2023 },
			}),
		refusal("weather_year_order"),
	);
	for (const year of [2000, 2024])
		assert.throws(
			() =>
				compileWeather({
					...value,
					interpretation: {
						...value.interpretation,
						synthetic_energy_year: year,
					},
				}),
			refusal("weather_leap_axis"),
		);
	assert.equal(
		compileWeather({
			...value,
			interpretation: { ...value.interpretation, synthetic_energy_year: 1900 },
		}).schema_version,
		1,
	);
	for (const request of [
		{ ...value.request, start_year: 2005.5 },
		{ ...value.request, latitude_deg: 90.01 },
		{ ...value.request, longitude_deg: -180.01 },
	])
		assert.throws(
			() => compileWeather({ ...value, request }),
			refusal("weather_parameters_incomplete"),
		);
});

test("changing source/model inputs invalidates prepared documents and retains unrelated draft edits", () => {
	const original = {
			...inputs(),
			unrelated: "keep",
			energy_replay: { schema_version: 1 },
		},
		setup = readSolarSetup(original);
	const weather = solarInputs(original, {
		...setup,
		weather: {
			...setup.weather,
			request: { ...setup.weather.request, use_terrain_horizon: true },
		},
	});
	assert.equal(weather.weather_acquisition, undefined);
	assert.deepEqual(weather.pv_generation, original.pv_generation);
	assert.equal(weather.unrelated, "keep");
	const pv = solarInputs(original, {
		...setup,
		pv: { ...setup.pv, source_note: "Changed declared assumption" },
	});
	assert.equal(pv.pv_generation, undefined);
	assert.equal(pv.energy_replay, undefined);
	assert.deepEqual(pv.pv_preparation, original.pv_preparation);
	assert.deepEqual(pv.weather_acquisition, original.weather_acquisition);
	assert.deepEqual(
		solarInputs(original, setup).pv_generation,
		original.pv_generation,
	);
});

test("PV preparation requires the current active layout, exact module set and partitioned conversion groups", () => {
	const original = inputs(),
		value = readSolarSetup(original).pv;
	const first = value.converters[0]!;
	for (const pv of [
		{ ...value, arrays: [...value.arrays, ...value.arrays] },
		{
			...value,
			modules: [
				...value.modules,
				{ ...value.modules[0]!, module_spec_id: "unused" },
			],
		},
		{ ...value, converters: [first, { ...first, id: "second" }] },
	])
		assert.throws(
			() => compilePv(pv, original.geometry),
			refusal("pv_layout_changed"),
		);
	assert.throws(
		() =>
			compilePv(value, {
				...original.geometry,
				coordinate_system: {
					...original.geometry.coordinate_system,
					anchor: null,
				},
			}),
		refusal("pv_location_required"),
	);
	assert.throws(() =>
		compilePv(value, {
			...original.geometry,
			arrays: original.geometry.arrays.map((a) => ({
				...a,
				excluded_slots: Array.from({ length: a.rows }, (_, row) =>
					Array.from({ length: a.columns }, (_, column) => `${row}:${column}`),
				).flat(),
			})),
		}),
	);
	const aligned = alignPv(
		{ ...value, arrays: [], modules: [], converters: [] },
		original.geometry,
	);
	assert.equal(aligned.arrays[0]!.thermal.a, null);
	assert.equal(aligned.modules[0]!.gamma_pdc_per_c, null);
	assert.equal(aligned.converters.length, 0);
	assert.deepEqual(alignPv(value, original.geometry), value);
});

test("PV source references require complete safe datasheet evidence before preparation", () => {
	const original = inputs(),
		value = readSolarSetup(original).pv,
		first = value.modules[0]!;
	const source = {
		kind: "datasheet" as const,
		note: "Declared document",
		document_sha256: "a".repeat(64),
		page: 2,
		url: "https://manufacturer.example/module.pdf",
	};
	assert.ok(
		compilePv({ ...value, modules: [{ ...first, source }] }, original.geometry),
	);
	for (const changed of [
		{ ...source, url: null },
		{ ...source, page: null },
		{ ...source, document_sha256: null },
		{ ...source, url: "javascript:alert(1)" },
		{ ...source, url: "https://user:password@manufacturer.example/file.pdf" },
	])
		assert.throws(() =>
			compilePv(
				{ ...value, modules: [{ ...first, source: changed }] },
				original.geometry,
			),
		);
	assert.throws(
		() =>
			compilePv(
				{ ...value, converters: [{ ...value.converters[0]!, eta_nominal: 0 }] },
				original.geometry,
			),
		refusal("pv_parameters_incomplete"),
	);
});

test("explicit weather replacement clears only the stale binding and prepared replay, so native saving can accept the new request", () => {
	const original = {
		...inputs(),
		energy_replay: { schema_version: 1 },
		profile_selections: {
			schema_version: 1,
			selected: { pv_available_ac: "a".repeat(32), gross_load: "b".repeat(32) },
		},
		unrelated: "keep",
	};
	const setup = readSolarSetup(original);
	const changed = solarInputs(original, {
		...setup,
		weather: {
			...setup.weather,
			request: { ...setup.weather.request, use_terrain_horizon: true },
		},
	});
	assert.deepEqual(
		changed.pv_preparation,
		original.pv_preparation,
		"editing a field does not select or remove a source",
	);
	const prepared = prepareWeatherInputs(changed);
	assert.equal(prepared.pv_preparation, undefined);
	assert.equal(prepared.energy_replay, undefined);
	assert.deepEqual(prepared.profile_selections, original.profile_selections);
	assert.deepEqual(prepared.pv_generation, original.pv_generation);
	assert.equal(prepared.unrelated, "keep");
	assert.deepEqual(
		prepareWeatherInputs(original).pv_preparation,
		original.pv_preparation,
		"preparing unchanged settings retains the matching selection",
	);
});

test("a maintained module selection supplies the coefficient and keeps the array settings", () => {
	const value = inputs();
	const setup = readSolarSetup(value);
	const geometry = structuredClone(
		value.geometry,
	) as unknown as GeometryDocument;
	const specification = geometry.module_specs[0]!;
	const source = {
		kind: "datasheet" as const,
		note: "Synthetic maintained-source contract fixture",
		url: "https://example.test/module.pdf",
		document_sha256: "b".repeat(64),
		page: 1,
		woo: {
			product_id: 42,
			product_revision: "a".repeat(64),
			reference_input_id: "synthetic_woo_reference",
		},
	};
	specification.source = source;
	const parameter = { ...setup.pv.modules[0]!, source };
	const template = {
		specification: { ...specification },
		parameters: parameter,
	};
	const next = alignPv({ ...setup.pv, modules: [] }, geometry, [template]);
	assert.deepEqual(next.modules, [parameter]);
	assert.deepEqual(next.arrays, setup.pv.arrays);
	assert.deepEqual(next.converters, setup.pv.converters);
});
