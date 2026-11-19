import { useState } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { DraftStore } from "../../data/DraftStore.ts";
import type { Project, Session } from "../../data/protocol.ts";
import { pendingInquiry } from "../../data/inquiryRecovery.ts";
import { useProjectDraft } from "../../data/useProjectDraft.ts";
import { emptyBrief, readBrief, type Brief } from "../../domain/brief.ts";
import { editDraft } from "../../domain/draft.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { PreliminaryOptions } from "./PreliminaryOptions.tsx";
import { InquiryStages, ProjectHeading } from "./ProjectHeading.tsx";
import { ReviewInquiry } from "./ReviewInquiry.tsx";

export function PreliminaryProject({
	project,
	session,
	client,
	store,
	locale,
	comparing,
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
	recoveringRevision: boolean;
	navigate: (
		destination:
			"sc-preliminary-options" | "sc-preliminary-review" | "sc-project",
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
	const blocked =
		!draft ||
		controller.busy ||
		inquiryPending ||
		!client.isCurrentScope(session.query_scope);
	// The full project editor already owns conflict and cross-account recovery.
	const needsRecovery = Boolean(
		draft?.conflict || controller.recoveries.length,
	);

	async function choose(systemScope: NonNullable<Brief["system_scope"]>) {
		if (!draft || needsRecovery || blocked || draft.pending) return;
		controller.update((previous) =>
			editDraft(previous, {
				...previous.history.current,
				brief: {
					...readBrief(previous.history.current.brief ?? emptyBrief()),
					system_scope: systemScope,
				},
			}),
		);
		await saveSelection();
	}
	async function saveSelection() {
		const saved = await controller.save();
		if (saved) navigate("sc-preliminary-review");
	}
	return (
		<div className="sc-configurator">
			<ProjectHeading
				anchor={
					showOptions ? "sc-preliminary-options" : "sc-preliminary-review"
				}
			/>
			<InquiryStages reviewing={!showOptions} />
			{showOptions && (
				<div className="sc-main">
					<PreliminaryOptions
						inputs={draft?.history.current ?? reviewed.inputs}
						disabled={blocked || needsRecovery || Boolean(draft?.pending)}
						choose={(direction) => void choose(direction)}
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
					{controller.busy && (
						<p role="status">{__("Saving…", "linker-tools")}</p>
					)}
					{needsRecovery ? (
						<Notice error>
							<button
								className="sc-button"
								type="button"
								onClick={() => navigate("sc-project")}
							>
								{__("Open project", "linker-tools")}
							</button>
						</Notice>
					) : (
						(draft?.pending || controller.failed) &&
						!controller.busy && (
							<Notice error>
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
			{brief.system_scope && (
				<ReviewInquiry
					project={reviewed}
					direction={brief.system_scope}
					client={client}
					scope={session.query_scope}
					locale={locale}
					active={!showOptions}
					changeSelection={() => navigate("sc-preliminary-options")}
					recheck={recheck}
					inquiryPending={setInquiryPending}
				/>
			)}
		</div>
	);
}
