import { useEffect, useRef, useState } from "react";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { JsonObject, Project, Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import type { DraftStore } from "../data/DraftStore.ts";
import { creationIntents, intentId } from "../data/recoveryIntents.ts";
import type { ScopedCreation } from "../data/recoveryIntents.ts";
import { readProject, wire } from "../data/readProtocol.ts";
import { emptyBrief } from "../domain/brief.ts";
import { projectInputContract } from "../domain/draft.ts";
import { __ } from "../i18n.ts";
import { Icon } from "./Icon.tsx";
import { Notice } from "./Notice.tsx";
import { useEquipmentProducts } from "../data/equipmentProducts.ts";
import { entryInputs, placedProduct } from "../domain/entryHints.ts";
import type { EntryHints } from "../domain/entryHints.ts";
import { formatDecimal } from "../domain/decimal.ts";

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
}: {
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	created: (project: Project, destination?: "design" | "equipment") => boolean;
	recheck: () => void;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	recoveryDiscoveryFailed?: boolean;
	entryHints?: EntryHints | null;
	initialProject?: { title: string; inputs: JsonObject } | null;
	cancelled?: () => void;
	locale?: string;
}) {
	const [open, setOpen] = useState(Boolean(entryHints || initialProject));
	const [useHints, setUseHints] = useState(true);
	const [title, setTitle] = useState(initialProject?.title ?? "");
	const [busy, setBusy] = useState(false);
	const [failed, setFailed] = useState(false);
	const [inputContractRequired, setInputContractRequired] = useState(false);
	const [recoveryFailed, setRecoveryFailed] = useState(false);
	const [productBlocked, setProductBlocked] = useState<
		"load" | "preparing" | "place" | null
	>(null);
	const catalog = useEquipmentProducts(
		client,
		session.query_scope,
		Boolean(entryHints?.productId),
	);
	const [checking, setChecking] = useState(true);
	const [requests, setRequests] = useState<readonly ScopedCreation[]>([]);
	const intent = useRef<string | null>(null);
	const intentScope = useRef(session.query_scope);
	const lifetime = useRef(0);
	const openWork = useRef(false);
	openWork.current = Boolean(
		intent.current || (title && title !== initialProject?.title),
	);
	const admitted = client.isCurrentScope(session.query_scope);
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
				setTitle(records[0]!.title);
				setOpen(true);
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
	async function submit() {
		if (
			busy ||
			checking ||
			recoveryChecking ||
			recoveryDiscoveryFailed ||
			!title.trim()
		)
			return;
		const instance = lifetime.current;
		if (!intent.current) intentScope.current = session.query_scope;
		const originScope = intentScope.current;

		setBusy(true);
		setFailed(false);
		setInputContractRequired(false);
		try {
			const requestedProduct = entryHints?.productId ?? null;
			const wantsProduct =
				!selectedRequest &&
				!initialProject &&
				useHints &&
				requestedProduct !== null;
			let placed: ReturnType<typeof placedProduct> = null;
			if (wantsProduct) {
				const fresh = await catalog.refetch();
				if (lifetime.current !== instance) return;
				if (!client.isCurrentScope(session.query_scope)) {
					setFailed(true);
					return;
				}
				if (fresh.error || !fresh.data) {
					setProductBlocked("load");
					return;
				}
				if (!fresh.data.prepared) {
					setProductBlocked("preparing");
					return;
				}
				placed = placedProduct(fresh.data.products, requestedProduct);
				if (!placed) {
					setProductBlocked("place");
					return;
				}
				setProductBlocked(null);
			}
			intent.current ??= wire(
				{
					schema_version: 1,
					input_contract: projectInputContract,
					title: title.trim(),
					inputs:
						initialProject && useHints
							? initialProject.inputs
							: entryHints && useHints
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
										placed,
									)
								: { brief: emptyBrief() },
					key: crypto.randomUUID(),
				},
				session.runtime.limits.max_json_depth,
				session.runtime.limits.max_body_bytes,
			);
			await store.writeCreation(originScope, intent.current).catch(() => {
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
			if (lifetime.current !== instance) return;
			if (
				!created(
					project,
					!selectedRequest && entryHints?.equipment
						? "equipment"
						: !selectedRequest && entryHints?.roof
							? "design"
							: undefined,
				)
			) {
				setFailed(true);
				return;
			}
			intent.current = null;
			setOpen(false);
			setTitle("");
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
		} finally {
			if (lifetime.current === instance) setBusy(false);
		}
	}
	const selectedRequest = requests.find(
		(request) =>
			request.body === intent.current && request.scope === intentScope.current,
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
	const proposed =
		catalog.data?.products.find((item) => item.id === entryHints?.productId) ??
		null;
	const proposedField = proposed
		? (placedProduct([proposed], proposed.id)?.field ?? null)
		: null;
	if (!open)
		return (
			<button
				className="lp-button"
				disabled={checking || recoveryChecking || recoveryDiscoveryFailed}
				onClick={() => setOpen(true)}
			>
				<Icon name="plus" />
				{__("New project", "linker-tools")}
			</button>
		);
	return (
		<form
			className="lp-new-project"
			onSubmit={(event) => {
				event.preventDefault();
				void submit();
			}}
		>
			{entryHints && !selectedRequest && (
				<Notice>
					<p>
						{initialProject
							? __(
									"Review these saved inputs before creating a new project. The original solution stays available. After creating the project, select equipment using current product data and run a new calculation.",
									"linker-tools",
								)
							: entryHints.productId !== null
								? __(
										"This product is a proposed input from current product data. Creating the project does not confirm that the products work together.",
										"linker-tools",
									)
								: entryHints.equipment && !hasCarriedValues
									? __("Create a project to open Equipment.", "linker-tools")
									: entryHints.roof && !hasCarriedValues
										? __(
												"Create a project to start the roof design.",
												"linker-tools",
											)
										: __(
												"Review the values from this link. If you choose to use them, they will be saved as project inputs when you create the project. This does not run a calculation or select equipment.",
												"linker-tools",
											)}
					</p>
					<dl className="lp-field-summary">
						{entryHints.annualKwh !== null && (
							<div>
								<dt>{__("Annual electricity consumption", "linker-tools")}</dt>
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
									{proposedField === "inverter"
										? __(
												"Inverter or integrated storage system",
												"linker-tools",
											)
										: proposedField === "battery"
											? __("Battery or storage system", "linker-tools")
											: proposedField === "accessory"
												? __("Additional products", "linker-tools")
												: __("Use current product data", "linker-tools")}
								</dt>
								<dd>
									{proposed
										? `${proposed.brand} ${proposed.model}`.trim()
										: String(entryHints.productId)}
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
								onChange={(e) => setUseHints(e.currentTarget.checked)}
							/>
							{__("Use these values for the new project", "linker-tools")}
						</label>
					)}
				</Notice>
			)}
			{requests.length > 1 && (
				<label className="lp-field">
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
							setTitle(request.title);
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
			<label className="lp-field">
				<span>{__("Project name", "linker-tools")}</span>
				<input
					autoFocus
					required
					maxLength={256}
					value={title}
					readOnly={Boolean(intent.current)}
					onChange={(event) => setTitle(event.currentTarget.value)}
				/>
			</label>
			<div className="lp-inline-actions">
				<button
					className="lp-button"
					disabled={
						busy ||
						checking ||
						recoveryChecking ||
						recoveryDiscoveryFailed ||
						!title.trim()
					}
				>
					{busy
						? __("Creating…", "linker-tools")
						: failed
							? __("Retry project creation", "linker-tools")
							: __("Create project", "linker-tools")}
				</button>
				{!intent.current && (
					<button
						className="lp-text-button"
						type="button"
						onClick={() => {
							setOpen(false);
							cancelled?.();
						}}
					>
						{__("Cancel", "linker-tools")}
					</button>
				)}
			</div>
			{productBlocked === "load" && (
				<Notice error>
					{__("Product data could not be loaded.", "linker-tools")}
				</Notice>
			)}
			{productBlocked === "preparing" && (
				<Notice>
					{__("Current product data is being prepared.", "linker-tools")}
				</Notice>
			)}
			{productBlocked === "place" && (
				<Notice error>
					{__(
						"Current product data cannot place this product, so the project was not created.",
						"linker-tools",
					)}
				</Notice>
			)}
			{failed && (
				<Notice error>
					{inputContractRequired
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
		</form>
	);
}
