import { readObject } from "../data/readProtocol.ts";
import { documentReference } from "../data/documentReference.ts";
import type { EquipmentProduct } from "../data/equipmentProducts.ts";
import type {
	InstallationInputs,
	InstallationCircuit,
} from "./installation.ts";

export type ConductorCandidate = {
	instanceId: string;
	product: EquipmentProduct;
	factId: string;
	documentId: string;
	documentRevision: string;
	page: number;
	url: string;
	quote: string;
	label: string;
	kind: InstallationCircuit["kind"];
};

export function conductorCandidates(
	plan: InstallationInputs,
	products: readonly EquipmentProduct[],
	locale: string,
): ConductorCandidate[] {
	return plan.instances.flatMap((instance) => {
		const product = products.find(
			(p) =>
				p.id === instance.product_id &&
				p.product_revision === instance.product_revision,
		);
		if (!product) return [];
		try {
			const facts = readObject(product.installation_facts);
			if (facts.status !== "documented" || !Array.isArray(facts.items))
				return [];
			return facts.items.flatMap((raw) => {
				try {
					const fact = readObject(raw),
						spec = readObject(fact.specification),
						source = readObject(fact.source),
						label = readObject(fact.label);
					const kind =
						fact.basis === "manufacturer_recommended_ac_conductor" &&
						spec.terminal_domain === "ac"
							? "ac"
							: fact.basis === "manufacturer_recommended_pe_conductor" &&
								  spec.terminal_domain === "pe"
								? "protective_earth"
								: fact.basis === "manufacturer_model_specific_conductor" &&
									  fact.id === "battery-cluster-conductor" &&
									  spec.terminal_domain === "battery_dc"
									? "battery_dc"
									: null;
					const text = locale.startsWith("de") ? label.de : label.en;
					documentReference(source, true);
					if (
						!kind ||
						!Array.isArray(fact.conditions) ||
						fact.conditions.length !== 0 ||
						typeof fact.id !== "string" ||
						typeof source.document_id !== "string" ||
						typeof source.document_revision !== "string" ||
						typeof source.page !== "number" ||
						typeof source.url !== "string" ||
						typeof source.quote !== "string" ||
						typeof text !== "string"
					)
						return [];
					return [
						{
							instanceId: instance.id,
							product,
							factId: fact.id,
							documentId: source.document_id,
							documentRevision: source.document_revision,
							page: source.page,
							url: source.url,
							quote: source.quote,
							label: text,
							kind,
						},
					];
				} catch {
					return [];
				}
			});
		} catch {
			return [];
		}
	});
}
