import { useQuery } from "@tanstack/react-query";
import type { PlannerClient } from "./PlannerClient.ts";
import { ApiError } from "./protocol.ts";
import type { JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { currentProductQuery } from "./currentProductQuery.ts";

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
	for (const [id, ports] of Object.entries(dcPorts))
		if (
			!products.some((p) => String(p.id) === id) ||
			!Array.isArray(ports) ||
			ports.some((p) => typeof p !== "string" || !p.trim()) ||
			new Set(ports).size !== ports.length
		)
			throw new ApiError(502, "invalid_product_reply");
	return {
		products,
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
