import type { Configuration } from "../data/config.ts";
import { __ } from "../i18n.ts";

export function RoofStart({
	config,
	country,
	address,
	disabled,
	changeCountry,
	changeAddress,
}: {
	config: Configuration;
	country: string;
	address: string;
	disabled: boolean;
	changeCountry: (value: string) => void;
	changeAddress: (value: string) => void;
}) {
	return (
		<div className="lp-roof-start">
			<div className="lp-roof-start-heading">
				<h2>{__("Start with your roof", "linker-tools")}</h2>
				<p>
					{__(
						"Find your building on the aerial image, then draw the roof and place panels.",
						"linker-tools",
					)}
				</p>
			</div>
			<label className="lp-field">
				<span>{__("Country", "linker-tools")}</span>
				<select
					autoFocus
					required
					autoComplete="country"
					value={country}
					disabled={disabled}
					onChange={(event) => changeCountry(event.currentTarget.value)}
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
			<label className="lp-field">
				<span>{__("Address or postcode", "linker-tools")}</span>
				<input
					type="text"
					required
					autoComplete="street-address"
					value={address}
					disabled={disabled}
					onChange={(event) => changeAddress(event.currentTarget.value)}
					aria-describedby="lp-roof-address-help"
				/>
			</label>
			<p id="lp-roof-address-help" className="lp-profile-help">
				{__(
					"Enter a street address and town, or use a postcode to find the building on the map.",
					"linker-tools",
				)}
			</p>
		</div>
	);
}
