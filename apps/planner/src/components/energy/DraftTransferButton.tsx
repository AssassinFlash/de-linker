import { useEffect, useMemo, useRef, useState } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import {
	readDraftPreview,
	readDraftReceipt,
} from "../../data/draftTransfer.ts";
import type { DraftPreview, DraftReceipt } from "../../data/draftTransfer.ts";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import { readPlanningOperation } from "../../data/planningProtocol.ts";
import type { usePlanningOperations } from "../../data/usePlanningOperations.ts";
import { ApiError } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

/** Preview is read-only. Only explicit confirmation submits a durable Woo intent. */
export function DraftTransferButton({
	run,
	client,
	scope,
	operations,
	current,
	blocked,
	locale,
	recheck,
}: {
	run: PlanningRun;
	client: PlannerClient;
	scope: string;
	operations: ReturnType<typeof usePlanningOperations>;
	current: boolean;
	blocked: boolean;
	locale: string;
	recheck: () => void;
}) {
	const [preview, setPreview] = useState<DraftPreview | null>(null),
		[preparing, setPreparing] = useState(false),
		[checking, setChecking] = useState(false),
		[receipt, setReceipt] = useState<DraftReceipt | null>(null),
		[error, setError] = useState<unknown>(null),
		[presentUrls, setPresentUrls] = useState<Readonly<
			Record<"en" | "de", string>
		> | null>(null);
	const confirmed = useRef<{ key: string; receipt: DraftReceipt } | null>(null),
		flight = useRef<AbortController | null>(null),
		lifetime = useRef(0);
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
					!["applied", "not_applied"].includes(String(status.state))
				)
					throw new ApiError(502, "invalid_draft_receipt");
				if (status.state === "applied") {
					const value = readDraftReceipt(
						status.receipt,
						readPlanningOperation(record.path, record.body),
						client.origin,
					);
					if (record.resultId !== null && record.resultId !== value.handoffId)
						throw new ApiError(502, "invalid_draft_receipt");
					confirmed.current = { key: record.key, receipt: value };
					setReceipt(value);
					setError(null);
					await operations.acknowledgeReadback(record, value.handoffId);
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
				if (admitted()) setChecking(false);
			});
		return () => {
			active = false;
			controller.abort();
		};
	}, [record?.body, record?.resultId, operations.busy, client, scope]);

	async function prepare() {
		if (
			flight.current ||
			blocked ||
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
			if (instance === lifetime.current && client.isCurrentScope(scope)) {
				const value = readDraftPreview(raw, command, client.origin);
				if (value.alreadyPresent) {
					setPresentUrls(value.urls);
					setPreview(null);
				} else {
					setPreview(value);
					setPresentUrls(null);
					setReceipt(null);
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
	async function confirm() {
		if (!preview || blocked || !current) return;
		const instance = lifetime.current;
		const reply = await operations.start("draft/apply", {
			expected_revision: run.revision,
			report_run_id: run.id,
			expected_draft_sha256: preview.draftSha256,
		});
		if (
			reply?.path === "draft/apply" &&
			instance === lifetime.current &&
			client.isCurrentScope(scope)
		) {
			confirmed.current = { key: reply.intent.key, receipt: reply.receipt };
			setReceipt(reply.receipt);
			setPreview(null);
			setError(null);
		}
	}
	const readyUrls = receipt?.urls ?? presentUrls;
	const operationError =
		operations.intent?.path === "draft/apply" &&
		readPlanningOperation("draft/apply", operations.intent.body)
			.report_run_id === run.id
			? operations.error
			: null;
	const failure = receipt || presentUrls ? null : (error ?? operationError),
		busy =
			preparing ||
			checking ||
			operations.busy ||
			operations.checking ||
			blocked;
	return (
		<section className="lp-scenario-block">
			<p>
				{__(
					"These are the products selected in this report. Adding them does not replace any outstanding engineering checks.",
					"linker-tools",
				)}
			</p>
			{readyUrls ? (
				<>
					{receipt && (
						<p role="status">
							{__("Selected products added to solution draft.", "linker-tools")}
						</p>
					)}
					<a
						className="lp-button"
						href={readyUrls[locale.startsWith("de") ? "de" : "en"]}
					>
						{__("View solution draft", "linker-tools")}
					</a>
					<button
						type="button"
						className="lp-button lp-button-secondary"
						disabled={busy || !current}
						onClick={() => {
							setReceipt(null);
							setPresentUrls(null);
							void prepare();
						}}
					>
						{__("Add selected products to solution draft", "linker-tools")}
					</button>
				</>
			) : record ? (
				<>
					<p>
						{__(
							"The previous transfer is not yet confirmed. Retry the same transfer.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-button"
						disabled={busy || operations.storageFailed}
						onClick={() => void operations.retry(record)}
					>
						{__("Retry transfer", "linker-tools")}
					</button>
				</>
			) : (
				<>
					{!current && (
						<Notice>
							{__(
								"Generate a report for the project's current saved inputs before adding products.",
								"linker-tools",
							)}
						</Notice>
					)}
					{!preview ? (
						<button
							type="button"
							className="lp-button"
							disabled={busy || !current || operations.storageFailed}
							onClick={() => void prepare()}
						>
							{preparing
								? __("Preparing changes…", "linker-tools")
								: __("Add selected products to solution draft", "linker-tools")}
						</button>
					) : (
						<>
							<p>
								{__(
									"Review the changes to this project's products in your solution draft.",
									"linker-tools",
								)}
							</p>
							<div className="lp-table-scroll">
								<table className="lp-data-table">
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
							<button
								type="button"
								className="lp-button"
								disabled={busy || !current || operations.storageFailed}
								onClick={() => void confirm()}
							>
								{operations.busy
									? __("Adding selected products…", "linker-tools")
									: __("Confirm changes", "linker-tools")}
							</button>
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
