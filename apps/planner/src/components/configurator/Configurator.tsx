import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Configuration } from "../../data/config.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { DraftStore } from "../../data/DraftStore.ts";
import {
	ApiError,
	type JsonObject,
	type Project,
	type Session,
} from "../../data/protocol.ts";
import {
	configuratorReportSources,
	hasReportWiring,
	sharedDcReportRun,
} from "../../data/configuratorReportSources.ts";
import { useGenieContext } from "../../data/useGenieContext.ts";
import { useProjectDraft } from "../../data/useProjectDraft.ts";
import { usePlanningOperations } from "../../data/usePlanningOperations.ts";
import {
	useInfiniteQuery,
	useQuery,
	useQueryClient,
} from "@tanstack/react-query";
import {
	readRunInputs,
	readRun,
	readRunPage,
	runPending,
	runTask,
	waitForRunPoll,
	RUN_OPERATIONS,
	type PlanningRun,
	type RunPage,
	type TaskKind,
} from "../../data/planningProtocol.ts";
import { REPORT_TASK, type ReportOptions } from "../../data/planningReport.ts";
import { WEATHER_TASK, PV_TASK } from "../../data/readPreparationResult.ts";
import { DC_PLANT_ENERGY_TASK } from "../../domain/plantEnergy.ts";
import { readObject } from "../../data/readProtocol.ts";
import { readEquipmentProducts } from "../../data/equipmentProducts.ts";
import {
	SEARCH_TASK,
	isPlantCandidate,
	type EquipmentCandidate,
} from "../../data/equipmentSearch.ts";
import {
	editDraft,
	isDirty,
	undoDraft,
	redoDraft,
	projectInputContract,
	sameJson,
} from "../../domain/draft.ts";
import {
	authoredCalculationInputs,
	authoredDiscoveryInputs,
	needsComparisonModels,
	restoreComparisonModels,
	sameEquipmentDemand,
} from "../../domain/currentCalculation.ts";
import { emptyBrief, readBrief } from "../../domain/brief.ts";
import {
	changeEquipment,
	checkRetainedEquipment,
	comparisonModels,
	equipmentDraft,
} from "../../domain/equipment.ts";
import { hasPlant, readPlantDraft } from "../../domain/equipmentPlant.ts";
import { invalidateEnergyReplay } from "../../domain/energyScenario.ts";
import { dropGeometricRoofAc } from "../../domain/profiles.ts";
import { readPvPlantStringPlan } from "../../domain/pvPlantStrings.ts";
import { adoptPlantCandidate } from "../../domain/plantSearch.ts";
import { replacePlannerLocation } from "../../data/plannerLocation.ts";
import { ProjectEquipment } from "./ProjectEquipment.tsx";
import { hasStorageToExclude, ProjectDetails } from "./ProjectDetails.tsx";
import { EnergyDemand } from "./EnergyDemand.tsx";
import { SharedDcEnergy, type SharedDcTask } from "./SharedDcEnergy.tsx";
import {
	CandidateMaterials,
	SystemOptions,
	useCandidateAssessment,
	type SystemComparison,
} from "./SystemOptions.tsx";
import { SolarInstallation } from "./SolarInstallation.tsx";
import { ReviewProposal } from "./ReviewProposal.tsx";
import { ProjectHeading } from "./ProjectHeading.tsx";
import { PlantPvStringSetup } from "../equipment/PlantPvStringSetup.tsx";
import {
	PvStringSetup,
	type StringEditBlock,
} from "../equipment/PvStringSetup.tsx";
import { energyErrorText } from "../energy/EnergyError.tsx";
import { referenceDraft, KNOWN_PV_MODEL } from "../../domain/pvgisReference.ts";
import { moduleSummary } from "../../domain/panelPoses.ts";
import { activePvGeometry, checkPvWeather } from "../../domain/solarSetup.ts";
import { __, sprintf } from "../../i18n.ts";

type Step = "project" | "solar" | "energy" | "system" | "review";
const steps: Step[] = ["project", "solar", "energy", "system", "review"];
const mapPropertyLinks = new Set([
	"#lp-map-roof-properties",
	"#lp-map-ring-properties",
	"#lp-map-feature-properties",
]);
function initialStep(): Step {
	const hash = location.hash.slice(1);
	if (
		hash === "sc-solar" ||
		hash === "lp-design" ||
		mapPropertyLinks.has(location.hash)
	)
		return "solar";
	if (hash === "sc-energy" || hash === "lp-load") return "energy";
	if (hash === "sc-system" || hash === "lp-equipment") return "system";
	if (hash === "sc-review" || hash === "lp-calculations") return "review";
	return "project";
}

function useProjectResult(
	client: PlannerClient,
	session: Session,
	projectId: string,
	task: TaskKind,
	id: string | null,
) {
	return useQuery({
		queryKey: [session.query_scope, "configurator-result", projectId, task, id],
		enabled:
			id !== null &&
			!session.claim_pending &&
			client.isCurrentScope(session.query_scope),
		queryFn: async ({ signal }) =>
			readRun(
				await client.query(
					"runs/read",
					{ schema_version: 1, run_id: id },
					session.query_scope,
					signal,
				),
				projectId,
				id!,
				task,
			),
		refetchIntervalInBackground: true,
		refetchInterval: (query) =>
			query.state.data && runPending(query.state.data.state) ? 1000 : false,
	});
}

