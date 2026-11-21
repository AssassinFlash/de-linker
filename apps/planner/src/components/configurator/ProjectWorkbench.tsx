import {
	useCallback,
	useEffect,
	useEffectEvent,
	useMemo,
	useRef,
	useState,
} from "react";
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
import {
	measurePlannerChrome,
	revealHashTarget,
} from "../../data/measurePlannerChrome.ts";
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
	readPlanningOperation,
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
import { takeRoofImageryConsent } from "../../data/roofImageryConsent.ts";
import { dropGeometricRoofAc } from "../../domain/profiles.ts";
import { readPvPlantStringPlan } from "../../domain/pvPlantStrings.ts";
import { adoptPlantCandidate } from "../../domain/plantSearch.ts";
import {
	PLANNER_NAVIGATION,
	replacePlannerLocation,
} from "../../data/plannerLocation.ts";
import { needsPreliminaryComparison } from "./HomepageDemand.tsx";
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
import { reportCanTransfer, ReviewProposal } from "./ReviewProposal.tsx";
import { ReviewInquiry } from "./ReviewInquiry.tsx";
import { InquiryStages, ProjectHeading } from "./ProjectHeading.tsx";
import { PlantPvStringSetup } from "../equipment/PlantPvStringSetup.tsx";
import {
	PvStringSetup,
	type StringEditBlock,
} from "../equipment/PvStringSetup.tsx";
import { EnergyComparison } from "../energy/EnergyComparison.tsx";
import { RunResult } from "../energy/RunResult.tsx";
import { RunBasis } from "../energy/RunBasis.tsx";
import { isEnergyTask } from "../../data/readEnergyResult.ts";
import { comparisonPair } from "../../data/energyComparison.ts";
import { energyErrorText } from "../energy/EnergyError.tsx";
import { referenceDraft, KNOWN_PV_MODEL } from "../../domain/pvgisReference.ts";
import { moduleSummary } from "../../domain/panelPoses.ts";
import { activePvGeometry, checkPvWeather } from "../../domain/solarSetup.ts";
import { __, sprintf } from "../../i18n.ts";

import {
	ProjectNavigation,
	isRoofLocation,
	projectChapter,
	type ProjectChapter as Step,
} from "./ProjectNavigation.tsx";

function initialStep(): Step {
	return projectChapter(new URL(location.href));
}

