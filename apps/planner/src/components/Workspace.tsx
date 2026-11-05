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
import { ApiError } from "../data/protocol.ts";
import { readProject } from "../data/readProtocol.ts";
import { readProjectPage } from "../data/projectIndex.ts";
import { useSiteIntegration } from "../data/useSiteIntegration.ts";
import { clearCreationsForTitle } from "../data/recoveryIntents.ts";
import { recoveryScopes } from "../data/recoveryScopes.ts";
import { __, sprintf } from "../i18n.ts";
import { Icon } from "./Icon.tsx";
import { NewProject } from "./NewProject.tsx";
import { ProjectBriefStart } from "./ProjectBriefStart.tsx";
import { SavedSolutionStart } from "./SavedSolutionStart.tsx";
import { projectBriefId } from "../domain/projectBrief.ts";
import { savedSolutionId } from "../domain/savedSolution.ts";
import { ProjectEditor } from "./ProjectEditor.tsx";
import { Notice } from "./Notice.tsx";
import { ENTRY_QUERY_KEYS, readEntryHints } from "../domain/entryHints.ts";
import { readObject, wire } from "../data/readProtocol.ts";
import { replacePlannerLocation } from "../data/plannerLocation.ts";

function currentProject(): string | null {
	const value = new URL(location.href).searchParams.get("project");
	return value && /^[a-f0-9]{32}$/.test(value) ? value : null;
}
/** A delete binds one key to one revision, so a changed revision is a new
 * command and never reuses the key of the attempt that lost the race. */
