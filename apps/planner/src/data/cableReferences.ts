import type { JsonObject } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { documentReference } from "./documentReference.ts";

export interface CableEvidence extends JsonObject {
	document_id: string;
	document_revision: string;
	blob_sha256: string;
	product_id: number;
	url: string;
	page: number;
	quote: string;
}
export interface CableParameterSet extends JsonObject {
	id: string;
	current_kind: "dc" | "ac";
	temperature_c: number;
	frequency_hz: number | null;
	arrangement: string | null;
	resistance_ohm_per_km: number;
	reactance_ohm_per_km: number | null;
	resistance_basis: "maximum" | "nominal";
	source: CableEvidence;
}
export interface CableReferenceCurrentRating extends JsonObject {
	id: string;
	laying: "single_in_air" | "single_on_surface" | "two_touching_on_surface";
	ambient_temperature_c: number;
	rated_conductor_temperature_c: number;
	current_a: number;
	source: CableEvidence;
}
export interface CableReference extends JsonObject {
	id: string;
	canonical_product_id: number;
	product_revision: string;
	brand: string;
	model: string;
	kind: "cable";
	cable_facts: JsonObject & {
		schema_version: 1;
		construction: "single_conductor" | "multicore_cable";
		core_count: number;
		cross_section_mm2: number;
		conductor_material: string;
		insulation: string;
		source: CableEvidence;
		parameter_sets: CableParameterSet[];
		reference_current_ratings?: CableReferenceCurrentRating[];
	};
}
export const isHash = (v: unknown): v is string =>
	typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
export const isText = (v: unknown): v is string =>
	typeof v === "string" && !!v.trim();
export const finite = (v: unknown): v is number =>
	typeof v === "number" && Number.isFinite(v);
const positive = (v: unknown): v is number => finite(v) && v > 0;
const count = (v: unknown): v is number =>
	positive(v) && Number.isSafeInteger(v);
const fail = (): never => {
	throw new ApiError(502, "invalid_cable_reference");
};
export function readCableEvidence(
	value: unknown,
	productId?: number,
): CableEvidence {
	const r = readObject(value);
	documentReference(r, true);
	if (
		!isText(r.document_id) ||
		!isHash(r.document_revision) ||
		!isHash(r.blob_sha256) ||
		!count(r.product_id) ||
		(productId !== undefined && r.product_id !== productId) ||
		!isText(r.quote) ||
		!String(r.url).startsWith("https://de-linker.com/wp-content/uploads/")
	)
		fail();
	return r as CableEvidence;
}
export function readCableReferences(value: unknown): CableReference[] {
	if (value === undefined) return [];
	if (!Array.isArray(value)) return fail();
	const rows = value.map((raw) => {
		const r = readObject(raw),
			f = readObject(r.cable_facts);
		if (
			r.kind !== "cable" ||
			!isText(r.id) ||
			!count(r.canonical_product_id) ||
			!isHash(r.product_revision) ||
			r.reference_revision !== r.product_revision ||
			typeof r.brand !== "string" ||
			typeof r.model !== "string" ||
			f.schema_version !== 1 ||
			!["single_conductor", "multicore_cable"].includes(
				String(f.construction),
			) ||
			!count(f.core_count) ||
			(f.construction === "single_conductor" && f.core_count !== 1) ||
			!positive(f.cross_section_mm2) ||
			!isText(f.conductor_material) ||
			!isText(f.insulation) ||
			!Array.isArray(f.parameter_sets) ||
			!Array.isArray(r.documents)
		)
			fail();
		const source = readCableEvidence(
			f.source,
			r.canonical_product_id as number,
		);
		const docs = r.documents as unknown[];
		const checkSource = (s: CableEvidence) => {
			if (
				!docs.some((raw) => {
					const d = readObject(raw);
					return (
						d.document_id === s.document_id &&
						d.document_revision === s.document_revision &&
						d.blob_sha256 === s.blob_sha256 &&
						d.url === s.url &&
						Array.isArray(d.product_ids) &&
						d.product_ids.includes(s.product_id)
					);
				})
			)
				fail();
		};
		checkSource(source);
		const ids = new Set<string>();
		for (const raw of f.parameter_sets as unknown[]) {
			const p = readObject(raw);
			if (
				!isText(p.id) ||
				ids.has(p.id) ||
				!["dc", "ac"].includes(String(p.current_kind)) ||
				!finite(p.temperature_c) ||
				!positive(p.resistance_ohm_per_km) ||
				!["maximum", "nominal"].includes(String(p.resistance_basis)) ||
				!(p.arrangement === null || isText(p.arrangement)) ||
				(p.current_kind === "dc"
					? p.frequency_hz !== null || p.reactance_ohm_per_km !== null
					: !positive(p.frequency_hz) ||
						!finite(p.reactance_ohm_per_km) ||
						p.reactance_ohm_per_km < 0 ||
						!isText(p.arrangement))
			)
				fail();
			ids.add(p.id as string);
			checkSource(
				readCableEvidence(p.source, r.canonical_product_id as number),
			);
		}
		if (f.reference_current_ratings !== undefined) {
			if (
				!Array.isArray(f.reference_current_ratings) ||
				(f.reference_current_ratings.length > 0 &&
					f.construction !== "single_conductor")
			)
				fail();
			const ratingIds = new Set<string>();
			for (const raw of f.reference_current_ratings as unknown[]) {
				const rating = readObject(raw);
				if (
					typeof rating.id !== "string" ||
					!/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(rating.id) ||
					ratingIds.has(rating.id) ||
					![
						"single_in_air",
						"single_on_surface",
						"two_touching_on_surface",
					].includes(String(rating.laying)) ||
					!finite(rating.ambient_temperature_c) ||
					!finite(rating.rated_conductor_temperature_c) ||
					!positive(rating.current_a)
				)
					fail();
				ratingIds.add(rating.id as string);
				checkSource(
					readCableEvidence(rating.source, r.canonical_product_id as number),
				);
			}
		}
		return r as CableReference;
	});
	if (
		new Set(rows.map((r) => r.canonical_product_id)).size !== rows.length ||
		new Set(rows.map((r) => r.id)).size !== rows.length
	)
		fail();
	return rows;
}
