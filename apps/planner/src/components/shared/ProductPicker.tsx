import { useState } from "react";
import type { EquipmentProduct } from "../../data/equipmentProducts.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { useProductCards } from "../../data/productCards.ts";
import { __ } from "../../i18n.ts";
import { ProductCard } from "./ProductCard.tsx";
import { CatalogStatus } from "./CatalogStatus.tsx";

/** Inspect photographs and facts before choosing; the native field remains available for known models. */
export function ProductPicker({
	options,
	client,
	scope,
	locale,
	disabled,
	selected,
	onSelect,
}: {
	options: readonly EquipmentProduct[];
	client: PlannerClient;
	scope: string;
	locale: string;
	disabled: boolean;
	selected: unknown;
	onSelect: (id: number) => void;
}) {
	const [open, setOpen] = useState(false);
	const [term, setTerm] = useState("");
	const cards = useProductCards(
		client,
		scope,
		locale,
		open ? options.map((p) => p.id) : [],
	);
	const matches = options.filter((p) =>
		[p.brand, p.model, p.sku]
			.join(" ")
			.toLocaleLowerCase(locale)
			.includes(term.trim().toLocaleLowerCase(locale)),
	);
	return (
		<details
			className="sc-product-picker"
			open={open}
			onToggle={(e) => setOpen(e.currentTarget.open)}
		>
			<summary>{__("Browse product details", "linker-tools")}</summary>
			{open && (
				<>
					<label className="sc-field">
						<span>{__("Find a product", "linker-tools")}</span>
						<input
							type="search"
							value={term}
							onChange={(e) => setTerm(e.currentTarget.value)}
						/>
					</label>
					<CatalogStatus
						pending={cards.isPending && options.length > 0}
						failed={cards.isError}
						retry={() => void cards.refetch()}
					/>
					{(!matches.length ||
						(cards.isSuccess &&
							!matches.some((p) => cards.data.has(p.id)))) && (
						<p className="sc-muted">
							{__("No matching products.", "linker-tools")}
						</p>
					)}
					<div className="linker-product-list">
						{matches.map((p) => {
							const card = cards.isSuccess ? cards.data.get(p.id) : undefined;
							return card ? (
								<ProductCard key={p.id} {...card}>
									<button
										type="button"
										className="sc-button"
										aria-pressed={selected === p.id}
										disabled={disabled}
										onClick={() => {
											onSelect(p.id);
											setOpen(false);
										}}
									>
										{selected === p.id
											? __("Selected", "linker-tools")
											: __("Choose this product", "linker-tools")}
									</button>
								</ProductCard>
							) : null;
						})}
					</div>
				</>
			)}
		</details>
	);
}
