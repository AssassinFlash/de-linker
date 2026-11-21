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
import {
	MAX_PROJECT_TITLE_LENGTH,
	projectTitleSearch,
	readProjectPage,
} from "../data/projectIndex.ts";
import { useSiteIntegration } from "../data/useSiteIntegration.ts";
import {
	guidedInquiryRetry,
	pendingInquiryRevision,
} from "../data/inquiryRecovery.ts";
import { clearCreationsForTitle } from "../data/recoveryIntents.ts";
import { recoveryScopes } from "../data/recoveryScopes.ts";
import { __, sprintf } from "../i18n.ts";
import { Icon } from "./Icon.tsx";
import { needsPhaseConfirmation } from "./configurator/HomepageDemand.tsx";
import { NewProject } from "./NewProject.tsx";
import { ProjectBriefStart } from "./ProjectBriefStart.tsx";
import { SavedSolutionStart } from "./SavedSolutionStart.tsx";
import { projectBriefId } from "../domain/projectBrief.ts";
import { savedSolutionId } from "../domain/savedSolution.ts";
const Configurator = lazy(() => import("./configurator/Configurator.tsx"));
import { PreliminaryProject } from "./configurator/PreliminaryProject.tsx";
import {
	InquiryStages,
	ProjectHeading,
} from "./configurator/ProjectHeading.tsx";
import { Notice } from "./Notice.tsx";
import { ENTRY_QUERY_KEYS, readEntryHints } from "../domain/entryHints.ts";
import { readObject, wire } from "../data/readProtocol.ts";
import {
	PLANNER_NAVIGATION,
	replacePlannerLocation,
} from "../data/plannerLocation.ts";

