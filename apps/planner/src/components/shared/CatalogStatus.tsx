import { __ } from "../../i18n.ts";

export function CatalogStatus({
	pending,
	failed,
	retry,
}: {
	pending: boolean;
	failed: boolean;
	retry: () => void;
}) {
	if (failed)
		return (
			<div className="sc-card-state" role="alert">
				<span>{__("Product data could not be loaded.", "linker-tools")}</span>
				<button type="button" className="sc-button" onClick={retry}>
					{__("Try again", "linker-tools")}
				</button>
			</div>
		);
	return pending ? (
		<p className="sc-card-state" role="status">
			{__("Loading product data…", "linker-tools")}
		</p>
	) : null;
}
