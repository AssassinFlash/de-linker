import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { geocodeAddress } from "../../data/googleMaps.ts";
import type { Brief } from "../../domain/brief.ts";
import type { Configuration } from "../../data/config.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { emptyBrief, readBrief } from "../../domain/brief.ts";
import {
	changeEnergyGoal,
	energyGoal,
	type EnergyGoal,
} from "./EnergyDemand.tsx";
import { changeEquipment, equipmentDraft } from "../../domain/equipment.ts";
import type { EquipmentUse } from "../../domain/equipment.ts";
import {
	hasPlant,
	plantInputs,
	readPlantDraft,
} from "../../domain/equipmentPlant.ts";
import { invalidateEnergyReplay } from "../../domain/energyScenario.ts";
import { __ } from "../../i18n.ts";

const solarDemand = {
	required_usable_kwh: null,
	required_discharge_ac_kw: null,
	operating_mode: "grid_connected",
} as const;

function hasStorageDemand(setup: JsonObject): boolean {
	return (
		setup.operating_mode === "backup" ||
		[setup.required_usable_kwh, setup.required_discharge_ac_kw].some(
			(value) => typeof value === "number" && value > 0,
		)
	);
}

function hasBattery(setup: JsonObject): boolean {
	const use = setup.equipment_use as EquipmentUse | null | undefined;
	return (
		setup.battery_product_id !== null || (use != null && use.battery !== "new")
	);
}

export function hasStorageToExclude(inputs: JsonObject): boolean {
	if (energyGoal(inputs) === "backup" || inputs.equipment_demand !== undefined)
		return true;
	if (!hasPlant(inputs)) {
		const setup = equipmentDraft(inputs);
		return hasBattery(setup) || hasStorageDemand(setup);
	}
	const plant = readPlantDraft(inputs);
	return (
		hasStorageDemand(plant.requirements) ||
		plant.units.some(({ inputs }) => {
			const setup = equipmentDraft(inputs);
			return hasBattery(setup) || hasStorageDemand(setup);
		})
	);
}

function withoutBattery(inputs: JsonObject): JsonObject {
	const use = equipmentDraft(inputs).equipment_use as
		EquipmentUse | null | undefined;
	return changeEquipment(inputs, {
		...solarDemand,
		battery_product_id: null,
		modules_per_stack: null,
		parallel_stacks: null,
		equipment_use: use ? { ...use, battery: "new" } : null,
	});
}

