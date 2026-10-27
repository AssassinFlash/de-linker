import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/brief.schema.json" with { type: "json" };
import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";

export interface Brief extends JsonObject {
	readonly schema_version: 1;
	readonly project_use: "residential" | "commercial" | "industrial" | null;
	readonly system_scope:
		"new_pv_storage" | "storage_addition" | "pv_only" | null;
	readonly site: {
		readonly country_code: string | null;
		readonly location_label: string;
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

const validate = new Ajv2020({
	strict: true,
	strictNumbers: true,
	allErrors: false,
}).compile<Brief>(schema);
export function readBrief(value: unknown): Brief {
	if (!validate(value)) throw new ApiError(422, "invalid_project_brief");
	return value;
}
export function emptyBrief(): Brief {
	return {
		schema_version: 1,
		project_use: null,
		system_scope: null,
		site: {
			country_code: null,
			location_label: "",
			latitude: null,
			longitude: null,
			coordinate_basis: "not_provided",
			timezone: null,
		},
		annual_load: { kwh: null, basis: null, source_note: "" },
		project_note: "",
	};
}
