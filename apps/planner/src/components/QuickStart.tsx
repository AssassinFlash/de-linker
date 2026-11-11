import { useCallback, useEffect, useRef, useState } from "react";
import type { Configuration } from "../data/config.ts";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { DraftStore } from "../data/DraftStore.ts";
import type { Json, JsonObject, Project, Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { readObject, readProject, wire } from "../data/readProtocol.ts";
import { useProjectDraft } from "../data/useProjectDraft.ts";
import { usePlanningOperations } from "../data/usePlanningOperations.ts";
import { readRun, runPending } from "../data/planningProtocol.ts";
import type { PlanningRun } from "../data/planningProtocol.ts";
import type { EquipmentCandidate } from "../data/equipmentSearch.ts";
import { isPlantCandidate } from "../data/equipmentSearch.ts";
import type { EquipmentSelection } from "../domain/equipment.ts";
import { readEquipmentProducts } from "../data/equipmentProducts.ts";
import { emptyBrief, readBrief } from "../domain/brief.ts";
import { editDraft, projectInputContract } from "../domain/draft.ts";
import {
	DEFAULT_MODULE_TIER,
	MODULE_TIERS,
	tierFor,
} from "../domain/moduleTiers.ts";
import {
	changeEquipment,
	compileEquipment,
	equipmentDraft,
} from "../domain/equipment.ts";
import { compileEquipmentRequirements } from "../domain/equipmentRequirements.ts";
import { __, sprintf } from "../i18n.ts";
import { Icon } from "./Icon.tsx";
import { Notice } from "./Notice.tsx";
import { EquipmentSearchResult } from "./equipment/EquipmentSearchResult.tsx";
import { EquipmentResult } from "./equipment/EquipmentResult.tsx";
import { PlanningReportResult } from "./energy/PlanningReportResult.tsx";
import { DraftTransferButton } from "./energy/DraftTransferButton.tsx";

/**
 * One screen, one button. The customer picks from lists and the screen runs the
 * existing planning operations in their documented order, stopping at the first
 * operation that cannot complete and keeping every confirmed result.
 *
 * What this screen can and cannot derive is declared, not guessed:
 *  - Equipment search needs only declared requirements, so it always runs.
 *  - Weather and PV need WGS 84 coordinates plus a drawn roof layout; the
 *    location field is free text until the Places integration lands, so those
 *    steps are reported as needing roof data instead of sending a request that
 *    would be refused.
 *  - The energy calculation needs imported interval profiles for total load,
 *    available PV and auxiliary demand. An annual figure is not an interval
 *    series, so that step reports its missing sources rather than inventing a
 *    synthetic profile that would be presented as a measurement.
 */

export const QUICK_START_PV_SIZES = [
	5, 8, 10, 12, 15, 20, 30, 50, 80, 100,
] as const;
export const QUICK_START_ORIENTATIONS = [
	"south_30",
	"south_15",
	"east_west_10",
	"flat_0",
] as const;
export const QUICK_START_RESIDENTIAL_KWH = [
	3500, 5000, 7500, 10000, 15000,
] as const;
export const QUICK_START_COMMERCIAL_KWH = [
	30000, 50000, 100000, 250000, 500000,
] as const;
export const QUICK_START_GOALS = [
	"self_use",
	"backup",
	"peak_shaving",
] as const;

export type QuickStartOrientation = (typeof QUICK_START_ORIENTATIONS)[number];
export type QuickStartGoal = (typeof QUICK_START_GOALS)[number];
export type QuickStartProjectType = "residential" | "commercial";

export interface QuickStartChoices {
	readonly projectType: QuickStartProjectType;
	readonly pvKwp: number;
	readonly orientation: QuickStartOrientation;
	readonly moduleTierId: string;
	readonly annualKwh: number;
	readonly phase: 1 | 3;
	readonly goal: QuickStartGoal;
	readonly location: string;
}

/** Everything except the location has a default, so the screen opens usable. */
export function quickStartDefaults(): QuickStartChoices {
	return {
		projectType: "residential",
		pvKwp: 10,
		orientation: "south_30",
		moduleTierId: DEFAULT_MODULE_TIER.id,
		annualKwh: 5000,
		phase: 3,
		goal: "self_use",
		location: "",
	};
}

/** The location is the only field without a default; it names the site. */
export function quickStartReady(choices: QuickStartChoices): boolean {
	return choices.location.trim().length > 0;
}

export function quickStartAnnualOptions(
	projectType: QuickStartProjectType,
): readonly number[] {
	return projectType === "commercial"
		? QUICK_START_COMMERCIAL_KWH
		: QUICK_START_RESIDENTIAL_KWH;
}

export function quickStartPhaseLabel(phase: 1 | 3): string {
	return phase === 1
		? __("Single-phase", "linker-tools")
		: __("Three-phase", "linker-tools");
}

export function quickStartGoalLabel(goal: QuickStartGoal): string {
	switch (goal) {
		case "backup":
			return __("Keep the lights on when the grid fails", "linker-tools");
		case "peak_shaving":
			return __("Cut commercial peak demand", "linker-tools");
		default:
			return __("Use as much of my own solar as possible", "linker-tools");
	}
}

export function quickStartOrientationLabel(
	orientation: QuickStartOrientation,
): string {
	switch (orientation) {
		case "south_15":
			return __("South-facing, 15°", "linker-tools");
		case "east_west_10":
			return __("East–west, 10°", "linker-tools");
		case "flat_0":
			return __("Flat roof, 0°", "linker-tools");
		default:
			return __("South-facing, 30°", "linker-tools");
	}
}

/**
 * Declared sizing assumption, not a product or engineering fact. The number is
 * the storage window this screen asks the search to fill, derived from the
 * customer's own annual consumption: one day of average demand for self-use,
 * one and a half days when backup matters, half a day for peak shaving (the
 * shaving window, not a daily cycle). The full workbench replaces it with the
 * customer's own figures.
 */
export const QUICK_START_SIZING_NOTE =
	"QuickStart planning assumption: storage window derived from the customer's declared annual consumption and chosen system goal. Not a product specification and not an engineering result.";

export function quickStartSizing(choices: QuickStartChoices): {
	readonly usableKwh: number;
	readonly dischargeKw: number;
} {
	const days =
		choices.goal === "backup" ? 1.5 : choices.goal === "peak_shaving" ? 0.5 : 1;
	const daily = choices.annualKwh / 365;
	const usableKwh = Math.max(3, Math.round(daily * days * 10) / 10);
	// Discharge is bounded by the array it is paired with and by the window it
	// drains in one hour; the search still qualifies real products against it.
	const dischargeKw =
		Math.round(Math.min(choices.pvKwp * 0.6, usableKwh) * 10) / 10;
	return { usableKwh, dischargeKw };
}

export function quickStartInputs(choices: QuickStartChoices): JsonObject {
	const brief = emptyBrief();
	const sizing = quickStartSizing(choices);
	const setup = {
		...equipmentDraft({}),
		grid_phase: choices.phase,
		operating_mode: choices.goal === "self_use" ? "grid_connected" : "backup",
		pv_dc_kw: choices.pvKwp,
		required_usable_kwh: sizing.usableKwh,
		required_discharge_ac_kw: sizing.dischargeKw,
	};
	const inputs: JsonObject = {
		brief: {
			...brief,
			project_use:
				choices.projectType === "commercial" ? "commercial" : "residential",
			system_scope: "new_pv_storage",
			site: {
				...brief.site,
				location_label: choices.location.trim(),
			},
			annual_load: {
				kwh: choices.annualKwh,
				basis: "user_estimate",
				source_note: __(
					"Declared on the one-screen start form.",
					"linker-tools",
				),
			},
			project_note: sprintf(
				__("Planned orientation: %s", "linker-tools"),
				quickStartOrientationLabel(choices.orientation),
			),
		},
		equipment_setup: setup,
		equipment_requirements: compileEquipmentRequirements(setup),
	};
	return inputs;
}

/**
 * Re-planning an existing project keeps everything this screen does not own:
 * roof geometry, imported profiles, solar setup, country rules and any chosen
 * products. Only the declared planning keys below are replaced.
 */
export function mergeQuickStartInputs(
	existing: JsonObject,
	choices: QuickStartChoices,
): JsonObject {
	const next = quickStartInputs(choices);
	let currentBrief: JsonObject;
	try {
		currentBrief = readBrief(existing.brief);
	} catch {
		currentBrief = emptyBrief();
	}
	let currentSetup: JsonObject;
	try {
		currentSetup = equipmentDraft(existing);
	} catch {
		currentSetup = equipmentDraft({});
	}
	const declared = readObject(next.equipment_setup);
	const setup: JsonObject = {
		...currentSetup,
		grid_phase: declared.grid_phase ?? null,
		operating_mode: declared.operating_mode ?? null,
		pv_dc_kw: declared.pv_dc_kw ?? null,
		required_usable_kwh: declared.required_usable_kwh ?? null,
		required_discharge_ac_kw: declared.required_discharge_ac_kw ?? null,
	};
	const note =
		typeof currentBrief.project_note === "string" &&
		currentBrief.project_note.trim()
			? currentBrief.project_note
			: String(readObject(next.brief).project_note ?? "");
	const site = readObject(currentBrief.site);
	const { equipment_candidate: _replaced, ...rest } = existing;
	return {
		...rest,
		brief: {
			...currentBrief,
			system_scope: currentBrief.system_scope ?? "new_pv_storage",
			site: { ...site, location_label: choices.location.trim() },
			annual_load: readObject(readObject(next.brief).annual_load),
			project_note: note,
		},
		equipment_setup: setup,
		equipment_requirements: compileEquipmentRequirements(setup),
	};
}

/** Choices read back from a saved project, so reopening shows its own plan. */
export function quickStartChoicesFrom(inputs: JsonObject): QuickStartChoices {
	const defaults = quickStartDefaults();
	const brief = (() => {
		try {
			return readBrief(inputs.brief);
		} catch {
			return emptyBrief();
		}
	})();
	const setup = (() => {
		try {
			return equipmentDraft(inputs);
		} catch {
			return equipmentDraft({});
		}
	})();
	const annual = Number(brief.annual_load.kwh);
	const phase = setup.grid_phase === 1 ? 1 : 3;
	const pv = Number(setup.pv_dc_kw);
	return {
		...defaults,
		projectType:
			brief.project_use === "commercial" ? "commercial" : "residential",
		pvKwp: QUICK_START_PV_SIZES.includes(pv as never) ? pv : defaults.pvKwp,
		annualKwh: quickStartAnnualOptions(
			brief.project_use === "commercial" ? "commercial" : "residential",
		).includes(annual)
			? annual
			: (quickStartAnnualOptions(
					brief.project_use === "commercial" ? "commercial" : "residential",
				)[1] ?? defaults.annualKwh),
		phase,
		goal: setup.operating_mode === "backup" ? "backup" : "self_use",
		location:
			typeof brief.site.location_label === "string"
				? brief.site.location_label
				: "",
	};
}

export function quickStartTitle(choices: QuickStartChoices): string {
	const tier = tierFor(Number(choices.moduleTierId.split("_")[1]));
	return sprintf(
		__("%1$s · %2$s kWp · %3$s", "linker-tools"),
		choices.projectType === "commercial"
			? __("Commercial", "linker-tools")
			: __("Residential", "linker-tools"),
		String(choices.pvKwp),
		choices.location.trim() || tier.model,
	);
}

export type QuickStartStepId =
	| "save"
	| "weather"
	| "pv"
	| "scenario"
	| "energy"
	| "search"
	| "qualify"
	| "report";

export interface QuickStartStep {
	readonly id: QuickStartStepId;
	readonly label: string;
}

/** The order the engine expects, listed once so the screen cannot drift. */
export function quickStartSteps(): readonly QuickStartStep[] {
	return [
		{ id: "save", label: __("Save the project", "linker-tools") },
		{ id: "weather", label: __("Fetch typical-year weather", "linker-tools") },
		{ id: "pv", label: __("Model the roof generation", "linker-tools") },
		{
			id: "scenario",
			label: __("Prepare the storage scenario", "linker-tools"),
		},
		{ id: "energy", label: __("Calculate self-consumption", "linker-tools") },
		{ id: "search", label: __("Find matching equipment", "linker-tools") },
		{
			id: "qualify",
			label: __("Check the chosen combination", "linker-tools"),
		},
		{ id: "report", label: __("Build the report", "linker-tools") },
	];
}

/** Equipment search publishes single-system and plant candidates; this screen
 * only adopts single systems, so the selection member is narrowed here once. */
type SingleSelectionCandidate = EquipmentCandidate & {
	readonly selection: EquipmentSelection;
};
export function singleSelectionCandidate(
	candidate: EquipmentCandidate | null,
): SingleSelectionCandidate | null {
	return candidate && !isPlantCandidate(candidate)
		? (candidate as SingleSelectionCandidate)
		: null;
}

type StepState =
	| { readonly kind: "pending" }
	| { readonly kind: "running" }
	| { readonly kind: "done"; readonly detail?: string }
	| {
			readonly kind: "blocked";
			readonly detail: string;
			readonly retry: boolean;
	  };

const POLL_MS = 1000;
const POLL_LIMIT = 300; // Visible wait policy for one step, not a model limit.

function wait(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

export function QuickStart({
	session,
	client,
	store,
	config,
	recheck,
	created,
	openWorkbench,
	onOpenProject,
	close,
	project: existingProject = null,
}: {
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	config: Configuration;
	recheck: () => void;
	created?: ((project: Project) => boolean) | undefined;
	openWorkbench?: ((projectId: string) => void) | undefined;
	onOpenProject?: ((projectId: string) => void) | undefined;
	close?: (() => void) | undefined;
	/** Re-plan an open project instead of creating another one. */
	project?: Project | null | undefined;
}) {
	const [choices, setChoices] = useState<QuickStartChoices>(() =>
		existingProject
			? quickStartChoicesFrom(existingProject.inputs)
			: quickStartDefaults(),
	);
	const [project, setProject] = useState<Project | null>(null);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const [title, setTitle] = useState<string | null>(null);
	const lifetime = useRef(0);
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
		};
	}, []);
	const ready = quickStartReady(choices);
	function change<K extends keyof QuickStartChoices>(
		key: K,
		value: QuickStartChoices[K],
	) {
		setChoices((previous) => {
			if (key === "projectType") {
				const type = value as QuickStartProjectType;
				const annual = quickStartAnnualOptions(type);
				return {
					...previous,
					projectType: type,
					annualKwh: annual.includes(previous.annualKwh)
						? previous.annualKwh
						: type === "commercial"
							? 50000
							: 5000,
				};
			}
			return { ...previous, [key]: value };
		});
		setFailure(null);
	}
	async function start() {
		if (!ready || busy || !client.isCurrentScope(session.query_scope)) return;
		const instance = lifetime.current;
		setBusy(true);
		setFailure(null);
		try {
			if (existingProject) {
				// Re-planning writes the declared keys onto the opened revision; the
				// run chain then continues from the confirmed reply.
				const value = readProject(
					await client.send(
						"projects/revise",
						wire(
							{
								schema_version: 1,
								input_contract: projectInputContract,
								project_id: existingProject.id,
								expected_revision: existingProject.revision,
								inputs: mergeQuickStartInputs(existingProject.inputs, choices),
								key: crypto.randomUUID(),
							},
							session.runtime.limits.max_json_depth,
							session.runtime.limits.max_body_bytes,
						),
						session.query_scope,
					),
				);
				if (
					instance !== lifetime.current ||
					!client.isCurrentScope(session.query_scope)
				)
					return;
				setTitle(value.title);
				setProject(value);
				return;
			}
			const inputs = quickStartInputs(choices);
			const value = readProject(
				await client.send(
					"projects/create",
					wire(
						{
							schema_version: 1,
							input_contract: projectInputContract,
							title: quickStartTitle(choices),
							inputs,
							key: crypto.randomUUID(),
						},
						session.runtime.limits.max_json_depth,
						session.runtime.limits.max_body_bytes,
					),
					session.query_scope,
				),
			);
			if (
				instance !== lifetime.current ||
				!client.isCurrentScope(session.query_scope)
			)
				return;
			setTitle(value.title);
			void created?.(value);
			setProject(value);
		} catch (error) {
			if (instance !== lifetime.current) return;
			if (
				error instanceof ApiError &&
				([401, 403].includes(error.status) || error.code === "session_changed")
			) {
				recheck();
				return;
			}
			setFailure(
				__(
					"The project could not be created. Nothing was saved; you can try again.",
					"linker-tools",
				),
			);
		} finally {
			if (instance === lifetime.current) setBusy(false);
		}
	}
	if (project)
		return (
			<QuickStartRun
				key={project.id}
				project={project}
				session={session}
				client={client}
				store={store}
				config={config}
				recheck={recheck}
				openWorkbench={openWorkbench}
				onOpenProject={onOpenProject}
			/>
		);
	const annual = quickStartAnnualOptions(choices.projectType);
	return (
		<section className="lp-quickstart" aria-labelledby="lp-quickstart-heading">
			<header className="lp-quickstart-head">
				<span className="lp-eyebrow">{__("Quick start", "linker-tools")}</span>
				<h1 id="lp-quickstart-heading">
					{existingProject
						? __("Re-plan this project in one screen", "linker-tools")
						: __("Plan a system in one screen", "linker-tools")}
				</h1>
				<p>
					{__(
						"Pick from the lists and press Generate solution. The workspace saves the project, fetches the data it can and shows the matching equipment with its bill of materials.",
						"linker-tools",
					)}
				</p>
				{close && (
					<button className="lp-text-button" type="button" onClick={close}>
						{__("Back to projects", "linker-tools")}
					</button>
				)}
			</header>
			<form
				className="lp-quickstart-form"
				onSubmit={(event) => {
					event.preventDefault();
					void start();
				}}
			>
				<label className="lp-field">
					<span>{__("Project type", "linker-tools")}</span>
					<select
						value={choices.projectType}
						onChange={(event) =>
							change(
								"projectType",
								event.currentTarget.value as QuickStartProjectType,
							)
						}
					>
						<option value="residential">
							{__("Residential", "linker-tools")}
						</option>
						<option value="commercial">
							{__("Commercial", "linker-tools")}
						</option>
					</select>
				</label>
				<label className="lp-field">
					<span>{__("PV array size", "linker-tools")}</span>
					<select
						value={String(choices.pvKwp)}
						onChange={(event) =>
							change("pvKwp", Number(event.currentTarget.value))
						}
					>
						{QUICK_START_PV_SIZES.map((size) => (
							<option key={size} value={String(size)}>
								{sprintf(__("%s kWp", "linker-tools"), String(size))}
							</option>
						))}
					</select>
				</label>
				<label className="lp-field">
					<span>{__("Roof orientation and tilt", "linker-tools")}</span>
					<select
						value={choices.orientation}
						onChange={(event) =>
							change(
								"orientation",
								event.currentTarget.value as QuickStartOrientation,
							)
						}
					>
						{QUICK_START_ORIENTATIONS.map((orientation) => (
							<option key={orientation} value={orientation}>
								{quickStartOrientationLabel(orientation)}
							</option>
						))}
					</select>
				</label>
				<label className="lp-field">
					<span>{__("Module power class", "linker-tools")}</span>
					<select
						value={choices.moduleTierId}
						onChange={(event) =>
							change("moduleTierId", event.currentTarget.value)
						}
					>
						{MODULE_TIERS.map((tier) => (
							<option key={tier.id} value={tier.id}>
								{sprintf(__("%s Wp", "linker-tools"), String(tier.stc_power_w))}
							</option>
						))}
					</select>
				</label>
				<label className="lp-field">
					<span>{__("Annual electricity use", "linker-tools")}</span>
					<select
						value={String(choices.annualKwh)}
						onChange={(event) =>
							change("annualKwh", Number(event.currentTarget.value))
						}
					>
						{annual.map((value) => (
							<option key={value} value={String(value)}>
								{sprintf(
									__("%s kWh per year", "linker-tools"),
									new Intl.NumberFormat(config.locale).format(value),
								)}
							</option>
						))}
					</select>
				</label>
				<label className="lp-field">
					<span>{__("Grid connection", "linker-tools")}</span>
					<select
						value={String(choices.phase)}
						onChange={(event) =>
							change("phase", Number(event.currentTarget.value) === 1 ? 1 : 3)
						}
					>
						<option value="3">{quickStartPhaseLabel(3)}</option>
						<option value="1">{quickStartPhaseLabel(1)}</option>
					</select>
				</label>
				<label className="lp-field">
					<span>{__("System goal", "linker-tools")}</span>
					<select
						value={choices.goal}
						onChange={(event) =>
							change("goal", event.currentTarget.value as QuickStartGoal)
						}
					>
						{QUICK_START_GOALS.map((goal) => (
							<option key={goal} value={goal}>
								{quickStartGoalLabel(goal)}
							</option>
						))}
					</select>
				</label>
				<label className="lp-field">
					<span>{__("Postcode or town", "linker-tools")}</span>
					<input
						type="text"
						required
						autoComplete="postal-code"
						value={choices.location}
						placeholder={__("e.g. 10115 Berlin", "linker-tools")}
						onChange={(event) => change("location", event.currentTarget.value)}
					/>
				</label>
				<div className="lp-quickstart-actions">
					<button className="lp-button" type="submit" disabled={!ready || busy}>
						{busy
							? __("Working…", "linker-tools")
							: __("Generate solution", "linker-tools")}
					</button>
					{/* TODO(#places): replace this free-text field with the Google
					    Places picker (another line owns that integration) and use the
					    returned coordinates for the weather request. */}
					<p className="lp-profile-help">
						{__(
							"Entering a postcode or town is enough to start. Roof drawing, interval data and the exact site coordinates stay optional and can be added later.",
							"linker-tools",
						)}
					</p>
				</div>
			</form>
			{failure && (
				<Notice error>
					<p>{failure}</p>
				</Notice>
			)}
			<details className="lp-quickstart-advanced">
				<summary>
					{__("Advanced engineering checks (optional)", "linker-tools")}
				</summary>
				<p>
					{__(
						"The full workbench adds roof geometry, imported interval data and the detailed engineering checks. Nothing on this screen is lost by opening it.",
						"linker-tools",
					)}
				</p>
			</details>
			{title && <p role="status">{title}</p>}
		</section>
	);
}

