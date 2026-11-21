import type { PlannerClient } from "../data/PlannerClient.ts";
import { useProductCards } from "../data/productCards.ts";
import type { SavedSolutionSource } from "../domain/savedSolution.ts";
import { ProductCard } from "./shared/ProductCard.tsx";
import { CatalogStatus } from "./shared/CatalogStatus.tsx";
import type { Json, JsonObject } from "../data/protocol.ts";
import { __ } from "../i18n.ts";

/** An input archive is editable project data, never permission or equipment proof. */
export function SavedSolutionReference({
	value,
	items,
	client,
	scope,
	locale,
}: {
	value: Json | undefined;
	items: SavedSolutionSource["recorded_items"];
	client: PlannerClient;
	scope: string;
	locale: string;
}) {
	const cards = useProductCards(
		client,
		scope,
		locale,
		items.map((item) => item.product_id),
	);
	if (!value || typeof value !== "object" || Array.isArray(value)) return null;
	const source = value as JsonObject;
	if (source.authority !== "historical_user_input") return null;
	return (
		<>
			{items.length > 0 && (
				<section className="sc-section">
					<h3>{__("Selected products", "linker-tools")}</h3>
					<CatalogStatus
						pending={cards.isPending}
						failed={cards.isError}
						retry={() => void cards.refetch()}
					/>
					{cards.data && (
						<div className="linker-product-list">
							{items.map((item) => {
								const product = cards.data.get(item.product_id);
								return (
									<ProductCard
										key={item.product_id}
										{...(product ?? {
											label: __("Saved product unavailable", "linker-tools"),
										})}
										quantity={`× ${new Intl.NumberFormat(locale).format(item.quantity)}`}
									/>
								);
							})}
						</div>
					)}
				</section>
			)}
			<details className="sc-section">
				<summary>{__("Original inputs", "linker-tools")}</summary>
				<p>{typeof source.title === "string" ? source.title : ""}</p>
				<a
					className="sc-text-button"
					download="saved-solution-inputs.json"
					href={
						"data:application/json;charset=utf-8," +
						encodeURIComponent(JSON.stringify(value, null, 2))
					}
				>
					{__("Download original inputs (JSON)", "linker-tools")}
				</a>
			</details>
		</>
	);
}
