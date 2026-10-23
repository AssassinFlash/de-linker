import { useCallback, useEffect, useRef, useState } from "react";
import type { Configuration } from "../data/config.ts";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { DraftStore } from "../data/DraftStore.ts";
import type { Project, Session } from "../data/protocol.ts";
import { useProjectDraft } from "../data/useProjectDraft.ts";
import { useProjectBar } from "../data/useProjectBar.ts";
import {
	editDraft,
	isDirty,
	keepLocalAgainst,
	redoDraft,
	undoDraft,
	useRemote,
} from "../domain/draft.ts";
import { emptyBrief, readBrief } from "../domain/brief.ts";
import { readSelections } from "../domain/profiles.ts";
import type { Measurement } from "../domain/profiles.ts";
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
import { revealActionResult } from "./revealActionResult.ts";

type ProjectWorkspace = "overview" | "site" | "energy" | "design";
const workspaceHash = {
	overview: "lp-overview",
	site: "lp-site",
	energy: "lp-load",
	design: "lp-design",
} as const;
const workspaceTarget = { ...workspaceHash, site: "lp-brief-use" } as const;
function workspaceFromHash(): ProjectWorkspace {
	if (["#lp-site", "#lp-brief-use", "#lp-notes"].includes(window.location.hash))
		return "site";
	if (["#lp-load", "#lp-profiles"].includes(window.location.hash))
		return "energy";
	return window.location.hash === "#lp-design" ? "design" : "overview";
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
		busy,
		failed,
		recoveryFailed,
		recovered,
		recoveries,
		restore,
	} = useProjectDraft(project, session, client, store, recheck);
	const [briefValid, setBriefValid] = useState(true);
	const [designValid, setDesignValid] = useState(true);
	const valid = briefValid && designValid;
	const [workspace, setWorkspace] =
		useState<ProjectWorkspace>(workspaceFromHash);
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
	function chooseWorkspace(next: ProjectWorkspace) {
		if (!client.isCurrentScope(session.query_scope)) return;
		if (!valid) {
			setCloseBlocked("invalid");
			return;
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
		setWorkspace(next);
		window.history.replaceState(null, "", "#" + workspaceHash[next]);
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
	if (!draft)
		return <p role="status">{__("Opening project…", "linker-tools")}</p>;
	const dirty = isDirty(draft);
	let brief;
	let selections;
	let geometry;
	let geometryImports;
	try {
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
			<header className="lp-project-bar" ref={bar}>
				<div className="lp-breadcrumb">
					<button
						className="lp-text-button"
						disabled={closing}
						onClick={() => {
							void leave();
						}}
					>
						{__("Projects", "linker-tools")}
					</button>
					<span aria-hidden="true">/</span>
					<span>{project.title}</span>
					<select
						className="lp-mobile-workspace"
						aria-label={__("Project sections", "linker-tools")}
						value={workspace}
						onChange={(event) =>
							chooseWorkspace(event.currentTarget.value as ProjectWorkspace)
						}
					>
						<option value="overview">
							{__("Project overview", "linker-tools")}
						</option>
						<option value="site">
							{__("Site and project", "linker-tools")}
						</option>
						<option value="design">{__("Roof design", "linker-tools")}</option>
						<option value="energy">
							{__("Energy inputs", "linker-tools")}
						</option>
					</select>
				</div>
				<div className="lp-edit-actions">
					<span className="lp-save-state" role="status">
						{busy
							? __("Saving…", "linker-tools")
							: draft.pending
								? __("Save not confirmed", "linker-tools")
								: !briefValid
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
				{((closeBlocked === "invalid" && !valid) ||
					(closeBlocked === "recovery" &&
						recoveryFailed &&
						(dirty || draft.pending))) && (
					<div className="lp-navigation-refusal">
						<Notice error>
							{!briefValid
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
			</header>
			<div className="lp-project-layout">
				<aside className="lp-project-aside">
					<div className="lp-project-nav-title">
						<span className="lp-nav-mark" aria-hidden="true">
							L
						</span>
						<span>{__("Solution Configurator", "linker-tools")}</span>
					</div>
					<span className="lp-eyebrow">
						{__("Current project", "linker-tools")}
					</span>
					<nav aria-label={__("Project sections", "linker-tools")}>
						<a
							href="#lp-overview"
							aria-current={workspace === "overview" ? "page" : undefined}
							onClick={(event) => {
								event.preventDefault();
								chooseWorkspace("overview");
							}}
						>
							<Icon name="overview" />
							{__("Project overview", "linker-tools")}
						</a>
						<a
							href="#lp-site"
							aria-current={workspace === "site" ? "page" : undefined}
							onClick={(event) => {
								event.preventDefault();
								chooseWorkspace("site");
							}}
						>
							<Icon name="location" />
							{__("Site and project", "linker-tools")}
						</a>
						<a
							href="#lp-design"
							aria-current={workspace === "design" ? "page" : undefined}
							onClick={(event) => {
								event.preventDefault();
								chooseWorkspace("design");
							}}
						>
							<Icon name="layers" />
							{__("Roof design", "linker-tools")}
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
							{__("Energy inputs", "linker-tools")}
						</a>
					</nav>
					<div className="lp-source-note">
						<Icon name="check" />
						<span>
							{__(
								"Project information is kept with its source and revision.",
								"linker-tools",
							)}
						</span>
					</div>
				</aside>
				<div className="lp-editor-main lp-editor-with-design">
					<header className="lp-project-title">
						<span className="lp-eyebrow">
							{__("Current project", "linker-tools")}
						</span>
						<h1>{project.title}</h1>
						<p>
							{__(
								"Site data and roof layouts are saved in the same project.",
								"linker-tools",
							)}
						</p>
					</header>
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
							{__(
								"The save could not be confirmed. Your input is still here.",
								"linker-tools",
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
									onClick={() => update(keepLocalAgainst)}
								>
									{__("Keep open changes", "linker-tools")}
								</button>
								<button
									className="lp-button lp-button-secondary"
									onClick={() => update(useRemote)}
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
							<ProjectOverview
								brief={brief}
								geometry={geometry}
								config={config}
								choose={chooseWorkspace}
							/>
						</div>
						<BriefForm
							brief={brief}
							workspace={workspace}
							config={config}
							onValidity={setBriefValid}
							onChange={(next) =>
								update((previous) =>
									editDraft(previous, {
										...previous.history.current,
										brief: readBrief(next),
									}),
								)
							}
						/>
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
									<summary>{measurementLabel(role as Measurement)}</summary>
									<OwnedProfile
										projectId={project.id}
										assetId={assetId}
										session={session}
										client={client}
										locale={config.locale}
										expectedRole={role as Measurement}
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
												delete chosen[role as Measurement];
												return editDraft(previous, {
													...previous.history.current,
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
											...previous.history.current,
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
							<DesignEditor
								geometry={geometry}
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
				</div>
			</div>
		</div>
	);
}
