import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
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
import { ProjectDetails } from "./configurator/ProjectDetails.tsx";
import { ProjectEquipment } from "./configurator/ProjectEquipment.tsx";
import {
	HomepageDemand,
	hasComparisonDemand,
} from "./configurator/HomepageDemand.tsx";
import {
	isHomepagePvReferenceReady,
	prepareHomepagePvReference,
} from "./configurator/HomepagePvReference.tsx";
import { changeEnergyGoal, energyGoal } from "./configurator/EnergyDemand.tsx";

import {
	PreliminaryOptions,
	systemNames,
} from "./configurator/PreliminaryOptions.tsx";

export function NewProject({
	session,
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
	enterDetails,
	hidden = false,
	creationPending = false,
	beginCreation,
	homeComparison,
}: {
	session: Session;
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
	enterDetails?: () => void;
	hidden?: boolean;
	creationPending?: boolean;
	beginCreation?: () => (() => void) | null;
	homeComparison?: {
		picker: ReactNode;
		savedProject: string;
		compareSaved: (projectId: string) => void;
	};
}) {
	const compareAtHome = Boolean(homeComparison);
	const [open, setOpen] = useState(
		Boolean(entryHints || initialProject || openOnLoad || compareOnLoad),
	);
	const openedOnLoad = useRef(openOnLoad);
	const [useHints, setUseHints] = useState(true);
	const [title, setTitle] = useState(initialProject?.title ?? "");
	const [busy, setBusy] = useState(false);
	const [failed, setFailed] = useState(false);
	const [inputContractRequired, setInputContractRequired] = useState(false);
	const [projectGone, setProjectGone] = useState(false);
	const [recoveryFailed, setRecoveryFailed] = useState(false);
	const [demandError, setDemandError] = useState(false);
	const [referenceError, setReferenceError] = useState<
		"settings" | "location" | null
	>(null);
	const [profileForm, setProfileForm] = useState(emptyHomepageProfile);
	const [profileError, setProfileError] = useState("");
	const [profileCorrection, setProfileCorrection] = useState(false);
	const profile = useRef<HomepageProfileUpload | undefined>(undefined);
	const changeProfile = useCallback((patch: Partial<HomepageProfileForm>) => {
		setProfileForm((current) => ({ ...current, ...patch }));
		if (patch.mappingValid === undefined) setProfileError("");
	}, []);
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
		session.query_scope,
		!hidden && Boolean(entryHints?.productId),
	);
	const [draft, setDraft] = useState<JsonObject | null>(null);
	const [carriedProduct, setCarriedProduct] = useState(true);
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
				compareOnLoad || compareAtHome
					? seedBrief.system_scope
					: (seedBrief.system_scope ?? "new_pv_storage"),
		},
	};
	const seeded =
		useHints && entryHints?.backup && entryHints.backup !== "none"
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
		if (busy || intent.current || !client.isCurrentScope(session.query_scope))
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
		setDemandError(false);
		setReferenceError(null);
		return true;
	}
	const [checking, setChecking] = useState(true);
	const [requests, setRequests] = useState<readonly ScopedCreation[]>([]);
	const intent = useRef<string | null>(null);
	const intentScope = useRef(session.query_scope);
	const destination = useRef<CreationDestination | null>(null);
	const lifetime = useRef(0);
	const sending = useRef(false);
	const openWork = useRef(false);
	openWork.current = Boolean(
		intent.current || draft || (title && title !== initialProject?.title),
	);
	const admitted = client.isCurrentScope(session.query_scope);
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
	}, [session.query_scope]);
	useEffect(() => {
		if (hidden || recoveryChecking || !admitted) return;
		let active = true;
		setChecking(true);
		void creationIntents(store, recoveryScopes ?? [session.query_scope])
			.then((records) => {
				if (!active || !client.isCurrentScope(session.query_scope)) return;
				const matching = records.filter((record) => {
					if (compareAtHome) return record.destination === "guided-comparison";
					return (
						record.destination !== "guided-comparison" &&
						(record.destination === "preliminary-review") === compareOnLoad
					);
				});
				setRequests(matching);
				if (openWork.current || !matching[0]) return;
				restoreCreation(matching[0]);
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
		session.query_scope,
		store,
		recoveryScopes,
		recoveryChecking,
		compareOnLoad,
		compareAtHome,
		hidden,
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
		{ discardProfile = false, useAddress = false } = {},
	) {
		if (
			sending.current ||
			creationPending ||
			checking ||
			recoveryChecking ||
			recoveryDiscoveryFailed ||
			waitingForProduct ||
			!client.isCurrentScope(session.query_scope) ||
			(!intent.current && !direction && (!title.trim() || !brief.system_scope))
		)
			return;
		if (compareAtHome && !intent.current) {
			const goal = energyGoal(inputs);
			const invalidVisible =
				invalidDemand.has("annual") ||
				(invalidDemand.has("pv") &&
					brief.system_scope !== "storage_only" &&
					!hasPlant(inputs)) ||
				(goal === "backup" &&
					(invalidDemand.has("load") || invalidDemand.has("duration"))) ||
				(goal === "peak" && invalidDemand.has("peak"));
			if (!hasComparisonDemand(inputs, brief) || invalidVisible) {
				setDemandError(true);
				return;
			}
			if (!isHomepagePvReferenceReady(inputs, brief, useAddress)) {
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
			compareAtHome && (!intent.current || profileCorrection);
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
		if (!intent.current) intentScope.current = session.query_scope;
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
				let submittedInputs = inputs;
				if (compareAtHome && useAddress) {
					try {
						submittedInputs = await prepareHomepagePvReference(
							inputs,
							config ?? { locale },
							useAddress,
						);
					} catch {
						if (lifetime.current === instance) setReferenceError("location");
						return;
					}
					if (lifetime.current !== instance) return;
				}
				const submittedBrief = readBrief(submittedInputs.brief);
				intent.current = wire(
					{
						schema_version: 1,
						input_contract: projectInputContract,
						title: title.trim() || __("New project", "linker-tools"),
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
				destination.current = compareAtHome
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
				.catch((error: unknown) => {
					if (lifetime.current === instance) setRecoveryFailed(true);
					if (previousProfile) throw error;
				});
			if (lifetime.current !== instance) return;
			profile.current = nextProfile;
			setProfileCorrection(false);
			if (!client.isCurrentScope(session.query_scope)) {
				setFailed(true);
				return;
			}
			let project = readProject(
				await client.send(
					"projects/create",
					intent.current,
					session.query_scope,
				),
			);
			if (lifetime.current !== instance) return;
			creationConfirmed = true;
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
				!created(
					project,
					destination.current ??
						(createdBrief?.system_scope === "storage_only"
							? "energy"
							: undefined),
					location.href === submittedFrom,
				)
			) {
				setFailed(true);
				return;
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
	const pendingRequests = requests.length > 1 && (
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

	if (hidden) return null;
	if (compareOnLoad) {
		const disabled =
			busy ||
			creationPending ||
			checking ||
			recoveryChecking ||
			recoveryDiscoveryFailed ||
			waitingForProduct ||
			!admitted;
		const retry = Boolean(intent.current);
		return (
			<section className="sc-main">
				<PreliminaryOptions
					inputs={inputs}
					disabled={disabled || retry}
					choose={(direction) => void submit(direction)}
					action={
						enterDetails && (
							<button
								className="sc-button"
								type="button"
								disabled={disabled || retry}
								onClick={enterDetails}
							>
								{__("Enter project details", "linker-tools")}
							</button>
						)
					}
				/>
				{pendingRequests}
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
							onClick={() => void submit()}
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
				onClick={() => setOpen(true)}
			>
				{__("New project", "linker-tools")}
			</button>
		);
	const compareLabel = compareAtHome
		? __("Compare project options", "linker-tools")
		: __("New project", "linker-tools");
	const showSavedPicker =
		!busy &&
		!checking &&
		!recoveryChecking &&
		!recoveryDiscoveryFailed &&
		!intent.current;
	if (homeComparison?.savedProject && showSavedPicker) {
		return (
			<form
				className="sc-main"
				aria-label={compareLabel}
				onSubmit={(event) => {
					event.preventDefault();
					homeComparison.compareSaved(homeComparison.savedProject);
				}}
			>
				{homeComparison.picker}
				<button className="sc-button sc-primary" type="submit">
					{__("Compare systems", "linker-tools")}
				</button>
			</form>
		);
	}
	return (
		<form
			className="sc-main"
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
			{showSavedPicker && homeComparison?.picker}
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
							<label className="lp-checkbox">
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
										setDraft(reviseCarriedEquipment(edited, hintInputs, next));
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
						"Choose the project type, purpose and grid connection. For backup, enter the load and how long it must run.",
						"linker-tools",
					)}
				</Notice>
			)}
			{profileError && <Notice error>{profileError}</Notice>}
			{referenceError && (
				<Notice error>
					{referenceError === "location"
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
			<ProjectDetails
				inputs={inputs}
				config={config ?? { locale, countries: {} }}
				disabled={
					busy ||
					creationPending ||
					checking ||
					recoveryChecking ||
					recoveryDiscoveryFailed ||
					!admitted
				}
				edit={edit}
				creation={{
					title,
					changeTitle: setTitle,
					locked: Boolean(intent.current),
					submitDisabled: waitingForProduct,
					comparison: compareAtHome,
					...(busy
						? {
								submitLabel: compareAtHome
									? __("Preparing comparison…", "linker-tools")
									: __("Creating…", "linker-tools"),
							}
						: failed
							? {
									submitLabel: compareAtHome
										? __("Try again", "linker-tools")
										: __("Retry project creation", "linker-tools"),
								}
							: compareAtHome
								? { submitLabel: __("Compare systems", "linker-tools") }
								: {}),
				}}
				demand={
					compareAtHome && (
						<HomepageDemand
							inputs={inputs}
							brief={brief}
							locale={locale}
							addressLookup={Boolean(config?.googleMapsApiKey)}
							edit={edit}
							validity={reportDemand}
						/>
					)
				}
				profile={
					compareAtHome &&
					(!intent.current || profileCorrection) && (
						<HomepageLoadProfile
							form={profileForm}
							locale={locale}
							disabled={busy || checking || !admitted}
							change={changeProfile}
							{...(profileCorrection && {
								discard: () => void submit(undefined, { discardProfile: true }),
							})}
						/>
					)
				}
				existingEquipment={
					config && (
						<ProjectEquipment
							inputs={inputs}
							client={client}
							scope={session.query_scope}
							disabled={busy || Boolean(intent.current)}
							edit={edit}
							intake={compareAtHome}
						/>
					)
				}
			/>
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