function useProjectResult(
	client: PlannerClient,
	session: Session,
	projectId: string,
	task: TaskKind | undefined,
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

function useSearchInputs(
	client: PlannerClient,
	scope: string,
	projectId: string,
	run: PlanningRun | null,
) {
	return useQuery({
		queryKey: [
			scope,
			"configurator-comparison-models",
			projectId,
			run?.id ?? null,
		],
		enabled: !!run && client.isCurrentScope(scope),
		queryFn: async ({ signal }) =>
			readRunInputs(
				await client.query(
					"runs/inputs",
					{ schema_version: 1, project_id: projectId, run_id: run!.id },
					scope,
					signal,
				),
				run!,
			),
	});
}

export default function ProjectWorkbench({
	project,
	session,
	client,
	store,
	config,
	recheck,
	close,
	comparePreliminary,
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
	comparePreliminary?: (project: Project) => void;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	recoveryFailed?: boolean;
}) {
	const controller = useProjectDraft(project, session, client, store, recheck);
	const { draft, update, acknowledgeProject } = controller;
	const params = new URL(location.href).searchParams;
	const guided =
		params.get("guided") === "inquiry" && params.get("project") === project.id;
	const [step, setStep] = useState<Step>(initialStep);
	const [systemRequest, setSystemRequest] = useState<
		"existing" | "navigation" | null
	>(() => (step === "system" ? "existing" : null));
	const checkingSystem = systemRequest !== null;
	useEffect(() => {
		if (!guided) return;
		const restore = () => {
			if (new URL(location.href).searchParams.get("project") === project.id) {
				const restored = initialStep();
				setSystemRequest(restored === "system" ? "existing" : null);
				setStep(restored);
			}
		};
		window.addEventListener("popstate", restore);
		return () => window.removeEventListener("popstate", restore);
	}, [guided, project.id]);
	const main = useRef<HTMLElement>(null);
	const energyReady = Boolean(draft && step === "energy");
	useEffect(() => {
		if (!energyReady || location.hash !== "#sc-energy") return;
		const root = main.current?.closest<HTMLElement>("[data-linker-planner]");
		if (root) {
			measurePlannerChrome(root);
			revealHashTarget(root);
		}
	}, [energyReady]);
	const workbench = useRef<HTMLDivElement>(null);
	const [assessmentPending, setAssessmentPending] = useState(false);
	const [energyValid, setEnergyValid] = useState(true);
	const [coordinatesValid, setCoordinatesValid] = useState(true);
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
		if (assessmentPending) return false;
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
		workbench.current?.scrollIntoView?.({ block: "start" });
	}, [step]);
	const [error, setError] = useState<unknown>(null);
	const [selecting, setSelecting] = useState(false);
	const reportPreparation = useRef<AbortController | null>(null);
	const [preparingReport, setPreparingReport] = useState(false);
	const [replacedSearch, setReplacedSearch] = useState<string | null>(null);
	const [submittedSearch, setSubmittedSearch] = useState<string | null>(null);
	const [comparison, setComparison] = useState<SystemComparison | null>(null);
	const [submittedReport, setSubmittedReport] = useState<string | null>(null);
	const [savedEnergy, setSavedEnergy] = useState<"run" | "comparison" | null>(
		() => {
			if (step !== "energy" || params.get("project") !== project.id)
				return null;
			if (comparisonPair(params.get("compare"))) return "comparison";
			return /^[a-f0-9]{32}$/.test(params.get("run") ?? "") ? "run" : null;
		},
	);
	const [viewedReport, setViewedReport] = useState(() => {
		const params = new URL(location.href).searchParams;
		return step === "review" && params.get("project") === project.id
			? params.get("run")
			: null;
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
		submittedSearch ??
		currentSearch ??
		(guided
			? step === "review"
				? selectedSearch
				: null
			: (selectedSearch ?? newest(SEARCH_TASK)));
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
	const requestedReport = params.get("run");
	const guidedReportId =
		guided &&
		step === "review" &&
		requestedReport &&
		/^[a-f0-9]{32}$/.test(requestedReport)
			? requestedReport
			: null;
	const reportId =
		submittedReport ??
		guidedReportId ??
		(guided
			? reportRuns.find((item) => item.revision === draft?.baseline.revision)
			: reportRuns[0]
		)?.id ??
		null;
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
		undefined,
		step === "review" ? viewedReportId : null,
	);
	const energyRun = useProjectResult(
		client,
		session,
		project.id,
		undefined,
		step === "energy" && savedEnergy === "run" ? params.get("run") : null,
	);
	function openEnergyRun(id: string) {
		const url = new URL(location.href);
		url.searchParams.delete("compare");
		url.searchParams.set("run", id);
		replacePlannerLocation(url);
		setSavedEnergy("run");
	}
	const historical = admitted ? historicalRunQuery.data : undefined;
	const viewedRun =
		historical && runTask(historical) === REPORT_TASK ? historical : null;
	useEffect(() => {
		const oldSingle =
			step === "review" && historical && isEnergyTask(runTask(historical));
		const oldPair = step === "energy" && savedEnergy === "comparison";
		if (!oldSingle && !oldPair) return;
		const url = new URL(location.href);
		if (
			url.searchParams.get("project") !== project.id ||
			url.hash === "#sc-energy"
		)
			return;
		url.hash = "sc-energy";
		if (oldSingle) {
			setViewedReport(null);
			setSavedEnergy("run");
			setStep("energy");
		}
		replacePlannerLocation(url);
	}, [historical, step, savedEnergy, project.id]);
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
	const searchRun =
			checkingSystem || search.data?.id === replacedSearch
				? null
				: (search.data ?? null),
		reportRun = report.data ?? null;
	const reviewedReportId =
		guided &&
		step === "review" &&
		draft &&
		reportRun?.state === "succeeded" &&
		reportRun.revision === draft.baseline.revision &&
		!isDirty(draft)
			? reportRun.id
			: null;
	useEffect(() => {
		if (!reviewedReportId) return;
		const url = new URL(location.href);
		if (
			url.searchParams.get("project") !== project.id ||
			url.hash !== "#sc-review" ||
			url.searchParams.get("run") === reviewedReportId
		)
			return;
		url.searchParams.set("run", reviewedReportId);
		replacePlannerLocation(url);
	}, [reviewedReportId, project.id]);
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
			report:
				step === "energy" &&
				savedEnergy === "run" &&
				energyRun.data &&
				isEnergyTask(energyRun.data.result?.kind)
					? energyRun.data
					: (genieRun ?? null),
			energyComparison: step === "energy" && savedEnergy === "comparison",
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
	const comparisonSource = useSearchInputs(
		client,
		session.query_scope,
		project.id,
		legacyModels ? adoptedRun : null,
	);
	const oldRevision =
		checkingSystem &&
		search.data &&
		search.data.revision !== draft?.baseline.revision
			? search.data
			: null;
	const recordedInputs = useSearchInputs(
		client,
		session.query_scope,
		project.id,
		oldRevision,
	);

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
		if (task === SEARCH_TASK) {
			setReplacedSearch(null);
			setSubmittedSearch(run.id);
		} else if (task === REPORT_TASK) setSubmittedReport(run.id);
		else setSubmittedDc({ id: run.id, task });
		void history.refetch();
	}
	const modelsUnavailable = legacyModels && comparisonInputs === undefined;
	const projectWritesBlocked =
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
		Boolean(draft?.conflict);
	const unconfirmedOperation = operations.records.some(
		(r) => r.resultId === null,
	);
	const independentlyBlocked = projectWritesBlocked || Boolean(draft?.pending);
	const blocked = independentlyBlocked || unconfirmedOperation;
	const requestedRoofSave = useRef<JsonObject | null>(null);
	const attemptedRoofSave = useRef<JsonObject | null>(null);
	useEffect(() => {
		if (
			step !== "solar" ||
			!draft ||
			projectWritesBlocked ||
			unconfirmedOperation
		)
			return;
		const inputs = draft.history.current;
		const recoverRoofSave =
			controller.recovered &&
			draft.pending &&
			!sameJson(inputs.geometry, draft.baseline.inputs.geometry);
		if (requestedRoofSave.current !== inputs && !recoverRoofSave) return;
		if (attemptedRoofSave.current === inputs) return;
		attemptedRoofSave.current = inputs;
		void controller.save().catch(setError);
	});
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
	function editHistory(operation: typeof undoDraft) {
		const before = latest.current?.history.current;
		const after = update(operation)?.history.current;
		if (
			step === "solar" &&
			before &&
			after &&
			!sameJson(before.geometry, after.geometry)
		)
			requestedRoofSave.current = after;
	}
	const editWiring = useCallback(
		(operation: (inputs: JsonObject) => JsonObject) =>
			edit((inputs) =>
				invalidateEnergyReplay(dropGeometricRoofAc(operation(inputs))),
			),
		[edit],
	);
	function navigate(next: Step) {
		if (!mayLeave()) return;
		showStep(next);
	}
	async function closeProject() {
		if (mayLeave() && (await controller.flush())) close();
	}
	function openChapter(next: Step) {
		const current = latest.current;
		if (!current || !mayLeave()) return;
		if (next === "system" && !coordinatesValid) {
			showStep("solar");
			return;
		}
		showStep(next);
	}
	const checkCurrentComparison = useEffectEvent(async () => {
		const current = latest.current;
		if (!current) return;
		const run = search.data;
		const frozen = oldRevision ? recordedInputs.data : current.baseline.inputs;
		if (run && !frozen) return;
		setSystemRequest(null);
		if (!run && systemRequest === "existing") return;
		const inputs = current.history.current;
		if (run) {
			if (run.revision === current.baseline.revision && !isDirty(current)) {
				setReplacedSearch(null);
				return;
			}
			const saved = frozen!;
			const authored =
				comparisonInputs && needsComparisonModels(inputs)
					? restoreComparisonModels(inputs, comparisonInputs)
					: inputs;
			const settingsChanged =
				!authored.equipment_candidate &&
				["equipment_setup", "equipment_plant_setup"].some(
					(key) => !sameJson(authored[key] ?? null, saved[key] ?? null),
				);
			if (!settingsChanged && sameEquipmentDemand(authored, saved)) {
				setReplacedSearch(null);
				return;
			}
			setReplacedSearch(run.id);
		}
		if (comparePreliminary && needsPreliminaryComparison(inputs)) {
			const instance = lifetime.current;
			const saved = await controller.save();
			if (
				saved &&
				instance === lifetime.current &&
				location.hash === "#sc-system" &&
				client.isCurrentScope(session.query_scope)
			)
				comparePreliminary(saved);
		} else if (run) await compare();
	});
	useEffect(() => {
		if (
			step === "system" &&
			checkingSystem &&
			history.isSuccess &&
			(!searchId || search.isSuccess) &&
			(!oldRevision || recordedInputs.isSuccess) &&
			!modelsUnavailable &&
			!blocked
		)
			void checkCurrentComparison();
	}, [
		step,
		checkingSystem,
		history.isSuccess,
		searchId,
		search.isSuccess,
		oldRevision,
		recordedInputs.isSuccess,
		modelsUnavailable,
		blocked,
	]);

	function showStep(next: Step) {
		if (next !== step)
			setSystemRequest(next === "system" ? "navigation" : null);
		setGenieReportId(null);
		const url = new URL(location.href);
		const previous = url.hash;
		url.hash = "sc-" + next;
		if (savedEnergy !== null && previous === "#sc-energy") {
			url.searchParams.delete("run");
			url.searchParams.delete("compare");
			setSavedEnergy(null);
		}
		if (guided && previous === "#sc-review" && next !== "review") {
			url.searchParams.delete("run");
			url.searchParams.delete("retry_revision");
			url.searchParams.delete("linker_inquiry_retry");
		}
		if (guided && previous === "#sc-system" && next === "review") {
			window.history.pushState(null, "", url);
			window.dispatchEvent(new Event(PLANNER_NAVIGATION));
		} else if (url.href !== location.href) replacePlannerLocation(url);
		if (next === "energy") setEnergyOpened(true);
		setStep(next);
		setNavigationRefused(false);
	}
	async function saveGuidedSelection() {
		const instance = lifetime.current;
		const saved = await controller.save();
		if (
			!saved ||
			instance !== lifetime.current ||
			!client.isCurrentScope(session.query_scope)
		)
			return;
		setSubmittedReport(null);
		showStep("review");
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
		if (blocked || modelsUnavailable || !latest.current || !coordinatesValid)
			return;
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
	const startGuidedComparison = useEffectEvent(() => {
		void compare();
	});
	const guidedComparisonStarted = useRef(false);
	useEffect(() => {
		if (
			!guided ||
			step !== "system" ||
			!draft ||
			blocked ||
			modelsUnavailable ||
			!history.isSuccess ||
			searchId !== null ||
			guidedComparisonStarted.current
		)
			return;
		guidedComparisonStarted.current = true;
		startGuidedComparison();
	}, [
		guided,
		step,
		draft,
		blocked,
		modelsUnavailable,
		history.isSuccess,
		searchId,
	]);

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
			if (guided) await saveGuidedSelection();
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
	const canKeepInstalled = Boolean(
		draft &&
		searchRun?.state === "succeeded" &&
		searchRun.result?.retained_inverter &&
		searchRun.manifest.input_sha256 === draft.baseline.input_sha256 &&
		!isDirty(draft),
	);
	const prepareGuidedReport = useEffectEvent(() => {
		void generate(null);
	});
	const guidedReportAttempt = useRef<number | null>(null);
	useEffect(() => {
		if (
			!guided ||
			step !== "review" ||
			!draft ||
			blocked ||
			modelsUnavailable ||
			!history.isSuccess ||
			reportId !== null ||
			(!choice && !canKeepInstalled) ||
			guidedReportAttempt.current === draft.baseline.revision
		)
			return;
		guidedReportAttempt.current = draft.baseline.revision;
		prepareGuidedReport();
	}, [
		guided,
		step,
		draft,
		blocked,
		modelsUnavailable,
		history.isSuccess,
		reportId,
		choice,
		canKeepInstalled,
	]);
	if (!draft)
		return <p role="status">{__("Opening the project…", "linker-tools")}</p>;
	const inputs = draft.history.current;
	const brief =
		inputs.brief === undefined ? emptyBrief() : readBrief(inputs.brief);
	const failedRead = [
		...(legacyModels ? [adoptedSearch, comparisonSource] : []),
		...(step === "system"
			? [systemRead, ...(oldRevision ? [recordedInputs] : [])]
			: []),
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
	const guidedReview = guided && activeStep === "review";
	const guidedView = guidedReview || (guided && activeStep === "system");
	const guidedReportFailed =
		guidedReview &&
		(reportRun?.state === "failed" || reportRun?.state === "cancelled");
	const guidedChoiceNeedsSave =
		guided && activeStep === "system" && choice && draft.pending;
	const outdatedOption =
		guided &&
		activeStep === "system" &&
		error instanceof ApiError &&
		["equipment_selection_changed", "product_evidence_changed"].includes(
			error.code,
		);
	const currentReport = Boolean(
		reportRun &&
		reportRun.revision === draft.baseline.revision &&
		!isDirty(draft),
	);
	const activeTransferRunId =
		activeStep === "review" && currentReport && reportCanTransfer(reportRun)
			? reportRun?.id
			: undefined;
	const otherUnconfirmed = unconfirmed.filter(
		(record) =>
			record.path !== "draft/apply" ||
			!activeTransferRunId ||
			readPlanningOperation(record.path, record.body).report_run_id !==
				activeTransferRunId,
	);
	return (
		<div
			className={
				guided
					? "sc-configurator sc-project-workbench sc-intake"
					: "sc-configurator sc-project-workbench"
			}
			ref={workbench}
		>
			<ProjectHeading
				title={project.title}
				location={siteLabel}
				actions={
					guidedView ? null : (
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
								onClick={() => editHistory(undoDraft)}
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
								onClick={() => editHistory(redoDraft)}
							>
								{__("Redo", "linker-tools")}
							</button>
							<button
								className="sc-button"
								disabled={
									projectWritesBlocked ||
									unconfirmedOperation ||
									(!draft.pending && navigationBlocked)
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
									void closeProject();
								}}
							>
								{__("Projects", "linker-tools")}
							</button>
						</div>
					)
				}
			/>
			{guidedView ? (
				<InquiryStages guided reviewing={guidedReview} />
			) : (
				<ProjectNavigation
					current={activeStep}
					storageOnly={brief.system_scope === "storage_only"}
					open={openChapter}
				/>
			)}
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
			{preparingReport && activeStep === "review" && !guidedReview && (
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
			{otherUnconfirmed.map((record) => (
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
									guidedReportAttempt.current = null;
									void history.refetch();
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
			<div className={activeStep === "review" ? undefined : "sc-layout"}>
				<main
					id={"sc-" + activeStep}
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
					{(activeStep === "solar" || !coordinatesValid) && (
						<div hidden={activeStep !== "solar"}>
							<SolarInstallation
								active={activeStep === "solar"}
								onCoordinateValidity={setCoordinatesValid}
								inputs={inputs}
								config={config}
								client={client}
								session={session}
								disabled={blocked || modelsUnavailable}
								edit={edit}
								onLayoutChange={() => {
									requestedRoofSave.current =
										latest.current?.history.current ?? null;
								}}
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
								initialMap={isRoofLocation(location.hash)}
								initialPlan={location.hash === "#sc-roof-plan"}
								takeImageryConsent={(source) =>
									takeRoofImageryConsent(project.id, source)
								}
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
						</div>
					)}
					{activeStep === "energy" && savedEnergy === "comparison" && (
						<EnergyComparison
							projectId={project.id}
							runs={latestRuns ?? []}
							client={client}
							session={session}
							active={admitted}
							locale={config.locale}
							recheck={recheck}
							reportDisabled={blocked || isDirty(draft)}
							generateReport={generateComparison}
							openRun={openEnergyRun}
						/>
					)}
					{activeStep === "energy" &&
						savedEnergy === "run" &&
						admitted &&
						(energyRun.data && isEnergyTask(energyRun.data.result?.kind) ? (
							<section className="sc-work-panel">
								<RunResult
									run={energyRun.data}
									locale={config.locale}
									dirty={isDirty(draft)}
									confirmedRevision={draft.baseline.revision}
								/>
								<RunBasis
									run={energyRun.data}
									locale={config.locale}
									client={client}
									session={session}
									recheck={recheck}
								/>
							</section>
						) : energyRun.isPending ? (
							<p role="status">
								{__("Reading the saved calculation…", "linker-tools")}
							</p>
						) : (
							<div role="alert">
								<p>{energyErrorText(energyRun.error)}</p>
								<button
									type="button"
									className="sc-button"
									onClick={() => void energyRun.refetch()}
								>
									{__("Try again", "linker-tools")}
								</button>
							</div>
						))}
					{savedEnergy === null &&
						(energyOpened || activeStep === "energy") && (
							<div hidden={activeStep !== "energy"}>
								<EnergyDemand
									coordinatesInvalid={!coordinatesValid}
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
							{guidedChoiceNeedsSave && (
								<button
									className="sc-button sc-primary"
									disabled={controller.busy}
									onClick={() => void saveGuidedSelection()}
								>
									{__("Try again", "linker-tools")}
								</button>
							)}
							{outdatedOption && (
								<button
									className="sc-button sc-primary"
									disabled={blocked || modelsUnavailable}
									onClick={() => void compare()}
								>
									{__("Compare systems", "linker-tools")}
								</button>
							)}
							{awaitingComparison ? null : findingEquipment && guided ? (
								<p className="sc-card" role="status">
									{__("Finding equipment for your project…", "linker-tools")}
								</p>
							) : findingEquipment ? null : searchRun?.state === "succeeded" &&
							  searchRun.result ? (
								<SystemOptions
									solarOnly={brief.system_scope === "pv_only"}
									guided={guided}
									run={searchRun}
									client={client}
									scope={session.query_scope}
									locale={config.locale}
									disabled={blocked || modelsUnavailable}
									selectedId={
										!guided && choice?.run_id === searchRun.id
											? String(choice.candidate_id)
											: null
									}
									comparison={comparison}
									{...(!guided && {
										onSaveComparison: setComparison,
										onEditEquipment: () => navigate("project"),
									})}
									onSelectionPending={setAssessmentPending}
									onSelect={select}
								/>
							) : !searchRun &&
							  !failedRead &&
							  (checkingSystem || systemRead.isPending) ? (
								<p className="sc-card" role="status">
									{__("Reading saved calculation results…", "linker-tools")}
								</p>
							) : !searchRun && failedRead ? null : (
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
													: guided && !Boolean(error ?? operations.error)
														? __(
																"Finding equipment for your project…",
																"linker-tools",
															)
														: __(
																"Enter your energy needs to compare equipment for this project.",
																"linker-tools",
															)}
											</p>
											{(guided || replacedSearch) &&
												((searchRun && !runPending(searchRun.state)) ||
													Boolean(error ?? operations.error)) && (
													<button
														className="sc-button sc-primary"
														disabled={blocked || modelsUnavailable}
														onClick={() =>
															replacedSearch
																? setSystemRequest("navigation")
																: void compare()
														}
													>
														{__("Try again", "linker-tools")}
													</button>
												)}
											{(!guided ||
												Boolean(error ?? operations.error) ||
												searchRun?.state === "failed") && (
												<button
													className={
														guided ? "sc-button" : "sc-button sc-primary"
													}
													onClick={() => navigate("energy")}
												>
													{__("Energy use", "linker-tools")}
												</button>
											)}
										</>
									)}
								</section>
							)}
							{guided ? (
								canKeepInstalled && (
									<footer className="sc-footer">
										<button
											className="sc-button sc-primary"
											disabled={blocked}
											onClick={() => navigate("review")}
										>
											{__("Use this configuration", "linker-tools")}
										</button>
									</footer>
								)
							) : (
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
											assessmentPending ||
											(!choice && !canKeepInstalled)
										}
										onClick={() => navigate("review")}
									>
										{__("Review the proposal", "linker-tools")}
									</button>
								</footer>
							)}
						</>
					)}
					{guidedReview &&
						(currentReport &&
						reportRun?.state === "succeeded" &&
						reportCanTransfer(reportRun) &&
						brief.system_scope ? (
							<ReviewInquiry
								project={draft.baseline}
								direction={brief.system_scope}
								client={client}
								scope={session.query_scope}
								locale={config.locale}
								active
								ready={!blocked}
								changeSelection={() => navigate("system")}
								recheck={recheck}
								reportRunId={reportRun.id}
							/>
						) : (
							<section className="sc-card">
								{Boolean(failure) ||
								(reportRun && !runPending(reportRun.state)) ||
								(!choice && !canKeepInstalled && history.isSuccess) ? (
									<>
										<p>
											{__(
												"The inquiry form could not be loaded.",
												"linker-tools",
											)}
										</p>
										{(Boolean(failure) || guidedReportFailed) &&
											(choice || canKeepInstalled) &&
											!blocked && (
												<button
													className="sc-button sc-primary"
													onClick={() =>
														report.isError
															? void report.refetch()
															: void generate(null)
													}
												>
													{__("Try again", "linker-tools")}
												</button>
											)}
										<button
											className="sc-button"
											onClick={() => navigate("system")}
										>
											{__("Change selection", "linker-tools")}
										</button>
									</>
								) : (
									<p role="status">
										{__("Preparing your inquiry…", "linker-tools")}
									</p>
								)}
							</section>
						))}
					{activeStep === "review" && !guidedReview && (
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
								readFailed:
									historicalRunQuery.isError ||
									Boolean(historical && !viewedRun),
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
								loading: history.isPending || olderHistory.isFetching,
								loadFailed: history.isError || olderHistory.isError,
								loadMore: history.isError
									? () => void history.refetch()
									: () => void olderHistory.fetchNextPage(),
							}}
							client={client}
							session={session}
							operations={operations}
							locale={config.locale}
							blocked={blocked || modelsUnavailable}
							transferBlocked={independentlyBlocked || modelsUnavailable}
							current={currentReport}
							generate={(logo) => void generate(logo)}
							askGenie={(run) => setGenieReportId(run.id)}
							recheck={recheck}
						/>
					)}
				</main>
				{activeStep !== "review" && (
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
										client={client}
										scope={session.query_scope}
										candidate={selectedCandidate}
										assessment={assessment}
										locale={config.locale}
									/>
								</details>
							)}
						</section>
					</aside>
				)}
			</div>
		</div>
	);
}
