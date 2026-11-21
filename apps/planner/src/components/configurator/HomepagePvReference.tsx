import { SiteCoordinates } from "./SiteCoordinates.tsx";
import { useState } from "react";
import type { Configuration } from "../../data/config.ts";
import { locateProjectSite } from "../../data/googleMaps.ts";
import { ApiError, type JsonObject } from "../../data/protocol.ts";
import { readBrief } from "../../domain/brief.ts";
import type { Brief } from "../../domain/brief.ts";
import { hasPlant } from "../../domain/equipmentPlant.ts";
import { invalidateEnergyReplay } from "../../domain/energyScenario.ts";
import {
	emptyPvgisReference,
	KNOWN_PV_MODEL,
	REFERENCE_DATABASES,
	REFERENCE_TECHNOLOGIES,
	referenceDraft,
	referenceInputs,
	referencePrepared,
} from "../../domain/pvgisReference.ts";
import type {
	KnownPvArray,
	PvgisReferenceDraft,
} from "../../domain/pvgisReference.ts";
import { __ } from "../../i18n.ts";

export function homepagePvReferenceAvailable(inputs: JsonObject, brief: Brief) {
	return Boolean(
		brief.system_scope &&
		brief.system_scope !== "storage_only" &&
		!hasPlant(inputs),
	);
}

export function isHomepagePvReferenceReady(
	inputs: JsonObject,
	brief: Brief,
	useAddress = false,
) {
	return (
		!homepagePvReferenceAvailable(inputs, brief) ||
		referenceDraft(inputs).model !== KNOWN_PV_MODEL ||
		(referencePrepared(inputs) &&
			(useAddress
				? Boolean(brief.site.country_code && brief.site.location_label.trim())
				: brief.site.latitude !== null &&
					brief.site.longitude !== null &&
					brief.site.coordinate_basis === "user_entered"))
	);
}

export async function prepareHomepagePvReference(
	inputs: JsonObject,
	config: Pick<Configuration, "googleMapsApiKey" | "locale">,
	useAddress: boolean,
): Promise<JsonObject> {
	if (!useAddress) return inputs;
	const brief = readBrief(inputs.brief);
	if (
		!homepagePvReferenceAvailable(inputs, brief) ||
		referenceDraft(inputs).model !== KNOWN_PV_MODEL
	)
		return inputs;
	const site = await locateProjectSite(brief.site, config);
	if (!site) throw new ApiError(422, "pvgis_reference_site_required");
	return {
		...invalidateEnergyReplay(inputs),
		brief: { ...brief, site },
	};
}

export function changeHomepagePvPower(
	inputs: JsonObject,
	power: number | null,
) {
	const reference = referenceDraft(inputs);
	if (reference.model !== KNOWN_PV_MODEL || reference.arrays?.length !== 1)
		return inputs;
	return referenceInputs(inputs, {
		...reference,
		arrays: [{ ...reference.arrays[0]!, peak_power_kwp: power }],
	});
}

