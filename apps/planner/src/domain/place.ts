import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";

/**
 * What the server resolved a declared place to. `found: false` is an answer,
 * not an error: an unknown postcode leaves the visitor's own text as typed.
 * `needs_country` distinguishes "nowhere" from "several countries write this
 * postcode the same way", which is answered by naming the country rather than
 * by correcting the postcode.
 */
export interface ResolvedPlace extends JsonObject {
	readonly schema_version: 1;
	readonly found: boolean;
	readonly query: string;
	readonly needs_country?: boolean;
	readonly country_code?: string;
	readonly location_label?: string;
	readonly latitude?: number;
	readonly longitude?: number;
	readonly region?: string;
	readonly timezone?: string;
	readonly attribution?: string;
	/** The official aerial layer for this place, or null where none exists. */
	readonly imagery?: PlaceImagery | null;
}

/** A WMS mosaic the map draws under the project geometry. */
export interface PlaceImagery extends JsonObject {
	readonly tiles: readonly string[];
	readonly credit: string;
	readonly licence: string;
	readonly licence_url: string;
}

export function imagerySourceKey(mosaic: PlaceImagery): string {
	return JSON.stringify([
		mosaic.tiles,
		mosaic.credit,
		mosaic.licence,
		mosaic.licence_url,
	]);
}

export function readPlaceImagery(value: unknown): PlaceImagery | null {
	if (value === null || value === undefined) return null;
	const data = readObject(value);
	if (!Array.isArray(data.tiles) || data.tiles.length === 0)
		throw new ApiError(502, "invalid_place_reply");
	if (
		typeof data.credit !== "string" ||
		typeof data.licence !== "string" ||
		typeof data.licence_url !== "string"
	)
		throw new ApiError(502, "invalid_place_reply");
	const tiles = data.tiles.filter(
		(tile): tile is string => typeof tile === "string" && tile.length > 0,
	);
	if (tiles.length !== data.tiles.length)
		throw new ApiError(502, "invalid_place_reply");
	return { ...data, tiles } as unknown as PlaceImagery;
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
	return { ...data, imagery: readPlaceImagery(data.imagery) } as ResolvedPlace;
}
