import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/installation.schema.json" with { type: "json" };
import { readElectricalReview } from "./installationElectrical.ts";
import type {
	CircuitOperatingCondition,
	CoreRole,
	ElectricalReview,
} from "./installationElectrical.ts";
import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { sameJson } from "./draft.ts";
import type { PvPlantStringPlan } from "./pvPlantStrings.ts";
import type { EquipmentPlant } from "./equipmentPlant.ts";
import type { PvStringPlan } from "./pvStrings.ts";
import { readTerminalAssessment } from "./installationTerminals.ts";
import type {
	TerminalAssessment,
	TerminalBinding,
} from "./installationTerminals.ts";

export interface RoutePoint {
	east_m: number;
	north_m: number;
	height_m: number | null;
}
export interface ConnectionPoint {
	id: string;
	name: string;
	position: RoutePoint;
	terminal_binding?: TerminalBinding | null;
}
export interface DeviceInstance {
	id: string;
	name: string;
	product_id: number | null;
	product_revision: string | null;
	source_id: string;
	ports: ConnectionPoint[];
}
export interface Endpoint {
	instance_id: string;
	port_id: string;
}
export interface InstallationCircuit {
	operating_conditions?: CircuitOperatingCondition[];
	communication_use?:
		"external_communication" | "internal_communication" | null;
	id: string;
	name: string;
	kind:
		"pv_dc" | "battery_dc" | "ac" | "control" | "protective_earth" | "other";
	start: Endpoint;
	end: Endpoint;
}
export interface InstallationRoute {
	id: string;
	name: string;
	source_id: string;
	points: RoutePoint[];
	extra_length_m: number | null;
	extra_length_note: string | null;
}
export interface ConductorSpecification extends JsonObject {
	readonly cross_section_mm2: number;
	readonly source_note: string;
	readonly cable_reference?: {
		product_id: number;
		product_revision: string;
	} | null;
}
export type ReferenceCurrentEndpoint = {
	instance_id: string;
	port_id: string;
	product_id: number | null;
	product_revision: string | null;
	position: { east_m: number; north_m: number; height_m: number | null };
};
export type ReferenceCurrentPhysical = {
	id: string;
	construction: CableRun["construction"];
	core_roles: CoreRole[];
	cross_section_mm2: number | null;
	cable_reference: { product_id: number; product_revision: string } | null;
	route: {
		id: string;
		points: { east_m: number; north_m: number; height_m: number | null }[];
		extra_length_m: number | null;
	};
	circuit: {
		id: string;
		kind: InstallationCircuit["kind"];
		start: ReferenceCurrentEndpoint;
		end: ReferenceCurrentEndpoint;
	};
};
export type ReferenceCurrentContext = {
	declaration: {
		rating_id: string;
		laying: ReferenceCurrentInstallation["laying"];
		ambient_temperature_c: number;
		touching_run_id: string | null;
		current_path: ReferenceCurrentInstallation["current_path"];
	};
	run: ReferenceCurrentPhysical;
	touching_run: ReferenceCurrentPhysical | null;
};
export interface ReferenceCurrentInstallation extends JsonObject {
	rating_id: string;
	laying: "single_in_air" | "single_on_surface" | "two_touching_on_surface";
	ambient_temperature_c: number;
	touching_run_id: string | null;
	current_path: "single_unbranched" | "unknown";
	conditions_confirmed: boolean;
	source_note: string;
	confirmation_context?: ReferenceCurrentContext | null;
}
export interface CableRun {
	core_roles?: CoreRole[];
	id: string;
	name: string;
	circuit_id: string;
	route_id: string;
	construction: "single_conductor" | "multicore_cable" | "unspecified";
	/** Absent keeps the specification explicitly open; it never inherits one. */
	conductor?: ConductorSpecification | null;
	reference_current_installation?: ReferenceCurrentInstallation | null;
}
export interface PvStringLink {
	string_id: string;
	circuit_id: string;
}
export interface InstallationMaterial {
	id: string;
	name: string;
	kind: "connector" | "protection" | "earthing" | "mounting" | "other";
	circuit_id: string | null;
	quantity: number | null;
	unit: "piece" | "m";
	specification: string;
	source_note: string;
	comparison?: {
		instance_id: string;
		product_id: number;
		product_revision: string;
		fact_id: string;
		document_id: string;
		document_revision: string;
		cross_section_mm2: number | null;
		rated_current_a: number | null;
		rated_voltage_v: number | null;
		conditions_confirmed: boolean;
		circuit_context: Pick<InstallationCircuit, "id" | "kind" | "start" | "end">;
	};
}
export interface InstallationInputs {
	schema_version: 1;
	geometry_sha256: string | null;
	instances: DeviceInstance[];
	circuits: InstallationCircuit[];
	routes: InstallationRoute[];
	cable_runs: CableRun[];
	pv_string_links?: PvStringLink[];
	materials?: InstallationMaterial[];
}
export const installationId = (prefix: string) =>
	prefix + "_" + crypto.randomUUID().replaceAll("-", "");
