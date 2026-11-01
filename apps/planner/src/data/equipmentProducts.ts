import { readCableReferences } from "./cableReferences.ts";
import { useQuery } from "@tanstack/react-query";
import type { PlannerClient } from "./PlannerClient.ts";
import { ApiError } from "./protocol.ts";
import type { JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { currentProductQuery } from "./currentProductQuery.ts";
import { documentReference } from "./documentReference.ts";

export interface BatteryAssembly extends JsonObject {
	sales_unit_kind: "battery_module" | "battery_system" | "integrated_system";
	fixed_modules_per_stack: number | null;
	documents: (JsonObject & { url: string; page: number })[];
}
export type BatteryAssemblies = Readonly<Record<string, BatteryAssembly>>;

export interface EquipmentProduct extends JsonObject {
	readonly id: number;
	readonly product_revision: string;
	readonly model: string;
	readonly brand: string;
	readonly device_class: string;
	readonly figures: JsonObject;
}
export function readEquipmentProducts(value: unknown) {
	const row = readObject(value);
	if (
		row.schema_version !== 1 ||
		row.provider !== "woocommerce" ||
		!Array.isArray(row.products)
	)
		throw new ApiError(502, "invalid_product_reply");
	const products = row.products.map((value) => {
		const item = readObject(value);
		if (
			typeof item.id !== "number" ||
			!Number.isSafeInteger(item.id) ||
			item.id <= 0 ||
			item.id !== item.canonical_product_id ||
			typeof item.product_revision !== "string" ||
			!/^[a-f0-9]{64}$/.test(item.product_revision) ||
			typeof item.model !== "string" ||
			!item.model.trim() ||
			typeof item.brand !== "string" ||
			typeof item.device_class !== "string"
		)
			throw new ApiError(502, "invalid_product_reply");
		readObject(item.figures);
		return item as EquipmentProduct;
	});
	if (new Set(products.map((p) => p.id)).size !== products.length)
		throw new ApiError(502, "invalid_product_reply");
	const dcPorts = readObject(row.dc_battery_ports ?? {});
	const assemblies = readObject(row.battery_assemblies ?? {});
	for (const [id, value] of Object.entries(assemblies)) {
		const assembly = readObject(value),
			fixed = assembly.fixed_modules_per_stack;
		if (
			!products.some((p) => String(p.id) === id) ||
			typeof assembly.sales_unit_kind !== "string" ||
			!["battery_module", "battery_system", "integrated_system"].includes(
				assembly.sales_unit_kind,
			) ||
			(fixed !== null &&
				(assembly.sales_unit_kind !== "battery_system" ||
					typeof fixed !== "number" ||
					!Number.isSafeInteger(fixed) ||
					fixed < 1)) ||
			!Array.isArray(assembly.documents) ||
			!assembly.documents.length
		)
			throw new ApiError(502, "invalid_product_reply");
		for (const doc of assembly.documents) documentReference(doc, true);
	}
	const controllerIds = row.parallel_controller_product_ids ?? [];
	if (
		!Array.isArray(controllerIds) ||
		new Set(controllerIds).size !== controllerIds.length ||
		controllerIds.some(
			(id) => typeof id !== "number" || !products.some((p) => p.id === id),
		)
	)
		throw new ApiError(502, "invalid_product_reply");
	for (const [id, ports] of Object.entries(dcPorts))
		if (
			!products.some((p) => String(p.id) === id) ||
			!Array.isArray(ports) ||
			ports.some((p) => typeof p !== "string" || !p.trim()) ||
			new Set(ports).size !== ports.length
		)
			throw new ApiError(502, "invalid_product_reply");
	return {
		cableReferences: readCableReferences(row.cable_references),
		products,
		assemblies: assemblies as BatteryAssemblies,
		controllers: products.filter((p) => controllerIds.includes(p.id)),
		dcPorts: dcPorts as Readonly<Record<string, readonly string[]>>,
		prepared:
			row.figure_projection_version === 2 &&
			row.compatibility_origin === "woocommerce",
	};
}
export function useEquipmentProducts(
	client: PlannerClient,
	scope: string,
	active: boolean,
) {
	return useQuery({
		...currentProductQuery(client, scope, active),
		select: readEquipmentProducts,
	});
}
