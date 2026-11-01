import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import {
	finite,
	isHash,
	isText,
	readCableEvidence,
} from "../data/cableReferences.ts";
import type { CableReferenceCurrentRating } from "../data/cableReferences.ts";
import { sameJson } from "./draft.ts";
import type {
	CableRun,
	Endpoint,
	InstallationInputs,
	ReferenceCurrentContext,
	ReferenceCurrentEndpoint,
	ReferenceCurrentInstallation,
	ReferenceCurrentPhysical,
} from "./installation.ts";
import type { CoreRole } from "./installationElectrical.ts";

export const referenceCurrentReasons = [
	"operating_condition_missing",
	"circuit_kind_not_supported",
	"condition_method_not_supported",
	"current_path_not_single_pair",
	"current_path_not_confirmed",
	"installation_conditions_not_confirmed",
	"confirmation_context_changed",
	"touching_pair_mismatch",
	"cable_reference_unavailable",
	"cable_specification_mismatch",
	"reference_rating_unavailable",
	"reference_rating_conditions_mismatch",
	"reference_source_unavailable",
] as const;

export interface ReferenceCurrentSegment {
	circuit_id: string;
	condition_id: string | null;
	run_id: string;
	role: CoreRole | null;
	status:
		"not_evaluated" | "below_reference" | "equal_reference" | "above_reference";
	reasons: (typeof referenceCurrentReasons)[number][];
	project_current_a: number | null;
	reference_current_a: number | null;
	installation: ReferenceCurrentInstallation;
	rating: CableReferenceCurrentRating | null;
	product_id: number | null;
	product_revision: string | null;
	reference_input_id: string | null;
	scope: "single_conductor_reference_only";
	qualified: false;
}

const fail = (): never => {
	throw new ApiError(502, "invalid_installation_review");
};

/** Snapshot the actual stated physical conditions only after an explicit confirmation. */
export function referenceCurrentContext(
	plan: InstallationInputs,
	run: CableRun,
	declaration: ReferenceCurrentInstallation,
): ReferenceCurrentContext {
	const endpoint = (value: Endpoint): ReferenceCurrentEndpoint => {
		const instance = plan.instances.find(
				(item) => item.id === value.instance_id,
			),
			port = instance?.ports.find((item) => item.id === value.port_id);
		if (!instance || !port)
			throw new Error("reference_current_endpoint_missing");
		return {
			instance_id: instance.id,
			port_id: port.id,
			product_id: instance.product_id,
			product_revision: instance.product_revision,
			position: { ...port.position },
		};
	};
	const physical = (item: CableRun): ReferenceCurrentPhysical => {
		const circuit = plan.circuits.find((row) => row.id === item.circuit_id),
			route = plan.routes.find((row) => row.id === item.route_id);
		if (!circuit || !route)
			throw new Error("reference_current_route_or_circuit_missing");
		return {
			id: item.id,
			construction: item.construction,
			core_roles: [...(item.core_roles ?? [])],
			cross_section_mm2: item.conductor?.cross_section_mm2 ?? null,
			cable_reference: item.conductor?.cable_reference
				? { ...item.conductor.cable_reference }
				: null,
			route: {
				id: route.id,
				points: route.points.map((point) => ({ ...point })),
				extra_length_m: route.extra_length_m,
			},
			circuit: {
				id: circuit.id,
				kind: circuit.kind,
				start: endpoint(circuit.start),
				end: endpoint(circuit.end),
			},
		};
	};
	const touching = plan.cable_runs.find(
		(item) => item.id === declaration.touching_run_id,
	);
	return {
		declaration: {
			rating_id: declaration.rating_id,
			laying: declaration.laying,
			ambient_temperature_c: declaration.ambient_temperature_c,
			touching_run_id: declaration.touching_run_id,
			current_path: declaration.current_path,
		},
		run: physical(run),
		touching_run: touching ? physical(touching) : null,
	};
}

function touchingMatches(
	plan: InstallationInputs,
	run: CableRun,
	rows: CableRun[],
): boolean {
	const current = run.reference_current_installation!;
	const incoming = (id: string) =>
		plan.cable_runs
			.filter(
				(other) => other.reference_current_installation?.touching_run_id === id,
			)
			.map((other) => other.id);
	if (current.laying !== "two_touching_on_surface")
		return current.touching_run_id === null && incoming(run.id).length === 0;
	const other = rows.find((row) => row.id === current.touching_run_id),
		declaration = other?.reference_current_installation;
	return Boolean(
		other &&
		other.id !== run.id &&
		declaration &&
		declaration.laying === current.laying &&
		declaration.rating_id === current.rating_id &&
		declaration.ambient_temperature_c === current.ambient_temperature_c &&
		declaration.touching_run_id === run.id &&
		sameJson(incoming(run.id), [other.id]) &&
		sameJson(incoming(other.id), [run.id]) &&
		declaration.conditions_confirmed &&
		declaration.confirmation_context &&
		sameJson(
			declaration.confirmation_context,
			referenceCurrentContext(plan, other, declaration),
		) &&
		other.route_id === run.route_id &&
		other.conductor &&
		run.conductor &&
		run.conductor.cable_reference &&
		sameJson(other.conductor.cable_reference, run.conductor.cable_reference),
	);
}

