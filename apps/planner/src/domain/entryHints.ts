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
	"saved_solution",
] as const;
export interface EntryHints {
	pvKw: number | null;
	annualKwh: number | null;
	phase: 1 | 3 | null;
	backup: "none" | "needed" | "needed_accessory_ok" | null;
	postalCode: string | null;
	roof: boolean;
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
		step = one("step");
	const phase = phaseValue === "1" ? 1 : phaseValue === "3" ? 3 : null;
	const backup =
		backupValue === "none" ||
		backupValue === "needed" ||
		backupValue === "needed_accessory_ok"
			? backupValue
			: null;
	const postalCode = postal !== null && /^\d{5}$/.test(postal) ? postal : null;
	if (
		(phaseValue !== null && phase === null) ||
		(backupValue !== null && backup === null) ||
		(postal !== null && postalCode === null) ||
		(step !== null && step !== "roof")
	)
		invalid = true;
	return {
		pvKw,
		annualKwh,
		phase,
		backup,
		postalCode,
		roof: step === "roof",
		invalid,
	};
}

export function entryInputs(
	hints: EntryHints,
	sourceNote: string,
	accessoryNote: string,
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
	if (hints.pvKw !== null || hints.phase !== null || hints.backup !== null)
		inputs.equipment_setup = {
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
	return inputs;
}