export const emptyInstallation = (): InstallationInputs => ({
	schema_version: 1,
	geometry_sha256: null,
	instances: [],
	circuits: [],
	routes: [],
	cable_runs: [],
});
const reviewReasons = new Set([
	"layout_confirmation_required",
	"source_missing",
	"source_export_unconfirmed",
	"route_endpoints_differ",
	"height_missing",
	"extra_length_unconfirmed",
	"route_length_not_positive",
]);
const validate = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<InstallationInputs>(schema);
/** Absent and null must not both exist: only absence keeps historical bytes. */
function canonicalConductor(value: InstallationInputs): InstallationInputs {
	if (
		value.cable_runs.every(
			(run) =>
				run.conductor !== null &&
				run.conductor?.cable_reference !== null &&
				run.reference_current_installation !== null &&
				run.reference_current_installation?.confirmation_context !== null,
		)
	)
		return value;
	return {
		...value,
		cable_runs: value.cable_runs.map((run) => {
			const next = { ...run };
			if (next.reference_current_installation === null)
				delete next.reference_current_installation;
			else if (
				next.reference_current_installation?.confirmation_context === null
			) {
				const declaration = { ...next.reference_current_installation };
				delete declaration.confirmation_context;
				next.reference_current_installation = declaration;
			}
			if (next.conductor?.cable_reference === null) {
				const conductor = { ...next.conductor };
				delete conductor.cable_reference;
				next.conductor = conductor;
			}
			if (next.conductor === null) delete next.conductor;
			return next;
		}),
	};
}
export function readInstallation(value: unknown): InstallationInputs {
	if (value === undefined) return emptyInstallation();
	if (!validate(value)) throw new ApiError(422, "invalid_installation");
	const distinct = (ids: readonly string[]) => new Set(ids).size === ids.length;
	if (
		!distinct((value.materials ?? []).map((row) => row.id)) ||
		(value.materials ?? []).some(
			(row) =>
				row.unit === "piece" &&
				row.quantity !== null &&
				!Number.isSafeInteger(row.quantity),
		) ||
		[value.instances, value.circuits, value.routes, value.cable_runs].some(
			(rows) => !distinct(rows.map((row) => row.id)),
		)
	)
		throw new ApiError(422, "invalid_installation");
	const ports = new Set(
		value.instances.flatMap((d) => d.ports.map((p) => d.id + ":" + p.id)),
	);
	if (
		value.instances.some(
			(d) =>
				(d.product_id === null) !== (d.product_revision === null) ||
				!distinct(d.ports.map((p) => p.id)),
		) ||
		value.circuits.some(
			(c) =>
				(c.communication_use != null && c.kind !== "control") ||
				!distinct((c.operating_conditions ?? []).map((row) => row.id)) ||
				!ports.has(c.start.instance_id + ":" + c.start.port_id) ||
				!ports.has(c.end.instance_id + ":" + c.end.port_id) ||
				sameJson(c.start, c.end),
		) ||
		value.cable_runs.some(
			(c) =>
				!distinct((c.core_roles ?? []).filter((role) => role !== "unused")) ||
				!value.circuits.some((x) => x.id === c.circuit_id) ||
				!value.routes.some((x) => x.id === c.route_id),
		)
	)
		throw new ApiError(422, "invalid_installation");
	const links = value.pv_string_links ?? [];
	if (
		!distinct(links.map((link) => link.string_id)) ||
		!distinct(links.map((link) => link.circuit_id))
	)
		throw new ApiError(422, "invalid_installation");
	return canonicalConductor(value);
}
export interface CableQuantity extends JsonObject {
	id: string;
	name: string;
	circuit_name: string;
	route_name: string;
	construction: CableRun["construction"];
	/** Null when the project declared no cross-section for this run. */
	conductor: ConductorSpecification | null;
	specification: "open" | "declared";
	quantity: number | null;
	unit: "m";
	plan_length_m: number;
	route_length_m: number | null;
	extra_length_m: number | null;
	reasons: string[];
}
export interface InstallationReview {
	material_review?: {
		rows: (InstallationMaterial & {
			circuit_status: string;
			verification: "not_assessed";
			comparison_result?: { status: string; qualified: false; fact: unknown };
		})[];
	};
	electrical?: ElectricalReview;
	terminal_assessment?: TerminalAssessment;
	prepared_inputs: InstallationInputs;
	geometry_sha256: string;
	cables: CableQuantity[];
	pv_string_reconciliation?: PvStringReconciliation;
}
export type PvStringLinkStatus =
	| "linked"
	| "unlinked"
	| "stale_string"
	| "stale_circuit"
	| "wrong_circuit_kind"
	| "inverter_endpoint_unresolved";
