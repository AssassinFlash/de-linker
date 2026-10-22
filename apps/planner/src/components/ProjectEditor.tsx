import { useEffect, useState } from "react";
import type { Configuration } from "../data/config.ts";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { DraftStore } from "../data/DraftStore.ts";
import type { Project, Session } from "../data/protocol.ts";
import { useProjectDraft } from "../data/useProjectDraft.ts";
import {
	editDraft,
	isDirty,
	keepLocalAgainst,
	redoDraft,
	undoDraft,
	useRemote,
} from "../domain/draft.ts";
import { emptyBrief, readBrief } from "../domain/brief.ts";
import { __, sprintf } from "../i18n.ts";
import { BriefForm } from "./BriefForm.tsx";
import { Icon } from "./Icon.tsx";
import { Notice } from "./Notice.tsx";
import { RevisionComparison } from "./RevisionComparison.tsx";

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
	close: () => void;
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
	const [closing, setClosing] = useState(false);
	const [closeBlocked, setCloseBlocked] = useState(false);
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
		if (!valid) {
			setCloseBlocked(true);
			document
				.querySelector<HTMLElement>(
					'[data-linker-planner] [aria-invalid="true"]',
				)
				?.focus();
			return;
		}
		setClosing(true);
		if (!draft || (!isDirty(draft) && !draft.pending) || (await flush()))
			close();
		else {
			setCloseBlocked(true);
			setClosing(false);
		}
	}
	if (!draft)
		return <p role="status">{__("Opening project…", "linker-tools")}</p>;
	const dirty = isDirty(draft);
	let brief;
	try {
		brief =
			draft.history.current.brief === undefined
				? emptyBrief()
				: readBrief(draft.history.current.brief);
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
			<header className="lp-project-bar">
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
					{closeBlocked && (
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
					</fieldset>
				</div>
			</div>
		</div>
	);
}
