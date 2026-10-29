import type { Json, JsonObject } from "../data/protocol.ts";
import { emptyBrief } from "./brief.ts";
import { equipmentDraft } from "./equipment.ts";

export const ENTRY_QUERY_KEYS = [
	"pv_kwp",
	"annual_kwh",
	"phase",
	"backup",
	"plz",
	"step",
	"product_id",
	"saved_solution",
] as const;
export type ProductEntryField = "inverter" | "battery" | "accessory";
export interface EntryHints {
	pvKw: number | null;
	annualKwh: number | null;
	phase: 1 | 3 | null;
	backup: "none" | "needed" | "needed_accessory_ok" | null;
	postalCode: string | null;
	roof: boolean;
	equipment: boolean;
	productId: number | null;
	invalid: boolean;
}

/** Public link values are proposals for a new project, never saved results. */
export function readEntryHints(params: URLSearchParams): EntryHints | null {
	if (
		params.has("project") ||
		params.has("saved_solution") ||
		!ENTRY_QUERY_KEYS.some((key) => params.has(key))
	)
		return null;
	let invalid = false;
	const one = (key: string): string | null => {
		const values = params.getAll(key);
		if (values.length > 1) invalid = true;
		return values.length === 1 ? values[0]! : null;
	};
	const positive = (key: string): number | null => {
		const raw = one(key);
		if (raw === null) return null;
		const value = Number(raw);
		if (
			!/^\d+(?:\.\d+)?$/.test(raw) ||
			!Number.isFinite(value) ||
			value <= 0 ||
			value > Number.MAX_SAFE_INTEGER
		) {
			invalid = true;
			return null;
		}
		return value;
	};
	const pvKw = positive("pv_kwp"),
		annualKwh = positive("annual_kwh");
	const phaseValue = one("phase"),
		backupValue = one("backup"),
		postal = one("plz"),
		step = one("step"),
		productRaw = one("product_id");
	const phase = phaseValue === "1" ? 1 : phaseValue === "3" ? 3 : null;
	const backup =
		backupValue === "none" ||
		backupValue === "needed" ||
		backupValue === "needed_accessory_ok"
			? backupValue
			: null;
	const postalCode = postal !== null && /^\d{5}$/.test(postal) ? postal : null;
	const productId =
		productRaw !== null &&
		/^[1-9]\d*$/.test(productRaw) &&
		Number.isSafeInteger(Number(productRaw))
			? Number(productRaw)
			: null;
	const equipment = step === "equipment";
	if (
		(phaseValue !== null && phase === null) ||
		(backupValue !== null && backup === null) ||
		(postal !== null && postalCode === null) ||
		(step !== null && step !== "roof" && step !== "equipment") ||
		(step === "equipment" && productId === null) ||
		(productRaw !== null && (productId === null || step !== "equipment"))
	)
		invalid = true;
	return {
		pvKw,
		annualKwh,
		phase,
		backup,
		postalCode,
		roof: step === "roof",
		equipment: step === "equipment" && productId !== null,
		productId: equipment ? productId : null,
		invalid,
	};
}

/**
 * The catalogue already splits converters, batteries and additional products.
 * Device class chooses the field. An unknown class is not treated as an inverter.
 */
export function productEntryField(product: {
	device_class: string;
	figures: JsonObject;
}): ProductEntryField | null {
	if (
		product.device_class === "home-storage" ||
		product.device_class === "battery-systems"
	)
		return "battery";
	if (product.device_class === "inverters") return "inverter";
	if (
		product.device_class === "all-in-one-systems" &&
		Object.hasOwn(product.figures, "ac_output_kw_nominal")
	)
		return "inverter";
	if (
		product.device_class === "accessories" ||
		product.device_class === "ems-monitoring" ||
		product.device_class === "ev-chargers"
	)
		return "accessory";
	return null;
}

export function placedProduct<
	T extends { id: number; device_class: string; figures: JsonObject },
>(
	products: readonly T[],
	productId: number,
): { id: number; field: ProductEntryField } | null {
	const product = products.find((item) => item.id === productId);
	const field = product ? productEntryField(product) : null;
	return product && field ? { id: product.id, field } : null;
}

export function entryInputs(
	hints: EntryHints,
	sourceNote: string,
	accessoryNote: string,
	product: { id: number; field: ProductEntryField } | null = null,
): JsonObject {
	const brief = emptyBrief();
	const inputs: Record<string, Json> = {
		brief: {
			...brief,
			site: { ...brief.site, location_label: hints.postalCode ?? "" },
			annual_load: {
				kwh: hints.annualKwh,
				basis: hints.annualKwh === null ? null : "user_estimate",
				source_note: hints.annualKwh === null ? "" : sourceNote,
			},
			project_note: hints.backup === "needed_accessory_ok" ? accessoryNote : "",
		},
	};
	if (
		hints.pvKw !== null ||
		hints.phase !== null ||
		hints.backup !== null ||
		product !== null
	) {
		const setup: Record<string, Json> = {
			...equipmentDraft({}),
			pv_dc_kw: hints.pvKw,
			grid_phase: hints.phase,
			operating_mode:
				hints.backup === null
					? null
					: hints.backup === "none"
						? "grid_connected"
						: "backup",
		};
		if (product?.field === "inverter") setup.inverter_product_id = product.id;
		if (product?.field === "battery") setup.battery_product_id = product.id;
		if (product?.field === "accessory")
			setup.accessory_product_ids = [product.id];
		inputs.equipment_setup = setup;
	}
	return inputs;
}
