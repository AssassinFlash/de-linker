import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { Configuration } from "../data/config.ts";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { DraftStore } from "../data/DraftStore.ts";
import type { Session } from "../data/protocol.ts";
import {
	MAX_PROJECT_TITLE_LENGTH,
	projectTitleSearch,
	readProjectPage,
} from "../data/projectIndex.ts";
import { recoveryScopes } from "../data/recoveryScopes.ts";
import { readEntryHints } from "../domain/entryHints.ts";
import { __ } from "../i18n.ts";
import { NewProject } from "./NewProject.tsx";
import { Notice } from "./Notice.tsx";

export function HomepageComparison({
	config,
	session,
	client,
	store,
	target,
	recheck,
}: {
	config: Configuration;
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	target: URL;
	recheck: () => void;
}) {
	const scope = session.query_scope;
	const pageSize = Math.min(30, session.runtime.limits.max_page_size);
	const [search, setSearch] = useState("");
	const [savedProject, setSavedProject] = useState("");
	const titleQuery = projectTitleSearch(search);
	const admitted = client.isCurrentScope(scope) && !session.claim_pending;
	const recovery = useQuery({
		queryKey: [scope, "homepage-recovery-scopes"],
		queryFn: ({ signal }) => recoveryScopes(client, scope, signal),
		enabled: admitted && session.kind !== "guest",
	});
	const projects = useQuery({
		queryKey: [scope, "homepage-projects", titleQuery],
		queryFn: async ({ signal }) =>
			readProjectPage(
				await client.query(
					"projects/list",
					{
						schema_version: 1,
						page_size: pageSize,
						after: null,
						...(titleQuery && { title_query: titleQuery }),
					},
					scope,
					signal,
				),
				pageSize,
			),
		enabled: admitted,
	});
	function openProject(projectId: string, roof = false): boolean {
		if (!client.isCurrentScope(scope) || session.claim_pending) return false;
		const url = new URL(target.href);
		url.searchParams.set("project", projectId);
		if (!roof) url.searchParams.set("guided", "inquiry");
		url.hash = roof ? "sc-roof" : "sc-system";
		location.assign(url.href);
		return true;
	}
	const rows = projects.data?.items ?? [];
	const chosen = rows.some((row) => row.id === savedProject)
		? savedProject
		: "";
	const picker = (
		<>
			{(rows.length > 0 || search) && (
				<div className="sc-card sc-fields">
					<label className="sc-field">
						<span>{__("Saved projects", "linker-tools")}</span>
						<select
							value={chosen}
							onChange={(event) => setSavedProject(event.currentTarget.value)}
						>
							<option value="">{__("New project", "linker-tools")}</option>
							{rows.map((project) => (
								<option key={project.id} value={project.id}>
									{project.title}
								</option>
							))}
						</select>
					</label>
					{(projects.data?.next || search) && (
						<label className="sc-field">
							<span>{__("Search projects", "linker-tools")}</span>
							<input
								type="search"
								value={search}
								maxLength={MAX_PROJECT_TITLE_LENGTH}
								onChange={(event) => {
									setSearch(event.currentTarget.value);
									setSavedProject("");
								}}
							/>
						</label>
					)}
				</div>
			)}
			{projects.isError && (
				<Notice error>
					{__("Saved projects could not be loaded.", "linker-tools")}{" "}
					<button
						className="sc-button"
						type="button"
						onClick={() => void projects.refetch()}
					>
						{__("Try again", "linker-tools")}
					</button>
				</Notice>
			)}
		</>
	);
	return (
		<div
			className="sc-configurator sc-intake sc-home-comparison"
			id="compare-project"
		>
			<header className="sc-section-head">
				<div>
					<h2>{__("Compare options for your project", "linker-tools")}</h2>
					<p>
						{__(
							"Enter your project details or use a saved project.",
							"linker-tools",
						)}
					</p>
				</div>
				<a className="sc-button" href={new URL("?step=roof", target).href}>
					{__("Start with your roof", "linker-tools")}
				</a>
			</header>
			{session.claim_pending ? (
				<Notice>
					{__(
						"Projects from the guest session are still being linked to your account.",
						"linker-tools",
					)}{" "}
					<button className="sc-button" type="button" onClick={recheck}>
						{__("Check session", "linker-tools")}
					</button>
				</Notice>
			) : (
				<NewProject
					config={config}
					locale={config.locale}
					session={session}
					client={client}
					store={store}
					recheck={recheck}
					recoveryScopes={recovery.data}
					recoveryChecking={session.kind !== "guest" && recovery.isPending}
					recoveryDiscoveryFailed={recovery.isError}
					entryHints={readEntryHints(new URL(location.href).searchParams)}
					openOnLoad
					created={(project, destination, openResult) =>
						openResult ? openProject(project.id, destination === "roof") : true
					}
					homeComparison={{
						picker,
						savedProject: chosen,
						compareSaved: openProject,
					}}
				/>
			)}
		</div>
	);
}
