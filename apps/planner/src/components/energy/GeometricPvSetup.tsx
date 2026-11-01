import { useCallback, useEffect, useMemo, useState } from "react";
import type { Draft } from "../../domain/draft.ts";
import { isDirty, sameJson } from "../../domain/draft.ts";
import type { JsonObject, Session } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { useRetainedWeather } from "../../data/useRetainedWeather.ts";
import { useModuleTemplates } from "../../data/useModuleTemplates.ts";
import { matchesModule } from "../../domain/productModules.ts";
import { referenceRoof } from "../../domain/pvgisReference.ts";
import { panelPoses } from "../../domain/panelPoses.ts";
import {
	GEOMETRIC_PV_TASK,
	compileGeometricPv,
	GEOMETRIC_PV_MODEL,
	GEOMETRIC_PV_MODEL_V1,
	GEOMETRIC_PV_MODEL_SERIES,
	GEOMETRIC_PV_SERIES_ELECTRICAL,
	geometricDiffuseSampleUpperBound,
	geometricPvDraft,
	geometricPvInputs,
	readGeometricPvLimits,
	removeGeometricPv,
} from "../../domain/geometricPv.ts";
import type { GeometricPvDraft } from "../../domain/geometricPv.ts";
import { PvForm } from "./PvForm.tsx";
import { ScenarioNumber } from "./ScenarioNumber.tsx";
import { Notice } from "../Notice.tsx";
import { __, sprintf } from "../../i18n.ts";

