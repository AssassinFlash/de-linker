import {
	lazy,
	Suspense,
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";
import {
	useInfiniteQuery,
	useQuery,
	useQueryClient,
} from "@tanstack/react-query";
import type { Configuration } from "../data/config.ts";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { CreationDestination, DraftStore } from "../data/DraftStore.ts";
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
const Configurator = lazy(() => import("./configurator/Configurator.tsx"));
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
	const [showProjects, setShowProjects] = useState(false);
	const [comparison, setComparison] = useState<{
		destination: "compare" | "options" | "review";
		projectId: string;
		inputs: JsonObject;
	} | null>(null);
	const consumeComparison = useCallback(() => setComparison(null), []);
	const [provisionedId, setProvisionedId] = useState<string | null>(null);
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
			setComparison(null);
			setProvisionedId(null);
			setSelected(id);
			setShowProjects(id === null);
		},
		[client, session.query_scope],
	);
	const pageSize = Math.min(30, session.runtime.limits.max_page_size); // UI page policy, not total project capacity.
	const indexKey = [session.query_scope, "projects", session.claim_pending];
	const index = useInfiniteQuery({
		queryKey: indexKey,
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
	useSiteIntegration(selected ?? provisionedId);
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
	function created(
		project: Project,
		destination?: CreationDestination,
		comparisonInputs?: JsonObject,
	) {
		if (!client.isCurrentScope(session.query_scope)) return false;
		cache.setQueryData(
			[session.query_scope, "project", project.id, session.claim_pending],
			project,
		);
		void cache.invalidateQueries({
			queryKey: [session.query_scope, "projects"],
		});
		if (destination === "edit") {
			const url = new URL(location.href);
			url.searchParams.set("project", project.id);
			replacePlannerLocation(url);
			setProvisionedId(project.id);
			return true;
		}
		select(
			project.id,
			destination === "energy"
				? "sc-energy"
				: destination === "equipment"
					? "sc-system"
					: destination === "design"
						? "sc-solar"
						: destination === "options" && !comparisonInputs
							? "sc-preliminary-options"
							: destination === "review" && !comparisonInputs
								? "sc-preliminary-review"
								: "sc-project",
		);
		if (
			destination === "compare" ||
			((destination === "review" || destination === "options") &&
				comparisonInputs)
		)
			setComparison({
				destination,
				projectId: project.id,
				inputs: comparisonInputs ?? project.inputs,
			});
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
					setDeleteRetry(null);
					if (error.code === "inquiry_linked") {
						setDeleteFailure({ id: item.id, kind: "handoff" });
						return;
					}
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
							kind: current.revision === item.revision ? "failed" : "changed",
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
			<Suspense
				fallback={
					<p className="lp-session-state" role="status">
						{__("Opening the project…", "linker-tools")}
					</p>
				}
			>
				<Configurator
					key={session.query_scope + ":" + selected}
					project={project.data}
					{...(comparison?.projectId === selected && {
						entryComparison: {
							destination: comparison.destination,
							inputs: comparison.inputs,
							consume: consumeComparison,
						},
					})}
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
			</Suspense>
		) : (
			<div className="sc-configurator">
				<button className="sc-button" onClick={() => select(null)}>
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
						<button className="sc-button" onClick={recheck}>
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
						<button className="sc-button" onClick={recheck}>
							{__("Check session", "linker-tools")}
						</button>
					</Notice>
				) : (
					<p role="status">{__("Opening project…", "linker-tools")}</p>
				)}
			</div>
		);

	return (
		<div className="sc-configurator">
			<header className="sc-project-toolbar">
				<span>{__("Solution Configurator", "linker-tools")}</span>
				<div className="sc-actions">
					<button
						className="sc-button"
						type="button"
						aria-controls="sc-saved-projects"
						aria-expanded={showProjects}
						onClick={() => setShowProjects(!showProjects)}
					>
						{showProjects
							? __("Back to project", "linker-tools")
							: __("Saved projects", "linker-tools")}
					</button>
					<button className="sc-button" type="button" data-linker-genie-open>
						{__("Ask Genie", "linker-tools")}
					</button>
				</div>
			</header>
			<div>
				<div hidden={showProjects}>
					{savedSource !== null ? (
						<SavedSolutionStart
							solutionId={savedSource}
							config={config}
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
							config={config}
							entryHints={entryHints}
							dismiss={() => {
								const url = new URL(location.href);
								url.searchParams.delete("brief");
								for (const key of ENTRY_QUERY_KEYS)
									url.searchParams.delete(key);
								setEntryHints(null);
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
							config={config}
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
				</div>
				{recovery.isError && (
					<Notice error>
						<p>
							{__(
								"Unconfirmed project creations and CSV imports from earlier sessions could not be checked. Any recovery data already stored in this browser remains unchanged.",
								"linker-tools",
							)}
						</p>
						<button className="sc-button" onClick={retryRecovery}>
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
						<button className="sc-button" onClick={recheck}>
							{__("Check session", "linker-tools")}
						</button>
					</Notice>
				)}
				<section
					id="sc-saved-projects"
					hidden={!showProjects}
					className="sc-card"
					aria-labelledby="lp-projects-heading"
				>
					<div className="sc-section-head">
						<h1 id="lp-projects-heading">
							{__("Your projects", "linker-tools")}
						</h1>
						<button
							className="sc-button"
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
							<button className="sc-button" onClick={recheck}>
								{__("Try again", "linker-tools")}
							</button>
						</Notice>
					)}
					{!index.isPending && !index.isError && !projects.length && (
						<p className="sc-muted">
							{__("No saved projects yet.", "linker-tools")}
						</p>
					)}
					<div role="list">
						{projects.map((item) => (
							<div role="listitem" key={item.id}>
								<div className="sc-section-head">
									<div>
										<h3 id={`sc-project-${item.id}`}>{item.title}</h3>
										<p className="sc-muted">
											{__("Last updated", "linker-tools")}{" "}
											<time
												dateTime={new Date(
													item.updated_at * 1000,
												).toISOString()}
											>
												{new Intl.DateTimeFormat(config.locale, {
													dateStyle: "medium",
												}).format(new Date(item.updated_at * 1000))}
											</time>
										</p>
									</div>
									<div className="sc-actions">
										<button
											className="sc-button"
											type="button"
											onClick={() => select(item.id)}
										>
											{__("Open project", "linker-tools")}
										</button>
										<button
											className="sc-button"
											type="button"
											aria-label={sprintf(
												__("Delete project %s", "linker-tools"),
												item.title,
											)}
											disabled={deleteBusy || index.isRefetching}
											onClick={() => {
												if (
													cache.isFetching({ queryKey: indexKey, exact: true })
												)
													return;
												setConfirmingDelete(item.id);
												setDeleteRetry(null);
												setDeleteFailure(null);
											}}
										>
											<Icon name="trash" />
										</button>
									</div>
								</div>
								{confirmingDelete === item.id && (
									<div
										className="sc-card"
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
										<div className="sc-actions">
											<button
												className="sc-button lp-button-danger"
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
												className="sc-button"
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
							className="sc-button"
							disabled={index.isFetchingNextPage}
							onClick={() => {
								void index.fetchNextPage();
							}}
						>
							{__("More projects", "linker-tools")}
						</button>
					)}
				</section>
				<footer hidden={!showProjects}>
					<p className="sc-muted">
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
