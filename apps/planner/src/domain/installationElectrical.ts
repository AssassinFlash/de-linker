import { ApiError } from "../data/protocol.ts";
import type { JsonObject } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import {
	finite,
	isHash,
	isText,
	readCableEvidence,
} from "../data/cableReferences.ts";
import type { CableEvidence } from "../data/cableReferences.ts";
import { sameJson } from "./draft.ts";
import type { InstallationInputs, CableQuantity } from "./installation.ts";
import { readReferenceCurrentSegments } from "./installationReferenceCurrent.ts";
import type { ReferenceCurrentSegment } from "./installationReferenceCurrent.ts";

export type CoreRole =
	| "dc_positive"
	| "dc_negative"
	| "line"
	| "neutral"
	| "l1"
	| "l2"
	| "l3"
	| "pe"
	| "unused";
export interface CircuitOperatingCondition extends JsonObject {
	id: string;
	name: string;
	method: "dc_resistive" | "ac_two_wire" | "ac_balanced_three_phase";
	current_a: number;
	reference_voltage_v: number;
	direction: "start_to_end" | "end_to_start";
	conductor_temperature_c: number;
	frequency_hz: number | null;
	power_factor: number | null;
	reactive_direction: "lagging" | "leading" | null;
	balanced: boolean | null;
	sinusoidal: boolean;
	arrangement: string | null;
	source_note: string;
	voltage_limit: { maximum_percent: number; source_note: string } | null;
}
export const electricalReasons = [
	"dc_condition_not_applicable",
	"ac_condition_not_applicable",
	"cable_runs_missing",
	"core_roles_missing",
	"core_roles_not_applicable",
	"cable_reference_unavailable",
	"cable_specification_mismatch",
	"cable_conditions_mismatch",
	"cable_parameter_set_ambiguous",
	"route_quantity_unconfirmed",
	"numerical_range_not_supported",
	"parallel_or_branched_cores_not_supported",
	"current_path_incomplete",
	"phase_impedances_not_equal",
] as const;
export interface ElectricalSegment extends JsonObject {
	run_id: string;
	role: CoreRole;
	length_m: number;
	product_id: number;
	product_revision: string;
	reference_input_id: string;
	parameter_set_id: string;
	resistance_basis: "maximum" | "nominal";
	resistance_ohm: number;
	reactance_ohm: number | null;
	source: CableEvidence;
}
export interface ElectricalConditionReview {
	condition_id: string;
	name: string;
	condition: CircuitOperatingCondition;
	status: "calculated" | "data_insufficient" | "method_not_applicable";
	reasons: string[];
	segments: ElectricalSegment[];
	resistance_basis: "maximum" | "nominal" | "mixed" | null;
	value_basis:
		| "resistance_upper_bound"
		| "nominal_parameters"
		| "mixed_resistance_parameters"
		| null;
	loop_resistance_ohm: number | null;
	loop_reactance_ohm: number | null;
	voltage_drop_v: number | null;
	voltage_drop_percent: number | null;
	end_minus_start_voltage_v: number | null;
	conductor_loss_w: number | null;
	limit: {
		reason?: "resistance_upper_bound_not_absolute_drop_bound";
		status:
			| "not_evaluated"
			| "not_declared"
			| "within_declared_limit"
			| "exceeds_declared_limit";
		declared: CircuitOperatingCondition["voltage_limit"];
	};
	scope: "conductor_segments_only";
	qualified: false;
}
export interface ElectricalReview {
	schema_version: 1;
	method: "installation_circuit_steady_conductors_v1";
	qualified: false;
	reference_current_segments?: ReferenceCurrentSegment[];
	circuits: {
		circuit_id: string;
		name: string;
		status: "not_recorded" | "reviewed";
		conditions: ElectricalConditionReview[];
	}[];
}
const fail = (): never => {
	throw new ApiError(502, "invalid_installation_review");
};
export function readElectricalReview(
	value: unknown,
	plan: InstallationInputs,
	cables: CableQuantity[],
): ElectricalReview | undefined {
	const opted =
		plan.circuits.some((c) => c.operating_conditions !== undefined) ||
		plan.cable_runs.some(
			(r) =>
				r.core_roles !== undefined ||
				r.conductor?.cable_reference != null ||
				r.reference_current_installation != null,
		);
	if (!opted) {
		if (value !== undefined) fail();
		return undefined;
	}
	const reply = readObject(value);
	if (
		reply.schema_version !== 1 ||
		reply.method !== "installation_circuit_steady_conductors_v1" ||
		reply.qualified !== false ||
		!Array.isArray(reply.circuits) ||
		reply.circuits.length !== plan.circuits.length
	)
		fail();
	for (const [i, raw] of (reply.circuits as unknown[]).entries()) {
		const c = readObject(raw),
			input = plan.circuits[i]!,
			conditions = input.operating_conditions ?? [];
		if (
			c.circuit_id !== input.id ||
			c.name !== input.name ||
			c.status !== (conditions.length ? "reviewed" : "not_recorded") ||
			!Array.isArray(c.conditions) ||
			c.conditions.length !== conditions.length
		)
			fail();
		for (const [j, rawCondition] of (c.conditions as unknown[]).entries()) {
			const r = readObject(rawCondition),
				condition = conditions[j]!;
			if (
				r.condition_id !== condition.id ||
				r.name !== condition.name ||
				!sameJson(r.condition, condition) ||
				r.scope !== "conductor_segments_only" ||
				r.qualified !== false ||
				!["calculated", "data_insufficient", "method_not_applicable"].includes(
					String(r.status),
				) ||
				!Array.isArray(r.reasons) ||
				r.reasons.some(
					(s) =>
						!electricalReasons.includes(
							s as (typeof electricalReasons)[number],
						),
				) ||
				new Set(r.reasons).size !== r.reasons.length ||
				!Array.isArray(r.segments) ||
				(r.status === "calculated") !== (r.reasons.length === 0)
			)
				fail();
			const segments = r.segments as unknown[];
			const seen = new Set<string>();
			for (const rawSegment of segments) {
				const s = readObject(rawSegment),
					run = plan.cable_runs.find(
						(run) => run.id === s.run_id && run.circuit_id === input.id,
					),
					quantity = cables.find((c) => c.id === s.run_id)?.quantity;
				if (
					!run ||
					!isText(s.role) ||
					!run.core_roles?.includes(s.role as CoreRole) ||
					["pe", "unused"].includes(s.role) ||
					seen.has(String(s.run_id) + ":" + s.role) ||
					!finite(s.length_m) ||
					s.length_m <= 0 ||
					s.length_m !== quantity ||
					!sameJson(run.conductor?.cable_reference, {
						product_id: s.product_id,
						product_revision: s.product_revision,
					}) ||
					!isHash(s.product_revision) ||
					!isText(s.reference_input_id) ||
					!isText(s.parameter_set_id) ||
					!["maximum", "nominal"].includes(String(s.resistance_basis)) ||
					!finite(s.resistance_ohm) ||
					s.resistance_ohm <= 0 ||
					!(
						s.reactance_ohm === null ||
						(finite(s.reactance_ohm) && s.reactance_ohm >= 0)
					) ||
					(condition.method === "dc_resistive"
						? s.reactance_ohm !== null
						: s.reactance_ohm === null)
				)
					fail();
				readCableEvidence(s.source, s.product_id as number);
				seen.add(String(s.run_id) + ":" + s.role);
			}
			const bases = new Set(
					segments.map((s) => readObject(s).resistance_basis),
				),
				basis = bases.size > 1 ? "mixed" : bases.size ? [...bases][0] : null;
			if (
				r.resistance_basis !== basis ||
				r.value_basis !==
					(basis === "maximum"
						? "resistance_upper_bound"
						: basis === "nominal"
							? "nominal_parameters"
							: basis === "mixed"
								? "mixed_resistance_parameters"
								: null)
			)
				fail();
			for (const key of [
				"loop_resistance_ohm",
				"loop_reactance_ohm",
				"voltage_drop_v",
				"voltage_drop_percent",
				"end_minus_start_voltage_v",
				"conductor_loss_w",
			]) {
				const n = r[key],
					needs =
						r.status === "calculated" &&
						!(
							key === "loop_reactance_ohm" &&
							condition.method === "dc_resistive"
						);
				if (needs ? !finite(n) : n !== null) fail();
			}
			if (r.status === "calculated") {
				const typedSegments = segments.map((s) => readObject(s));
				const roles = typedSegments.map((s) => s.role);
				const required =
					condition.method === "dc_resistive"
						? ["dc_positive", "dc_negative"]
						: condition.method === "ac_balanced_three_phase"
							? ["l1", "l2", "l3"]
							: roles.includes("line") || roles.includes("neutral")
								? ["line", "neutral"]
								: ["l1", "l2"];
				if (
					roles.length !== required.length ||
					required.some((role) => roles.filter((r) => r === role).length !== 1)
				)
					fail();
				const expectedPairs = plan.cable_runs
					.filter((run) => run.circuit_id === input.id)
					.flatMap((run) =>
						(run.core_roles ?? [])
							.filter(
								(role) =>
									role !== "pe" &&
									role !== "unused" &&
									!(
										condition.method === "ac_balanced_three_phase" &&
										condition.balanced === true &&
										condition.sinusoidal &&
										role === "neutral"
									),
							)
							.map((role) => run.id + ":" + role),
					);
				if (
					expectedPairs.length !== seen.size ||
					expectedPairs.some((pair) => !seen.has(pair))
				)
					fail();
				const drop = r.voltage_drop_v as number;
				if (
					(r.loop_resistance_ohm as number) < 0 ||
					(r.conductor_loss_w as number) < 0 ||
					r.voltage_drop_percent !==
						(100 * drop) / condition.reference_voltage_v ||
					r.end_minus_start_voltage_v !==
						(condition.direction === "start_to_end" ? -drop : drop)
				)
					fail();
			}
			const limit = readObject(r.limit),
				status =
					r.status !== "calculated"
						? "not_evaluated"
						: condition.voltage_limit === null
							? "not_declared"
							: Math.abs(r.voltage_drop_percent as number) <=
								  condition.voltage_limit.maximum_percent
								? "within_declared_limit"
								: "exceeds_declared_limit";
			const upperBoundNotAbsolute =
				r.status === "calculated" &&
				condition.voltage_limit !== null &&
				condition.method !== "dc_resistive" &&
				condition.reactive_direction === "leading" &&
				condition.power_factor !== null &&
				condition.power_factor > 0 &&
				condition.power_factor < 1 &&
				condition.current_a > 0 &&
				(r.loop_reactance_ohm as number) > 0 &&
				segments.some((s) => readObject(s).resistance_basis === "maximum");
			if (
				limit.status !== (upperBoundNotAbsolute ? "not_evaluated" : status) ||
				limit.reason !==
					(upperBoundNotAbsolute
						? "resistance_upper_bound_not_absolute_drop_bound"
						: undefined) ||
				!sameJson(limit.declared, condition.voltage_limit)
			)
				fail();
		}
	}
	readReferenceCurrentSegments(reply.reference_current_segments, plan);
	return reply as unknown as ElectricalReview;
}
