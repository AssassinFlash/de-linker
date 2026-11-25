import { ProductCard } from "../shared/ProductCard.tsx";
import {
	createContext,
	useCallback,
	useEffect,
	useLayoutEffect,
	useRef,
	useState,
	type ReactNode,
} from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { ApiError, type Project } from "../../data/protocol.ts";
import { InquiryBomLine } from "./InquiryBomLine.tsx";
import { readInquiryForm } from "../../data/draftTransfer.ts";
import {
	pendingInquiry,
	guidedInquiryRetry,
	forgetInquiry,
	rememberInquiry,
	restoreInquiry,
	inquiryPayload,
	replayWindow,
	type PendingInquiry,
} from "../../data/inquiryRecovery.ts";
import type { Brief } from "../../domain/brief.ts";
import { __, sprintf } from "../../i18n.ts";
import { ProjectFacts } from "./ProjectFacts.tsx";
import { existingSystem } from "./ProjectEquipment.tsx";
import { retrofitOptions, systemNames } from "./PreliminaryOptions.tsx";

export const InquiryProductSkus = createContext<ReadonlySet<string> | null>(
	null,
);

type CustomerField = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
type CustomerDraft = Map<string, string | boolean>;

const DRAFT_KEY = "linker-preliminary-inquiry";
const contactFields = [
	"name",
	"email",
	"company",
	"message",
	"consent",
	"linker_include_project_notes",
];

function customerFields(form: HTMLFormElement): CustomerField[] {
	return Array.from(form.elements).filter(
		(field): field is CustomerField =>
			((field instanceof window.HTMLInputElement &&
				field.type !== "hidden" &&
				!field.readOnly) ||
				(field instanceof window.HTMLTextAreaElement && !field.readOnly) ||
				field instanceof window.HTMLSelectElement) &&
			!field.disabled &&
			(contactFields.includes(field.name) || field.name.startsWith("billing_")),
	);
}

function readCustomerFields(
	form: HTMLFormElement,
	tracked: CustomerDraft,
): CustomerDraft {
	const values: CustomerDraft = new Map();
	for (const field of customerFields(form)) {
		if (field instanceof window.HTMLInputElement && field.type === "checkbox") {
			if (tracked.has(field.name) || field.checked !== field.defaultChecked)
				values.set(field.name, field.checked);
		} else {
			const defaultValue =
				field instanceof window.HTMLSelectElement
					? (
							Array.from(field.options).find(
								(option) => option.defaultSelected,
							) ?? field.options[0]
						)?.value
					: field.defaultValue;
			if (tracked.has(field.name) || field.value !== defaultValue)
				values.set(field.name, field.value);
		}
	}
	return values;
}

function restoreCustomerFields(
	form: HTMLFormElement,
	values: CustomerDraft,
): void {
	for (const field of customerFields(form)) {
		const previous = values.get(field.name);
		if (
			typeof previous === "boolean" &&
			field instanceof window.HTMLInputElement &&
			field.type === "checkbox"
		)
			field.checked = previous;
		else if (typeof previous === "string" && field.value !== previous) {
			if (
				field instanceof window.HTMLSelectElement &&
				!Array.from(field.options).some((option) => option.value === previous)
			)
				continue;
			field.value = previous;
			const details = field.closest("details");
			if (details) details.open = true;
		}
	}
	if (values.has("name") || values.has("email")) {
		const name = form.querySelector<HTMLInputElement>('input[name="name"]');
		const email = form.querySelector<HTMLInputElement>('input[name="email"]');
		const summary = form.querySelector(".linker-inquiry-details summary small");
		if (name && email && summary)
			summary.textContent = `${name.value} · ${email.value}`;
	}
}

function takeNavigationDraft(
	scope: string,
	projectId: string,
): CustomerDraft | null {
	try {
		const draft = JSON.parse(
			window.sessionStorage.getItem(DRAFT_KEY) ?? "null",
		);
		if (!draft) return null;
		if (draft.scope === scope && draft.projectId !== projectId) return null;
		window.sessionStorage.removeItem(DRAFT_KEY);
		if (
			draft.scope !== scope ||
			!draft.fields ||
			typeof draft.fields !== "object"
		)
			return null;
		return new Map(
			Object.entries(draft.fields).filter(
				(entry): entry is [string, string | boolean] =>
					typeof entry[1] === "string" || typeof entry[1] === "boolean",
			),
		);
	} catch {
		return null;
	}
}