function QuickStartRun({
	project,
	session,
	client,
	store,
	config,
	recheck,
	openWorkbench,
	onOpenProject,
}: {
	project: Project;
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	config: Configuration;
	recheck: () => void;
	openWorkbench?: ((projectId: string) => void) | undefined;
	onOpenProject?: ((projectId: string) => void) | undefined;
}) {
	const {
		draft,
		update,
		save,
		busy: saving,
	} = useProjectDraft(project, session, client, store, recheck);
	const operations = usePlanningOperations({
		projectId: project.id,
		session,
		client,
		recheck,
	});
	const [states, setStates] = useState<Readonly<Record<string, StepState>>>({});
	const [searchRun, setSearchRun] = useState<PlanningRun | null>(null);
	const [qualifyRun, setQualifyRun] = useState<PlanningRun | null>(null);
	const [reportRun, setReportRun] = useState<PlanningRun | null>(null);
	const [candidate, setCandidate] = useState<EquipmentCandidate | null>(null);
	const started = useRef(false);
	const lifetime = useRef(0);
	const setStep = useCallback((id: QuickStartStepId, state: StepState) => {
		setStates((previous) => ({ ...previous, [id]: state }));
	}, []);
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
		};
	}, []);

	const readyOperations =
		!operations.checking && !operations.storageFailed && !operations.busy;

	// Only the operations this screen can supply complete inputs for. Weather and
	// PV preparation need a coordinate anchor and placed modules, so they are
	// reported as not run instead of being started with borrowed values.
	async function startRun(
		path:
			| "runs/energy"
			| "runs/equipment-search"
			| "runs/equipment"
			| "runs/report",
		fields: JsonObject = {},
	): Promise<PlanningRun | null> {
		const reply = await operations.start(path, fields);
		if (!reply || reply.path !== path) return null;
		if (!("run" in reply)) return null;
		return await poll(reply.run);
	}

	async function poll(start: PlanningRun): Promise<PlanningRun | null> {
		let current = start;
		for (let attempt = 0; attempt < POLL_LIMIT; attempt++) {
			if (!runPending(current.state)) return current;
			await wait(POLL_MS);
			if (!client.isCurrentScope(session.query_scope)) return null;
			current = readRun(
				await client.query(
					"runs/read",
					{ schema_version: 1, run_id: current.id },
					session.query_scope,
				),
				project.id,
				current.id,
			);
		}
		return current;
	}

	function runFailure(run: PlanningRun | null): string {
		const code =
			run && run.error && typeof run.error.code === "string"
				? run.error.code
				: null;
		if (run?.state === "failed" && code)
			return sprintf(
				__("The server stopped this step (%s).", "linker-tools"),
				code,
			);
		if (!run)
			return __(
				"The step could not be started. Your saved project is unchanged.",
				"linker-tools",
			);
		return __(
			"The step did not finish in time. It keeps running on the server; retrying only starts a new attempt.",
			"linker-tools",
		);
	}

	const run = useCallback(async () => {
		if (!draft || started.current) return;
		started.current = true;
		const step = (id: QuickStartStepId) => setStep(id, { kind: "running" });
		const done = (id: QuickStartStepId, detail?: string) =>
			setStep(
				id,
				detail === undefined ? { kind: "done" } : { kind: "done", detail },
			);
		const blocked = (id: QuickStartStepId, detail: string, retry = true) =>
			setStep(id, { kind: "blocked", detail, retry });
		const current = () => lifetime.current > 0;
		try {
			// 1. Save: the confirmed revision every later operation is bound to.
			step("save");
			const saved = await save();
			if (!current()) return;
			const revision = saved?.revision ?? draft.baseline.revision;
			done("save", sprintf(__("Revision %d", "linker-tools"), revision));

			// 2-5. Steps whose inputs this screen does not collect are reported as
			// not run rather than marked complete. A location typed as text is not
			// a WGS 84 coordinate, so no weather request is sent from here, and an
			// annual consumption figure is not an interval series.
			blocked(
				"weather",
				__(
					"Typical-year weather needs the site coordinates that a drawn roof supplies. Add the roof in the full workbench to run this step.",
					"linker-tools",
				),
				false,
			);
			blocked(
				"pv",
				__(
					"Roof generation needs placed modules. Draw the roof in the full workbench and this step runs with the same inputs.",
					"linker-tools",
				),
				false,
			);
			blocked(
				"scenario",
				__(
					"The storage calculation needs imported interval data for total load, available PV and auxiliary demand. Import the profile in the full workbench.",
					"linker-tools",
				),
				false,
			);
			blocked(
				"energy",
				__("Waiting for the interval data.", "linker-tools"),
				false,
			);

			// 6. Equipment search runs from the declared requirements alone.
			step("search");
			const search = await startRun("runs/equipment-search", {
				expected_revision: draft.baseline.revision,
			});
			if (!current()) return;
			if (!search || search.state !== "succeeded") {
				blocked("search", runFailure(search));
				return;
			}
			setSearchRun(search);
			const listed = search.result
				? (readObject(readObject(search.result).search).candidates as
						readonly EquipmentCandidate[] | undefined)
				: undefined;
			const first = singleSelectionCandidate(
				listed?.find((item) => !isPlantCandidate(item)) ?? null,
			);
			if (!first) {
				blocked(
					"search",
					__(
						"No single-system combination satisfies these requirements. The full workbench shows every check that refused a product.",
						"linker-tools",
					),
					false,
				);
				return;
			}
			setCandidate(first);
			done(
				"search",
				sprintf(
					__("%d matching combinations", "linker-tools"),
					listed?.length ?? 1,
				),
			);

			// 7. Apply the leading candidate, then let the engine qualify it.
			const catalog = readEquipmentProducts(
				await client.query(
					"products/current",
					{ schema_version: 1 },
					session.query_scope,
				),
			);
			if (!current()) return;
			if (!catalog.prepared) {
				blocked(
					"qualify",
					__("Current product data is still being prepared.", "linker-tools"),
				);
				return;
			}
			step("qualify");
			const patch = Object.fromEntries(
				(
					[
						"inverter_product_id",
						"battery_product_id",
						"modules_per_stack",
						"parallel_stacks",
						"accessory_product_ids",
					] as const
				).map((key) => [key, first.selection[key] as Json]),
			);
			let next = changeEquipment(draft.history.current, patch);
			const selection = compileEquipment(
				equipmentDraft(next),
				catalog.products,
			);
			next = {
				...next,
				equipment_selection: selection,
				equipment_candidate: {
					run_id: search.id,
					candidate_id: first.id,
					assessment_sha256: first.assessment_sha256,
				} as JsonObject,
			};
			update((previous) => editDraft(previous, next));
			const confirmed = await save();
			if (!current()) return;
			if (!confirmed) {
				blocked(
					"qualify",
					__(
						"The chosen combination could not be saved. Your open changes stay on this screen.",
						"linker-tools",
					),
				);
				return;
			}
			const qualified = await startRun("runs/equipment", {
				expected_revision: confirmed.revision,
			});
			if (!current()) return;
			if (!qualified || qualified.state !== "succeeded") {
				blocked("qualify", runFailure(qualified));
				return;
			}
			setQualifyRun(qualified);
			done("qualify", __("Requirements checked", "linker-tools"));

			// 8. Report: the PDF and the solution draft both come from here.
			// The adopted candidate is this project's equipment source, exactly
			// as the workbench's report form treats it: naming a separate run
			// there contradicts the saved choice and the engine refuses it.
			step("report");
			const report = await startRun("runs/report", {
				expected_revision: confirmed.revision,
				options: {
					locale: config.locale.toLowerCase().startsWith("de") ? "de" : "en",
					energy_run_id: null,
					pv_run_id: null,
					equipment_run_id: null,
					logo: null,
				},
			});
			if (!current()) return;
			// The PDF no longer depends on an energy result, so a failure here is
			// the step's own failure and must name it instead of blaming a
			// calculation this screen never promised to run.
			if (!report || report.state !== "succeeded") {
				blocked("report", runFailure(report));
				return;
			}
			setReportRun(report);
			done("report");
		} catch (error) {
			if (!current()) return;
			if (
				error instanceof ApiError &&
				([401, 403].includes(error.status) || error.code === "session_changed")
			) {
				recheck();
				return;
			}
			const message =
				error instanceof ApiError
					? sprintf(__("The step stopped with %s.", "linker-tools"), error.code)
					: __(
							"The step stopped unexpectedly. Every confirmed result stays saved.",
							"linker-tools",
						);
			setStates((previous) => {
				const running = Object.entries(previous).find(
					([, value]) => value.kind === "running",
				);
				return running
					? {
							...previous,
							[running[0]]: { kind: "blocked", detail: message, retry: true },
						}
					: previous;
			});
		}
	}, [
		client,
		config.locale,
		draft,
		recheck,
		save,
		session.query_scope,
		setStep,
		update,
	]);

	useEffect(() => {
		if (!draft || operations.checking) return;
		void run();
		// One automatic pass per opened project; the retry buttons start a new
		// attempt explicitly.
	}, [draft !== null, operations.checking, run]);

	const steps = quickStartSteps();
	const running = saving || operations.busy;
	const blockedStep = steps.find((item) => states[item.id]?.kind === "blocked");
	return (
		<section className="lp-quickstart" aria-labelledby="lp-quickstart-run">
			<header className="lp-quickstart-head">
				<span className="lp-eyebrow">{__("Quick start", "linker-tools")}</span>
				<h1 id="lp-quickstart-run">{project.title}</h1>
				<p role="status">
					{running
						? __("Working through the steps…", "linker-tools")
						: __(
								"Steps run one after another; each result stays saved.",
								"linker-tools",
							)}
				</p>
			</header>
			<ol className="lp-quickstart-steps">
				{steps.map((item) => {
					const state = states[item.id] ?? { kind: "pending" };
					return (
						<li key={item.id} data-step={item.id} data-state={state.kind}>
							<strong>{item.label}</strong>
							{state.kind === "done" && (
								<span>
									{" "}
									<Icon name="check" width="16" height="16" />{" "}
									{state.detail ?? __("Done", "linker-tools")}
								</span>
							)}
							{state.kind === "running" && (
								<span> {__("Running…", "linker-tools")}</span>
							)}
							{state.kind === "blocked" && (
								<Notice error>
									<p>{state.detail}</p>
									{state.retry && (
										<button
											className="lp-button lp-button-secondary"
											type="button"
											disabled={running || !readyOperations}
											onClick={() => {
												started.current = false;
												void run();
											}}
										>
											{sprintf(
												__("Retry this step: %s", "linker-tools"),
												item.label,
											)}
										</button>
									)}
								</Notice>
							)}
						</li>
					);
				})}
			</ol>
			{searchRun && (
				<section
					className="lp-quickstart-result"
					aria-label={__("Matching equipment", "linker-tools")}
				>
					<h2>{__("Recommended equipment", "linker-tools")}</h2>
					<EquipmentSearchResult
						run={searchRun}
						locale={config.locale}
						dirty={false}
						confirmedRevision={searchRun.revision}
						client={client}
						scope={session.query_scope}
						disabled={running}
						apply={async (chosen) => {
							setCandidate(chosen);
						}}
						onError={() => undefined}
						{...(draft?.history.current.equipment_candidate === undefined
							? {}
							: {
									projectCandidate: readObject(
										draft.history.current.equipment_candidate,
									),
								})}
					/>
					{candidate && (
						<p className="lp-profile-help">
							{sprintf(
								__(
									"This combination fills the %s kWh storage window this screen asked for.",
									"linker-tools",
								),
								String(
									draft?.history.current.equipment_setup
										? (readObject(draft.history.current.equipment_setup)
												.required_usable_kwh ?? "—")
										: "—",
								),
							)}{" "}
							{QUICK_START_SIZING_NOTE}
						</p>
					)}
				</section>
			)}
			{qualifyRun && (
				<section
					className="lp-quickstart-result"
					aria-label={__("Engineering result", "linker-tools")}
				>
					<h2>{__("Checks and bill of materials", "linker-tools")}</h2>
					<EquipmentResult
						run={qualifyRun}
						locale={config.locale}
						dirty={Boolean(
							draft && draft.history.current !== draft.baseline.inputs,
						)}
						confirmedRevision={qualifyRun.revision}
					/>
				</section>
			)}
			{reportRun && (
				<section
					className="lp-quickstart-result"
					aria-label={__("Report", "linker-tools")}
				>
					<h2>{__("Report and solution draft", "linker-tools")}</h2>
					<PlanningReportResult
						run={reportRun}
						client={client}
						scope={session.query_scope}
						recheck={recheck}
						operations={operations}
						current={client.isCurrentScope(session.query_scope)}
						blocked={false}
						locale={config.locale}
					/>
					<DraftTransferButton
						run={reportRun}
						client={client}
						scope={session.query_scope}
						operations={operations}
						current={client.isCurrentScope(session.query_scope)}
						blocked={operations.busy}
						locale={config.locale}
						recheck={recheck}
					/>
				</section>
			)}
			<details className="lp-quickstart-advanced">
				<summary>
					{__("Advanced engineering checks (optional)", "linker-tools")}
				</summary>
				<p>
					{__(
						"Roof geometry, imported interval data and every detailed check live in the full workbench. This project opens there with everything already saved.",
						"linker-tools",
					)}
				</p>
				<button
					className="lp-button lp-button-secondary"
					type="button"
					onClick={() =>
						openWorkbench
							? openWorkbench(project.id)
							: onOpenProject?.(project.id)
					}
				>
					{__("Open the full workbench", "linker-tools")}
				</button>
			</details>
			{blockedStep && (
				<p className="lp-profile-help">
					{__(
						"A later step needs inputs this screen does not collect. Everything already calculated stays saved.",
						"linker-tools",
					)}
				</p>
			)}
		</section>
	);
}
