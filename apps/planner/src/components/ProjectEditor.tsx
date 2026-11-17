import { GridConnectionForm } from "./GridConnectionForm.tsx";
import { CountryRuleForm } from "./CountryRuleForm.tsx";
import {
	readCountryRuleInputs,
	replaceCountryRuleInputs,
} from "../domain/countryRules.ts";
import {
	readGridConnection,
	replaceGridConnection,
} from "../domain/gridConnection.ts";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Configuration } from "../data/config.ts";
import { readPlaceImagery } from "../domain/place.ts";
import type { PlaceImagery } from "../domain/place.ts";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { DraftStore } from "../data/DraftStore.ts";
import type { JsonObject, Project, Session } from "../data/protocol.ts";
import { useProjectDraft } from "../data/useProjectDraft.ts";
import { useProjectBar } from "../data/useProjectBar.ts";
import { editDraft, isDirty, redoDraft, undoDraft } from "../domain/draft.ts";
import { emptyBrief, readBrief } from "../domain/brief.ts";
import { readSelections } from "../domain/profiles.ts";
import { __, sprintf } from "../i18n.ts";
import { BriefForm } from "./BriefForm.tsx";
import { Icon } from "./Icon.tsx";
import { Notice } from "./Notice.tsx";
import { RevisionComparison } from "./RevisionComparison.tsx";
import { ProfileIntake } from "./ProfileIntake.tsx";
import { OwnedProfile } from "./OwnedProfile.tsx";
import { measurementLabel } from "./ProfileLabels.ts";
import { DesignEditor } from "./design/DesignEditor.tsx";
import {
	applyGeometryCommand,
	emptyGeometry,
} from "../domain/geometryCommands.ts";
import type { GeometryCommand } from "../domain/geometryCommands.ts";
import { readGeometry } from "../domain/validateGeometry.ts";
import geometryPolicy from "../contracts/geometry-policy.json" with { type: "json" };
import { readObject } from "../data/readProtocol.ts";
import {
	attachGeometryImport,
	readGeometryImports,
} from "../domain/geometryImports.ts";
import type { PreparedGeometryImport } from "../domain/geometryImports.ts";
import type { GeometryDocument } from "../domain/geometry.ts";
import { ProjectOverview } from "./ProjectOverview.tsx";
import { SavedSolutionReference } from "./SavedSolutionReference.tsx";
import { revealActionResult } from "./revealActionResult.ts";
import { EnergyWorkspace } from "./energy/EnergyWorkspace.tsx";
import { invalidateEnergyReplay } from "../domain/energyScenario.ts";
import { replacePlannerLocation } from "../data/plannerLocation.ts";
import { useGenieContext } from "../data/useGenieContext.ts";
import { InstallationEditor } from "./installation/InstallationEditor.tsx";
import { readInstallation } from "../domain/installation.ts";

type ProjectWorkspace =
	| "overview"
	| "site"
	| "energy"
	| "design"
	| "calculations"
	| "equipment"
	| "installation";
const workspaceHash = {
	overview: "lp-overview",
	site: "lp-site",
	energy: "lp-load",
	design: "lp-design",
	calculations: "lp-calculations",
	equipment: "lp-equipment",
	installation: "lp-installation",
} as const;
const workspaceTarget = { ...workspaceHash, site: "lp-brief-use" } as const;
const mapPropertyHashes: readonly string[] = [
	"#lp-map-roof-properties",
	"#lp-map-ring-properties",
	"#lp-map-feature-properties",
];
export function workspaceFromHash(inputs: JsonObject): ProjectWorkspace {
	if (window.location.hash === "#lp-installation") return "installation";
	if (window.location.hash === "#lp-equipment") return "equipment";
	if (
		window.location.hash === "#lp-calculations" ||
		(!window.location.hash &&
			/^[a-f0-9]{32}$/.test(
				new URL(window.location.href).searchParams.get("run") ?? "",
			))
	)
		return "calculations";
	if (["#lp-site", "#lp-brief-use", "#lp-notes"].includes(window.location.hash))
		return "site";
	if (["#lp-load", "#lp-profiles"].includes(window.location.hash))
		return "energy";
	if (
		window.location.hash === "#lp-design" ||
		(!window.location.hash &&
			new URL(window.location.href).searchParams.getAll("step").length === 1 &&
			new URL(window.location.href).searchParams.get("step") === "roof") ||
		mapPropertyHashes.includes(window.location.hash)
	)
		return "design";
	// Site-only roof starts and their saved geometry reopen at the drawing.
	// Established energy/equipment projects keep their existing overview entry.
	if (
		!window.location.hash &&
		Object.keys(inputs).every((key) =>
			["brief", "geometry", "geometry_imports"].includes(key),
		) &&
		inputs.brief !== undefined
	) {
		try {
			const brief = readBrief(inputs.brief);
			if (
				brief.site.country_code &&
				brief.site.latitude !== null &&
				brief.site.longitude !== null &&
				brief.project_use === null &&
				brief.system_scope !== "storage_only" &&
				brief.annual_load.kwh === null
			)
				return "design";
		} catch {
			// The editor reports unsupported input formats in its existing notice.
		}
	}
	return "site";
}

