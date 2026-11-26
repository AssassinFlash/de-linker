import {
	readComparisonDraft,
	writeComparisonDraft,
	forgetComparisonDraft,
	type ComparisonDraft,
} from "../data/comparisonDraft.ts";
import {
	lazy,
	Suspense,
	useCallback,
	useEffect,
	useEffectEvent,
	useRef,
	useState,
} from "react";
import { flushSync } from "react-dom";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { JsonObject, Project, Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import type { CreationDestination, DraftStore } from "../data/DraftStore.ts";
import { creationIntents, intentId } from "../data/recoveryIntents.ts";
import type { ScopedCreation } from "../data/recoveryIntents.ts";
import { readObject, readProject, wire } from "../data/readProtocol.ts";
import type { Brief } from "../domain/brief.ts";
import { emptyBrief, readBrief } from "../domain/brief.ts";
import { changeEquipment, equipmentDraft } from "../domain/equipment.ts";
import { readScenarioDraft } from "../domain/energyScenario.ts";
import { issueLabel } from "./ProfileLabels.ts";
import {
	attachHomepageProfile,
	prepareHomepageProfile,
} from "../data/homepageProfile.ts";
import type { HomepageProfileUpload } from "../data/homepageProfile.ts";
import {
	emptyHomepageProfile,
	homepageProfileFile,
	HomepageLoadProfile,
	restoreHomepageProfile,
} from "./configurator/HomepageLoadProfile.tsx";
import type { HomepageProfileForm } from "./configurator/HomepageLoadProfile.tsx";
import { hasPlant } from "../domain/equipmentPlant.ts";
import { projectInputContract, sameJson } from "../domain/draft.ts";
import { __ } from "../i18n.ts";
import { Notice } from "./Notice.tsx";
import { useEquipmentProducts } from "../data/equipmentProducts.ts";
import { entryInputs, placedProduct } from "../domain/entryHints.ts";
import type { EntryHints } from "../domain/entryHints.ts";
import { formatDecimal } from "../domain/decimal.ts";
import type { Configuration } from "../data/config.ts";
import { RoofMapAction } from "./RoofMapAction.tsx";
import type { PlaceImagery } from "../domain/place.ts";
import {
	allowRoofImagery,
	clearRoofImageryConsent,
} from "../data/roofImageryConsent.ts";
import { RoofStart } from "./RoofStart.tsx";
import { locateProjectSite } from "../data/googleMaps.ts";
import { MAX_PROJECT_TITLE_LENGTH } from "../data/projectIndex.ts";
import { ProjectHeading } from "./configurator/ProjectHeading.tsx";
import { ProjectSummary, projectFacts } from "./configurator/ProjectFacts.tsx";
const ProjectDetails = lazy(() => import("./configurator/ProjectDetails.tsx"));
import { changeExistingSystem } from "../domain/existingSystem.ts";
const ProjectEquipment = lazy(
	() => import("./configurator/ProjectEquipment.tsx"),
);
import {
	AnnualElectricityUse,
	HomepageDemand,
} from "./configurator/HomepageDemand.tsx";
import {
	isHomepagePvReferenceReady,
	prepareHomepagePvReference,
} from "./configurator/HomepagePvReference.tsx";
import { changeEnergyGoal, energyGoal } from "../domain/energyGoal.ts";

import {
	PreliminaryOptions,
	systemNames,
} from "./configurator/PreliminaryOptions.tsx";

type LanguageIssue = "csv" | "number" | "storage";

import { ProjectDirections } from "./configurator/ProjectDirections.tsx";

export function NewProject({
	session,
	ensureSession,
	client,
	store,
	created,
	recheck,
	recoveryScopes,
	recoveryChecking = false,
	recoveryDiscoveryFailed = false,
	entryHints = null,
	initialProject = null,
	cancelled,
	locale = "en",
	config,
	openOnLoad = false,
	compareOnLoad = false,
	directComparison = false,
	workspaceHeading = false,
	equipmentFirst = false,
	opened,
	enterDetails,
	returnToComparison,
	creationPending = false,
	beginCreation,
}: {
	session: Session | null;
	ensureSession?: (() => Promise<Session>) | undefined;
	client: PlannerClient;
	store: DraftStore;
	created: (
		project: Project,
		destination?: CreationDestination | "energy",
		openResult?: boolean,
	) => boolean;
	recheck: () => void;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	recoveryDiscoveryFailed?: boolean;
	entryHints?: EntryHints | null;
	initialProject?: { title: string; inputs: JsonObject } | null;
	cancelled?: () => void;
	locale?: string;
	config?: Configuration;
	openOnLoad?: boolean;
	compareOnLoad?: boolean;
	directComparison?: boolean;
	workspaceHeading?: boolean;
	equipmentFirst?: boolean;
	opened?: () => void;
	enterDetails?: () => void;
	returnToComparison?: () => void;
	creationPending?: boolean;
	beginCreation?: () => (() => void) | null;
}) {
	const scope = session?.query_scope ?? "";
	const roofPermission = useRef<PlaceImagery | null>(null);
	const roofEntry = Boolean(
		config &&
		entryHints?.roof &&
		!initialProject &&
		!directComparison &&
		!compareOnLoad,
	);
	const [open, setOpen] = useState(
		Boolean(entryHints || initialProject || openOnLoad || compareOnLoad),
	);
	const openedOnLoad = useRef(openOnLoad);
	const comparisonStarted = useRef(false);
	function trackStart() {
		if (!comparisonStarted.current)
			comparisonStarted.current = Boolean(
				window.linkerTrack?.("configurator_start"),
			);
	}
	const draftEntry =
		directComparison || compareOnLoad || Boolean(returnToComparison);
	const source = JSON.stringify(entryHints);
	const [restored] = useState(() =>
		draftEntry && scope ? readComparisonDraft(scope, source) : null,
	);
	const draftId = useRef(restored?.id);
	const [scene, setScene] = useState<NonNullable<
		ComparisonDraft["scene"]
	> | null>(restored?.scene ?? null);
	const savedDraft = useRef<ComparisonDraft | null>(null);
	const [draftUnavailable, setDraftUnavailable] = useState(false);
	const [languageIssue, setLanguageIssue] = useState<LanguageIssue | null>(
		null,
	);
	const languageNotice = useRef<HTMLDivElement>(null);
	const projectForm = useRef<HTMLFormElement>(null);
	const [useHints, setUseHints] = useState(restored?.useHints ?? true);
	const [title, setTitle] = useState(
		restored?.title ?? initialProject?.title ?? "",
	);
	const [busy, setBusy] = useState(false);
	const [failed, setFailed] = useState(false);
	const [inputContractRequired, setInputContractRequired] = useState(false);
	const [projectGone, setProjectGone] = useState(false);
	const [recoveryFailed, setRecoveryFailed] = useState(false);
	const [demandError, setDemandError] = useState(false);
	const [referenceError, setReferenceError] = useState<
		"settings" | "location" | "addressService" | null
	>(null);
	const [profileForm, setProfileForm] = useState(emptyHomepageProfile);
	const [profileError, setProfileError] = useState("");
	const [profileCorrection, setProfileCorrection] = useState(false);
	const [editedCorrection, setEditedCorrection] = useState(false);
	const profile = useRef<HomepageProfileUpload | undefined>(undefined);
	const changeProfile = useCallback(
		(patch: Partial<HomepageProfileForm>) => {
			setProfileForm((current) => ({ ...current, ...patch }));
			if (patch.mappingValid === undefined) setProfileError("");
			if (profileCorrection && patch.mappingValid !== true)
				setEditedCorrection(true);
		},
		[profileCorrection],
	);
	const [invalidDemand, setInvalidDemand] = useState<ReadonlySet<string>>(
		new Set(),
	);
	const reportDemand = useCallback((field: string, valid: boolean) => {
		setInvalidDemand((before) => {
			if (before.has(field) === !valid) return before;
			const next = new Set(before);
			if (valid) next.delete(field);
			else next.add(field);
			return next;
		});
	}, []);
	const catalog = useEquipmentProducts(
		client,
		scope,
		Boolean(scope && entryHints?.productId),
	);
	const [draft, setDraft] = useState<JsonObject | null>(
		restored?.inputs ?? null,
	);
	const [carriedProduct, setCarriedProduct] = useState(
		restored?.carriedProduct ?? true,
	);
	const [recoveredInputs, setRecoveredInputs] = useState<JsonObject | null>(
		null,
	);
	const proposed = catalog.data?.prepared
		? catalog.data.products.find((item) => item.id === entryHints?.productId)
		: undefined;
	const product = proposed ? placedProduct([proposed], proposed.id) : null;
	const seed =
		initialProject?.inputs ??
		(entryHints && useHints
			? entryInputs(
					entryHints,
					__(
						"Values carried from a tool link. Review them for this project.",
						"linker-tools",
					),
					__(
						"Backup supply requested; accessories may be considered.",
						"linker-tools",
					),
				)
			: { brief: emptyBrief() });
	const seedBrief =
		seed.brief === undefined ? emptyBrief() : readBrief(seed.brief);
	const initialInputs = {
		...seed,
		brief: {
			...seedBrief,
			system_scope:
				compareOnLoad || returnToComparison || directComparison || roofEntry
					? seedBrief.system_scope
					: (seedBrief.system_scope ?? "new_pv_storage"),
		},
	};
	const goal = useHints ? entryHints?.commercialGoal : undefined;
	const commercialInputs =
		goal === "ev_buffer"
			? {
					...initialInputs,
					brief: {
						...initialInputs.brief,
						project_note: __("Buffer peaks from EV charging.", "linker-tools"),
					},
				}
			: initialInputs;
	const seeded = goal
		? changeEnergyGoal(
				commercialInputs,
				goal === "backup"
					? "backup"
					: goal === "self_consumption"
						? "self"
						: "peak",
			)
		: useHints && entryHints?.backup && entryHints.backup !== "none"
			? changeEnergyGoal(initialInputs, "backup")
			: initialInputs;
	const draftInputs = draft ?? seeded;
	const inputs: JsonObject =
		recoveredInputs ??
		(product && useHints && carriedProduct && !hasPlant(draftInputs)
			? withProduct(draftInputs, product)
			: draftInputs);
	const brief =
		inputs.brief === undefined ? emptyBrief() : readBrief(inputs.brief);
	function edit(operation: (inputs: JsonObject) => JsonObject) {
		if (busy || intent.current || (session && !client.isCurrentScope(scope)))
			return false;
		const changed = operation(inputs);
		if (
			product &&
			useHints &&
			carriedProduct &&
			changed.equipment_setup !== inputs.equipment_setup
		)
			setCarriedProduct(false);
		setDraft(changed);
		setLanguageIssue(null);
		setDemandError(false);
		setReferenceError(null);
		return true;
	}
	const [waitingAction, setWaitingAction] = useState<
		"details" | "submit" | null
	>(null);
	const pendingSubmit = useRef<Parameters<typeof submit>>([]);
	const [checking, setChecking] = useState(true);
	const [requests, setRequests] = useState<readonly ScopedCreation[]>([]);
	const intent = useRef<string | null>(null);
	const intentScope = useRef(scope);
	const destination = useRef<CreationDestination | null>(null);
	const lifetime = useRef(0);
	const sending = useRef(false);
	const openWork = useRef(false);
	openWork.current = Boolean(
		intent.current || draft || (title && title !== initialProject?.title),
	);
	const admitted = Boolean(scope && client.isCurrentScope(scope));
	const currentInputs = useEffectEvent(() => inputs);
	useEffect(() => {
		if (
			!draftEntry ||
			(intent.current && !(profileCorrection && editedCorrection)) ||
			!admitted ||
			(!draft &&
				!title &&
				useHints &&
				!draftId.current &&
				!profileForm.file &&
				!invalidDemand.size &&
				!entryHints)
		)
			return;
		const record = intent.current
			? null
			: {
					id: (draftId.current ??= crypto.randomUUID()),
					scope: scope,
					source,
					scene,
					title,
					inputs: directComparison ? currentInputs() : draft,
					useHints,
					carriedProduct,
				};
		if (record) {
			savedDraft.current = record;
			try {
				writeComparisonDraft(record);
				setDraftUnavailable(false);
			} catch {
				setDraftUnavailable(true);
			}
		}
		function showLanguageIssue(event: MouseEvent, reason: LanguageIssue) {
			event.preventDefault();
			flushSync(() => {
				setLanguageIssue(reason);
				if (reason === "storage") setDraftUnavailable(true);
			});
			const notice = languageNotice.current;
			notice?.focus({ preventScroll: true });
			notice?.scrollIntoView({ block: "center", behavior: "instant" });
		}
		function handoff(event: MouseEvent) {
			const target = event.target;
			if (!(target instanceof window.Element)) return;
			const link = target.closest<HTMLAnchorElement>(
				"header a[hreflang][lang], footer a[hreflang][lang]",
			);
			if (!link || new URL(link.href).origin !== location.origin) return;
			try {
				if (
					directComparison &&
					(profileForm.file ||
						projectForm.current?.querySelector(
							'[aria-invalid="true"], input:out-of-range',
						))
				) {
					showLanguageIssue(event, profileForm.file ? "csv" : "number");
					return;
				}
				const usePvAddress =
					projectForm.current?.querySelector<HTMLInputElement>(
						'input[name="pvgis_use_address"]',
					)?.checked ?? false;
				if (record)
					writeComparisonDraft({ ...record, usePvAddress }, link.href);
			} catch {
				showLanguageIssue(event, "storage");
			}
		}
		document.addEventListener("click", handoff, true);
		return () => document.removeEventListener("click", handoff, true);
	}, [
		scene,
		draftEntry,
		compareOnLoad,
		directComparison,
		carriedProduct,
		entryHints,
		profileForm.file,
		profileCorrection,
		editedCorrection,
		invalidDemand.size,
		admitted,
		draft,
		title,
		useHints,
		scope,
		source,
	]);
	useEffect(() => {
		if (directComparison && restored?.languageUrl === location.href)
			projectForm.current?.scrollIntoView({ block: "start" });
	}, [directComparison, restored]);

	const waitingForProduct = Boolean(
		!intent.current && useHints && entryHints?.productId && catalog.isPending,
	);
	const hasCarriedValues =
		entryHints &&
		[
			entryHints.annualKwh,
			entryHints.pvKw,
			entryHints.phase,
			entryHints.backup,
			entryHints.postalCode,
			entryHints.productId,
		].some((v) => v !== null);
	useEffect(() => {
		if (openOnLoad && !openedOnLoad.current) {
			openedOnLoad.current = true;
			setOpen(true);
		}
	}, [openOnLoad]);
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
		};
	}, [scope]);
	useEffect(() => {
		if (recoveryChecking || !admitted) return;
		let active = true;
		setChecking(true);
		void creationIntents(store, recoveryScopes ?? [scope])
			.then((records) => {
				if (!active || !client.isCurrentScope(scope)) return;
				const matching = records.filter((record) => {
					if (record.destination === "roof-comparison") return roofEntry;
					if (
						directComparison &&
						(record.destination === "guided-comparison" ||
							record.destination === "roof")
					)
						return true;
					if (roofEntry)
						return (
							!record.profile &&
							(record.destination === "roof" ||
								record.destination === "roof-plan" ||
								record.destination === "design")
						);
					if (
						record.destination === "roof" ||
						record.destination === "roof-plan"
					)
						return false;
					return (
						record.destination !== "guided-comparison" &&
						(record.destination === "preliminary-review") === compareOnLoad
					);
				});
				setRequests(matching);
				if (openWork.current) return;
				// Earlier roof entries and the regular project form both stored "design".
				// Offer those receipts by title until the customer chooses one.
				const resume = roofEntry
					? matching.find((record) => record.destination !== "design")
					: matching[0];
				if (resume) restoreCreation(resume);
			})
			.catch(() => {
				if (active) setRecoveryFailed(true);
			})
			.finally(() => {
				if (active) setChecking(false);
			});
		return () => {
			active = false;
		};
	}, [
		admitted,
		client,
		scope,
		store,
		recoveryScopes,
		recoveryChecking,
		compareOnLoad,
		directComparison,
		roofEntry,
	]);

	function admittedAction(
		action: "details" | "submit",
		...args: Parameters<typeof submit>
	) {
		if (admitted && !checking && !recoveryChecking) {
			if (action === "details") enterDetails?.();
			else void submit(...args);
			return;
		}
		if (!ensureSession) return;
		pendingSubmit.current = args;
		setWaitingAction(action);
		void ensureSession().catch(() => setWaitingAction(null));
	}
	const continueAction = useEffectEvent(() => {
		if (waitingAction === "details") enterDetails?.();
		if (waitingAction === "submit") void submit(...pendingSubmit.current);
	});
	useEffect(() => {
		if (
			waitingAction &&
			admitted &&
			!checking &&
			!recoveryChecking &&
			!recoveryDiscoveryFailed
		) {
			setWaitingAction(null);
			continueAction();
		}
	}, [
		waitingAction,
		admitted,
		checking,
		recoveryChecking,
		recoveryDiscoveryFailed,
	]);
	function restoreCreation(record: ScopedCreation) {
		intent.current = record.body;
		const { profile: savedProfile, profileIssue: issue } = record;
		profile.current = savedProfile;
		setProfileForm(
			savedProfile && issue
				? restoreHomepageProfile(savedProfile)
				: emptyHomepageProfile(),
		);
		setProfileCorrection(Boolean(issue));
		setEditedCorrection(false);
		setProfileError(issue ? issueLabel(issue.issue) : "");
		intentScope.current = record.scope;
		destination.current = record.destination;
		setTitle(record.title);
		setRecoveredInputs(readObject(JSON.parse(record.body).inputs));
		setProjectGone(false);
		setInputContractRequired(false);
		setOpen(true);
		setFailed(!issue);
	}
	async function submit(
		direction?: NonNullable<Brief["system_scope"]>,
		{
			discardProfile = false,
			useAddress = false,
			openRoof = false,
			useRoofPlan = false,
			compareRoofSite = false,
			keepInverter,
		}: {
			discardProfile?: boolean;
			useAddress?: boolean;
			openRoof?: boolean;
			useRoofPlan?: boolean;
			compareRoofSite?: boolean;
			keepInverter?: boolean;
		} = {},
	) {
		const roofPlan = useRoofPlan || destination.current === "roof-plan";
		const roof =
			!compareRoofSite &&
			(roofEntry || openRoof || destination.current === "roof");
		if (
			!session ||
			sending.current ||
			creationPending ||
			checking ||
			recoveryChecking ||
			recoveryDiscoveryFailed ||
			waitingForProduct ||
			!client.isCurrentScope(scope) ||
			(!intent.current &&
				!direction &&
				!compareRoofSite &&
				(roof || roofPlan
					? !roofPlan &&
						(!brief.site.country_code || !brief.site.location_label.trim())
					: !directComparison && (!title.trim() || !brief.system_scope)))
		)
			return;
		if (directComparison && !roof && !intent.current) {
			const goal = energyGoal(inputs);
			const invalidVisible =
				invalidDemand.has("annual") ||
				(invalidDemand.has("pv") &&
					brief.system_scope !== "storage_only" &&
					!hasPlant(inputs)) ||
				(goal === "backup" &&
					(invalidDemand.has("load") || invalidDemand.has("duration"))) ||
				(goal === "peak" && invalidDemand.has("peak"));
			if (invalidVisible) {
				setDemandError(true);
				return;
			}
			if (
				invalidDemand.has("coordinates") ||
				!isHomepagePvReferenceReady(inputs, brief, useAddress)
			) {
				setReferenceError(
					useAddress &&
						(!brief.site.country_code || !brief.site.location_label.trim())
						? "location"
						: "settings",
				);
				return;
			}
		}
		const editableProfile =
			directComparison && (!intent.current || profileCorrection);
		const file =
			editableProfile && !discardProfile
				? homepageProfileFile(profileForm)
				: null;
		if (
			editableProfile &&
			!discardProfile &&
			(profileForm.file || profileCorrection) &&
			!file
		) {
			setProfileError(
				__(
					"Check the profile columns, units and time interval, then try again.",
					"linker-tools",
				),
			);
			return;
		}
		if (
			file &&
			!roof &&
			energyGoal(inputs) === "peak" &&
			readScenarioDraft(inputs.energy_scenario).schedule.some(
				(period) => period.import_cap_kw === null,
			)
		) {
			setProfileError(
				__(
					"Enter your target grid import limit to compare peak reduction.",
					"linker-tools",
				),
			);
			return;
		}
		const releaseCreation = beginCreation?.();
		if (releaseCreation === null) return;
		const instance = lifetime.current;
		const submittedFrom = location.href;
		if (!intent.current) intentScope.current = scope;
		const originScope = intentScope.current;

		sending.current = true;
		setBusy(true);
		setReferenceError(null);
		setFailed(false);
		setProjectGone(false);
		setInputContractRequired(false);
		let creationConfirmed = false;
		try {
			const previousProfile = profileCorrection ? profile.current : undefined;
			let nextProfile = editableProfile ? undefined : profile.current;
			if (file) {
				try {
					nextProfile = await prepareHomepageProfile(
						file,
						session.runtime.limits,
					);
				} catch (error) {
					setProfileError(
						error instanceof ApiError &&
							(error.code === "file_size" || error.code === "body_too_large")
							? __("The file is empty or too large.", "linker-tools")
							: __(
									"Check the profile columns, units and time interval, then try again.",
									"linker-tools",
								),
					);
					return;
				}
			}
			if (lifetime.current !== instance) return;
			if (!intent.current) {
				let submittedInputs =
					keepInverter === undefined
						? inputs
						: changeExistingSystem(inputs, { keep_inverter: keepInverter });
				if ((roof && !roofPlan) || (directComparison && useAddress)) {
					try {
						if (roof && config) {
							if (!config.googleMapsApiKey) {
								setReferenceError("addressService");
								return;
							}
							const site = await locateProjectSite(brief.site, config);
							if (!site) {
								if (lifetime.current === instance)
									setReferenceError("location");
								return;
							}
							submittedInputs = { ...inputs, brief: { ...brief, site } };
						} else
							submittedInputs = await prepareHomepagePvReference(
								inputs,
								config ?? { locale },
								useAddress,
							);
					} catch {
						if (lifetime.current === instance)
							setReferenceError(roof ? "addressService" : "location");
						return;
					}
					if (lifetime.current !== instance) return;
				}
				const submittedBrief = readBrief(submittedInputs.brief);
				intent.current = wire(
					{
						schema_version: 1,
						input_contract: projectInputContract,
						title:
							title.trim() ||
							(roof && submittedBrief.site.location_label.trim()
								? submittedBrief.site.location_label
										.trim()
										.slice(0, MAX_PROJECT_TITLE_LENGTH)
								: __("New project", "linker-tools")),
						inputs: {
							...submittedInputs,
							brief: {
								...submittedBrief,
								system_scope: direction ?? submittedBrief.system_scope,
								site: {
									...submittedBrief.site,
									location_label: submittedBrief.site.location_label.trim(),
								},
							},
						},
						key: crypto.randomUUID(),
					},
					session.runtime.limits.max_json_depth,
					session.runtime.limits.max_body_bytes,
				);
				destination.current = compareRoofSite
					? "roof-comparison"
					: roofPlan
						? "roof-plan"
						: roof
							? "roof"
							: directComparison && !direction
								? "guided-comparison"
								: direction
									? "preliminary-review"
									: brief.system_scope === "storage_only"
										? null
										: "design";
			}
			await store
				.writeCreation(
					originScope,
					intent.current,
					destination.current,
					nextProfile,
					previousProfile ? { previous: previousProfile } : undefined,
				)
				.then(() => {
					if (directComparison && savedDraft.current) {
						forgetComparisonDraft(savedDraft.current);
						savedDraft.current = null;
						draftId.current = undefined;
					}
				})
				.catch((error: unknown) => {
					if (lifetime.current === instance) setRecoveryFailed(true);
					if (previousProfile) throw error;
				});
			if (lifetime.current !== instance) return;
			profile.current = nextProfile;
			setProfileCorrection(false);
			if (!client.isCurrentScope(scope)) {
				setFailed(true);
				return;
			}
			let project = readProject(
				await client.send("projects/create", intent.current, scope),
			);
			if (lifetime.current !== instance) return;
			creationConfirmed = true;
			trackStart();
			if (profile.current) {
				try {
					project = await attachHomepageProfile(
						client,
						session,
						project,
						profile.current,
					);
				} catch (error) {
					if (lifetime.current !== instance) return;
					if (!(error instanceof ApiError && error.profileIssue)) throw error;
					const issue = error.profileIssue;
					await store.writeCreation(
						originScope,
						intent.current,
						destination.current,
						profile.current,
						{ previous: profile.current, issue },
					);
					if (lifetime.current !== instance) return;
					setProfileForm(restoreHomepageProfile(profile.current));
					setProfileCorrection(true);
					setEditedCorrection(false);
					setProfileError(issueLabel(issue.issue));
					return;
				}
			}
			if (lifetime.current !== instance) return;
			await store.clearCreation(originScope, intent.current).catch(() => {
				if (lifetime.current === instance) setRecoveryFailed(true);
			});
			if (lifetime.current !== instance) return;
			const createdBrief =
				project.inputs.brief === undefined
					? null
					: readBrief(project.inputs.brief);
			if (
				destination.current === "roof" &&
				location.href === submittedFrom &&
				client.isCurrentScope(scope)
			) {
				if (roofPermission.current)
					allowRoofImagery(project.id, roofPermission.current);
				else clearRoofImageryConsent();
			}
			if (
				!created(
					project,
					destination.current === "roof-comparison"
						? "guided-comparison"
						: (destination.current ??
								(createdBrief?.system_scope === "storage_only"
									? "energy"
									: undefined)),
					location.href === submittedFrom,
				)
			) {
				setFailed(true);
				return;
			}
			if (savedDraft.current) {
				forgetComparisonDraft(savedDraft.current);
				savedDraft.current = null;
				draftId.current = undefined;
			}
			intent.current = null;
			destination.current = null;
			profile.current = undefined;
			setProfileForm(emptyHomepageProfile());
			setProfileCorrection(false);
			setProfileError("");
			setOpen(false);
			setTitle("");
			setDraft(null);
			setRecoveredInputs(null);
		} catch (error) {
			if (lifetime.current !== instance) return;
			setFailed(true);
			setInputContractRequired(
				error instanceof ApiError &&
					error.status === 422 &&
					error.code === "project_input_contract_required",
			);
			if (
				error instanceof ApiError &&
				(error.status === 401 ||
					error.status === 403 ||
					error.code === "session_changed")
			)
				recheck();
			// A creation receipt names its project. Once that project is deleted
			// the receipt can never replay, so the stored request is dead. Keep
			// the draft's own command and only replace its key, so the next
			// attempt creates the same project content instead of an empty one.
			if (
				error instanceof ApiError &&
				!creationConfirmed &&
				error.status === 404 &&
				error.code === "not_found" &&
				intent.current !== null
			) {
				const dead = intent.current;
				const draft = readObject(JSON.parse(dead));
				const rekeyed = wire(
					{ ...draft, key: crypto.randomUUID() },
					session.runtime.limits.max_json_depth,
					session.runtime.limits.max_body_bytes,
				);
				await store
					.replaceCreation(originScope, dead, rekeyed, destination.current)
					.catch(() => {
						if (lifetime.current === instance) setRecoveryFailed(true);
					});
				if (lifetime.current !== instance) return;
				intent.current = rekeyed;
				setRequests((records) =>
					records.map((record) =>
						record.body === dead ? { ...record, body: rekeyed } : record,
					),
				);
				setProjectGone(true);
			}
		} finally {
			releaseCreation?.();
			sending.current = false;
			if (lifetime.current === instance) setBusy(false);
		}
	}
	const selectedRequest = requests.find(
		(request) =>
			request.body === intent.current && request.scope === intentScope.current,
	);
	const chooseLegacy =
		roofEntry && requests.some((record) => record.destination === "design");
	const pendingRequests = (requests.length > 1 || chooseLegacy) && (
		<label className="sc-field">
			<span>{__("Unconfirmed project creations", "linker-tools")}</span>
			<select
				disabled={busy}
				value={selectedRequest ? intentId(selectedRequest) : ""}
				onChange={(event) => {
					const request = requests.find(
						(candidate) => intentId(candidate) === event.currentTarget.value,
					);
					if (!request) return;
					restoreCreation(request);
				}}
			>
				{chooseLegacy && !selectedRequest && (
					<option value="" disabled>
						{__("New project", "linker-tools")}
					</option>
				)}
				{requests.map((request, index) => (
					<option key={intentId(request)} value={intentId(request)}>
						{index + 1}.{" "}
						{compareOnLoad ? preliminaryRecoveryLabel(request) : request.title}
					</option>
				))}
			</select>
		</label>
	);
	const failureMessage = projectGone
		? __(
				"The project this request belonged to was deleted. Your draft is still here; creating it now starts a new project.",
				"linker-tools",
			)
		: inputContractRequired
			? __(
					"This workspace version cannot safely save all data in this project. Keep your local draft and reload the workspace before saving again.",
					"linker-tools",
				)
			: profile.current
				? __(
						"The project and load profile could not be confirmed. Try again to resume this request.",
						"linker-tools",
					)
				: __(
						"Project creation was not confirmed. Retrying uses the same request.",
						"linker-tools",
					);

	const draftNotice = draftUnavailable && (
		<Notice
			error
			focusTarget={languageIssue === "storage" ? languageNotice : undefined}
		>
			{__(
				"Your browser could not save your entries. Stay on this page to avoid losing them.",
				"linker-tools",
			)}
		</Notice>
	);

	return (
		<>
			{draftNotice}
			{languageIssue === "csv" && profileForm.file && (
				<Notice error focusTarget={languageNotice}>
					<p>
						{profileCorrection
							? __(
									"Your CSV changes are still here. Retry the import or compare without this load profile before switching languages.",
									"linker-tools",
								)
							: __(
									"Your CSV is still here. Finish this comparison or remove the file to switch languages.",
									"linker-tools",
								)}
					</p>
					{!intent.current && (
						<button
							type="button"
							className="sc-button"
							onClick={() => {
								setProfileForm(emptyHomepageProfile());
								setProfileError("");
								setLanguageIssue(null);
								const field =
									projectForm.current?.querySelector<HTMLInputElement>(
										'input[name="load_profile"]',
									);
								if (field) field.value = "";
							}}
						>
							{__("Remove CSV", "linker-tools")}
						</button>
					)}
				</Notice>
			)}
			{languageIssue === "number" && (
				<Notice error focusTarget={languageNotice}>
					{__(
						"Check the highlighted value before switching languages.",
						"linker-tools",
					)}
				</Notice>
			)}
			{renderEntry()}
		</>
	);

	function renderEntry() {
		if (compareOnLoad) {
			const disabled =
				busy ||
				creationPending ||
				recoveryDiscoveryFailed ||
				waitingForProduct ||
				(session !== null && !admitted);
			const retry = Boolean(intent.current);
			return (
				<section className="sc-main sc-direction-entry">
					<ProjectDirections
						selectedScene={scene}
						changeScene={(next) => {
							trackStart();
							setScene(next);
						}}
						inputs={inputs}
						title={title}
						changeTitle={setTitle}
						edit={edit}
						config={config ?? { locale, countries: {} }}
						validity={reportDemand}
						disabled={disabled || retry}
						roof={() =>
							admittedAction("submit", undefined, { useRoofPlan: true })
						}
						compare={
							brief.system_scope &&
							equipmentDraft(inputs).grid_phase != null &&
							!invalidDemand.size
								? () => admittedAction("submit")
								: undefined
						}
						details={() => admittedAction("details")}
					/>
					<PreliminaryOptions
						locale={locale}
						inputs={inputs}
						disabled={disabled || retry || invalidDemand.size > 0}
						choose={(direction) => admittedAction("submit", direction)}
						chooseRetrofit={(keepInverter) =>
							admittedAction("submit", "storage_addition", { keepInverter })
						}
					/>
					{pendingRequests}
					{waitingAction && (
						<p role="status">
							{__("Preparing your workspace…", "linker-tools")}
						</p>
					)}
					{(busy || creationPending) && (
						<p role="status">{__("Creating…", "linker-tools")}</p>
					)}
					{failed && (
						<Notice error>
							<p>{failureMessage}</p>
							<button
								className="sc-button"
								type="button"
								disabled={disabled || inputContractRequired}
								onClick={() => admittedAction("submit")}
							>
								{__("Retry project creation", "linker-tools")}
							</button>
						</Notice>
					)}
					{recoveryFailed && (
						<Notice error>
							{__(
								"Browser recovery is unavailable. The open request can still be retried here.",
								"linker-tools",
							)}
						</Notice>
					)}
				</section>
			);
		}
		if (!open)
			return (
				<button
					className="sc-button sc-primary"
					disabled={
						creationPending ||
						checking ||
						recoveryChecking ||
						recoveryDiscoveryFailed
					}
					onClick={() => {
						setOpen(true);
						opened?.();
					}}
				>
					{__("New project", "linker-tools")}
				</button>
			);
		const compareLabel = directComparison
			? __("Compare project options", "linker-tools")
			: __("New project", "linker-tools");
		const addressForm =
			roofEntry ||
			(failed && destination.current === "roof" && !profileCorrection);
		const editingDisabled =
			busy ||
			creationPending ||
			checking ||
			recoveryChecking ||
			recoveryDiscoveryFailed ||
			!admitted;
		const mapAction = config &&
			(addressForm ||
				(directComparison &&
					brief.system_scope !== "storage_only" &&
					(!intent.current || destination.current === "roof"))) && (
				<RoofMapAction
					config={config}
					site={brief.site}
					client={client}
					scope={scope}
					disabled={editingDisabled || inputContractRequired}
					locked={Boolean(intent.current)}
					busy={busy}
					permitted={roofPermission}
					{...(!addressForm && {
						open: () => void submit(undefined, { openRoof: true }),
					})}
				/>
			);
		const showSummary = !addressForm && (directComparison || workspaceHeading);
		const projectName = title.trim() || __("New project", "linker-tools");
		const site = [
			brief.site.location_label.trim(),
			brief.site.country_code && config?.countries[brief.site.country_code],
		]
			.filter(Boolean)
			.join(" · ");
		const form = (
			<form
				ref={projectForm}
				className={
					directComparison ? "sc-main sc-comparison-intake" : "sc-main"
				}
				aria-label={compareLabel}
				onSubmit={(event) => {
					event.preventDefault();
					const useAddress =
						event.currentTarget.querySelector<HTMLInputElement>(
							'input[name="pvgis_use_address"]',
						)?.checked ?? false;
					void submit(undefined, { useAddress });
				}}
			>
				{entryHints &&
					!intent.current &&
					(hasCarriedValues || entryHints.invalid) && (
						<Notice>
							<dl className="sc-fields">
								{entryHints.annualKwh !== null && (
									<div>
										<dt>
											{__("Annual electricity consumption", "linker-tools")}
										</dt>
										<dd>{formatDecimal(entryHints.annualKwh, locale)} kWh</dd>
									</div>
								)}
								{entryHints.pvKw !== null && (
									<div>
										<dt>{__("PV array", "linker-tools")}</dt>
										<dd>{formatDecimal(entryHints.pvKw, locale)} kWp</dd>
									</div>
								)}
								{entryHints.phase !== null && (
									<div>
										<dt>{__("Grid connection", "linker-tools")}</dt>
										<dd>
											{entryHints.phase === 3
												? __("Three-phase", "linker-tools")
												: __("Single-phase", "linker-tools")}
										</dd>
									</div>
								)}
								{entryHints.backup !== null && (
									<div>
										<dt>{__("Backup supply", "linker-tools")}</dt>
										<dd>
											{entryHints.backup === "none"
												? __("Not needed", "linker-tools")
												: __("Requested", "linker-tools")}
										</dd>
									</div>
								)}
								{entryHints.postalCode !== null && (
									<div>
										<dt>{__("Postal code", "linker-tools")}</dt>
										<dd>{entryHints.postalCode}</dd>
									</div>
								)}
								{entryHints.productId !== null && (
									<div>
										<dt>
											{product?.field === "inverter"
												? __(
														"Inverter or integrated storage system",
														"linker-tools",
													)
												: product?.field === "battery"
													? __("Battery or storage system", "linker-tools")
													: product?.field === "accessory"
														? __("Additional products", "linker-tools")
														: __("Use current product data", "linker-tools")}
										</dt>
										<dd>
											{proposed
												? `${proposed.brand} ${proposed.model}`.trim()
												: catalog.isPending
													? __("Loading product data…", "linker-tools")
													: __(
															"Product from the link is unavailable",
															"linker-tools",
														)}
										</dd>
									</div>
								)}
							</dl>
							{entryHints.invalid && (
								<p>
									{initialProject
										? __(
												"Some saved inputs cannot be carried over automatically. They are kept for reference and need review in the new project.",
												"linker-tools",
											)
										: __(
												"Some link values are invalid and have not been applied. Check the project inputs before calculating.",
												"linker-tools",
											)}
								</p>
							)}
							{!intent.current && hasCarriedValues && (
								<label className="sc-checkbox">
									<input
										type="checkbox"
										checked={useHints}
										onChange={(e) => {
											setUseHints(e.currentTarget.checked);
											const next = e.currentTarget.checked;
											const hintInputs = entryInputs(
												entryHints,
												__(
													"Values carried from a tool link. Review them for this project.",
													"linker-tools",
												),
												__(
													"Backup supply requested; accessories may be considered.",
													"linker-tools",
												),
												product,
											);
											const hintBrief = readBrief(hintInputs.brief);
											const empty = emptyBrief();
											const currentBrief = readBrief(inputs.brief);
											const matchedBrief = next ? empty : hintBrief;
											const replacement = next ? hintBrief : empty;
											const edited = {
												...inputs,
												brief: {
													...currentBrief,
													site: {
														...currentBrief.site,
														location_label:
															currentBrief.site.location_label ===
															matchedBrief.site.location_label
																? replacement.site.location_label
																: currentBrief.site.location_label,
													},
													annual_load: sameJson(
														currentBrief.annual_load,
														matchedBrief.annual_load,
													)
														? replacement.annual_load
														: currentBrief.annual_load,
													project_note:
														currentBrief.project_note ===
														matchedBrief.project_note
															? replacement.project_note
															: currentBrief.project_note,
												},
											};
											setDraft(
												reviseCarriedEquipment(edited, hintInputs, next),
											);
											setCarriedProduct(next);
										}}
									/>
									{__("Use these values for the new project", "linker-tools")}
								</label>
							)}
						</Notice>
					)}
				{pendingRequests}
				{demandError && (
					<Notice error>
						{__(
							"Choose a project type and purpose. For backup, enter the load and how long it must run.",
							"linker-tools",
						)}
					</Notice>
				)}
				{profileError && <Notice error>{profileError}</Notice>}
				{referenceError && (
					<Notice error>
						{referenceError === "addressService"
							? __(
									"Address search is unavailable right now. Your details are still here; please try again.",
									"linker-tools",
								)
							: referenceError === "location"
								? __(
										"The location could not be found. Check the country and address, then try again.",
										"linker-tools",
									)
								: __(
										"Complete the site coordinates, array details and PVGIS settings to compare systems.",
										"linker-tools",
									)}
					</Notice>
				)}
				{addressForm && config ? (
					<RoofStart
						config={config}
						site={brief.site}
						disabled={editingDisabled || inputContractRequired}
						locked={Boolean(intent.current)}
						action={mapAction}
						compareSite={() =>
							void submit(undefined, { compareRoofSite: true })
						}
						openPlan={() => {
							roofPermission.current = null;
							void submit(undefined, { useRoofPlan: true });
						}}
						change={(site) =>
							edit((current) => ({ ...current, brief: { ...brief, site } }))
						}
					/>
				) : (
					<ProjectDetails
						inputs={inputs}
						config={config ?? { locale, countries: {} }}
						disabled={editingDisabled}
						roofAction={mapAction}
						edit={edit}
						creation={{
							...(returnToComparison &&
								!profileForm.file && {
									returnToComparison,
									comparisonDisabled: invalidDemand.has("annual"),
								}),
							title,
							changeTitle: setTitle,
							locked: Boolean(intent.current),
							submitDisabled: waitingForProduct,
							comparison: directComparison,
							preliminary: directComparison,
							...(busy
								? {
										submitLabel: directComparison
											? __("Preparing comparison…", "linker-tools")
											: __("Creating…", "linker-tools"),
									}
								: failed
									? {
											submitLabel: directComparison
												? __("Try again", "linker-tools")
												: __("Retry project creation", "linker-tools"),
										}
									: directComparison
										? { submitLabel: __("Compare systems", "linker-tools") }
										: {}),
						}}
						demand={
							directComparison ? (
								<HomepageDemand
									inputs={inputs}
									brief={brief}
									locale={locale}
									addressLookup={Boolean(config?.googleMapsApiKey)}
									usePvAddress={restored?.usePvAddress ?? false}
									edit={edit}
									validity={reportDemand}
								/>
							) : returnToComparison ? (
								<div className="sc-fields">
									<AnnualElectricityUse
										brief={brief}
										locale={locale}
										edit={edit}
										validity={reportDemand}
									/>
								</div>
							) : undefined
						}
						profile={
							directComparison &&
							(!intent.current || profileCorrection) && (
								<HomepageLoadProfile
									form={profileForm}
									locale={locale}
									disabled={busy || checking || !admitted}
									change={changeProfile}
									{...(profileCorrection && {
										discard: () =>
											void submit(undefined, { discardProfile: true }),
									})}
								/>
							)
						}
						equipmentFirst={equipmentFirst}
						existingEquipment={
							config && (
								<ProjectEquipment
									inputs={inputs}
									client={client}
									scope={scope}
									disabled={busy || Boolean(intent.current)}
									edit={edit}
									initiallyOpen={equipmentFirst}
								/>
							)
						}
					/>
				)}
				{cancelled && !intent.current && (
					<button
						className="sc-button"
						type="button"
						disabled={busy}
						onClick={cancelled}
					>
						{__("Cancel", "linker-tools")}
					</button>
				)}
				{failed && <Notice error>{failureMessage}</Notice>}

				{recoveryFailed && (
					<Notice error>
						{__(
							"Browser recovery is unavailable. The open request can still be retried here.",
							"linker-tools",
						)}
					</Notice>
				)}
			</form>
		);
		const detailsForm = (
			<Suspense
				fallback={
					<p role="status">{__("Opening the project…", "linker-tools")}</p>
				}
			>
				{form}
			</Suspense>
		);
		if (!showSummary) return detailsForm;
		return (
			<>
				{workspaceHeading && (
					<ProjectHeading title={projectName} location={site} />
				)}
				<div className="sc-layout sc-intake-layout">
					{detailsForm}
					<ProjectSummary
						title={projectName}
						facts={[
							[
								__("Planned system", "linker-tools"),
								brief.system_scope
									? systemNames()[brief.system_scope]
									: __("Not specified", "linker-tools"),
							],
							...projectFacts(inputs, locale),
						]}
					/>
				</div>
			</>
		);
	}
}

