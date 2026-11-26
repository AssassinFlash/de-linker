import { validate2020 } from "../data/schemaValidator.ts";
import schema from "../contracts/brief.schema.json" with { type: "json" };
import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";

export interface Brief extends JsonObject {
	readonly schema_version: 1;
	readonly project_use: "residential" | "commercial" | "industrial" | null;
	readonly system_scope:
		"new_pv_storage" | "storage_addition" | "storage_only" | "pv_only" | null;
	readonly site: {
		readonly country_code: string | null;
		readonly location_label: string;
		readonly postal_code?: string | null;
		readonly latitude: number | null;
		readonly longitude: number | null;
		readonly coordinate_basis: "user_entered" | "not_provided";
		readonly timezone: string | null;
	};
	readonly annual_load: {
		readonly kwh: number | null;
		readonly basis: "bill_total" | "user_estimate" | null;
		readonly source_note: string;
	};
	readonly project_note: string;
}

const validate = validate2020<Brief>(schema);
export function readBrief(value: unknown): Brief {
	if (value === blankBrief) return blankBrief;
	if (!validate(value)) throw new ApiError(422, "invalid_project_brief");
	return value;
}
/** The public intake can display the empty native shape before any external input needs validation. */
export const blankBrief: Brief = Object.freeze({
	schema_version: 1,
	project_use: null,
	system_scope: null,
	site: Object.freeze({
		country_code: null,
		location_label: "",
		latitude: null,
		longitude: null,
		coordinate_basis: "not_provided",
		timezone: null,
	}),
	annual_load: Object.freeze({ kwh: null, basis: null, source_note: "" }),
	project_note: "",
});
export function emptyBrief(): Brief {
	return {
		...blankBrief,
		site: { ...blankBrief.site },
		annual_load: { ...blankBrief.annual_load },
	};
}
