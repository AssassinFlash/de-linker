import type { ModuleSpec, PanelElectrical } from "./geometry.ts";

export interface PanelFields {
	length: string;
	width: string;
	thickness: string;
	power: string;
	coefficient: string;
	electrical?: Partial<Record<keyof PanelElectrical, string>>;
}

export function emptyPanelFields(): PanelFields {
	return { length: "", width: "", thickness: "", power: "", coefficient: "" };
}
export function panelFields(spec: ModuleSpec): PanelFields {
	return {
		length: String(spec.length_m * 1000),
		width: String(spec.width_m * 1000),
		thickness: String(spec.thickness_m * 1000),
		power: String(spec.stc_power_w),
		electrical: Object.fromEntries(
			Object.entries(spec.electrical ?? {})
				.filter(([, value]) => value != null)
				.map(([key, value]) => [key, String(value)]),
		),
		coefficient:
			spec.gamma_pdc_per_c == null ? "" : String(spec.gamma_pdc_per_c * 100),
	};
}
export function panelLabel(
	spec: Pick<ModuleSpec, "stc_power_w" | "length_m" | "width_m">,
	locale = "en",
): string {
	const format = new Intl.NumberFormat(locale, {
		useGrouping: false,
		maximumFractionDigits: 3,
	});
	return `${format.format(spec.stc_power_w)} Wp · ${format.format(spec.length_m * 1000)} × ${format.format(spec.width_m * 1000)} mm`;
}

export function panelSpecification(
	id: string,
	fields: PanelFields,
): ModuleSpec | null {
	const length = Number(fields.length),
		width = Number(fields.width),
		thickness = Number(fields.thickness),
		power = Number(fields.power);
	if (
		![length, width, thickness, power].every((n) => Number.isFinite(n) && n > 0)
	)
		return null;
	const gamma = fields.coefficient.trim()
		? Number(fields.coefficient) / 100
		: null;
	if (gamma !== null && !(gamma < 0 && gamma > -1)) return null;
	const values = {
		width_m: width / 1000,
		length_m: length / 1000,
		thickness_m: thickness / 1000,
		stc_power_w: power,
	};
	const electrical: PanelElectrical = {};
	for (const key of [
		"voc_v",
		"vmpp_v",
		"isc_a",
		"impp_a",
		"max_system_voltage_v",
		"alpha_isc_pct_per_c",
		"beta_voc_pct_per_c",
	] as const) {
		const entered = fields.electrical?.[key]?.trim();
		if (!entered) continue;
		const value = Number(entered);
		if (!Number.isFinite(value) || (!key.endsWith("_pct_per_c") && value <= 0))
			return null;
		electrical[key] = value;
	}
	const technology = fields.electrical?.cell_technology?.trim();
	if (technology) electrical.cell_technology = technology;
	return {
		id,
		...values,
		...(Object.keys(electrical).length ? { electrical } : {}),
		model: "PV " + panelLabel(values),
		gamma_pdc_per_c: gamma,
		source: {
			kind: "user_declared",
			note: "declared_reference — Customer-provided panel parameters.",
			document_sha256: null,
			url: null,
			page: null,
		},
	};
}
