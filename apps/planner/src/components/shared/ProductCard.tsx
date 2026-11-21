import type { ReactNode } from "react";

export interface ProductCardDetails {
	label: string;
	imageUrl?: string | null;
	productUrl?: string | null;
	highlight?: string | null;
}

export function ProductCard({
	label,
	imageUrl,
	productUrl,
	highlight,
	quantity,
	children,
}: ProductCardDetails & {
	quantity?: ReactNode;
	children?: ReactNode;
}) {
	const identity = (
		<>
			{imageUrl && (
				<img
					loading="lazy"
					decoding="async"
					src={imageUrl}
					alt=""
					width="80"
					height="80"
				/>
			)}
			<span className="linker-product-card__copy">
				<strong>{label}</strong>
				{highlight && <small>{highlight}</small>}
			</span>
		</>
	);
	return (
		<article className="linker-product-card">
			{productUrl ? (
				<a
					className="linker-product-card__identity"
					href={productUrl}
					target="_blank"
					rel="noopener noreferrer"
				>
					{identity}
				</a>
			) : (
				<div className="linker-product-card__identity">{identity}</div>
			)}
			{quantity != null && (
				<strong className="linker-product-card__qty">{quantity}</strong>
			)}
			{children && (
				<div className="linker-product-card__details">{children}</div>
			)}
		</article>
	);
}
