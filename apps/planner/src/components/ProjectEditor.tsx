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

export function ProjectEditor({
	project,
	session,
	client,
	store,
	config,
	recheck,
	close,
}: {
	project: Project;
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	config: Configuration;
	recheck: () => void;
	close: () => boolean;
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
	const [valid, setValid] = useState(true);
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
	try {
		brief =
			draft.history.current.brief === undefined
				? emptyBrief()
				: readBrief(draft.history.current.brief);
		selections = readSelections(draft.history.current.profile_selections);
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
		<div className="lp-project">
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
				</div>
				<div className="lp-edit-actions">
					<span className="lp-save-state" role="status">
						{busy
							? __("Saving…", "linker-tools")
							: draft.pending
								? __("Save not confirmed", "linker-tools")
								: !valid
									? __("Input needs attention", "linker-tools")
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
						disabled={!draft.history.past.length}
						onClick={() => update(undoDraft)}
					>
						<Icon name="undo" />
					</button>
					<button
						className="lp-icon-button"
						title={__("Redo", "linker-tools")}
						aria-label={__("Redo", "linker-tools")}
						disabled={!draft.history.future.length}
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
			</header>
			<div className="lp-project-layout">
				<aside className="lp-project-aside">
					<span className="lp-eyebrow">{__("Project", "linker-tools")}</span>
					<h1>{project.title}</h1>
					<p>
						{__(
							"Site data is saved with your project. A roof layout can be added later.",
							"linker-tools",
						)}
					</p>
					<nav aria-label={__("Project sections", "linker-tools")}>
						<a href="#lp-brief-use">
							<Icon name="folder" />
							{__("Project brief", "linker-tools")}
						</a>
						<a href="#lp-site">
							<Icon name="location" />
							{__("Project location", "linker-tools")}
						</a>
						<a href="#lp-load">
							<Icon name="layers" />
							{__("Electricity consumption", "linker-tools")}
						</a>
						<a href="#lp-profiles">
							<Icon name="layers" />
							{__("Interval data", "linker-tools")}
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
				<div className="lp-editor-main">
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
					{((closeBlocked === "invalid" && !valid) ||
						(closeBlocked === "recovery" &&
							recoveryFailed &&
							(dirty || draft.pending))) && (
						<Notice error>
							{!valid
								? __(
										"Correct the highlighted input before leaving this project.",
										"linker-tools",
									)
								: __(
										"Save the project before leaving. Browser recovery could not be stored.",
										"linker-tools",
									)}
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
						<BriefForm
							brief={brief}
							config={config}
							onValidity={setValid}
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
					</fieldset>
				</div>
			</div>
		</div>
	);
}
