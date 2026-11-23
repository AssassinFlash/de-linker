import { useLayoutEffect, useState, type RefObject } from "react";
import { useQuery } from "@tanstack/react-query";
import type { Configuration } from "../data/config.ts";
import type { PlannerClient } from "../data/PlannerClient.ts";
import { readObject } from "../data/readProtocol.ts";
import {
	clearRoofImageryConsent,
	onMapConsentChange,
} from "../data/roofImageryConsent.ts";
import type { Brief } from "../domain/brief.ts";
import {
	imagerySourceKey,
	readPlaceImagery,
	type PlaceImagery,
} from "../domain/place.ts";
import { __, sprintf } from "../i18n.ts";

export function RoofMapAction({
	config,
	site,
	client,
	scope,
	disabled,
	locked,
	busy,
	permitted,
	open,
}: {
	config: Configuration;
	site: Brief["site"];
	client: PlannerClient;
	scope: string;
	disabled: boolean;
	locked: boolean;
	busy: boolean;
	permitted: RefObject<PlaceImagery | null>;
	open?: () => void;
}) {
	const country = site.country_code;
	// German editing layers belong to individual states. The place service
	// resolves a postcode even when a street address includes the town after it.
	const regionalPostcode =
		country === "DE" ? site.location_label.match(/\b\d{5}\b/u)?.[0] : null;
	const query =
		site.postal_code ||
		(country === "DE"
			? regionalPostcode
			: country && config.countries[country]);
	const offer = useQuery({
		queryKey: [scope, "roof-entry-imagery", country, query],
		enabled: Boolean(
			country &&
			query &&
			site.location_label.trim() &&
			client.isCurrentScope(scope),
		),
		retry: false,
		queryFn: async ({ signal }) => {
			const result = readObject(
				await client.query(
					"places/lookup",
					{
						schema_version: 1,
						country,
						query: query || "",
					},
					scope,
					signal,
				),
			);
			return (
				readPlaceImagery(result.imagery) ??
				readPlaceImagery(result.viewing_imagery)
			);
		},
	});
	const source = offer.data;
	const sourceKey = source ? imagerySourceKey(source) : "";
	const [checked, setChecked] = useState(false);
	useLayoutEffect(() => {
		setChecked(false);
		permitted.current = null;
		const revoke = () => {
			setChecked(false);
			permitted.current = null;
			clearRoofImageryConsent();
		};
		const unsubscribe = onMapConsentChange(revoke);
		return () => {
			permitted.current = null;
			unsubscribe();
		};
	}, [country, permitted, sourceKey]);
	return (
		<div className="sc-field-wide sc-roof-access">
			<p className="sc-muted">
				{__(
					"Opening the map sends this address to Google Maps to find your building.",
					"linker-tools",
				)}
			</p>
			{source && (
				<label className="sc-checkbox">
					<input
						type="checkbox"
						name="roof_imagery_consent"
						checked={checked}
						disabled={disabled}
						onChange={(event) => {
							setChecked(event.currentTarget.checked);
							permitted.current = event.currentTarget.checked ? source : null;
						}}
					/>
					{sprintf(
						__(
							"Load aerial imagery from %s. The provider receives your IP address and the map area shown.",
							"linker-tools",
						),
						source.credit,
					)}
				</label>
			)}
			<button
				className={open ? "sc-button" : "sc-button sc-primary"}
				type={open ? "button" : "submit"}
				onClick={open}
				disabled={
					disabled || (!locked && (!country || !site.location_label.trim()))
				}
			>
				{busy
					? __("Finding the site…", "linker-tools")
					: locked
						? __("Retry project creation", "linker-tools")
						: __("Open aerial map", "linker-tools")}
			</button>
		</div>
	);
}
