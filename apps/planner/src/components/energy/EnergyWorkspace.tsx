import { SolarEnergySetup } from "./SolarEnergySetup.tsx";
import {
	PLANT_ENERGY_TASK,
	DC_PLANT_ENERGY_TASK,
	plantEnergyTask,
	plantEnergyDraft,
	plantEnergyInputs,
	plantEnergyParts,
	plantEnergyEquipment,
} from "../../domain/plantEnergy.ts";
import type { PlantEnergyDraft } from "../../domain/plantEnergy.ts";
import { PlantEnergyForm } from "./PlantEnergyForm.tsx";
import { readInstallation } from "../../domain/installation.ts";
import { hasReportableInstallation } from "../../domain/installationTerminals.ts";
import { readObject } from "../../data/readProtocol.ts";
import {
	DC_MODEL,
	REFERENCE_CAPACITY,
	restoreDcConditions,
	readDcLossScenario,
} from "../../domain/dcEnergy.ts";
import { PlanningReportForm } from "./PlanningReportForm.tsx";
import { PlanningReportResult } from "./PlanningReportResult.tsx";
import { EnergyComparison } from "./EnergyComparison.tsx";
import { REPORT_TASK } from "../../data/planningReport.ts";
import type { ReportOptions } from "../../data/planningReport.ts";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Draft } from "../../domain/draft.ts";
import { isDirty, sameJson, projectInputContract } from "../../domain/draft.ts";
import {
	BATTERY_FIELDS,
	isStorageOnly,
	isPvOnly,
	emptyScenario,
	useEquipmentCapacity,
	readScenarioDraft,
	readBatteryParameters,
	readEnergyInputs,
	scenarioInputs,
} from "../../domain/energyScenario.ts";
import type { ScenarioDraft } from "../../domain/energyScenario.ts";
import {
	readAsset,
	readPreview,
	readSelections,
} from "../../domain/profiles.ts";
import type { ProfileRole } from "../../domain/profiles.ts";
import { sharedProfileRange } from "../../domain/profileCoverage.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { JsonObject, Project, Session } from "../../data/protocol.ts";
import { ApiError, clearInputFields } from "../../data/protocol.ts";
import {
	initialEnergyView,
	PLANNER_NAVIGATION,
	replacePlannerLocation,
} from "../../data/plannerLocation.ts";
import type { EnergyView } from "../../data/plannerLocation.ts";
import { usePlanningOperations } from "../../data/usePlanningOperations.ts";
import { usePlanningRuns } from "../../data/usePlanningRuns.ts";
import {
	readPlanningOperation,
	readRunInputs,
	runPending,
	runTask,
} from "../../data/planningProtocol.ts";
import { WEATHER_TASK, PV_TASK } from "../../data/readPreparationResult.ts";
import { EQUIPMENT_TASK } from "../../data/readEquipmentResult.ts";
import { EquipmentWorkspace } from "../equipment/EquipmentWorkspace.tsx";
import {
	hasPlant,
	readEquipmentPlant,
	equipmentContext,
	applyEquipmentContext,
} from "../../domain/equipmentPlant.ts";
import { adoptPlantCandidate } from "../../domain/plantSearch.ts";
import { EquipmentResult } from "../equipment/EquipmentResult.tsx";
import { CertificateEvidence } from "../equipment/CertificateEvidence.tsx";
import {
	readEquipmentSelection,
	equipmentDraft,
	changeEquipment,
	checkRetainedEquipment,
	comparisonModels,
	compileEquipment,
} from "../../domain/equipment.ts";
import {
	authoredCalculationInputs,
	authoredDiscoveryInputs,
} from "../../domain/currentCalculation.ts";
import { readEquipmentProducts } from "../../data/equipmentProducts.ts";
import { SEARCH_TASK, isPlantCandidate } from "../../data/equipmentSearch.ts";
import type { EquipmentCandidate } from "../../data/equipmentSearch.ts";
import { EquipmentSearchResult } from "../equipment/EquipmentSearchResult.tsx";
import type { PlanningIntent } from "../../data/PlanningIntentStore.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { revealActionResult } from "../revealActionResult.ts";
import { measurementLabel } from "../ProfileLabels.ts";
import { ScenarioForm } from "./ScenarioForm.tsx";
import { EnergyError } from "./EnergyError.tsx";
import { RunResult } from "./RunResult.tsx";
import { TraceExplorer } from "./TraceExplorer.tsx";
import { runStateLabel, taskLabel } from "./planningLabels.ts";
import { PreparationResult } from "./PreparationResult.tsx";
import { RunBasis } from "./RunBasis.tsx";
import { WeatherSetup } from "./WeatherSetup.tsx";
import { PvSetup } from "./PvSetup.tsx";
import { PvgisReferenceSetup } from "./PvgisReferenceSetup.tsx";
import { PvgisReferenceResult } from "./PvgisReferenceResult.tsx";
import { DirectBeamSetup } from "./DirectBeamSetup.tsx";
import { DirectBeamResult } from "./DirectBeamResult.tsx";
import {
	DIRECT_BEAM_TASK,
	compileDirectBeam,
	directBeamDraft,
} from "../../domain/directBeam.ts";
import { readDirectBeamLimits } from "../../data/directBeamResult.ts";
import { GeometricPvSetup } from "./GeometricPvSetup.tsx";
import {
	GEOMETRIC_PV_TASK,
	compileGeometricPv,
	geometricPvDraft,
} from "../../domain/geometricPv.ts";
import {
	PVGIS_REFERENCE_TASK,
	compilePvgisReference,
	readPvgisReference,
	referenceDraft,
	referenceRoof,
} from "../../domain/pvgisReference.ts";
import {
	compileWeather,
	compilePv,
	checkPvWeather,
	readSolarSetup,
} from "../../domain/solarSetup.ts";

function requireUnchangedDemand(inputs: JsonObject, frozenInputs: JsonObject) {
	const current = authoredDiscoveryInputs(inputs);
	const frozen = authoredDiscoveryInputs(frozenInputs);
	if (
		isStorageOnly(current) !== isStorageOnly(frozen) ||
		["energy_scenario", "profile_selections", "equipment_demand"].some(
			(key) => !sameJson(current[key] ?? null, frozen[key] ?? null),
		)
	)
		throw new ApiError(409, "equipment_selection_changed");
}

