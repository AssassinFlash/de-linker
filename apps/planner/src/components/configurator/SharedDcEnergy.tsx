import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { DraftStore } from "../../data/DraftStore.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import {
	sameEnergyReportInputs,
	sharedDcReportRun,
} from "../../data/configuratorReportSources.ts";
import type { ReportOptions } from "../../data/planningReport.ts";
import {
	readRun,
	runPending,
	type RunSummary,
	type TaskKind,
} from "../../data/planningProtocol.ts";
import {
	ApiError,
	type JsonObject,
	type Project,
	type Session,
} from "../../data/protocol.ts";
import { readProject } from "../../data/readProtocol.ts";
import { PV_TASK, WEATHER_TASK } from "../../data/readPreparationResult.ts";
import { readBrief } from "../../domain/brief.ts";
import { REFERENCE_CAPACITY } from "../../domain/dcEnergy.ts";
import { isDirty, sameJson, type Draft } from "../../domain/draft.ts";
import { invalidateEnergyReplay } from "../../domain/energyScenario.ts";
import {
	DC_PLANT_ENERGY_TASK,
	plantEnergyDraft,
	plantEnergyEquipment,
	plantEnergyInputs,
	type PlantEnergyDraft,
} from "../../domain/plantEnergy.ts";
import { sharedProfileRange } from "../../domain/profileCoverage.ts";
import {
	matchesProfileRole,
	readAsset,
	readPreview,
	readSelections,
	type ProfileRole,
} from "../../domain/profiles.ts";
import { readSolarSetup } from "../../domain/solarSetup.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { OwnedProfile } from "../OwnedProfile.tsx";
import { ProfileIntake } from "../ProfileIntake.tsx";
import { measurementLabel } from "../ProfileLabels.ts";
import { EnergyComparison } from "../energy/EnergyComparison.tsx";
import { EnergyError } from "../energy/EnergyError.tsx";
import { PlantEnergyForm } from "../energy/PlantEnergyForm.tsx";
import { PreparationResult } from "../energy/PreparationResult.tsx";
import { PvSetup } from "../energy/PvSetup.tsx";
import { RunBasis } from "../energy/RunBasis.tsx";
import { RunResult } from "../energy/RunResult.tsx";
import { WeatherSetup } from "../energy/WeatherSetup.tsx";

export type SharedDcTask =
	typeof DC_PLANT_ENERGY_TASK | typeof WEATHER_TASK | typeof PV_TASK;

type Section = "storage" | "initial" | "operation" | "sources" | "results";

