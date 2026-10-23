/**
 * Shapes of the engine's answers that the configurator reads.
 *
 * The engine owns them (services/engine/src/linker_engine/models.py); the
 * request bodies are validated against the JSON Schemas it exports into
 * ./schema, so only the fields the screens use are typed here.
 */

export type Locale = 'en' | 'de';

export interface Range {
	low: number;
	high: number;
}

export interface Doc {
	url: string;
	page?: number | null;
}

export interface RuleResult {
	id: string;
	passed: boolean | null;
	value: number | string | null;
	limit?: number | string | null;
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

export type Verdict =
	'released' | 'released_with_accessory' | 'not_released' | 'unknown';

export interface Release {
	verdict: Verdict;
	conditions: string[];
	documents: Doc[];
}

export type Role =
	| 'inverter'
	| 'battery'
	| 'accessory'
	| 'meter'
	| 'backup'
	| 'controller'
	| 'pv_module'
	| 'mounting'
	| 'dc_cable'
	| 'connector'
	| 'string_fuse'
	| 'ac_protection';

export interface Line {
	role: Role;
	product: ProductRef | null;
	quantity: number;
	unit: 'pcs' | 'm' | 'pairs' | 'set';
	label: string;
	basis: string[];
	documents: Doc[];
}

export interface BatteryChoice {
	product: ProductRef;
	quantity: number;
	stacks: number;
	usable_kwh: number;
	above_upper_limit: boolean;
	release: Release;
}

export interface Selection {
	inverter: ProductRef;
	inverter_rules: RuleResult[];
	battery: BatteryChoice | null;
	lines: Line[];
}

export interface CandidateInverter {
	product: ProductRef;
	ac_power_kw: number | null;
	battery: BatteryChoice | null;
}

export interface Excluded {
	product: ProductRef;
	failed: RuleResult[];
}

export interface ReportSection {
	id: string;
	title: string;
	/** `href`: a document on de-linker.com that the value names. */
	rows: { label: string; value: string; href?: string | null }[];
	paragraphs: string[];
	table: { columns: string[]; rows: string[][] } | null;
}

export interface Report {
	title: string;
	subtitle: string;
	generated_at: string;
	locale: Locale;
	sections: ReportSection[];
}

export interface ResidentialResult {
	selection_fingerprint?: string;
	publication?: Record<string, unknown>;
	status: 'solution' | 'no_candidate';
	yield: {
		kwh_year_range: Range;
		kwh_year_mean: number;
		years: [ number, number ];
	};
	storage: {
		recommended: boolean;
		usable_kwh_range: Range | null;
		upper_kwh: number;
	};
	metrics: {
		usable_kwh: number;
		autarky_range: Range;
		self_consumption_range: Range;
	} | null;
	selected: Selection | null;
	candidates: {
		inverters: CandidateInverter[];
		batteries: BatteryChoice[];
		accessories: ProductRef[];
		excluded: Excluded[];
	};
	rules: RuleResult[];
	warnings: string[];
	relaxations: string[];
	report: Report;
}

export interface PlaneInput {
	kwp: number;
	tilt_deg: number;
	azimuth_deg: number;
}

export interface ResidentialInput {
	locale: Locale;
	plz: string;
	annual_kwh: number;
	pv_kwp: number;
	planes?: PlaneInput[];
	location?: { latitude: number; longitude: number };
	roof_source?: 'lod2' | 'drawn';
	phase: 1 | 3;
	backup: 'none' | 'needed' | 'needed_accessory_ok';
	backup_load_kw?: number;
	backup_hours?: number;
	heat_pump: boolean;
	electric_vehicle: boolean;
	existing_inverter?: string;
	inverter_id?: number;
	battery_id?: number;
}

export type Ring = [ number, number ][];

export interface RoofPlane {
	id: number;
	polygon: Ring;
	tilt_deg: number;
	azimuth_deg: number;
	area_m2: number;
	usable: boolean;
	excluded_reason: string | null;
	modules: number;
	kwp: number;
	module_polygons: Ring[];
}

export interface RoofResult {
	found: boolean;
	building_id: string | null;
	address: string | null;
	outline: Ring[];
	planes: RoofPlane[];
	modules: number;
	kwp: number;
	module: string;
	module_wp: number;
	source: string;
	licence: string;
	assumptions: string[];
}

export interface Place {
	plz: string;
	latitude: number;
	longitude: number;
	state: string;
	place: string;
	attribution: string;
	imagery: {
		tiles: string[];
		credit: string;
		licence: string;
		licence_url: string;
	} | null;
}

export type Goal = 'peak_shaving' | 'self_consumption' | 'backup';

export interface CommercialInput {
	locale: Locale;
	plz: string;
	grid_connection_kva: number;
	annual_kwh: number;
	goals: Goal[];
	peak_kw?: number;
	target_peak_kw?: number;
	pv_kwp?: number;
	backup_load_kw?: number;
	backup_hours?: number;
	load_profile_csv?: string;
	load_profile_unit: 'kW' | 'kWh';
	site: { installation: 'indoor' | 'outdoor' | 'unknown'; notes: string };
}

export interface ShavingOption {
	cap_kw: number;
	power_kw: number;
	energy_kwh: number;
	events: number;
}

export interface CommercialSystem {
	inverter: ProductRef;
	inverter_units: number;
	battery: ProductRef | null;
	battery_units: number;
	usable_kwh: number;
	power_kw: number;
	release: Release | null;
	lines: Line[];
}

export interface CommercialResult {
	selection_fingerprint?: string;
	publication?: Record<string, unknown>;
	status: 'sized' | 'indicative';
	load: {
		intervals: number;
		days: number;
		annual_kwh: number;
		peak_kw: number;
		base_kw: number;
		full_load_hours: number;
		duration_curve_kw: number[];
	} | null;
	options: ShavingOption[];
	power_kw_range: Range | null;
	energy_kwh_range: Range | null;
	basis: string[];
	systems: CommercialSystem[];
	warnings: string[];
	inquiry: string;
}

/** A product as the WooCommerce Store API describes it (wc/store/v1/products). */
export interface StoreProduct {
	id: number;
	name: string;
	permalink: string;
	images: { src: string; alt: string }[];
	is_in_stock: boolean;
}
