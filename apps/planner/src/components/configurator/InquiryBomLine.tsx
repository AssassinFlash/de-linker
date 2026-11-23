import { useState } from "react";
import { __, sprintf } from "../../i18n.ts";
import type { readInquiryForm } from "../../data/draftTransfer.ts";

type Review = ReturnType<typeof readInquiryForm>;

export function InquiryBomLine({
	line,
	edit,
	pending,
	onBusy,
	onUpdated,
	onEditConfiguration,
	onProjectQuantity,
}: {
	line: Review["lines"][number];
	edit: Review["draftEdit"];
	pending: boolean;
	onBusy: (value: boolean) => void;
	onUpdated: () => void;
	onEditConfiguration?: (() => void) | undefined;
	onProjectQuantity?: ((next: number) => Promise<void>) | undefined;
}) {
	const [error, setError] = useState(false);
	const { label, imageUrl, sku, availability, productUrl, quantity, cartKey } =
		line;
	async function update(next: number) {
		if (pending) return;
		onBusy(true);
		setError(false);
		try {
			if (onProjectQuantity) {
				await onProjectQuantity(next);
				return;
			}
			if (!edit || !cartKey) return;
			const response = await fetch(edit.url, {
				method: "POST",
				mode: "same-origin",
				credentials: "same-origin",
				headers: {
					"Content-Type": "application/json",
					Nonce: edit.nonce,
					"X-WP-Nonce": edit.restNonce,
				},
				body: JSON.stringify({ key: cartKey, quantity: next }),
			});
			if (!response.ok) throw new Error("quantity_update");
			onUpdated();
		} catch {
			setError(true);
		} finally {
			onBusy(false);
		}
	}
	const identity = (
		<>
			{imageUrl && (
				<span className="linker-inquiry-image">
					<img src={imageUrl} alt="" />
				</span>
			)}
			<span className="linker-inquiry-identity">
				<strong>{label}</strong>
				{sku && (
					<small className="linker-inquiry-sku" title={sku}>
						{sku}
					</small>
				)}
			</span>
		</>
	);
	return (
		<div className="linker-inquiry-line">
			{productUrl ? (
				<a
					className="linker-inquiry-product"
					href={productUrl}
					title={line.highlight ?? undefined}
				>
					{identity}
				</a>
			) : (
				<span className="linker-inquiry-product">{identity}</span>
			)}
			<div className="linker-inquiry-line-controls">
				{availability && (
					<span className="linker-inquiry-stock" data-stock={availability}>
						{availability === "in-stock"
							? __("In stock", "linker-tools")
							: __("Currently unavailable", "linker-tools")}
					</span>
				)}
				{onProjectQuantity || (cartKey && edit) ? (
					<div className="linker-inquiry-stepper">
						<button
							type="button"
							disabled={pending || quantity <= 1}
							aria-label={sprintf(
								__("Decrease quantity for %s", "linker-tools"),
								label,
							)}
							onClick={() => void update(quantity - 1)}
						>
							−
						</button>
						<span>{quantity}</span>
						<button
							type="button"
							disabled={pending}
							aria-label={sprintf(
								__("Increase quantity for %s", "linker-tools"),
								label,
							)}
							onClick={() => void update(quantity + 1)}
						>
							+
						</button>
					</div>
				) : (
					<span>× {quantity}</span>
				)}
			</div>
			{!onProjectQuantity && !cartKey && onEditConfiguration && (
				<button
					type="button"
					className="btn-ghost"
					disabled={pending}
					onClick={onEditConfiguration}
				>
					{__("Adjust equipment quantities", "linker-tools")}
				</button>
			)}
			{error && (
				<p role="alert">
					{__(
						"The quantity could not be updated. Please try again.",
						"linker-tools",
					)}
				</p>
			)}
		</div>
	);
}
