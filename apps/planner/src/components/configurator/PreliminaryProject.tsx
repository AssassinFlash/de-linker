import { useEffect, useRef, useState } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { DraftStore } from "../../data/DraftStore.ts";
import type { Project, Session } from "../../data/protocol.ts";
import { pendingInquiry } from "../../data/inquiryRecovery.ts";
import { useProjectDraft } from "../../data/useProjectDraft.ts";
import { emptyBrief, readBrief, type Brief } from "../../domain/brief.ts";
import { editDraft, isDirty } from "../../domain/draft.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { changeExistingSystem } from "./ProjectEquipment.tsx";
import { energyGoal } from "./EnergyDemand.tsx";
import { PreliminaryOptions } from "./PreliminaryOptions.tsx";
import { InquiryStages, ProjectHeading } from "./ProjectHeading.tsx";
import { ReviewInquiry } from "./ReviewInquiry.tsx";
import { usePlanningOperations } from "../../data/usePlanningOperations.ts";
import { InquiryExportBar } from "./InquiryExportBar.tsx";
import { useReportLogo } from "./ReportLogo.tsx";

function PreliminaryExports({
	project,
	session,
	client,
	locale,
	recheck,
}: {
	project: Project;
	session: Session;
	client: PlannerClient;
	locale: string;
	recheck: () => void;
}) {
	const operations = usePlanningOperations({
		projectId: project.id,
		session,
		client,
		recheck,
	});
	const { logo, logoField, logoPending } = useReportLogo(operations.busy);
	return (
		<InquiryExportBar
			project={project}
			scope={session.query_scope}
			client={client}
			locale={locale}
			logo={logo?.data ?? null}
			logoField={logoField}
			blocked={logoPending || operations.checking || operations.busy}
			prepare={async (branding) => {
				const prepared = await operations.start("runs/report", {
					expected_revision: project.revision,
					options: {
						locale: locale.startsWith("de") ? "de" : "en",
						logo: branding,
					},
				});
				return prepared?.path === "runs/report" ? prepared.run : undefined;
			}}
		/>
	);
}

export function PreliminaryProject({
	project,
	session,
	client,
	store,
	locale,
	comparing,
	guided,
	recoveringRevision,
	navigate,
	recheck,
}: {
	project: Project;
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	locale: string;
	comparing: boolean;
	guided: boolean;
	recoveringRevision: boolean;
	navigate: (
		destination:
			"sc-preliminary-options" | "sc-preliminary-review" | "sc-project",
		confirmed?: Project,
	) => void;
	recheck: () => void;
}) {
	const controller = useProjectDraft(project, session, client, store, recheck);
	const draft = controller.draft;
	const reviewed = recoveringRevision ? project : (draft?.baseline ?? project);
	const brief =
		reviewed.inputs.brief === undefined
			? emptyBrief()
			: readBrief(reviewed.inputs.brief);
	const showOptions = comparing || !brief.system_scope;
	const [inquiryPending, setInquiryPending] = useState(() =>
		Boolean(pendingInquiry(session.query_scope, project)),
	);
	const [saveNeedsEditor, setSaveNeedsEditor] = useState(false);
	const automaticSaveStarted = useRef(false);
	const admitted = client.isCurrentScope(session.query_scope);
	const blocked = !draft || controller.busy || inquiryPending || !admitted;
	// The full project editor already owns conflict and cross-account recovery.
	const needsRecovery = Boolean(
		draft?.conflict ||
		controller.recoveries.length ||
		controller.inputContractRequired ||
		saveNeedsEditor,
	);
	const replaying = recoveringRevision || inquiryPending;
	const dirty = draft !== null && isDirty(draft);
	const ready =
		replaying ||
		(admitted && draft !== null && !dirty && !draft.pending && !needsRecovery);
	const autoSave =
		!showOptions &&
		!replaying &&
		dirty &&
		!draft?.pending &&
		!blocked &&
		!needsRecovery &&
		!controller.failed;
	useEffect(() => {
		if (!autoSave || automaticSaveStarted.current) return;
		automaticSaveStarted.current = true;
		void saveSelection();
	});

	async function choose(
		systemScope: NonNullable<Brief["system_scope"]>,
		keepInverter?: boolean,
	) {
		if (!draft || needsRecovery || blocked || draft.pending) return;
		controller.update((previous) =>
			editDraft(previous, {
				...(keepInverter === undefined
					? previous.history.current
					: changeExistingSystem(previous.history.current, {
							keep_inverter: keepInverter,
						})),
				brief: {
					...readBrief(previous.history.current.brief ?? emptyBrief()),
					system_scope: systemScope,
				},
			}),
		);
		await saveSelection();
	}
	async function saveSelection() {
		try {
			const saved = await controller.save();
			if (saved) navigate("sc-preliminary-review", saved);
		} catch {
			setSaveNeedsEditor(true);
		}
	}
	return (
		<div className="sc-configurator sc-intake">
			<ProjectHeading
				title={reviewed.title}
				anchor={
					showOptions ? "sc-preliminary-options" : "sc-preliminary-review"
				}
			/>
			<InquiryStages current={showOptions ? 1 : 3} />
			{showOptions && (
				<div className="sc-main">
					<PreliminaryOptions
						projectTitle={reviewed.title}
						locale={locale}
						inputs={draft?.history.current ?? reviewed.inputs}
						disabled={blocked || needsRecovery || Boolean(draft?.pending)}
						choose={choose}
						{...((guided || energyGoal(reviewed.inputs)) && {
							chooseRetrofit: (keep: boolean) =>
								void choose("storage_addition", keep),
						})}
					/>
					{inquiryPending && (
						<button
							className="sc-button"
							type="button"
							onClick={() => navigate("sc-preliminary-review")}
						>
							{__("Check inquiry status", "linker-tools")}
						</button>
					)}
				</div>
			)}
			{!replaying && (showOptions || !ready) && (
				<div className="sc-main">
					{(controller.busy || autoSave) && (
						<p role="status">{__("Saving…", "linker-tools")}</p>
					)}
					{!draft && !showOptions && (
						<p role="status">{__("Opening the project…", "linker-tools")}</p>
					)}
					{needsRecovery ? (
						<Notice error>
							<p>{__("Save not confirmed", "linker-tools")}</p>
							<button
								className="sc-button"
								type="button"
								disabled={blocked}
								onClick={() => navigate("sc-project")}
							>
								{__("Open project", "linker-tools")}
							</button>
						</Notice>
					) : (
						(draft?.pending || controller.failed) &&
						!controller.busy && (
							<Notice error>
								<p>{__("Save not confirmed", "linker-tools")}</p>
								<button
									className="sc-button"
									type="button"
									disabled={blocked}
									onClick={() => void saveSelection()}
								>
									{__("Retry save", "linker-tools")}
								</button>
							</Notice>
						)
					)}
				</div>
			)}
			{!showOptions && !replaying && ready && (
				<PreliminaryExports
					key={reviewed.id}
					project={reviewed}
					session={session}
					client={client}
					locale={locale}
					recheck={recheck}
				/>
			)}
			{brief.system_scope && (
				<ReviewInquiry
					project={reviewed}
					direction={brief.system_scope}
					client={client}
					scope={session.query_scope}
					locale={locale}
					active={!showOptions && ready}
					ready={ready}
					changeSelection={() => navigate("sc-preliminary-options")}
					enterDetails={
						blocked || draft?.pending ? undefined : () => navigate("sc-project")
					}
					recheck={recheck}
					inquiryPending={setInquiryPending}
				/>
			)}
		</div>
	);
}