export function HomepagePvReference({
	inputs,
	brief,
	power,
	addressLookup = false,
	initialUseAddress = false,
	locale,
	onCoordinateValidity,
	edit,
}: {
	inputs: JsonObject;
	brief: Brief;
	power: number | null;
	addressLookup?: boolean;
	initialUseAddress?: boolean;
	locale: string;
	onCoordinateValidity: (valid: boolean) => void;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
}) {
	const [useAddress, setUseAddress] = useState(initialUseAddress);
	const reference = referenceDraft(inputs);
	const array =
		reference.model === KNOWN_PV_MODEL ? reference.arrays?.[0] : undefined;
	function toggle(enabled: boolean) {
		if (!enabled) setUseAddress(false);
		edit((current) => {
			if (enabled)
				return referenceInputs(current, {
					...emptyPvgisReference(),
					model: KNOWN_PV_MODEL,
					arrays: [
						{
							id: "declared-array",
							peak_power_kwp: power,
							tilt_deg: null,
							azimuth_north_clockwise_deg: null,
							source_note: "",
						},
					],
				});
			const {
				pvgis_reference_setup: _draft,
				pvgis_reference: _compiled,
				...rest
			} = invalidateEnergyReplay(current);
			return rest;
		});
	}
	function update(
		patch: Partial<PvgisReferenceDraft>,
		arrayPatch?: Partial<
			Pick<
				KnownPvArray,
				"tilt_deg" | "azimuth_north_clockwise_deg" | "source_note"
			>
		>,
	) {
		edit((current) => {
			const prior = referenceDraft(current);
			const first = prior.arrays?.[0];
			if (prior.model !== KNOWN_PV_MODEL || !first) return current;
			return referenceInputs(current, {
				...prior,
				...patch,
				arrays: [{ ...first, ...arrayPatch }],
			});
		});
	}
	function coordinate(field: "latitude" | "longitude", value: number | null) {
		edit((current) => {
			const before = readBrief(current.brief);
			const site = { ...before.site, [field]: value };
			return {
				...invalidateEnergyReplay(current),
				brief: {
					...before,
					site: {
						...site,
						coordinate_basis:
							site.latitude !== null && site.longitude !== null
								? "user_entered"
								: "not_provided",
					},
				},
			};
		});
	}
	function number(
		name: string,
		label: string,
		value: number | null,
		min: number,
		max: number,
		change: (value: number | null) => void,
		step = "any",
	) {
		return (
			<label className="sc-field">
				<span>{label}</span>
				<input
					name={name}
					type="number"
					required
					step={step}
					min={min}
					max={max}
					value={value ?? ""}
					onChange={(event) => {
						const field = event.currentTarget;
						change(
							field.value && field.validity.valid ? field.valueAsNumber : null,
						);
					}}
				/>
			</label>
		);
	}
	return (
		<fieldset className="sc-field-wide">
			<label className="sc-check">
				<input
					name="estimate_solar"
					type="checkbox"
					checked={Boolean(array)}
					onChange={(event) => toggle(event.currentTarget.checked)}
				/>
				{__("Estimate solar generation with PVGIS", "linker-tools")}
			</label>
			{array && (
				<div className="sc-fields">
					{addressLookup && (
						<label className="sc-check sc-field-wide">
							<input
								name="pvgis_use_address"
								type="checkbox"
								checked={useAddress}
								onChange={(event) => setUseAddress(event.currentTarget.checked)}
							/>
							{__(
								"Use the street address above for this estimate (send it to Google Maps)",
								"linker-tools",
							)}
						</label>
					)}
					{(!addressLookup || !useAddress) && (
						<SiteCoordinates
							site={brief.site}
							locale={locale}
							change={coordinate}
							onValidity={onCoordinateValidity}
						/>
					)}
					{number(
						"pv_tilt_deg",
						__("Array inclination (°)", "linker-tools"),
						array.tilt_deg,
						0,
						90,
						(tilt_deg) => update({}, { tilt_deg }),
					)}
					{number(
						"pv_azimuth_deg",
						__("Azimuth clockwise from north (°)", "linker-tools"),
						array.azimuth_north_clockwise_deg,
						0,
						360,
						(azimuth_north_clockwise_deg) =>
							update({}, { azimuth_north_clockwise_deg }),
					)}
					{number(
						"pvgis_year",
						__("Calendar year", "linker-tools"),
						reference.year,
						1,
						9998,
						(year) => update({ year }),
						"1",
					)}
					{number(
						"pvgis_loss_percent",
						__("System loss (%)", "linker-tools"),
						reference.system_loss_percent,
						0,
						100,
						(system_loss_percent) => update({ system_loss_percent }),
					)}
					<label className="sc-field">
						<span>{__("Radiation database", "linker-tools")}</span>
						<select
							name="pvgis_database"
							required
							value={reference.radiation_database ?? ""}
							onChange={(event) =>
								update({
									radiation_database:
										REFERENCE_DATABASES.find(
											(value) => value === event.currentTarget.value,
										) ?? null,
								})
							}
						>
							<option value="">
								{__("Choose a radiation database", "linker-tools")}
							</option>
							{REFERENCE_DATABASES.map((value) => (
								<option key={value}>{value}</option>
							))}
						</select>
					</label>
					<label className="sc-field">
						<span>{__("PV reference technology", "linker-tools")}</span>
						<select
							name="pvgis_technology"
							required
							value={reference.pv_technology ?? ""}
							onChange={(event) =>
								update({
									pv_technology:
										REFERENCE_TECHNOLOGIES.find(
											(value) => value === event.currentTarget.value,
										) ?? null,
								})
							}
						>
							<option value="">
								{__("Choose a reference technology", "linker-tools")}
							</option>
							{REFERENCE_TECHNOLOGIES.map((value) => (
								<option key={value}>{value}</option>
							))}
						</select>
					</label>
					<label className="sc-field">
						<span>{__("Mounting place", "linker-tools")}</span>
						<select
							name="pvgis_mounting"
							required
							value={reference.mounting_place ?? ""}
							onChange={(event) => {
								const value = event.currentTarget.value;
								update({
									mounting_place:
										value === "free" || value === "building" ? value : null,
								});
							}}
						>
							<option value="">
								{__("Choose the mounting place", "linker-tools")}
							</option>
							<option value="free">
								{__("Freestanding or ventilated", "linker-tools")}
							</option>
							<option value="building">
								{__("Building-integrated", "linker-tools")}
							</option>
						</select>
					</label>
					<label className="sc-field">
						<span>{__("Terrain horizon", "linker-tools")}</span>
						<select
							name="pvgis_horizon"
							required
							value={
								reference.use_terrain_horizon === null
									? ""
									: String(reference.use_terrain_horizon)
							}
							onChange={(event) =>
								update({
									use_terrain_horizon: event.currentTarget.value
										? event.currentTarget.value === "true"
										: null,
								})
							}
						>
							<option value="">
								{__("Choose a horizon setting", "linker-tools")}
							</option>
							<option value="true">
								{__("Include PVGIS terrain horizon", "linker-tools")}
							</option>
							<option value="false">
								{__("Omit terrain horizon", "linker-tools")}
							</option>
						</select>
					</label>
					<label className="sc-field sc-field-wide">
						<span>
							{__("Source of array details and model settings", "linker-tools")}
						</span>
						<input
							name="pvgis_source"
							required
							maxLength={4096}
							value={reference.source_note ?? ""}
							onChange={(event) => {
								const source_note = event.currentTarget.value;
								update({ source_note }, { source_note });
							}}
						/>
					</label>
				</div>
			)}
		</fieldset>
	);
}