/** Bind every comparison to the exact requested run, condition and declaration. */
export function readReferenceCurrentSegments(
	value: unknown,
	plan: InstallationInputs,
): ReferenceCurrentSegment[] | undefined {
	const opted = plan.cable_runs.some(
		(run) => run.reference_current_installation != null,
	);
	if (!opted) {
		if (value !== undefined) fail();
		return undefined;
	}
	const expected = plan.circuits.flatMap((circuit) => {
		const runs = plan.cable_runs.filter((run) => run.circuit_id === circuit.id),
			conditions = circuit.operating_conditions?.length
				? circuit.operating_conditions
				: [null];
		return conditions.flatMap((condition) =>
			runs
				.filter((run) => run.reference_current_installation != null)
				.map((run) => ({ circuit, condition, run, runs })),
		);
	});
	if (!Array.isArray(value) || value.length !== expected.length) return fail();
	return value.map((raw, index) => {
		const row = readObject(raw),
			{ circuit, condition, run, runs } = expected[index]!,
			declaration = run.reference_current_installation!,
			selected = run.conductor?.cable_reference ?? null;
		if (
			row.circuit_id !== circuit.id ||
			row.condition_id !== (condition?.id ?? null) ||
			row.run_id !== run.id ||
			row.role !== (run.core_roles?.length === 1 ? run.core_roles[0] : null) ||
			!sameJson(row.installation, declaration) ||
			row.product_id !== (selected?.product_id ?? null) ||
			row.product_revision !== (selected?.product_revision ?? null) ||
			!(row.reference_input_id === null || isText(row.reference_input_id)) ||
			row.scope !== "single_conductor_reference_only" ||
			row.qualified !== false ||
			![
				"not_evaluated",
				"below_reference",
				"equal_reference",
				"above_reference",
			].includes(String(row.status)) ||
			!Array.isArray(row.reasons) ||
			row.reasons.some(
				(reason) =>
					!referenceCurrentReasons.includes(
						reason as (typeof referenceCurrentReasons)[number],
					),
			) ||
			new Set(row.reasons).size !== row.reasons.length ||
			(row.status === "not_evaluated") !== row.reasons.length > 0
		)
			fail();
		let rating: CableReferenceCurrentRating | null = null;
		if (row.rating !== null) {
			const r = readObject(row.rating);
			if (
				!selected ||
				r.id !== declaration.rating_id ||
				!isHash(selected.product_revision) ||
				![
					"single_in_air",
					"single_on_surface",
					"two_touching_on_surface",
				].includes(String(r.laying)) ||
				!finite(r.ambient_temperature_c) ||
				!finite(r.rated_conductor_temperature_c) ||
				!finite(r.current_a) ||
				r.current_a <= 0
			)
				fail();
			readCableEvidence(r.source, selected!.product_id);
			rating = r as CableReferenceCurrentRating;
		}
		if (row.status === "not_evaluated") {
			if (row.project_current_a !== null || row.reference_current_a !== null)
				fail();
		} else {
			const roles = runs.flatMap((item) => item.core_roles ?? []).sort();
			if (
				!condition ||
				circuit.kind !== "pv_dc" ||
				condition.method !== "dc_resistive" ||
				[
					condition.frequency_hz,
					condition.power_factor,
					condition.reactive_direction,
					condition.balanced,
				].some((v) => v !== null) ||
				runs.length !== 2 ||
				!sameJson(roles, ["dc_negative", "dc_positive"]) ||
				runs.some(
					(item) =>
						item.construction !== "single_conductor" ||
						item.core_roles?.length !== 1 ||
						item.reference_current_installation?.current_path !==
							"single_unbranched",
				) ||
				!declaration.conditions_confirmed ||
				!declaration.confirmation_context ||
				!sameJson(
					declaration.confirmation_context,
					referenceCurrentContext(plan, run, declaration),
				) ||
				!touchingMatches(plan, run, runs) ||
				!rating ||
				rating.laying !== declaration.laying ||
				rating.ambient_temperature_c !== declaration.ambient_temperature_c ||
				rating.ambient_temperature_c !== 60 ||
				rating.rated_conductor_temperature_c !== 120 ||
				row.project_current_a !== condition.current_a ||
				row.reference_current_a !== rating.current_a ||
				row.status !==
					(condition.current_a < rating.current_a
						? "below_reference"
						: condition.current_a > rating.current_a
							? "above_reference"
							: "equal_reference")
			)
				fail();
		}
		return row as unknown as ReferenceCurrentSegment;
	});
}
