/**
 * The Solution Configurator's cases (docs/specs/14-solution-configurator.md
 * §验收): the eight typical households, the three compliance cases, the
 * commercial paths with and without a load profile, and the roof step at a
 * real address.
 *
 * The engine is the deployed one (`just serve <name>`, the same process the
 * app's screen calls); the requests are the app's own contract.
 */

/**
 * External dependencies
 */
import { expect, test } from '@playwright/test';

/**
 * Internal dependencies
 */
import {
	engineGet,
	enginePost,
	HOUSEHOLDS,
	loadProfileCsv,
	TRIFTSTRASSE_5,
	type CommercialResult,
	type ResidentialResult,
	type RoofResult,
} from '../lib/engine';
import { instance } from '../lib/instance';

const PLZ = '80538';

function design(fields: Record<string, unknown>): Promise<ResidentialResult> {
	return enginePost<ResidentialResult>('/design/residential', {
		locale: 'en',
		plz: PLZ,
		annual_kwh: 5000,
		pv_kwp: 10,
		phase: 3,
		...fields,
	});
}

test.describe('Solution Configurator', () => {
	for (const [kwp, kwh] of HOUSEHOLDS) {
		test(`household ${kwp} kWp / ${kwh} kWh stays inside the HTW caps and gets ranges`, async () => {
			const result = await design({ pv_kwp: kwp, annual_kwh: kwh });
			// HTW Berlin: usable capacity ≤ 1.5 kWh/kWp and ≤ 1.5 kWh/MWh·a.
			const cap = Math.min(1.5 * kwp, (1.5 * kwh) / 1000);
			expect(result.storage.recommended).toBe(true);
			expect(result.storage.usable_kwh_range).not.toBeNull();
			expect(result.storage.usable_kwh_range!.high).toBeLessThanOrEqual(
				cap + 1e-6
			);
			expect(
				result.storage.basis.map((rule) => rule.id),
				'the HTW basis names its rules'
			).toEqual(expect.arrayContaining(['htw_min_pv']));

			expect(result.yield.kwh_year_range.low).toBeLessThan(
				result.yield.kwh_year_range.high
			);
			expect(
				result.metrics,
				'self-sufficiency is reported as ranges'
			).not.toBeNull();
			for (const span of [
				result.metrics!.autarky_range,
				result.metrics!.self_consumption_range,
			]) {
				expect(span.low).toBeGreaterThanOrEqual(0);
				expect(span.low).toBeLessThan(span.high);
				expect(span.high).toBeLessThanOrEqual(1);
			}
		});
	}

	test('a three-phase 10 kWp home gets a complete released system', async () => {
		const result = await design({});
		expect(result.status).toBe('solution');
		const selected = result.selected;
		expect(selected, 'a system is selected').not.toBeNull();
		expect(selected!.inverter.device_class).toBe('inverters');
		expect(
			selected!.battery,
			'with a battery, since one was designed'
		).not.toBeNull();
		expect(
			['released', 'released_with_accessory'],
			'the pairing carries a release'
		).toContain(selected!.battery!.release.verdict);
		expect(
			selected!.battery!.release.documents.length,
			'the release names its documents'
		).toBeGreaterThan(0);
		// The bill of materials leads with the two big items, and everything
		// of ours carries a quantity.
		expect(selected!.lines.slice(0, 2).map((line) => line.role)).toEqual([
			'inverter',
			'battery',
		]);
		for (const line of selected!.lines.filter(
			(one) => one.product !== null
		)) {
			expect(line.quantity).toBeGreaterThanOrEqual(1);
		}
		// Nothing commercial and nothing single-phase among the candidates.
		for (const candidate of result.candidates.inverters) {
			expect(candidate.product.device_class).toBe('inverters');
		}
	});

	test('compliance: a single-phase request never gets an inverter above 4.6 kVA', async () => {
		const result = await design({ phase: 1, pv_kwp: 6, annual_kwh: 4000 });
		const excluded = new Map(
			result.candidates.excluded.map((one) => [
				one.product.model,
				one.failed.map((rule) => rule.id),
			])
		);
		for (const model of ['EF HD-P1-6K0-S2', 'GW6K-EHA-G20']) {
			expect(
				excluded.get(model),
				`${model} must be excluded for the single-phase limit`
			).toContain('single_phase_limit');
		}
		for (const candidate of result.candidates.inverters) {
			expect(
				candidate.ac_power_kw ?? 0,
				'a single-phase feed-in may not exceed the unbalance limit'
			).toBeLessThanOrEqual(4.6);
		}
	});

	test('compliance: an inverter whose PV input is too small is excluded', async () => {
		const result = await design({});
		const excluded = new Map(
			result.candidates.excluded.map((one) => [
				one.product.model,
				one.failed.map((rule) => rule.id),
			])
		);
		// HS2-5K takes 7.5 kWp and HS2-6K 9 kWp: both below the 10 kWp asked for.
		for (const model of ['HS2-5K-T2-X', 'HS2-6K-T2-X']) {
			expect(excluded.get(model), `${model} must be excluded`).toEqual(
				expect.arrayContaining(['pv_input'])
			);
		}
		// 10 kWp is exactly the HS3-5K's own limit: it stays a candidate.
		expect(excluded.has('HS3-5K-T2-W/G-PX')).toBe(false);
	});

	// Every MPPT input is its own fuse group: a fault in one string is fed by
	// the strings in parallel with it on the same input, so the count is
	// per-input, never per-array (rules.py STRING_FUSE_*, IEC 60364-7-712).
	// Two parallel strings of the reference module do not reach the reverse
	// current that needs fuses, and the layout spreads a large array over the
	// inverter's inputs rather than concentrating it, so the deployed products
	// top out at two strings per input and every group reads 0.
	// The counting branch itself is locked by the engine's own unit test
	// (services/engine/tests/test_strings.py:33), which reaches four parallel
	// strings directly; this case holds the deployed layout to the invariant.
	for (const kwp of [15, 25]) {
		test(`compliance: fuses are counted per MPPT string group (${kwp} kWp)`, async () => {
			const result = await design({ pv_kwp: kwp, annual_kwh: 8000 });
			expect(
				result.selected?.strings,
				'the strings are laid out'
			).toBeTruthy();
			const groups = result.selected!.strings!.groups;
			expect(groups.length).toBeGreaterThan(0);
			expect(result.selected!.strings!.module_count).toBe(
				groups.reduce(
					(total, group) =>
						total + group.strings * group.modules_per_string,
					0
				)
			);
			for (const group of groups) {
				// Two poles per string; anything else is neither the rule nor
				// "no fuses needed".
				expect([0, group.strings * 2]).toContain(group.fuses);
				if (group.strings < 2) {
					expect(group.fuses, 'a single string needs no fuse').toBe(
						0
					);
				}
			}
		});
	}

	test('commercial: a 15-minute load profile sizes power and energy, or offers caps', async () => {
		const withProfile = await enginePost<CommercialResult>(
			'/design/commercial',
			{
				locale: 'en',
				plz: PLZ,
				grid_connection_kva: 150,
				annual_kwh: 380000,
				goals: ['peak_shaving', 'self_consumption'],
				peak_kw: 120,
				load_profile_csv: loadProfileCsv(),
				load_profile_unit: 'kW',
			}
		);
		expect(withProfile.load, 'the profile is read').not.toBeNull();
		expect(withProfile.load!.intervals).toBe(30 * 96);
		expect(withProfile.load!.peak_kw).toBeGreaterThan(0);
		expect(
			withProfile.options.length,
			'the caps to choose from'
		).toBeGreaterThan(0);

		// With a cap chosen, the engine sizes a system in kW and kWh.
		const sized = await enginePost<CommercialResult>('/design/commercial', {
			locale: 'en',
			plz: PLZ,
			grid_connection_kva: 150,
			annual_kwh: 380000,
			goals: ['peak_shaving'],
			peak_kw: 120,
			target_peak_kw: 70,
			load_profile_csv: loadProfileCsv(),
			load_profile_unit: 'kW',
		});
		expect(sized.status).toBe('sized');
		expect(sized.power_kw_range, 'the power in kW').not.toBeNull();
		expect(sized.energy_kwh_range, 'the energy in kWh').not.toBeNull();
		expect(sized.systems.length, 'a system from our range').toBeGreaterThan(
			0
		);
		for (const system of sized.systems) {
			expect(system.inverter_units).toBeGreaterThanOrEqual(1);
			expect(system.power_kw).toBeGreaterThanOrEqual(
				sized.power_kw_range!.low
			);
		}
	});

	test('commercial: without a profile the answer is an indicative range plus the inquiry', async () => {
		const result = await enginePost<CommercialResult>(
			'/design/commercial',
			{
				locale: 'en',
				plz: PLZ,
				grid_connection_kva: 150,
				annual_kwh: 380000,
				goals: ['peak_shaving', 'self_consumption'],
				peak_kw: 120,
				target_peak_kw: 80,
				pv_kwp: 100,
			}
		);
		expect(result.status).toBe('indicative');
		expect(result.load).toBeNull();
		expect(result.systems).toEqual([]);
		expect(
			result.power_kw_range,
			'an indicative power range'
		).not.toBeNull();
		expect(
			result.energy_kwh_range,
			'an indicative energy range'
		).not.toBeNull();
		expect(result.inquiry, 'the inquiry route').toContain(
			'sales@de-linker.com'
		);
	});

	test('roof step: a real Munich address yields an outline and a module count', async () => {
		const outline = await enginePost<RoofResult>('/roof/outline', {
			plz: PLZ,
			location: TRIFTSTRASSE_5,
			locale: 'en',
		});
		expect(outline.found).toBe(true);
		expect(outline.address).toBe('Triftstraße 5');
		expect(outline.outline.length).toBeGreaterThan(0);
		expect(outline.outline[0]!.length).toBeGreaterThanOrEqual(4);
		expect(outline.planes.length).toBeGreaterThan(0);
		expect(outline.modules).toBeGreaterThan(0);
		expect(outline.modules).toBe(
			outline.planes.reduce((total, plane) => total + plane.modules, 0)
		);
		expect(outline.kwp).toBeCloseTo(
			(outline.modules * outline.module_wp) / 1000,
			2
		);
		for (const plane of outline.planes) {
			expect(plane.modules).toBe(plane.usable ? plane.modules : 0);
		}
		expect(outline.licence).toContain('CC BY 4.0');
		expect(
			outline.assumptions.length,
			'the assumptions are disclosed'
		).toBeGreaterThan(0);

		// The PLZ's own centre is not on a building: the step must say so
		// rather than invent a roof.
		const place = await engineGet<{ latitude: number; longitude: number }>(
			`/geo/plz/${PLZ}`
		);
		const beside = await enginePost<RoofResult>('/roof/outline', {
			plz: PLZ,
			location: { latitude: place.latitude, longitude: place.longitude },
			locale: 'en',
		});
		expect(beside.modules).toBe(0);
	});

	test('the design report is a PDF in both languages', async () => {
		for (const locale of ['en', 'de']) {
			const response = await fetch(`${instance().engineUrl}/report/pdf`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					input: {
						locale,
						plz: PLZ,
						annual_kwh: 5000,
						pv_kwp: 10,
						phase: 3,
					},
				}),
			});
			expect(response.status, `the ${locale} report`).toBe(200);
			expect(response.headers.get('content-type')).toContain(
				'application/pdf'
			);
			const body = Buffer.from(await response.arrayBuffer());
			expect(body.subarray(0, 5).toString('latin1')).toBe('%PDF-');
			expect(body.length).toBeGreaterThan(10_000);
		}
	});
});