export default function Configurator({
	project,
	session,
	client,
	store,
	config,
	recheck,
	close,
	recoveryScopes,
	recoveryChecking = false,
	recoveryFailed = false,
}: {
	project: Project;
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	config: Configuration;
	recheck: () => void;
	close: () => boolean;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	recoveryFailed?: boolean;
}) {
	const controller = useProjectDraft(project, session, client, store, recheck);
	const { draft, update, acknowledgeProject } = controller;
	const [step, setStep] = useState<Step>(initialStep);
	const main = useRef<HTMLElement>(null);
	const [energyValid, setEnergyValid] = useState(true);
	const [energyOpened, setEnergyOpened] = useState(() =>
		["energy", "solar"].includes(initialStep()),
	);
	const [roofEditing, setRoofEditing] = useState(false);
	const [importOpen, setImportOpen] = useState(false);
	const [navigationRefused, setNavigationRefused] = useState(false);
	const [sharedDcValid, setSharedDcValid] = useState(true);
	const profileGuard = useRef<() => boolean>(() => true);
	const registerProfileGuard = useCallback((guard: () => boolean) => {
		profileGuard.current = guard;
	}, []);
	const [submittedDc, setSubmittedDc] = useState<{
		id: string;
		task: SharedDcTask;
	} | null>(null);
	const [wiringValidity, setWiringValidity] = useState<
		Record<string, "ready" | "invalid" | NonNullable<StringEditBlock>>
	>({});
	const wiringInputs = draft?.history.current;
	const wiringPlant =
		step === "solar" && wiringInputs && hasPlant(wiringInputs)
			? readPlantDraft(wiringInputs)
			: null;
	const wiringIds = wiringPlant?.units.map((unit) => unit.id).join(",") ?? "";
	const wiringCallbacks = useMemo(
		() =>
			Object.fromEntries(
				["", ...wiringIds.split(",").filter(Boolean)].map((id) => [
					id,
					(canLeave: boolean, editBlock: StringEditBlock) => {
						const status = canLeave ? "ready" : (editBlock ?? "invalid");
						setWiringValidity((state) =>
							state[id] === status ? state : { ...state, [id]: status },
						);
					},
				]),
			),
		[wiringIds],
	);
	const wiringStates = (wiringPlant?.units.map((unit) => unit.id) ?? [""]).map(
		(id) => wiringValidity[id],
	);
	const invalidInput =
		!energyValid || !sharedDcValid || wiringStates.includes("invalid");
	const missingModules = wiringStates.includes("selection");
	const navigationBlocked =
		invalidInput ||
		missingModules ||
		wiringStates.includes("pending") ||
		roofEditing ||
		importOpen;
	function mayLeave() {
		if (!client.isCurrentScope(session.query_scope) || !profileGuard.current())
			return false;
		if (!navigationBlocked) return true;
		setNavigationRefused(true);
		const target = main.current?.querySelector<HTMLElement>(
			invalidInput
				? '[aria-invalid="true"]:not(summary)'
				: missingModules
					? 'summary[aria-invalid="true"]'
					: '[aria-invalid="true"]',
		);
		for (
			let details = target?.parentElement?.closest("details");
			details;
			details = details.parentElement?.closest("details")
		)
			details.open = true;
		target?.focus();
		return false;
	}
	const lastStep = useRef(step);
	useEffect(() => {
		if (lastStep.current === step) return;
		lastStep.current = step;
		main.current?.focus({ preventScroll: true });
		main.current?.scrollIntoView?.({ block: "start" });
	}, [step]);
	const [error, setError] = useState<unknown>(null);
	const [selecting, setSelecting] = useState(false);
	const reportPreparation = useRef<AbortController | null>(null);
	const [preparingReport, setPreparingReport] = useState(false);
	const [submittedSearch, setSubmittedSearch] = useState<string | null>(null);
	const [comparison, setComparison] = useState<SystemComparison | null>(null);
	const [submittedReport, setSubmittedReport] = useState<string | null>(null);
	const [viewedReport, setViewedReport] = useState(() => {
		const params = new URL(location.href).searchParams;
		return params.get("project") === project.id ? params.get("run") : null;
	});
	const [genieReportId, setGenieReportId] = useState<string | null>(null);
	const cache = useQueryClient();
	const latest = useRef(draft);
	latest.current = draft;
	const lifetime = useRef(0);
	useEffect(() => {
		lifetime.current++;
		setPreparingReport(false);
		return () => {
			reportPreparation.current?.abort();
			reportPreparation.current = null;
			lifetime.current++;
		};
	}, [project.id, session.query_scope]);
	const operations = usePlanningOperations({
		projectId: project.id,
		session,
		client,
		recheck,
		recoveryScopes,
		recoveryChecking,
		acknowledgeProject,
	});
	const admitted =
		client.isCurrentScope(session.query_scope) && !session.claim_pending;
	async function readHistoryPage(cursor: RunPage["next"], signal: AbortSignal) {
		return readRunPage(
			await client.query(
				"projects/runs",
				{
					schema_version: 1,
					project_id: project.id,
					page_size: session.runtime.limits.max_page_size,
					before_created_at: cursor?.before_created_at ?? null,
					before_id: cursor?.before_id ?? null,
				},
				session.query_scope,
				signal,
			),
			project.id,
		);
	}
	const history = useQuery({
		queryKey: [session.query_scope, "configurator-history", project.id],
		enabled: admitted,
		queryFn: ({ signal }) => readHistoryPage(null, signal),
	});
	const firstCursor = history.data?.next ?? null;
	const olderHistory = useInfiniteQuery({
		queryKey: [
			session.query_scope,
			"configurator-older-history",
			project.id,
			firstCursor,
		],
		enabled: false,
		initialPageParam: firstCursor,
		queryFn: ({ signal, pageParam }) => readHistoryPage(pageParam, signal),
		getNextPageParam: (page) => page.next,
	});
	const latestRuns = history.data?.items;
	const choiceInput = draft?.history.current.equipment_candidate;
	const choice = choiceInput == null ? null : readObject(choiceInput);
	const selectedSearch =
		typeof choice?.run_id === "string" ? choice.run_id : null;
	const newest = (kind: TaskKind) =>
		latestRuns?.find((item) => item.task_kind === kind)?.id ?? null;
	const currentSearch = latestRuns?.find(
		(item) => item.task_kind === SEARCH_TASK && item.is_current,
	)?.id;
	const searchId =
		submittedSearch ?? currentSearch ?? selectedSearch ?? newest(SEARCH_TASK);
	const search = useProjectResult(
		client,
		session,
		project.id,
		SEARCH_TASK,
		searchId,
	);
	const systemRead = searchId ? search : history;
	const adoptedSearch = useProjectResult(
		client,
		session,
		project.id,
		SEARCH_TASK,
		selectedSearch,
	);
	const reportRuns = [
		...(latestRuns ?? []),
		...(olderHistory.data?.pages.flatMap((page) => page.items) ?? []),
	].filter((item) => item.task_kind === REPORT_TASK);
	const reportId = submittedReport ?? reportRuns?.[0]?.id ?? null;
	const report = useProjectResult(
		client,
		session,
		project.id,
		REPORT_TASK,
		reportId,
	);
	const earlierReports =
		reportRuns?.filter(
			(item) => item.state === "succeeded" && item.id !== reportId,
		) ?? [];
	const viewedReportId =
		viewedReport !== null && /^[a-f0-9]{32}$/.test(viewedReport)
			? viewedReport
			: null;
	const historicalRunQuery = useProjectResult(
		client,
		session,
		project.id,
		REPORT_TASK,
		step === "review" ? viewedReportId : null,
	);
	const viewedRun = admitted ? (historicalRunQuery.data ?? null) : null;
	function selectReport(id: string | null) {
		const url = new URL(location.href);
		if (!admitted || url.searchParams.get("project") !== project.id) return;
		setGenieReportId(null);
		setViewedReport(id);
		if (id === null) url.searchParams.delete("run");
		else url.searchParams.set("run", id);
		url.searchParams.delete("compare");
		url.searchParams.delete("energy_view");
		replacePlannerLocation(url);
	}
	const searchRun = search.data ?? null,
		reportRun = report.data ?? null;
	const genieRun =
		step === "review" && genieReportId !== null
			? [reportRun, viewedRun].find(
					(run) => run?.id === genieReportId && run.state === "succeeded",
				)
			: null;
	const openReport = viewedReport === null ? reportRun : viewedRun;
	useGenieContext(
		draft?.baseline ?? project,
		session,
		!draft || isDirty(draft) || Boolean(draft.pending || draft.conflict),
		{
			client,
			report: genieRun ?? null,
			openReport:
				step === "review" && openReport?.state === "succeeded"
					? openReport
					: null,
		},
	);
	const adoptedRun = adoptedSearch.data ?? null;
	const legacyModels = draft
		? needsComparisonModels(draft.history.current)
		: false;
	const comparisonSource = useQuery({
		queryKey: [
			session.query_scope,
			"configurator-comparison-models",
			project.id,
			selectedSearch,
		],
		enabled:
			legacyModels &&
			adoptedRun !== null &&
			client.isCurrentScope(session.query_scope),
		queryFn: async ({ signal }) =>
			readRunInputs(
				await client.query(
					"runs/inputs",
					{ schema_version: 1, project_id: project.id, run_id: adoptedRun!.id },
					session.query_scope,
					signal,
				),
				adoptedRun!,
			),
	});
	const comparisonInputs = legacyModels ? comparisonSource.data : undefined;
	const frozenSearch = adoptedRun?.result?.search
		? readObject(adoptedRun.result.search)
		: null;
	const selectedCandidate =
		choice && choice.run_id === adoptedRun?.id
			? (frozenSearch?.candidates as EquipmentCandidate[] | undefined)?.find(
					(item) =>
						item.id === choice.candidate_id &&
						item.assessment_sha256 === choice.assessment_sha256,
				)
			: undefined;
	const selectedDetail = useCandidateAssessment(
		client,
		session.query_scope,
		adoptedRun,
		selectedCandidate,
	);
	function accepted(run: PlanningRun) {
		const task = runTask(run);
		if (
			task !== SEARCH_TASK &&
			task !== REPORT_TASK &&
			task !== DC_PLANT_ENERGY_TASK &&
			task !== WEATHER_TASK &&
			task !== PV_TASK
		)
			return;
		cache.setQueryData(
			[session.query_scope, "configurator-result", project.id, task, run.id],
			run,
		);
		if (task === SEARCH_TASK) setSubmittedSearch(run.id);
		else if (task === REPORT_TASK) setSubmittedReport(run.id);
		else setSubmittedDc({ id: run.id, task });
		void history.refetch();
	}
	const modelsUnavailable = legacyModels && comparisonInputs === undefined;
	const blocked =
		!admitted ||
		recoveryChecking ||
		recoveryFailed ||
		controller.busy ||
		selecting ||
		preparingReport ||
		operations.busy ||
		operations.checking ||
		operations.storageFailed ||
		controller.recoveries.length > 0 ||
		Boolean(draft?.pending || draft?.conflict) ||
		operations.records.some((r) => r.resultId === null);
	const edit = useCallback(
		(operation: (inputs: JsonObject) => JsonObject): boolean => {
			if (
				!client.isCurrentScope(session.query_scope) ||
				!latest.current ||
				latest.current.pending ||
				latest.current.conflict
			)
				return false;
			let applied = false;
			const next = update((previous) => {
				const before = previous.history.current;
				const legacy = needsComparisonModels(before);
				const restored =
					comparisonInputs && legacy
						? restoreComparisonModels(before, comparisonInputs)
						: before;
				const after = operation(restored);
				const sameChoice = sameJson(
					after.equipment_candidate,
					before.equipment_candidate,
				);
				// The adopted run is the source of the original preferences. Do not
				// discard that reference before recovering them.
				if (
					legacy &&
					!comparisonInputs &&
					(!sameChoice || !sameEquipmentDemand(restored, after))
				)
					return previous;
				applied = true;
				if (
					after.equipment_candidate != null &&
					sameChoice &&
					!sameEquipmentDemand(restored, after)
				) {
					const { equipment_candidate: _stale, ...inputs } = after;
					return editDraft(previous, inputs);
				}
				return editDraft(previous, after);
			});
			latest.current = next;
			return next !== null && applied;
		},
		[client, comparisonInputs, session.query_scope, update],
	);
	const editWiring = useCallback(
		(operation: (inputs: JsonObject) => JsonObject) =>
			edit((inputs) =>
				invalidateEnergyReplay(dropGeometricRoofAc(operation(inputs))),
			),
		[edit],
	);
	function navigate(next: Step) {
		if (!mayLeave()) return;
		setGenieReportId(null);
		const url = new URL(location.href);
		url.hash = "sc-" + next;
		replacePlannerLocation(url);
		if (next === "energy") setEnergyOpened(true);
		setStep(next);
		setNavigationRefused(false);
	}
	async function startSharedDc(
		path: "runs/calculate" | "runs/weather" | "runs/pv",
	) {
		if (
			blocked ||
			modelsUnavailable ||
			!latest.current ||
			!profileGuard.current()
		)
			return;
		const instance = lifetime.current;
		setError(null);
		try {
			const current = latest.current;
			if (path === "runs/pv") checkPvWeather(current.baseline.inputs);
			const reply = await operations.start(path, {
				expected_revision: current.baseline.revision,
				...(path === "runs/calculate"
					? {
							input_contract: projectInputContract,
							inputs: authoredCalculationInputs(current.history.current),
						}
					: {}),
			});
			if (reply && "run" in reply && instance === lifetime.current && admitted)
				accepted(reply.run);
		} catch (cause) {
			if (
				instance === lifetime.current &&
				client.isCurrentScope(session.query_scope)
			)
				setError(cause);
		}
	}
	async function generateComparison(options: ReportOptions) {
		if (blocked || !latest.current || isDirty(latest.current)) return;
		const reply = await operations.start("runs/report", {
			expected_revision: latest.current.baseline.revision,
			options,
		});
		if (
			reply?.path === "runs/report" &&
			client.isCurrentScope(session.query_scope)
		) {
			accepted(reply.run);
			navigate("review");
		}
	}
	async function compare() {
		if (blocked || modelsUnavailable || !latest.current) return;
		setError(null);
		const instance = lifetime.current;
		const reply = await operations.start("runs/find-equipment", {
			expected_revision: latest.current.baseline.revision,
			input_contract: projectInputContract,
			inputs: authoredDiscoveryInputs(latest.current.history.current),
		});
		if (
			reply?.path === "runs/find-equipment" &&
			instance === lifetime.current &&
			client.isCurrentScope(session.query_scope)
		) {
			accepted(reply.run);
			navigate("system");
		}
	}

	async function select(candidate: EquipmentCandidate, run: PlanningRun) {
		if (
			blocked ||
			modelsUnavailable ||
			!latest.current ||
			run.project_id !== project.id
		)
			return;
		setSelecting(true);
		setError(null);
		const snapshot = latest.current.history.current,
			instance = lifetime.current;
		try {
			const [products, frozen] = await Promise.all([
				client
					.query("products/current", { schema_version: 1 }, session.query_scope)
					.then(readEquipmentProducts),
				client
					.query(
						"runs/inputs",
						{ schema_version: 1, project_id: project.id, run_id: run.id },
						session.query_scope,
					)
					.then((raw) => readRunInputs(raw, run)),
			]);
			if (
				instance !== lifetime.current ||
				!client.isCurrentScope(session.query_scope)
			)
				return;
			if (!products.prepared)
				throw new ApiError(409, "product_evidence_changed");
			const authoredSnapshot =
				comparisonInputs && needsComparisonModels(snapshot)
					? restoreComparisonModels(snapshot, comparisonInputs)
					: snapshot;
			if (!sameEquipmentDemand(authoredSnapshot, frozen))
				throw new ApiError(409, "equipment_selection_changed");
			const choice = {
				run_id: run.id,
				candidate_id: candidate.id,
				assessment_sha256: candidate.assessment_sha256,
			};
			let next: JsonObject;
			if (isPlantCandidate(candidate))
				next = adoptPlantCandidate(
					authoredSnapshot,
					candidate.plant,
					products.products,
					choice,
					frozen,
				);
			else {
				if (
					Object.entries(candidate.selection.product_revisions).some(
						([id, revision]) =>
							!products.products.some(
								(p) => String(p.id) === id && p.product_revision === revision,
							),
					)
				)
					throw new ApiError(409, "product_evidence_changed");
				checkRetainedEquipment(equipmentDraft(snapshot), candidate.selection);
				const { product_revisions: _revisions, ...selection } =
					candidate.selection;
				next = {
					...changeEquipment(snapshot, {
						...selection,
						comparison_models: comparisonModels(equipmentDraft(frozen)),
					}),
					equipment_selection: candidate.selection,
					equipment_candidate: choice,
				};
			}
			if (
				!latest.current ||
				!sameJson(latest.current.history.current, snapshot)
			)
				throw new ApiError(409, "equipment_selection_changed");
			if (!edit(() => next))
				throw new ApiError(409, "equipment_selection_changed");
			setSubmittedSearch(run.id);
		} catch (cause) {
			if (instance === lifetime.current) {
				setError(cause);
				throw cause;
			}
		} finally {
			if (instance === lifetime.current) setSelecting(false);
		}
	}
	async function generate(logo: string | null) {
		if (
			blocked ||
			modelsUnavailable ||
			reportPreparation.current ||
			!latest.current
		)
			return;
		setError(null);
		const request = new AbortController();
		reportPreparation.current = request;
		setPreparingReport(true);
		const current = () =>
			!request.signal.aborted && client.isCurrentScope(session.query_scope);
		try {
			let saved = await controller.save();
			if (!saved || !current()) return;
			const { options: sources, pendingWiringCheck } =
				await configuratorReportSources({
					project: saved,
					pageSize: session.runtime.limits.max_page_size,
					query: (path, body, signal) =>
						client.query(path, body, session.query_scope, signal),
					signal: request.signal,
				});
			if (!current()) return;
			if (sharedDcReportRun(saved.inputs) && !sources.energy_run_id)
				throw new ApiError(409, "report_inputs_changed");
			if (hasReportWiring(saved.inputs) && !sources.equipment_run_id) {
				const readCheck = async (id: string) =>
					readRun(
						await client.query(
							"runs/read",
							{ schema_version: 1, run_id: id },
							session.query_scope,
							request.signal,
						),
						project.id,
						id,
						RUN_OPERATIONS["runs/check-equipment"],
					);
				let run: PlanningRun;
				if (pendingWiringCheck) {
					run = await readCheck(pendingWiringCheck);
				} else {
					const checked = await operations.start("runs/check-equipment", {
						expected_revision: saved.revision,
						input_contract: projectInputContract,
						inputs: authoredDiscoveryInputs(saved.inputs),
					});
					if (!current() || checked?.path !== "runs/check-equipment") return;
					saved = checked.project;
					run = checked.run;
				}
				while (runPending(run.state)) {
					await waitForRunPoll(request.signal);
					run = await readCheck(run.id);
				}
				if (!current()) return;
				if (
					run.revision !== saved.revision ||
					run.manifest.input_sha256 !== saved.input_sha256 ||
					run.state !== "succeeded" ||
					!run.result ||
					readObject(run.result.assessment).pv_electrical == null
				)
					throw new ApiError(422, "report_wiring_check_failed");
				sources.equipment_run_id = run.id;
			}
			const reply = await operations.start("runs/report", {
				expected_revision: saved.revision,
				options: {
					locale: config.locale.startsWith("de") ? "de" : "en",
					...sources,
					logo,
				},
			});
			if (reply?.path === "runs/report" && current()) {
				accepted(reply.run);
				navigate("review");
			}
		} catch (cause) {
			if (!current()) return;
			if (
				cause instanceof ApiError &&
				([401, 403].includes(cause.status) || cause.code === "session_changed")
			)
				recheck();
			else setError(cause);
		} finally {
			if (reportPreparation.current === request) {
				reportPreparation.current = null;
				setPreparingReport(false);
			}
		}
	}
	if (!draft)
		return <p role="status">{__("Opening the project…", "linker-tools")}</p>;
	const inputs = draft.history.current;
	const brief =
		inputs.brief === undefined ? emptyBrief() : readBrief(inputs.brief);
	const visible = steps.filter(
		(s) => s !== "solar" || brief.system_scope !== "storage_only",
	);
	const labels: Record<Step, string> = {
		project: __("Project", "linker-tools"),
		solar: __("Solar", "linker-tools"),
		energy: __("Energy use", "linker-tools"),
		system: __("System", "linker-tools"),
		review: __("Report & inquiry", "linker-tools"),
	};
	const failedRead = [
		...(legacyModels ? [adoptedSearch, comparisonSource] : []),
		...(step === "system" ? [systemRead] : []),
	].find((query) => query.isError);
	const confirmedIntent = operations.intent?.resultId
		? operations.intent
		: null;
	const unconfirmed = operations.records.filter(
		(record) =>
			!operations.busy &&
			record.resultId === null &&
			(operations.storageFailed || record.key !== confirmedIntent?.key),
	);
	const awaitingComparison = unconfirmed.some(
		(record) => record.path === "runs/find-equipment",
	);
	const findingEquipment =
		operations.busy && operations.intent?.path === "runs/find-equipment";
	const failure =
		failedRead?.error ??
		error ??
		operations.error ??
		history.error ??
		search.error ??
		report.error;
	const country = brief.site.country_code
		? (config.countries[brief.site.country_code] ?? brief.site.country_code)
		: "";
	const siteLabel = [brief.site.location_label, country]
		.filter(Boolean)
		.join(" · ");
	const number = new Intl.NumberFormat(config.locale, {
		maximumFractionDigits: 2,
	});
	const reference = referenceDraft(inputs);
	const pvArrays =
		reference.model === KNOWN_PV_MODEL ? reference.arrays : undefined;
	const selectedUnits = selectedCandidate
		? isPlantCandidate(selectedCandidate)
			? selectedCandidate.plant.units.map((u) => u.selection)
			: [selectedCandidate.selection]
		: [];
	const pvSizes = pvArrays?.length
		? pvArrays.map((a) => a.peak_power_kwp)
		: selectedUnits.map((u) => u.pv_dc_kw);
	const roofModules =
		brief.system_scope !== "storage_only" &&
		!pvSizes.some((size) => size != null) &&
		inputs.geometry !== undefined
			? moduleSummary(activePvGeometry(inputs.geometry).geometry)
			: null;
	const assessment = selectedDetail.data;
	const assessments = assessment?.systems
		? (assessment.systems as JsonObject[]).map((u) => readObject(u.assessment))
		: assessment
			? [assessment]
			: [];
	const powers = assessments.map(
		(a) =>
			(a.checks as JsonObject[]).find(
				(c) => c.id === "converter_identity" && c.status === "satisfied",
			)?.actual,
	);
	const total = (values: unknown[], unit: string) =>
		values.length && values.every((v): v is number => typeof v === "number")
			? `${number.format(values.reduce((a, b) => a + b, 0))} ${unit}`
			: "—";
	const inverterId = equipmentDraft(inputs).inverter_product_id;
	const plantWiring =
		wiringPlant && inputs.pv_plant_string_plan != null
			? readPvPlantStringPlan(inputs.pv_plant_string_plan).units
			: [];
	const hasRoofModules =
		wiringPlant &&
		inputs.geometry !== undefined &&
		activePvGeometry(inputs.geometry).arrays.length > 0;
	const activeStep =
		brief.system_scope === "pv_only" && hasStorageToExclude(inputs)
			? "project"
			: step === "solar" && brief.system_scope === "storage_only"
				? "energy"
				: step;
	return (
		<div className="sc-configurator">
			<ProjectHeading
				title={project.title}
				location={siteLabel}
				actions={
					<div className="sc-actions">
						<span className="sc-muted" role="status">
							{controller.busy
								? __("Saving…", "linker-tools")
								: draft.pending
									? __("Save not confirmed", "linker-tools")
									: isDirty(draft)
										? __("Unsaved changes", "linker-tools")
										: sprintf(
												__("Saved · revision %d", "linker-tools"),
												draft.baseline.revision,
											)}
						</span>
						<button
							type="button"
							className="sc-button"
							data-linker-genie-open
							data-linker-genie-planning=""
							disabled={!admitted}
							onClick={() => setGenieReportId(null)}
						>
							{__("Ask Genie", "linker-tools")}
						</button>
						<button
							className="sc-button"
							disabled={
								controller.busy ||
								preparingReport ||
								navigationBlocked ||
								Boolean(draft.pending || draft.conflict) ||
								!draft.history.past.length
							}
							onClick={() => update(undoDraft)}
						>
							{__("Undo", "linker-tools")}
						</button>
						<button
							className="sc-button"
							disabled={
								controller.busy ||
								navigationBlocked ||
								Boolean(draft.pending || draft.conflict) ||
								!draft.history.future.length
							}
							onClick={() => update(redoDraft)}
						>
							{__("Redo", "linker-tools")}
						</button>
						<button
							className="sc-button"
							disabled={
								controller.busy ||
								navigationBlocked ||
								Boolean(draft.conflict) ||
								controller.recoveries.length > 0
							}
							onClick={() => void controller.save()}
						>
							{draft.pending && !draft.conflict && !controller.busy
								? __("Retry save", "linker-tools")
								: __("Save snapshot", "linker-tools")}
						</button>
						<button
							className="sc-button"
							onClick={() => {
								if (!mayLeave()) return;
								void controller.flush().then((ok) => {
									if (ok) close();
								});
							}}
						>
							{__("Projects", "linker-tools")}
						</button>
					</div>
				}
			/>
			<nav
				className="sc-nav"
				aria-label={__("Project navigation", "linker-tools")}
			>
				{visible.map((s, i) => (
					<button
						key={s}
						aria-current={activeStep === s ? "step" : undefined}
						onClick={() => navigate(s)}
					>
						<span className="sc-step-number">{i + 1}</span>
						{labels[s]}
					</button>
				))}
			</nav>
			{navigationRefused &&
				navigationBlocked &&
				(!missingModules || invalidInput || roofEditing || importOpen) && (
					<p role="alert">
						{roofEditing || importOpen
							? __(
									"Finish or cancel roof editing before leaving this workspace.",
									"linker-tools",
								)
							: invalidInput
								? __(
										"Correct the highlighted input before leaving this project.",
										"linker-tools",
									)
								: __(
										"Save or cancel your string changes before continuing.",
										"linker-tools",
									)}
					</p>
				)}
			{preparingReport && activeStep === "review" && (
				<p className="sc-card" role="status">
					{__("Preparing planning report…", "linker-tools")}
				</p>
			)}
			{Boolean(failure) && (
				<div className="sc-card" role="alert">
					<p>
						{failure instanceof ApiError &&
						[
							"equipment_selection_changed",
							"preparation_source_changed",
						].includes(failure.code)
							? __(
									"The project has changed. Compare systems again to update the choices.",
									"linker-tools",
								)
							: failure instanceof ApiError &&
								  failure.code === "report_wiring_check_failed"
								? __(
										"The wiring check could not finish. Review the equipment and PV strings, then generate the report again.",
										"linker-tools",
									)
								: failure instanceof ApiError &&
									  failure.fields.some((field) =>
											/^(?:pvgis_reference|brief\.site\.(?:latitude|longitude))/.test(
												field,
											),
									  )
									? __(
											"Complete the site coordinates, array details and PVGIS settings to compare systems.",
											"linker-tools",
										)
									: energyErrorText(failure)}
					</p>
					{failedRead && (
						<button
							className="sc-button"
							onClick={() => void failedRead.refetch()}
						>
							{__("Try again", "linker-tools")}
						</button>
					)}
				</div>
			)}
			{(controller.failed ||
				controller.recoveryFailed ||
				recoveryFailed ||
				operations.storageFailed) && (
				<p className="sc-card" role="alert">
					{__(
						"The project could not be saved or recovered. Keep this page open and try again.",
						"linker-tools",
					)}
				</p>
			)}
			{draft.conflict && (
				<div className="sc-card" role="alert">
					<p>
						{__(
							"This project was changed elsewhere. Choose which inputs to continue with.",
							"linker-tools",
						)}
					</p>
					<div className="sc-actions">
						<button
							className="sc-button"
							disabled={controller.busy}
							onClick={() => void controller.resolveConflict("local")}
						>
							{__("Keep my changes", "linker-tools")}
						</button>
						<button
							className="sc-button"
							disabled={controller.busy}
							onClick={() => void controller.resolveConflict("saved")}
						>
							{__("Use saved project", "linker-tools")}
						</button>
					</div>
				</div>
			)}
			{controller.recoveries.map((candidate) => (
				<button
					className="sc-button"
					key={candidate.scope}
					onClick={() => controller.restore(candidate)}
				>
					{__("Restore local changes", "linker-tools")}
				</button>
			))}
			{findingEquipment && (
				<p className="sc-card" role="status">
					{__("Finding equipment for your project…", "linker-tools")}
				</p>
			)}
			{unconfirmed.map((record) => (
				<div className="sc-card" key={record.key}>
					<p>
						{__(
							"Confirm the result of your previous request before continuing.",
							"linker-tools",
						)}
					</p>
					<button
						className="sc-button"
						disabled={operations.busy}
						onClick={() =>
							void operations.retry(record).then((reply) => {
								if (reply?.path === "runs/check-equipment") {
									navigate("review");
								} else if (
									reply &&
									"run" in reply &&
									reply.path !== "runs/pvgis-reference"
								) {
									accepted(reply.run);
									if (reply.path === "runs/report") navigate("review");
									else if (reply.path === "runs/find-equipment")
										navigate("system");
									else if (
										reply.path === "runs/calculate" ||
										reply.path === "runs/weather" ||
										reply.path === "runs/pv"
									)
										navigate("energy");
								}
							})
						}
					>
						{__("Check previous request", "linker-tools")}
					</button>
				</div>
			))}
			<div className="sc-layout">
				<main
					id={activeStep === "review" ? "lp-calculations" : undefined}
					ref={main}
					tabIndex={-1}
					className="sc-main"
				>
					{activeStep === "project" && (
						<ProjectDetails
							existingEquipment={
								<ProjectEquipment
									inputs={
										comparisonInputs
											? restoreComparisonModels(inputs, comparisonInputs)
											: inputs
									}
									client={client}
									scope={session.query_scope}
									disabled={blocked || modelsUnavailable}
									edit={edit}
								/>
							}
							inputs={inputs}
							config={config}
							disabled={blocked || modelsUnavailable}
							edit={edit}
							next={() =>
								navigate(
									brief.system_scope === "storage_only" ? "energy" : "solar",
								)
							}
						/>
					)}
					{activeStep === "solar" && (
						<SolarInstallation
							inputs={inputs}
							config={config}
							client={client}
							session={session}
							disabled={blocked || modelsUnavailable}
							edit={edit}
							next={() => navigate("energy")}
							wiring={
								wiringPlant
									? wiringPlant.units.map((unit, index) => {
											const hasPlan = plantWiring.some(
												(row) => row.unit_id === unit.id,
											);
											if (
												!hasPlan &&
												(!hasRoofModules ||
													typeof equipmentDraft(unit.inputs)
														.inverter_product_id !== "number")
											)
												return null;
											return (
												<fieldset className="sc-card" key={unit.id}>
													<legend>
														{unit.name ||
															sprintf(
																__("System %d", "linker-tools"),
																index + 1,
															)}
													</legend>
													<PlantPvStringSetup
														draft={draft}
														unit={unit}
														units={wiringPlant.units}
														edit={editWiring}
														locale={config.locale}
														disabled={blocked || modelsUnavailable}
														onValidity={wiringCallbacks[unit.id]!}
														checkedInReport
													/>
												</fieldset>
											);
										})
									: (typeof inverterId === "number" ||
											inputs.pv_string_plan != null) && (
											<PvStringSetup
												draft={draft}
												edit={editWiring}
												inverterId={
													typeof inverterId === "number" ? inverterId : null
												}
												locale={config.locale}
												disabled={blocked || modelsUnavailable}
												onValidity={wiringCallbacks[""]!}
												checkedInReport
											/>
										)
							}
							initialMap={mapPropertyLinks.has(location.hash)}
							onEditing={setRoofEditing}
							geometryImport={{
								projectId: project.id,
								recheck,
								confirmedInputs: draft.baseline.inputs,
								onActivity: setImportOpen,
								recoveryScopes,
								recoveryChecking,
							}}
						/>
					)}
					{(energyOpened || activeStep === "energy") && (
						<div hidden={activeStep !== "energy"}>
							<EnergyDemand
								projectId={project.id}
								inputs={inputs}
								locale={config.locale}
								client={client}
								session={session}
								recheck={recheck}
								disabled={blocked}
								edit={edit}
								modelsUnavailable={modelsUnavailable}
								compare={() => void compare()}
								onValidity={setEnergyValid}
							/>
							{hasPlant(inputs) &&
								brief.system_scope !== "storage_only" &&
								brief.system_scope !== "pv_only" && (
									<SharedDcEnergy
										draft={draft}
										locale={config.locale}
										client={client}
										session={session}
										store={store}
										disabled={blocked || modelsUnavailable || !energyValid}
										active={activeStep === "energy"}
										edit={edit}
										save={controller.save}
										openEquipment={() => navigate("project")}
										openDesign={() => navigate("solar")}
										onValidity={setSharedDcValid}
										registerProfileGuard={registerProfileGuard}
										recoveryScopes={recoveryScopes}
										recoveryChecking={recoveryChecking}
										recheck={recheck}
										runs={[
											...(latestRuns ?? []),
											...(olderHistory.data?.pages.flatMap(
												(page) => page.items,
											) ?? []),
										]}
										moreRuns={
											(olderHistory.data
												? olderHistory.hasNextPage
												: firstCursor) && !olderHistory.isFetching
												? () => void olderHistory.fetchNextPage()
												: undefined
										}
										submitted={submittedDc}
										start={(path) => void startSharedDc(path)}
										generateComparison={generateComparison}
										operationError={error ?? operations.error}
									/>
								)}
						</div>
					)}
					{activeStep === "system" && (
						<>
							{findingEquipment ||
							awaitingComparison ? null : searchRun?.state === "succeeded" &&
							  searchRun.result ? (
								<SystemOptions
									solarOnly={brief.system_scope === "pv_only"}
									run={searchRun}
									client={client}
									scope={session.query_scope}
									locale={config.locale}
									disabled={blocked || modelsUnavailable}
									selectedId={
										choice?.run_id === searchRun.id
											? String(choice.candidate_id)
											: null
									}
									comparison={comparison}
									onSaveComparison={setComparison}
									onEditEquipment={() => navigate("project")}
									onSelect={select}
								/>
							) : !searchRun && systemRead.isPending ? (
								<p className="sc-card" role="status">
									{__("Reading saved calculation results…", "linker-tools")}
								</p>
							) : !searchRun && systemRead.isError ? null : (
								<section className="sc-card">
									{searchRun && runPending(searchRun.state) ? (
										<p role="status">
											{__(
												"Finding equipment for your project…",
												"linker-tools",
											)}
										</p>
									) : (
										<>
											<p>
												{searchRun?.state === "failed"
													? searchRun.error?.code ===
														"comparison_pv_no_common_period"
														? __(
																"The solar year does not overlap the energy use profile. Choose a matching year in Solar or change the energy use profile.",
																"linker-tools",
															)
														: searchRun.error?.code
																	?.toString()
																	.startsWith("weather_")
															? __(
																	"PVGIS could not estimate generation. Check the site coordinates, array orientation and reference settings, then compare systems again.",
																	"linker-tools",
																)
															: __(
																	"The equipment search could not finish. Your inputs are saved.",
																	"linker-tools",
																)
													: __(
															"Enter your energy needs to compare equipment for this project.",
															"linker-tools",
														)}
											</p>
											<button
												className="sc-button sc-primary"
												onClick={() => navigate("energy")}
											>
												{__("Energy use", "linker-tools")}
											</button>
										</>
									)}
								</section>
							)}
							<footer className="sc-footer">
								<button
									className="sc-button"
									onClick={() => navigate("energy")}
								>
									{__("Back", "linker-tools")}
								</button>
								<button
									className="sc-button sc-primary"
									disabled={
										blocked ||
										(!choice &&
											!(
												searchRun?.state === "succeeded" &&
												searchRun.result?.retained_inverter &&
												searchRun.manifest.input_sha256 ===
													draft.baseline.input_sha256 &&
												sameJson(inputs, draft.baseline.inputs)
											))
									}
									onClick={() => navigate("review")}
								>
									{__("Review the proposal", "linker-tools")}
								</button>
							</footer>
						</>
					)}
					{activeStep === "review" && (
						<ReviewProposal
							project={draft.baseline}
							inputs={inputs}
							run={reportRun}
							history={{
								items: earlierReports,
								selected: viewedReport,
								select: selectReport,
								run: viewedRun,
								reading:
									historicalRunQuery.isLoading ||
									Boolean(viewedRun && runPending(viewedRun.state)),
								readFailed: historicalRunQuery.isError,
								unavailable:
									viewedReportId === null ||
									Boolean(
										viewedRun &&
										viewedRun.state !== "succeeded" &&
										!runPending(viewedRun.state),
									),
								retryRead: () => void historicalRunQuery.refetch(),
								hasMore: olderHistory.data
									? olderHistory.hasNextPage
									: firstCursor !== null,
								loading: olderHistory.isFetching,
								loadFailed: olderHistory.isError,
								loadMore: () => void olderHistory.fetchNextPage(),
							}}
							client={client}
							session={session}
							operations={operations}
							locale={config.locale}
							blocked={blocked || modelsUnavailable}
							current={Boolean(
								reportRun &&
								reportRun.revision === draft.baseline.revision &&
								!isDirty(draft),
							)}
							generate={(logo) => void generate(logo)}
							askGenie={(run) => setGenieReportId(run.id)}
							recheck={recheck}
						/>
					)}
				</main>
				<aside className="sc-sidebar">
					<section className="sc-card">
						<p className="sc-muted">
							{__("Current configuration", "linker-tools")}
						</p>
						<h3>{project.title}</h3>
						<dl>
							{brief.system_scope !== "storage_only" && (
								<div>
									<dt>{__("Solar capacity", "linker-tools")}</dt>
									<dd>
										{total(
											roofModules?.count ? [roofModules.stc_kwp] : pvSizes,
											"kWp",
										)}
									</dd>
								</div>
							)}
							{brief.system_scope !== "pv_only" && (
								<div>
									<dt>{__("Usable battery capacity", "linker-tools")}</dt>
									<dd>
										{total([selectedCandidate?.usable_energy_kwh], "kWh")}
									</dd>
								</div>
							)}
							<div>
								<dt>{__("Inverter power", "linker-tools")}</dt>
								<dd>{total(powers, "kW")}</dd>
							</div>
						</dl>
						{selectedCandidate && assessment && (
							<details>
								<summary>{__("View parts list", "linker-tools")}</summary>
								<CandidateMaterials
									candidate={selectedCandidate}
									assessment={assessment}
									locale={config.locale}
								/>
							</details>
						)}
					</section>
				</aside>
			</div>
		</div>
	);
}
