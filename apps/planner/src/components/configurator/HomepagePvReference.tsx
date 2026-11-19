import { readBrief } from "../../domain/brief.ts";
import type { Brief } from "../../domain/brief.ts";
import type { JsonObject } from "../../data/protocol.ts";
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

export function isHomepagePvReferenceReady(inputs: JsonObject, brief: Brief) {
	return (
		!homepagePvReferenceAvailable(inputs, brief) ||
		referenceDraft(inputs).model !== KNOWN_PV_MODEL ||
		(brief.site.latitude !== null &&
			brief.site.longitude !== null &&
			brief.site.coordinate_basis === "user_entered" &&
			referencePrepared(inputs))
	);
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
	edit,
}: {
	inputs: JsonObject;
	brief: Brief;
	power: number | null;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
}) {
	const reference = referenceDraft(inputs);
	const array =
		reference.model === KNOWN_PV_MODEL ? reference.arrays?.[0] : undefined;
	function toggle(enabled: boolean) {
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
					{number(
						"latitude",
						__("Latitude", "linker-tools"),
						brief.site.latitude,
						-90,
						90,
						(value) => coordinate("latitude", value),
					)}
					{number(
						"longitude",
						__("Longitude", "linker-tools"),
						brief.site.longitude,
						-180,
						180,
						(value) => coordinate("longitude", value),
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
