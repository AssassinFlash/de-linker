import { useCallback, useEffect, useRef, useState } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { ApiError, type Project } from "../../data/protocol.ts";
import { readInquiryForm } from "../../data/draftTransfer.ts";
import {
	pendingInquiry,
	rememberInquiry,
	restoreInquiry,
	inquiryPayload,
	replayWindow,
	type PendingInquiry,
} from "../../data/inquiryRecovery.ts";
import type { Brief } from "../../domain/brief.ts";
import { __, sprintf } from "../../i18n.ts";
import { systemNames } from "./PreliminaryOptions.tsx";

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
	"linker_individual_review",
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
	direction,
	client,
	scope,
	locale,
	active,
	changeSelection,
	enterDetails,
	recheck,
	inquiryPending,
}: {
	project: Project;
	direction: NonNullable<Brief["system_scope"]>;
	client: PlannerClient;
	scope: string;
	locale: string;
	active: boolean;
	changeSelection: () => void;
	enterDetails?: (() => void) | undefined;
	recheck: () => void;
	inquiryPending?: (pending: boolean) => void;
}) {
	const [failed, setFailed] = useState(false);
	const [lines, setLines] = useState<
		ReturnType<typeof readInquiryForm>["lines"] | null
	>(null);
	const [navigationFailed, setNavigationFailed] = useState(false);
	const [attempt, setAttempt] = useState(0);
	const host = useRef<HTMLDivElement>(null);
	const heading = useRef<HTMLHeadingElement>(null);
	const projectId = project.id;
	const revision = project.revision;
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
	const save = useCallback(() => {
		const form = host.current?.querySelector("form");
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
	}, [client, projectId, scope]);
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
				!["#sc-preliminary-review", "#sc-preliminary-options"].includes(
					target.hash,
				)
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
	useEffect(() => {
		const node = host.current;
		if (!node) return;
		const request = new AbortController();
		let expiry: number | undefined;
		const abort = () => request.abort();
		window.addEventListener("pagehide", abort, { once: true });
		setLines(null);
		setFailed(false);
		void client
			.query(
				"inquiry/form",
				{
					schema_version: 1,
					lang: locale.startsWith("de") ? "de" : "en",
					project_id: projectId,
					revision,
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
					)?.value !== `${projectId}:${revision}`
				)
					throw new Error("invalid_inquiry_form");
				const local = volatile.current;
				const pending =
					pendingInquiry(scope, { id: projectId, revision }) ??
					(local?.scope === scope &&
					local.projectId === projectId &&
					local.revision === revision
						? local.pending
						: null);
				const payload =
					pending && replayWindow(form) ? inquiryPayload(pending) : null;
				if (
					pending &&
					!payload &&
					local?.pending === pending &&
					Date.now() >= pending.expiresAt
				)
					local.pending = {
						requestId: pending.requestId,
						expiresAt: pending.expiresAt,
					};
				const unavailable = Boolean(pending && !payload);
				activeReplay.current = pending;
				setOutcomeUnconfirmed(unavailable);
				setCheckingInquiry(Boolean(pending));
				inquiryPending?.(Boolean(pending));
				setLines(response.lines);
				if (unavailable) return;
				if (pending && payload) {
					expiry = window.setTimeout(
						() => setAttempt((value) => value + 1),
						Math.max(0, pending.expiresAt - Date.now()),
					);
					restoreCustomerFields(form, new Map(payload));
					restoreInquiry(form, payload);
					const send = form.querySelector('button[type="submit"]');
					if (send)
						send.textContent = __("Check inquiry status", "linker-tools");
				} else {
					retained.current =
						takeNavigationDraft(scope, projectId) ?? retained.current;
					restoreCustomerFields(form, retained.current);
				}
				node.replaceChildren(template.content);
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
			const form = node.querySelector("form");
			if (form) retained.current = readCustomerFields(form, retained.current);
			node.replaceChildren();
		};
	}, [client, scope, projectId, revision, locale, attempt, recheck]);
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
				<aside className="linker-inquiry-draft">
					<h3>{__("Current configuration", "linker-tools")}</h3>
					<p>
						{sprintf(
							__("Planned system: %s", "linker-tools"),
							systemNames()[direction],
						)}
					</p>
					{!checkingInquiry && Boolean(lines?.length) && (
						<ul>
							{lines?.map((line, index) => (
								<li key={index}>
									{line.label} × {line.quantity}
								</li>
							))}
						</ul>
					)}
					<button
						className="sc-button"
						type="button"
						disabled={checkingInquiry}
						onClick={changeSelection}
					>
						{__("Change selection", "linker-tools")}
					</button>
					{enterDetails && (
						<button
							className="sc-button"
							type="button"
							disabled={checkingInquiry}
							onClick={() => {
								if (posting.current || !client.isCurrentScope(scope)) return;
								try {
									save();
								} catch {
									setNavigationFailed(true);
									return;
								}
								enterDetails();
							}}
						>
							{__("Enter project details", "linker-tools")}
						</button>
					)}
				</aside>
				<div className="sc-inquiry-fields">
					{!lines && !failed && (
						<p role="status">{__("Preparing your inquiry…", "linker-tools")}</p>
					)}
					<div
						ref={host}
						onSubmit={(event) => {
							if (!client.isCurrentScope(scope)) event.preventDefault();
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
					{outcomeUnconfirmed && !failed && lines && (
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
