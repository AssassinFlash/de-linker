import { Icon } from "../Icon.tsx";
import { attachGrossLoad } from "../../domain/grossLoad.ts";
import { useEffect, useMemo, useRef, useState } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { ApiError } from "../../data/protocol.ts";
import { isPreMutationInputRefusal } from "../../data/inputRefusal.ts";
import type { JsonObject, JsonRpcPath, Session } from "../../data/protocol.ts";
import { emptyBrief, readBrief } from "../../domain/brief.ts";
import { changeEquipment, equipmentDraft } from "../../domain/equipment.ts";
import {
	hasPlant,
	plantInputs,
	readPlantDraft,
} from "../../domain/equipmentPlant.ts";
import {
	emptyScenario,
	isStorageOnly,
	readScenarioDraft,
} from "../../domain/energyScenario.ts";
import {
	fileBase64,
	readAsset,
	readInspection,
	readPreview,
	readProfileImport,
	readSelections,
} from "../../domain/profiles.ts";
import type { CsvInspection, ProfilePreview } from "../../domain/profiles.ts";
import { KNOWN_PV_MODEL, referenceDraft } from "../../domain/pvgisReference.ts";
import { emptyMapping, mappedProfile } from "../ProfileMapping.tsx";
import { issueLabel } from "../ProfileLabels.ts";
import { NumberField } from "../NumberField.tsx";
import { ProfileCurve, profileDateFormat } from "../ProfileCurve.tsx";
import { revealActionResult } from "../revealActionResult.ts";
import { __ } from "../../i18n.ts";
import { retainsUnverifiedInverter } from "./ProjectEquipment.tsx";

export function changeDemandEquipment(
	inputs: JsonObject,
	patch: JsonObject,
): JsonObject {
	if (!hasPlant(inputs)) return changeEquipment(inputs, patch);
	const plant = readPlantDraft(inputs);
	return plantInputs(inputs, {
		...plant,
		requirements: { ...plant.requirements, ...patch },
	});
}

export type EnergyGoal = "" | "self" | "backup" | "peak";
export function energyGoal(inputs: JsonObject): EnergyGoal {
	const scenario =
		inputs.energy_scenario === undefined
			? null
			: readScenarioDraft(inputs.energy_scenario);
	if (
		inputs.backup_demand !== undefined ||
		scenario?.schedule.some((period) => period.mode === "outage")
	)
		return "backup";
	if (scenario?.controller === "peak_shaving_with_reserve_v1") return "peak";
	return scenario?.schedule.some((period) => period.mode === "connected")
		? "self"
		: "";
}
export function changeEnergyGoal(
	inputs: JsonObject,
	goal: EnergyGoal,
): JsonObject {
	const scenario =
		inputs.energy_scenario === undefined
			? emptyScenario()
			: readScenarioDraft(inputs.energy_scenario);
	const { backup_demand, ...rest } = inputs;
	const leavingPeak =
		goal !== "peak" && scenario.controller === "peak_shaving_with_reserve_v1";
	return changeDemandEquipment(
		{
			...rest,
			...(goal === "backup"
				? {
						backup_demand: backup_demand ?? {
							schema_version: 1,
							load_kw: null,
							duration_hours: null,
						},
					}
				: {}),
			energy_scenario: {
				...scenario,
				controller:
					goal === "peak"
						? "peak_shaving_with_reserve_v1"
						: "self_consumption_with_reserve_v1",
				schedule: scenario.schedule.map((period) => ({
					...period,
					mode: goal === "backup" ? "outage" : goal ? "connected" : null,
					...(goal === "peak" ? { import_policy: "limited" } : {}),
					...(leavingPeak ? { import_policy: null, import_cap_kw: null } : {}),
					...(goal === "backup" ? { allow_grid_charge: false } : {}),
					...(goal && { pv_enabled: !isStorageOnly(inputs) }),
				})),
			},
		},
		{
			operating_mode:
				goal === "backup" ? "backup" : goal ? "grid_connected" : null,
		},
	);
}