export function SharedDcEnergy({
	draft,
	locale,
	client,
	session,
	store,
	disabled,
	active,
	edit,
	save,
	openEquipment,
	openDesign,
	onValidity,
	registerProfileGuard,
	recoveryScopes,
	recoveryChecking,
	recheck,
	runs,
	moreRuns,
	submitted,
	start,
	generateComparison,
	operationError,
}: {
	draft: Draft;
	locale: string;
	client: PlannerClient;
	session: Session;
	store: DraftStore;
	disabled: boolean;
	active: boolean;
	edit: (apply: (inputs: JsonObject) => JsonObject) => boolean;
	save: () => Promise<Project | null>;
	openEquipment: () => void;
	openDesign: () => void;
	onValidity: (valid: boolean) => void;
	registerProfileGuard: (guard: () => boolean) => void;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking: boolean;
	recheck: () => void;
	runs: readonly RunSummary[];
	moreRuns: (() => void) | undefined;
	submitted: { id: string; task: SharedDcTask } | null;
	start: (path: "runs/calculate" | "runs/weather" | "runs/pv") => void;
	generateComparison: (options: ReportOptions) => Promise<void>;
	operationError: unknown;
}) {
	const inputs = draft.history.current;
	const [section, setSection] = useState<Section>(() =>
		sharedDcReportRun(inputs) ? "results" : "storage",
	);
	const [formValid, setFormValid] = useState(true);
	const [weatherValid, setWeatherValid] = useState(true);
	const [pvValid, setPvValid] = useState(true);
	const valid = formValid && weatherValid && pvValid;
	useEffect(() => onValidity(valid), [valid, onValidity]);
	const [sourceEditor, setSourceEditor] = useState<"weather" | "pv" | null>(
		null,
	);
	const [error, setError] = useState<unknown>(null);
	const [rangeBusy, setRangeBusy] = useState(false);
	const [chosen, setChosen] = useState<string | null>(null);
	const [adopting, setAdopting] = useState(false);
	const rangeRequest = useRef<AbortController | null>(null);
	const profileGuard = useRef<() => boolean>(() => true);
	const setProfileGuard = useCallback(
		(guard: () => boolean) => {
			profileGuard.current = guard;
			registerProfileGuard(guard);
		},
		[registerProfileGuard],
	);
	useEffect(() => () => rangeRequest.current?.abort(), [session.query_scope]);
	const equipment = plantEnergyEquipment(inputs);
	const setup = plantEnergyDraft(inputs, equipment);
	const configured =
		inputs.energy_plant_setup !== undefined &&
		setup.coupling === "plant_shared_dc";
	const supported =
		session.runtime.models.plant_dc_replay === DC_PLANT_ENERGY_TASK;
	const selected = readSelections(inputs.profile_selections).selected;
	const adopted = sharedDcReportRun(inputs);
	const dcRuns = runs.filter(
		({ task_kind }) => task_kind === DC_PLANT_ENERGY_TASK,
	);
	const runId =
		chosen ??
		(submitted?.task === DC_PLANT_ENERGY_TASK ? submitted.id : null) ??
		adopted ??
		dcRuns[0]?.id ??
		null;
	const current = () => client.isCurrentScope(session.query_scope);
	const blocked = disabled || adopting || rangeBusy;
	const read = useCallback(
		async (id: string, task: TaskKind, signal: AbortSignal) => {
			try {
				return readRun(
					await client.query(
						"runs/read",
						{ schema_version: 1, run_id: id },
						session.query_scope,
						signal,
					),
					draft.baseline.id,
					id,
					task,
				);
			} catch (cause) {
				if (
					cause instanceof ApiError &&
					([401, 403].includes(cause.status) ||
						cause.code === "session_changed")
				)
					recheck();
				throw cause;
			}
		},
		[client, draft.baseline.id, recheck, session.query_scope],
	);
	const result = useQuery({
		queryKey: [
			session.query_scope,
			"configurator-result",
			draft.baseline.id,
			DC_PLANT_ENERGY_TASK,
			runId,
		],
		enabled: active && configured && runId !== null && current(),
		queryFn: ({ signal }) => read(runId!, DC_PLANT_ENERGY_TASK, signal),
		retry: false,
		refetchIntervalInBackground: true,
		refetchInterval: ({ state }) =>
			state.data && runPending(state.data.state) ? 1000 : false,
	});
	const run = result.data;
	const sourceBasis = useQuery({
		queryKey: [
			session.query_scope,
			"shared-dc-run-revision",
			draft.baseline.id,
			run?.revision,
		],
		enabled:
			active &&
			current() &&
			run?.state === "succeeded" &&
			run.revision !== draft.baseline.revision,
		queryFn: async ({ signal }) => {
			const project = readProject(
				await client.query(
					"projects/read",
					{
						schema_version: 1,
						project_id: draft.baseline.id,
						revision: run!.revision,
					},
					session.query_scope,
					signal,
				),
			);
			if (
				project.id !== draft.baseline.id ||
				project.revision !== run!.revision
			)
				throw new ApiError(502, "run_source_mismatch");
			return project;
		},
		retry: false,
	});
	const basis =
		run?.revision === draft.baseline.revision
			? draft.baseline
			: sourceBasis.data;
	const compatible =
		run?.state === "succeeded" &&
		basis !== undefined &&
		basis.input_sha256 === run.manifest.input_sha256 &&
		sameEnergyReportInputs(basis.inputs, inputs);
	const preparationTask = sourceEditor === "weather" ? WEATHER_TASK : PV_TASK;
	const preparationId =
		submitted?.task === preparationTask
			? submitted.id
			: runs.find(({ task_kind }) => task_kind === preparationTask)?.id;
	const preparation = useQuery({
		queryKey: [
			session.query_scope,
			"configurator-result",
			draft.baseline.id,
			preparationTask,
			preparationId,
		],
		enabled:
			active &&
			section === "sources" &&
			sourceEditor !== null &&
			preparationId !== undefined &&
			current(),
		queryFn: ({ signal }) => read(preparationId!, preparationTask, signal),
		retry: false,
		refetchIntervalInBackground: true,
		refetchInterval: ({ state }) =>
			state.data && runPending(state.data.state) ? 1000 : false,
	});
	useEffect(() => {
		if (submitted?.task === DC_PLANT_ENERGY_TASK) {
			setChosen(submitted.id);
			setSection("results");
		}
	}, [submitted]);
	const change = (next: PlantEnergyDraft) => {
		setError(null);
		return edit((snapshot) => plantEnergyInputs(snapshot, next));
	};
	async function adopt() {
		if (!run || !basis || !compatible || blocked) return;
		setAdopting(true);
		try {
			if (
				!edit((snapshot) => {
					if (!sameEnergyReportInputs(basis.inputs, snapshot))
						throw new ApiError(409, "scenario_changed");
					return { ...snapshot, shared_dc_energy_run_id: run.id };
				})
			)
				throw new ApiError(409, "scenario_changed");
			await save();
		} catch (cause) {
			if (current()) setError(cause);
		} finally {
			if (current()) setAdopting(false);
		}
	}
	const requiresRoof =
		setup.units.some((unit) => unit.pv_dc_input_unused === false) ||
		Boolean(setup.ac_pv_converter_ids?.length);
	const roles: ProfileRole[] = [
		"gross_load",
		"pv_reference",
		"aux_ac",
		"pv_available_ac",
		...(setup.schedule.some((period) => period.mode === "outage")
			? ["critical_load" as const]
			: []),
	];
	async function useRange() {
		if (rangeRequest.current || blocked) return;
		const request = new AbortController();
		rangeRequest.current = request;
		setRangeBusy(true);
		setError(null);
		try {
			const ranges = await Promise.all(
				roles
					.filter(
						(role) =>
							selected[role] ||
							(role !== "pv_available_ac" &&
								(role !== "pv_reference" || requiresRoof)),
					)
					.map(async (role) => {
						const id = selected[role];
						if (!id) throw new ApiError(422, "scenario_profiles_required");
						const asset = readAsset(
							await client.query(
								"assets/read",
								{
									schema_version: 1,
									project_id: draft.baseline.id,
									asset_id: id,
								},
								session.query_scope,
								request.signal,
							),
							draft.baseline.id,
						);
						const preview = readPreview(
							await client.query(
								"profiles/preview",
								{
									schema_version: 1,
									project_id: draft.baseline.id,
									asset_id: id,
									offset: 0,
									page_size: 1,
								},
								session.query_scope,
								request.signal,
							),
							asset,
						);
						if (asset.id !== id || !matchesProfileRole(role, asset, preview))
							throw new ApiError(502, "profile_role_mismatch");
						return preview.summary;
					}),
			);
			const range = sharedProfileRange(ranges);
			if (request.signal.aborted || !current()) return;
			if (
				!edit((snapshot) => {
					if (
						!sameJson(snapshot.profile_selections, inputs.profile_selections) ||
						!sameJson(snapshot.energy_plant_setup, inputs.energy_plant_setup)
					)
						throw new ApiError(409, "scenario_changed");
					return plantEnergyInputs(snapshot, {
						...setup,
						schedule: setup.schedule.map((period, i) => ({
							...period,
							...(i === 0 ? { start_utc: range.start_utc } : {}),
							...(i === setup.schedule.length - 1
								? { end_utc: range.end_utc }
								: {}),
						})),
					});
				})
			)
				throw new ApiError(409, "scenario_changed");
		} catch (cause) {
			if (!request.signal.aborted && current()) setError(cause);
		} finally {
			rangeRequest.current = null;
			if (!request.signal.aborted && current()) setRangeBusy(false);
		}
	}
	const actionError =
		error ??
		operationError ??
		result.error ??
		sourceBasis.error ??
		preparation.error;
	const brief = inputs.brief === undefined ? null : readBrief(inputs.brief);
	const editorProps = {
		draft,
		edit,
		locale,
		disabled: blocked,
		actionsDisabled: blocked || !valid,
		onError: setError,
	};
	const readySources =
		selected.gross_load &&
		selected.aux_ac &&
		(!requiresRoof || selected.pv_reference) &&
		(!roles.includes("critical_load") || selected.critical_load);
	return (
		<section className="sc-card sc-shared-energy">
			<h2>{__("Shared DC energy flows", "linker-tools")}</h2>
			{!supported && (
				<Notice>
					{__(
						"Joint storage calculation is unavailable in this service version. Your equipment plan remains available.",
						"linker-tools",
					)}
				</Notice>
			)}
			{!configured ? (
				<button
					type="button"
					className="sc-button"
					disabled={blocked || !supported}
					onClick={() =>
						change({
							...setup,
							coupling: "plant_shared_dc",
							controller: "proportional_available_power_self_consumption_v1",
							aux_ac_kw: null,
						})
					}
				>
					{__("Set up shared DC energy flows", "linker-tools")}
				</button>
			) : (
				<>
					<div
						className="sc-energy-sections"
						role="group"
						aria-label={__("Shared DC energy flows", "linker-tools")}
					>
						{(
							[
								["sources", __("Interval sources", "linker-tools")],
								["storage", __("Storage", "linker-tools")],
								["initial", __("Starting state", "linker-tools")],
								["operation", __("Operation", "linker-tools")],
								["results", __("Saved calculations", "linker-tools")],
							] as const
						).map(([key, label]) => (
							<button
								key={key}
								type="button"
								className="sc-button"
								aria-pressed={section === key}
								disabled={!valid || adopting || rangeBusy}
								onClick={() => {
									if (profileGuard.current()) setSection(key);
								}}
							>
								{label}
							</button>
						))}
					</div>
					{Boolean(actionError) && <EnergyError error={actionError} />}
					{section === "sources" && (
						<div className="sc-energy-work">
							{roles.map((role) =>
								selected[role] ? (
									<details key={role}>
										<summary>{measurementLabel(role)}</summary>
										{active && (
											<OwnedProfile
												assetId={selected[role]!}
												projectId={draft.baseline.id}
												session={session}
												client={client}
												locale={locale}
												expectedRole={role}
												recheck={recheck}
											/>
										)}
										<button
											type="button"
											className="sc-button"
											disabled={blocked}
											onClick={() =>
												edit((snapshot) => {
													const next = {
														...readSelections(snapshot.profile_selections)
															.selected,
													};
													delete next[role];
													return {
														...invalidateEnergyReplay(snapshot),
														profile_selections: {
															schema_version: 1,
															selected: next,
														},
													};
												})
											}
										>
											{__("Remove draft selection", "linker-tools")}
										</button>
									</details>
								) : (
									<p key={role}>
										{measurementLabel(role)} ·{" "}
										{role === "pv_available_ac" ||
										(role === "pv_reference" && !requiresRoof)
											? __("Optional", "linker-tools")
											: __("Required", "linker-tools")}
									</p>
								),
							)}
							<p>
								{__(
									"Use the prepared roof PV source for DC groups. Upload a separate interval profile for any additional AC generation.",
									"linker-tools",
								)}
							</p>
							<fieldset disabled={blocked}>
								<ProfileIntake
									projectId={draft.baseline.id}
									client={client}
									session={session}
									store={store}
									recheck={recheck}
									locale={locale}
									timezone={brief?.site.timezone ?? null}
									annualKwh={brief?.annual_load.kwh ?? null}
									recoveryScopes={recoveryScopes}
									recoveryChecking={recoveryChecking}
									currentAssetIds={Object.values(selected)}
									confirmedAssetIds={Object.values(
										readSelections(draft.baseline.inputs.profile_selections)
											.selected,
									)}
									registerGuard={setProfileGuard}
									attach={async (id, role) =>
										edit((snapshot) => ({
											...invalidateEnergyReplay(snapshot),
											profile_selections: {
												schema_version: 1,
												selected: {
													...readSelections(snapshot.profile_selections)
														.selected,
													[role]: id,
												},
											},
										})) && Boolean(await save())
									}
								/>
							</fieldset>
							<div className="sc-actions">
								<button
									type="button"
									className="sc-button"
									disabled={!valid || blocked}
									aria-pressed={sourceEditor === "weather"}
									onClick={() =>
										setSourceEditor(
											sourceEditor === "weather" ? null : "weather",
										)
									}
								>
									{__("Weather source", "linker-tools")}
								</button>
								<button
									type="button"
									className="sc-button"
									disabled={!valid || blocked}
									aria-pressed={sourceEditor === "pv"}
									onClick={() =>
										setSourceEditor(sourceEditor === "pv" ? null : "pv")
									}
								>
									{__("Weather-based PV reference", "linker-tools")}
								</button>
							</div>
							{sourceEditor === "weather" && (
								<WeatherSetup
									{...editorProps}
									valid={weatherValid}
									onValidity={setWeatherValid}
									start={() => start("runs/weather")}
								/>
							)}
							{sourceEditor === "pv" && (
								<PvSetup
									{...editorProps}
									valid={pvValid}
									onValidity={setPvValid}
									start={() => start("runs/pv")}
									openDesign={openDesign}
								/>
							)}
							{sourceEditor && preparation.data && (
								<PreparationResult
									run={preparation.data}
									inputs={inputs}
									edit={edit}
									session={session}
									client={client}
									recheck={recheck}
									locale={locale}
									blocked={blocked || !valid}
									active={active}
								/>
							)}
						</div>
					)}
					{section !== "sources" && section !== "results" && (
						<PlantEnergyForm
							sharedDcOnly
							value={setup}
							plant={equipment}
							section={section}
							locale={locale}
							disabled={blocked}
							onChange={change}
							onValidity={setFormValid}
							useProfileRange={() => void useRange()}
							rangeBusy={rangeBusy}
							inputErrors={
								actionError instanceof ApiError
									? actionError.fields.filter((field) =>
											field.startsWith("energy_plant_setup.schedule["),
										)
									: []
							}
							openEquipment={openEquipment}
							client={client}
							scope={session.query_scope}
							active={active}
							converters={readSolarSetup(inputs).pv.converters.map(
								({ id }) => id,
							)}
							referenceCapacitySupported={
								session.runtime.models.capacity_reference === REFERENCE_CAPACITY
							}
						/>
					)}
					{section === "results" ? (
						<div className="sc-energy-work">
							{dcRuns.length > 0 && (
								<label className="sc-field">
									<span>{__("Saved calculation", "linker-tools")}</span>
									<select
										value={runId ?? ""}
										onChange={(event) => setChosen(event.currentTarget.value)}
									>
										{runId !== null &&
											!dcRuns.some((row) => row.id === runId) && (
												<option value={runId}>
													{__("Selected calculation", "linker-tools")}
												</option>
											)}
										{dcRuns.map((row) => (
											<option key={row.id} value={row.id}>
												{sprintf(
													__("Input revision %d", "linker-tools"),
													row.revision,
												)}{" "}
												·{" "}
												{new Intl.DateTimeFormat(locale, {
													dateStyle: "short",
													timeStyle: "medium",
												}).format(row.created_at * 1000)}
											</option>
										))}
									</select>
								</label>
							)}
							{moreRuns && (
								<button type="button" className="sc-button" onClick={moreRuns}>
									{__("Earlier calculations", "linker-tools")}
								</button>
							)}
							{run && (
								<>
									<RunResult
										run={run}
										locale={locale}
										dirty={isDirty(draft)}
										confirmedRevision={draft.baseline.revision}
									/>
									<RunBasis
										run={run}
										locale={locale}
										client={client}
										session={session}
										recheck={recheck}
									/>
									{compatible &&
										(adopted === run.id &&
										draft.baseline.inputs.shared_dc_energy_run_id === run.id ? (
											<p role="status">
												{__("Selected for the report", "linker-tools")}
											</p>
										) : (
											<button
												type="button"
												className="sc-button"
												disabled={blocked || !valid}
												onClick={() => void adopt()}
											>
												{__(
													"Use this calculation in the report",
													"linker-tools",
												)}
											</button>
										))}
								</>
							)}
							{dcRuns.filter((row) => row.state === "succeeded").length >=
								2 && (
								<EnergyComparison
									projectId={draft.baseline.id}
									runs={dcRuns}
									client={client}
									session={session}
									active={active}
									locale={locale}
									recheck={recheck}
									reportDisabled={
										blocked ||
										!valid ||
										isDirty(draft) ||
										!session.runtime.models.report
									}
									generateReport={generateComparison}
									openRun={setChosen}
								/>
							)}
						</div>
					) : (
						<button
							type="button"
							className="sc-button"
							disabled={blocked || !valid || !supported}
							onClick={() => {
								if (!profileGuard.current()) return;
								if (!readySources) {
									setSection("sources");
									setError(new ApiError(422, "scenario_profiles_required"));
									return;
								}
								setError(null);
								start("runs/calculate");
							}}
						>
							{__("Calculate energy flows", "linker-tools")}
						</button>
					)}
				</>
			)}
		</section>
	);
}