export function ReviewInquiry({
	project,
	reportRunId,
	changeRequestedQuantity,
	equipmentDetails,
	direction,
	client,
	scope,
	locale,
	active,
	ready = true,
	submitReady = true,
	changeSelection,
	enterDetails,
	recheck,
	inquiryPending,
}: {
	project: Project;
	reportRunId?: string;
	equipmentDetails?: ReactNode;
	changeRequestedQuantity?: (
		productId: number,
		current: number,
		next: number,
	) => Promise<void>;
	direction: Brief["system_scope"];
	client: PlannerClient;
	scope: string;
	locale: string;
	active: boolean;
	ready?: boolean;
	submitReady?: boolean;
	changeSelection: () => void;
	enterDetails?: (() => void) | undefined;
	recheck: () => void;
	inquiryPending?: (pending: boolean) => void;
}) {
	const [failed, setFailed] = useState(false);
	const [cartBusy, setCartBusy] = useState(false);
	const [review, setReview] = useState<ReturnType<
		typeof readInquiryForm
	> | null>(null);
	const [navigationFailed, setNavigationFailed] = useState(false);
	const [attempt, setAttempt] = useState(0);
	const host = useRef<HTMLDivElement>(null);
	const heading = useRef<HTMLHeadingElement>(null);
	const summaryDetails = useRef<HTMLDetailsElement>(null);
	useEffect(() => {
		const media = window.matchMedia?.("(max-width: 600px)");
		if (!media) return;
		const sync = () => {
			if (summaryDetails.current) summaryDetails.current.open = !media.matches;
		};
		sync();
		media.addEventListener("change", sync);
		return () => media.removeEventListener("change", sync);
	}, []);
	const projectId = project.id;
	const revision = project.revision;
	const loadedBinding = useRef<{
		revision: number;
		reportRunId: string | undefined;
	} | null>(null);
	const canSubmit =
		submitReady &&
		Boolean(review) &&
		loadedBinding.current?.revision === revision &&
		loadedBinding.current?.reportRunId === reportRunId;
	const retained = useRef<CustomerDraft>(new Map());
	const posting = useRef(false);
	const volatile = useRef<{
		scope: string;
		projectId: string;
		revision: number;
		pending: PendingInquiry;
	} | null>(null);
	const activeReplay = useRef<PendingInquiry | null>(null);
	const [outcomeUnconfirmed, setOutcomeUnconfirmed] = useState(false);
	const [checkingInquiry, setCheckingInquiry] = useState(() =>
		Boolean(pendingInquiry(scope, project)),
	);
	// The next form consumes the draft only for the same owned project.
	const save = useCallback(
		(form = host.current?.querySelector("form")) => {
			if (!form || posting.current || !client.isCurrentScope(scope)) return;
			const values = readCustomerFields(form, retained.current);
			retained.current = values;
			if (values.size)
				window.sessionStorage.setItem(
					DRAFT_KEY,
					JSON.stringify({
						scope,
						projectId,
						fields: Object.fromEntries(values),
					}),
				);
		},
		[client, projectId, scope],
	);
	useEffect(() => {
		const onPageHide = (event: PageTransitionEvent) => {
			try {
				save();
			} catch {
				// Browser Back itself cannot be canceled from pagehide.
			} finally {
				if (event.persisted) host.current?.replaceChildren();
			}
		};
		const onPageShow = (event: PageTransitionEvent) => {
			posting.current = false;
			// Reauthorize the project before restoring edits in a cached page.
			if (event.persisted) setAttempt((value) => value + 1);
		};
		const saveForLanguage = (event: MouseEvent) => {
			if (
				event.defaultPrevented ||
				event.button !== 0 ||
				event.metaKey ||
				event.ctrlKey ||
				event.shiftKey ||
				event.altKey ||
				!(event.target instanceof window.Element)
			)
				return;
			const link = event.target.closest<HTMLAnchorElement>(
				"header a[hreflang][lang], footer a[hreflang][lang]",
			);
			const target = link && URL.parse(link.href);
			if (
				!target ||
				(link.target && link.target !== "_self") ||
				target.origin !== location.origin ||
				target.searchParams.get("project") !== projectId ||
				![
					"#sc-preliminary-review",
					"#sc-preliminary-options",
					"#sc-review",
				].includes(target.hash)
			)
				return;
			try {
				save();
			} catch {
				event.preventDefault();
				setNavigationFailed(true);
			}
		};
		document.addEventListener("click", saveForLanguage);
		window.addEventListener("pagehide", onPageHide);
		window.addEventListener("pageshow", onPageShow);
		return () => {
			document.removeEventListener("click", saveForLanguage);
			window.removeEventListener("pagehide", onPageHide);
			window.removeEventListener("pageshow", onPageShow);
		};
	}, [projectId, save]);
	useEffect(() => {
		if (active) heading.current?.focus({ preventScroll: true });
	}, [active]);
	// Keep the editable native form in place until its replacement is authorized.
	useEffect(() => {
		const node = host.current;
		return () => {
			const form = node?.querySelector("form");
			if (form) {
				try {
					save(form);
				} catch {
					/* In-memory edits remain in the current page. */
				}
				node?.replaceChildren();
			}
		};
	}, [save, ready]);
	useLayoutEffect(() => {
		const send = host.current?.querySelector<HTMLButtonElement>(
			'button[type="submit"]',
		);
		if (!send || canSubmit) return;
		const previouslyDisabled = send.disabled;
		send.disabled = true;
		return () => {
			send.disabled = previouslyDisabled;
		};
	}, [review, canSubmit]);
	useEffect(() => {
		const node = host.current;
		if (!node || !ready) return;
		const request = new AbortController();
		let expiry: number | undefined;
		const abort = () => request.abort();
		window.addEventListener("pagehide", abort, { once: true });
		setReview(null);
		setFailed(false);
		const local = volatile.current;
		const pending =
			pendingInquiry(scope, { id: projectId, revision }) ??
			(local?.scope === scope &&
			local.projectId === projectId &&
			local.revision === revision
				? local.pending
				: null);
		const transfer = pending?.fields?.linker_report_transfer;
		const retry = reportRunId
			? guidedInquiryRetry(new URL(location.href))?.handle
			: null;
		void client
			.query(
				"inquiry/form",
				{
					schema_version: 1,
					lang: locale.startsWith("de") ? "de" : "en",
					project_id: projectId,
					revision,
					...(reportRunId ? { report_run_id: reportRunId } : {}),
					...(retry
						? { retry }
						: transfer
							? { report_transfer: transfer }
							: {}),
				},
				scope,
				request.signal,
			)
			.then((raw) => {
				if (request.signal.aborted || !client.isCurrentScope(scope)) return;
				const response = readInquiryForm(raw);
				const template = document.createElement("template");
				template.innerHTML = response.form;
				const form = template.content.querySelector<HTMLFormElement>(
					"form.linker-inquiry-form",
				);
				const action = form?.getAttribute("action")?.trim();
				const target = action ? URL.parse(action, node.baseURI) : null;
				if (
					!form ||
					form.method !== "post" ||
					target?.origin !== client.origin ||
					!target.pathname.endsWith("/wp-admin/admin-post.php") ||
					form.querySelector<HTMLInputElement>(
						'input[name="linker_preliminary_project"]',
					)?.value !== `${projectId}:${revision}` ||
					(reportRunId &&
						!form
							.querySelector<HTMLInputElement>(
								'input[name="linker_report_transfer"]',
							)
							?.value.startsWith(reportRunId + ":"))
				)
					throw new Error("invalid_inquiry_form");
				const replay = retry ? null : pending;
				const serverReplay = Boolean(
					retry &&
					form.querySelector('input[name="linker_inquiry_receipt_only"]'),
				);
				if (retry && !serverReplay) {
					forgetInquiry(scope, { id: projectId, revision });
					volatile.current = null;
				}
				const payload =
					replay && replayWindow(form) ? inquiryPayload(replay) : null;
				if (
					replay &&
					!payload &&
					local?.pending === replay &&
					Date.now() >= replay.expiresAt
				)
					local.pending = {
						requestId: replay.requestId,
						expiresAt: replay.expiresAt,
					};
				const unavailable = Boolean(replay && !payload);
				activeReplay.current = replay;
				setOutcomeUnconfirmed(unavailable);
				setCheckingInquiry(Boolean(replay) || serverReplay);
				inquiryPending?.(Boolean(replay) || serverReplay);
				loadedBinding.current = { revision, reportRunId };
				setReview(response);
				if (unavailable) {
					node.replaceChildren();
					return;
				}
				if (replay && payload) {
					expiry = window.setTimeout(
						() => setAttempt((value) => value + 1),
						Math.max(0, replay.expiresAt - Date.now()),
					);
					restoreCustomerFields(form, new Map(payload));
					restoreInquiry(form, payload);
					const send = form.querySelector('button[type="submit"]');
					if (send)
						send.textContent = __("Check inquiry status", "linker-tools");
				} else {
					const previous = node.querySelector("form");
					retained.current = previous
						? readCustomerFields(previous, retained.current)
						: (takeNavigationDraft(scope, projectId) ?? retained.current);
					restoreCustomerFields(form, retained.current);
				}
				const focused = document.activeElement;
				const focusName =
					focused && node.contains(focused)
						? focused.getAttribute("name")
						: null;
				node.replaceChildren(template.content);
				if (focusName)
					customerFields(form)
						.find((field) => field.name === focusName)
						?.focus({ preventScroll: true });
				form.dispatchEvent(
					new Event("linker:inquiry-form-mounted", { bubbles: true }),
				);
			})
			.catch((error) => {
				if (request.signal.aborted) return;
				if (
					error instanceof ApiError &&
					(error.status === 401 ||
						error.status === 403 ||
						error.code === "session_changed")
				)
					recheck();
				setFailed(true);
			});
		return () => {
			window.removeEventListener("pagehide", abort);
			window.clearTimeout(expiry);
			abort();
		};
	}, [
		client,
		scope,
		projectId,
		revision,
		locale,
		attempt,
		recheck,
		ready,
		save,
		reportRunId,
	]);
	const editConfiguration = enterDetails
		? () => {
				if (posting.current || !client.isCurrentScope(scope)) return;
				try {
					save();
				} catch {
					setNavigationFailed(true);
					return;
				}
				enterDetails();
			}
		: undefined;
	const facts = review?.facts ?? [];
	const inverter = existingSystem(project.inputs);
	const retrofit =
		!reportRunId &&
		inverter &&
		retrofitOptions(project.inputs)?.find(
			(option) => option.keep === inverter.keep_inverter,
		);
	const changes = review?.changes ?? [];
	const lines = review?.lines;
	return (
		<section
			className="sc-main sc-draft-transfer sc-preliminary-review"
			hidden={!active}
		>
			<header className="sc-section-head">
				<h2 ref={heading} tabIndex={-1}>
					{__("Review your inquiry", "linker-tools")}
				</h2>
			</header>
			<div className="linker-inquiry linker-inquiry-columns">
				<aside className="linker-inquiry-draft sc-inquiry-overview">
					<h3>{__("Inquiry summary", "linker-tools")}</h3>
					{direction && (
						<p>
							{sprintf(
								__("Planned system: %s", "linker-tools"),
								systemNames()[direction],
							)}
						</p>
					)}
					{direction === "storage_addition" && inverter && (
						<p className="sc-review-choice">
							{inverter.keep_inverter
								? __("Keep the existing inverter", "linker-tools")
								: __("Consider a replacement inverter", "linker-tools")}
						</p>
					)}
					<details
						ref={summaryDetails}
						className="sc-review-details"
						hidden={!retrofit && !facts.length}
					>
						<summary>{__("Project details", "linker-tools")}</summary>
						{retrofit && (
							<div className="sc-review-tradeoff">
								<p>{retrofit.benefit}</p>
								<p>{retrofit.check}</p>
							</div>
						)}
						{facts.length > 0 && <ProjectFacts facts={facts} />}
					</details>
					{!equipmentDetails &&
						!checkingInquiry &&
						canSubmit &&
						review &&
						!lines?.length &&
						!changes.length && (
							<p className="sc-empty-supply">
								{__(
									"No products selected. We can discuss equipment after you send your inquiry.",
									"linker-tools",
								)}
							</p>
						)}
					{!checkingInquiry && Boolean(lines?.length) && (
						<>
							{changeRequestedQuantity && (
								<p className="sc-muted">
									{__(
										"Adjust the quantities you want to request. The system design stays the same.",
										"linker-tools",
									)}
								</p>
							)}
							<ul className="sc-inquiry-products">
								{lines?.map((line, index) => (
									<li
										key={
											line.cartKey ??
											`${line.projectId ?? "cart"}-${line.productId}-${index}`
										}
									>
										<InquiryBomLine
											line={line}
											edit={review?.draftEdit ?? null}
											pending={cartBusy || checkingInquiry}
											onBusy={setCartBusy}
											onUpdated={() => {
												setReview(null);
												setAttempt((value) => value + 1);
											}}
											onProjectQuantity={
												reportRunId &&
												line.projectId === projectId &&
												changeRequestedQuantity
													? async (next) => {
															save();
															await changeRequestedQuantity(
																line.productId,
																line.quantity,
																next,
															);
														}
													: undefined
											}
											onEditConfiguration={
												reportRunId && line.projectId === projectId
													? editConfiguration
													: undefined
											}
										/>
									</li>
								))}
							</ul>
						</>
					)}
					{!checkingInquiry && equipmentDetails && (
						<InquiryProductSkus.Provider
							value={
								new Set(
									lines?.flatMap((line) =>
										line.sku && line.projectId === projectId ? [line.sku] : [],
									),
								)
							}
						>
							{equipmentDetails}
						</InquiryProductSkus.Provider>
					)}
					{!checkingInquiry && changes.length > 0 && (
						<table className="sc-data-table">
							<thead>
								<tr>
									<th scope="col">{__("Product", "linker-tools")}</th>
									<th scope="col">{__("Current quantity", "linker-tools")}</th>
									<th scope="col">{__("New quantity", "linker-tools")}</th>
								</tr>
							</thead>
							<tbody>
								{changes.map((line) => (
									<tr key={line.productId}>
										<th scope="row">
											<ProductCard {...line} />
										</th>
										<td>{line.before}</td>
										<td>{line.after}</td>
									</tr>
								))}
							</tbody>
						</table>
					)}
					{!checkingInquiry &&
						review?.conflicts.map((conflict) => (
							<p key={conflict.unit ?? "system"}>
								{conflict.unit && <strong>{conflict.unit} · </strong>}
								{sprintf(
									// translators: 1: inverter phase count, 2: required grid phase count.
									__(
										"Grid phase mismatch. Selected inverter: %1$d. Project requirement: %2$d. You can send an inquiry to discuss the configuration.",
										"linker-tools",
									),
									conflict.actual,
									conflict.required,
								)}
							</p>
						))}
				</aside>
				<div className="sc-inquiry-fields">
					{!review && !failed && (
						<p role="status">{__("Preparing your inquiry…", "linker-tools")}</p>
					)}
					<div
						ref={host}
						inert={cartBusy || undefined}
						onSubmitCapture={(event) => {
							if (!canSubmit || !client.isCurrentScope(scope)) {
								event.preventDefault();
								event.stopPropagation();
							}
						}}
						onSubmit={(event) => {
							if (cartBusy || !review || !client.isCurrentScope(scope))
								event.preventDefault();
							if (
								event.defaultPrevented ||
								!(event.target instanceof window.HTMLFormElement)
							)
								return;
							const replay = activeReplay.current;
							if (
								replay &&
								(!replay.fields || Date.now() >= replay.expiresAt)
							) {
								event.preventDefault();
								setAttempt((value) => value + 1);
								return;
							}
							if (!replay) {
								const captured = rememberInquiry(event.target, scope, project);
								if (captured) {
									if (!captured.saved)
										volatile.current = {
											scope,
											projectId,
											revision,
											pending: captured.attempt,
										};
									inquiryPending?.(true);
								}
							}
							posting.current = true;
							setCheckingInquiry(true);
							retained.current.clear();
							takeNavigationDraft(scope, projectId);
						}}
					/>
					{outcomeUnconfirmed && !failed && review && (
						<p role="status">
							{__(
								"We could not confirm whether your inquiry was received. Please contact sales@de-linker.com before sending another one.",
								"linker-tools",
							)}
						</p>
					)}
					{failed && (
						<div role="alert">
							<p>
								{__("The inquiry form could not be loaded.", "linker-tools")}
							</p>
							<button
								className="sc-button"
								type="button"
								onClick={() => setAttempt((value) => value + 1)}
							>
								{__("Load inquiry form again", "linker-tools")}
							</button>
						</div>
					)}
					<div className="sc-review-actions">
						<button
							className="sc-button btn-secondary"
							type="button"
							disabled={checkingInquiry}
							onClick={() => {
								if (reportRunId) {
									try {
										save();
									} catch {
										setNavigationFailed(true);
										return;
									}
								}
								changeSelection();
							}}
						>
							{__("Change selection", "linker-tools")}
						</button>
						{enterDetails && (
							<button
								className="sc-button btn-ghost"
								type="button"
								disabled={checkingInquiry}
								onClick={editConfiguration}
							>
								{__("Enter project details", "linker-tools")}
							</button>
						)}
					</div>
				</div>
			</div>
			{navigationFailed && (
				<p role="alert">
					{__(
						"Your browser could not save your entries. Stay on this page to avoid losing them.",
						"linker-tools",
					)}
				</p>
			)}
		</section>
	);
}
