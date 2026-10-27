import { useCallback, useEffect, useMemo, useState } from "react";
import type { Draft } from "../../domain/draft.ts";
import { isDirty } from "../../domain/draft.ts";
import type { JsonObject } from "../../data/protocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { useModuleTemplates } from "../../data/useModuleTemplates.ts";
import { matchesModule } from "../../domain/productModules.ts";
import {
	referencePrepared,
	referenceDraft,
	referenceInputs,
	referenceRoof,
	REFERENCE_DATABASES,
	REFERENCE_TECHNOLOGIES,
} from "../../domain/pvgisReference.ts";
import type { PvgisReferenceDraft } from "../../domain/pvgisReference.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { ScenarioNumber } from "./ScenarioNumber.tsx";
import { PvgisRoofFacts } from "./PvgisRoofFacts.tsx";

export function PvgisReferenceSetup({
	draft,
	edit,
	client,
	scope,
	active,
	locale,
	disabled,
	actionsDisabled,
	onValidity,
	start,
	openDesign,
	supported,
}: {
	draft: Draft;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	client: PlannerClient;
	scope: string;
	active: boolean;
	locale: string;
	disabled: boolean;
	actionsDisabled: boolean;
	onValidity: (valid: boolean) => void;
	start: () => void;
	openDesign: (() => void) | undefined;
	supported: boolean;
}) {
	const catalog = useModuleTemplates(client, scope, active),
		inputs = draft.history.current;
	const parsed = useMemo(() => {
		try {
			return referenceDraft(inputs);
		} catch {
			return null;
		}
	}, [inputs.pvgis_reference_setup, inputs.pvgis_reference]);
	const roof = useMemo(() => {
		try {
			return referenceRoof(inputs);
		} catch {
			return null;
		}
	}, [inputs.geometry]);
	const [invalid, setInvalid] = useState<readonly string[]>([]);
	const report = useCallback(
		(field: string, valid: boolean) =>
			setInvalid((previous) =>
				valid
					? previous.filter((key) => key !== field)
					: previous.includes(field)
						? previous
						: [...previous, field],
			),
		[],
	);
	useEffect(() => {
		onValidity(invalid.length === 0);
		return () => onValidity(true);
	}, [invalid, onValidity]);
	const currentModules =
		roof &&
		catalog.data &&
		!catalog.error &&
		!catalog.isFetching &&
		roof.arrays.every((array) => {
			const module = roof.geometry.module_specs.find(
				(m) => m.id === array.module_spec_id,
			);
			return (
				module &&
				catalog.data.some((template) => matchesModule(module, template))
			);
		});
	const complete = referencePrepared(inputs);
	const change = (
		patch: Partial<
			Pick<
				PvgisReferenceDraft,
				| "radiation_database"
				| "year"
				| "pv_technology"
				| "mounting_place"
				| "system_loss_percent"
				| "use_terrain_horizon"
				| "source_note"
			>
		>,
	) => {
		if (!disabled && parsed)
			edit((current) =>
				referenceInputs(current, { ...referenceDraft(current), ...patch }),
			);
	};
	return (
		<section className="lp-scenario-block">
			<h3>{__("PVGIS annual AC reference", "linker-tools")}</h3>
			<p>
				{__(
					"Estimate AC generation for a selected calendar year with JRC PVGIS 5.3. This method uses PV reference technology and a system loss setting; it does not model device-specific inverter behavior, nearby obstacles or shading between module rows. Electrical design and grid acceptance require separate assessment.",
					"linker-tools",
				)}
			</p>
			<p>
				{__(
					"The calculation sends the roof location, array power and orientation, and the model choices below to the European Commission's PVGIS service. Your project title and private note are not sent.",
					"linker-tools",
				)}
			</p>
			<p>
				{__(
					"ERA5 uses hourly averages. In this reference, each SARAH3 sample is treated as representative of its containing UTC hour.",
					"linker-tools",
				)}
			</p>
			{!supported && (
				<Notice>
					{__(
						"This calculation method is unavailable in the current service version. Saved inputs and earlier results remain available.",
						"linker-tools",
					)}
				</Notice>
			)}
			{!parsed ? (
				<Notice error>
					{__(
						"These reference settings cannot be edited in this version. Saved inputs and previous calculations remain available.",
						"linker-tools",
					)}
				</Notice>
			) : (
				<fieldset disabled={disabled}>
					<div className="lp-scenario-fields">
						<label className="lp-field">
							<span>{__("Radiation database", "linker-tools")}</span>
							<select
								value={parsed.radiation_database ?? ""}
								onChange={(e) =>
									change({
										radiation_database:
											(e.currentTarget
												.value as PvgisReferenceDraft["radiation_database"]) ||
											null,
									})
								}
							>
								<option value="">
									{__("Choose a database", "linker-tools")}
								</option>
								{REFERENCE_DATABASES.map((v) => (
									<option key={v} value={v}>
										{v}
									</option>
								))}
							</select>
						</label>
						<ScenarioNumber
							field="reference-year"
							label={__("Calendar year", "linker-tools")}
							value={parsed.year}
							unit=""
							locale={locale}
							min={1}
							max={9998}
							integer
							onChange={(year) => change({ year })}
							report={report}
						/>
						<label className="lp-field">
							<span>{__("PV reference technology", "linker-tools")}</span>
							<select
								value={parsed.pv_technology ?? ""}
								onChange={(e) =>
									change({
										pv_technology:
											(e.currentTarget
												.value as PvgisReferenceDraft["pv_technology"]) || null,
									})
								}
							>
								<option value="">
									{__("Choose a reference technology", "linker-tools")}
								</option>
								{REFERENCE_TECHNOLOGIES.map((v) => (
									<option key={v} value={v}>
										{v}
									</option>
								))}
							</select>
						</label>
						<label className="lp-field">
							<span>{__("PVGIS mounting type", "linker-tools")}</span>
							<select
								value={parsed.mounting_place ?? ""}
								onChange={(e) =>
									change({
										mounting_place:
											(e.currentTarget
												.value as PvgisReferenceDraft["mounting_place"]) ||
											null,
									})
								}
							>
								<option value="">
									{__("Choose a mounting type", "linker-tools")}
								</option>
								<option value="free">
									{__("Free-standing (free)", "linker-tools")}
								</option>
								<option value="building">
									{__("Building-integrated (building)", "linker-tools")}
								</option>
							</select>
						</label>
						<ScenarioNumber
							field="reference-loss"
							label={__("PVGIS system loss setting", "linker-tools")}
							value={parsed.system_loss_percent}
							unit="%"
							locale={locale}
							min={0}
							max={100}
							onChange={(system_loss_percent) =>
								change({ system_loss_percent })
							}
							report={report}
						/>
						<label className="lp-field">
							<span>{__("Terrain horizon", "linker-tools")}</span>
							<select
								value={
									parsed.use_terrain_horizon === null
										? ""
										: String(parsed.use_terrain_horizon)
								}
								onChange={(e) =>
									change({
										use_terrain_horizon:
											e.currentTarget.value === ""
												? null
												: e.currentTarget.value === "true",
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
						<label className="lp-field">
							<span>
								{__("Private assumption note (optional)", "linker-tools")}
							</span>
							<textarea
								rows={2}
								maxLength={4096}
								value={parsed.source_note ?? ""}
								onChange={(e) =>
									change({
										source_note: e.currentTarget.value.trim()
											? e.currentTarget.value
											: null,
									})
								}
							/>
						</label>
					</div>
				</fieldset>
			)}
			{roof ? (
				<div className="lp-scenario-sources">
					<PvgisRoofFacts geometry={roof.geometry} locale={locale} />
					<p>
						{__(
							"Array power and orientation are taken from the modules included in your roof design. You can change them in the roof design.",
							"linker-tools",
						)}
					</p>
				</div>
			) : (
				<Notice>
					{__(
						"Choose modules and add a location and north reference in the roof design before calculating.",
						"linker-tools",
					)}
				</Notice>
			)}
			{catalog.error && (
				<Notice error>
					<p>{__("Module data could not be loaded.", "linker-tools")}</p>
					<button
						type="button"
						className="lp-text-button"
						onClick={() => void catalog.refetch()}
					>
						{__("Reload module data", "linker-tools")}
					</button>
				</Notice>
			)}
			{openDesign && (
				<button type="button" className="lp-text-button" onClick={openDesign}>
					{__("Review roof design", "linker-tools")}
				</button>
			)}
			<div className="lp-energy-submit">
				<p>
					{isDirty(draft) || draft.pending
						? __(
								"Save the roof and reference choices before starting this calculation.",
								"linker-tools",
							)
						: sprintf(
								__(
									"PV generation uses saved input revision %d.",
									"linker-tools",
								),
								draft.baseline.revision,
							)}
				</p>
				<button
					type="button"
					className="lp-button"
					onClick={start}
					disabled={
						actionsDisabled ||
						!supported ||
						!complete ||
						!roof ||
						!currentModules ||
						invalid.length > 0 ||
						isDirty(draft) ||
						!!draft.pending ||
						!!draft.conflict
					}
				>
					{__("Calculate annual AC reference", "linker-tools")}
				</button>
			</div>
		</section>
	);
}
