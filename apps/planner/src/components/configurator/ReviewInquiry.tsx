import { useEffect, useRef, useState, type FormEvent } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { ApiError } from "../../data/protocol.ts";
import {
	readInquiryForm,
	readInquiryPreview,
	readDraftReceipt,
} from "../../data/draftTransfer.ts";
import { readObject } from "../../data/readProtocol.ts";
import {
	readPlanningOperation,
	type PlanningRun,
} from "../../data/planningProtocol.ts";
import type { usePlanningOperations } from "../../data/usePlanningOperations.ts";
import { __, sprintf } from "../../i18n.ts";

/** The commerce form owns contact validation, proof and the order-received redirect. */
export function ReviewInquiry({
	run,
	direction,
	client,
	scope,
	operations,
	locale,
	blocked,
	recheck,
}: {
	run?: PlanningRun;
	direction?: string;
	client: PlannerClient;
	scope: string;
	operations: ReturnType<typeof usePlanningOperations>;
	locale: string;
	blocked: boolean;
	recheck: () => void;
}) {
	const [preview, setPreview] = useState<
			| (ReturnType<typeof readInquiryForm> & {
					transfer: ReturnType<typeof readInquiryPreview> | null;
			  })
			| null
		>(null),
		[error, setError] = useState<{
			stage: "load" | "send";
			cause: unknown;
		} | null>(null),
		[attempt, setAttempt] = useState(0),
		[sending, setSending] = useState(false);
	const retained = useRef<FormData | null>(null);
	const staleIntent = useRef<typeof record>(null);
	const host = useRef<HTMLDivElement>(null),
		flight = useRef(false);
	const record = operations.records.find(
		(row) =>
			row.path === "draft/apply" &&
			readPlanningOperation(row.path, row.body).report_run_id === run?.id,
	);
	useEffect(() => {
		const request = new AbortController();
		const lang = locale.startsWith("de") ? "de" : "en";
		const command = run
			? {
					schema_version: 1,
					project_id: run.project_id,
					report_run_id: run.id,
					expected_revision: run.revision,
					lang,
					key: crypto.randomUUID(),
				}
			: { schema_version: 1, lang };
		setError(null);
		void client
			.query(
				run ? "draft/inquiry-preview" : "inquiry/form",
				command,
				scope,
				request.signal,
			)
			.then((raw) => {
				if (request.signal.aborted || !client.isCurrentScope(scope)) return;
				if (run) {
					const transfer = readInquiryPreview(raw, command, client.origin);
					setPreview({ form: transfer.form, lines: transfer.lines, transfer });
				} else setPreview({ ...readInquiryForm(raw), transfer: null });
			})
			.catch((cause) => {
				if (request.signal.aborted) return;
				if (
					cause instanceof ApiError &&
					([401, 403].includes(cause.status) ||
						cause.code === "session_changed")
				)
					recheck();
				setError({ stage: "load", cause });
			});
		return () => request.abort();
	}, [client, scope, run?.project_id, run?.id, run?.revision, locale, attempt]);
	useEffect(() => {
		const node = host.current;
		if (!node || !preview) return;
		// This fragment comes from the same-origin commerce form renderer.
		node.innerHTML = preview.form;
		const form = node.querySelector("form");
		if (
			!form ||
			form.method !== "post" ||
			new URL(form.action).origin !== client.origin
		) {
			node.replaceChildren();
			setError({ stage: "load", cause: new Error("invalid_inquiry_form") });
			return;
		}
		if (retained.current) {
			for (const name of ["name", "email", "company", "message", "consent"]) {
				const field = form.elements.namedItem(name),
					previous = retained.current.get(name);
				if (
					field instanceof window.HTMLInputElement &&
					field.type === "checkbox"
				)
					field.checked = previous === field.value;
				else if (
					(field instanceof window.HTMLInputElement ||
						field instanceof window.HTMLTextAreaElement) &&
					typeof previous === "string"
				)
					field.value = previous;
			}
			retained.current = null;
		}
		if (direction) {
			const message = form.elements.namedItem("message");
			if (!(message instanceof window.HTMLTextAreaElement)) {
				node.replaceChildren();
				setError({ stage: "load", cause: new Error("invalid_inquiry_form") });
				return;
			}
			const full = document.createElement("input");
			full.type = "hidden";
			full.name = "message";
			message.removeAttribute("name");
			if (message.maxLength >= 0)
				message.maxLength = Math.max(
					0,
					message.maxLength - direction.length - 2,
				);
			const update = () => {
				full.value = message.value
					? `${direction}\n\n${message.value}`
					: direction;
			};
			update();
			message.addEventListener("input", update);
			form.addEventListener("submit", update, { capture: true });
			form.append(full);
		}
		form.dispatchEvent(
			new Event("linker:inquiry-form-mounted", { bubbles: true }),
		);
		return () => node.replaceChildren();
	}, [preview, client.origin, direction]);
	async function send(event: FormEvent) {
		if (event.defaultPrevented) return;
		const form = event.target;
		if (
			!(form instanceof window.HTMLFormElement) ||
			!preview ||
			flight.current ||
			!form.reportValidity() ||
			blocked ||
			operations.busy ||
			operations.checking ||
			operations.storageFailed ||
			!client.isCurrentScope(scope)
		) {
			event.preventDefault();
			return;
		}
		if (!run || !preview.transfer) return;
		event.preventDefault();
		flight.current = true;
		setSending(true);
		form.inert = true;
		let posted = false;
		setError(null);
		try {
			const cart = form.elements.namedItem("linker_draft_hash"),
				digest = form.elements.namedItem("linker_planner_draft_sha256"),
				handoff = form.elements.namedItem("linker_planner_handoff_id");
			if (
				!(cart instanceof window.HTMLInputElement) ||
				!(digest instanceof window.HTMLInputElement) ||
				!(handoff instanceof window.HTMLInputElement) ||
				handoff.value !== preview.transfer.handoffId
			)
				throw new Error("invalid_inquiry_form");
			let receipt;
			if (record) {
				const command = readPlanningOperation(record.path, record.body),
					status = readObject(
						await client.send("draft/read", record.body, scope),
					);
				if (status.schema_version !== 1)
					throw new Error("invalid_draft_receipt");
				if (status.state === "applied") {
					receipt = readDraftReceipt(status.receipt, command, client.origin);
					if (record.resultId && record.resultId !== receipt.handoffId)
						throw new Error("invalid_draft_receipt");
					await operations.acknowledgeReadback(record, receipt.handoffId);
				} else if (status.state === "not_applied") {
					if (command.expected_draft_sha256 !== preview.transfer.draftSha256) {
						staleIntent.current = record;
						throw new ApiError(409, "planning_draft_changed");
					}
					const reply = await operations.retry(record);
					if (reply?.path === "draft/apply") receipt = reply.receipt;
				} else throw new Error("invalid_draft_receipt");
			} else {
				const reply = await operations.start("draft/apply", {
					report_run_id: run.id,
					expected_revision: run.revision,
					expected_draft_sha256: preview.transfer.draftSha256,
				});
				if (reply?.path === "draft/apply") receipt = reply.receipt;
			}
			if (!form.isConnected || !client.isCurrentScope(scope)) return;
			if (
				!receipt ||
				receipt.handoffId !== handoff.value ||
				typeof receipt.inquiryCartHash !== "string" ||
				!receipt.inquiryDraftSha256
			)
				throw new Error("missing_inquiry_receipt");
			cart.value = receipt.inquiryCartHash;
			digest.value = receipt.inquiryDraftSha256;
			window.HTMLFormElement.prototype.submit.call(form);
			posted = true;
		} catch (cause) {
			if (form.isConnected) {
				setError({ stage: "send", cause });
				if (
					cause instanceof ApiError &&
					([401, 403].includes(cause.status) ||
						cause.code === "session_changed")
				)
					recheck();
			}
		} finally {
			if (!posted) {
				flight.current = false;
				form.inert = false;
				if (form.isConnected) setSending(false);
			}
		}
	}
	return (
		<section className="sc-card sc-draft-transfer">
			<h2>{__("Request a quotation", "linker-tools")}</h2>
			{direction && <p>{direction}</p>}
			{preview?.lines.length ? (
				<table className="lp-data-table">
					<caption>
						{__("Products included in your inquiry", "linker-tools")}
					</caption>
					<thead>
						<tr>
							<th>{__("Product", "linker-tools")}</th>
							<th>{__("Quantity", "linker-tools")}</th>
						</tr>
					</thead>
					<tbody>
						{preview.lines.map((line, index) => (
							<tr key={index}>
								<td>{line.label}</td>
								<td>{line.quantity}</td>
							</tr>
						))}
					</tbody>
				</table>
			) : null}
			{preview?.transfer?.phaseConflicts.map((check, index) => (
				<p key={index}>
					{check.unit && `${check.unit}: `}
					{sprintf(
						__(
							"Grid phase mismatch. Selected inverter: %1$d. Project requirement: %2$d. You can send an inquiry to discuss the configuration.",
							"linker-tools",
						),
						check.actual,
						check.required,
					)}
				</p>
			))}
			{!preview && !error && (
				<p role="status">{__("Preparing your inquiry…", "linker-tools")}</p>
			)}
			<div ref={host} onSubmit={send} />
			{sending && (
				<p role="status">{__("Sending your inquiry…", "linker-tools")}</p>
			)}
			{error && (
				<p role="alert">
					{error.stage === "send"
						? __("Your inquiry could not be sent.", "linker-tools")
						: __("The inquiry form could not be loaded.", "linker-tools")}{" "}
					{(!preview ||
						error.stage === "load" ||
						(operations.error instanceof ApiError &&
							operations.error.code === "planning_draft_changed") ||
						(error.cause instanceof ApiError &&
							error.cause.code === "planning_draft_changed")) && (
						<button
							type="button"
							className="sc-button"
							onClick={async () => {
								if (staleIntent.current) {
									await operations.discard(staleIntent.current);
									staleIntent.current = null;
								}
								const form = host.current?.querySelector("form");
								if (form) retained.current = new window.FormData(form);
								setPreview(null);
								setAttempt((value) => value + 1);
							}}
						>
							{error.stage === "send"
								? __("Review inquiry again", "linker-tools")
								: __("Load inquiry form again", "linker-tools")}
						</button>
					)}
				</p>
			)}
		</section>
	);
}
