/**
 * The Solution Configurator's engine (`just serve <name>` writes its address
 * into the instance's `linker_engine_url` option; here it is the port
 * `instances.toml` registers). The app itself is a React screen; these calls
 * are its own contract (docs/specs/14-solution-configurator.md §引擎).
 */

/**
 * Internal dependencies
 */
import { instance } from './instance';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${instance().engineUrl}${path}`, init);
	const body = await response.text();
	if (!response.ok) {
		throw new Error(
			`the engine answered ${response.status} for ${path}: ${body.slice(0, 400)}`
		);
	}
	return JSON.parse(body) as T;
}

export function engineGet<T>(path: string): Promise<T> {
	return request<T>(path);
}

export function enginePost<T>(path: string, body: unknown): Promise<T> {
	return request<T>(path, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
	});
}

export interface Range {
	low: number;
	high: number;
}

export interface RuleResult {
	id: string;
	passed: boolean | null;
	value: number | string | null;
	limit: number | string | null;
	label: string;
	text: string;
}

export interface ProductRef {
	id: number;
	sku: string;
	model: string;
	brand: string;
	device_class: string;
}

export interface Release {
	verdict:
		'released' | 'released_with_accessory' | 'not_released' | 'unknown';
	conditions: string[];
	documents: Array<{ url: string; page?: number }>;
}

export interface Line {
	role: string;
	product: ProductRef | null;
	quantity: number;
	unit: string;
	label: string;
	basis: string[];
	documents: Array<{ url: string; page?: number }>;
}

export interface StringGroup {
	mppt: number;
	strings: number;
	modules_per_string: number;
	fuses: number;
}

export interface ResidentialResult {
	status: 'solution' | 'no_candidate';
	yield: {
		kwh_year_range: Range;
		kwh_per_kwp_range: Range;
		kwh_year_mean: number;
		source: string;
	};
	storage: {
		recommended: boolean;
		usable_kwh_range: Range | null;
		upper_kwh: number;
		backup_reserve_kwh: number;
		basis: RuleResult[];
	};
	metrics: {
		usable_kwh: number;
		autarky_range: Range;
		self_consumption_range: Range;
		basis: string;
	} | null;
	selected: {
		inverter: ProductRef;
		inverter_rules: RuleResult[];
		battery: {
			product: ProductRef;
			quantity: number;
			stacks: number;
			usable_kwh: number;
			above_upper_limit: boolean;
			release: Release;
		} | null;
		strings: {
			module: string;
			module_count: number;
			array_kwp: number;
			groups: StringGroup[];
		} | null;
		lines: Line[];
	} | null;
	candidates: {
		inverters: Array<{ product: ProductRef; ac_power_kw: number | null }>;
		batteries: Array<{ product: ProductRef; usable_kwh: number }>;
		excluded: Array<{ product: ProductRef; failed: RuleResult[] }>;
	};
	rules: RuleResult[];
	warnings: string[];
	relaxations: string[];
	report: {
		title: string;
		locale: string;
		sections: Array<{
			id: string;
			title: string;
			rows: Array<{ label: string }>;
		}>;
	};
}

export interface CommercialResult {
	status: 'sized' | 'indicative';
	load: {
		intervals: number;
		days: number;
		annual_kwh: number;
		peak_kw: number;
		full_load_hours: number;
	} | null;
	options: Array<{
		cap_kw: number;
		power_kw: number;
		energy_kwh: number;
		events: number;
	}>;
	power_kw_range: Range | null;
	energy_kwh_range: Range | null;
	basis: string[];
	systems: Array<{
		inverter: ProductRef;
		inverter_units: number;
		battery: ProductRef | null;
		usable_kwh: number;
		power_kw: number;
		lines: Line[];
	}>;
	warnings: string[];
	inquiry: string;
}

export interface RoofResult {
	found: boolean;
	building_id: string | null;
	address: string | null;
	outline: Array<Array<[number, number]>>;
	planes: Array<{
		id: number;
		tilt_deg: number;
		azimuth_deg: number;
		usable: boolean;
		excluded_reason: string | null;
		modules: number;
		kwp: number;
	}>;
	modules: number;
	kwp: number;
	module: string;
	module_wp: number;
	source: string;
	licence: string;
	assumptions: string[];
}

/** The eight typical households of planner-methods.md §4.1: (kWp, kWh a year). */
export const HOUSEHOLDS: Array<[number, number]> = [
	[5, 3000],
	[6, 2500],
	[8, 4000],
	[10, 4000],
	[10, 5000],
	[12, 6000],
	[15, 8000],
	[10, 10000],
];

/** The Munich address of the roof step's fixture (engine tests/conftest.py). */
export const TRIFTSTRASSE_5 = { latitude: 48.140278, longitude: 11.588411 };

/** A 30-day 15-minute load profile, as the C&I step uploads it. */
export function loadProfileCsv(days = 30): string {
	const values: number[] = [];
	for (let day = 0; day < days; day += 1) {
		for (let quarter = 0; quarter < 96; quarter += 1) {
			const hour = (quarter * 15) / 60;
			const base = 40 + 30 * Math.sin(((hour - 6) / 24) * 2 * Math.PI);
			const jitter = Math.sin(day * 1.7 + quarter * 0.31) * 6;
			values.push(Math.round(Math.max(5, base + jitter) * 1000) / 1000);
		}
	}
	return values.join('\n');
}
