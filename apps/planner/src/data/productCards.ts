import { useQuery } from "@tanstack/react-query";
import type { PlannerClient } from "./PlannerClient.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

interface ShopCard {
	label: string;
	productUrl: string;
	imageUrl: string | null;
	highlight: string | null;
}

/** Current shop presentation is independent of the frozen engineering quantities. */
export function useProductCards(
	client: PlannerClient,
	scope: string,
	locale: string,
	productIds: readonly number[],
) {
	const ids = [...new Set(productIds)].sort((a, b) => a - b);
	const lang = locale.toLowerCase().startsWith("de") ? "de" : "en";
	return useQuery({
		queryKey: ["planner-shop-cards", scope, lang, ids],
		enabled: ids.length > 0 && client.isCurrentScope(scope),
		retry: false,
		refetchOnWindowFocus: false,
		queryFn: async ({ signal }) => {
			const reply = readObject(
				await client.query(
					"products/cards",
					{ schema_version: 1, product_ids: ids, lang },
					scope,
					signal,
				),
			);
			if (!Array.isArray(reply.cards))
				throw new ApiError(502, "invalid_product_reply");
			const cards = new Map<number, ShopCard>();
			for (const value of reply.cards) {
				const row = readObject(value);
				if (
					typeof row.id !== "number" ||
					!ids.includes(row.id) ||
					typeof row.label !== "string" ||
					typeof row.product_url !== "string"
				)
					throw new ApiError(502, "invalid_product_reply");
				cards.set(row.id, {
					label: row.label,
					productUrl: row.product_url,
					imageUrl: typeof row.image_url === "string" ? row.image_url : null,
					highlight: typeof row.highlight === "string" ? row.highlight : null,
				});
			}
			return cards;
		},
	});
}
