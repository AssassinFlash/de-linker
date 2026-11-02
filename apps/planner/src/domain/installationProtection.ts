import type { CoreRole } from "./installationElectrical.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { finite, isHash } from "../data/cableReferences.ts";

export interface ProtectionAssessment {
	id: string;
	circuit_id: string;
	protection_material_id: string | null;
	operating_condition_id: string | null;
	scenario: string;
	fault_range: {
		minimum_fault_a: number;
		maximum_fault_a: number;
		source_note: string;
	} | null;
	breaking: {
		capacity_a: number;
		rated_voltage_v: number;
		current_kind: "ac" | "dc";
		source_note: string;
	} | null;
	disconnection: {
		device_worst_case_clear_s: number;
		required_clear_s: number;
		device_source_note: string;
		limit_source_note: string;
	} | null;
	thermal: {
		run_id: string;
		core_role: Exclude<CoreRole, "unused">;
		maximum_let_through_a2s: number;
		coverage_min_fault_a: number;
		coverage_max_fault_a: number;
		maximum_clear_s: number;
		k_a_sqrt_s_per_mm2: number;
		k_source_note: string;
		let_through_source_note: string;
	}[];
	confirmed_context_sha256: string | null;
}

export interface ProtectionComparison {
	status: "not_assessed" | "within_declared_values" | "outside_declared_values";
	measured: number | null;
	maximum: number | null;
	reason: string | null;
}
export interface ProtectionReview {
	assessments: {
		id: string;
		circuit_id: string;
		protection_material_id: string | null;
		scenario: string;
		confirmation_context_sha256: string | null;
		confirmation_status:
			| "confirmed"
			| "context_changed"
			| "confirmation_required"
			| "context_unavailable";
		breaking: ProtectionComparison;
		disconnection: ProtectionComparison;
		thermal: (ProtectionComparison & {
			run_id: string;
			core_role: Exclude<CoreRole, "unused">;
			cross_section_mm2: number | null;
		})[];
	}[];
}

const invalid = (): never => {
	throw new ApiError(502, "invalid_installation_review");
};

function comparison(raw: unknown, confirmed: boolean): ProtectionComparison {
	const row = readObject(raw);
	if (row.status === "not_assessed")
		return {
			status: row.status,
			measured: null,
			maximum: null,
			reason: typeof row.reason === "string" ? row.reason : null,
		};
	if (
		!confirmed ||
		!finite(row.measured) ||
		!finite(row.maximum) ||
		row.status !==
			(row.measured <= row.maximum
				? "within_declared_values"
				: "outside_declared_values")
	)
		return invalid();
	return {
		status: row.status,
		measured: row.measured,
		maximum: row.maximum,
		reason: null,
	};
}

export function readProtectionReview(
	raw: unknown,
	declarations: ProtectionAssessment[] | undefined,
): ProtectionReview | undefined {
	if (declarations === undefined)
		return raw === undefined ? undefined : invalid();
	const result = readObject(raw);
	if (
		result.method !== "installation_protection_evidence_v1" ||
		result.qualified !== false ||
		!Array.isArray(result.assessments) ||
		result.assessments.length !== declarations.length
	)
		return invalid();
	return {
		assessments: result.assessments.map((entry, index) => {
			const row = readObject(entry),
				input = declarations[index]!;
			const hash = row.confirmation_context_sha256;
			if (hash !== null && !isHash(hash)) return invalid();
			const status =
				hash === null
					? "context_unavailable"
					: input.confirmed_context_sha256 === null
						? "confirmation_required"
						: input.confirmed_context_sha256 === hash
							? "confirmed"
							: "context_changed";
			if (
				row.id !== input.id ||
				row.circuit_id !== input.circuit_id ||
				row.scenario !== input.scenario ||
				row.protection_material_id !== input.protection_material_id ||
				row.qualified !== false ||
				row.confirmation_status !== status ||
				!Array.isArray(row.thermal) ||
				row.thermal.length !== input.thermal.length
			)
				return invalid();
			const confirmed = status === "confirmed";
			return {
				id: input.id,
				circuit_id: input.circuit_id,
				scenario: input.scenario,
				protection_material_id: input.protection_material_id,
				confirmation_context_sha256: hash,
				confirmation_status: status,
				breaking: comparison(row.breaking, confirmed),
				disconnection: comparison(row.disconnection, confirmed),
				thermal: row.thermal.map((piece, i) => {
					const core = readObject(piece),
						expected = input.thermal[i]!;
					if (
						core.run_id !== expected.run_id ||
						core.core_role !== expected.core_role
					)
						return invalid();
					return {
						...comparison(core, confirmed),
						run_id: expected.run_id,
						core_role: expected.core_role,
						cross_section_mm2: finite(core.cross_section_mm2)
							? core.cross_section_mm2
							: null,
					};
				}),
			};
		}),
	};
}