function deleteCommand(
	projectId: string,
	revision: number,
	maxDepth: number,
	maxBytes: number,
): string {
	return wire(
		{
			schema_version: 1,
			project_id: projectId,
			expected_revision: revision,
			key: crypto.randomUUID(),
		},
		maxDepth,
		maxBytes,
	);
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
	const [savedSource, setSavedSource] = useState(() =>
		savedSolutionId(new URL(location.href).searchParams),
	);
	const [briefSource, setBriefSource] = useState(() =>
		projectBriefId(new URL(location.href).searchParams),
	);
	const [entryHints, setEntryHints] = useState(() =>
		readEntryHints(new URL(location.href).searchParams),
	);
	const cache = useQueryClient();
	const recovery = useQuery({
		queryKey: [session.query_scope, "recovery-scopes", session.claim_pending],
		queryFn: ({ signal }) =>
			session.kind === "guest"
				? Promise.resolve([session.query_scope])
				: recoveryScopes(client, session.query_scope, signal),
	});
	const recoveryAuthError =
		recovery.error instanceof ApiError &&
		([401, 403].includes(recovery.error.status) ||
			recovery.error.code === "session_changed");
	const recoveryRechecked = useRef(false);
	useEffect(() => {
		if (recovery.isSuccess) recoveryRechecked.current = false;
		if (recoveryAuthError && !recoveryRechecked.current) {
			recoveryRechecked.current = true;
			recheck();
		}
	}, [recheck, recovery.isSuccess, recoveryAuthError]);
	function retryRecovery() {
		if (recoveryAuthError || !client.isCurrentScope(session.query_scope))
			recheck();
		else void recovery.refetch();
	}
	const previousSession = useRef(session);
	useEffect(() => {
		if (previousSession.current !== session) {
			previousSession.current = session;
			// A parallel owned read may have failed when admission was withdrawn.
			// Retry those reads after native confirmation. Successful opening
			// snapshots stay pinned, so revalidation cannot reset an open draft.
			void cache.invalidateQueries({
				predicate: (query) =>
					query.queryKey[0] === session.query_scope &&
					(query.queryKey[1] === "recovery-scopes" ||
						query.queryKey[1] === "projects" ||
						query.state.status === "error"),
			});
		}
	}, [cache, session]);
	const select = useCallback(
		(id: string | null, destination = "") => {
			if (!client.isCurrentScope(session.query_scope)) return;
			const url = new URL(location.href);
			if (id) url.searchParams.set("project", id);
			else url.searchParams.delete("project");
			url.searchParams.delete("run");
			url.searchParams.delete("compare");
			url.searchParams.delete("energy_view");
			url.searchParams.delete("brief");
			for (const key of ENTRY_QUERY_KEYS) url.searchParams.delete(key);
			url.hash = destination;
			replacePlannerLocation(url);
			setEntryHints(null);
			setSavedSource(null);
			setBriefSource(null);
			setSelected(id);
		},
		[client, session.query_scope],
	);
	const pageSize = Math.min(30, session.runtime.limits.max_page_size); // UI page policy, not total project capacity.
	const index = useInfiniteQuery({
		queryKey: [session.query_scope, "projects", session.claim_pending],
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
		queryKey: [session.query_scope, "project", selected, session.claim_pending],
		queryFn: async ({ signal }) =>
			readProject(
				await client.query(
					"projects/read",
					{ schema_version: 1, project_id: selected, revision: null },
					session.query_scope,
					signal,
				),
			),
		enabled: selected !== null && !session.claim_pending,
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
	function created(project: Project, destination?: "design" | "equipment") {
		if (!client.isCurrentScope(session.query_scope)) return false;
		cache.setQueryData(
			[session.query_scope, "project", project.id, session.claim_pending],
			project,
		);
		void cache.invalidateQueries({
			queryKey: [session.query_scope, "projects"],
		});
		select(
			project.id,
			destination === "equipment"
				? "lp-equipment"
				: destination === "design"
					? "lp-design"
					: "lp-site",
		);
		return true;
	}
	const [confirmingDelete, setConfirmingDelete] = useState<string | null>(null);
	const [deleteBusy, setDeleteBusy] = useState(false);
	const [deleteRetry, setDeleteRetry] = useState<{
		id: string;
		body: string;
	} | null>(null);
	const [deleteFailure, setDeleteFailure] = useState<{
		id: string;
		kind: "handoff" | "changed" | "failed";
	} | null>(null);
	const remove = useCallback(
		async (item: { id: string; title: string; revision: number }) => {
			if (deleteBusy || !client.isCurrentScope(session.query_scope)) return;
			// A command key is bound to one canonical command. Repeated transport
			// failures repeat the captured bytes so the engine can replay its
			// receipt; a conflict starts a new command for the current revision.
			const body =
				deleteRetry?.id === item.id
					? deleteRetry.body
					: deleteCommand(
							item.id,
							item.revision,
							session.runtime.limits.max_json_depth,
							session.runtime.limits.max_body_bytes,
						);
			setDeleteRetry({ id: item.id, body });
			setDeleteBusy(true);
			try {
				const reply = readObject(
					await client.send("projects/delete", body, session.query_scope),
				);
				if (
					reply.project_id !== item.id ||
					reply.deleted !== true ||
					typeof reply.revision !== "number"
				)
					throw new ApiError(502, "invalid_reply");
				setConfirmingDelete(null);
				setDeleteRetry(null);
				setDeleteFailure(null);
				cache.removeQueries({
					queryKey: [session.query_scope, "project", item.id],
				});
				void clearCreationsForTitle(
					store,
					recovery.data ?? [session.query_scope],
					item.title,
					projects
						.filter((candidate) => candidate.id !== item.id)
						.map((candidate) => candidate.title),
				).catch(() => undefined);
				void cache.invalidateQueries({
					queryKey: [session.query_scope, "projects"],
				});
			} catch (error) {
				if (!(error instanceof ApiError)) {
					setDeleteFailure({ id: item.id, kind: "failed" });
					return;
				}
				if (
					error.status === 401 ||
					error.status === 403 ||
					error.code === "session_changed"
				) {
					recheck();
					return;
				}
				if (error.status === 404 && error.code === "not_found") {
					// Another session already removed it; the list is the truth.
					setConfirmingDelete(null);
					setDeleteRetry(null);
					setDeleteFailure(null);
					void cache.invalidateQueries({
						queryKey: [session.query_scope, "projects"],
					});
					return;
				}
				if (error.status === 409) {
					// The single conflict code covers a changed revision and a
					// handoff refusal; the current row discriminates them. Neither
					// attempt mutated anything, so the next one is a new command
					// carrying the revision the refreshed list now shows.
					setDeleteRetry(null);
					try {
						const current = readProject(
							await client.query(
								"projects/read",
								{
									schema_version: 1,
									project_id: item.id,
									revision: null,
								},
								session.query_scope,
							),
						);
						setDeleteFailure({
							id: item.id,
							kind: current.revision === item.revision ? "handoff" : "changed",
						});
					} catch {
						setDeleteFailure({ id: item.id, kind: "failed" });
					}
					void cache.invalidateQueries({
						queryKey: [session.query_scope, "projects"],
					});
					return;
				}
				setDeleteFailure({ id: item.id, kind: "failed" });
			} finally {
				setDeleteBusy(false);
			}
		},
		[
			cache,
			client,
			deleteBusy,
			deleteRetry,
			projects,
			recheck,
			recovery.data,
			session,
			store,
		],
	);
	if (selected)
		return !session.claim_pending && project.data ? (
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
				{session.claim_pending ? (
					<Notice>
						<p role="status">
							{__(
								"Projects from the guest session are still being linked to your account.",
								"linker-tools",
							)}
						</p>
						<button className="lp-button" onClick={recheck}>
							{__("Check session", "linker-tools")}
						</button>
					</Notice>
				) : project.isError ? (
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
					{savedSource !== null ? (
						<SavedSolutionStart
							solutionId={savedSource}
							dismiss={() => {
								const url = new URL(location.href);
								url.searchParams.delete("saved_solution");
								replacePlannerLocation(url);
								setSavedSource(null);
							}}
							locale={config.locale}
							session={session}
							client={client}
							store={store}
							created={created}
							recheck={recheck}
							recoveryScopes={recovery.data}
							recoveryChecking={recovery.isFetching}
							recoveryDiscoveryFailed={recovery.isError}
						/>
					) : briefSource !== null ? (
						<ProjectBriefStart
							briefId={briefSource}
							entryHints={entryHints}
							dismiss={() => {
								const url = new URL(location.href);
								url.searchParams.delete("brief");
								replacePlannerLocation(url);
								setBriefSource(null);
							}}
							locale={config.locale}
							session={session}
							client={client}
							store={store}
							created={created}
							recheck={recheck}
							recoveryScopes={recovery.data}
							recoveryChecking={recovery.isFetching}
							recoveryDiscoveryFailed={recovery.isError}
						/>
					) : (
						<NewProject
							entryHints={entryHints}
							locale={config.locale}
							session={session}
							client={client}
							store={store}
							created={created}
							recheck={recheck}
							recoveryScopes={recovery.data}
							recoveryChecking={recovery.isFetching}
							recoveryDiscoveryFailed={recovery.isError}
						/>
					)}
				</header>
				{recovery.isError && (
					<Notice error>
						<p>
							{__(
								"Unconfirmed project creations and CSV imports from earlier sessions could not be checked. Any recovery data already stored in this browser remains unchanged.",
								"linker-tools",
							)}
						</p>
						<button className="lp-text-button" onClick={retryRecovery}>
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
							<div className="lp-project-entry" key={item.id}>
								<div className="lp-project-entry-row">
									<button
										className="lp-project-row"
										onClick={() => select(item.id)}
									>
										<span className="lp-project-row-icon">
											<Icon name="folder" />
										</span>
										<span>
											<strong>{item.title}</strong>
											<small>
												{sprintf(
													__("Revision %d", "linker-tools"),
													item.revision,
												)}{" "}
												<span aria-hidden="true">·</span>{" "}
												{new Intl.DateTimeFormat(config.locale, {
													dateStyle: "medium",
												}).format(new Date(item.updated_at * 1000))}
											</small>
										</span>
										<Icon name="arrow" />
									</button>
									<button
										className="lp-icon-button lp-project-delete"
										aria-label={sprintf(
											__("Delete project %s", "linker-tools"),
											item.title,
										)}
										disabled={deleteBusy}
										onClick={() => {
											setConfirmingDelete(item.id);
											setDeleteRetry(null);
											setDeleteFailure(null);
										}}
									>
										<Icon name="trash" />
									</button>
								</div>
								{confirmingDelete === item.id && (
									<div
										className="lp-delete-confirm"
										role="group"
										aria-label={__("Delete this project", "linker-tools")}
									>
										<p>
											{sprintf(
												__(
													'Delete the project "%s" at revision %d?',
													"linker-tools",
												),
												item.title,
												item.revision,
											)}
										</p>
										<p>
											{__(
												"All of its revisions, runs and stored inputs are removed from the workspace. A project handed to the Linker team as an inquiry cannot be deleted.",
												"linker-tools",
											)}
										</p>
										<div className="lp-inline-actions">
											<button
												className="lp-button lp-button-danger"
												disabled={deleteBusy}
												onClick={() => {
													void remove(item);
												}}
											>
												{deleteBusy
													? __("Deleting…", "linker-tools")
													: deleteFailure?.id === item.id
														? __("Try deleting again", "linker-tools")
														: __("Delete project", "linker-tools")}
											</button>
											<button
												className="lp-text-button"
												disabled={deleteBusy}
												onClick={() => {
													setConfirmingDelete(null);
													setDeleteRetry(null);
													setDeleteFailure(null);
												}}
											>
												{__("Cancel", "linker-tools")}
											</button>
										</div>
										{deleteFailure?.id === item.id && (
											<Notice error>
												<p>
													{deleteFailure.kind === "handoff"
														? __(
																"This project was handed to the Linker team as an inquiry and cannot be deleted.",
																"linker-tools",
															)
														: deleteFailure.kind === "changed"
															? __(
																	"This project changed before it could be deleted. The list now shows the current revision; deleting uses that revision the next time.",
																	"linker-tools",
																)
															: __(
																	"The project could not be deleted. Nothing was removed; you can try again.",
																	"linker-tools",
																)}
												</p>
											</Notice>
										)}
									</div>
								)}
							</div>
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
