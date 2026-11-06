/**
 * Generic module size/power tiers for roof layout and planning arithmetic.
 *
 * These are planning references, not product data. Every number below is a
 * mid-range value for the mainstream M10/G12 module families a customer is
 * likely to install — an unverified planning assumption, not a value read
 * from any manufacturer datasheet. The planner never presents them as a
 * Linker product, a quotation basis or a verified product fact; the
 * customer's actual modules govern the built array.
 *
 * Format sizes follow the wafer families that set the outer dimensions
 * (54-cell M10 ≈ 1.7–1.8 m, 60-cell M10 ≈ 1.96 m, 72-cell M10 ≈ 2.28 m,
 * 66-cell G12 ≈ 2.38 m). Electrical values sit in the middle of the usual
 * spread for those formats so that string voltage, current and the energy
 * model stay inside a realistic range on either side of the assumption; the
 * moduleTiers test holds Vmp × Imp close to the tier's nameplate power.
 */
import type { ModuleSpec } from "./geometry.ts";

/** What this record is: a declared planning reference, never a Woo product. */
export interface DeclaredReferenceSource {
	readonly kind: "declared_reference";
	readonly source_note: string;
}

export interface PlanningModuleTier {
	readonly id: string;
	/** Language-neutral label: it is stored in the geometry and listed as an
	 * object name, so it carries units but no prose in either language. */
	readonly model: string;
	/** STC nameplate power the tier is drawn for. */
	readonly stc_power_w: number;
	readonly length_m: number;
	readonly width_m: number;
	readonly thickness_m: number;
	/** Fraction of Pmax lost per °C above 25 °C: mid-range silicon value,
	 * recorded as a planning assumption like every other number here. */
	readonly gamma_pdc_per_c: number;
	/** STC electrical points, chosen so Vmp × Imp ≈ stc_power_w; planning
	 * assumptions, not datasheet readings. */
	readonly voc_v: number;
	readonly vmp_v: number;
	readonly isc_a: number;
	readonly imp_a: number;
	readonly source: DeclaredReferenceSource;
}

const SOURCE_NOTE =
	"Generic tier planning reference; unverified planning assumption, not a manufacturer datasheet value. Customer-supplied modules, not a Linker product.";

const TIERS = [
	{
		id: "tier_400",
		model: "PV 400 Wp · 1722 × 1134 mm",
		stc_power_w: 400,
		length_m: 1.722,
		width_m: 1.134,
		thickness_m: 0.035,
		gamma_pdc_per_c: -0.0034,
		voc_v: 37.2,
		vmp_v: 31.2,
		isc_a: 13.6,
		imp_a: 12.8,
	},
	{
		id: "tier_450",
		model: "PV 450 Wp · 1762 × 1134 mm",
		stc_power_w: 450,
		length_m: 1.762,
		width_m: 1.134,
		thickness_m: 0.035,
		gamma_pdc_per_c: -0.0034,
		voc_v: 40.9,
		vmp_v: 34.4,
		isc_a: 13.9,
		imp_a: 13.08,
	},
	{
		id: "tier_500",
		model: "PV 500 Wp · 1960 × 1134 mm",
		stc_power_w: 500,
		length_m: 1.96,
		width_m: 1.134,
		thickness_m: 0.035,
		gamma_pdc_per_c: -0.0034,
		voc_v: 45.6,
		vmp_v: 38.2,
		isc_a: 13.95,
		imp_a: 13.09,
	},
	{
		id: "tier_550",
		model: "PV 550 Wp · 2278 × 1134 mm",
		stc_power_w: 550,
		length_m: 2.278,
		width_m: 1.134,
		thickness_m: 0.035,
		gamma_pdc_per_c: -0.0034,
		voc_v: 49.9,
		vmp_v: 41.8,
		isc_a: 14.0,
		imp_a: 13.16,
	},
	{
		id: "tier_600",
		model: "PV 600 Wp · 2384 × 1303 mm",
		stc_power_w: 600,
		length_m: 2.384,
		width_m: 1.303,
		thickness_m: 0.035,
		gamma_pdc_per_c: -0.0034,
		voc_v: 53.6,
		vmp_v: 44.8,
		isc_a: 14.2,
		imp_a: 13.4,
	},
] as const;

export const MODULE_TIERS: readonly PlanningModuleTier[] = TIERS.map(
	(tier) => ({
		...tier,
		source: { kind: "declared_reference", source_note: SOURCE_NOTE },
	}),
);

/**
 * 450 Wp is the default because it is the tier nearest the reference module
 * the configurator used before this list existed (460 Wp), so an existing
 * draft keeps its roof layout when it is reopened.
 */
export const DEFAULT_MODULE_TIER: PlanningModuleTier = MODULE_TIERS[1]!;

/** Nearest tier for a declared power; the default when no usable value exists. */
export function tierFor(stcPowerW: number): PlanningModuleTier {
	if (!Number.isFinite(stcPowerW) || stcPowerW <= 0) return DEFAULT_MODULE_TIER;
	let best = MODULE_TIERS[0]!;
	for (const tier of MODULE_TIERS)
		if (
			Math.abs(tier.stc_power_w - stcPowerW) <
			Math.abs(best.stc_power_w - stcPowerW)
		)
			best = tier;
	return best;
}

/**
 * Projection into the stored geometry shape. `source.kind` must stay
 * `user_declared` (the schema and the engine allow nothing else for a module
 * without maintained documents), so the reference marker travels in the note
 * and `woo` stays absent: this is never a product reference.
 *
 * A tier module is a roof-layout input only. The energy and PVGIS steps read
 * Woo-maintained modules (services/engine/src/linker_engine/planning/
 * product_sources.py rejects any other roof module), so no tier is ever
 * offered as a calculation basis.
 */
export function moduleSpecFromTier(
	tier: PlanningModuleTier,
	id: string,
): ModuleSpec {
	return {
		id,
		model: tier.model,
		width_m: tier.width_m,
		length_m: tier.length_m,
		thickness_m: tier.thickness_m,
		stc_power_w: tier.stc_power_w,
		// The energy model reads the coefficient from the module when no
		// published product supplies one, so a tier must carry its own.
		gamma_pdc_per_c: tier.gamma_pdc_per_c,
		source: {
			kind: "user_declared",
			note: `declared_reference — ${tier.source.source_note}`,
			document_sha256: null,
			url: null,
			page: null,
		},
	};
}
