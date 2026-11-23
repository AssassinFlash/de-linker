import type { JsonObject } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";

/** Requested units belong to the inquiry. Engineering inputs still describe the complete system. */
export function changeInquiryQuantity(
	inputs: JsonObject,
	productId: number,
	current: number,
	next: number,
): JsonObject {
	const quantities = { ...readObject(inputs.inquiry_quantities ?? {}) };
	const key = String(productId);
	const previous = readObject(quantities[key] ?? {});
	const planned =
		previous.requested === current &&
		typeof previous.planned_purchase === "number"
			? previous.planned_purchase
			: current;
	if (next === planned) delete quantities[key];
	else quantities[key] = { planned_purchase: planned, requested: next };
	const { inquiry_quantities: _previous, ...project } = inputs;
	return Object.keys(quantities).length
		? { ...project, inquiry_quantities: quantities }
		: project;
}
