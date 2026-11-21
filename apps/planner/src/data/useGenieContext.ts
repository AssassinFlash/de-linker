import { useEffect } from "react";
import type { PlannerClient } from "./PlannerClient.ts";
import { PLANNER_NAVIGATION } from "./plannerLocation.ts";
import type { Project, Session } from "./protocol.ts";

/** Same-window bridge between the two existing React roots; no second store. */
export function useGenieContext(
	project: Project,
	session: Session,
	unsaved: boolean,
	selection?: {
		client: Pick<PlannerClient, "isCurrentScope">;
		report: { id: string; revision: number } | null;
		openReport?: { id: string; revision: number } | null;
		energyComparison?: boolean;
	},
) {
	const client = selection?.client;
	const energyComparison = selection?.energyComparison;
	const reportId = selection?.report?.id;
	const reportRevision = selection?.report?.revision;
	const openReportId = selection?.openReport?.id;
	const openReportRevision = selection?.openReport?.revision;
	useEffect(() => {
		const clear = () =>
			window.dispatchEvent(
				new CustomEvent("linker-genie-planning-context", { detail: null }),
			);
		const publish = (event?: Event) => {
			const params = new URL(location.href).searchParams;
			if (
				client &&
				(session.claim_pending ||
					!client.isCurrentScope(session.query_scope) ||
					params.get("project") !== project.id)
			) {
				clear();
				return;
			}
			const opener =
				event instanceof CustomEvent &&
				event.type === "linker-genie-planning-context-request"
					? event.detail?.opener
					: null;
			const choice =
				client && opener instanceof HTMLElement
					? opener.getAttribute("data-linker-genie-planning")
					: null;
			// The warm dock requests context in click capture, before React's onClick.
			if (choice && choice !== openReportId) {
				clear();
				return;
			}
			const comparison =
				!client || energyComparison ? params.get("compare") : null;
			const run = client ? (choice ?? reportId) : params.get("run");
			const savedReportRevision =
				choice === null
					? reportRevision
					: choice
						? openReportRevision
						: undefined;
			const runs =
				comparison &&
				/^[a-f0-9]{32},[a-f0-9]{32}$/.test(comparison) &&
				new Set(comparison.split(",")).size === 2
					? comparison.split(",")
					: run && /^[a-f0-9]{32}$/.test(run)
						? [run]
						: [];
			window.dispatchEvent(
				new CustomEvent("linker-genie-planning-context", {
					detail: {
						page: {
							type: "other",
							title: project.title,
							url: location.href,
							planning_project_id: project.id,
							planning_revision: savedReportRevision ?? project.revision,
							planning_run_ids: runs,
							planning_unsaved: savedReportRevision === undefined && unsaved,
						},
						// Existing guest CSRF nonce, sent only as a native request header.
						plannerNonce: session.nonce,
					},
				}),
			);
		};
		publish();
		for (const event of [
			PLANNER_NAVIGATION,
			"hashchange",
			"popstate",
			"linker-genie-planning-context-request",
		])
			window.addEventListener(event, publish);
		return () => {
			for (const event of [
				PLANNER_NAVIGATION,
				"hashchange",
				"popstate",
				"linker-genie-planning-context-request",
			])
				window.removeEventListener(event, publish);
			clear();
		};
	}, [
		client,
		energyComparison,
		project.id,
		project.title,
		project.revision,
		reportId,
		reportRevision,
		openReportId,
		openReportRevision,
		session.claim_pending,
		session.nonce,
		session.query_scope,
		unsaved,
	]);
}
