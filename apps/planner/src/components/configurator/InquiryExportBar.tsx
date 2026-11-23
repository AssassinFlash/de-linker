import { useEffect, useRef, useState, type ReactNode } from "react";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import {
	readRun,
	runPending,
	waitForRunPoll,
	type PlanningRun,
} from "../../data/planningProtocol.ts";
import { REPORT_TASK, reportFromRun } from "../../data/planningReport.ts";
import { readReportFile } from "../../data/readReportFile.ts";
import type { Project } from "../../data/protocol.ts";
import { __ } from "../../i18n.ts";

export function InquiryExportBar({
	project,
	run,
	scope,
	client,
	locale,
	prepare,
	accept,
	logoField,
	logo,
	blocked,
	children,
}: {
	project: Project;
	run?: PlanningRun | null;
	scope: string;
	client: PlannerClient;
	locale: string;
	prepare?:
		((logo: string | null) => Promise<PlanningRun | undefined>) | undefined;
	accept?: ((completed: PlanningRun) => void) | undefined;
	logo: string | null;
	logoField: ReactNode;
	blocked: boolean;
	children?: ReactNode;
}) {
	const saved = useRef<{ run: PlanningRun; logo: string | null } | null>(null),
		flight = useRef<AbortController | null>(null),
		objectUrl = useRef<string | null>(null);
	const [busy, setBusy] = useState(false),
		[failed, setFailed] = useState(false);
	useEffect(
		() => () => {
			flight.current?.abort();
			if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
		},
		[project.id, scope],
	);
	async function download(format: "pdf" | "materials") {
		if (blocked || flight.current || !client.isCurrentScope(scope)) return;
		const request = new AbortController();
		flight.current = request;
		setBusy(true);
		setFailed(false);
		const lang = locale.startsWith("de") ? "de" : "en";
		try {
			const cached = saved.current;
			let source =
				cached?.logo === logo &&
				cached.run.revision === project.revision &&
				(!run || cached.run.id === run.id)
					? cached.run
					: !logo &&
						  run?.revision === project.revision &&
						  reportFromRun(run).locale === lang
						? run
						: null;
			const prepared = !source;
			if (!source) source = (await prepare?.(logo)) ?? null;
			if (
				!source ||
				source.project_id !== project.id ||
				source.revision !== project.revision
			)
				throw Error("report_revision");
			while (runPending(source.state)) {
				await waitForRunPoll(request.signal);
				source = readRun(
					await client.query(
						"runs/read",
						{ schema_version: 1, run_id: source.id },
						scope,
						request.signal,
					),
					project.id,
					source.id,
					REPORT_TASK,
				);
			}
			if (source.state !== "succeeded" || !client.isCurrentScope(scope))
				throw Error("report_unavailable");
			const { blob, filename } = await readReportFile(
				client,
				source,
				scope,
				lang,
				format,
				request.signal,
			);
			if (request.signal.aborted || !client.isCurrentScope(scope)) return;
			if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
			objectUrl.current = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = objectUrl.current;
			link.download = filename;
			link.click();
			saved.current = { run: source, logo };
			if (prepared) accept?.(source);
		} catch {
			if (!request.signal.aborted) setFailed(true);
		} finally {
			if (flight.current === request) {
				flight.current = null;
				setBusy(false);
			}
		}
	}
	return (
		<section
			className="sc-card sc-export-strip"
			aria-label={__("Project report", "linker-tools")}
		>
			{logoField}
			<div className="sc-actions">
				<button
					type="button"
					className="sc-button btn-secondary"
					disabled={blocked || busy}
					onClick={() => void download("pdf")}
				>
					{__("Download PDF", "linker-tools")}
				</button>
				<button
					type="button"
					className="sc-button btn-secondary"
					disabled={blocked || busy}
					onClick={() => void download("materials")}
				>
					{__("Download bill of materials (CSV)", "linker-tools")}
				</button>
				{children}
				{busy && (
					<p role="status">
						{__("Preparing planning report…", "linker-tools")}
					</p>
				)}
				{failed && (
					<p role="alert">
						{__(
							"The report could not be generated. Please try again.",
							"linker-tools",
						)}
					</p>
				)}
			</div>
		</section>
	);
}