export function EnergyWorkspace({
	draft,
	edit,
	flush,
	acknowledgeProject,
	session,
	client,
	recheck,
	locale,
	blocked,
	active,
	recoveryScopes,
	recoveryChecking = false,
	onValidity,
	openProfiles,
	openDesign,
	equipmentFocus = false,
	openEquipment,
	openResults,
	sceneModuleUrl = null,
}: {
	draft: Draft;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	flush: () => Promise<boolean>;
	acknowledgeProject: (
		project: Project,
		command: JsonObject,
		path: "runs/calculate" | "runs/find-equipment" | "runs/check-equipment",
	) => Promise<void>;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	locale: string;
	blocked: boolean;
	active: boolean;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	onValidity: (valid: boolean) => void;
	openProfiles: () => void;
	openDesign?: () => void;
	equipmentFocus?: boolean;
	openEquipment?: () => void;
	openResults?: () => void;
	sceneModuleUrl?: string | null;
}) {
	const storageOnly = isStorageOnly(draft.history.current);
	const pvOnly = isPvOnly(draft.history.current);
	const joint = hasPlant(draft.history.current);
	const jointContext = useMemo(() => {
		if (!joint) return { value: null, error: null };
		try {
			const plant = plantEnergyEquipment(draft.history.current);
			return {
				value: { plant, setup: plantEnergyDraft(draft.history.current, plant) },
				error: null,
			};
		} catch (error) {
			return { value: null, error };
		}
	}, [
		joint,
		draft.history.current.brief,
		draft.history.current.equipment_plant,
		draft.history.current.equipment_plant_setup,
		draft.history.current.energy_plant_setup,
	]);
	const jointTask =
		!pvOnly && jointContext.value
			? plantEnergyTask(jointContext.value.setup)
			: PLANT_ENERGY_TASK;
	const jointAvailable =
		session.runtime.models[
			jointTask === DC_PLANT_ENERGY_TASK ? "plant_dc_replay" : "plant_replay"
		] === jointTask;

	const parsed = useMemo(() => {
		try {
			return {
				value:
					draft.history.current.energy_scenario === undefined
						? emptyScenario()
						: readScenarioDraft(draft.history.current.energy_scenario),
				error: null,
			};
		} catch (error) {
			return { value: null, error };
		}
	}, [draft.history.current.energy_scenario]);
	const converterIds = useMemo(() => {
		try {
			return readSolarSetup(draft.history.current).pv.converters.map(
				(c) => c.id,
			);
		} catch {
			return [];
		}
	}, [draft.history.current.solar_setup]);
	const setupDocument = joint
		? draft.history.current.energy_plant_setup
		: draft.history.current.energy_scenario;
	const equipmentSelection = useMemo(() => {
		try {
			return readEquipmentSelection(draft.history.current.equipment_selection);
		} catch {
			return null;
		}
	}, [draft.history.current.equipment_selection]);
	const equipmentForEditing = useMemo(() => {
		try {
			const current = equipmentDraft(draft.history.current);
			return typeof current.inverter_product_id === "number" ? current : null;
		} catch {
			return null;
		}
	}, [
		draft.history.current.equipment_setup,
		draft.history.current.equipment_selection,
		draft.history.current.equipment_requirements,
		draft.history.current.brief,
	]);
	const setup = parsed.value,
		currentSetup = joint ? (jointContext.value?.setup ?? null) : setup,
		selections = readSelections(draft.history.current.profile_selections);
	const sharedDc =
		!pvOnly &&
		(currentSetup?.coupling === "shared_dc" ||
			currentSetup?.coupling === "plant_shared_dc");
	const pvInactive =
		storageOnly ||
		Boolean(
			currentSetup &&
			!sharedDc &&
			currentSetup.schedule.length > 0 &&
			currentSetup.schedule.every((period) => period.pv_enabled === false),
		);
	const [selectedView, setView] = useState<EnergyView>(() =>
			initialEnergyView(new URL(window.location.href)),
		),
		[section, setSection] = useState<"storage" | "initial" | "operation">(() =>
			!joint &&
			!pvOnly &&
			!equipmentForEditing &&
			setup?.coupling !== "shared_dc" &&
			setup?.schedule.length === 1 &&
			setup.battery.usable_window_kwh === null
				? "operation"
				: "storage",
		),
		[scenarioValid, setScenarioValid] = useState(true),
		[compactValid, setCompactValid] = useState(true),
		[weatherValid, setWeatherValid] = useState(true),
		[pvValid, setPvValid] = useState(true),
		[equipmentValid, setEquipmentValid] = useState(true),
		[beamValid, setBeamValid] = useState(true),
		[error, setError] = useState<unknown>(null),
		[rangeBusy, setRangeBusy] = useState(false);
	const view = equipmentFocus
		? "equipment"
		: storageOnly &&
			  [
					"weather",
					"pv",
					"pvgis-reference",
					"geometric-pv",
					"direct-beam",
			  ].includes(selectedView)
			? "scenario"
			: selectedView;
	useEffect(() => {
		// A link, a reload or the back button can change the requested view after
		// this workspace mounted. Without this the form keeps whatever view it
		// started with, so a direct `energy_view=pv` link silently lands on the
		// scenario form and the module catalogue behind PV preparation never loads.
		const sync = () =>
			setView(initialEnergyView(new URL(window.location.href)));
		window.addEventListener(PLANNER_NAVIGATION, sync);
		window.addEventListener("popstate", sync);
		return () => {
			window.removeEventListener(PLANNER_NAVIGATION, sync);
			window.removeEventListener("popstate", sync);
		};
	}, []);
	useEffect(() => {
		// Undo/redo and profile edits also change the effective scenario, without
		// passing through this form's onChange handler.
		setError(null);
	}, [
		setupDocument,
		draft.history.current.profile_selections,
		draft.history.current.equipment_plant,
	]);
	const lifetime = useRef(0),
		rangeFlight = useRef<AbortController | null>(null);
	const projectId = draft.baseline.id,
		admitted = client.isCurrentScope(session.query_scope),
		dirty = isDirty(draft),
		syntaxValid =
			scenarioValid &&
			compactValid &&
			equipmentValid &&
			(storageOnly || (weatherValid && pvValid && beamValid));
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
			rangeFlight.current?.abort();
		};
	}, [projectId, session.query_scope]);
	useEffect(() => {
		onValidity(syntaxValid);
		return () => onValidity(true);
	}, [syntaxValid, onValidity]);
	const confirmedBatteryId = useMemo(() => {
		try {
			return readEnergyInputs(draft.baseline.inputs.energy_replay)
				.battery_parameters_asset_id;
		} catch {
			return null;
		}
	}, [draft.baseline.inputs.energy_replay]);
	const confirmedBatteryIds = useMemo(() => {
		const input = draft.baseline.inputs.energy_plant;
		if (!input || !Array.isArray(readObject(input).units)) return [];
		return (readObject(input).units as readonly JsonObject[]).map((u) =>
			String(u.battery_parameters_asset_id),
		);
	}, [draft.baseline.inputs.energy_plant]);
	const operations = usePlanningOperations({
		projectId,
		session,
		client,
		recheck,
		recoveryScopes,
		recoveryChecking,
		confirmedBatteryId,
		confirmedBatteryIds,
		acknowledgeProject,
	});
	const actionError =
			error ??
			(operations.intent?.path === "draft/apply" ? null : operations.error),
		errorTarget = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (actionError && active)
			revealActionResult(errorTarget.current, () =>
				client.isCurrentScope(session.query_scope),
			);
	}, [actionError, active, client, session.query_scope]);
	const schedulePath = joint
			? "energy_plant_setup.schedule"
			: "energy_scenario.schedule",
		scenarioErrors =
			actionError instanceof ApiError
				? actionError.fields.filter((path) =>
						path.startsWith(schedulePath + "["),
					)
				: [],
		scenarioTarget = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (!scenarioErrors.length || !active || blocked || operations.busy) return;
		setView("scenario");
		setSection("operation");
		const frame = window.requestAnimationFrame(() => {
			if (!client.isCurrentScope(session.query_scope)) return;
			const field = [
				...(scenarioTarget.current?.querySelectorAll<HTMLInputElement>(
					"input[name]",
				) ?? []),
			].find(
				(node) =>
					scenarioErrors.includes(node.name) && !node.closest("[hidden]"),
			);
			if (!field) return;
			let ancestor = field.parentElement;
			while (ancestor && ancestor !== scenarioTarget.current) {
				if (ancestor.tagName === "DETAILS")
					(ancestor as HTMLDetailsElement).open = true;
				ancestor = ancestor.parentElement;
			}
			field.focus();
			field.scrollIntoView({ block: "center" });
		});
		return () => window.cancelAnimationFrame(frame);
	}, [
		actionError,
		active,
		blocked,
		schedulePath,
		operations.busy,
		client,
		session.query_scope,
	]);
	const runs = usePlanningRuns({
		projectId,
		session,
		client,
		recheck,
		active:
			active &&
			(view === "runs" || view === "reports" || view === "comparison"),
		readSelected: view === "runs",
	});
	const runTarget = useRef<HTMLDivElement>(null),
		visibleRunId = runs.run.data?.id;
	useEffect(() => {
		if (
			!active ||
			view !== "runs" ||
			!visibleRunId ||
			visibleRunId !== runs.runId
		)
			return;
		// Let the parent/native bar layout commit before restoring a result route.
		const frame = window.requestAnimationFrame(() =>
			revealActionResult(
				runTarget.current?.querySelector<HTMLElement>(".sc-run-result h3") ??
					null,
				() => client.isCurrentScope(session.query_scope),
			),
		);
		return () => window.cancelAnimationFrame(frame);
		// Changing a selected calculation reveals its heading. Polling the same
		// calculation never takes focus back from the reader's current control.
	}, [view, visibleRunId, runs.runId, active, client, session.query_scope]);
	const unconfirmed = operations.records.filter(
		(record) => record.resultId === null,
	);
	const canCalculate =
		Boolean(currentSetup) &&
		(!joint || jointAvailable) &&
		!draft.pending &&
		!draft.conflict &&
		!blocked &&
		!rangeBusy &&
		syntaxValid &&
		admitted &&
		!operations.busy &&
		!operations.checking &&
		!operations.storageFailed &&
		!unconfirmed.length;
	function clearScheduleErrors(next: ScenarioDraft | PlantEnergyDraft) {
		const changed = scenarioErrors.filter((path) => {
			const [index, field] = path.slice(schedulePath.length + 1).split("].");
			return (
				next.schedule[Number(index)]?.[field!] !==
				currentSetup?.schedule[Number(index)]?.[field!]
			);
		});
		if (changed.length) operations.clearError(changed);
	}
	function change(next: ScenarioDraft) {
		if (blocked || !client.isCurrentScope(session.query_scope)) return;
		clearScheduleErrors(next);
		edit((inputs) => scenarioInputs(inputs, next));
		setError(null);
	}
	function changeJoint(next: PlantEnergyDraft) {
		if (blocked || !client.isCurrentScope(session.query_scope)) return;
		clearScheduleErrors(next);
		edit((inputs) => plantEnergyInputs(inputs, next));
		setError(null);
	}
	async function recover(record: PlanningIntent) {
		if (
			blocked ||
			!syntaxValid ||
			operations.busy ||
			!client.isCurrentScope(session.query_scope)
		)
			return;
		setError(null);
		try {
			if (record.path !== "battery/scenario") {
				const reply = await operations.retry(record);
				if (reply && "run" in reply) {
					runs.accepted(reply.run);
					setView("runs");
					openResults?.();
				}
				return;
			}

			const command = readPlanningOperation(record.path, record.body),
				parameters =
					readObject(command.parameters).model === DC_MODEL
						? readDcLossScenario(command.parameters)
						: readBatteryParameters(command.parameters),
				dc = parameters.model === DC_MODEL,
				instance = lifetime.current;
			// Confirm the original receipt before deciding whether it can be applied.
			const reply = await operations.retry(record);
			if (
				!reply ||
				reply.path !== "battery/scenario" ||
				instance !== lifetime.current ||
				!client.isCurrentScope(session.query_scope)
			)
				return;
			if (command.equipment_unit_id !== undefined) {
				if (
					!jointContext.value ||
					!dc ||
					command.expected_revision !== draft.baseline.revision ||
					!sameJson(
						equipmentContext(draft.history.current),
						equipmentContext(draft.baseline.inputs),
					)
				)
					throw new ApiError(409, "product_evidence_changed");
				const { setup: current } = jointContext.value;
				const plant = readEquipmentPlant(draft.history.current.equipment_plant);
				const unit = current.units.find(
						(u) => u.unit_id === command.equipment_unit_id,
					),
					hardware = plant.units.find(
						(u) => u.id === command.equipment_unit_id,
					);
				if (
					!unit ||
					!hardware ||
					!sameJson(
						plantEnergyParts(
							current,
							selections,
							plant,
							draft.history.current,
						).parameters.get(unit.unit_id),
						parameters,
					)
				)
					throw new ApiError(409, "scenario_changed");
				const next = {
					...current,
					units: current.units.map((u) =>
						u.unit_id === unit.unit_id
							? {
									...u,
									settings: {
										...u.settings,
										battery_binding: {
											asset_id: reply.asset.id,
											parameters,
											source_note: String(command.source_note),
											equipment_selection: hardware.selection,
										},
									},
								}
							: u,
					),
				};
				if (
					!edit((inputs) => {
						if (
							!sameJson(inputs.energy_plant_setup, setupDocument) ||
							!sameJson(inputs.equipment_plant, plant)
						)
							throw new ApiError(409, "scenario_changed");
						return plantEnergyInputs(inputs, next);
					})
				)
					throw new ApiError(409, "scenario_changed");
				await flush();
				return;
			}
			if (!setup || joint) return;
			if (
				dc &&
				(dirty ||
					command.expected_revision !== draft.baseline.revision ||
					!sameJson(
						equipmentSelection,
						draft.baseline.inputs.equipment_selection,
					))
			) {
				setError(new ApiError(409, "product_evidence_changed"));
				return;
			}

			const restored = readScenarioDraft({
				...setup,
				coupling: dc ? "shared_dc" : "independent_ac",
				...(dc
					? {
							dc: {
								...restoreDcConditions(
									setup.dc,
									readDcLossScenario(parameters),
								),
								source_note: command.source_note,
								battery_port_id: parameters.battery_port_id,
								losses: Object.fromEntries(
									[
										"eta_bus_to_battery",
										"eta_battery_to_bus",
										"eta_store_charge",
										"eta_store_discharge",
										"eta_inverter_forward",
										"eta_inverter_reverse",
										"internal_aux_kw",
										"standing_loss_rate_per_hour",
									].map((key) => [key, parameters[key]]),
								),
							},
						}
					: {
							battery: Object.fromEntries(
								BATTERY_FIELDS.map((key) => [key, parameters[key]]),
							),
						}),
				...(dc ? {} : { source_note: command.source_note }),
				battery_binding: null,
			});
			const applied = edit((inputs) => {
				const current = restored;
				if (
					!sameJson(inputs.energy_scenario, setupDocument) ||
					!sameJson(
						inputs.equipment_selection,
						draft.history.current.equipment_selection,
					)
				)
					throw new Error("scenario_changed");
				return scenarioInputs(inputs, {
					...current,
					battery_binding: {
						asset_id: reply.asset.id,
						parameters,
						source_note: dc ? parameters.source_note : restored.source_note,
						...(dc && equipmentSelection
							? { equipment_selection: equipmentSelection }
							: {}),
					},
				});
			});
			if (!applied) throw new ApiError(409, "scenario_changed");
			await flush();
		} catch (cause) {
			if (client.isCurrentScope(session.query_scope)) setError(cause);
		}
	}
	async function calculate() {
		if (!canCalculate) return;
		const reply = await operations.start("runs/calculate", {
			expected_revision: draft.baseline.revision,
			input_contract: projectInputContract,
			inputs: authoredCalculationInputs(draft.history.current),
		});
		if (reply?.path === "runs/calculate") {
			runs.accepted(reply.run);
			setView("runs");
			openResults?.();
		}
	}
	async function applyEquipment(candidate: EquipmentCandidate) {
		const selectedRun = runs.run.data;
		if (
			!selectedRun ||
			selectedRun.project_id !== projectId ||
			blocked ||
			draft.pending ||
			draft.conflict
		)
			return;
		const snapshot = draft.history.current,
			original = equipmentContext(snapshot),
			instance = lifetime.current;
		if (hasPlant(snapshot) !== isPlantCandidate(candidate))
			throw new ApiError(422, "equipment_plant_single_candidate");
		const current = readEquipmentProducts(
			await client.query(
				"products/current",
				{ schema_version: 1 },
				session.query_scope,
			),
		);
		const demandInputs = candidate.demand?.metrics
			? readRunInputs(
					await client.query(
						"runs/inputs",
						{
							schema_version: 1,
							project_id: projectId,
							run_id: selectedRun.id,
						},
						session.query_scope,
					),
					selectedRun,
				)
			: null;
		if (demandInputs) requireUnchangedDemand(snapshot, demandInputs);
		if (
			!client.isCurrentScope(session.query_scope) ||
			instance !== lifetime.current
		)
			return;
		if (!current.prepared) throw new ApiError(409, "product_evidence_changed");
		const choice = {
			run_id: selectedRun.id,
			candidate_id: candidate.id,
			assessment_sha256: candidate.assessment_sha256,
		};
		let next: JsonObject;
		if (isPlantCandidate(candidate)) {
			next = adoptPlantCandidate(
				snapshot,
				candidate.plant,
				current.products,
				choice,
			);
		} else {
			if (
				Object.entries(candidate.selection.product_revisions).some(
					([id, revision]) =>
						!current.products.some(
							(p) => String(p.id) === id && p.product_revision === revision,
						),
				)
			)
				throw new ApiError(409, "product_evidence_changed");
			checkRetainedEquipment(equipmentDraft(snapshot), candidate.selection);
			const patch = Object.fromEntries(
				(
					[
						"inverter_product_id",
						"battery_product_id",
						"modules_per_stack",
						"parallel_stacks",
						"accessory_product_ids",
					] as const
				).map((key) => [key, candidate.selection[key]]),
			);
			next = changeEquipment(snapshot, {
				...patch,
				comparison_models: comparisonModels(equipmentDraft(snapshot)),
			});
			try {
				const selection = compileEquipment(
					equipmentDraft(next),
					current.products,
				);
				next = {
					...next,
					equipment_selection: selection,
					// Match the server's typed equality: absent and null both mean
					// the default procurement intent, while retain/replace remain distinct.
					...(sameJson(
						{ ...selection, equipment_use: selection.equipment_use ?? null },
						{
							...candidate.selection,
							equipment_use: candidate.selection.equipment_use ?? null,
						},
					)
						? { equipment_candidate: choice }
						: {}),
				};
			} catch {
				/* Updated sizing requirements remain editable for a new assessment. */
			}
		}
		const replacement = equipmentContext(next);
		const applied = edit((inputs) => {
			if (!sameJson(equipmentContext(inputs), original))
				throw new ApiError(409, "equipment_selection_changed");
			if (demandInputs) requireUnchangedDemand(inputs, demandInputs);
			const updated = applyEquipmentContext(inputs, replacement);
			if (
				!isPlantCandidate(candidate) &&
				typeof candidate.usable_energy_kwh === "number"
			) {
				const scenario =
					updated.energy_scenario === undefined
						? emptyScenario()
						: readScenarioDraft(updated.energy_scenario);
				if (demandInputs && candidate.demand?.metrics) {
					const initial = readObject(candidate.demand.metrics.stored_initial);
					return scenarioInputs(updated, {
						...scenario,
						battery: {
							...scenario.battery,
							usable_window_kwh: candidate.usable_energy_kwh,
						},
						initial_inventory: {
							pv_kwh: initial.pv_kwh as number,
							grid_kwh: initial.grid_kwh as number,
							initial_unknown_kwh: initial.initial_unknown_kwh as number,
							source_note: readObject(demandInputs.equipment_demand)
								.source_note as string,
						},
						battery_binding: null,
					});
				}
				return scenarioInputs(
					updated,
					useEquipmentCapacity(scenario, candidate.usable_energy_kwh),
				);
			}
			return updated;
		});
		if (!applied) throw new ApiError(409, "equipment_selection_changed");
		setError(null);
		chooseView("scenario");
		openResults?.();
	}
	async function generateReport(options: ReportOptions) {
		if (
			dirty ||
			draft.pending ||
			draft.conflict ||
			blocked ||
			!syntaxValid ||
			operations.busy ||
			operations.checking ||
			operations.storageFailed ||
			unconfirmed.length ||
			!client.isCurrentScope(session.query_scope)
		)
			return;
		const instance = lifetime.current;
		try {
			const reply = await operations.start("runs/report", {
				expected_revision: draft.baseline.revision,
				options,
			});
			if (
				reply?.path === "runs/report" &&
				instance === lifetime.current &&
				client.isCurrentScope(session.query_scope)
			) {
				runs.accepted(reply.run);
				setView("runs");
				openResults?.();
			}
		} catch (cause) {
			if (client.isCurrentScope(session.query_scope)) setError(cause);
		}
	}
	async function submitEquipment(
		path: "runs/find-equipment" | "runs/check-equipment",
	) {
		if (
			blocked ||
			draft.pending ||
			draft.conflict ||
			!syntaxValid ||
			!admitted ||
			operations.busy ||
			operations.checking ||
			operations.storageFailed ||
			unconfirmed.length
		)
			return;
		setError(null);
		try {
			const reply = await operations.start(path, {
				expected_revision: draft.baseline.revision,
				input_contract: projectInputContract,
				inputs: authoredDiscoveryInputs(draft.history.current),
			});
			if (reply?.path === path) {
				runs.accepted(reply.run);
				setView("runs");
				openResults?.();
			}
		} catch (cause) {
			if (client.isCurrentScope(session.query_scope)) setError(cause);
		}
	}
	async function startSolar(
		path:
			| "runs/weather"
			| "runs/pv"
			| "runs/pvgis-reference"
			| "runs/direct-beam"
			| "runs/geometric-pv",
	) {
		if (
			dirty ||
			draft.pending ||
			draft.conflict ||
			blocked ||
			!syntaxValid ||
			!client.isCurrentScope(session.query_scope) ||
			operations.busy ||
			operations.checking ||
			operations.storageFailed ||
			unconfirmed.length
		) {
			return;
		}
		try {
			const inputs = draft.baseline.inputs;
			const setup =
				path === "runs/pvgis-reference" ||
				path === "runs/geometric-pv" ||
				path === "runs/direct-beam"
					? null
					: readSolarSetup(inputs);
			if (path === "runs/geometric-pv") {
				if (
					session.runtime.models.geometric_pv_generation !== GEOMETRIC_PV_TASK
				)
					return;
				compileGeometricPv(geometricPvDraft(inputs), inputs.geometry);
			} else if (path === "runs/direct-beam") {
				if (session.runtime.models.direct_beam_visibility !== DIRECT_BEAM_TASK)
					return;
				const limits = readDirectBeamLimits(
					session.runtime.limits.direct_beam_visibility,
				);
				compileDirectBeam(directBeamDraft(inputs), limits);
			} else if (path === "runs/pvgis-reference") {
				if (
					session.runtime.models.pvgis_roof_reference !== PVGIS_REFERENCE_TASK
				)
					return;
				referenceRoof(inputs);
				if (
					!sameJson(
						compilePvgisReference(referenceDraft(inputs)),
						readPvgisReference(inputs.pvgis_reference),
					)
				)
					return;
			} else if (path === "runs/weather" && setup) {
				if (
					!sameJson(compileWeather(setup.weather), inputs.weather_acquisition)
				)
					return;
			} else if (setup) {
				if (
					!sameJson(compilePv(setup.pv, inputs.geometry), inputs.pv_generation)
				)
					return;
				checkPvWeather(inputs);
			}
			const instance = lifetime.current;
			const reply = await operations.start(path, {
				expected_revision: draft.baseline.revision,
			});
			if (
				reply?.path === path &&
				instance === lifetime.current &&
				client.isCurrentScope(session.query_scope)
			) {
				runs.accepted(reply.run);
				setView("runs");
				openResults?.();
			}
		} catch (cause) {
			if (client.isCurrentScope(session.query_scope)) setError(cause);
		}
	}
	function chooseView(next: EnergyView) {
		setView(next);
		if (next === "runs" && runs.runId) {
			runs.select(runs.runId);
			return;
		}
		const url = new URL(window.location.href);
		url.searchParams.set("energy_view", next);
		if (next !== "runs") url.searchParams.delete("run");
		if (next !== "comparison") url.searchParams.delete("compare");
		replacePlannerLocation(url);
	}
	function showEquipment() {
		if (
			!joint &&
			setup &&
			equipmentDraft(draft.history.current).operating_mode === null
		) {
			const mode = setup.schedule.some((period) => period.mode === "outage")
				? "backup"
				: setup.schedule.some((period) => period.mode === "connected")
					? "grid_connected"
					: null;
			if (mode)
				edit((inputs) => changeEquipment(inputs, { operating_mode: mode }));
		}
		if (openEquipment) openEquipment();
		else chooseView("equipment");
	}
	async function useRange() {
		if (!currentSetup || rangeFlight.current || !admitted) return;
		const controller = new AbortController(),
			instance = lifetime.current;
		rangeFlight.current = controller;
		setRangeBusy(true);
		setError(null);
		try {
			const profileRoles = (
				inputs: JsonObject,
				value: ScenarioDraft | PlantEnergyDraft,
			): ProfileRole[] => {
				const selected = readSelections(inputs.profile_selections).selected,
					dc =
						!isPvOnly(inputs) &&
						(value.coupling === "shared_dc" ||
							value.coupling === "plant_shared_dc"),
					inactive =
						isStorageOnly(inputs) ||
						(!dc &&
							value.schedule.every((period) => period.pv_enabled === false)),
					pvRoles: ProfileRole[] = inactive
						? []
						: joint && dc
							? (["pv_reference", "pv_available_ac"] as const).filter(
									(role) => !!selected[role],
								)
							: ["pv_available_ac"];
				return [
					...(value.schedule.some((period) => period.mode !== "outage")
						? ["gross_load" as const]
						: []),
					...pvRoles,
					...(value.aux_ac_kw == null ? ["aux_ac" as const] : []),
					...(value.schedule.some((period) => period.mode === "outage")
						? ["critical_load" as const]
						: []),
				];
			};
			const roles = profileRoles(draft.history.current, currentSetup);
			const ranges = await Promise.all(
				roles.map(async (role) => {
					const id = selections.selected[role];
					if (!id) throw new ApiError(422, "scenario_profiles_required");
					const asset = readAsset(
						await client.query(
							"assets/read",
							{ schema_version: 1, project_id: projectId, asset_id: id },
							session.query_scope,
							controller.signal,
						),
						projectId,
					);
					const preview = readPreview(
						await client.query(
							"profiles/preview",
							{
								schema_version: 1,
								project_id: projectId,
								asset_id: id,
								offset: 0,
								page_size: 1,
							},
							session.query_scope,
							controller.signal,
						),
						asset,
					);
					if (
						asset.id !== id ||
						(preview.measurement !== role &&
							!(
								role === "pv_reference" &&
								asset.purpose === "pvlib_reference_profile_v1" &&
								preview.measurement === "pv_available_ac"
							))
					)
						throw new ApiError(502, "profile_role_mismatch");
					return preview.summary;
				}),
			);
			if (
				instance !== lifetime.current ||
				!client.isCurrentScope(session.query_scope)
			)
				return;
			const range = sharedProfileRange(ranges);
			const applied = edit((inputs) => {
				if (hasPlant(inputs) !== joint)
					throw new ApiError(409, "scenario_changed");
				const selected = readSelections(inputs.profile_selections).selected;
				function applyRange<T extends ScenarioDraft | PlantEnergyDraft>(
					value: T,
				): T {
					if (
						!sameJson(profileRoles(inputs, value), roles) ||
						roles.some(
							(role) => selected[role] !== selections.selected[role],
						) ||
						!sameJson(
							value.schedule.map(({ id, start_utc, end_utc }) => ({
								id,
								start_utc,
								end_utc,
							})),
							currentSetup!.schedule.map(({ id, start_utc, end_utc }) => ({
								id,
								start_utc,
								end_utc,
							})),
						)
					)
						throw new ApiError(409, "scenario_changed");
					return {
						...value,
						schedule: value.schedule.map((period, index) => ({
							...period,
							...(index === 0 ? { start_utc: range.start_utc } : {}),
							...(index === value.schedule.length - 1
								? { end_utc: range.end_utc }
								: {}),
						})),
					};
				}
				return joint
					? plantEnergyInputs(
							inputs,
							applyRange(
								inputs.energy_plant_setup === undefined
									? jointContext.value!.setup
									: plantEnergyDraft(inputs, plantEnergyEquipment(inputs)),
							),
						)
					: scenarioInputs(
							inputs,
							applyRange(
								inputs.energy_scenario === undefined
									? setup!
									: readScenarioDraft(inputs.energy_scenario),
							),
						);
			});
			if (!applied) throw new ApiError(409, "scenario_changed");
		} catch (cause) {
			if (
				cause instanceof ApiError &&
				([401, 403].includes(cause.status) || cause.code === "session_changed")
			)
				recheck();
			if (
				instance === lifetime.current &&
				client.isCurrentScope(session.query_scope)
			)
				setError(cause);
		} finally {
			if (rangeFlight.current === controller) {
				rangeFlight.current = null;
				if (instance === lifetime.current) setRangeBusy(false);
			}
		}
	}
	return (
		<section
			className="sc-section sc-energy-workspace"
			id="sc-review"
			tabIndex={-1}
			aria-labelledby={
				equipmentFocus ? "sc-equipment-title" : "sc-calculations-heading"
			}
		>
			<div className="sc-section-heading" hidden={equipmentFocus}>
				<span className="sc-index">07</span>
				<div>
					<h2 id="sc-calculations-heading">
						{__("Energy calculation", "linker-tools")}
					</h2>
					<p>
						{__(
							"Calculate this project's energy flows over the selected periods. Each saved result keeps the inputs, sources and model used.",
							"linker-tools",
						)}
					</p>
				</div>
			</div>
			<div
				className="sc-energy-switch sc-work-toolbar"
				role="group"
				aria-label={__("Calculation workspace view", "linker-tools")}
				hidden={equipmentFocus}
			>
				<button
					type="button"
					hidden={storageOnly}
					aria-pressed={view === "weather"}
					onClick={() => chooseView("weather")}
				>
					{__("Weather source", "linker-tools")}
				</button>
				<button
					type="button"
					hidden={storageOnly}
					aria-pressed={
						view === "pv" ||
						view === "pvgis-reference" ||
						view === "geometric-pv"
					}
					onClick={() =>
						chooseView(
							selectedView === "pvgis-reference" ||
								selectedView === "geometric-pv"
								? selectedView
								: "pv",
						)
					}
				>
					{__("PV generation", "linker-tools")}
				</button>
				<button
					type="button"
					hidden={storageOnly}
					aria-pressed={view === "direct-beam"}
					onClick={() => chooseView("direct-beam")}
				>
					{__("Direct-beam visibility", "linker-tools")}
				</button>
				<button
					type="button"
					aria-pressed={view === "scenario"}
					onClick={() => chooseView("scenario")}
				>
					{__("Scenario settings", "linker-tools")}
				</button>
				<button
					type="button"
					aria-pressed={view === "equipment"}
					onClick={showEquipment}
				>
					{__("Equipment", "linker-tools")}
				</button>
				<button
					type="button"
					aria-pressed={view === "comparison"}
					disabled={
						session.runtime.models.comparison !== "frozen_energy_comparison_v1"
					}
					onClick={() => chooseView("comparison")}
				>
					{__("Compare calculations", "linker-tools")}
				</button>
				<button
					type="button"
					aria-pressed={view === "reports"}
					disabled={!session.runtime.models.report}
					onClick={() => chooseView("reports")}
				>
					{__("Planning report", "linker-tools")}
				</button>
				<button
					type="button"
					aria-pressed={view === "runs"}
					onClick={() => chooseView("runs")}
				>
					{__("Saved calculations", "linker-tools")}
				</button>
			</div>
			{Boolean(actionError) && (
				<div ref={errorTarget} className="sc-focus-target" tabIndex={-1}>
					<EnergyError
						error={actionError}
						openEquipment={showEquipment}
						openScenario={() => chooseView("scenario")}
					/>
				</div>
			)}
			{operations.storageFailed && (
				<Notice error>
					<p>
						{__(
							"This browser could not save or read the information needed to recover calculation requests. New requests are paused until this is available.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="sc-text-button"
						onClick={operations.refresh}
					>
						{__("Check browser storage", "linker-tools")}
					</button>
				</Notice>
			)}
			{operations.records.length > 0 && (
				<details
					className="sc-disclosure sc-energy-recovery sc-work-panel"
					open={unconfirmed.length > 0}
				>
					<summary>{__("Stored requests", "linker-tools")}</summary>
					{unconfirmed.length > 0 && (
						<p role="status">
							{__(
								"Recover the stored request below before starting a new calculation or report.",
								"linker-tools",
							)}
						</p>
					)}
					<p>
						{__(
							"Retrying a calculation uses its original request and saved input revision. Restoring storage settings replaces those settings in your open draft.",
							"linker-tools",
						)}
					</p>
					{operations.records.map((record) => (
						<div
							key={record.scope + record.path + record.key}
							className="sc-energy-recovery-row"
						>
							<span>
								{record.path === "battery/scenario"
									? __("Saved storage settings", "linker-tools")
									: record.path === "draft/apply"
										? sprintf(
												__(
													"Product transfer · input revision %d",
													"linker-tools",
												),
												Number(
													readPlanningOperation(record.path, record.body)
														.expected_revision,
												),
											)
										: sprintf(
												__("Calculation request · revision %d", "linker-tools"),
												Number(
													readPlanningOperation(record.path, record.body)
														.expected_revision,
												),
											)}
							</span>
							<button
								type="button"
								className="sc-button"
								disabled={operations.busy || blocked || !syntaxValid}
								onClick={() => void recover(record)}
							>
								{record.path === "battery/scenario"
									? __("Restore and retry storage settings", "linker-tools")
									: record.path === "draft/apply"
										? __("Retry transfer", "linker-tools")
										: __("Retry original calculation request", "linker-tools")}
							</button>
							<button
								type="button"
								className="sc-text-button"
								disabled={operations.busy || operations.checking}
								onClick={() => void operations.discard(record)}
							>
								{__("Discard stored request", "linker-tools")}
							</button>
							{record.resultId !== null && (
								<button
									type="button"
									className="sc-text-button"
									disabled={operations.busy || operations.checking}
									onClick={() => void operations.dismissAcknowledged(record)}
								>
									{__("Dismiss confirmed request", "linker-tools")}
								</button>
							)}
						</div>
					))}
				</details>
			)}
			<div hidden={view !== "direct-beam"}>
				<DirectBeamSetup
					draft={draft}
					locale={locale}
					edit={edit}
					session={session}
					client={client}
					active={active && view === "direct-beam"}
					disabled={blocked || operations.busy || !admitted}
					actionsDisabled={
						blocked ||
						!admitted ||
						!syntaxValid ||
						operations.busy ||
						operations.checking ||
						operations.storageFailed ||
						unconfirmed.length > 0
					}
					onValidity={setBeamValid}
					start={() => void startSolar("runs/direct-beam")}
					openWeather={() => chooseView("weather")}
					openDesign={openDesign}
				/>
			</div>
			<div hidden={view !== "weather"}>
				<WeatherSetup
					draft={draft}
					edit={edit}
					locale={locale}
					disabled={blocked || operations.busy || !admitted}
					actionsDisabled={
						blocked ||
						!admitted ||
						!syntaxValid ||
						operations.busy ||
						operations.checking ||
						operations.storageFailed ||
						unconfirmed.length > 0
					}
					valid={weatherValid}
					onValidity={setWeatherValid}
					onError={setError}
					start={() => void startSolar("runs/weather")}
				/>
			</div>
			<div
				hidden={
					view !== "pv" && view !== "pvgis-reference" && view !== "geometric-pv"
				}
			>
				<div
					className="sc-energy-switch sc-work-toolbar"
					role="group"
					aria-label={__("PV generation method", "linker-tools")}
				>
					<button
						type="button"
						aria-pressed={view === "pv"}
						onClick={() => chooseView("pv")}
					>
						{__("Weather-based PV reference", "linker-tools")}
					</button>
					<button
						type="button"
						aria-pressed={view === "pvgis-reference"}
						onClick={() => chooseView("pvgis-reference")}
					>
						{__("PVGIS annual AC reference", "linker-tools")}
					</button>
					<button
						type="button"
						aria-pressed={view === "geometric-pv"}
						onClick={() => chooseView("geometric-pv")}
					>
						{__("PV reference with roof shading", "linker-tools")}
					</button>
				</div>
				{view === "geometric-pv" ? (
					<GeometricPvSetup
						draft={draft}
						edit={edit}
						session={session}
						client={client}
						active={active && view === "geometric-pv"}
						locale={locale}
						disabled={blocked || operations.busy || !admitted}
						actionsDisabled={
							blocked ||
							!admitted ||
							!syntaxValid ||
							operations.busy ||
							operations.checking ||
							operations.storageFailed ||
							unconfirmed.length > 0
						}
						onValidity={setPvValid}
						start={() => void startSolar("runs/geometric-pv")}
						openDesign={openDesign}
						openWeather={() => chooseView("weather")}
					/>
				) : view === "pvgis-reference" ? (
					<PvgisReferenceSetup
						draft={draft}
						edit={edit}
						locale={locale}
						disabled={blocked || operations.busy || !admitted}
						actionsDisabled={
							blocked ||
							!admitted ||
							!syntaxValid ||
							operations.busy ||
							operations.checking ||
							operations.storageFailed ||
							unconfirmed.length > 0
						}
						onValidity={setPvValid}
						start={() => void startSolar("runs/pvgis-reference")}
						openDesign={openDesign}
						supported={
							session.runtime.models.pvgis_roof_reference ===
							PVGIS_REFERENCE_TASK
						}
					/>
				) : (
					<PvSetup
						draft={draft}
						edit={edit}
						locale={locale}
						disabled={blocked || operations.busy || !admitted}
						actionsDisabled={
							blocked ||
							!admitted ||
							!syntaxValid ||
							operations.busy ||
							operations.checking ||
							operations.storageFailed ||
							unconfirmed.length > 0
						}
						valid={pvValid}
						onValidity={setPvValid}
						onError={setError}
						start={() => void startSolar("runs/pv")}
						openDesign={openDesign}
					/>
				)}
			</div>
			<div
				hidden={view !== "equipment"}
				id="sc-system"
				className="sc-focus-target"
				tabIndex={-1}
			>
				<EquipmentWorkspace
					draft={draft}
					edit={edit}
					client={client}
					session={session}
					scope={session.query_scope}
					standalone={equipmentFocus}
					active={active && view === "equipment"}
					locale={locale}
					disabled={blocked || operations.busy || !admitted}
					actionsDisabled={
						blocked ||
						Boolean(draft.pending || draft.conflict) ||
						operations.busy ||
						operations.checking ||
						operations.storageFailed ||
						unconfirmed.length > 0
					}
					onValidity={setEquipmentValid}
					inputErrors={
						actionError instanceof ApiError ? actionError.fields : []
					}
					onError={(cause, changed) => {
						if (cause !== null) setError(cause);
						else {
							setError((previous: unknown) =>
								clearInputFields(previous, changed),
							);
							operations.clearError(changed);
						}
					}}
					search={() => void submitEquipment("runs/find-equipment")}
					check={() => void submitEquipment("runs/check-equipment")}
					searchEnabled={
						hasPlant(draft.history.current)
							? session.runtime.models.equipment_plant_search ===
								"declared_plant_v1"
							: session.runtime.models.equipment_search === SEARCH_TASK
					}
				/>
			</div>
			<div hidden={view !== "scenario"} ref={scenarioTarget}>
				{Boolean(joint ? jointContext.error : parsed.error) && (
					<Notice error>
						{joint
							? __(
									"Review the equipment plan and storage settings for each unit.",
									"linker-tools",
								)
							: __(
									"This scenario-settings format cannot be edited here. Its saved input and calculation history remain available.",
									"linker-tools",
								)}
					</Notice>
				)}
				{currentSetup && (
					<>
						<div className="sc-setup-layout">
							<aside className="sc-setup-nav">
								<nav aria-label={__("Scenario settings", "linker-tools")}>
									<ol className="sc-scenario-steps">
										{(pvOnly
											? (["storage", "operation"] as const)
											: (["storage", "initial", "operation"] as const)
										).map((step, index) => (
											<li
												key={step}
												aria-current={
													section === step ||
													(pvOnly &&
														section === "initial" &&
														step === "storage")
														? "step"
														: undefined
												}
											>
												<button
													type="button"
													disabled={!syntaxValid}
													aria-current={
														section === step ||
														(pvOnly &&
															section === "initial" &&
															step === "storage")
															? "step"
															: undefined
													}
													aria-controls="sc-energy-chapter"
													onClick={() => setSection(step)}
												>
													<span>{String(index + 1).padStart(2, "0")}</span>
													{step === "storage"
														? pvOnly
															? __("Solar-only energy flows", "linker-tools")
															: __("Storage", "linker-tools")
														: step === "initial"
															? __("Starting state", "linker-tools")
															: __("Operation", "linker-tools")}
												</button>
											</li>
										))}
									</ol>
								</nav>
								<section className="sc-scenario-sources sc-work-panel">
									<h3 className="sc-work-panel-heading">
										{__("Interval sources", "linker-tools")}
									</h3>
									<ul>
										{(
											[
												"gross_load",
												...(currentSetup.schedule.some(
													(period) => period.mode === "outage",
												)
													? ["critical_load" as const]
													: []),
												joint && sharedDc ? "pv_reference" : "pv_available_ac",
												"aux_ac",
											] as const
										)
											.filter(
												(role) =>
													(role !== "gross_load" ||
														currentSetup.schedule.some(
															(period) => period.mode !== "outage",
														)) &&
													(!pvInactive ||
														(role !== "pv_available_ac" &&
															role !== "pv_reference")) &&
													(role !== "aux_ac" || currentSetup.aux_ac_kw == null),
											)
											.map((role) => (
												<li key={role}>
													<span>
														{role === "pv_available_ac" && !joint && sharedDc
															? __("PV generation", "linker-tools")
															: measurementLabel(role)}
													</span>
													<strong>
														{selections.selected[role]
															? __("Selected in this draft", "linker-tools")
															: __("Required", "linker-tools")}
													</strong>
												</li>
											))}
									</ul>
									<button
										type="button"
										className="sc-text-button"
										onClick={openProfiles}
										disabled={!syntaxValid}
									>
										{__("Review energy inputs", "linker-tools")}
									</button>
								</section>
							</aside>
							<div
								className="sc-setup-content sc-work-main"
								id="sc-energy-chapter"
							>
								{pvOnly ? (
									<SolarEnergySetup
										section={section === "operation" ? "operation" : "storage"}
										inputPath={schedulePath}
										value={currentSetup}
										hasAuxiliaryProfile={Boolean(selections.selected.aux_ac)}
										locale={locale}
										disabled={blocked || operations.busy || !admitted}
										onChange={(changes) => {
											if (joint && jointContext.value)
												changeJoint({
													...jointContext.value.setup,
													...changes,
												});
											else if (setup) change({ ...setup, ...changes });
										}}
										onValidity={setCompactValid}
										useProfileRange={() => void useRange()}
										rangeBusy={rangeBusy}
										inputErrors={scenarioErrors}
									/>
								) : (
									<>
										{joint && jointContext.value ? (
											<PlantEnergyForm
												storageOnly={storageOnly}
												referenceCapacitySupported={
													session.runtime.models.capacity_reference ===
													REFERENCE_CAPACITY
												}
												value={jointContext.value.setup}
												plant={jointContext.value.plant}
												converters={converterIds}
												section={section}
												locale={locale}
												disabled={blocked || operations.busy || !admitted}
												onChange={changeJoint}
												onValidity={setScenarioValid}
												useProfileRange={() => void useRange()}
												rangeBusy={rangeBusy}
												inputErrors={scenarioErrors}
												openEquipment={showEquipment}
												client={client}
												scope={session.query_scope}
												active={active && view === "scenario"}
											/>
										) : (
											setup && (
												<ScenarioForm
													storageOnly={storageOnly}
													referenceCapacitySupported={
														session.runtime.models.capacity_reference ===
														REFERENCE_CAPACITY
													}
													client={client}
													scope={session.query_scope}
													active={active && view === "scenario"}
													equipmentSelection={equipmentForEditing}
													converters={converterIds}
													key={setup.coupling ?? "independent_ac"}
													openEquipment={showEquipment}
													value={setup}
													section={section}
													locale={locale}
													disabled={blocked || operations.busy || !admitted}
													onChange={change}
													onValidity={setScenarioValid}
													useProfileRange={() => void useRange()}
													rangeBusy={rangeBusy}
													inputErrors={scenarioErrors}
												/>
											)
										)}
									</>
								)}
								{joint && !jointAvailable && (
									<Notice>
										{__(
											"Joint storage calculation is unavailable in this service version. Your equipment plan remains available.",
											"linker-tools",
										)}
									</Notice>
								)}
								<div className="sc-energy-submit sc-work-panel sc-work-toolbar">
									<p>
										{__(
											"Calculate using the current project inputs. The result retains its inputs and sources.",
											"linker-tools",
										)}
									</p>
									<button
										type="button"
										className="sc-button sc-primary"
										disabled={!canCalculate}
										onClick={() => void calculate()}
									>
										{operations.busy
											? __("Confirming request…", "linker-tools")
											: __("Calculate energy flows", "linker-tools")}
									</button>
								</div>
							</div>
						</div>
					</>
				)}
			</div>
			<div hidden={view !== "comparison"}>
				<div className="sc-actions">
					{runs.hasPrevious && (
						<button
							type="button"
							className="sc-text-button"
							disabled={runs.page.isFetching}
							onClick={runs.first}
						>
							{__("Latest calculations", "linker-tools")}
						</button>
					)}
					{runs.page.data?.next && (
						<button
							type="button"
							className="sc-text-button"
							disabled={runs.page.isFetching}
							onClick={runs.next}
						>
							{__("Earlier calculations", "linker-tools")}
						</button>
					)}
				</div>
				<EnergyComparison
					key={`${projectId}:${session.query_scope}`}
					projectId={projectId}
					runs={runs.page.data?.items ?? []}
					client={client}
					session={session}
					active={active && view === "comparison"}
					locale={locale}
					recheck={recheck}
					reportDisabled={
						dirty ||
						!!draft.pending ||
						!!draft.conflict ||
						blocked ||
						!syntaxValid ||
						operations.busy ||
						operations.checking ||
						operations.storageFailed ||
						Boolean(unconfirmed.length) ||
						!session.runtime.models.report
					}
					generateReport={generateReport}
					openRun={(id) => {
						runs.select(id);
						setView("runs");
					}}
				/>
			</div>
			<div hidden={view !== "reports"}>
				{runs.page.error && (
					<Notice error>
						<p>
							{__(
								"Saved calculation history could not be refreshed.",
								"linker-tools",
							)}
						</p>
						<button
							type="button"
							className="sc-text-button"
							onClick={() => void runs.page.refetch()}
						>
							{__("Refresh calculation history", "linker-tools")}
						</button>
					</Notice>
				)}
				{!runs.page.data && !runs.page.error && (
					<p role="status">
						{__("Reading saved calculations…", "linker-tools")}
					</p>
				)}
				<div className="sc-run-pagination">
					{runs.hasPrevious && (
						<button
							type="button"
							className="sc-text-button"
							disabled={runs.page.isFetching}
							onClick={runs.first}
						>
							{__("Latest calculations", "linker-tools")}
						</button>
					)}
					{runs.page.data?.next && (
						<button
							type="button"
							className="sc-text-button"
							disabled={runs.page.isFetching}
							onClick={runs.next}
						>
							{__("Earlier calculations", "linker-tools")}
						</button>
					)}
				</div>

				<PlanningReportForm
					runs={runs.page.data?.items ?? []}
					locale={locale}
					hasCandidate={Boolean(draft.baseline.inputs.equipment_candidate)}
					hasWiring={Boolean(
						draft.baseline.inputs.pv_string_plan ||
						draft.baseline.inputs.pv_plant_string_plan,
					)}
					hasInstallation={hasReportableInstallation(
						readInstallation(draft.baseline.inputs.installation),
					)}
					disabled={
						dirty ||
						!!draft.pending ||
						!!draft.conflict ||
						blocked ||
						!syntaxValid ||
						operations.busy ||
						operations.checking ||
						operations.storageFailed ||
						unconfirmed.length > 0 ||
						!session.runtime.models.report
					}
					generate={generateReport}
				/>
			</div>
			<div className="sc-energy-runs" hidden={view !== "runs"}>
				{runs.page.error && (
					<Notice error>
						<p>
							{__(
								"Saved calculation history could not be refreshed.",
								"linker-tools",
							)}
						</p>
						<button
							type="button"
							className="sc-text-button"
							onClick={() => void runs.page.refetch()}
						>
							{__("Refresh calculation history", "linker-tools")}
						</button>
					</Notice>
				)}
				{!runs.page.data && !runs.page.error && (
					<p role="status">
						{__("Reading saved calculations…", "linker-tools")}
					</p>
				)}
				<div className="sc-work-grid">
					{runs.page.data && (
						<aside className="sc-run-history sc-work-aside sc-work-panel">
							<h3 className="sc-work-panel-heading">
								{__("Calculation history", "linker-tools")}
							</h3>
							{!runs.page.data.items.length && (
								<p>
									{__(
										"No saved calculation is available on this page.",
										"linker-tools",
									)}
								</p>
							)}
							{runs.page.data.items.map((run) => (
								<button
									type="button"
									key={run.id}
									aria-pressed={runs.runId === run.id}
									onClick={() => runs.select(run.id)}
								>
									<strong>
										{sprintf(__("Revision %d", "linker-tools"), run.revision)}
									</strong>
									{run.task_kind && <span>{taskLabel(run.task_kind)}</span>}
									<span>{runStateLabel(run.state, run.task_kind)}</span>
									<small>
										{new Intl.DateTimeFormat(locale, {
											dateStyle: "short",
											timeStyle: "short",
										}).format(run.created_at * 1000)}
									</small>
								</button>
							))}
							<div className="sc-actions">
								{runs.hasPrevious && (
									<button
										type="button"
										className="sc-text-button"
										onClick={runs.first}
									>
										{__("Latest calculations", "linker-tools")}
									</button>
								)}
								{runs.page.data.next && (
									<button
										type="button"
										className="sc-text-button"
										onClick={runs.next}
									>
										{__("Earlier calculations", "linker-tools")}
									</button>
								)}
							</div>
						</aside>
					)}
					<div ref={runTarget} className="sc-run-content sc-work-main">
						{runs.run.error && (
							<Notice error>
								<p>
									{__(
										"The selected calculation could not be refreshed. Any visible state is the last confirmed response.",
										"linker-tools",
									)}
								</p>
								<button
									type="button"
									className="sc-text-button"
									onClick={() => void runs.run.refetch()}
								>
									{__("Refresh calculation status", "linker-tools")}
								</button>
							</Notice>
						)}
						{runs.runId && !runs.run.data && !runs.run.error && (
							<p role="status">
								{__("Reading the saved calculation…", "linker-tools")}
							</p>
						)}
						{runs.run.data && (
							<>
								{runTask(runs.run.data) === DIRECT_BEAM_TASK ? (
									<DirectBeamResult
										key={runs.run.data.id}
										run={runs.run.data}
										session={session}
										client={client}
										locale={locale}
										sceneModuleUrl={sceneModuleUrl}
									/>
								) : runTask(runs.run.data) === PVGIS_REFERENCE_TASK ? (
									<PvgisReferenceResult
										key={runs.run.data.id}
										run={runs.run.data}
										inputs={draft.history.current}
										edit={edit}
										session={session}
										client={client}
										recheck={recheck}
										locale={locale}
										blocked={blocked || !syntaxValid}
										active={active && view === "runs"}
									/>
								) : [WEATHER_TASK, PV_TASK, GEOMETRIC_PV_TASK].includes(
										runTask(runs.run.data) ?? "",
								  ) ? (
									<PreparationResult
										key={runs.run.data.id}
										run={runs.run.data}
										inputs={draft.history.current}
										edit={edit}
										session={session}
										client={client}
										recheck={recheck}
										locale={locale}
										blocked={blocked || !syntaxValid}
										active={active && view === "runs"}
									/>
								) : runTask(runs.run.data) === REPORT_TASK ? (
									<PlanningReportResult
										key={runs.run.data.id}
										run={runs.run.data}
										client={client}
										scope={session.query_scope}
										recheck={recheck}
										operations={operations}
										current={
											!dirty &&
											!draft.pending &&
											runs.run.data.revision === draft.baseline.revision
										}
										blocked={blocked}
										locale={locale}
									/>
								) : runTask(runs.run.data) === SEARCH_TASK ? (
									<EquipmentSearchResult
										key={runs.run.data.id}
										run={runs.run.data}
										locale={locale}
										dirty={dirty || Boolean(draft.pending)}
										confirmedRevision={draft.baseline.revision}
										client={client}
										scope={session.query_scope}
										disabled={
											blocked ||
											!!draft.pending ||
											!!draft.conflict ||
											operations.busy ||
											!syntaxValid
										}
										apply={applyEquipment}
										plantActive={hasPlant(draft.history.current)}
										projectCandidate={readObject(
											draft.history.current.equipment_candidate ?? {},
										)}
										onError={setError}
									/>
								) : runTask(runs.run.data) === EQUIPMENT_TASK ? (
									<EquipmentResult
										run={runs.run.data}
										locale={locale}
										dirty={dirty || Boolean(draft.pending)}
										confirmedRevision={draft.baseline.revision}
										certificateSources={
											<CertificateEvidence
												client={client}
												scope={session.query_scope}
												run={runs.run.data}
											/>
										}
									/>
								) : (
									<>
										<RunResult
											run={runs.run.data}
											locale={locale}
											dirty={dirty || Boolean(draft.pending)}
											confirmedRevision={draft.baseline.revision}
											certificateSources={
												<CertificateEvidence
													client={client}
													scope={session.query_scope}
													run={runs.run.data}
												/>
											}
										/>
										{runs.run.data.state === "succeeded" &&
											typeof runs.run.data.result?.trace_sha256 ===
												"string" && (
												<TraceExplorer
													key={runs.run.data.id}
													run={runs.run.data}
													client={client}
													session={session}
													locale={locale}
													active={active && view === "runs"}
												/>
											)}
										<RunBasis
											key={runs.run.data.id}
											run={runs.run.data}
											session={session}
											client={client}
											recheck={recheck}
											locale={locale}
										/>
									</>
								)}
								{runPending(runs.run.data.state) && (
									<button
										type="button"
										className="sc-button"
										disabled={runs.cancelPending}
										onClick={() => void runs.cancel()}
									>
										{runs.cancelBusy
											? __("Confirming cancellation…", "linker-tools")
											: __("Cancel calculation", "linker-tools")}
									</button>
								)}
								{runs.cancelError && (
									<Notice error>
										{__(
											"Cancellation could not be confirmed. The calculation may still be running; its server status can be refreshed.",
											"linker-tools",
										)}
									</Notice>
								)}
							</>
						)}
					</div>
				</div>
			</div>
		</section>
	);
}