export function ProjectEditor({
	project,
	session,
	client,
	store,
	config,
	recheck,
	close,
	recoveryScopes,
	recoveryChecking = false,
	recoveryFailed: discoveryFailed = false,
}: {
	project: Project;
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	config: Configuration;
	recheck: () => void;
	close: () => boolean;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	recoveryFailed?: boolean;
}) {
	const {
		draft,
		update,
		save,
		flush,
		acknowledgeProject,
		busy,
		failed,
		sourceChanged,
		inputContractRequired,
		recoveryFailed,
		recovered,
		recoveries,
		restore,
		resolveConflict,
	} = useProjectDraft(project, session, client, store, recheck);
	// Map imagery is independent of postcode geocoding. A selected full address
	// already has its exact centre stored in the brief.
	const [siteImagery, setSiteImagery] = useState<PlaceImagery | null>(null);
	const [siteImageryFailed, setSiteImageryFailed] = useState(false);
	const [siteImageryAttempt, setSiteImageryAttempt] = useState(0);
	// The mapped building at the declared site, with official 3D roof planes
	// where published (DE/NL/CH/LI) or 2D outline elsewhere.
	const [siteOutline, setSiteOutline] = useState<{
		ring: [number, number][];
		source: string;
		licence: string;
		planes?: {
			id: number;
			polygon: [number, number][];
			tilt_deg: number;
			azimuth_deg: number;
			area_m2: number;
		}[];
	} | null>(null);
	const mapSite = useMemo(() => {
		try {
			const stored = draft?.history.current.brief;
			const value = stored === undefined ? emptyBrief() : readBrief(stored);
			return {
				label: value.site.location_label.trim(),
				postcode: value.site.postal_code,
				country: value.site.country_code,
				latitude: value.site.latitude,
				longitude: value.site.longitude,
			};
		} catch {
			return null;
		}
	}, [draft?.history.current.brief]);
	useEffect(() => {
		const label = mapSite?.label;
		const country = mapSite?.country;
		setSiteImagery(null);
		setSiteImageryFailed(false);
		setSiteOutline(null);
		if (!label || !client.isCurrentScope(session.query_scope)) {
			return;
		}
		let live = true;
		void (async () => {
			try {
				const answer = await client.query(
					"places/lookup",
					{
						schema_version: 1,
						query: mapSite?.postcode || label,
						...(country ? { country } : {}),
					},
					session.query_scope,
				);
				if (!live) return;
				const reply = readObject(answer);
				setSiteImagery(readPlaceImagery(reply.imagery));
				const latitude = mapSite?.latitude ?? reply.latitude;
				const longitude = mapSite?.longitude ?? reply.longitude;
				const replyCountry = country ?? reply.country_code;
				if (
					typeof latitude !== "number" ||
					typeof longitude !== "number" ||
					typeof replyCountry !== "string"
				) {
					setSiteOutline(null);
					return;
				}
				try {
					const found = readObject(
						await client.query(
							"places/outline",
							{
								schema_version: 1,
								query: label,
								country: replyCountry,
								latitude,
								longitude,
							},
							session.query_scope,
						),
					);
					if (!live) return;
					const ring = Array.isArray(found.outline)
						? (found.outline as [number, number][])
						: [];
					const planes = Array.isArray(found.planes)
						? found.planes.filter(
								(
									plane,
								): plane is {
									id: number;
									polygon: [number, number][];
									tilt_deg: number;
									azimuth_deg: number;
									area_m2: number;
								} =>
									typeof plane === "object" &&
									plane !== null &&
									typeof plane.id === "number" &&
									Array.isArray(plane.polygon) &&
									plane.polygon.length >= 3 &&
									typeof plane.tilt_deg === "number" &&
									typeof plane.azimuth_deg === "number" &&
									typeof plane.area_m2 === "number",
							)
						: [];
					setSiteOutline(
						found.found === true &&
							ring.length >= 3 &&
							typeof found.source === "string" &&
							typeof found.licence === "string"
							? {
									ring,
									source: found.source,
									licence: found.licence,
									...(planes.length > 0 ? { planes } : {}),
								}
							: null,
					);
				} catch {
					if (live) setSiteOutline(null);
				}
			} catch {
				// A missing mosaic never blocks the design step.
				if (live) {
					setSiteImagery(null);
					setSiteImageryFailed(true);
				}
			}
		})();
		return () => {
			live = false;
		};
	}, [
		mapSite?.label,
		mapSite?.postcode,
		mapSite?.country,
		mapSite?.latitude,
		mapSite?.longitude,
		siteImageryAttempt,
		client,
		session.query_scope,
	]);

	const [gridValid, setGridValid] = useState(true);
	const [ruleValid, setRuleValid] = useState(true);
	const [briefValid, setBriefValid] = useState(true);
	const [designValid, setDesignValid] = useState(true);
	const [energyValid, setEnergyValid] = useState(true);
	const [installationValid, setInstallationValid] = useState(true);
	const valid =
		gridValid &&
		ruleValid &&
		briefValid &&
		designValid &&
		energyValid &&
		installationValid;
	const [workspace, setWorkspace] = useState<ProjectWorkspace>(() =>
		workspaceFromHash(project.inputs),
	);
	const [calculationsOpened, setCalculationsOpened] = useState(() =>
		["energy", "calculations", "equipment"].includes(workspace),
	);
	const workspaceFocus = useRef(false);
	useEffect(() => {
		if (!workspaceFocus.current) return;
		if (
			revealActionResult(
				document.querySelector<HTMLElement>(
					"[data-linker-planner] #" + workspaceTarget[workspace],
				),
				() => client.isCurrentScope(session.query_scope),
			)
		)
			workspaceFocus.current = false;
	}, [workspace, client, session.query_scope]);
	function chooseWorkspace(next: ProjectWorkspace, report = false) {
		if (!client.isCurrentScope(session.query_scope)) return;
		if (!valid) {
			setCloseBlocked("invalid");
			return;
		}
		if (report || next === "energy") {
			const url = new URL(window.location.href);
			url.searchParams.delete("run");
			url.searchParams.delete("compare");
			url.searchParams.set("energy_view", report ? "reports" : "scenario");
			replacePlannerLocation(url);
		}
		if (next === workspace) {
			revealActionResult(
				document.querySelector<HTMLElement>(
					"[data-linker-planner] #" + workspaceTarget[next],
				),
				() => client.isCurrentScope(session.query_scope),
			);
			return;
		}
		workspaceFocus.current = true;
		if (["energy", "calculations", "equipment"].includes(next))
			setCalculationsOpened(true);
		setWorkspace(next);
		const url = new URL(window.location.href);
		url.hash = workspaceHash[next];
		replacePlannerLocation(url);
	}
	const editGeometry = useCallback(
		(command: GeometryCommand): boolean => {
			if (!client.isCurrentScope(session.query_scope)) return false;
			try {
				update((previous) => {
					const current = previous.history.current;
					const geometry =
						current.geometry === undefined
							? emptyGeometry()
							: readGeometry(current.geometry, geometryPolicy);
					return editDraft(previous, {
						...current,
						geometry: readObject(applyGeometryCommand(geometry, command)),
					});
				});
				return true;
			} catch {
				return false;
			}
		},
		[client, session.query_scope, update],
	);
	const editEnergy = useCallback(
		(operation: (inputs: JsonObject) => JsonObject): boolean => {
			if (!client.isCurrentScope(session.query_scope)) return false;
			try {
				update((previous) =>
					editDraft(previous, operation(previous.history.current)),
				);
				return true;
			} catch {
				return false;
			}
		},
		[client, session.query_scope, update],
	);
	const importGeometry = useCallback(
		(before: GeometryDocument, asset: PreparedGeometryImport): boolean => {
			if (!client.isCurrentScope(session.query_scope)) return false;
			try {
				update((previous) =>
					editDraft(
						previous,
						attachGeometryImport(previous.history.current, before, asset),
					),
				);
				return true;
			} catch {
				return false;
			}
		},
		[client, session.query_scope, update],
	);
	const profileGuard = useRef<() => boolean>(() => true);
	const registerProfileGuard = useCallback((guard: () => boolean) => {
		profileGuard.current = guard;
	}, []);
	const bar = useProjectBar();
	const [closing, setClosing] = useState(false);
	const [closeBlocked, setCloseBlocked] = useState<
		"invalid" | "recovery" | null
	>(null);
	useEffect(() => {
		if (valid) setCloseBlocked(null);
	}, [valid]);
	useEffect(() => {
		if (valid) return;
		const preventLoss = (event: BeforeUnloadEvent) => {
			event.preventDefault();
			event.returnValue = "";
		};
		window.addEventListener("beforeunload", preventLoss);
		return () => window.removeEventListener("beforeunload", preventLoss);
	}, [valid]);
	async function leave() {
		if (closing) return;
		if (!profileGuard.current()) return;
		if (!valid) {
			setCloseBlocked("invalid");
			document
				.querySelector<HTMLElement>(
					'[data-linker-planner] [aria-invalid="true"]',
				)
				?.focus();
			return;
		}
		setClosing(true);
		if (!draft || (!isDirty(draft) && !draft.pending) || (await flush())) {
			if (!close()) setClosing(false);
		} else {
			setCloseBlocked("recovery");
			setClosing(false);
		}
	}
	const dirty = draft ? isDirty(draft) : false;
	useGenieContext(
		draft?.baseline ?? project,
		session,
		!draft || !valid || dirty || Boolean(draft?.pending),
	);
	if (!draft)
		return <p role="status">{__("Opening project…", "linker-tools")}</p>;
	let gridConnection;
	let countryRuleInputs;
	let brief;
	let selections;
	let geometry;
	let geometryImports;
	try {
		gridConnection = readGridConnection(draft.history.current.grid_connection);
		countryRuleInputs = readCountryRuleInputs(
			draft.history.current.country_rule_inputs,
		);
		if (countryRuleInputs && !gridConnection)
			throw new Error("country_rules_without_grid");
		brief =
			draft.history.current.brief === undefined
				? emptyBrief()
				: readBrief(draft.history.current.brief);
		selections = readSelections(draft.history.current.profile_selections);
		geometry =
			draft.history.current.geometry === undefined
				? emptyGeometry()
				: readGeometry(draft.history.current.geometry, geometryPolicy);
		geometryImports = readGeometryImports(
			draft.history.current.geometry_imports,
		);
		readInstallation(draft.history.current.installation);
	} catch {
		return (
			<Notice error>
				{__(
					"This project contains an input format that this workspace cannot edit.",
					"linker-tools",
				)}
			</Notice>
		);
	}
	return (
		<div className="lp-project" data-workspace={workspace}>
			<header className="lp-project-bar lp-project-masthead" ref={bar}>
				<div className="lp-project-masthead-inner">
					<div className="lp-project-topline">
						<div className="lp-breadcrumb">
							<button
								className="lp-text-button lp-back-projects"
								disabled={closing}
								onClick={() => {
									void leave();
								}}
							>
								<Icon name="back" />
								{__("Projects", "linker-tools")}
							</button>
						</div>
						<div className="lp-project-nav-title">
							<span className="lp-nav-mark" aria-hidden="true">
								L
							</span>
							<span>{__("Solution Configurator", "linker-tools")}</span>
						</div>
					</div>
					<div className="lp-project-heading">
						<div className="lp-project-identity">
							<h1>{project.title}</h1>
							{brief.site.location_label &&
								brief.site.location_label !== project.title && (
									<p>
										<Icon name="location" />
										{brief.site.location_label}
									</p>
								)}
						</div>
						<div className="lp-edit-actions">
							<button
								className="lp-text-button"
								type="button"
								data-linker-genie-open
							>
								<Icon name="sparkle" />
								{__("Ask Genie", "linker-tools")}
							</button>
							<span className="lp-save-state" role="status">
								{busy
									? __("Saving…", "linker-tools")
									: draft.pending
										? __("Save not confirmed", "linker-tools")
										: !gridValid ||
											  !ruleValid ||
											  !briefValid ||
											  !energyValid ||
											  !installationValid
											? __("Input needs attention", "linker-tools")
											: !designValid
												? __("Roof editing in progress", "linker-tools")
												: dirty
													? __("Unsaved changes", "linker-tools")
													: sprintf(
															__("Saved · revision %d", "linker-tools"),
															draft.baseline.revision,
														)}
							</span>
							<button
								className="lp-icon-button"
								title={__("Undo", "linker-tools")}
								aria-label={__("Undo", "linker-tools")}
								disabled={!valid || !draft.history.past.length}
								onClick={() => update(undoDraft)}
							>
								<Icon name="undo" />
							</button>
							<button
								className="lp-icon-button"
								title={__("Redo", "linker-tools")}
								aria-label={__("Redo", "linker-tools")}
								disabled={!valid || !draft.history.future.length}
								onClick={() => update(redoDraft)}
							>
								<Icon name="redo" />
							</button>
							<button
								className="lp-button"
								disabled={
									busy ||
									!valid ||
									Boolean(draft.conflict) ||
									Boolean(recoveries.length) ||
									(!dirty && !draft.pending)
								}
								onClick={() => {
									void save();
								}}
							>
								{draft.pending && !busy
									? __("Retry save", "linker-tools")
									: __("Save project", "linker-tools")}
							</button>
						</div>
					</div>
					{((closeBlocked === "invalid" && !valid) ||
						(closeBlocked === "recovery" &&
							recoveryFailed &&
							(dirty || draft.pending))) && (
						<div className="lp-navigation-refusal">
							<Notice error>
								{!gridValid ||
								!ruleValid ||
								!briefValid ||
								!energyValid ||
								!installationValid
									? __(
											"Correct the highlighted input before leaving this project.",
											"linker-tools",
										)
									: !designValid
										? __(
												"Finish or cancel roof editing before leaving this workspace.",
												"linker-tools",
											)
										: __(
												"Save the project before leaving. Browser recovery could not be stored.",
												"linker-tools",
											)}
							</Notice>
						</div>
					)}
					<div className="lp-project-chapters">
						<nav
							className="lp-project-chapter-links"
							aria-label={__("Project sections", "linker-tools")}
						>
							<a
								href="#lp-site"
								aria-current={workspace === "site" ? "page" : undefined}
								onClick={(event) => {
									event.preventDefault();
									chooseWorkspace("site");
								}}
							>
								<Icon name="location" />
								{__("Project", "linker-tools")}
							</a>
							<a
								hidden={brief.system_scope === "storage_only"}
								href="#lp-design"
								aria-current={workspace === "design" ? "page" : undefined}
								onClick={(event) => {
									event.preventDefault();
									chooseWorkspace("design");
								}}
							>
								<Icon name="solar" />
								{__("Solar", "linker-tools")}
							</a>
							<a
								href="#lp-load"
								aria-current={workspace === "energy" ? "page" : undefined}
								onClick={(event) => {
									event.preventDefault();
									chooseWorkspace("energy");
								}}
							>
								<Icon name="energy" />
								{__("Energy use", "linker-tools")}
							</a>
							<a
								href="#lp-equipment"
								aria-current={workspace === "equipment" ? "page" : undefined}
								onClick={(event) => {
									event.preventDefault();
									chooseWorkspace("equipment");
								}}
							>
								<Icon name="system" />
								{__("System", "linker-tools")}
							</a>
							<a
								href="#lp-calculations"
								aria-current={workspace === "calculations" ? "page" : undefined}
								onClick={(event) => {
									event.preventDefault();
									chooseWorkspace("calculations", true);
								}}
							>
								<Icon name="report" />
								{__("Review & share", "linker-tools")}
							</a>
						</nav>
						<label className="lp-mobile-chapters">
							<span>{__("Project sections", "linker-tools")}</span>
							<select
								className="lp-mobile-workspace"
								aria-label={__("Project sections", "linker-tools")}
								value={workspace}
								onChange={(event) =>
									chooseWorkspace(
										event.currentTarget.value as ProjectWorkspace,
										event.currentTarget.value === "calculations",
									)
								}
							>
								<option value="site">{__("Project", "linker-tools")}</option>
								{brief.system_scope !== "storage_only" && (
									<option value="design">{__("Solar", "linker-tools")}</option>
								)}
								<option value="energy">
									{__("Energy use", "linker-tools")}
								</option>
								<option value="equipment">
									{__("System", "linker-tools")}
								</option>
								<option value="calculations">
									{__("Review & share", "linker-tools")}
								</option>
							</select>
						</label>
					</div>
				</div>
			</header>
			<div className="lp-project-layout">
				<div className="lp-editor-main lp-editor-with-design">
					{discoveryFailed && (
						<Notice error>
							<p>
								{__(
									"Unconfirmed project creations and CSV imports from earlier sessions could not be checked. Any recovery data already stored in this browser remains unchanged.",
									"linker-tools",
								)}
							</p>
							<button className="lp-text-button" onClick={recheck}>
								{__("Check session", "linker-tools")}
							</button>
						</Notice>
					)}
					{recoveries.length > 0 && (
						<Notice>
							<p>
								{__(
									"Several local drafts are available for this project. Select one to compare with the saved revision.",
									"linker-tools",
								)}
							</p>
							<div className="lp-inline-actions">
								{recoveries.map((candidate) => (
									<button
										key={candidate.scope}
										className="lp-button lp-button-secondary"
										onClick={() => restore(candidate)}
									>
										{sprintf(
											__("Local draft · revision %d", "linker-tools"),
											candidate.draft.baseline.revision,
										)}
										{candidate.updatedAt > 0 &&
											` · ${new Intl.DateTimeFormat(config.locale, { dateStyle: "short", timeStyle: "short" }).format(candidate.updatedAt)}`}
									</button>
								))}
							</div>
						</Notice>
					)}
					{recovered && (
						<Notice>
							{__(
								"Unsaved work from this browser has been restored.",
								"linker-tools",
							)}
						</Notice>
					)}
					{recoveryFailed && (
						<Notice error>
							{__(
								"Browser recovery is unavailable. Changes remain open here until the server confirms a save.",
								"linker-tools",
							)}
						</Notice>
					)}
					{failed && !draft.conflict && (
						<Notice error>
							{inputContractRequired
								? __(
										"This workspace version cannot safely save all data in this project. Keep your local draft and reload the workspace before saving again.",
										"linker-tools",
									)
								: __(
										"The save could not be confirmed. Your input is still here.",
										"linker-tools",
									)}
							{sourceChanged && (
								<p>
									{__(
										"A new calculation requires an updated module selection.",
										"linker-tools",
									)}{" "}
									<button
										type="button"
										className="lp-text-button"
										onClick={() => chooseWorkspace("design")}
									>
										{__("Review roof design", "linker-tools")}
									</button>
								</p>
							)}
						</Notice>
					)}
					{draft.conflict && (
						<Notice error>
							<p>
								{__(
									"Open changes have been kept alongside the saved revision.",
									"linker-tools",
								)}
							</p>
							<RevisionComparison draft={draft} config={config} />
							<div className="lp-inline-actions">
								<button
									className="lp-button"
									disabled={busy}
									onClick={() => void resolveConflict("local")}
								>
									{__("Keep open changes", "linker-tools")}
								</button>
								<button
									className="lp-button lp-button-secondary"
									disabled={busy}
									onClick={() => void resolveConflict("saved")}
								>
									{__("Use saved revision", "linker-tools")}
								</button>
							</div>
						</Notice>
					)}
					<fieldset
						disabled={recoveries.length > 0}
						className="lp-brief-fields"
					>
						<div hidden={workspace !== "overview"}>
							<SavedSolutionReference
								value={draft.history.current.saved_solution_reference}
							/>
							<ProjectOverview
								brief={brief}
								geometry={geometry}
								config={config}
								installation={readInstallation(
									draft.history.current.installation,
								)}
								choose={chooseWorkspace}
							/>
						</div>
						<BriefForm
							brief={brief}
							workspace={workspace}
							config={config}
							onValidity={setBriefValid}
							onChange={(next) =>
								update((previous) => {
									const { equipment_demand, ...rest } =
										previous.history.current;
									return editDraft(previous, {
										...(next.system_scope === "pv_only"
											? rest
											: previous.history.current),
										brief: readBrief(next),
									});
								})
							}
						/>
						<details
							className="lp-site-technical"
							hidden={workspace !== "site"}
							open={Boolean(gridConnection)}
						>
							<summary>
								{__("Grid connection information", "linker-tools")}
							</summary>
							<GridConnectionForm
								value={gridConnection}
								hasRules={Boolean(countryRuleInputs)}
								onValidity={setGridValid}
								onChange={(next) =>
									update((previous) =>
										editDraft(
											previous,
											replaceGridConnection(previous.history.current, next),
										),
									)
								}
							/>
							{gridConnection && (
								<CountryRuleForm
									value={countryRuleInputs}
									country={brief.site.country_code}
									locale={config.locale}
									onValidity={setRuleValid}
									onChange={(next) =>
										update((previous) =>
											editDraft(
												previous,
												replaceCountryRuleInputs(
													previous.history.current,
													next,
												),
											),
										)
									}
								/>
							)}
						</details>
						<section
							className="lp-section"
							id="lp-profiles"
							hidden={workspace !== "energy"}
							tabIndex={-1}
							aria-labelledby="lp-profiles-heading"
						>
							<div className="lp-section-heading">
								<span className="lp-index">05</span>
								<div>
									<h2 id="lp-profiles-heading">
										{__("Interval data", "linker-tools")}
									</h2>
									<p>
										{__(
											"After import, the data's meaning and coverage are shown for review. A profile selection applies to the open draft and is saved with Save project. The annual consumption entry remains separate.",
											"linker-tools",
										)}
									</p>
								</div>
							</div>
							{Object.entries(selections.selected).map(([role, assetId]) => (
								<details
									className="lp-selected-profile lp-comparison"
									key={role + assetId}
								>
									<summary>
										{measurementLabel(
											role as import("../domain/profiles.ts").ProfileRole,
										)}
									</summary>
									<OwnedProfile
										projectId={project.id}
										assetId={assetId}
										session={session}
										client={client}
										locale={config.locale}
										expectedRole={
											role as import("../domain/profiles.ts").ProfileRole
										}
										recheck={recheck}
									/>
									<button
										type="button"
										className="lp-text-button"
										onClick={() => {
											if (!client.isCurrentScope(session.query_scope)) return;
											update((previous) => {
												const chosen = {
													...readSelections(
														previous.history.current.profile_selections,
													).selected,
												};
												delete chosen[
													role as import("../domain/profiles.ts").ProfileRole
												];
												return editDraft(previous, {
													...invalidateEnergyReplay(previous.history.current),
													profile_selections: {
														schema_version: 1,
														selected: chosen,
													},
												});
											});
										}}
									>
										{__("Remove draft selection", "linker-tools")}
									</button>
									<p className="lp-profile-help">
										{__(
											"Removing a selection leaves the stored source unchanged. Save the project to record the change.",
											"linker-tools",
										)}
									</p>
								</details>
							))}
							<ProfileIntake
								projectId={project.id}
								session={session}
								client={client}
								store={store}
								locale={config.locale}
								timezone={brief.site.timezone}
								annualKwh={brief.annual_load.kwh}
								recheck={recheck}
								recoveryScopes={recoveryScopes}
								recoveryChecking={recoveryChecking}
								registerGuard={registerProfileGuard}
								currentAssetIds={Object.values(selections.selected)}
								confirmedAssetIds={Object.values(
									readSelections(draft.baseline.inputs.profile_selections)
										.selected,
								)}
								attach={async (assetId, role) => {
									if (
										!client.isCurrentScope(session.query_scope) ||
										recoveries.length ||
										draft.conflict
									)
										return false;
									update((previous) =>
										editDraft(previous, {
											...invalidateEnergyReplay(previous.history.current),
											profile_selections: {
												schema_version: 1,
												selected: {
													...readSelections(
														previous.history.current.profile_selections,
													).selected,
													[role]: assetId,
												},
											},
										}),
									);
									return (
										(await flush()) &&
										client.isCurrentScope(session.query_scope)
									);
								}}
							/>
						</section>
						<div className="lp-design-panel" hidden={workspace !== "design"}>
							{siteImageryFailed && (
								<Notice error>
									<p>
										{__(
											"Aerial imagery is not available. You can upload a roof plan or retry loading the map.",
											"linker-tools",
										)}
									</p>
									<button
										type="button"
										className="lp-button lp-button-secondary"
										onClick={() => setSiteImageryAttempt((value) => value + 1)}
									>
										{__("Try again", "linker-tools")}
									</button>
								</Notice>
							)}
							<DesignEditor
								initialMapView={mapPropertyHashes.includes(
									window.location.hash,
								)}
								imagery={siteImagery}
								siteOutline={siteOutline}
								siteCentre={
									brief.site.latitude !== null && brief.site.longitude !== null
										? [brief.site.longitude, brief.site.latitude]
										: null
								}
								geometry={geometry}
								confirmedGeometry={
									draft.baseline.inputs.geometry === undefined
										? null
										: readGeometry(
												draft.baseline.inputs.geometry,
												geometryPolicy,
											)
								}
								geometryImports={geometryImports}
								attachImport={importGeometry}
								confirmedAssetIds={Object.values(
									readGeometryImports(draft.baseline.inputs.geometry_imports)
										.selected,
								)}
								recoveryScopes={recoveryScopes}
								recoveryChecking={recoveryChecking}
								sceneModuleUrl={config.sceneModuleUrl ?? null}
								mapModuleUrl={config.mapModuleUrl ?? null}
								googleMapsApiKey={config.googleMapsApiKey ?? null}
								commit={editGeometry}
								locale={config.locale}
								projectId={project.id}
								session={session}
								client={client}
								recheck={recheck}
								onValidity={setDesignValid}
							/>
						</div>
					</fieldset>
					{workspace === "equipment" && (
						<div className="lp-inline-actions">
							<a
								href="#lp-installation"
								className="lp-text-button"
								onClick={(event) => {
									event.preventDefault();
									chooseWorkspace("installation");
								}}
							>
								{__("Installation routing", "linker-tools")}
							</a>
						</div>
					)}
					{workspace === "installation" && (
						<fieldset
							disabled={
								busy ||
								Boolean(draft.pending) ||
								Boolean(draft.conflict) ||
								recoveries.length > 0
							}
						>
							<InstallationEditor
								inputs={draft.history.current}
								savedInputs={draft.baseline.inputs}
								savedRevision={draft.baseline.revision}
								geometry={geometry}
								client={client}
								session={session}
								projectId={project.id}
								locale={config.locale}
								sceneModuleUrl={config.sceneModuleUrl ?? null}
								editGeometry={editGeometry}
								onValidity={setInstallationValid}
								change={(plan) =>
									editEnergy((inputs) => ({
										...inputs,
										...(inputs.geometry === undefined
											? { geometry: readObject(geometry) }
											: {}),
										installation: readObject(plan),
									}))
								}
							/>
						</fieldset>
					)}
					{calculationsOpened && (
						<div
							hidden={
								!["energy", "calculations", "equipment"].includes(workspace)
							}
						>
							<EnergyWorkspace
								draft={draft}
								edit={editEnergy}
								flush={flush}
								acknowledgeProject={acknowledgeProject}
								session={session}
								client={client}
								recheck={recheck}
								locale={config.locale}
								active={["energy", "calculations", "equipment"].includes(
									workspace,
								)}
								equipmentFocus={workspace === "equipment"}
								openEquipment={() => chooseWorkspace("equipment")}
								openResults={() => chooseWorkspace("calculations")}
								recoveryScopes={recoveryScopes}
								recoveryChecking={recoveryChecking}
								onValidity={setEnergyValid}
								openProfiles={() => chooseWorkspace("energy")}
								openDesign={() => chooseWorkspace("design")}
								sceneModuleUrl={config.sceneModuleUrl ?? null}
								blocked={
									busy ||
									recoveries.length > 0 ||
									Boolean(draft.conflict) ||
									!gridValid ||
									!ruleValid ||
									!briefValid ||
									!designValid ||
									recoveryChecking ||
									discoveryFailed
								}
							/>
						</div>
					)}
					{workspace !== "calculations" && (
						<div className="lp-project-next">
							<button
								type="button"
								className="lp-button"
								onClick={() => {
									if (workspace === "equipment")
										chooseWorkspace("calculations", true);
									else if (
										workspace === "energy" ||
										workspace === "installation"
									)
										chooseWorkspace("equipment");
									else if (
										workspace === "design" ||
										brief.system_scope === "storage_only"
									)
										chooseWorkspace("energy");
									else chooseWorkspace("design");
								}}
							>
								{workspace === "equipment"
									? __("Review & share", "linker-tools")
									: workspace === "energy" || workspace === "installation"
										? __("Continue to system", "linker-tools")
										: workspace === "design" ||
											  brief.system_scope === "storage_only"
											? __("Continue to energy use", "linker-tools")
											: __("Continue to solar", "linker-tools")}
								<Icon name="arrow" />
							</button>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}

export default ProjectEditor;
