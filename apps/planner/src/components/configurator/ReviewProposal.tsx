import {
	useCallback,
	useEffect,
	useId,
	useRef,
	useState,
	type ReactNode,
} from "react";
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
import { ProjectFacts, projectFacts } from "./ProjectFacts.tsx";
import { __, sprintf } from "../../i18n.ts";
import { EvidenceCard } from "../shared/EvidenceCard.tsx";
import { Icon } from "../Icon.tsx";
import { DraftTransferButton } from "../energy/DraftTransferButton.tsx";
import { runStateLabel } from "../energy/planningLabels.ts";

function isReportItemSection(section: ReportSection) {
	return ["bom", "site-materials", "pv-components"].includes(section.id);
}

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
						<div
							className={row.href ? "sc-report-citation" : "sc-summary"}
							key={index}
						>
							<dt>{row.label}</dt>
							<dd>
								{row.href ? (
									<EvidenceCard title={row.value} url={row.href} />
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
					<table
						className={
							isReportItemSection(section) ? "sc-bom-table" : undefined
						}
					>
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
										<td
											key={column}
											className={
												isReportItemSection(section) && column === 0
													? "whitespace-nowrap tabular-nums"
													: undefined
											}
										>
											{isReportItemSection(section) && (
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

function ReportItemSections({
	report,
	heading: Heading = "h2",
	materials,
}: {
	report: PlanningReport;
	heading?: "h2" | "h4";
	materials: ReactNode;
}) {
	return report.sections.filter(isReportItemSection).map((section, index) => (
		<section key={section.id} className="sc-card sc-report-items">
			<header className="sc-report-items-head">
				<Heading lang={report.locale}>{section.title}</Heading>
				{index === 0 && materials}
			</header>
			<div lang={report.locale}>
				<ReportContent section={section} />
			</div>
		</section>
	));
}

function ReportPreview({
	report,
	allowed,
	loadPdf,
}: {
	report: PlanningReport;
	allowed: boolean;
	loadPdf: (signal: AbortSignal) => Promise<Blob | null>;
}) {
	const dialog = useRef<HTMLDialogElement>(null);
	const request = useRef<AbortController | null>(null);
	const objectUrl = useRef<string | null>(null);
	const [pdfUrl, setPdfUrl] = useState<string | null>(null);
	const [pdfFailed, setPdfFailed] = useState(false);
	const [open, setOpen] = useState(false);
	const name = useId();

	const releasePdf = useCallback(() => {
		request.current?.abort();
		request.current = null;
		if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
		objectUrl.current = null;
	}, []);
	useEffect(() => releasePdf, [releasePdf]);

	async function preparePdf() {
		if (request.current) return;
		const controller = new AbortController();
		request.current = controller;
		setPdfFailed(false);
		try {
			const blob = await loadPdf(controller.signal);
			if (controller.signal.aborted) return;
			if (blob) {
				objectUrl.current = URL.createObjectURL(blob);
				setPdfUrl(objectUrl.current);
			} else {
				setPdfFailed(true);
			}
		} catch {
			if (!controller.signal.aborted) setPdfFailed(true);
		} finally {
			if (request.current === controller) request.current = null;
		}
	}
	return (
		<>
			<button
				type="button"
				className="sc-button sc-report-preview-button"
				disabled={!allowed}
				onClick={() => {
					dialog.current?.showModal();
					setOpen(true);
					void preparePdf();
				}}
			>
				{__("Preview report", "linker-tools")}
			</button>
			<dialog
				ref={dialog}
				className="sc-report-dialog"
				aria-labelledby={name}
				onClose={() => {
					releasePdf();
					setOpen(false);
					setPdfUrl(null);
					setPdfFailed(false);
				}}
			>
				<header className="sc-section-head">
					<h2 id={name} lang={report.locale}>
						{report.title}
					</h2>
					<button
						type="button"
						className="sc-button"
						onClick={() => dialog.current?.close()}
					>
						{__("Close", "linker-tools")}
					</button>
				</header>
				<div className="sc-report-pdf">
					{pdfUrl && allowed ? (
						<>
							<a
								className="sc-button"
								href={pdfUrl}
								target="_blank"
								rel="noopener noreferrer"
							>
								{__("Open report PDF", "linker-tools")}
							</a>
							<p className="sc-muted">
								{__(
									"The PDF shows the original layout and any logo saved with this report.",
									"linker-tools",
								)}
							</p>
						</>
					) : pdfFailed || !allowed ? (
						<>
							<p role="alert">
								{__("The report PDF could not be opened.", "linker-tools")}
							</p>
							{allowed && (
								<button
									type="button"
									className="sc-button"
									onClick={() => void preparePdf()}
								>
									{__("Try again", "linker-tools")}
								</button>
							)}
						</>
					) : (
						<p role="status">{__("Preparing PDF…", "linker-tools")}</p>
					)}
				</div>
				<section
					className="sc-report-readable"
					aria-label={__("Report details", "linker-tools")}
				>
					<div className="sc-report-preview" lang={report.locale}>
						<p className="sc-muted">{report.subtitle}</p>
						{open &&
							report.sections.map((section) => (
								<section key={section.id}>
									<h3>{section.title}</h3>
									<ReportContent section={section} />
								</section>
							))}
					</div>
				</section>
			</dialog>
		</>
	);
}

function ReportDownloads({
	run,
	report,
	client,
	scope,
	recheck,
	askGenie,
	suspended = false,
	children,
}: {
	run: PlanningRun;
	report: PlanningReport;
	client: PlannerClient;
	scope: string;
	recheck: () => void;
	askGenie: () => void;
	suspended?: boolean;
	children?: (files: {
		actions: ReactNode;
		materials: ReactNode;
		error: ReactNode;
	}) => ReactNode;
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
	}, [run.id, scope, suspended]);
	function readPdf(signal: AbortSignal) {
		const file = readObject(run.result?.prepared_asset);
		return client.reportPdf(
			run.project_id,
			String(file.id),
			scope,
			signal,
			String(file.content_sha256),
		);
	}
	function recheckAccess(cause: unknown) {
		if (
			cause instanceof ApiError &&
			([401, 403].includes(cause.status) || cause.code === "session_changed")
		)
			recheck();
	}
	async function loadPreviewPdf(signal: AbortSignal) {
		try {
			const blob = await readPdf(signal);
			return client.isCurrentScope(scope) ? blob : null;
		} catch (cause) {
			if (!signal.aborted) recheckAccess(cause);
			throw cause;
		}
	}
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
					? await readPdf(controller.signal)
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
			recheckAccess(cause);
			if (client.isCurrentScope(scope)) setError(true);
		} finally {
			if (flight.current === controller) flight.current = null;
			if (instance === lifetime.current) setBusy(false);
		}
	}
	const materials = Boolean(attachments?.bill_of_materials_csv) && (
		<button
			type="button"
			className="sc-button"
			disabled={busy || !client.isCurrentScope(scope)}
			onClick={() => void download("materials")}
		>
			{__("Download bill of materials (CSV)", "linker-tools")}
		</button>
	);
	const actions = (
		<>
			<ReportPreview
				key={`${run.id}:${scope}`}
				report={report}
				allowed={client.isCurrentScope(scope)}
				loadPdf={loadPreviewPdf}
			/>
			<button
				type="button"
				className="sc-button"
				disabled={busy || !client.isCurrentScope(scope)}
				onClick={() => void download("pdf")}
			>
				{__("Download PDF", "linker-tools")}
			</button>
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
		</>
	);
	const downloadError = error && (
		<p role="alert">
			{__("The file could not be downloaded. Try again.", "linker-tools")}
		</p>
	);
	return children ? (
		children({ actions, materials, error: downloadError })
	) : (
		<>
			<div className="sc-actions">
				{actions}
				{materials}
			</div>
			{downloadError}
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

export function reportCanTransfer(
	run: PlanningRun | null,
	report = run?.result ? reportFromRun(run) : null,
): boolean {
	if (!run?.result || !report) return false;
	return (
		run.result.has_report_only_handoff === true ||
		(typeof run.result.has_draft_items === "boolean"
			? run.result.has_draft_items
			: report.sections.some(
					(section) => section.id === "bom" && section.table?.rows.length,
				))
	);
}

export function ReviewProposal({
	project,
	inputs,
	run,
	history,
	client,
	session,
	operations,
	locale,
	blocked,
	transferBlocked = blocked,
	current,
	generate,
	askGenie,
	recheck,
}: {
	project: Project;
	inputs: JsonObject;
	run: PlanningRun | null;
	history?: ReportHistory;
	client: PlannerClient;
	session: Session;
	operations: ReturnType<typeof usePlanningOperations>;
	locale: string;
	blocked: boolean;
	transferBlocked?: boolean;
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
	const [logo, setLogo] = useState<{ name: string; data: string } | null>(null),
		[logoError, setLogoError] = useState(false),
		[reading, setReading] = useState(false);
	const reader = useRef<FileReader | null>(null);
	const logoInput = useRef<HTMLInputElement>(null);
	const resetLogo = () => {
		reader.current?.abort();
		reader.current = null;
		setLogo(null);
		setLogoError(false);
		setReading(false);
	};
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
		<div className="sc-report-logo">
			<label className="sc-field">
				<span>{__("Your logo on the PDF (optional)", "linker-tools")}</span>
				<span className="sc-file-picker">
					<span className="sc-file-button" aria-hidden="true">
						{__("Choose logo", "linker-tools")}
					</span>
					<span className="sc-file-name" aria-hidden="true">
						{logo?.name ?? __("No file chosen", "linker-tools")}
					</span>
					<input
						ref={logoInput}
						aria-label={__("Your logo on the PDF (optional)", "linker-tools")}
						type="file"
						accept="image/png,image/jpeg"
						disabled={blocked || operations.busy}
						onChange={(event) => {
							resetLogo();
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
								if (
									reader.current === next &&
									typeof next.result === "string"
								) {
									setLogo({ name: file.name, data: next.result });
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
				</span>
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
			{(logo || logoError || reading) && (
				<div className="sc-actions">
					{logo && (
						<img src={logo.data} alt={__("Report logo", "linker-tools")} />
					)}
					<button
						type="button"
						className="sc-button"
						disabled={blocked || operations.busy}
						onClick={() => {
							resetLogo();
							if (logoInput.current) {
								logoInput.current.value = "";
								logoInput.current.focus();
							}
						}}
					>
						{__("Remove logo", "linker-tools")}
					</button>
				</div>
			)}
		</div>
	);
	const reportOnly = run?.result?.has_report_only_handoff === true;
	const transferable = reportCanTransfer(run, report);

	const facts = projectFacts(inputs, locale);
	const overviewSections =
		current && report
			? report.sections.filter(
					(section) =>
						[
							"pv",
							"energy",
							"existing-system",
							"retained-energy-baseline",
						].includes(section.id) ||
						section.id.startsWith("declared-equipment-demand"),
				)
			: [];
	const reportDescription = __(
		"Project inputs, layout, equipment and selection basis.",
		"linker-tools",
	);
	const draftTransfer = transferable && run && (
		<section className="sc-draft-transfer">
			<h2>{__("Request a quotation", "linker-tools")}</h2>
			{selected && current && (
				<p>
					{sprintf(
						__(
							"Your inquiry uses the current report (revision %d).",
							"linker-tools",
						),
						run.revision,
					)}
				</p>
			)}
			{!reportOnly && (
				<p className="sc-muted">
					{__(
						"The selected equipment and project details are included.",
						"linker-tools",
					)}
				</p>
			)}
			<DraftTransferButton
				key={`${run.id}:${scope}`}
				run={run}
				client={client}
				scope={scope}
				operations={operations}
				reportOnly={reportOnly}
				current={current}
				blocked={transferBlocked}
				locale={locale}
				recheck={recheck}
			/>
		</section>
	);
	const historyPanel = history &&
		(selected ||
			history.items.length > 0 ||
			history.hasMore ||
			history.loading ||
			history.loadFailed) && (
			<section
				className="sc-card sc-report-history"
				aria-label={__("Calculation history", "linker-tools")}
			>
				<h2>{__("Calculation history", "linker-tools")}</h2>
				<div className="sc-report-versions">
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
							<strong>
								{sprintf(__("Revision %d", "linker-tools"), item.revision)}
							</strong>
							<time dateTime={new Date(item.created_at * 1000).toISOString()}>
								{new Intl.DateTimeFormat(locale, {
									dateStyle: "short",
									timeStyle: "short",
								}).format(item.created_at * 1000)}
							</time>
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
					{history.hasMore && !history.loadFailed && (
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
				{history.loading && (
					<p role="status">
						{__("Reading saved calculation results…", "linker-tools")}
					</p>
				)}
				{history.loadFailed && (
					<div role="alert">
						<p>
							{__(
								"Saved calculation history could not be refreshed.",
								"linker-tools",
							)}
						</p>
						<button
							type="button"
							className="sc-button"
							disabled={history.loading || !client.isCurrentScope(scope)}
							onClick={history.loadMore}
						>
							{__("Try again", "linker-tools")}
						</button>
					</div>
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
						<p className="sc-report-meta">
							{sprintf(__("Revision %d", "linker-tools"), earlierRun.revision)}
						</p>
						<ReportDownloads
							run={earlierRun}
							report={earlierReport}
							client={client}
							scope={scope}
							recheck={recheck}
							askGenie={() => askGenie(earlierRun)}
						>
							{({ actions, materials, error }) => (
								<>
									<ReportItemSections
										report={earlierReport}
										heading="h4"
										materials={materials}
									/>
									<div className="sc-actions">
										{actions}
										{!earlierReport.sections.some(isReportItemSection) &&
											materials}
									</div>
									{error}
								</>
							)}
						</ReportDownloads>
					</>
				)}
			</section>
		);
	return (
		<article
			className="sc-review sc-report-workspace"
			aria-label={project.title}
		>
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
			{!selected && (facts.length > 0 || overviewSections.length > 0) && (
				<section className="sc-card sc-report-overview">
					<h2>{__("Project overview", "linker-tools")}</h2>
					{facts.length > 0 && <ProjectFacts facts={facts} />}
					{overviewSections.length > 0 && (
						<div lang={report?.locale}>
							{overviewSections.map((section) => (
								<details key={section.id} className="sc-review-details">
									<summary>{section.title}</summary>
									<ReportContent section={section} />
								</details>
							))}
						</div>
					)}
				</section>
			)}
			{!selected && run && !current && (
				<p className="sc-card sc-muted" role="status" data-report-outdated="">
					{__(
						"This report describes an earlier version of the project.",
						"linker-tools",
					)}
				</p>
			)}
			{!selected && (!report || !run) && (
				<section className="sc-card sc-report-create">
					<h2>
						<Icon name="report" />
						{__("Project report", "linker-tools")}
					</h2>
					<p className="sc-muted">{reportDescription}</p>
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
							onClick={() => generate(logo?.data ?? null)}
						>
							{__("Generate project report", "linker-tools")}
						</button>
					</div>
				</section>
			)}
			{selected && historyPanel}
			{report && run && (
				<ReportDownloads
					run={run}
					report={report}
					client={client}
					scope={scope}
					recheck={recheck}
					askGenie={() => askGenie(run)}
					suspended={selected}
				>
					{({ actions, materials, error }) => (
						<>
							{!selected && (
								<ReportItemSections report={report} materials={materials} />
							)}
							{(!selected || draftTransfer) && (
								<div
									className={selected ? "sc-card" : "sc-card sc-report-actions"}
								>
									{!selected && (
										<section className="sc-report-files">
											<h2>
												<Icon name="report" />
												{__("Project report", "linker-tools")}
											</h2>
											<p className="sc-muted">{reportDescription}</p>
											<div className="sc-report-file-info">
												<span className="sc-report-filetype" aria-hidden="true">
													PDF
												</span>
												<div>
													<p
														lang={report.locale}
														className="sc-report-filename"
													>
														{report.title}
													</p>
													<p className="sc-report-meta">
														{sprintf(
															__("Revision %d", "linker-tools"),
															run.revision,
														)}
													</p>
													{reportLanguageDiffers(report.locale, locale) && (
														<p className="sc-muted">
															{report.locale === "de"
																? __("Report language: German", "linker-tools")
																: __(
																		"Report language: English",
																		"linker-tools",
																	)}
														</p>
													)}
													<time
														className="sc-muted"
														dateTime={report.generated_at}
													>
														{new Intl.DateTimeFormat(locale, {
															dateStyle: "medium",
															timeStyle: "short",
															timeZone: "UTC",
														}).format(new Date(report.generated_at))}{" "}
														UTC
													</time>
												</div>
											</div>
											<div className="sc-actions">
												{actions}
												{!report.sections.some(isReportItemSection) &&
													materials}
											</div>
											{error}
											{logoField}
											<button
												type="button"
												className="sc-button"
												disabled={disabled}
												onClick={() => generate(logo?.data ?? null)}
											>
												{reportLanguageDiffers(report.locale, locale)
													? locale.startsWith("de")
														? __("Generate report in German", "linker-tools")
														: __("Generate report in English", "linker-tools")
													: __("Update project report", "linker-tools")}
											</button>
										</section>
									)}
									{draftTransfer}
								</div>
							)}
						</>
					)}
				</ReportDownloads>
			)}
			{!selected && historyPanel}
		</article>
	);
}