export function ProjectDetails({
	inputs,
	config,
	disabled,
	edit,
	next,
	creation,
	existingEquipment,
	equipmentFirst = false,
	demand,
	roofAction,
	profile,
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
		comparison?: boolean;
		preliminary?: boolean;
		submitDisabled?: boolean;
		submitLabel?: string;
		returnToComparison?: () => void;
		comparisonDisabled?: boolean;
	};
	existingEquipment?: ReactNode;
	equipmentFirst?: boolean;
	demand?: ReactNode;
	roofAction?: ReactNode;
	profile?: ReactNode;
}) {
	const brief =
		inputs.brief === undefined ? emptyBrief() : readBrief(inputs.brief);
	const [pendingScope, setPendingScope] = useState<
		"pv_only" | "storage_only" | null
	>(null);
	const solarConflict =
		brief.system_scope === "pv_only" && hasStorageToExclude(inputs);
	const [locating, setLocating] = useState(false);
	const [locationError, setLocationError] = useState(false);
	const live = useRef(true);
	const heading = useRef<HTMLHeadingElement>(null);
	useEffect(() => {
		live.current = true;
		if (location.hash === "#sc-project")
			heading.current?.focus({ preventScroll: true });
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
					...invalidateEnergyReplay(current),
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
	function changeScope(system_scope: Brief["system_scope"]) {
		setPendingScope(null);
		edit((current) => {
			const b =
				current.brief === undefined ? emptyBrief() : readBrief(current.brief);
			const amended: Record<string, JsonObject[string]> = {
				...current,
				brief: { ...b, system_scope },
			};
			if (system_scope === "storage_only") {
				delete amended.pv_string_plan;
				delete amended.pv_plant_string_plan;
				delete amended.shared_dc_energy_run_id;
			}
			const goal = energyGoal(amended);
			if (system_scope === "pv_only") {
				const { equipment_demand: _demand, ...solar } = goal
					? changeEnergyGoal(amended, goal === "backup" ? "self" : goal)
					: amended;
				if (!hasPlant(solar)) return withoutBattery(solar);
				const plant = readPlantDraft(solar);
				return plantInputs(solar, {
					...plant,
					requirements: { ...plant.requirements, ...solarDemand },
					units: plant.units.map((unit) => ({
						...unit,
						inputs: withoutBattery(unit.inputs),
					})),
				});
			}
			return goal &&
				(b.system_scope === "storage_only") !==
					(system_scope === "storage_only")
				? changeEnergyGoal(amended, goal)
				: amended;
		});
	}
	function change(operation: (brief: Brief) => Brief) {
		edit((current) => ({
			...current,
			brief: operation(
				current.brief === undefined ? emptyBrief() : readBrief(current.brief),
			),
		}));
	}
	function changeLocation(
		patch: Partial<Pick<Brief["site"], "country_code" | "location_label">>,
	) {
		setLocationError(false);
		edit((current) => {
			const before =
				current.brief === undefined ? emptyBrief() : readBrief(current.brief);
			return {
				...invalidateEnergyReplay(current),
				brief: {
					...before,
					site: {
						...before.site,
						...patch,
						postal_code: null,
						latitude: null,
						longitude: null,
						coordinate_basis: "not_provided",
						timezone: null,
					},
				},
			};
		});
	}
	return (
		<>
			{(!creation?.comparison || creation.preliminary) && (
				<header className="sc-section-head">
					<div>
						<h2 ref={heading} tabIndex={-1}>
							{__("What is the project?", "linker-tools")}
						</h2>
						<p className="sc-muted">
							{__(
								"Start with the location and what is already known.",
								"linker-tools",
							)}
						</p>
					</div>
				</header>
			)}
			<fieldset className="sc-card" disabled={fieldsDisabled}>
				{equipmentFirst && existingEquipment}
				<div className="sc-fields">
					{creation && (
						<label className="sc-field">
							<span>{__("Project name", "linker-tools")}</span>
							<input
								name="project_title"
								required={!creation.preliminary}
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
							onChange={(e) =>
								changeLocation({ country_code: e.currentTarget.value || null })
							}
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
							onChange={(e) =>
								changeLocation({ location_label: e.currentTarget.value })
							}
						/>
					</label>
					<label className="sc-field">
						<span>{__("Planned system", "linker-tools")}</span>
						<select
							name="system_scope"
							required={creation?.comparison && !creation.preliminary}
							value={brief.system_scope ?? ""}
							onChange={(e) => {
								const system_scope = (e.currentTarget.value ||
									null) as Brief["system_scope"];
								if (
									(system_scope === "pv_only" && hasStorageToExclude(inputs)) ||
									(system_scope === "storage_only" &&
										(inputs.pv_string_plan != null ||
											inputs.pv_plant_string_plan != null))
								)
									setPendingScope(system_scope);
								else changeScope(system_scope);
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
							required={creation?.comparison && !creation.preliminary}
							value={energyGoal(inputs)}
							onChange={(e) => {
								const goal = e.currentTarget.value as EnergyGoal;
								edit((current) => changeEnergyGoal(current, goal));
							}}
						>
							<option value="">{__("Choose an option", "linker-tools")}</option>
							<option value="self">
								{__("Use more solar on site", "linker-tools")}
							</option>
							<option
								value="backup"
								disabled={brief.system_scope === "pv_only"}
							>
								{__("Backup supply", "linker-tools")}
							</option>
							<option value="peak">
								{__("Reduce peak demand", "linker-tools")}
							</option>
						</select>
					</label>
					{roofAction}
					{mapKey &&
						!creation?.comparison &&
						brief.system_scope !== "storage_only" && (
							<div className="sc-field-wide">
								<div className="sc-actions">
									<button
										className="sc-button"
										type="button"
										disabled={!country || !address.trim()}
										onClick={() => void locate()}
									>
										{__("Find site coordinates", "linker-tools")}
									</button>
									<span role="status">
										{locating
											? __("Finding the site…", "linker-tools")
											: brief.site.latitude !== null &&
												  brief.site.longitude !== null
												? __("Site coordinates found", "linker-tools")
												: ""}
									</span>
								</div>
								{locationError && (
									<p role="alert">
										{__(
											"The location could not be found. Check the country and address, then try again.",
											"linker-tools",
										)}
									</p>
								)}
							</div>
						)}
				</div>
				{demand}
				{(pendingScope || solarConflict) && (
					<div>
						<p>
							{pendingScope === "storage_only"
								? __(
										"Switching to storage removes the PV wiring plan from this project version.",
										"linker-tools",
									)
								: __(
										"Switching to solar excludes battery equipment and storage requirements, including backup supply.",
										"linker-tools",
									)}
						</p>
						<div className="sc-actions">
							<button
								type="button"
								className="sc-button"
								onClick={() => changeScope(pendingScope ?? "pv_only")}
							>
								{pendingScope === "storage_only"
									? __("Switch to storage and remove PV wiring", "linker-tools")
									: __("Switch to solar and exclude storage", "linker-tools")}
							</button>
							{(pendingScope === "storage_only" || !solarConflict) && (
								<button
									type="button"
									className="sc-button"
									onClick={() => setPendingScope(null)}
								>
									{__("Keep current system", "linker-tools")}
								</button>
							)}
						</div>
					</div>
				)}
				{!equipmentFirst && existingEquipment}
			</fieldset>
			{profile}
			<footer className="sc-footer">
				{creation?.returnToComparison ? (
					<button
						type="button"
						className="sc-button"
						disabled={
							fieldsDisabled ||
							pendingScope !== null ||
							creation.comparisonDisabled
						}
						onClick={creation.returnToComparison}
					>
						{__("Compare options", "linker-tools")}
					</button>
				) : (
					<span />
				)}
				<button
					className="sc-button sc-primary"
					type={creation ? "submit" : "button"}
					disabled={
						disabled ||
						locating ||
						pendingScope !== null ||
						solarConflict ||
						creation?.submitDisabled ||
						(!creation?.locked &&
							!creation?.preliminary &&
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
