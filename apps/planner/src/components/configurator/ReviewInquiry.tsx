import { useEffect, useRef, useState } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { ApiError, type Project } from "../../data/protocol.ts";
import { readInquiryForm } from "../../data/draftTransfer.ts";
import type { Brief } from "../../domain/brief.ts";
import { __, sprintf } from "../../i18n.ts";
import { systemNames } from "./PreliminaryOptions.tsx";

function customerFields(form: HTMLFormElement) {
	return Array.from(form.elements).filter(
		(field): field is HTMLInputElement | HTMLTextAreaElement =>
			((field instanceof window.HTMLInputElement && field.type !== "hidden") ||
				field instanceof window.HTMLTextAreaElement) &&
			[
				"name",
				"email",
				"company",
				"message",
				"consent",
				"linker_include_project_notes",
			].includes(field.name),
	);
}

function readCustomerFields(
	form: HTMLFormElement,
): Map<string, string | boolean> {
	const values = new Map<string, string | boolean>();
	for (const field of customerFields(form)) {
		if (field instanceof window.HTMLInputElement && field.type === "checkbox") {
			if (field.checked !== field.defaultChecked)
				values.set(field.name, field.checked);
		} else if (field.value !== field.defaultValue)
			values.set(field.name, field.value);
	}
	return values;
}

export function ReviewInquiry({
	project,
	direction,
	client,
	scope,
	locale,
	active,
	changeSelection,
	recheck,
}: {
	project: Project;
	direction: NonNullable<Brief["system_scope"]>;
	client: PlannerClient;
	scope: string;
	locale: string;
	active: boolean;
	changeSelection: () => void;
	recheck: () => void;
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
	const retained = useRef(new Map<string, string | boolean>());
	const recoveryKey = `linker-preliminary-inquiry:${scope}:${projectId}`;
	useEffect(() => {
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
			const form = host.current?.querySelector("form");
			if (!form) return;
			const values = readCustomerFields(form);
			if (!values.size) return;
			try {
				window.sessionStorage.setItem(
					recoveryKey,
					JSON.stringify({
						path: target.pathname,
						fields: Object.fromEntries(values),
					}),
				);
			} catch {
				event.preventDefault();
				setNavigationFailed(true);
			}
		};
		document.addEventListener("click", saveForLanguage);
		return () => document.removeEventListener("click", saveForLanguage);
	}, [projectId, recoveryKey]);
	useEffect(() => {
		if (active) heading.current?.focus();
	}, [active]);
	useEffect(() => {
		const node = host.current;
		if (!node) return;
		const request = new AbortController();
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
				let translated: Record<string, unknown> | undefined;
				try {
					const draft = JSON.parse(
						window.sessionStorage.getItem(recoveryKey) ?? "null",
					);
					if (draft?.path === location.pathname) {
						translated = draft.fields;
						window.sessionStorage.removeItem(recoveryKey);
					}
				} catch {
					// A draft can carry edits only when the browser allowed its write.
				}
				for (const field of customerFields(form)) {
					const previous =
						retained.current.get(field.name) ?? translated?.[field.name];
					if (
						typeof previous === "boolean" &&
						field instanceof window.HTMLInputElement &&
						field.type === "checkbox"
					)
						field.checked = previous;
					else if (typeof previous === "string") field.value = previous;
				}
				node.replaceChildren(template.content);
				form.dispatchEvent(
					new Event("linker:inquiry-form-mounted", { bubbles: true }),
				);
				setLines(response.lines);
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
			request.abort();
			const form = node.querySelector("form");
			if (form) retained.current = readCustomerFields(form);
			node.replaceChildren();
		};
	}, [
		client,
		scope,
		projectId,
		revision,
		locale,
		attempt,
		recheck,
		recoveryKey,
	]);
	return (
		<section
			className="sc-main sc-draft-transfer"
			id="sc-preliminary-review"
			hidden={!active}
		>
			<header className="sc-section-head">
				<h2 ref={heading} tabIndex={-1}>
					{__("Review your inquiry", "linker-tools")}
				</h2>
			</header>
			<div className="linker-inquiry linker-inquiry-columns">
				<aside className="linker-inquiry-draft">
					<p>
						{sprintf(
							__("Planned system: %s", "linker-tools"),
							systemNames()[direction],
						)}
					</p>
					{Boolean(lines?.length) && (
						<ul>
							{lines?.map((line, index) => (
								<li key={index}>
									{line.label} × {line.quantity}
								</li>
							))}
						</ul>
					)}
					<button className="sc-button" type="button" onClick={changeSelection}>
						{__("Change selection", "linker-tools")}
					</button>
				</aside>
				<div className="sc-inquiry-fields">
					{!lines && !failed && (
						<p role="status">{__("Preparing your inquiry…", "linker-tools")}</p>
					)}
					<div
						ref={host}
						onSubmit={(event) => {
							if (!client.isCurrentScope(scope)) event.preventDefault();
						}}
					/>
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
