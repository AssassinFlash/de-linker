import { EnergyError } from "./EnergyError.tsx";
import { ApiError } from "../../data/protocol.ts";
import { runStateLabel } from "./planningLabels.ts";
import { REPORT_TASK } from "../../data/planningReport.ts";
import { useEffect, useRef, useState } from "react";
import { DraftTransferButton } from "./DraftTransferButton.tsx";
import type { usePlanningOperations } from "../../data/usePlanningOperations.ts";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { ReportSection } from "../../data/planningReport.ts";
import { reportFromRun } from "../../data/planningReport.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

function SectionContent({ section }: { section: ReportSection }) {
	return (
		<>
			{section.paragraphs.map((p, i) => (
				<p key={i}>{p}</p>
			))}
			{section.rows.length > 0 && (
				<dl className="lp-field-summary">
					{section.rows.map((row, i) => (
						<div key={i}>
							<dt>{row.label}</dt>
							<dd>
								{row.href ? (
									<a href={row.href} target="_blank" rel="noreferrer">
										{row.value}
									</a>
								) : (
									row.value
								)}
							</dd>
						</div>
					))}
				</dl>
			)}
			{section.table && (
				<div className="lp-table-scroll">
					<table className="lp-data-table">
						<thead>
							<tr>
								{section.table.columns.map((label, i) => (
									<th key={i}>{label}</th>
								))}
							</tr>
						</thead>
						<tbody>
							{section.table.rows.map((row, i) => (
								<tr key={i}>
									{row.map((cell, j) => (
										<td key={j}>{cell}</td>
									))}
								</tr>
							))}
						</tbody>
					</table>
				</div>
			)}
		</>
	);
}
export function PlanningReportResult({
	run,
	client,
	scope,
	recheck,
	operations,
	current,
	blocked,
	locale,
}: {
	run: PlanningRun;
	client: PlannerClient;
	scope: string;
	recheck: () => void;
	operations: ReturnType<typeof usePlanningOperations>;
	current: boolean;
	blocked: boolean;
	locale: string;
}) {
	const report = run.result ? reportFromRun(run) : null,
		asset = run.result ? readObject(run.result.prepared_asset) : null;
	const [busy, setBusy] = useState(false),
		[error, setError] = useState(false);
	const lifetime = useRef(0),
		objectUrl = useRef<string | null>(null),
		flight = useRef<AbortController | null>(null);
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
			flight.current?.abort();
			if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
			objectUrl.current = null;
		};
	}, [run.id, scope]);
	async function download() {
		if (busy || !report || !asset || !client.isCurrentScope(scope)) return;
		const instance = lifetime.current,
			controller = new AbortController();
		flight.current = controller;
		setBusy(true);
		setError(false);
		try {
			const blob = await client.reportPdf(
				run.project_id,
				String(asset.id),
				scope,
				controller.signal,
			);
			if (instance !== lifetime.current || !client.isCurrentScope(scope))
				return;
			if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
			objectUrl.current = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = objectUrl.current;
			link.download = `linker-planning-${run.project_id}-r${run.revision}-${report.locale}.pdf`;
			link.click();
		} catch (cause) {
			if (instance === lifetime.current) {
				if (
					cause instanceof ApiError &&
					([401, 403].includes(cause.status) ||
						cause.code === "session_changed")
				)
					recheck();
				setError(true);
			}
		} finally {
			if (flight.current === controller) flight.current = null;
			if (instance === lifetime.current) setBusy(false);
		}
	}
	if (!report)
		return (
			<div className="lp-run-result">
				<h3>{__("Planning report", "linker-tools")}</h3>
				<p role="status">{runStateLabel(run.state, REPORT_TASK)}</p>
				{run.error && (
					<EnergyError
						error={
							new ApiError(422, String(run.error.code ?? "execution_failed"))
						}
					/>
				)}
			</div>
		);
	return (
		<article className="lp-run-result">
			<div className="lp-run-heading">
				<div>
					<h3>{report.title}</h3>
					<p>{report.subtitle}</p>
					<p>
						<time dateTime={report.generated_at}>
							{new Intl.DateTimeFormat(report.locale, {
								dateStyle: "medium",
								timeStyle: "short",
								timeZone: "UTC",
							}).format(new Date(report.generated_at))}{" "}
							UTC
						</time>
					</p>
				</div>
				<button
					type="button"
					className="lp-button"
					disabled={busy || !client.isCurrentScope(scope)}
					onClick={() => void download()}
				>
					{__("Download PDF", "linker-tools")}
				</button>
			</div>
			{error && (
				<Notice error>
					{__("The PDF could not be downloaded. Try again.", "linker-tools")}
				</Notice>
			)}
			{report.sections.some(
				(section) => section.id === "bom" && section.table?.rows.length,
			) && (
				<DraftTransferButton
					run={run}
					client={client}
					scope={scope}
					operations={operations}
					current={current}
					blocked={blocked}
					locale={locale}
					recheck={recheck}
				/>
			)}
			{report.sections.map((section) =>
				section.id.startsWith("check-") ||
				["basis", "conditions"].includes(section.id) ? (
					<details key={section.id} className="lp-comparison">
						<summary>{section.title}</summary>
						<SectionContent section={section} />
					</details>
				) : (
					<section key={section.id} className="lp-scenario-block">
						<h4>{section.title}</h4>
						<SectionContent section={section} />
					</section>
				),
			)}
		</article>
	);
}