export type ConductorClosure =
	"declared" | "unconfirmed" | "conflicting" | "not_recorded";
export type QuantityClosure = "confirmed" | "pending" | "not_recorded";
/** What one frozen revision actually records about a linked circuit. */
export interface PvStringClosure {
	conductor: ConductorClosure;
	quantity: QuantityClosure;
	recorded: boolean;
	/** Sizing, protection and country admission are never implied here. */
	approval: "not_assessed";
}
export interface PvStringLinkReview {
	unit_id?: string | null;
	inverter_instance_id?: string | null;
	instance_status?: string;
	string_id: string;
	mppt: number | null;
	input: number | null;
	circuit_id: string | null;
	status: PvStringLinkStatus;
	endpoints: {
		side: "start" | "end";
		instance_id: string;
		port_id: string;
		product_id: number | null;
		product_revision: string | null;
	}[];
	cable_runs: CableQuantity[];
	closure: PvStringClosure;
	reasons: "cable_runs_missing"[];
}
export interface PvStringReconciliation {
	pv_string_plan_sha256?: string | null;
	pv_plant_string_plan_sha256?: string;
	installation_input_sha256: string;
	geometry_sha256: string;
	plan_status: "missing" | "empty" | "available";
	rows: PvStringLinkReview[];
}
function readStringReconciliation(
	value: unknown,
	requested: InstallationInputs,
	strings: PvStringPlan | PvPlantStringPlan | null,
	cables: CableQuantity[],
	geometrySha: string,
	inputSha: unknown,
	plant?: EquipmentPlant | null,
): PvStringReconciliation {
	const multi = strings !== null && "units" in strings;
	const plantStrings = multi ? (strings as PvPlantStringPlan) : null;
	const singleStrings = !multi ? (strings as PvStringPlan | null) : null;
	const owners = new Map(
		plantStrings?.units.flatMap((u) =>
			u.plan.strings.map((s) => [s.id, u] as const),
		) ?? [],
	);
	const allStrings = plantStrings
		? plantStrings.units.flatMap((u) => u.plan.strings)
		: (singleStrings?.strings ?? []);
	const result = readObject(value),
		hash = (v: unknown): v is string =>
			typeof v === "string" && /^[a-f0-9]{64}$/.test(v),
		fail = (): never => {
			throw new ApiError(502, "invalid_installation_review");
		},
		known = new Map(allStrings.map((s) => [s.id, s])),
		links = new Map(requested.pv_string_links?.map((l) => [l.string_id, l])),
		ids = [
			...known.keys(),
			...[...links.keys()].filter((id) => !known.has(id)),
		],
		planStatus = !strings ? "missing" : known.size ? "available" : "empty";
	if (
		result.schema_version !== (multi ? 2 : 1) ||
		result.scope !== "declared_project_identity_only" ||
		result.qualified !== false ||
		result.plan_status !== planStatus ||
		!hash(inputSha) ||
		result.installation_input_sha256 !== inputSha ||
		result.geometry_sha256 !== geometrySha ||
		(multi
			? !hash(result.pv_plant_string_plan_sha256) ||
				result.pv_string_plan_sha256 !== undefined
			: strings
				? !hash(result.pv_string_plan_sha256)
				: result.pv_string_plan_sha256 !== null) ||
		!Array.isArray(result.rows) ||
		result.rows.length !== ids.length
	)
		fail();
	const rows = (result.rows as unknown[]).map(
		(raw, index): PvStringLinkReview => {
			const owner = owners.get(ids[index]!);
			const plantUnit = plant?.units.find((u) => u.id === owner?.unit_id);
			const instance = requested.instances.find(
				(i) => i.id === owner?.inverter_instance_id,
			);
			const instanceStatus = !owner
				? "not_recorded"
				: !plant
					? "unprepared_plant"
					: !plantUnit
						? "unknown_unit"
						: owner.plan.inverter_product_id !==
							  plantUnit.selection.inverter_product_id
							? "plan_product_mismatch"
							: owner.inverter_instance_id === null
								? "not_recorded"
								: !instance
									? "stale_instance"
									: instance.product_id !==
										  plantUnit.selection.inverter_product_id
										? "product_mismatch"
										: instance.product_revision !==
											  plantUnit.selection.product_revisions[
													String(plantUnit.selection.inverter_product_id)
											  ]
											? "revision_mismatch"
											: "declared";
			const row = readObject(raw),
				id = ids[index]!,
				string = known.get(id),
				link = links.get(id),
				circuit = requested.circuits.find((c) => c.id === link?.circuit_id),
				endpoints: PvStringLinkReview["endpoints"] = circuit
					? (["start", "end"] as const).map((side) => {
							const endpoint = circuit[side],
								instance = requested.instances.find(
									(i) => i.id === endpoint.instance_id,
								)!;
							return {
								side,
								instance_id: instance.id,
								port_id: endpoint.port_id,
								product_id: instance.product_id,
								product_revision: instance.product_revision,
							};
						})
					: [],
				recorded = cables.filter((c) => circuit && c.circuit_id === circuit.id),
				status: PvStringLinkStatus = !string
					? "stale_string"
					: !link
						? "unlinked"
						: !circuit
							? "stale_circuit"
							: circuit.kind !== "pv_dc"
								? "wrong_circuit_kind"
								: (
											multi
												? instanceStatus !== "declared" ||
													endpoints.filter(
														(e) =>
															e.instance_id === owner?.inverter_instance_id,
													).length !== 1
												: endpoints.filter(
														(e) =>
															e.product_id ===
															singleStrings?.inverter_product_id,
													).length !== 1
									  )
									? "inverter_endpoint_unresolved"
									: "linked",
				reasons: PvStringLinkReview["reasons"] =
					circuit && !recorded.length ? ["cable_runs_missing"] : [],
				// Recomputed from the recorded runs so a reply cannot claim a
				// closure the frozen inputs do not support.
				closure: PvStringClosure = {
					conductor: !recorded.length
						? "not_recorded"
						: recorded.some((c) => c.conductor === null)
							? "unconfirmed"
							: new Set(recorded.map((c) => c.conductor!.cross_section_mm2))
										.size > 1
								? "conflicting"
								: "declared",
					quantity: !recorded.length
						? "not_recorded"
						: recorded.some((c) => c.quantity === null)
							? "pending"
							: "confirmed",
					recorded: false,
					approval: "not_assessed",
				};
			closure.recorded =
				status === "linked" &&
				closure.conductor === "declared" &&
				closure.quantity === "confirmed";
			if (
				(multi &&
					(row.unit_id !== (owner?.unit_id ?? null) ||
						row.inverter_instance_id !==
							(owner?.inverter_instance_id ?? null) ||
						row.instance_status !== instanceStatus)) ||
				row.string_id !== id ||
				row.mppt !== (string?.mppt ?? null) ||
				row.input !== (string?.input ?? null) ||
				row.circuit_id !== (link?.circuit_id ?? null) ||
				row.status !== status ||
				!sameJson(row.endpoints, endpoints) ||
				!sameJson(row.cable_runs, recorded) ||
				!sameJson(row.closure, closure) ||
				!sameJson(row.reasons, reasons)
			)
				fail();
			return {
				...(multi
					? {
							unit_id: owner?.unit_id ?? null,
							inverter_instance_id: owner?.inverter_instance_id ?? null,
							instance_status: instanceStatus,
						}
					: {}),
				string_id: id,
				mppt: string?.mppt ?? null,
				input: string?.input ?? null,
				circuit_id: link?.circuit_id ?? null,
				status,
				endpoints,
				cable_runs: recorded,
				closure,
				reasons,
			};
		},
	);
	return {
		...(multi
			? {
					pv_plant_string_plan_sha256:
						result.pv_plant_string_plan_sha256 as string,
				}
			: {
					pv_string_plan_sha256: result.pv_string_plan_sha256 as string | null,
				}),
		installation_input_sha256: inputSha as string,
		geometry_sha256: geometrySha,
		plan_status: planStatus,
		rows,
	};
}
export function readInstallationReview(
	value: unknown,
	requested: InstallationInputs,
	projectId: string,
	savedStrings?: PvStringPlan | PvPlantStringPlan | null,
	expectedRevision?: number,
	savedPlant?: EquipmentPlant | null,
): InstallationReview {
	const row = readObject(value);
	const prepared = readInstallation(row.prepared_inputs);
	if (
		row.schema_version !== 1 ||
		row.method !== "installation_route_takeoff_v1" ||
		row.project_id !== projectId ||
		(expectedRevision !== undefined &&
			row.project_revision !== expectedRevision) ||
		row.qualified !== false ||
		typeof row.geometry_sha256 !== "string" ||
		!/^[a-f0-9]{64}$/.test(row.geometry_sha256) ||
		prepared.geometry_sha256 !== row.geometry_sha256 ||
		!sameJson(
			{ ...prepared, geometry_sha256: requested.geometry_sha256 },
			requested,
		) ||
		!Array.isArray(row.cables) ||
		row.cables.length !== requested.cable_runs.length
	)
		throw new ApiError(502, "invalid_installation_review");
	const cables = row.cables.map((raw, index) => {
		const c = readObject(raw),
			input = requested.cable_runs[index]!;
		if (
			c.id !== input.id ||
			c.name !== input.name ||
			c.circuit_id !== input.circuit_id ||
			c.route_id !== input.route_id ||
			c.unit !== "m" ||
			typeof c.circuit_name !== "string" ||
			typeof c.route_name !== "string" ||
			!Array.isArray(c.reasons) ||
			c.reasons.some((x) => typeof x !== "string" || !reviewReasons.has(x))
		)
			throw new ApiError(502, "invalid_installation_review");
		for (const field of [
			"quantity",
			"plan_length_m",
			"route_length_m",
			"extra_length_m",
		]) {
			const n = c[field];
			if (
				!(n === null && field !== "plan_length_m") &&
				(typeof n !== "number" ||
					!Number.isFinite(n) ||
					n < 0 ||
					n > Number.MAX_SAFE_INTEGER)
			)
				throw new ApiError(502, "invalid_installation_review");
		}
		if (
			(c.reasons.length === 0) !== (c.quantity !== null) ||
			(typeof c.quantity === "number" && c.quantity <= 0)
		)
			throw new ApiError(502, "invalid_installation_review");
		// The declared section and the reported status must describe the same
		// frozen run; a reply may not upgrade an undeclared run on its own.
		const declared = c.conductor,
			expected = input.conductor ?? null;
		if (
			!sameJson(declared, expected) ||
			c.specification !== (expected === null ? "open" : "declared")
		)
			throw new ApiError(502, "invalid_installation_review");
		return c as CableQuantity;
	});
	const optedIn =
		requested.pv_string_links !== undefined ||
		(savedStrings !== null &&
			savedStrings !== undefined &&
			"units" in savedStrings);
	if (
		(optedIn &&
			(savedStrings === undefined || expectedRevision === undefined)) ||
		(!optedIn && row.pv_string_reconciliation !== undefined)
	)
		throw new ApiError(502, "invalid_installation_review");
	const electrical = readElectricalReview(row.electrical, requested, cables);
	const terminals = readTerminalAssessment(row.terminal_assessment, requested);
	let materialReview: InstallationReview["material_review"];
	if (requested.materials !== undefined) {
		const review = readObject(row.material_review);
		if (
			review.method !== "project_declared_installation_materials_v1" ||
			review.qualified !== false ||
			review.complete_bos !== false ||
			!Array.isArray(review.rows) ||
			review.rows.length !== requested.materials.length
		)
			throw new ApiError(502, "invalid_installation_review");
		const rows = review.rows.map((raw, i) => {
			const item = readObject(raw),
				expected = requested.materials![i]!;
			const status =
				expected.circuit_id === null
					? "not_linked"
					: requested.circuits.some((c) => c.id === expected.circuit_id)
						? "linked"
						: "circuit_unavailable";
			const {
				circuit_status,
				verification,
				comparison_result,
				...declaration
			} = item;
			if (
				!sameJson(declaration, expected) ||
				circuit_status !== status ||
				verification !== "not_assessed"
			)
				throw new ApiError(502, "invalid_installation_review");
			if (expected.comparison) {
				const comparison = readObject(comparison_result);
				const statuses = [
					"within_recommendation",
					"outside_recommendation",
					"meets_minimum_values",
					"below_minimum_values",
					"unavailable",
					"circuit_or_instance_unavailable",
					"instance_mismatch",
					"product_unavailable",
					"fact_unavailable",
					"document_unavailable",
					"conditions_not_assessed",
					"conditions_not_confirmed",
					"conditions_changed",
					"scope_mismatch",
				];
				if (
					comparison.qualified !== false ||
					typeof comparison.status !== "string" ||
					!statuses.includes(comparison.status)
				)
					throw new ApiError(502, "invalid_installation_review");
				if (
					[
						"within_recommendation",
						"outside_recommendation",
						"meets_minimum_values",
						"below_minimum_values",
					].includes(comparison.status)
				) {
					const fact = readObject(comparison.fact),
						source = readObject(fact.source),
						spec = readObject(fact.specification),
						binding = expected.comparison;
					const circuit = requested.circuits.find(
						(c) => c.id === expected.circuit_id,
					);
					const instance = requested.instances.find(
						(d) => d.id === binding.instance_id,
					);
					if (
						!circuit ||
						!instance ||
						![circuit.start.instance_id, circuit.end.instance_id].includes(
							instance.id,
						) ||
						instance.product_id !== binding.product_id ||
						instance.product_revision !== binding.product_revision ||
						!binding.conditions_confirmed ||
						!sameJson(binding.circuit_context, {
							id: circuit.id,
							kind: circuit.kind,
							start: circuit.start,
							end: circuit.end,
						}) ||
						fact.id !== binding.fact_id ||
						source.product_id !== binding.product_id ||
						source.document_id !== binding.document_id ||
						source.document_revision !== binding.document_revision ||
						!Array.isArray(fact.conditions) ||
						fact.conditions.length
					)
						throw new ApiError(502, "invalid_installation_review");
					if (
						expected.kind === "earthing" &&
						circuit.kind === "protective_earth" &&
						fact.basis === "manufacturer_recommended_pe_conductor" &&
						spec.terminal_domain === "pe"
					) {
						const range = readObject(spec.recommended_conductor_mm2),
							value = binding.cross_section_mm2;
						if (
							typeof range.low !== "number" ||
							typeof range.high !== "number" ||
							value === null ||
							comparison.status !==
								(value >= range.low && value <= range.high
									? "within_recommendation"
									: "outside_recommendation")
						)
							throw new ApiError(502, "invalid_installation_review");
					} else if (
						expected.kind === "protection" &&
						circuit.kind === "ac" &&
						fact.basis === "manufacturer_minimum_rating" &&
						spec.terminal_domain === "ac"
					) {
						if (
							typeof spec.minimum_current_a !== "number" ||
							typeof spec.minimum_voltage_v !== "number" ||
							binding.rated_current_a === null ||
							binding.rated_voltage_v === null ||
							comparison.status !==
								(binding.rated_current_a >= spec.minimum_current_a &&
								binding.rated_voltage_v >= spec.minimum_voltage_v
									? "meets_minimum_values"
									: "below_minimum_values")
						)
							throw new ApiError(502, "invalid_installation_review");
					} else throw new ApiError(502, "invalid_installation_review");
				} else if (comparison.fact !== null)
					throw new ApiError(502, "invalid_installation_review");
			} else if (comparison_result !== undefined)
				throw new ApiError(502, "invalid_installation_review");
			return item as unknown as InstallationMaterial & {
				circuit_status: string;
				verification: "not_assessed";
				comparison_result?: { status: string; qualified: false; fact: unknown };
			};
		});
		materialReview = { rows };
	} else if (row.material_review !== undefined)
		throw new ApiError(502, "invalid_installation_review");
	return {
		...(materialReview ? { material_review: materialReview } : {}),
		...(electrical ? { electrical } : {}),
		...(terminals ? { terminal_assessment: terminals } : {}),
		prepared_inputs: prepared,
		geometry_sha256: row.geometry_sha256,
		cables,
		...(optedIn
			? {
					pv_string_reconciliation: readStringReconciliation(
						row.pv_string_reconciliation,
						requested,
						savedStrings ?? null,
						cables,
						row.geometry_sha256,
						row.input_sha256,
						savedPlant,
					),
				}
			: {}),
	};
}
