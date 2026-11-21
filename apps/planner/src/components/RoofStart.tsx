import type { ReactNode } from "react";
import type { Configuration } from "../data/config.ts";
import type { Brief } from "../domain/brief.ts";
import { __ } from "../i18n.ts";

export function RoofStart({
	config,
	site,
	disabled,
	locked,
	action,
	openPlan,
	change,
}: {
	config: Configuration;
	site: Brief["site"];
	disabled: boolean;
	locked: boolean;
	action: ReactNode;
	openPlan: () => void;
	change: (site: Brief["site"]) => void;
}) {
	return (
		<>
			<div className="sc-actions sc-roof-plan-entry">
				<button
					className="sc-button"
					type="button"
					disabled={disabled || locked}
					onClick={openPlan}
				>
					{__("Use a roof plan or measurements", "linker-tools")}
				</button>
				{!locked && (
					<a className="sc-button" href="?compare=preliminary">
						{__("Compare options", "linker-tools")}
					</a>
				)}
			</div>
			<section className="sc-card">
				<header className="sc-section-head">
					<div>
						<p>
							{__(
								"Find your building on the aerial image, then draw the roof and place panels.",
								"linker-tools",
							)}
						</p>
					</div>
				</header>
				<fieldset className="sc-fields" disabled={disabled || locked}>
					<label className="sc-field">
						<span>{__("Country", "linker-tools")}</span>
						<select
							name="country"
							required
							autoComplete="country"
							value={site.country_code ?? ""}
							onChange={(event) =>
								change({
									...site,
									country_code: event.currentTarget.value || null,
								})
							}
						>
							<option value="">{__("Select a country", "linker-tools")}</option>
							{Object.entries(config.countries)
								.sort((a, b) => a[1].localeCompare(b[1], config.locale))
								.map(([code, name]) => (
									<option key={code} value={code}>
										{name}
									</option>
								))}
						</select>
					</label>
					<label className="sc-field">
						<span>{__("Address or postcode", "linker-tools")}</span>
						<input
							type="text"
							name="location_label"
							autoComplete="street-address"
							required
							value={site.location_label}
							onChange={(event) =>
								change({ ...site, location_label: event.currentTarget.value })
							}
						/>
					</label>
				</fieldset>
				{action}
			</section>
		</>
	);
}