export function changeBackupDemand(
	inputs: JsonObject,
	field: "load_kw" | "duration_hours",
	value: number | null,
): JsonObject {
	return {
		...inputs,
		backup_demand: {
			schema_version: 1,
			load_kw: null,
			duration_hours: null,
			...(inputs.backup_demand as JsonObject | undefined),
			[field]: value,
		},
	};
}

export function changePeakDemand(
	inputs: JsonObject,
	value: number | null,
): JsonObject {
	const scenario =
		inputs.energy_scenario === undefined
			? emptyScenario()
			: readScenarioDraft(inputs.energy_scenario);
	return {
		...inputs,
		energy_scenario: {
			...scenario,
			schedule: scenario.schedule.map((period) => ({
				...period,
				import_policy: "limited",
				import_cap_kw: value,
			})),
		},
	};
}

/** Customer demand and real interval sources, all attached to the open project. */
export function EnergyDemand({
	projectId,
	inputs,
	locale,
	disabled,
	edit,
	compare,
	modelsUnavailable = false,
	coordinatesInvalid = false,
	client,
	session,
	recheck,
	onValidity,
}: {
	projectId: string;
	inputs: JsonObject;
	locale: string;
	disabled: boolean;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	compare: () => void;
	modelsUnavailable?: boolean;
	coordinatesInvalid?: boolean;
	client: PlannerClient;
	session: Session;
	recheck: () => void;
	onValidity?: (valid: boolean) => void;
}) {
	const goal = energyGoal(inputs);
	const brief =
		inputs.brief === undefined ? emptyBrief() : readBrief(inputs.brief);
	const scenario =
		inputs.energy_scenario === undefined
			? emptyScenario()
			: readScenarioDraft(inputs.energy_scenario);
	const equipment = hasPlant(inputs)
		? readPlantDraft(inputs).requirements
		: equipmentDraft(inputs);
	const backup = inputs.backup_demand as
		{ load_kw: number | null; duration_hours: number | null } | undefined;
	const [invalid, setInvalid] = useState<ReadonlySet<string>>(new Set());
	useEffect(() => onValidity?.(invalid.size === 0), [invalid, onValidity]);
	const validityCallbacks = useRef(new Map<string, (valid: boolean) => void>());
	function report(field: string) {
		let callback = validityCallbacks.current.get(field);
		if (!callback) {
			callback = (valid: boolean) =>
				setInvalid((previous) => {
					if (previous.has(field) === !valid) return previous;
					const next = new Set(previous);
					if (valid) next.delete(field);
					else next.add(field);
					return next;
				});
			validityCallbacks.current.set(field, callback);
		}
		return callback;
	}
	const number = (
		field: string,
		label: string,
		unit: string,
		value: number | null,
		onChange: (value: number | null) => void,
	) => (
		<NumberField
			key={field}
			disabled={modelsUnavailable && field !== "annual"}
			label={label}
			unit={unit}
			value={value}
			locale={locale}
			onChange={onChange}
			onValidity={report(field)}
			min={0}
		/>
	);
	const [pattern, setPattern] = useState("");
	const [year, setYear] = useState(() => {
		const reference = referenceDraft(inputs);
		return String(
			(reference.model === KNOWN_PV_MODEL ? reference.year : null) ??
				new Date().getFullYear(),
		);
	});
	const [zone, setZone] = useState(brief.site.timezone ?? "");
	const [profileMethod, setProfileMethod] = useState<"typical" | "csv" | null>(
		null,
	);
	const csv = profileMethod === "csv";
	const [content, setContent] = useState("");
	const [delimiter, setDelimiter] = useState(";");
	const [inspection, setInspection] = useState<CsvInspection | null>(null);
	const [mapping, setMapping] = useState(() =>
		emptyMapping(brief.site.timezone),
	);
	const [label, setLabel] = useState("");
	const [rights, setRights] = useState("");
	const [busy, setBusy] = useState(false);
	const [error, setError] = useState("");
	const [profilePreview, setPreview] = useState<ProfilePreview | null>(null);
	const dates = useMemo(() => profileDateFormat(locale), [locale]);
	const profileHeading = useRef<HTMLHeadingElement>(null);
	const importedAsset = useRef<string | null>(null);
	const pending = useRef<{ path: JsonRpcPath; body: JsonObject } | null>(null);
	const flight = useRef(false);
	const generation = useRef(0);
	const selected = readSelections(inputs.profile_selections).selected
		.gross_load;
	const preview =
		profilePreview?.asset_id === selected &&
		profilePreview?.project_id === projectId &&
		profilePreview.measurement === "gross_load" &&
		client.isCurrentScope(session.query_scope)
			? profilePreview
			: null;
	const blocked = disabled || busy;
	const demandBlocked = blocked || modelsUnavailable;
	useEffect(() => {
		generation.current++;
		setPreview(null);
		importedAsset.current = null;
		setError("");
		pending.current = null;
		flight.current = false;
		setBusy(false);
		return () => {
			generation.current++;
		};
	}, [projectId, session.query_scope]);
	useEffect(() => {
		if (
			preview &&
			importedAsset.current === preview.asset_id &&
			revealActionResult(profileHeading.current, () =>
				client.isCurrentScope(session.query_scope),
			)
		)
			importedAsset.current = null;
	}, [preview, client, session.query_scope]);
	function failure(cause: unknown) {
		if (
			cause instanceof ApiError &&
			([401, 403].includes(cause.status) || cause.code === "session_changed")
		) {
			recheck();
			return;
		}
		setError(
			cause instanceof ApiError && cause.profileIssue
				? issueLabel(cause.profileIssue.issue)
				: cause instanceof ApiError && cause.status === 422
					? __(
							"Check the profile columns, units and time interval, then try again.",
							"linker-tools",
						)
					: __("The profile request failed. Please try again.", "linker-tools"),
		);
	}
	async function previewAsset(asset: ReturnType<typeof readAsset>) {
		return readPreview(
			await client.query(
				"profiles/preview",
				{
					schema_version: 1,
					project_id: projectId,
					asset_id: asset.id,
					offset: 0,
					page_size: Math.min(20, session.runtime.limits.max_page_size),
				},
				session.query_scope,
			),
			asset,
		);
	}
	useEffect(() => {
		if (!selected) return;
		const instance = generation.current;
		let active = true;
		void (async () => {
			try {
				const asset = readAsset(
					await client.query(
						"assets/read",
						{ schema_version: 1, project_id: projectId, asset_id: selected },
						session.query_scope,
					),
					projectId,
				);
				const result = await previewAsset(asset);
				if (
					active &&
					instance === generation.current &&
					client.isCurrentScope(session.query_scope)
				)
					setPreview(result);
			} catch (cause) {
				if (active && instance === generation.current) failure(cause);
			}
		})();
		return () => {
			active = false;
		};
	}, [selected, projectId, session.query_scope, client]);
	async function run(action: () => Promise<void>) {
		if (flight.current || disabled || modelsUnavailable) return;
		flight.current = true;
		setBusy(true);
		setError("");
		const instance = generation.current;
		try {
			await action();
		} catch (cause) {
			if (
				instance === generation.current &&
				client.isCurrentScope(session.query_scope)
			) {
				if (isPreMutationInputRefusal(cause)) pending.current = null;
				failure(cause);
			} else if (cause instanceof ApiError && cause.code === "session_changed")
				recheck();
		} finally {
			if (instance === generation.current) {
				flight.current = false;
				setBusy(false);
			}
		}
	}
	async function importProfile(command?: {
		path: JsonRpcPath;
		body: JsonObject;
	}) {
		if (command) pending.current = command;
		const request = pending.current;
		if (!request) return;
		const instance = generation.current;
		const asset = readAsset(
			await client.query(request.path, request.body, session.query_scope),
			projectId,
		);
		const result = await previewAsset(asset);
		if (
			instance !== generation.current ||
			!client.isCurrentScope(session.query_scope)
		)
			return;
		if (result.measurement !== "gross_load")
			throw new ApiError(422, "gross_load_profile_required");
		if (edit((current) => attachGrossLoad(current, result))) {
			importedAsset.current = asset.id;
			setPreview(result);
			pending.current = null;
			setProfileMethod(null);
			setContent("");
			setInspection(null);
		}
	}
	function changeDemand(
		field: "load_kw" | "duration_hours",
		value: number | null,
	) {
		edit((current) => changeBackupDemand(current, field, value));
	}
	function changePeak(value: number | null) {
		edit((current) => changePeakDemand(current, value));
	}
	const backupReady =
		goal !== "backup" ||
		(backup?.load_kw !== null &&
			backup?.load_kw !== undefined &&
			backup.load_kw > 0 &&
			backup.duration_hours !== null &&
			backup.duration_hours > 0);
	const solarOnly = brief.system_scope === "pv_only";
	const retainsInverter = retainsUnverifiedInverter(inputs);
	const needsGridPhase = equipment.grid_phase === null && !retainsInverter;
	const needsPeakTarget =
		goal === "peak" &&
		Boolean(selected) &&
		!retainsInverter &&
		inputs.equipment_demand === undefined &&
		scenario.schedule.some((period) => period.import_cap_kw === null);
	const canCompare =
		!coordinatesInvalid &&
		Boolean(goal) &&
		(!solarOnly || goal !== "backup") &&
		!needsGridPhase &&
		!needsPeakTarget &&
		backupReady &&
		invalid.size === 0 &&
		!demandBlocked;
	const canStandard =
		pattern !== "" &&
		brief.annual_load.kwh !== null &&
		brief.annual_load.kwh > 0 &&
		zone.trim() !== "" &&
		Number.isInteger(Number(year)) &&
		Number(year) >= 2000 &&
		Number(year) <= 2100 &&
		invalid.size === 0;
	const csvMapping = mappedProfile(
		{ ...mapping, measurement: "gross_load", timezone: zone },
		delimiter,
	);
	const profileEditor = (
		<>
			<p className="sc-muted">
				{__(
					"A load profile adds the timing of consumption. Annual electricity use alone does not determine storage size.",
					"linker-tools",
				)}
			</p>
			<div
				className="sc-profile-methods"
				role="group"
				aria-label={__("Electricity use over time", "linker-tools")}
			>
				{(["typical", "csv"] as const).map((method) => (
					<button
						key={method}
						className="sc-button"
						type="button"
						disabled={demandBlocked || pending.current !== null}
						aria-pressed={profileMethod === method}
						onClick={() => setProfileMethod(method)}
					>
						<Icon name={method === "csv" ? "report" : "energy"} />
						{method === "csv"
							? __("Import CSV", "linker-tools")
							: __("Use a typical profile", "linker-tools")}
					</button>
				))}
			</div>
			{profileMethod && (
				<fieldset disabled={demandBlocked} className="sc-profile-fields">
					<div className="sc-fields sc-profile-sources">
						<label className="sc-field">
							<span>{__("Time zone", "linker-tools")}</span>
							<input
								value={zone}
								placeholder="Europe/Berlin"
								onChange={(event) => setZone(event.currentTarget.value)}
							/>
						</label>
						{!csv && (
							<>
								<label className="sc-field">
									<span>{__("Typical use", "linker-tools")}</span>
									<select
										name="load-pattern"
										value={pattern}
										onChange={(event) => setPattern(event.currentTarget.value)}
									>
										<option value="">
											{__("Choose a template", "linker-tools")}
										</option>
										{[
											["H0", __("Household", "linker-tools")],
											["G0", __("General business", "linker-tools")],
											["G1", __("Business hours, weekdays", "linker-tools")],
											["G2", __("Evening business", "linker-tools")],
											["G3", __("Continuous operation", "linker-tools")],
											["G4", __("Retail", "linker-tools")],
											["G5", __("Bakery", "linker-tools")],
											["G6", __("Weekend business", "linker-tools")],
											["H25", __("Household (2025)", "linker-tools")],
											["G25", __("Business (2025)", "linker-tools")],
											["L25", __("Agriculture (2025)", "linker-tools")],
										].map(([value, text]) => (
											<option key={value} value={value}>
												{text} · {value}
											</option>
										))}
									</select>
								</label>
								<label className="sc-field">
									<span>{__("Profile year", "linker-tools")}</span>
									<input
										type="number"
										min="2000"
										max="2100"
										step="1"
										value={year}
										onChange={(event) => setYear(event.currentTarget.value)}
									/>
								</label>
							</>
						)}
					</div>
					{!csv ? (
						<>
							<p className="sc-muted">
								{__(
									"BDEW/VDEW templates use the German calendar and are scaled to your annual consumption. For other sites, use them as an explicit template or import local meter data.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="sc-button"
								disabled={!canStandard || pending.current !== null}
								onClick={() =>
									void run(() =>
										importProfile({
											path: "profiles/standard",
											body: readProfileImport({
												schema_version: 1,
												project_id: projectId,
												edition: pattern.endsWith("25") ? 2025 : 1999,
												profile: pattern,
												year: Number(year),
												annual_kwh: brief.annual_load.kwh,
												timezone: zone.trim(),
												key: crypto.randomUUID(),
											}),
										}),
									)
								}
							>
								{__("Use this load profile", "linker-tools")}
							</button>
						</>
					) : (
						<>
							<div className="sc-fields">
								<label className="sc-field">
									<span>{__("CSV file", "linker-tools")}</span>
									<input
										type="file"
										accept=".csv,text/csv,text/plain"
										onChange={(event) => {
											const file = event.currentTarget.files?.[0];
											if (file)
												void run(async () => {
													const encoded = await fileBase64(
														file,
														session.runtime.limits.max_csv_bytes,
													);
													setContent(encoded);
													setInspection(null);
													setLabel(file.name);
												});
										}}
									/>
								</label>
								<label className="sc-field">
									<span>{__("Column delimiter", "linker-tools")}</span>
									<select
										value={delimiter}
										onChange={(event) => {
											setDelimiter(event.currentTarget.value);
											setInspection(null);
										}}
									>
										<option value=";">{__("Semicolon", "linker-tools")}</option>
										<option value=",">{__("Comma", "linker-tools")}</option>
										<option value={"\t"}>{__("Tab", "linker-tools")}</option>
									</select>
								</label>
							</div>
							<button
								className="sc-button"
								type="button"
								disabled={!content || pending.current !== null}
								onClick={() =>
									void run(async () => {
										const result = readInspection(
											await client.query(
												"profiles/inspect",
												{
													schema_version: 1,
													project_id: projectId,
													content_base64: content,
													delimiter,
													page_size: Math.min(
														10,
														session.runtime.limits.max_page_size,
													),
												},
												session.query_scope,
											),
											delimiter,
										);
										setInspection(result);
									})
								}
							>
								{__("Read CSV columns", "linker-tools")}
							</button>
							{inspection && (
								<>
									<p>
										{inspection.record_count}{" "}
										{__("readings found", "linker-tools")}
									</p>
									<div className="sc-fields">
										{(
											[
												["timestamp", __("Timestamp column", "linker-tools")],
												["value", __("Consumption column", "linker-tools")],
											] as const
										).map(([key, text]) => (
											<label className="sc-field" key={key}>
												<span>{text}</span>
												<select
													value={mapping[key]}
													onChange={(event) =>
														setMapping({
															...mapping,
															[key]: event.currentTarget.value,
														})
													}
												>
													<option value="">
														{__("Choose a column", "linker-tools")}
													</option>
													{inspection.columns.map((column) => (
														<option key={column} value={column}>
															{column}
														</option>
													))}
												</select>
											</label>
										))}
										<label className="sc-field">
											<span>{__("Values represent", "linker-tools")}</span>
											<select
												value={mapping.unit}
												onChange={(event) =>
													setMapping({
														...mapping,
														unit: event.currentTarget.value,
													})
												}
											>
												<option value="">
													{__("Choose a unit", "linker-tools")}
												</option>
												<option value="interval_average_kw">kW</option>
												<option value="interval_energy_kwh">kWh</option>
											</select>
										</label>
										<label className="sc-field">
											<span>{__("Timestamp marks", "linker-tools")}</span>
											<select
												value={mapping.timeRole}
												onChange={(event) =>
													setMapping({
														...mapping,
														timeRole: event.currentTarget.value,
														durationMode: "fixed",
													})
												}
											>
												<option value="">
													{__("Choose an option", "linker-tools")}
												</option>
												<option value="start">
													{__("Interval start", "linker-tools")}
												</option>
												<option value="end">
													{__("Interval end", "linker-tools")}
												</option>
											</select>
										</label>
										{number(
											"csv-minutes",
											__("Interval length", "linker-tools"),
											"min",
											mapping.minutes,
											(value) =>
												setMapping({
													...mapping,
													minutes: value,
													durationMode: "fixed",
												}),
										)}
										<label className="sc-field">
											<span>{__("Decimal separator", "linker-tools")}</span>
											<select
												value={mapping.decimal}
												onChange={(event) =>
													setMapping({
														...mapping,
														decimal: event.currentTarget.value,
													})
												}
											>
												<option value="">
													{__("Choose an option", "linker-tools")}
												</option>
												<option value=".">.</option>
												<option value=",">,</option>
											</select>
										</label>
										<label className="sc-field">
											<span>{__("Data source", "linker-tools")}</span>
											<select
												value={mapping.origin}
												onChange={(event) =>
													setMapping({
														...mapping,
														origin: event.currentTarget.value,
													})
												}
											>
												<option value="">
													{__("Choose an option", "linker-tools")}
												</option>
												<option value="measured">
													{__("Meter readings", "linker-tools")}
												</option>
												<option value="modelled">
													{__("Modelled data", "linker-tools")}
												</option>
												<option value="template">
													{__("Template", "linker-tools")}
												</option>
												<option value="synthetic">
													{__("Synthetic data", "linker-tools")}
												</option>
											</select>
										</label>
										<label className="sc-field">
											<span>{__("Source name", "linker-tools")}</span>
											<input
												value={label}
												maxLength={256}
												onChange={(event) =>
													setLabel(event.currentTarget.value)
												}
											/>
										</label>
										<label className="sc-field">
											<span>
												{__(
													"Source and permission to store privately",
													"linker-tools",
												)}
											</span>
											<textarea
												value={rights}
												maxLength={4096}
												onChange={(event) =>
													setRights(event.currentTarget.value)
												}
											/>
										</label>
									</div>
									<p className="sc-muted">
										{__(
											"Import total site consumption, rather than net grid import. Use ISO timestamps with UTC offsets for repeated daylight-saving hours. The original data and gaps are preserved.",
											"linker-tools",
										)}
									</p>
									<button
										className="sc-button"
										type="button"
										disabled={
											!csvMapping ||
											!rights.trim() ||
											!label.trim() ||
											invalid.size > 0 ||
											pending.current !== null
										}
										onClick={() =>
											void run(() =>
												importProfile({
													path: "profiles/csv",
													body: readProfileImport({
														schema_version: 1,
														project_id: projectId,
														content_base64: content,
														mapping: csvMapping,
														source_label: label.trim(),
														rights_note: rights.trim(),
														key: crypto.randomUUID(),
													}),
												}),
											)
										}
									>
										{__("Use CSV consumption", "linker-tools")}
									</button>
								</>
							)}
						</>
					)}
				</fieldset>
			)}
		</>
	);
	return (
		<div className="sc-energy-demand">
			<header className="sc-section-head">
				<div>
					<h1>{__("What should the system do?", "linker-tools")}</h1>
					<p className="sc-muted">
						{__(
							"The purpose determines which information matters.",
							"linker-tools",
						)}
					</p>
				</div>
			</header>
			<fieldset disabled={blocked} className="sc-card">
				<div className="sc-fields">
					<label className="sc-field">
						<span>{__("Purpose", "linker-tools")}</span>
						<select
							value={goal}
							disabled={modelsUnavailable}
							onChange={(event) => {
								const next = event.currentTarget.value;
								if (next === "self" || next === "backup" || next === "peak") {
									setInvalid(
										(previous) =>
											new Set(
												[...previous].filter(
													(field) =>
														field !== "backup-load" &&
														field !== "backup-hours" &&
														field !== "peak",
												),
											),
									);
									edit((current) => changeEnergyGoal(current, next));
								}
							}}
						>
							<option value="">{__("Choose an option", "linker-tools")}</option>
							<option value="self">
								{__("Use more solar on site", "linker-tools")}
							</option>
							<option value="backup" disabled={solarOnly}>
								{__("Backup supply", "linker-tools")}
							</option>
							<option value="peak">
								{__("Reduce peak demand", "linker-tools")}
							</option>
						</select>
					</label>
					{number(
						"annual",
						__("Annual electricity use", "linker-tools"),
						"kWh",
						brief.annual_load.kwh,
						(value) =>
							edit((current) => {
								const currentBrief =
									current.brief === undefined
										? emptyBrief()
										: readBrief(current.brief);
								return {
									...current,
									brief: {
										...currentBrief,
										annual_load: {
											...currentBrief.annual_load,
											kwh: value,
											basis: value === null ? null : "user_estimate",
										},
									},
								};
							}),
					)}
					<label className="sc-field">
						<span>{__("Grid connection", "linker-tools")}</span>
						<select
							value={String(equipment.grid_phase ?? "")}
							disabled={modelsUnavailable}
							onChange={(event) => {
								const value = event.currentTarget.value;
								edit((current) =>
									changeDemandEquipment(current, {
										grid_phase: value === "" ? null : value === "1" ? 1 : 3,
									}),
								);
							}}
						>
							<option value="">{__("Choose an option", "linker-tools")}</option>
							<option value="1">{__("Single phase", "linker-tools")}</option>
							<option value="3">{__("Three phase", "linker-tools")}</option>
						</select>
					</label>
					{goal === "peak" &&
						number(
							"peak",
							__("Target grid import limit", "linker-tools"),
							"kW",
							scenario.schedule[0]?.import_cap_kw ?? null,
							changePeak,
						)}
				</div>
				{goal === "backup" && (
					<>
						<p className="sc-muted">
							{__(
								"Backup sizing starts with the loads that must keep running.",
								"linker-tools",
							)}
						</p>
						<div className="sc-fields">
							{number(
								"backup-load",
								__("Backup load", "linker-tools"),
								"kW",
								backup?.load_kw ?? null,
								(value) => changeDemand("load_kw", value),
							)}
							{number(
								"backup-hours",
								__("Required duration", "linker-tools"),
								"h",
								backup?.duration_hours ?? null,
								(value) => changeDemand("duration_hours", value),
							)}
						</div>
						{backupReady && (
							<p>
								<strong>
									{new Intl.NumberFormat(locale).format(
										backup!.load_kw! * backup!.duration_hours!,
									)}{" "}
									kWh
								</strong>{" "}
								· {__("Load energy before system losses", "linker-tools")}
							</p>
						)}
					</>
				)}
			</fieldset>
			<section className="sc-card sc-demand-profile">
				<h2 ref={profileHeading}>
					{__("Electricity use over time", "linker-tools")}
				</h2>
				{preview && (
					<>
						<ProfileCurve
							preview={preview}
							locale={locale}
							title={__("Electricity demand", "linker-tools")}
						/>
						<p>
							<strong>
								{new Intl.NumberFormat(locale).format(
									preview.summary.energy_kwh,
								)}{" "}
								kWh
							</strong>{" "}
							· {preview.summary.interval_count}{" "}
							{__("readings", "linker-tools")} ·{" "}
							{dates.formatRange(
								new Date(preview.summary.start_utc),
								new Date(preview.summary.end_utc),
							)}{" "}
							UTC
						</p>
						{goal === "peak" && (
							<dl className="sc-fields sc-demand-metrics">
								<div>
									<dt>{__("Peak in this profile", "linker-tools")}</dt>
									<dd>
										{new Intl.NumberFormat(locale).format(
											preview.summary.max_interval_mean_kw,
										)}{" "}
										kW
									</dd>
								</div>
								{typeof scenario.schedule[0]?.import_cap_kw === "number" && (
									<div>
										<dt>{__("Target grid import limit", "linker-tools")}</dt>
										<dd>
											{new Intl.NumberFormat(locale).format(
												scenario.schedule[0].import_cap_kw,
											)}{" "}
											kW
										</dd>
									</div>
								)}
							</dl>
						)}
						{preview.summary.gap_count > 0 && (
							<p>
								{preview.summary.gap_count}{" "}
								{__("gaps in the source data", "linker-tools")}
							</p>
						)}
						<details>
							<summary>{__("View readings", "linker-tools")}</summary>
							<div className="sc-readings-table">
								<table>
									<thead>
										<tr>
											<th>{__("Interval start (UTC)", "linker-tools")}</th>
											<th>kW</th>
										</tr>
									</thead>
									<tbody>
										{preview.rows.map((row) => (
											<tr key={row.interval_index}>
												<td>
													<time dateTime={row.start_utc}>
														{dates.format(new Date(row.start_utc))}
													</time>
												</td>
												<td>
													{new Intl.NumberFormat(locale).format(
														row.interval_mean_kw,
													)}
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						</details>
					</>
				)}
				{preview ? (
					<details>
						<summary>{__("Change load profile", "linker-tools")}</summary>
						{profileEditor}
					</details>
				) : (
					profileEditor
				)}
				{busy && (
					<p role="status">{__("Loading consumption data…", "linker-tools")}</p>
				)}
				{error && <p role="alert">{error}</p>}
				{pending.current && error && (
					<button
						type="button"
						className="sc-button"
						disabled={demandBlocked}
						onClick={() => void run(() => importProfile())}
					>
						{__("Retry profile import", "linker-tools")}
					</button>
				)}
			</section>
			{!solarOnly && (
				<details className="sc-card sc-demand-requirements">
					<summary>
						{__("Required power and capacity already known?", "linker-tools")}
					</summary>
					<p className="sc-muted">
						{__(
							"These optional values set minimum requirements for equipment comparison. Leave unknown values blank.",
							"linker-tools",
						)}
					</p>
					<fieldset disabled={demandBlocked} className="sc-fields">
						{number(
							"power",
							__("Continuous discharge power", "linker-tools"),
							"kW",
							equipment.required_discharge_ac_kw as number | null,
							(value) =>
								edit((current) =>
									changeDemandEquipment(current, {
										required_discharge_ac_kw: value,
									}),
								),
						)}
						{number(
							"capacity",
							__("Usable storage capacity", "linker-tools"),
							"kWh",
							equipment.required_usable_kwh as number | null,
							(value) =>
								edit((current) =>
									changeDemandEquipment(current, {
										required_usable_kwh: value,
									}),
								),
						)}
					</fieldset>
				</details>
			)}
			<footer className="sc-footer">
				{coordinatesInvalid && (
					<p className="sc-muted">
						{__("Check the project coordinates.", "linker-tools")}
					</p>
				)}
				{goal && needsGridPhase && (
					<p className="sc-muted">
						{__(
							"Choose a single-phase or three-phase grid connection.",
							"linker-tools",
						)}
					</p>
				)}
				{needsPeakTarget && (
					<p className="sc-muted">
						{__(
							"Enter a grid import target to compare peak demand.",
							"linker-tools",
						)}
					</p>
				)}
				{canCompare && goal !== "backup" && !selected && (
					<p className="sc-muted">
						{__(
							"You can compare equipment now. Add a load profile to compare energy use over time.",
							"linker-tools",
						)}
					</p>
				)}
				<div className="sc-actions">
					<button
						type="button"
						className="sc-button sc-primary"
						disabled={!canCompare}
						onClick={compare}
					>
						{__("Compare systems", "linker-tools")}
					</button>
				</div>
			</footer>
		</div>
	);
}
