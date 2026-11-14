import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";

/**
 * What the server resolved a declared place to. `found: false` is an answer,
 * not an error: an unknown postcode leaves the visitor's own text as typed.
 */
export interface ResolvedPlace extends JsonObject {
	readonly schema_version: 1;
	readonly found: boolean;
	readonly query: string;
	readonly country_code?: string;
	readonly location_label?: string;
	readonly latitude?: number;
	readonly longitude?: number;
	readonly region?: string;
	readonly timezone?: string;
	readonly attribution?: string;
}

export function readResolvedPlace(value: unknown): ResolvedPlace {
	const data = readObject(value);
	if (data.schema_version !== 1 || typeof data.found !== "boolean")
		throw new ApiError(502, "invalid_place_reply");
	if (typeof data.query !== "string")
		throw new ApiError(502, "invalid_place_reply");
	if (!data.found) return data as ResolvedPlace;
	if (
		typeof data.country_code !== "string" ||
		!/^[A-Z]{2}$/.test(data.country_code) ||
		typeof data.location_label !== "string" ||
		typeof data.latitude !== "number" ||
		typeof data.longitude !== "number" ||
		typeof data.timezone !== "string"
	)
		throw new ApiError(502, "invalid_place_reply");
	return data as ResolvedPlace;
}