export function GeometricPvSetup({
	draft,
	edit,
	session,
	client,
	active,
	locale,
	disabled,
	actionsDisabled,
	onValidity,
	start,
	openDesign,
	openWeather,
}: {
	draft: Draft;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	session: Session;
	client: PlannerClient;
	active: boolean;
	locale: string;
	disabled: boolean;
	actionsDisabled: boolean;
	onValidity: (valid: boolean) => void;
	start: () => void;
	openDesign: (() => void) | undefined;
	openWeather: () => void;
}) {
	const inputs = draft.history.current,
		scope = session.query_scope,
		owned = client.isCurrentScope(scope);
	const parsed = useMemo(() => {
		try {
			return geometricPvDraft(inputs);
		} catch {
			return null;
		}
	}, [
		inputs.geometric_pv_preparation,
		inputs.solar_setup,
		inputs.pv_generation,
	]);
	const roof = useMemo(() => {
		try {
			return referenceRoof(inputs);
		} catch {
			return null;
		}
	}, [inputs.geometry]);
	const limits = useMemo(() => {
		try {
			return readGeometricPvLimits(
				session.runtime.limits.geometric_pv_generation,
			);
		} catch {
			return null;
		}
	}, [session.runtime]);
	const supported =
		session.runtime.models.geometric_pv_generation === GEOMETRIC_PV_TASK &&
		limits !== null;
	const weather = useRetainedWeather(
		client,
		session,
		draft.baseline.id,
		parsed?.weather_asset_id ?? null,
		active && supported,
	);
	const catalog = useModuleTemplates(client, scope, active);
	const [fieldsValid, setFieldsValid] = useState(true),
		[invalidSampling, setInvalidSampling] = useState<readonly string[]>([]);
	const report = useCallback(
		(field: string, valid: boolean) =>
			setInvalidSampling((previous) =>
				valid
					? previous.filter((key) => key !== field)
					: previous.includes(field)
						? previous
						: [...previous, field],
			),
		[],
	);
	let complete = false;
	try {
		if (parsed && roof) {
			compileGeometricPv(parsed, inputs.geometry);
			complete = true;
		}
	} catch {
		/* Incomplete choices remain in the recoverable draft. */
	}
	const valid =
		fieldsValid &&
		invalidSampling.length === 0 &&
		(inputs.geometric_pv_preparation === undefined || complete);
	useEffect(() => {
		onValidity(valid);
		return () => onValidity(true);
	}, [valid, onValidity]);
	const currentModules =
		!!roof &&
		!!parsed &&
		!!catalog.data &&
		!catalog.error &&
		!catalog.isFetching &&
		parsed.parameters.modules.every((module) => {
			const specification = roof.geometry.module_specs.find(
					(item) => item.id === module.module_spec_id,
				),
				template =
					specification &&
					catalog.data.find((item) => matchesModule(specification, item));
			return (
				!!template &&
				sameJson(module, {
					...template.parameters,
					module_spec_id: module.module_spec_id,
				})
			);
		});
	const binding = owned ? weather.binding.data : undefined,
		requestMatches =
			inputs.weather_acquisition === undefined ||
			(!!binding &&
				sameJson(
					readObject(inputs.weather_acquisition).request,
					binding.metadata.weather_request,
				) &&
				sameJson(
					readObject(inputs.weather_acquisition).interpretation,
					binding.metadata.weather_interpretation,
				)),
		locationMatches =
			!!roof &&
			!!binding &&
			binding.weather.latitude_deg ===
				roof.geometry.coordinate_system.anchor?.latitude_deg &&
			binding.weather.longitude_deg ===
				roof.geometry.coordinate_system.anchor?.longitude_deg,
		rows = binding ? Number(binding.weather.interval_count) : null,
		moduleSteps =
			roof && rows
				? panelPoses(roof.geometry).filter((pose) => pose.included).length *
					rows
				: null,
		samples =
			moduleSteps !== null && parsed && complete
				? moduleSteps *
						(Number(parsed.sampling.coarse_cells_per_edge) ** 2 +
							Number(parsed.sampling.fine_cells_per_edge) ** 2) +
					(parsed.model !== GEOMETRIC_PV_MODEL_V1
						? geometricDiffuseSampleUpperBound(
								moduleSteps / Number(rows),
								Number(parsed.sampling.fine_cells_per_edge),
							)
						: 0)
				: null,
		withinBudget =
			limits &&
			moduleSteps !== null &&
			samples !== null &&
			Number.isSafeInteger(moduleSteps) &&
			moduleSteps <= limits.max_module_steps &&
			Number.isSafeInteger(samples) &&
			samples <= limits.max_samples;
	const change = (next: GeometricPvDraft) => {
		if (!disabled && owned) edit((current) => geometricPvInputs(current, next));
	};
	if (!owned)
		return (
			<Notice>
				{__(
					"The saved result is hidden until this session is verified.",
					"linker-tools",
				)}
			</Notice>
		);
	return (
		<section className="lp-scenario-block">
			<h3>{__("PV reference with roof shading", "linker-tools")}</h3>
			<p>
				{parsed?.model === GEOMETRIC_PV_MODEL_V1
					? __(
							"Estimate available AC generation across the complete retained weather year using the declared roof, obstacle volumes and included modules. Geometric shading reduces direct sunlight at each module; sky and ground diffuse light remain unobstructed reference components.",
							"linker-tools",
						)
					: __(
							"Available AC generation for the complete retained weather year is calculated from the declared roof, obstacle volumes and included modules. With the Perez transposition, geometric shading reduces direct sunlight and the isotropic, circumsolar, horizon and ground components at each module. A negative Perez horizon correction stays in the calculation. This result does not establish complete shading accuracy, actual inverter tracking, or equipment or country approval.",
							"linker-tools",
						)}
			</p>
			<p>
				{parsed?.model === GEOMETRIC_PV_MODEL_SERIES
					? __(
							"Each declared string uses a common current and the selected inverter tracker window. The calculation models uniform irradiance within each module; bypass diodes, parallel strings and actual inverter tracking are not assessed.",
							"linker-tools",
						)
					: __(
							"Module temperature follows the declared SAPM model using mean irradiance across each module. Electrical response is uniform per module, with independent maximum-power outputs summed before the declared conversion groups. Cell substrings, bypass diodes, string I–V curves and actual inverter tracking are not modelled.",
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
			{!roof && (
				<Notice>
					<p>
						{__(
							"A georeferenced roof with a defined north direction and current module data is required. Review the roof design and its module selection.",
							"linker-tools",
						)}
					</p>
					<button type="button" className="lp-text-button" onClick={openDesign}>
						{__("Open roof design", "linker-tools")}
					</button>
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
				<>
					<fieldset disabled={disabled}>
						<label className="lp-field">
							<span>{__("Electrical scenario", "linker-tools")}</span>
							<select
								value={
									parsed.model === GEOMETRIC_PV_MODEL_SERIES
										? "series"
										: "independent"
								}
								onChange={(event) => {
									const series = event.currentTarget.value === "series";
									change({
										...parsed,
										model: series
											? GEOMETRIC_PV_MODEL_SERIES
											: GEOMETRIC_PV_MODEL,
										diffuse_policy:
											"cosine_weighted_perez_component_visibility_v1",
										electrical_policy: series
											? GEOMETRIC_PV_SERIES_ELECTRICAL
											: "uniform_module_pvwatts_independent_mpp_sum_v1",
										parameters: {
											...parsed.parameters,
											converters: parsed.parameters.converters.map((group) => ({
												...group,
												input_assumption: series
													? "one_string_per_tracker_independent_mpp_sum"
													: "independent_mppt_array_mpp_sum",
											})),
										},
									});
								}}
							>
								<option value="independent">
									{__("Independent module reference", "linker-tools")}
								</option>
								<option value="series">
									{__("Series string reference", "linker-tools")}
								</option>
							</select>
						</label>
						{parsed.model === GEOMETRIC_PV_MODEL_SERIES && (
							<p>
								{__(
									"Save one selected inverter and assign every included roof module to strings, with one string per tracker. Each string must belong to one roof array.",
									"linker-tools",
								)}
							</p>
						)}
						<label className="lp-field">
							<span>{__("Project weather source", "linker-tools")}</span>
							<select
								value={parsed.weather_asset_id ?? ""}
								onChange={(event) =>
									change({
										...parsed,
										weather_asset_id: event.currentTarget.value || null,
									})
								}
							>
								<option value="">
									{__("Choose a weather source", "linker-tools")}
								</option>
								{parsed.weather_asset_id && !weather.selected && (
									<option value={parsed.weather_asset_id}>
										{__("Saved weather source", "linker-tools")} ·{" "}
										{parsed.weather_asset_id.slice(0, 8)}
									</option>
								)}
								{weather.assets.map((asset) => (
									<option key={asset.asset_id} value={asset.asset_id}>
										{asset.label} · {asset.synthetic_year}
									</option>
								))}
							</select>
						</label>
						{weather.sources.hasNextPage && (
							<button
								type="button"
								className="lp-text-button"
								disabled={weather.sources.isFetchingNextPage}
								onClick={() => void weather.sources.fetchNextPage()}
							>
								{__("More weather sources", "linker-tools")}
							</button>
						)}
						<div className="lp-geometry-fields">
							{(["coarse_cells_per_edge", "fine_cells_per_edge"] as const).map(
								(key) => (
									<ScenarioNumber
										key={key}
										field={key}
										label={
											key === "coarse_cells_per_edge"
												? __(
														"Coarse grid cells per module edge",
														"linker-tools",
													)
												: __("Fine grid cells per module edge", "linker-tools")
										}
										value={parsed.sampling[key]}
										unit=""
										locale={locale}
										min={1}
										integer
										report={report}
										onChange={(value) =>
											change({
												...parsed,
												sampling: { ...parsed.sampling, [key]: value },
											})
										}
									/>
								),
							)}
						</div>
						<p>
							{__(
								"Both equal-area midpoint grids must be specified. The fine grid must have more cells per edge. Their observed difference is not an error bound.",
								"linker-tools",
							)}
						</p>
					</fieldset>
					{(weather.sources.error || weather.binding.error) && (
						<Notice error>
							<p>
								{__(
									"The selected weather source could not be verified. Review the source selection before calculating.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="lp-text-button"
								onClick={() => {
									void weather.sources.refetch();
									if (parsed.weather_asset_id) void weather.binding.refetch();
								}}
							>
								{__("Try again", "linker-tools")}
							</button>
						</Notice>
					)}
					{weather.sources.isSuccess &&
						!weather.assets.length &&
						!parsed.weather_asset_id && (
							<Notice>
								<p>
									{__(
										"This project has no retained weather source for this method. Prepare weather data first.",
										"linker-tools",
									)}
								</p>
								<button
									type="button"
									className="lp-text-button"
									onClick={openWeather}
								>
									{__("Open weather preparation", "linker-tools")}
								</button>
							</Notice>
						)}
					{binding && (!locationMatches || !requestMatches) && (
						<Notice error>
							{__(
								"The retained weather source must match the saved roof location and weather interpretation. Review the source or roof settings before calculating.",
								"linker-tools",
							)}
						</Notice>
					)}
					{binding && (
						<p>
							{sprintf(
								__(
									"All %s retained weather intervals are calculated. The selected rows in the geometric visibility diagnostic do not restrict this PV profile.",
									"linker-tools",
								),
								Number(rows).toLocaleString(locale),
							)}
						</p>
					)}
					{samples !== null && moduleSteps !== null && limits && (
						<p>
							{sprintf(
								__(
									"Requested module intervals: %s / %s. Maximum midpoint samples: %s / %s.",
									"linker-tools",
								),
								moduleSteps.toLocaleString(locale),
								limits.max_module_steps.toLocaleString(locale),
								samples.toLocaleString(locale),
								limits.max_samples.toLocaleString(locale),
							)}
						</p>
					)}
					{samples !== null && !withinBudget && (
						<Notice error>
							{__(
								"The complete weather year exceeds this service's calculation budget at the selected sampling resolution. Reduce the sampling resolution or roof scope; the calculation does not silently omit weather intervals.",
								"linker-tools",
							)}
						</Notice>
					)}
					{roof && (
						<PvForm
							value={parsed.parameters}
							geometry={roof.geometry}
							arrays={roof.arrays}
							locale={locale}
							disabled={disabled}
							valid={fieldsValid && invalidSampling.length === 0}
							onValidity={setFieldsValid}
							onChange={(parameters) =>
								change({
									...parsed,
									parameters: {
										...parameters,
										converters: parameters.converters.map((group) => ({
											...group,
											input_assumption:
												parsed.model === GEOMETRIC_PV_MODEL_SERIES
													? "one_string_per_tracker_independent_mpp_sum"
													: "independent_mppt_array_mpp_sum",
										})),
									},
								})
							}
							moduleTemplates={
								catalog.error || catalog.isFetching ? undefined : catalog.data
							}
							geometric
							series={parsed.model === GEOMETRIC_PV_MODEL_SERIES}
						/>
					)}
				</>
			)}
			{inputs.geometric_pv_preparation !== undefined && (
				<button
					type="button"
					className="lp-text-button"
					disabled={disabled}
					onClick={() => {
						if (!edit(removeGeometricPv)) return;
						setFieldsValid(true);
						setInvalidSampling([]);
					}}
				>
					{__("Remove this PV reference setup from the draft", "linker-tools")}
				</button>
			)}
			{!valid && (
				<Notice>
					{__(
						"The weather source, both sampling grids and all PV parameters must be complete before saving this setup.",
						"linker-tools",
					)}
				</Notice>
			)}
			<p>
				{__(
					"This method creates a separate AC profile. Earlier unshaded results stay in the calculation history. Selecting the new profile for energy calculation is an explicit action after preparation.",
					"linker-tools",
				)}
			</p>
			{isDirty(draft) && (
				<Notice>
					{__(
						"The roof layout, PV model and weather selection must be recorded with Save project before PV generation can start.",
						"linker-tools",
					)}
				</Notice>
			)}
			<button
				type="button"
				className="lp-button"
				disabled={
					actionsDisabled ||
					!supported ||
					!valid ||
					!complete ||
					!currentModules ||
					!binding ||
					!locationMatches ||
					!requestMatches ||
					!withinBudget ||
					isDirty(draft) ||
					!!draft.pending ||
					!!draft.conflict
				}
				onClick={start}
			>
				{__("Calculate saved PV reference with roof shading", "linker-tools")}
			</button>
		</section>
	);
}