function currentProject(): string | null {
	const value = new URL(location.href).searchParams.get("project");
	return value && /^[a-f0-9]{32}$/.test(value) ? value : null;
}
function preliminaryRoute(route: string): boolean {
	return (
		route === "sc-preliminary-options" || route === "sc-preliminary-review"
	);
}
function currentGuidedRetryRevision(): number | null {
	return guidedInquiryRetry(new URL(location.href))?.revision ?? null;
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
	const projectIndex =
		new URL(location.href).searchParams.get("projects") === "1";
	const [titleQuery, setTitleQuery] = useState(() =>
		projectIndex
			? projectTitleSearch(
					new URL(location.href).searchParams.get("project_search"),
				)
			: "",
	);
	const [newProjectOpen, setNewProjectOpen] = useState(false);
	const [route, setRoute] = useState(
		() =>
			location.hash.slice(1) ||
			(!currentProject() &&
			new URL(location.href).searchParams.get("compare") === "preliminary"
				? "sc-preliminary-options"
				: ""),
	);
	const [guidedRetryRevision, setGuidedRetryRevision] = useState(
		currentGuidedRetryRevision,
	);
	useEffect(() => {
		const update = () => setGuidedRetryRevision(currentGuidedRetryRevision());
		window.addEventListener(PLANNER_NAVIGATION, update);
		window.addEventListener("popstate", update);
		return () => {
			window.removeEventListener(PLANNER_NAVIGATION, update);
			window.removeEventListener("popstate", update);
		};
	}, []);
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
	useEffect(() => {
		const restore = () => {
			const destination = location.hash.slice(1);
			if (!preliminaryRoute(route) && !preliminaryRoute(destination)) return;
			const id = currentProject();
			if (
				id &&
				!preliminaryRoute(route) &&
				preliminaryRoute(destination) &&
				pendingInquiryRevision(session.query_scope, id) === null
			)
				void cache.resetQueries({
					queryKey: [session.query_scope, "project", id, session.claim_pending],
					exact: true,
				});
			setRoute(destination);
			setSelected(id);
			setEntryHints(readEntryHints(new URL(location.href).searchParams));
		};
		window.addEventListener("popstate", restore);
		return () => window.removeEventListener("popstate", restore);
	}, [cache, route, session.claim_pending, session.query_scope]);
	const select = useCallback(
		(id: string | null, destination = "", guided = false) => {
			if (!client.isCurrentScope(session.query_scope)) return;
			const url = new URL(location.href);
			const from = url.hash.slice(1);
			if (guided) url.searchParams.set("guided", "inquiry");
			else if (
				id !== url.searchParams.get("project") ||
				(preliminaryRoute(from) && !preliminaryRoute(destination))
			)
				url.searchParams.delete("guided");
			if (
				id &&
				from === "sc-preliminary-review" &&
				destination === "sc-preliminary-options" &&
				window.history.state?.preliminaryProject === id
			) {
				window.history.back();
				return;
			}
			if (id) url.searchParams.set("project", id);
			else url.searchParams.delete("project");
			url.searchParams.delete("run");
			url.searchParams.delete("retry_revision");
			url.searchParams.delete("linker_inquiry_retry");
			url.searchParams.delete("compare");
			url.searchParams.delete("energy_view");
			url.searchParams.delete("brief");
			for (const key of ENTRY_QUERY_KEYS) url.searchParams.delete(key);
			url.hash = destination;
			setRoute(destination);
			if (
				id &&
				from === "sc-preliminary-options" &&
				destination === "sc-preliminary-review"
			) {
				// The comparison stays in this project's history after creation.
				// Back can change the choice without losing a filled inquiry.
				const comparison = new URL(url);
				comparison.hash = "sc-preliminary-options";
				window.history.replaceState(null, "", comparison);
				window.history.pushState({ preliminaryProject: id }, "", url);
				window.dispatchEvent(new Event(PLANNER_NAVIGATION));
			} else if (
				id &&
				from === "sc-preliminary-review" &&
				destination === "sc-project"
			) {
				window.history.pushState(null, "", url);
				window.dispatchEvent(new Event(PLANNER_NAVIGATION));
			} else replacePlannerLocation(url);
			setEntryHints(null);
			setNewProjectOpen(false);
			setSavedSource(null);
			setBriefSource(null);
			setSelected(id);
		},
		[client, session.query_scope],
	);
	const pageSize = Math.min(30, session.runtime.limits.max_page_size); // UI page policy, not total project capacity.
	const indexKey = [
		session.query_scope,
		"projects",
		session.claim_pending,
		titleQuery,
	];
	const index = useInfiniteQuery({
		queryKey: indexKey,
		initialPageParam: null as JsonObject | null,
		queryFn: async ({ pageParam, signal }) =>
			readProjectPage(
				await client.query(
					"projects/list",
					{
						schema_version: 1,
						page_size: pageSize,
						after: pageParam,
						...(titleQuery && { title_query: titleQuery }),
					},
					session.query_scope,
					signal,
				),
				pageSize,
			),
		getNextPageParam: (page) => page.next ?? undefined,
		enabled: selected === null,
	});
	const inquiryRevision =
		guidedRetryRevision ??
		(selected &&
		(preliminaryRoute(route) ||
			(route === "sc-review" &&
				new URL(location.href).searchParams.get("guided") === "inquiry"))
			? pendingInquiryRevision(session.query_scope, selected)
			: null);
	const project = useQuery({
		queryKey: [
			session.query_scope,
			"project",
			selected,
			session.claim_pending,
			...(inquiryRevision === null ? [] : [inquiryRevision]),
		],
		queryFn: async ({ signal }) => {
			const authorized = readProject(
				await client.query(
					"projects/read",
					{
						schema_version: 1,
						project_id: selected,
						revision: inquiryRevision,
					},
					session.query_scope,
					signal,
				),
			);
			if (
				inquiryRevision !== null &&
				(authorized.id !== selected || authorized.revision !== inquiryRevision)
			)
				throw new Error("inquiry_revision_unavailable");
			return authorized;
		},
		enabled: selected !== null && !session.claim_pending,
		staleTime: Infinity,
	});
	const startPreliminary = Boolean(
		selected &&
		project.data &&
		route === "sc-system" &&
		new URL(location.href).searchParams.get("guided") === "inquiry" &&
		needsPhaseConfirmation(project.data.inputs),
	);
	useEffect(() => {
		if (startPreliminary) select(selected, "sc-preliminary-options");
	}, [startPreliminary, selected, select]);
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
	const creatingProject = useRef<string | null>(null);
	const [creationPending, setCreationPending] = useState(false);
	function beginCreation(entryKey: string) {
		if (creatingProject.current) return null;
		creatingProject.current = entryKey;
		setCreationPending(true);
		return () => {
			creatingProject.current = null;
			setCreationPending(false);
		};
	}
	function created(
		project: Project,
		destination?: CreationDestination | "energy",
		openResult = true,
	) {
		if (!client.isCurrentScope(session.query_scope)) return false;
		cache.setQueryData(
			[session.query_scope, "project", project.id, session.claim_pending],
			project,
		);
		void cache.invalidateQueries({
			queryKey: [session.query_scope, "projects"],
		});
		if (openResult)
			select(
				project.id,
				destination === "guided-comparison"
					? "sc-system"
					: destination === "preliminary-review"
						? "sc-preliminary-review"
						: destination === "energy"
							? "sc-energy"
							: destination === "equipment"
								? "sc-system"
								: destination === "roof"
									? "sc-roof"
									: destination === "design"
										? "sc-solar"
										: "sc-project",
				destination === "guided-comparison",
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
	if (
		selected &&
		!session.claim_pending &&
		project.data &&
		(preliminaryRoute(route) || startPreliminary)
	)
		return (
			<PreliminaryProject
				key={session.query_scope + ":" + selected}
				project={project.data}
				session={session}
				client={client}
				store={store}
				locale={config.locale}
				guided={new URL(location.href).searchParams.get("guided") === "inquiry"}
				comparing={startPreliminary || route === "sc-preliminary-options"}
				recoveringRevision={inquiryRevision !== null}
				navigate={(destination, confirmed) => {
					if (confirmed)
						cache.setQueryData<Project>(
							[session.query_scope, "project", selected, session.claim_pending],
							(current) =>
								current && current.revision >= confirmed.revision
									? current
									: confirmed,
						);
					if (route !== destination) select(selected, destination);
				}}
				recheck={recheck}
			/>
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
					client={client}
					store={store}
					config={config}
					session={session}
					recheck={recheck}
					recoveryScopes={recovery.data}
					recoveryChecking={recovery.isFetching}
					recoveryFailed={recovery.isError}
					comparePreliminary={(saved) => {
						cache.setQueryData(
							[session.query_scope, "project", selected, session.claim_pending],
							saved,
						);
						select(saved.id, "sc-preliminary-options");
					}}
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

	const recoveryNotice = recovery.isError && (
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
	);
	const canCompareDirections =
		!projectIndex &&
		savedSource === null &&
		briefSource === null &&
		!entryHints?.roof &&
		!entryHints?.equipment;

	const bareComparison = canCompareDirections && !route;
	const firstVisitComparison =
		canCompareDirections && route === "sc-preliminary-options";
	const directEntry =
		!projectIndex &&
		savedSource === null &&
		briefSource === null &&
		!entryHints?.roof &&
		!firstVisitComparison &&
		(bareComparison ||
			newProjectOpen ||
			route === "sc-project" ||
			Boolean(entryHints) ||
			(index.isSuccess && !projects.length));
	const entryKey =
		canCompareDirections && (firstVisitComparison || route === "sc-project")
			? JSON.stringify(entryHints)
			: "workspace";
	function showCreationPage(anchor: "sc-project" | "sc-preliminary-options") {
		const url = new URL(location.href);
		url.hash = anchor;
		window.history.pushState(null, "", url);
		setRoute(anchor);
		window.dispatchEvent(new Event(PLANNER_NAVIGATION));
	}

	return (
		<div
			className={
				directEntry || firstVisitComparison
					? "sc-configurator sc-intake"
					: "sc-configurator"
			}
		>
			{firstVisitComparison ? (
				<>
					<ProjectHeading
						anchor="sc-preliminary-options"
						actions={
							<button
								className="sc-button"
								type="button"
								onClick={() => select(null)}
							>
								{__("Projects", "linker-tools")}
							</button>
						}
					/>
					<InquiryStages />
				</>
			) : (
				<header
					className={directEntry ? "sc-entry-toolbar" : "sc-project-heading"}
				>
					<div>
						<p>{__("Solution Configurator", "linker-tools")}</p>
						{!directEntry && (
							<h1>
								{entryHints?.roof
									? __("Start with your roof", "linker-tools")
									: __("Your projects", "linker-tools")}
							</h1>
						)}
					</div>
					<div className="sc-actions">
						{!entryHints && !projectIndex && !savedSource && !briefSource && (
							<a className="sc-button" href="?step=roof">
								{__("Start with your roof", "linker-tools")}
							</a>
						)}
						<button className="sc-button" type="button" data-linker-genie-open>
							{__("Ask Genie", "linker-tools")}
						</button>
					</div>
				</header>
			)}
			<div className={firstVisitComparison ? undefined : "sc-main"}>
				<div>
					{projectIndex ? null : savedSource !== null ? (
						<SavedSolutionStart
							directComparison
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
							directComparison
							briefId={briefSource}
							config={config}
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
							key={creatingProject.current ?? entryKey}
							compareOnLoad={firstVisitComparison}
							directComparison={
								bareComparison ||
								entryHints?.equipment === true ||
								route === "sc-project"
							}
							workspaceHeading={directEntry}
							opened={() => setNewProjectOpen(true)}
							enterDetails={() => showCreationPage("sc-project")}

							creationPending={creationPending}
							beginCreation={() => beginCreation(entryKey)}
							config={config}
							openOnLoad={
								bareComparison ||
								route === "sc-project" ||
								(index.isSuccess && !projects.length)
							}
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
				{recoveryNotice}
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
					className="sc-card sc-saved-projects"
					hidden={firstVisitComparison || Boolean(entryHints?.roof)}
					aria-labelledby="lp-projects-heading"
				>
					<div className="sc-section-head">
						<h2 id="lp-projects-heading">
							{__("Saved projects", "linker-tools")}
						</h2>
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
					{projectIndex && (
						<form
							className="sc-actions sc-project-search"
							role="search"
							onSubmit={(event) => {
								event.preventDefault();
								const name = new FormData(event.currentTarget).get(
									"project_search",
								);
								const query = projectTitleSearch(
									typeof name === "string" ? name : null,
								);
								const url = new URL(location.href);
								if (query) url.searchParams.set("project_search", query);
								else url.searchParams.delete("project_search");
								replacePlannerLocation(url);
								setTitleQuery(query);
							}}
						>
							<label className="sc-field">
								{__("Project name", "linker-tools")}
								<input
									name="project_search"
									type="search"
									maxLength={MAX_PROJECT_TITLE_LENGTH}
									defaultValue={titleQuery}
								/>
							</label>
							<button className="sc-button" type="submit">
								{__("Search projects", "linker-tools")}
							</button>
						</form>
					)}
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
						<p className="sc-muted" role="status">
							{titleQuery
								? __("No matching projects.", "linker-tools")
								: __("No saved projects yet.", "linker-tools")}
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
													cache.isFetching({
														queryKey: indexKey,
														exact: true,
													})
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
				<footer hidden={firstVisitComparison}>
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
