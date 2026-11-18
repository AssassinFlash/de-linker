import {
	type ReactNode,
	useCallback,
	useEffect,
	useRef,
	useState,
} from "react";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { JsonObject, Project, Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import type { CreationDestination, DraftStore } from "../data/DraftStore.ts";
import { creationIntents, intentId } from "../data/recoveryIntents.ts";
import type { ScopedCreation } from "../data/recoveryIntents.ts";
import { readObject, readProject, wire } from "../data/readProtocol.ts";
import { type Brief, emptyBrief, readBrief } from "../domain/brief.ts";
import { changeEquipment, equipmentDraft } from "../domain/equipment.ts";
import { hasPlant } from "../domain/equipmentPlant.ts";
import { projectInputContract, sameJson } from "../domain/draft.ts";
import { __ } from "../i18n.ts";
import { Notice } from "./Notice.tsx";
import { useEquipmentProducts } from "../data/equipmentProducts.ts";
import { entryInputs, placedProduct } from "../domain/entryHints.ts";
import type { EntryHints } from "../domain/entryHints.ts";
import { formatDecimal } from "../domain/decimal.ts";
import type { Configuration } from "../data/config.ts";
import { ConfiguratorSteps } from "./configurator/ConfiguratorSteps.tsx";
import {
	hasStorageToExclude,
	ProjectDetails,
} from "./configurator/ProjectDetails.tsx";
import { ProjectEquipment } from "./configurator/ProjectEquipment.tsx";
import { ProjectInputsStep } from "./configurator/ProjectInputsStep.tsx";
import { SolarInstallation } from "./configurator/SolarInstallation.tsx";
import {
	EnergyDemand,
	changeEnergyGoal,
	energyGoal,
} from "./configurator/EnergyDemand.tsx";

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
	briefEntry,
	initialProject = null,
	cancelled,
	locale = "en",
	config,
}: {
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	created: (
		project: Project,
		destination?: CreationDestination,
		comparisonInputs?: JsonObject,
	) => boolean;
	recheck: () => void;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	recoveryDiscoveryFailed?: boolean;
	entryHints?: EntryHints | null;
	briefEntry?: {
		note: string;
		flush: () => Promise<boolean>;
		render: (
			disabled: boolean,
			apply: (hints: JsonObject) => boolean,
		) => ReactNode;
	};
	initialProject?: { title: string; inputs: JsonObject } | null;
	cancelled?: () => void;
	locale?: string;
	config?: Configuration;
}) {
	const [useHints, setUseHints] = useState(true);
	const [title, setTitle] = useState(initialProject?.title ?? "");
	const [busy, setBusy] = useState(false);
	const [failed, setFailed] = useState(false);
	const [inputContractRequired, setInputContractRequired] = useState(false);
	const [projectGone, setProjectGone] = useState(false);
	const [recoveryFailed, setRecoveryFailed] = useState(false);
	const catalog = useEquipmentProducts(
		client,
		session.query_scope,
		Boolean(entryHints?.productId),
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
				seedBrief.system_scope ?? (entryHints?.roof ? "new_pv_storage" : null),
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
		return true;
	}
	const [detailsReady, setDetailsReady] = useState(true);
	const [comparingDirections, setComparingDirections] = useState(false);
	const optionsHeading = useRef<HTMLHeadingElement>(null);
	useEffect(() => {
		if (comparingDirections) optionsHeading.current?.focus();
	}, [comparingDirections]);
	const [importOpen, setImportOpen] = useState(false);
	const [roofEditing, setRoofEditing] = useState(false);
	const provisioned = useRef<Project | null>(null);
	const [checking, setChecking] = useState(true);
	const [requests, setRequests] = useState<readonly ScopedCreation[]>([]);
	const intent = useRef<string | null>(null);
	const intentScope = useRef(session.query_scope);
	const destination = useRef<CreationDestination | null>(null);
	const projectForm = useRef<HTMLFormElement>(null);
	const energySection = useRef<HTMLDivElement>(null);
	const lifetime = useRef(0);
	const sending = useRef(false);
	const openWork = useRef(false);
	openWork.current = Boolean(
		intent.current ||
		draft ||
		(briefEntry && briefEntry.note !== seedBrief.project_note) ||
		(title && title !== initialProject?.title),
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
		lifetime.current++;
		return () => {
			lifetime.current++;
		};
	}, [session.query_scope]);
	useEffect(() => {
		if (recoveryChecking || !admitted) return;
		let active = true;
		setChecking(true);
		void creationIntents(store, recoveryScopes ?? [session.query_scope])
			.then((records) => {
				if (
					!active ||
					!client.isCurrentScope(session.query_scope) ||
					!records.length
				)
					return;
				setRequests(records);
				if (openWork.current) return;
				intent.current = records[0]!.body;
				intentScope.current = records[0]!.scope;
				destination.current = records[0]!.destination;
				setTitle(records[0]!.title);
				setRecoveredInputs(readObject(JSON.parse(records[0]!.body).inputs));
				setFailed(true);
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
	]);
	async function submit(
		action: "compare" | "edit" | "review",
		direction?: NonNullable<Brief["system_scope"]>,
	) {
		if (
			sending.current ||
			checking ||
			recoveryChecking ||
			recoveryDiscoveryFailed ||
			waitingForProduct ||
			!detailsReady ||
			roofEditing ||
			!client.isCurrentScope(session.query_scope) ||
			(!intent.current &&
				!direction &&
				(!projectForm.current?.reportValidity() || !brief.system_scope))
		)
			return;
		const instance = lifetime.current;
		if (!intent.current) intentScope.current = session.query_scope;
		const originScope = intentScope.current;

		sending.current = true;
		setBusy(true);
		setFailed(false);
		setProjectGone(false);
		setInputContractRequired(false);
		try {
			if (
				!intent.current &&
				briefEntry &&
				(!(await briefEntry.flush()) ||
					lifetime.current !== instance ||
					!client.isCurrentScope(session.query_scope))
			) {
				if (lifetime.current === instance) setComparingDirections(false);
				return;
			}
			const currentInputs = {
				...inputs,
				brief: {
					...brief,
					...(direction && { system_scope: direction }),
					...(briefEntry && { project_note: briefEntry.note }),
					site: {
						...brief.site,
						location_label: brief.site.location_label.trim(),
					},
				},
			};
			if (provisioned.current) {
				if (action === "compare")
					created(provisioned.current, "compare", currentInputs);
				return provisioned.current;
			}
			if (!intent.current) {
				intent.current = wire(
					{
						schema_version: 1,
						input_contract: projectInputContract,
						title: projectName.slice(0, 256),
						inputs: currentInputs,
						key: crypto.randomUUID(),
					},
					session.runtime.limits.max_json_depth,
					session.runtime.limits.max_body_bytes,
				);
				destination.current = action;
			}
			await store
				.writeCreation(originScope, intent.current, destination.current)
				.catch(() => {
					if (lifetime.current === instance) setRecoveryFailed(true);
				});
			if (lifetime.current !== instance) return;
			if (!client.isCurrentScope(session.query_scope)) {
				setFailed(true);
				return;
			}
			const project = readProject(
				await client.send(
					"projects/create",
					intent.current,
					session.query_scope,
				),
			);
			await store.clearCreation(originScope, intent.current).catch(() => {
				if (lifetime.current === instance) setRecoveryFailed(true);
			});
			if (
				lifetime.current !== instance ||
				!client.isCurrentScope(session.query_scope)
			)
				return;
			const target = destination.current;
			if (target === "edit") {
				provisioned.current = project;
				setDraft(project.inputs);
				setTitle(project.title);
				// Reload or language navigation can now resume this same owned project.
				created(project, "edit");
			} else if (
				!created(
					project,
					target ??
						(readBrief(project.inputs.brief ?? emptyBrief()).system_scope ===
						"storage_only"
							? "energy"
							: undefined),
				)
			) {
				setFailed(true);
				return;
			}
			intent.current = null;
			destination.current = null;
			setRecoveredInputs(null);
			return project;
		} catch (error) {
			if (lifetime.current !== instance) return;
			setComparingDirections(false);
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
			sending.current = false;
			if (lifetime.current === instance) setBusy(false);
		}
	}
	const resolveProject = useRef(submit);
	resolveProject.current = submit;
	const ensureProjectId = useCallback(async () => {
		const project =
			provisioned.current ?? (await resolveProject.current("edit"));
		if (!project) throw new Error("project_creation_not_confirmed");
		return project.id;
	}, []);
	const locked =
		busy ||
		checking ||
		recoveryChecking ||
		recoveryDiscoveryFailed ||
		!admitted;
	function compare() {
		if (
			!detailsReady ||
			roofEditing ||
			importOpen ||
			!projectForm.current?.reportValidity()
		)
			return;
		void submit("compare");
	}
	function openDirections() {
		if (
			!locked &&
			!waitingForProduct &&
			detailsReady &&
			projectForm.current?.reportValidity()
		)
			setComparingDirections(true);
	}
	function continueProject() {
		if (intent.current) void submit("compare");
		else if (!brief.system_scope && !provisioned.current) openDirections();
		else
			energySection.current
				?.querySelector<HTMLButtonElement>("footer button.sc-primary")
				?.click();
	}
	const selectedRequest = requests.find(
		(request) =>
			request.body === intent.current && request.scope === intentScope.current,
	);
	const projectName =
		title.trim() ||
		brief.site.location_label.trim() ||
		__("New project", "linker-tools");
	const country = brief.site.country_code
		? config?.countries[brief.site.country_code]
		: undefined;
	const site = [brief.site.location_label.trim(), country]
		.filter(Boolean)
		.join(" · ");
	const showDirections = comparingDirections && !intent.current;
	const systemDescriptions = {
		new_pv_storage: __(
			"Plan panels and a battery together to use solar power after sunset. Panel area and electricity use will help size both.",
			"linker-tools",
		),
		storage_addition: __(
			"Store surplus power from an existing solar array. The existing inverter determines how a battery can be connected.",
			"linker-tools",
		),
		pv_only: __(
			"Generate electricity with solar panels alone. Available panel area and daytime electricity use guide the array size.",
			"linker-tools",
		),
		storage_only: __(
			"Plan a battery without adding solar panels. Electricity use and the charging source guide battery sizing.",
			"linker-tools",
		),
	};
	const systemNames = {
		new_pv_storage: __("Solar and storage", "linker-tools"),
		storage_addition: __("Storage for existing PV", "linker-tools"),
		pv_only: __("Solar", "linker-tools"),
		storage_only: __("Storage", "linker-tools"),
	};
	return (
		<>
			<header className="sc-project-heading">
				<div>
					<p className="sc-eyebrow">{__("Your project", "linker-tools")}</p>
					<h1>{projectName}</h1>
					{site && <p>{site}</p>}
				</div>
			</header>
			<ConfiguratorSteps active={showDirections ? "system" : "project"} />
			<div className="sc-layout">
				{showDirections && (
					<section className="sc-card">
						<header className="sc-section-head">
							<div>
								<h2 ref={optionsHeading} tabIndex={-1}>
									{__("Preliminary options", "linker-tools")}
								</h2>
								<p>
									{__(
										"Choose the direction you want to discuss. System size, grid connection and equipment compatibility still need to be confirmed.",
										"linker-tools",
									)}
								</p>
							</div>
						</header>
						<div className="sc-fields">
							{(Object.keys(systemNames) as (keyof typeof systemNames)[])
								.filter(
									(scope) =>
										(scope !== "pv_only" || !hasStorageToExclude(inputs)) &&
										(scope !== "storage_only" ||
											(!inputs.pv_string_plan && !inputs.pv_plant_string_plan)),
								)
								.map((scope) => (
									<article key={scope} className="sc-package">
										<h3 id={`sc-direction-${scope}`}>{systemNames[scope]}</h3>
										<p>{systemDescriptions[scope]}</p>
										<button
											type="button"
											className="sc-button sc-primary"
											disabled={locked}
											aria-describedby={`sc-direction-${scope}`}
											onClick={() => void submit("review", scope)}
										>
											{__("Choose this option", "linker-tools")}
										</button>
									</article>
								))}
						</div>
						<footer className="sc-footer">
							<button
								type="button"
								className="sc-button"
								disabled={locked}
								onClick={() => setComparingDirections(false)}
							>
								{__("Back to project", "linker-tools")}
							</button>
						</footer>
					</section>
				)}
				<div className="sc-main" hidden={showDirections}>
					{!brief.system_scope && !provisioned.current && !intent.current && (
						<section className="sc-card">
							<header className="sc-section-head">
								<div>
									<h2>{__("Explore system options", "linker-tools")}</h2>
									<p>
										{__(
											"Compare solar and storage options now, or enter project details below for an equipment comparison.",
											"linker-tools",
										)}
									</p>
								</div>
							</header>
							<button
								type="button"
								className="sc-button sc-primary"
								disabled={locked || !detailsReady || waitingForProduct}
								onClick={openDirections}
							>
								{__("Compare preliminary options", "linker-tools")}
							</button>
						</section>
					)}
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
					{!intent.current &&
						briefEntry?.render(
							busy || checking || recoveryChecking || !admitted,
							(hints) =>
								edit((current) => {
									const b = readBrief(current.brief);
									const carried = readBrief(hints.brief);
									return reviseCarriedEquipment(
										{
											...current,
											brief: {
												...b,
												annual_load:
													b.annual_load.kwh === null
														? carried.annual_load
														: b.annual_load,
												site: {
													...b.site,
													location_label:
														b.site.location_label ||
														carried.site.location_label,
												},
											},
										},
										hints,
										true,
									);
								}),
						)}
					{requests.length > 1 && (
						<label className="sc-field">
							<span>{__("Unconfirmed project creations", "linker-tools")}</span>
							<select
								disabled={busy}
								value={selectedRequest ? intentId(selectedRequest) : ""}
								onChange={(event) => {
									const request = requests.find(
										(candidate) =>
											intentId(candidate) === event.currentTarget.value,
									);
									if (!request) return;
									intent.current = request.body;
									intentScope.current = request.scope;
									destination.current = request.destination;
									setTitle(request.title);
									setRecoveredInputs(
										readObject(JSON.parse(request.body).inputs),
									);
									setFailed(true);
								}}
							>
								{requests.map((request, index) => (
									<option key={intentId(request)} value={intentId(request)}>
										{index + 1}. {request.title}
									</option>
								))}
							</select>
						</label>
					)}
					<ProjectInputsStep
						focusSection={entryHints?.roof ? "solar" : null}
						details={
							<form
								ref={projectForm}

								aria-label={__("New project", "linker-tools")}
								onSubmit={(event) => {
									event.preventDefault();
									continueProject();
								}}
							>
								<ProjectDetails
									embedded
									onReady={setDetailsReady}
									inputs={inputs}
									config={config ?? { locale, countries: {} }}
									disabled={locked}
									edit={edit}
									creation={{
										title,
										changeTitle: setTitle,
										locked: Boolean(intent.current),
										titleLocked: Boolean(provisioned.current),
									}}
									existingEquipment={
										config && (
											<ProjectEquipment
												inputs={inputs}
												client={client}
												scope={session.query_scope}
												disabled={locked || Boolean(intent.current)}
												edit={edit}
											/>
										)
									}
								/>
							</form>
						}
						solar={
							config &&
							brief.system_scope &&
							brief.system_scope !== "storage_only" && (
								<SolarInstallation
									inputs={inputs}
									config={config}
									client={client}
									session={session}
									disabled={locked || Boolean(intent.current)}
									edit={edit}
									initialMap={Boolean(entryHints?.roof)}
									onEditing={setRoofEditing}
									geometryImport={{
										projectId: provisioned.current?.id ?? ensureProjectId,
										recheck,
										confirmedInputs: provisioned.current?.inputs ?? inputs,
										onActivity: setImportOpen,
										recoveryScopes,
										recoveryChecking,
									}}
								/>
							)
						}
						energy={
							brief.system_scope && (
								<div ref={energySection}>
									<EnergyDemand
										embedded
										projectId={ensureProjectId}
										inputs={inputs}
										locale={locale}
										disabled={
											locked ||
											Boolean(intent.current) ||
											waitingForProduct ||
											roofEditing ||
											importOpen ||
											!detailsReady
										}
										edit={edit}
										compare={compare}
										client={client}
										session={session}
										recheck={recheck}
									/>
								</div>
							)
						}
					/>
					{intent.current && (
						<button
							type="button"
							onClick={() => void submit("compare")}
							className="sc-button sc-primary"
							disabled={locked}
						>
							{__("Retry project creation", "linker-tools")}
						</button>
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
					{failed && (
						<Notice error>
							{projectGone
								? __(
										"The project this request belonged to was deleted. Your draft is still here; creating it now starts a new project.",
										"linker-tools",
									)
								: inputContractRequired
									? __(
											"This workspace version cannot safely save all data in this project. Keep your local draft and reload the workspace before saving again.",
											"linker-tools",
										)
									: __(
											"Project creation was not confirmed. Retrying uses the same request.",
											"linker-tools",
										)}
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
				</div>
				<aside className="sc-sidebar">
					<section className="sc-card">
						<div>
							<p className="sc-eyebrow">
								{__("Current configuration", "linker-tools")}
							</p>
							<h3>{projectName}</h3>
						</div>
						<dl>
							{brief.system_scope && (
								<div>
									<dt>{__("Planned system", "linker-tools")}</dt>
									<dd>{systemNames[brief.system_scope]}</dd>
								</div>
							)}
							{site && (
								<div>
									<dt>{__("Town or site", "linker-tools")}</dt>
									<dd>{site}</dd>
								</div>
							)}
						</dl>
					</section>
				</aside>
			</div>
		</>
	);
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