function preliminaryRecoveryLabel(record: ScopedCreation): string {
	const inputs = readObject(JSON.parse(record.body).inputs);
	const scope = readBrief(inputs.brief ?? emptyBrief()).system_scope;
	return scope ? systemNames()[scope] : record.title;
}

function withProduct(
	inputs: JsonObject,
	product: NonNullable<ReturnType<typeof placedProduct>>,
): JsonObject {
	const setup = equipmentDraft(inputs);
	if (product.field === "accessory") {
		const ids = setup.accessory_product_ids as readonly number[];
		return ids.includes(product.id)
			? inputs
			: changeEquipment(inputs, {
					accessory_product_ids: [...ids, product.id],
				});
	}
	const field =
		product.field === "inverter" ? "inverter_product_id" : "battery_product_id";
	return setup[field] === null
		? changeEquipment(inputs, { [field]: product.id })
		: inputs;
}

function reviseCarriedEquipment(
	inputs: JsonObject,
	hints: JsonObject,
	include: boolean,
): JsonObject {
	if (
		inputs.equipment_plant_setup !== undefined ||
		inputs.equipment_plant !== undefined ||
		hints.equipment_setup === undefined
	)
		return inputs;
	const current = equipmentDraft(inputs);
	const carried = equipmentDraft(hints);
	const blank = equipmentDraft({});
	const from = include ? blank : carried;
	const to = include ? carried : blank;
	const fields = [
		"pv_dc_kw",
		"grid_phase",
		"inverter_product_id",
		"battery_product_id",
		"accessory_product_ids",
	] as const;
	const patch = Object.fromEntries(
		fields
			.filter(
				(field) =>
					sameJson(current[field], from[field]) &&
					!sameJson(from[field], to[field]),
			)
			.map((field) => [field, to[field]!]),
	);
	let updated = Object.keys(patch).length
		? changeEquipment(inputs, patch)
		: inputs;
	if (carried.operating_mode === "backup") {
		if (include && !energyGoal(updated))
			updated = changeEnergyGoal(updated, "backup");
		if (
			!include &&
			energyGoal(updated) === "backup" &&
			sameJson(updated.backup_demand, {
				schema_version: 1,
				load_kw: null,
				duration_hours: null,
			})
		) {
			const { backup_demand, energy_scenario, ...rest } = updated;
			updated = changeEquipment(rest, { operating_mode: null });
		}
	} else if (
		carried.operating_mode === "grid_connected" &&
		!energyGoal(updated) &&
		current.operating_mode === from.operating_mode
	) {
		updated = changeEquipment(updated, { operating_mode: to.operating_mode! });
	}
	return updated;
}
