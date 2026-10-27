import { useEffect } from "react";
import { PLANNER_NAVIGATION } from "./plannerLocation.ts";
import type { Project, Session } from "./protocol.ts";

/** Same-window bridge between the two existing React roots; no second store. */
export function useGenieContext(
	project: Project,
	session: Session,
	unsaved: boolean,
) {
	useEffect(() => {
		const publish = () => {
			const params = new URL(location.href).searchParams;
			const comparison = params.get("compare");
			const run = params.get("run");
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
							planning_revision: project.revision,
							planning_run_ids: runs,
							planning_unsaved: unsaved,
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
			window.dispatchEvent(
				new CustomEvent("linker-genie-planning-context", { detail: null }),
			);
		};
	}, [project.id, project.title, project.revision, session.nonce, unsaved]);
}
