import { readBrief } from "../../domain/brief.ts";
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { PlanningRun, RunSummary } from "../../data/planningProtocol.ts";
import {
	REPORT_TASK,
	reportFromRun,
	reportLanguageDiffers,
	type PlanningReport,
	type ReportSection,
} from "../../data/planningReport.ts";
import {
	ApiError,
	type JsonObject,
	type Project,
	type Session,
} from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import type { usePlanningOperations } from "../../data/usePlanningOperations.ts";
import { __, sprintf } from "../../i18n.ts";
import { ReviewInquiry } from "./ReviewInquiry.tsx";
import { runStateLabel } from "../energy/planningLabels.ts";

function ReportContent({ section }: { section: ReportSection }) {
	return (
		<>
			{section.paragraphs.map((text, index) => (
				<p className="sc-muted" key={index}>
					{text}
				</p>
			))}
			{section.rows.length > 0 && (
				<dl>
					{section.rows.map((row, index) => (
						<div className="sc-summary" key={index}>
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
				<div
					className="sc-report-table"
					tabIndex={0}
					role="region"
					aria-label={section.title}
				>
					<table className={section.id === "bom" ? "sc-bom-table" : undefined}>
						<thead>
							<tr>
								{section.table.columns.map((column, index) => (
									<th scope="col" key={index}>
										{column}
									</th>
								))}
							</tr>
						</thead>
						<tbody>
							{section.table.rows.map((row, index) => (
								<tr key={index}>
									{row.map((cell, column) => (
										<td key={column}>
											{section.id === "bom" && (
												<span className="sc-bom-label" aria-hidden="true">
													{section.table?.columns[column]}
												</span>
											)}
											{cell}
										</td>
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

function ReportPreview({ report }: { report: PlanningReport }) {
	return (
		<details>
			<summary>{__("Preview report", "linker-tools")}</summary>
			<div lang={report.locale}>
				{report.sections.map((section) => (
					<section key={section.id}>
						<h3>{section.title}</h3>
						<ReportContent section={section} />
					</section>
				))}
			</div>
		</details>
	);
}

function ReportDownloads({
	run,
	report,
	client,
	scope,
	recheck,
	askGenie,
	children,
}: {
	run: PlanningRun;
	report: PlanningReport;
	client: PlannerClient;
	scope: string;
	recheck: () => void;
	askGenie: () => void;
	children?: ReactNode;
}) {
	const [busy, setBusy] = useState(false),
		[error, setError] = useState(false);
	const attachments = run.result?.prepared_attachments
		? readObject(run.result.prepared_attachments)
		: null;
	const lifetime = useRef(0),
		flight = useRef<AbortController | null>(null),
		objectUrl = useRef<string | null>(null);
	useEffect(() => {
		lifetime.current++;
		setBusy(false);
		setError(false);
		return () => {
			lifetime.current++;
			flight.current?.abort();
			flight.current = null;
			if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
			objectUrl.current = null;
		};
	}, [run.id, scope]);
	async function download(format: "pdf" | "materials" | "rules" | "series") {
		if (!run.result || busy || flight.current || !client.isCurrentScope(scope))
			return;
		const raw =
			format === "pdf"
				? run.result.prepared_asset
				: attachments?.[
						format === "materials"
							? "bill_of_materials_csv"
							: format === "rules"
								? "country_rule_review_csv"
								: "pv_series_csv"
					];
		if (!raw) return;
		const file = readObject(raw),
			controller = new AbortController(),
			instance = lifetime.current;
		flight.current = controller;
		setBusy(true);
		setError(false);
		try {
			const blob =
				format === "pdf"
					? await client.reportPdf(
							run.project_id,
							String(file.id),
							scope,
							controller.signal,
							String(file.content_sha256),
						)
					: await client.reportCsv(
							run.project_id,
							String(file.id),
							scope,
							String(file.content_sha256),
							controller.signal,
							format === "series",
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
			if (instance !== lifetime.current) return;
			if (
				cause instanceof ApiError &&
				([401, 403].includes(cause.status) || cause.code === "session_changed")
			)
				recheck();
			if (client.isCurrentScope(scope)) setError(true);
		} finally {
			if (flight.current === controller) flight.current = null;
			if (instance === lifetime.current) setBusy(false);
		}
	}
	return (
		<>
			<div className="sc-actions">
				<button
					type="button"
					className="sc-button"
					disabled={busy || !client.isCurrentScope(scope)}
					onClick={() => void download("pdf")}
				>
					{__("Download PDF", "linker-tools")}
				</button>
				{Boolean(attachments?.bill_of_materials_csv) && (
					<button
						type="button"
						className="sc-button"
						disabled={busy || !client.isCurrentScope(scope)}
						onClick={() => void download("materials")}
					>
						{__("Download bill of materials (CSV)", "linker-tools")}
					</button>
				)}
				{Boolean(attachments?.country_rule_review_csv) && (
					<button
						type="button"
						className="sc-button"
						disabled={busy || !client.isCurrentScope(scope)}
						onClick={() => void download("rules")}
					>
						{__("Download country rule review (CSV)", "linker-tools")}
					</button>
				)}
				{Boolean(attachments?.pv_series_csv) && (
					<button
						type="button"
						className="sc-button"
						disabled={busy || !client.isCurrentScope(scope)}
						onClick={() => void download("series")}
					>
						{__("Download PV string intervals (CSV)", "linker-tools")}
					</button>
				)}
				<button
					type="button"
					className="sc-button"
					data-linker-genie-open
					data-linker-genie-planning={run.id}
					disabled={!client.isCurrentScope(scope)}
					onClick={askGenie}
				>
					{__("Ask Genie", "linker-tools")}
				</button>
				{children}
			</div>
			{error && (
				<p role="alert">
					{__("The file could not be downloaded. Try again.", "linker-tools")}
				</p>
			)}
		</>
	);
}

interface ReportHistory {
	items: readonly RunSummary[];
	selected: string | null;
	select: (id: string | null) => void;
	run: PlanningRun | null;
	reading: boolean;
	readFailed: boolean;
	unavailable: boolean;
	retryRead: () => void;
	hasMore: boolean;
	loading: boolean;
	loadFailed: boolean;
	loadMore: () => void;
}

export function ReviewProposal({
	inputs,
	preliminary = false,
	project,
	summary,
	materials,
	run,
	history,
	client,
	session,
	operations,
	locale,
	blocked,
	current,
	generate,
	askGenie,
	recheck,
}: {
	project: Project;
	summary?: ReactNode;
	materials?: ReactNode;
	inputs: JsonObject;
	preliminary?: boolean;
	run: PlanningRun | null;
	history?: ReportHistory;
	client: PlannerClient;
	session: Session;
	operations: ReturnType<typeof usePlanningOperations>;
	locale: string;
	blocked: boolean;
	current: boolean;
	generate: (logo: string | null) => void;
	askGenie: (run: PlanningRun) => void;
	recheck: () => void;
}) {
	const scope = session.query_scope;
	const report = run?.result ? reportFromRun(run) : null;
	const selected = history?.selected != null;
	const earlierRun = history?.run?.state === "succeeded" ? history.run : null;
	const earlierReport = earlierRun?.result ? reportFromRun(earlierRun) : null;
	const [logo, setLogo] = useState<string | null>(null),
		[logoError, setLogoError] = useState(false),
		[reading, setReading] = useState(false);
	const reader = useRef<FileReader | null>(null);
	useEffect(
		() => () => {
			reader.current?.abort();
			reader.current = null;
		},
		[],
	);
	const waiting = Boolean(
		run && ["queued", "running", "retry_wait"].includes(run.state),
	);
	const disabled =
		blocked ||
		operations.busy ||
		operations.checking ||
		waiting ||
		reading ||
		logoError;
	const logoField = (
		<label className="sc-field">
			<span>{__("Your logo on the PDF (optional)", "linker-tools")}</span>
			<input
				type="file"
				accept="image/png,image/jpeg"
				disabled={blocked || operations.busy}
				onChange={(event) => {
					reader.current?.abort();
					reader.current = null;
					setLogo(null);
					setReading(false);
					setLogoError(false);
					const file = event.currentTarget.files?.[0];
					if (!file) return;
					if (
						file.size > 500000 ||
						!["image/png", "image/jpeg"].includes(file.type)
					) {
						setLogoError(true);
						return;
					}
					const next = new FileReader();
					reader.current = next;
					setReading(true);
					next.onload = () => {
						if (reader.current === next && typeof next.result === "string") {
							setLogo(next.result);
							setReading(false);
						}
					};
					next.onerror = () => {
						if (reader.current === next) {
							setLogoError(true);
							setReading(false);
						}
					};
					next.readAsDataURL(file);
				}}
			/>
			<small>{__("PNG or JPG, up to 500 kB.", "linker-tools")}</small>
			{logoError && (
				<small role="alert">
					{__(
						"The logo could not be used. Choose a PNG or JPG of up to 500 kB.",
						"linker-tools",
					)}
				</small>
			)}
		</label>
	);
	const reportOnly = run?.result?.has_report_only_handoff === true;
	const transferable =
		run?.result &&
		report &&
		(reportOnly ||
			(typeof run.result.has_draft_items === "boolean"
				? run.result.has_draft_items
				: report.sections.some(
						(section) => section.id === "bom" && section.table?.rows.length,
					)));
	const preliminaryBrief =
		inputs.brief &&
		(preliminary ||
			Object.keys(inputs).every(
				(key) => key === "brief" || key === "saved_solution_reference",
			))
			? readBrief(inputs.brief)
			: null;
	const hasHistory =
		history && (selected || history.items.length > 0 || history.hasMore);
	if (preliminaryBrief?.system_scope && (preliminary || (!run && !hasHistory))) {
		const label = {
			new_pv_storage: __("Solar and storage", "linker-tools"),
			storage_addition: __("Storage for existing PV", "linker-tools"),
			pv_only: __("Solar", "linker-tools"),
			storage_only: __("Storage", "linker-tools"),
		}[preliminaryBrief.system_scope];
		const direction = sprintf(__("Planned system: %s", "linker-tools"), label);
		return (
			<article className="sc-review">
				<ReviewInquiry
					key={`${project.id}:${project.revision}:${scope}:${direction}`}
					noteProjectId={
						preliminaryBrief.project_note.trim() ? project.id : undefined
					}
					direction={direction}
					client={client}
					scope={scope}
					operations={operations}
					locale={locale}
					blocked={blocked}
					recheck={recheck}
				/>
			</article>
		);
	}
	const transfer = transferable && run && current && (
		<ReviewInquiry
			key={`${run.id}:${scope}`}
			run={run}
			client={client}
			scope={scope}
			operations={operations}
			locale={locale}
			blocked={blocked}
			recheck={recheck}
		/>
	);

	return (
		<article className="sc-review">
			<header className="sc-section-head">
				<div>
					<h1>{__("Ready to discuss", "linker-tools")}</h1>
					<p>
						{__(
							"The selected configuration stays with the report and inquiry.",
							"linker-tools",
						)}
					</p>
				</div>
			</header>
			{!selected && run && !current && (
				<p className="sc-card sc-muted" role="status" data-report-outdated="">
					{__(
						"This report describes an earlier version of the project.",
						"linker-tools",
					)}
				</p>
			)}
			{transfer}
			{!selected && (!report || !current) && summary}
			{!selected && !report && materials}
			{!selected && !report && (
				<section className="sc-card">
					<h2>{__("Project report", "linker-tools")}</h2>
					<p>{project.title}</p>
					{run && <p role="status">{runStateLabel(run.state, REPORT_TASK)}</p>}
					{run?.error && (
						<p role="alert">
							{__(
								"The report could not be generated. Please try again.",
								"linker-tools",
							)}
						</p>
					)}
					{logoField}
					<div className="sc-actions">
						<button
							type="button"
							className="sc-button sc-primary"
							disabled={disabled}
							onClick={() => generate(logo)}
						>
							{__("Generate project report", "linker-tools")}
						</button>
					</div>
				</section>
			)}
			{!selected && report && run && (
				<>
					<section className="sc-card" lang={report.locale}>
						<h2>{report.title}</h2>
						<p className="sc-muted">{report.subtitle}</p>
						{reportLanguageDiffers(report.locale, locale) && (
							<p className="sc-muted" lang={locale}>
								{report.locale === "de"
									? __("Report language: German", "linker-tools")
									: __("Report language: English", "linker-tools")}
							</p>
						)}
						<time className="sc-muted" dateTime={report.generated_at}>
							{new Intl.DateTimeFormat(locale, {
								dateStyle: "medium",
								timeStyle: "short",
								timeZone: "UTC",
							}).format(new Date(report.generated_at))}{" "}
							UTC
						</time>
					</section>
					{report.sections
						.filter(
							(section) =>
								[
									"project",
									"pv",
									"energy",
									"bom",
									"existing-system",
									"retained-energy-baseline",
								].includes(section.id) ||
								section.id.startsWith("declared-equipment-demand"),
						)
						.map((section) => (
							<section
								className="sc-card"
								key={section.id}
								lang={report.locale}
							>
								<div className="sc-section-head">
									<h2>{section.title}</h2>
								</div>
								<ReportContent section={section} />
							</section>
						))}
					<div className="sc-review-actions">
						<section className="sc-card">
							<div className="sc-section-head">
								<div>
									<h2>{__("Project report", "linker-tools")}</h2>
									<p className="sc-muted">
										{__(
											"Project inputs, layout, equipment and selection basis.",
											"linker-tools",
										)}
									</p>
								</div>
							</div>
							{logoField}
							<ReportDownloads
								run={run}
								report={report}
								client={client}
								scope={scope}
								recheck={recheck}
								askGenie={() => askGenie(run)}
							>
								<button
									type="button"
									className="sc-button"
									disabled={disabled}
									onClick={() => generate(logo)}
								>
									{reportLanguageDiffers(report.locale, locale)
										? locale.startsWith("de")
											? __("Generate report in German", "linker-tools")
											: __("Generate report in English", "linker-tools")
										: __("Update project report", "linker-tools")}
								</button>
							</ReportDownloads>
							<ReportPreview report={report} />
						</section>
					</div>
				</>
			)}
			{hasHistory && (
				<section
					className="sc-card"
					aria-label={__("Calculation history", "linker-tools")}
				>
					<h2>{__("Calculation history", "linker-tools")}</h2>
					<div className="sc-actions">
						{history.items.map((item) => (
							<button
								type="button"
								className="sc-button"
								key={item.id}
								aria-pressed={history.selected === item.id}
								disabled={!client.isCurrentScope(scope)}
								onClick={() =>
									history.select(history.selected === item.id ? null : item.id)
								}
							>
								{sprintf(__("Revision %d", "linker-tools"), item.revision)}
								{" · "}
								{new Intl.DateTimeFormat(locale, {
									dateStyle: "short",
									timeStyle: "short",
								}).format(item.created_at * 1000)}
							</button>
						))}
						{selected && (
							<button
								type="button"
								className="sc-button"
								disabled={!client.isCurrentScope(scope)}
								onClick={() => history.select(null)}
							>
								{__("Close", "linker-tools")}
							</button>
						)}
						{history.hasMore && (
							<button
								type="button"
								className="sc-button"
								disabled={history.loading || !client.isCurrentScope(scope)}
								onClick={history.loadMore}
							>
								{__("Earlier calculations", "linker-tools")}
							</button>
						)}
					</div>
					{history.loadFailed && (
						<p role="alert">
							{__(
								"Saved calculation history could not be refreshed.",
								"linker-tools",
							)}
						</p>
					)}
					{history.reading && (
						<p role="status">
							{__("Reading the saved calculation…", "linker-tools")}
						</p>
					)}
					{selected && history.unavailable && (
						<p role="alert">
							{__(
								"The saved calculation details could not be verified for this response.",
								"linker-tools",
							)}
						</p>
					)}
					{history.readFailed && (
						<div role="alert">
							<p>
								{__(
									"The selected calculation could not be refreshed. Any visible state is the last confirmed response.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="sc-button"
								disabled={!client.isCurrentScope(scope)}
								onClick={history.retryRead}
							>
								{__("Refresh calculation status", "linker-tools")}
							</button>
						</div>
					)}
					{earlierRun && earlierReport && (
						<>
							<h3 lang={earlierReport.locale}>{earlierReport.title}</h3>
							<ReportDownloads
								run={earlierRun}
								report={earlierReport}
								client={client}
								scope={scope}
								recheck={recheck}
								askGenie={() => askGenie(earlierRun)}
							/>
							<ReportPreview report={earlierReport} />
						</>
					)}
				</section>
			)}
		</article>
	);
}
