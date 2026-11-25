import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import {
	readDraftPreview,
	readDraftReceipt,
} from "../../data/draftTransfer.ts";
import type { DraftPreview, DraftReceipt } from "../../data/draftTransfer.ts";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import { readPlanningOperation } from "../../data/planningProtocol.ts";
import type { PlanningIntent } from "../../data/PlanningIntentStore.ts";
import type {
	PlanningReply,
	usePlanningOperations,
} from "../../data/usePlanningOperations.ts";
import { ApiError } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

/** Changes to the solution draft require review before the Woo transfer. */
export function DraftTransferButton({
	run,
	client,
	scope,
	operations,
	current,
	blocked,
	locale,
	recheck,
	reviewedSelection = false,
	reportOnly = run.result?.has_report_only_handoff === true,
}: {
	run: PlanningRun;
	client: PlannerClient;
	scope: string;
	operations: ReturnType<typeof usePlanningOperations>;
	current: boolean;
	blocked: boolean;
	locale: string;
	recheck: () => void;
	reviewedSelection?: boolean;
	reportOnly?: boolean;
}) {
	const pending = operations.records.some((record) => record.resultId === null);
	const transferBlocked = blocked || pending;
	const [preview, setPreview] = useState<DraftPreview | null>(null),
		[preparing, setPreparing] = useState(false),
		[checking, setChecking] = useState(false),
		[checkedBody, setCheckedBody] = useState<string | null>(null),
		[receipt, setReceipt] = useState<DraftReceipt | null>(null),
		[error, setError] = useState<unknown>(null),
		[present, setPresent] = useState<DraftPreview | null>(null);
	const confirmed = useRef<{ key: string; receipt: DraftReceipt } | null>(null),
		flight = useRef<AbortController | null>(null),
		lifetime = useRef(0),
		transferEnabled = useRef(current && !transferBlocked),
		currentReport = useRef(current);
	const record = useMemo(
		() =>
			operations.records
				.filter(
					(row) =>
						row.path === "draft/apply" &&
						readPlanningOperation(row.path, row.body).report_run_id === run.id,
				)
				.sort((a, b) => b.createdAt - a.createdAt)[0] ?? null,
		[operations.records, run.id],
	);
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
			flight.current?.abort();
		};
	}, [run.id, scope]);
	useEffect(() => {
		if (!current) setPreview(null);
	}, [current]);
	useLayoutEffect(() => {
		transferEnabled.current = current && !transferBlocked;
		currentReport.current = current;
	}, [current, transferBlocked]);

	useEffect(() => {
		if (!record || operations.busy) {
			setChecking(false);
			return;
		}
		if (confirmed.current?.key === record.key) {
			setChecking(false);
			return;
		}
		const controller = new AbortController(),
			instance = lifetime.current;
		let active = true;
		const admitted = () =>
			active && instance === lifetime.current && client.isCurrentScope(scope);
		setChecking(true);
		void client
			.send("draft/read", record.body, scope, controller.signal)
			.then(async (raw) => {
				if (!admitted()) return;
				const status = readObject(raw);
				if (
					status.schema_version !== 1 ||
					!["applied", "not_applied"].includes(String(status.state)) ||
					(status.active !== undefined && typeof status.active !== "boolean")
				)
					throw new ApiError(502, "invalid_draft_receipt");
				if (status.state === "not_applied") setError(null);
				if (status.state === "applied") {
					const receipt = readDraftReceipt(
						status.receipt,
						readPlanningOperation(record.path, record.body),
						client.origin,
					);
					if (record.resultId !== null && record.resultId !== receipt.handoffId)
						throw new ApiError(502, "invalid_draft_receipt");
					const recovered =
						status.active === undefined
							? receipt
							: { ...receipt, active: status.active };
					confirmed.current = { key: record.key, receipt: recovered };
					setReceipt(recovered);
					setError(null);
					await operations.acknowledgeReadback(record, receipt.handoffId);
				}
			})
			.catch((cause) => {
				if (!admitted()) return;
				if (
					cause instanceof ApiError &&
					([401, 403].includes(cause.status) ||
						cause.code === "session_changed")
				)
					recheck();
				else setError(cause);
			})
			.finally(() => {
				if (!admitted()) return;
				setCheckedBody(record.body);
				setChecking(false);
			});
		return () => {
			active = false;
			controller.abort();
		};
	}, [record?.body, record?.resultId, operations.busy, client, scope]);

	async function prepare() {
		if (
			flight.current ||
			transferBlocked ||
			!current ||
			preparing ||
			operations.busy ||
			operations.checking ||
			operations.storageFailed ||
			record
		)
			return;
		const controller = new AbortController(),
			instance = lifetime.current;
		flight.current = controller;
		setPreparing(true);
		setError(null);
		const command = {
			schema_version: 1,
			project_id: run.project_id,
			report_run_id: run.id,
			expected_revision: run.revision,
			key: crypto.randomUUID(),
		};
		try {
			const raw = await client.query(
				"draft/preview",
				command,
				scope,
				controller.signal,
			);
			if (
				instance === lifetime.current &&
				transferEnabled.current &&
				client.isCurrentScope(scope)
			) {
				const value = readDraftPreview(raw, command, client.origin);
				setReceipt(null);
				if (value.alreadyPresent) {
					setPresent(value);
					setPreview(null);
				} else {
					setPresent(null);
					if (
						(reportOnly
							? value.changes.length === 0
							: reviewedSelection &&
								value.changes.every((row) => row.before === 0)) &&
						value.phaseConflicts.length === 0
					) {
						await confirm(value);
					} else {
						setPreview(value);
					}
				}
			}
		} catch (cause) {
			if (instance === lifetime.current) {
				if (
					cause instanceof ApiError &&
					([401, 403].includes(cause.status) ||
						cause.code === "session_changed")
				)
					recheck();
				else setError(cause);
			}
		} finally {
			if (flight.current === controller) {
				flight.current = null;
				if (instance === lifetime.current) setPreparing(false);
			}
		}
	}
	const language = locale.startsWith("de") ? "de" : "en";
	async function confirm(preview: DraftPreview, continueToInquiry = false) {
		if (!transferEnabled.current || !client.isCurrentScope(scope)) return;
		const instance = lifetime.current;
		const reply = await operations.start("draft/apply", {
			expected_revision: run.revision,
			report_run_id: run.id,
			expected_draft_sha256: preview.draftSha256,
		});
		applyReceipt(reply, instance, continueToInquiry);
	}
	function applyReceipt(
		reply: PlanningReply | undefined,
		instance: number,
		continueToInquiry = false,
	) {
		if (
			reply?.path !== "draft/apply" ||
			instance !== lifetime.current ||
			!client.isCurrentScope(scope)
		)
			return;
		confirmed.current = { key: reply.intent.key, receipt: reply.receipt };
		setReceipt(reply.receipt);
		if (!reportOnly && reply.receipt.active !== false)
			document.body.dispatchEvent(
				new CustomEvent("wc-blocks_added_to_cart", { bubbles: true }),
			);
		setPreview(null);
		setError(null);
		if (
			continueToInquiry &&
			currentReport.current &&
			reply.receipt.active !== false &&
			reply.receipt.inquiryUrls
		)
			window.location.assign(reply.receipt.inquiryUrls[language]);
	}
	async function retry(record: PlanningIntent) {
		if (retryBlocked || !currentReport.current || !client.isCurrentScope(scope))
			return;
		setCheckedBody(null);
		const instance = lifetime.current;
		applyReceipt(await operations.retry(record), instance);
	}
	const retired = current && receipt?.active === false;
	const ready = current && !retired ? (receipt ?? present) : null;
	const readyUrls = ready?.urls;
	const inquiryUrl =
		ready?.inquiryUrls?.[language] ??
		(reportOnly ? readyUrls?.[language] : undefined);
	const operationError =
		operations.intent?.path === "draft/apply" &&
		readPlanningOperation("draft/apply", operations.intent.body)
			.report_run_id === run.id
			? operations.error
			: null;
	const failure = !current || readyUrls ? null : (error ?? operationError),
		busy = preparing || checking || operations.busy || operations.checking;
	const transferBusy = busy || transferBlocked;
	const retryBlocked =
		busy ||
		(record !== null && checkedBody !== record.body) ||
		blocked ||
		operations.storageFailed ||
		operations.records.some(
			(other) => other !== record && other.resultId === null,
		);
	const addLabel = reportOnly
		? __("Attach report to inquiry", "linker-tools")
		: reviewedSelection
			? __("Add to solution draft", "linker-tools")
			: __("Add selected products to solution draft", "linker-tools");
	return (
		<section className="sc-draft-operation">
			{!reportOnly && (
				<p>
					{__(
						"These are the products selected in this report. Adding them does not replace any outstanding engineering checks.",
						"linker-tools",
					)}
				</p>
			)}
			{readyUrls ? (
				<>
					{receipt && (
						<p role="status">
							{reportOnly
								? __(
										"Report ready to include with your inquiry.",
										"linker-tools",
									)
								: __(
										"Selected products added to solution draft.",
										"linker-tools",
									)}
						</p>
					)}
					<div className="sc-actions">
						{inquiryUrl && (
							<a className="sc-button sc-primary" href={inquiryUrl}>
								{__("Continue to inquiry", "linker-tools")}
							</a>
						)}
						{!reportOnly && (
							<a
								className={inquiryUrl ? "sc-button" : "sc-button sc-primary"}
								href={readyUrls[language]}
							>
								{__("View solution draft", "linker-tools")}
							</a>
						)}
						<button
							type="button"
							className="sc-button"
							disabled={transferBusy || !current}
							onClick={() => {
								setReceipt(null);
								setPresent(null);
								void prepare();
							}}
						>
							{addLabel}
						</button>
					</div>
				</>
			) : record && current && !retired ? (
				<>
					<p>
						{__(
							"The previous transfer is not yet confirmed. Retry the same transfer.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="sc-button sc-primary"
						disabled={retryBlocked}
						onClick={() => void retry(record)}
					>
						{__("Retry transfer", "linker-tools")}
					</button>
				</>
			) : (
				<>
					{!current && (
						<Notice>
							{reportOnly
								? __(
										"Generate a report for the current project before attaching it.",
										"linker-tools",
									)
								: __(
										"Generate a report for the project's current saved inputs before adding products.",
										"linker-tools",
									)}
						</Notice>
					)}
					{retired && !preview && (
						<Notice>
							{__(
								"This report is no longer in your solution draft.",
								"linker-tools",
							)}
						</Notice>
					)}
					{!preview ? (
						<button
							type="button"
							className="sc-button sc-primary"
							disabled={
								transferBusy ||
								!current ||
								operations.storageFailed ||
								Boolean(record)
							}
							onClick={() => void prepare()}
						>
							{preparing ? __("Preparing changes…", "linker-tools") : addLabel}
						</button>
					) : (
						<>
							{preview.changes.length > 0 && (
								<>
									<p>
										{__(
											"Review the changes to this project's products in your solution draft.",
											"linker-tools",
										)}
									</p>
									<div className="sc-report-table">
										<table className="sc-transfer-lines">
											<thead>
												<tr>
													<th>{__("Product", "linker-tools")}</th>
													<th>{__("Current quantity", "linker-tools")}</th>
													<th>{__("New quantity", "linker-tools")}</th>
												</tr>
											</thead>
											<tbody>
												{preview.changes.map((row) => (
													<tr key={row.productId}>
														<td>{row.label}</td>
														<td>{row.before}</td>
														<td>{row.after}</td>
													</tr>
												))}
											</tbody>
										</table>
									</div>
								</>
							)}
							{preview.phaseConflicts.map((conflict, index) => (
								<Notice key={index}>
									{conflict.unit && <strong>{conflict.unit}: </strong>}
									{sprintf(
										// translators: 1: inverter phase count, 2: required grid phase count.
										__(
											"Grid phase mismatch. Selected inverter: %1$d. Project requirement: %2$d. You can send an inquiry to discuss the configuration.",
											"linker-tools",
										),
										conflict.actual,
										conflict.required,
									)}
								</Notice>
							))}
							<div className="sc-actions">
								{preview.inquiryUrls && (
									<button
										type="button"
										className="sc-button sc-primary"
										disabled={
											transferBusy || !current || operations.storageFailed
										}
										onClick={() => void confirm(preview, true)}
									>
										{__("Confirm and continue to inquiry", "linker-tools")}
									</button>
								)}
								<button
									type="button"
									className={
										preview.inquiryUrls ? "sc-button" : "sc-button sc-primary"
									}
									disabled={
										transferBusy || !current || operations.storageFailed
									}
									onClick={() => void confirm(preview)}
								>
									{operations.busy
										? reportOnly
											? __("Attaching report…", "linker-tools")
											: __("Adding selected products…", "linker-tools")
										: preview.inquiryUrls
											? __("Add to solution draft", "linker-tools")
											: reportOnly
												? addLabel
												: __("Confirm changes", "linker-tools")}
								</button>
							</div>
						</>
					)}
				</>
			)}
			{Boolean(failure) && (
				<Notice error>
					{failure instanceof ApiError && failure.code === "handoff_incomplete"
						? __(
								"Quantities have not been determined for some selected products. Update the equipment selection and generate a new report.",
								"linker-tools",
							)
						: failure instanceof ApiError &&
							  failure.code === "planning_draft_changed"
							? __(
									"Your solution draft has changed. Refresh this page and try again.",
									"linker-tools",
								)
							: record && record.resultId === null
								? __(
										"The previous transfer is not yet confirmed. Retry the same transfer.",
										"linker-tools",
									)
								: __(
										"The selected products could not be added. Review your solution draft and try again.",
										"linker-tools",
									)}
				</Notice>
			)}
		</section>
	);
}
