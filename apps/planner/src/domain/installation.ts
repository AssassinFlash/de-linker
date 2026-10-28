import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/installation.schema.json" with { type: "json" };
import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { sameJson } from "./draft.ts";
import type { PvStringPlan } from "./pvStrings.ts";

export interface RoutePoint {
	east_m: number;
	north_m: number;
	height_m: number | null;
}
export interface ConnectionPoint {
	id: string;
	name: string;
	position: RoutePoint;
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
export interface CableRun {
	id: string;
	name: string;
	circuit_id: string;
	route_id: string;
	construction: "single_conductor" | "multicore_cable" | "unspecified";
}
export interface PvStringLink {
	string_id: string;
	circuit_id: string;
}
export interface InstallationInputs {
	schema_version: 1;
	geometry_sha256: string | null;
	instances: DeviceInstance[];
	circuits: InstallationCircuit[];
	routes: InstallationRoute[];
	cable_runs: CableRun[];
	pv_string_links?: PvStringLink[];
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
export function readInstallation(value: unknown): InstallationInputs {
	if (value === undefined) return emptyInstallation();
	if (!validate(value)) throw new ApiError(422, "invalid_installation");
	const distinct = (ids: readonly string[]) => new Set(ids).size === ids.length;
	if (
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
				!ports.has(c.start.instance_id + ":" + c.start.port_id) ||
				!ports.has(c.end.instance_id + ":" + c.end.port_id) ||
				sameJson(c.start, c.end),
		) ||
		value.cable_runs.some(
			(c) =>
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
	return value;
}
export interface CableQuantity extends JsonObject {
	id: string;
	name: string;
	circuit_name: string;
	route_name: string;
	quantity: number | null;
	unit: "m";
	plan_length_m: number;
	route_length_m: number | null;
	extra_length_m: number | null;
	reasons: string[];
}
export interface InstallationReview {
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
export interface PvStringLinkReview {
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
	reasons: "cable_runs_missing"[];
}
export interface PvStringReconciliation {
	pv_string_plan_sha256: string | null;
	installation_input_sha256: string;
	geometry_sha256: string;
	plan_status: "missing" | "empty" | "available";
	rows: PvStringLinkReview[];
}
function readStringReconciliation(
	value: unknown,
	requested: InstallationInputs,
	strings: PvStringPlan | null,
	cables: CableQuantity[],
	geometrySha: string,
	inputSha: unknown,
): PvStringReconciliation {
	const result = readObject(value),
		hash = (v: unknown): v is string =>
			typeof v === "string" && /^[a-f0-9]{64}$/.test(v),
		fail = (): never => {
			throw new ApiError(502, "invalid_installation_review");
		},
		known = new Map(strings?.strings.map((s) => [s.id, s]) ?? []),
		links = new Map(requested.pv_string_links?.map((l) => [l.string_id, l])),
		ids = [
			...known.keys(),
			...[...links.keys()].filter((id) => !known.has(id)),
		],
		planStatus = !strings ? "missing" : known.size ? "available" : "empty";
	if (
		result.schema_version !== 1 ||
		result.scope !== "declared_project_identity_only" ||
		result.qualified !== false ||
		result.plan_status !== planStatus ||
		!hash(inputSha) ||
		result.installation_input_sha256 !== inputSha ||
		result.geometry_sha256 !== geometrySha ||
		(strings
			? !hash(result.pv_string_plan_sha256)
			: result.pv_string_plan_sha256 !== null) ||
		!Array.isArray(result.rows) ||
		result.rows.length !== ids.length
	)
		fail();
	const rows = (result.rows as unknown[]).map(
		(raw, index): PvStringLinkReview => {
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
								: endpoints.filter(
											(e) => e.product_id === strings?.inverter_product_id,
									  ).length !== 1
									? "inverter_endpoint_unresolved"
									: "linked",
				reasons: PvStringLinkReview["reasons"] =
					circuit && !recorded.length ? ["cable_runs_missing"] : [];
			if (
				row.string_id !== id ||
				row.mppt !== (string?.mppt ?? null) ||
				row.input !== (string?.input ?? null) ||
				row.circuit_id !== (link?.circuit_id ?? null) ||
				row.status !== status ||
				!sameJson(row.endpoints, endpoints) ||
				!sameJson(row.cable_runs, recorded) ||
				!sameJson(row.reasons, reasons)
			)
				fail();
			return {
				string_id: id,
				mppt: string?.mppt ?? null,
				input: string?.input ?? null,
				circuit_id: link?.circuit_id ?? null,
				status,
				endpoints,
				cable_runs: recorded,
				reasons,
			};
		},
	);
	return {
		pv_string_plan_sha256: result.pv_string_plan_sha256 as string | null,
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
	savedStrings?: PvStringPlan | null,
	expectedRevision?: number,
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
		return c as CableQuantity;
	});
	const optedIn = requested.pv_string_links !== undefined;
	if (
		(optedIn &&
			(savedStrings === undefined || expectedRevision === undefined)) ||
		(!optedIn && row.pv_string_reconciliation !== undefined)
	)
		throw new ApiError(502, "invalid_installation_review");
	return {
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
					),
				}
			: {}),
	};
}
