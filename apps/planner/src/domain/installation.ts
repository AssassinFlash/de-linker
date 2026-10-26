import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/installation.schema.json" with { type: "json" };
import type { JsonObject } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { sameJson } from "./draft.ts";

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
export interface InstallationInputs {
	schema_version: 1;
	geometry_sha256: string | null;
	instances: DeviceInstance[];
	circuits: InstallationCircuit[];
	routes: InstallationRoute[];
	cable_runs: CableRun[];
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
}
export function readInstallationReview(
	value: unknown,
	requested: InstallationInputs,
	projectId: string,
): InstallationReview {
	const row = readObject(value);
	const prepared = readInstallation(row.prepared_inputs);
	if (
		row.schema_version !== 1 ||
		row.method !== "installation_route_takeoff_v1" ||
		row.project_id !== projectId ||
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
	return {
		prepared_inputs: prepared,
		geometry_sha256: row.geometry_sha256,
		cables,
	};
}
