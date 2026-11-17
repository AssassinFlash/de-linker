import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { geocodeAddress } from "../../data/googleMaps.ts";
import type { Brief } from "../../domain/brief.ts";
import type { Configuration } from "../../data/config.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { emptyBrief, readBrief } from "../../domain/brief.ts";
import { changeEnergyGoal, energyGoal } from "./EnergyDemand.tsx";
import { __ } from "../../i18n.ts";

export function ProjectDetails({
	inputs,
	config,
	disabled,
	edit,
	next,
	creation,
	existingEquipment,
}: {
	inputs: JsonObject;
	config: Pick<Configuration, "countries" | "locale" | "googleMapsApiKey">;
	disabled: boolean;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	next?: () => void;
	creation?: {
		title: string;
		changeTitle: (value: string) => void;
		locked: boolean;
		submitDisabled?: boolean;
		submitLabel?: string;
	};
	existingEquipment?: ReactNode;
}) {
	const brief =
		inputs.brief === undefined ? emptyBrief() : readBrief(inputs.brief);
	const [locating, setLocating] = useState(false);
	const [locationError, setLocationError] = useState(false);
	const live = useRef(true);
	useEffect(() => {
		live.current = true;
		return () => {
			live.current = false;
		};
	}, []);
	const country = brief.site.country_code;
	const address = brief.site.location_label;
	const mapKey = config.googleMapsApiKey;
	const fieldsDisabled = disabled || locating || Boolean(creation?.locked);
	async function locate() {
		if (fieldsDisabled || !mapKey || !country || !address.trim()) return;
		setLocating(true);
		setLocationError(false);
		try {
			const place = await geocodeAddress(
				mapKey,
				address,
				country,
				config.locale,
			);
			if (!live.current) return;
			if (!place) {
				setLocationError(true);
				return;
			}
			edit((current) => {
				const b =
					current.brief === undefined ? emptyBrief() : readBrief(current.brief);
				if (
					b.site.location_label !== address ||
					b.site.country_code !== country
				)
					return current;
				return {
					...current,
					brief: {
						...b,
						site: {
							...b.site,
							location_label: place.formattedAddress,
							latitude: place.lat,
							longitude: place.lng,
							postal_code: place.postcode,
							coordinate_basis: "user_entered",
						},
					},
				};
			});
		} catch {
			if (live.current) setLocationError(true);
		} finally {
			if (live.current) setLocating(false);
		}
	}
	function change(operation: (brief: Brief) => Brief) {
		edit((current) => ({
			...current,
			brief: operation(
				current.brief === undefined ? emptyBrief() : readBrief(current.brief),
			),
		}));
	}
	return (
		<>
			<header className="sc-section-head">
				<div>
					<h2>{__("What is the project?", "linker-tools")}</h2>
					<p className="sc-muted">
						{__(
							"Start with the location and what is already known.",
							"linker-tools",
						)}
					</p>
				</div>
			</header>
			<fieldset className="sc-card" disabled={fieldsDisabled}>
				<div className="sc-fields">
					{creation && (
						<label className="sc-field">
							<span>{__("Project name", "linker-tools")}</span>
							<input
								name="project_title"
								required
								maxLength={256}
								value={creation.title}
								readOnly={creation.locked}
								onChange={(event) =>
									creation.changeTitle(event.currentTarget.value)
								}
							/>
						</label>
					)}
					<label className="sc-field">
						<span>{__("Country", "linker-tools")}</span>
						<select
							name="country"
							value={country ?? ""}
							onChange={(e) => {
								const country_code = e.currentTarget.value || null;
								setLocationError(false);
								change((b) => ({
									...b,
									site: {
										...b.site,
										country_code,
										postal_code: null,
										latitude: null,
										longitude: null,
										coordinate_basis: "not_provided",
										timezone: null,
									},
								}));
							}}
						>
							<option value="">{__("Choose a country", "linker-tools")}</option>
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
						<span>{__("Town or site", "linker-tools")}</span>
						<input
							name="location_label"
							autoComplete="street-address"
							maxLength={4096}
							value={brief.site.location_label}
							onChange={(e) => {
								const location_label = e.currentTarget.value;
								setLocationError(false);
								change((b) => ({
									...b,
									site: {
										...b.site,
										location_label,
										postal_code: null,
										latitude: null,
										longitude: null,
										coordinate_basis: "not_provided",
										timezone: null,
									},
								}));
							}}
						/>
					</label>
					<label className="sc-field">
						<span>{__("Planned system", "linker-tools")}</span>
						<select
							name="system_scope"
							value={brief.system_scope ?? ""}
							onChange={(e) => {
								const system_scope = (e.currentTarget.value ||
									null) as Brief["system_scope"];
								edit((current) => {
									const b =
										current.brief === undefined
											? emptyBrief()
											: readBrief(current.brief);
									const amended = { ...current, brief: { ...b, system_scope } };
									const goal = energyGoal(amended);
									return goal &&
										(b.system_scope === "storage_only") !==
											(system_scope === "storage_only")
										? changeEnergyGoal(amended, goal)
										: amended;
								});
							}}
						>
							<option value="">{__("Choose an option", "linker-tools")}</option>
							<option value="new_pv_storage">
								{__("Solar and storage", "linker-tools")}
							</option>
							<option value="storage_addition">
								{__("Storage for existing PV", "linker-tools")}
							</option>
							<option value="pv_only">{__("Solar", "linker-tools")}</option>
							<option value="storage_only">
								{__("Storage", "linker-tools")}
							</option>
						</select>
					</label>
					<label className="sc-field">
						<span>{__("Site use", "linker-tools")}</span>
						<select
							value={brief.project_use ?? ""}
							onChange={(e) => {
								const project_use = (e.currentTarget.value ||
									null) as Brief["project_use"];
								change((b) => ({ ...b, project_use }));
							}}
						>
							<option value="">{__("Not specified", "linker-tools")}</option>
							<option value="residential">
								{__("Residential", "linker-tools")}
							</option>
							<option value="commercial">
								{__("Commercial", "linker-tools")}
							</option>
							<option value="industrial">
								{__("Industrial", "linker-tools")}
							</option>
						</select>
					</label>
					<label className="sc-field">
						<span>{__("Main purpose", "linker-tools")}</span>
						<select
							name="project_purpose"
							value={energyGoal(inputs)}
							onChange={(e) => {
								const goal = e.currentTarget.value as
									"self" | "backup" | "peak";
								if (goal) edit((current) => changeEnergyGoal(current, goal));
							}}
						>
							<option value="">{__("Choose an option", "linker-tools")}</option>
							<option value="self">
								{__("Use more solar on site", "linker-tools")}
							</option>
							<option value="backup">
								{__("Backup supply", "linker-tools")}
							</option>
							<option value="peak">
								{__("Reduce peak demand", "linker-tools")}
							</option>
						</select>
					</label>
				</div>
				{mapKey && brief.system_scope !== "storage_only" && (
					<div className="sc-actions">
						<button
							className="sc-button"
							type="button"
							disabled={!country || !address.trim()}
							onClick={() => void locate()}
						>
							{__("Find site coordinates", "linker-tools")}
						</button>
						{brief.site.latitude !== null && brief.site.longitude !== null && (
							<span>{__("Site coordinates found", "linker-tools")}</span>
						)}
					</div>
				)}
			</fieldset>
			{existingEquipment}
			{locationError && (
				<p role="alert">
					{__(
						"The location could not be found. Check the country and address, then try again.",
						"linker-tools",
					)}
				</p>
			)}
			{locating && (
				<p role="status">{__("Finding the site…", "linker-tools")}</p>
			)}
			<footer className="sc-footer">
				<span />
				<button
					className="sc-button sc-primary"
					type={creation ? "submit" : "button"}
					disabled={
						disabled ||
						locating ||
						creation?.submitDisabled ||
						(!creation?.locked &&
							(!brief.system_scope || (creation && !creation.title.trim())))
					}
					onClick={next}
				>
					{creation?.submitLabel ??
						(brief.system_scope === "storage_only"
							? __("Continue with storage", "linker-tools")
							: __("Continue with solar", "linker-tools"))}
				</button>
			</footer>
		</>
	);
}
