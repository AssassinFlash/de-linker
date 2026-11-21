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
import {
	reportFromRun,
	reportLanguageDiffers,
} from "../../data/planningReport.ts";
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
				<dl className="sc-field-summary">
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
				<>
					<div className="sc-table-scroll sc-report-table">
						<table className="sc-data-table">
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
					<ol className="sc-report-cards">
						{section.table.rows.map((row, i) => (
							<li key={i}>
								<dl>
									{row.map((cell, j) => (
										<div key={j}>
											<dt>{section.table?.columns[j]}</dt>
											<dd>{cell}</dd>
										</div>
									))}
								</dl>
							</li>
						))}
					</ol>
				</>
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
		asset = run.result ? readObject(run.result.prepared_asset) : null,
		csv = run.result?.prepared_attachments
			? readObject(
					readObject(run.result.prepared_attachments).bill_of_materials_csv,
				)
			: null,
		ruleCsv =
			run.result?.prepared_attachments &&
			readObject(run.result.prepared_attachments).country_rule_review_csv
				? readObject(
						readObject(run.result.prepared_attachments).country_rule_review_csv,
					)
				: null,
		seriesCsv =
			run.result?.prepared_attachments &&
			readObject(run.result.prepared_attachments).pv_series_csv
				? readObject(readObject(run.result.prepared_attachments).pv_series_csv)
				: null;
	const [busy, setBusy] = useState(false),
		[error, setError] = useState(false);
	const lifetime = useRef(0),
		objectUrl = useRef<string | null>(null),
		flight = useRef<AbortController | null>(null);
	useEffect(() => {
		lifetime.current++;
		// A different report run now occupies this component: the replaced
		// run's in-flight download never reaches its finally-reset, so release
		// its busy and error state here rather than leaving the button locked.
		setBusy(false);
		setError(false);
		return () => {
			lifetime.current++;
			flight.current?.abort();
			if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
			objectUrl.current = null;
		};
	}, [run.id, scope]);
	async function download(format: "pdf" | "materials" | "rules" | "series") {
		const file =
			format === "pdf"
				? asset
				: format === "materials"
					? csv
					: format === "rules"
						? ruleCsv
						: seriesCsv;
		if (busy || !report || !file || !client.isCurrentScope(scope)) return;
		const instance = lifetime.current,
			controller = new AbortController();
		flight.current = controller;
		setBusy(true);
		setError(false);
		try {
			const blob =
				format !== "pdf"
					? await client.reportCsv(
							run.project_id,
							String(file.id),
							scope,
							String(file.content_sha256),
							controller.signal,
							format === "series",
						)
					: await client.reportPdf(
							run.project_id,
							String(file.id),
							scope,
							controller.signal,
							String(file.content_sha256),
						);
			if (instance !== lifetime.current || !client.isCurrentScope(scope))
				return;
			if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
			objectUrl.current = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = objectUrl.current;
			const suffix =
				format === "rules"
					? "-country-rules"
					: format === "series"
						? "-pv-strings"
						: "";
			link.download = `linker-planning-${run.project_id}-r${run.revision}-${report.locale}${suffix}.${format === "pdf" ? "pdf" : "csv"}`;
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
			<div className="sc-run-result sc-work-panel">
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
	const languageNotice =
		report.locale === "en"
			? __("Report language: English", "linker-tools")
			: __("Report language: German", "linker-tools");
	return (
		<article className="sc-run-result sc-report-detail">
			{!current && (
				<div className="sc-notice" data-report-outdated="" role="status">
					<p>
						{__(
							"This report describes an earlier version of the project.",
							"linker-tools",
						)}
					</p>
				</div>
			)}
			<header className="sc-run-heading sc-work-panel sc-report-heading">
				<div>
					<h3 lang={report.locale}>{report.title}</h3>
					<p lang={report.locale}>{report.subtitle}</p>
					{reportLanguageDiffers(report.locale, locale) && (
						<p role="status" lang={locale}>
							{languageNotice}
						</p>
					)}
					<p lang={report.locale}>
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
			</header>
			<div className="sc-report-detail-layout">
				<aside className="sc-report-actions sc-work-panel">
					<div className="sc-report-downloads">
						<button
							type="button"
							className="sc-button sc-primary"
							disabled={busy || !client.isCurrentScope(scope)}
							onClick={() => void download("pdf")}
						>
							{__("Download PDF", "linker-tools")}
						</button>
						{csv && (
							<button
								type="button"
								className="sc-button"
								disabled={busy || !client.isCurrentScope(scope)}
								onClick={() => void download("materials")}
							>
								{__("Download bill of materials (CSV)", "linker-tools")}
							</button>
						)}
						{ruleCsv && (
							<button
								type="button"
								className="sc-button"
								disabled={busy || !client.isCurrentScope(scope)}
								onClick={() => void download("rules")}
							>
								{__("Download country rule review (CSV)", "linker-tools")}
							</button>
						)}
						{seriesCsv && (
							<button
								type="button"
								className="sc-button"
								disabled={busy || !client.isCurrentScope(scope)}
								onClick={() => void download("series")}
							>
								{__("Download PV string intervals (CSV)", "linker-tools")}
							</button>
						)}
					</div>
					{seriesCsv && (
						<p>
							{__(
								"The PV string CSV has one row per string and time interval. The module condition lists follow the order of module IDs in that row.",
								"linker-tools",
							)}
						</p>
					)}
					{error && (
						<Notice error>
							{__(
								"The file could not be downloaded. Try again.",
								"linker-tools",
							)}
						</Notice>
					)}
					{(typeof run.result?.has_draft_items === "boolean"
						? run.result.has_draft_items
						: report.sections.some(
								(section) => section.id === "bom" && section.table?.rows.length,
							)) && (
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
				</aside>
				<div className="sc-report-content">
					{report.sections.map((section) =>
						section.id.startsWith("check-") ||
						["basis", "conditions"].includes(section.id) ? (
							<details
								key={section.id}
								className="sc-disclosure sc-work-panel"
								lang={report.locale}
							>
								<summary>{section.title}</summary>
								<SectionContent section={section} />
							</details>
						) : (
							<section
								key={section.id}
								className="sc-scenario-block sc-work-panel"
								lang={report.locale}
							>
								<h4 className="sc-work-panel-heading">{section.title}</h4>
								<SectionContent section={section} />
							</section>
						),
					)}
				</div>
			</div>
		</article>
	);
}
