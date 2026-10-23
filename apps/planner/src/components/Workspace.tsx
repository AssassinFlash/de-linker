import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
	useInfiniteQuery,
	useQuery,
	useQueryClient,
} from "@tanstack/react-query";
import type { Configuration } from "../data/config.ts";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { DraftStore } from "../data/DraftStore.ts";
import type { JsonObject, Project, Session } from "../data/protocol.ts";
import { readProject } from "../data/readProtocol.ts";
import { readProjectPage } from "../data/projectIndex.ts";
import { useSiteIntegration } from "../data/useSiteIntegration.ts";
import { recoveryScopes } from "../data/recoveryScopes.ts";
import { __, sprintf } from "../i18n.ts";
import { Icon } from "./Icon.tsx";
import { NewProject } from "./NewProject.tsx";
import { ProjectEditor } from "./ProjectEditor.tsx";
import { Notice } from "./Notice.tsx";

function currentProject(): string | null {
	const value = new URL(location.href).searchParams.get("project");
	return value && /^[a-f0-9]{32}$/.test(value) ? value : null;
}
export function Workspace({
	client,
	store,
	config,
	session,
	recheck,
}: {
	client: PlannerClient;
	store: DraftStore;
	config: Configuration;
	session: Session;
	recheck: () => void;
}) {
	const [selected, setSelected] = useState<string | null>(currentProject);
	const cache = useQueryClient();
	const recovery = useQuery({
		queryKey: [session.query_scope, "recovery-scopes", session.claim_pending],
		queryFn: ({ signal }) =>
			session.kind === "guest"
				? Promise.resolve([session.query_scope])
				: recoveryScopes(client, session.query_scope, signal),
	});
	const previousSession = useRef(session);
	useEffect(() => {
		if (previousSession.current !== session) {
			previousSession.current = session;
			void cache.invalidateQueries({
				queryKey: [session.query_scope, "recovery-scopes"],
			});
		}
	}, [cache, session]);
	const select = useCallback(
		(id: string | null) => {
			if (!client.isCurrentScope(session.query_scope)) return;
			const url = new URL(location.href);
			if (id) url.searchParams.set("project", id);
			else url.searchParams.delete("project");
			url.hash = "";
			history.replaceState(null, "", url);
			setSelected(id);
		},
		[client, session.query_scope],
	);
	const pageSize = Math.min(30, session.runtime.limits.max_page_size); // UI page policy, not total project capacity.
	const index = useInfiniteQuery({
		queryKey: [session.query_scope, "projects"],
		initialPageParam: null as JsonObject | null,
		queryFn: async ({ pageParam, signal }) =>
			readProjectPage(
				await client.query(
					"projects/list",
					{ schema_version: 1, page_size: pageSize, after: pageParam },
					session.query_scope,
					signal,
				),
				pageSize,
			),
		getNextPageParam: (page) => page.next ?? undefined,
		enabled: selected === null,
	});
	const project = useQuery({
		queryKey: [session.query_scope, "project", selected],
		queryFn: async ({ signal }) =>
			readProject(
				await client.query(
					"projects/read",
					{ schema_version: 1, project_id: selected, revision: null },
					session.query_scope,
					signal,
				),
			),
		enabled: selected !== null,
		staleTime: Infinity,
	});
	useSiteIntegration(selected);
	const projects = useMemo(() => {
		const seen = new Set<string>();
		return (index.data?.pages.flatMap((page) => page.items) ?? []).filter(
			(item) => {
				if (seen.has(item.id)) return false;
				seen.add(item.id);
				return true;
			},
		);
	}, [index.data]);
	function created(project: Project) {
		if (!client.isCurrentScope(session.query_scope)) return false;
		cache.setQueryData([session.query_scope, "project", project.id], project);
		void cache.invalidateQueries({
			queryKey: [session.query_scope, "projects"],
		});
		select(project.id);
		return true;
	}
	if (selected)
		return project.data ? (
			<ProjectEditor
				key={session.query_scope + ":" + selected}
				project={project.data}
				client={client}
				store={store}
				config={config}
				session={session}
				recheck={recheck}
				recoveryScopes={recovery.data}
				recoveryChecking={recovery.isFetching}
				recoveryFailed={recovery.isError}
				close={() => {
					if (!client.isCurrentScope(session.query_scope)) return false;
					void cache.invalidateQueries({
						queryKey: [session.query_scope, "projects"],
					});
					cache.removeQueries({
						queryKey: [session.query_scope, "project", selected],
					});
					select(null);
					return true;
				}}
			/>
		) : (
			<div className="lp-page">
				<button className="lp-text-button" onClick={() => select(null)}>
					{__("Back to projects", "linker-tools")}
				</button>
				{project.isError ? (
					<Notice error>
						<p>
							{__(
								"This project could not be opened in the current session.",
								"linker-tools",
							)}
						</p>
						<button className="lp-button" onClick={recheck}>
							{__("Check session", "linker-tools")}
						</button>
					</Notice>
				) : (
					<p role="status">{__("Opening project…", "linker-tools")}</p>
				)}
			</div>
		);

	return (
		<div className="lp-workspace">
			<aside className="lp-workspace-rail">
				<div className="lp-brand-symbol" aria-hidden="true">
					L<span>·</span>
				</div>
				<span className="lp-rail-caption">
					{__("Solution Configurator", "linker-tools")}
				</span>
				<span className="lp-rail-current">
					<Icon name="folder" />
					{__("Projects", "linker-tools")}
				</span>
				<div className="lp-rail-session">
					{session.kind === "guest"
						? __("Guest workspace", "linker-tools")
						: __("Account workspace", "linker-tools")}
				</div>
			</aside>
			<div className="lp-page">
				<header className="lp-workspace-header">
					<div>
						<span className="lp-eyebrow">
							{__("Solution Configurator", "linker-tools")}
						</span>
						<h1>{__("Your projects", "linker-tools")}</h1>
						<p>
							{__(
								"Site information, roof layout and system planning belong to the same project.",
								"linker-tools",
							)}
						</p>
					</div>
					<NewProject
						session={session}
						client={client}
						store={store}
						created={created}
						recheck={recheck}
						recoveryScopes={recovery.data}
						recoveryChecking={recovery.isFetching}
						recoveryDiscoveryFailed={recovery.isError}
					/>
				</header>
				{recovery.isError && (
					<Notice error>
						<p>
							{__(
								"Unconfirmed project creations and CSV imports from earlier sessions could not be checked. Any recovery data already stored in this browser remains unchanged.",
								"linker-tools",
							)}
						</p>
						<button
							className="lp-text-button"
							onClick={() => void recovery.refetch()}
						>
							{__("Try again", "linker-tools")}
						</button>
					</Notice>
				)}
				{session.claim_pending && (
					<Notice>
						{__(
							"Projects from the guest session are still being linked to your account.",
							"linker-tools",
						)}
						<button className="lp-text-button" onClick={recheck}>
							{__("Check session", "linker-tools")}
						</button>
					</Notice>
				)}
				<section
					className="lp-project-index"
					aria-labelledby="lp-projects-heading"
				>
					<div className="lp-index-heading">
						<h2 id="lp-projects-heading">
							{__("Saved projects", "linker-tools")}
						</h2>
						<button
							className="lp-icon-button"
							aria-label={__("Refresh projects", "linker-tools")}
							disabled={index.isFetching}
							onClick={() => {
								void index.refetch();
							}}
						>
							<Icon name="refresh" />
						</button>
					</div>
					{index.isPending && (
						<p role="status">{__("Loading projects…", "linker-tools")}</p>
					)}
					{index.isError && (
						<Notice error>
							<p>{__("Saved projects could not be loaded.", "linker-tools")}</p>
							<button className="lp-button" onClick={recheck}>
								{__("Try again", "linker-tools")}
							</button>
						</Notice>
					)}
					{!index.isPending && !index.isError && !projects.length && (
						<div className="lp-empty">
							<Icon name="layers" width="36" height="36" />
							<h3>{__("Project workspace", "linker-tools")}</h3>
							<p>
								{__(
									"A project can start with the information already available. Roof drawing is optional.",
									"linker-tools",
								)}
							</p>
						</div>
					)}
					<div className="lp-project-rows">
						{projects.map((item) => (
							<button
								key={item.id}
								className="lp-project-row"
								onClick={() => select(item.id)}
							>
								<span className="lp-project-row-icon">
									<Icon name="folder" />
								</span>
								<span>
									<strong>{item.title}</strong>
									<small>
										{sprintf(__("Revision %d", "linker-tools"), item.revision)}{" "}
										<span aria-hidden="true">·</span>{" "}
										{new Intl.DateTimeFormat(config.locale, {
											dateStyle: "medium",
										}).format(new Date(item.updated_at * 1000))}
									</small>
								</span>
								<Icon name="arrow" />
							</button>
						))}
					</div>
					{index.hasNextPage && (
						<button
							className="lp-button lp-button-secondary"
							disabled={index.isFetchingNextPage}
							onClick={() => {
								void index.fetchNextPage();
							}}
						>
							{__("More projects", "linker-tools")}
						</button>
					)}
				</section>
				<footer className="lp-workspace-footnote">
					<Icon name="check" />
					<p>
						{session.kind === "guest"
							? __(
									"Guest projects are available in this browser session. Signing in links them to the account.",
									"linker-tools",
								)
							: __(
									"Saved projects are linked to your account.",
									"linker-tools",
								)}
					</p>
				</footer>
			</div>
		</div>
	);
}
