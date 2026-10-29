import type { Json, JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { invalidateEnergyReplay } from "./energyScenario.ts";
import { readSelections } from "./profiles.ts";
import { activePvGeometry } from "./solarSetup.ts";
import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/pvgis-roof-reference.schema.json" with { type: "json" };
import { sameJson } from "./draft.ts";

const ajv = new Ajv2020({ strict: true, strictNumbers: true });
const checkComplete = ajv.compile<JsonObject>(schema);
const checkDraft = ajv.compile<JsonObject>({
	...schema,
	properties: Object.fromEntries(
		Object.entries(schema.properties).map(([key, value]) => [
			key,
			["schema_version", "model", "source_note"].includes(key)
				? value
				: { anyOf: [value, { type: "null" }] },
		]),
	),
});

export const PVGIS_REFERENCE_TASK = "prepare_pvgis_roof_ac_reference_v1";
export const PVGIS_REFERENCE_PURPOSE = "pvgis_roof_ac_reference_profile_v1";
export const REFERENCE_DATABASES = ["PVGIS-ERA5", "PVGIS-SARAH3"] as const;
export const REFERENCE_TECHNOLOGIES = [
	"crystSi",
	"crystSi2025",
	"CIS",
	"CdTe",
] as const;
export interface PvgisReferenceDraft extends JsonObject {
	readonly schema_version: 1;
	readonly model: "pvgis_5_3_roof_ac_reference_v1";
	readonly radiation_database: (typeof REFERENCE_DATABASES)[number] | null;
	readonly year: number | null;
	readonly pv_technology: (typeof REFERENCE_TECHNOLOGIES)[number] | null;
	readonly mounting_place: "free" | "building" | null;
	readonly system_loss_percent: number | null;
	readonly use_terrain_horizon: boolean | null;
	readonly source_note: string | null;
}
export function emptyPvgisReference(): PvgisReferenceDraft {
	return {
		schema_version: 1,
		model: "pvgis_5_3_roof_ac_reference_v1",
		radiation_database: null,
		year: null,
		pv_technology: null,
		mounting_place: null,
		system_loss_percent: null,
		use_terrain_horizon: null,
		source_note: null,
	};
}
export function readPvgisReference(value: unknown): PvgisReferenceDraft {
	const row = readObject(value);
	if (!checkDraft(row)) throw new ApiError(422, "pvgis_reference_invalid");
	return {
		...row,
		source_note:
			typeof row.source_note === "string" && row.source_note.trim()
				? row.source_note
				: null,
	} as PvgisReferenceDraft;
}
export function referenceDraft(inputs: JsonObject): PvgisReferenceDraft {
	const value = inputs.pvgis_reference_setup ?? inputs.pvgis_reference;
	return value === undefined
		? emptyPvgisReference()
		: readPvgisReference(value);
}
export function compilePvgisReference(value: PvgisReferenceDraft): JsonObject {
	if (!checkComplete(value))
		throw new ApiError(422, "pvgis_reference_incomplete");
	return value;
}
export function referencePrepared(inputs: JsonObject): boolean {
	try {
		return sameJson(
			compilePvgisReference(referenceDraft(inputs)),
			readPvgisReference(inputs.pvgis_reference),
		);
	} catch {
		return false;
	}
}
export function assertReferenceAcTopology(inputs: JsonObject): void {
	const single = readObject(
		inputs.energy_scenario ?? inputs.energy_replay ?? {},
	);
	const plant = readObject(
		inputs.energy_plant_setup ?? inputs.energy_plant ?? {},
	);
	// A shared DC plant, or a retained PV group, already accounts for this roof.
	// Unit assignment is not required: the coupling or pv_reference is enough.
	if (
		single.coupling === "shared_dc" ||
		plant.coupling === "plant_shared_dc" ||
		readSelections(inputs.profile_selections).selected.pv_reference !==
			undefined
	)
		throw new ApiError(422, "pvgis_reference_dc_conflict");
}
export function referenceRoof(inputs: JsonObject) {
	const layout = activePvGeometry(inputs.geometry),
		anchor = layout.geometry.coordinate_system.anchor;
	if (
		!anchor ||
		layout.geometry.coordinate_system.north_reference === "unreferenced" ||
		!layout.arrays.length ||
		layout.arrays.some(
			(a) =>
				!layout.geometry.module_specs.find((m) => m.id === a.module_spec_id)
					?.source.woo,
		)
	)
		throw new ApiError(422, "pvgis_reference_roof_required");
	return layout;
}
export function referenceInputs(
	inputs: JsonObject,
	value: PvgisReferenceDraft,
): JsonObject {
	const next: Record<string, Json> = {
		...invalidateEnergyReplay(inputs),
		pvgis_reference_setup: value,
	};
	try {
		next.pvgis_reference = compilePvgisReference(value);
	} catch {
		delete next.pvgis_reference;
	}
	return next;
}
