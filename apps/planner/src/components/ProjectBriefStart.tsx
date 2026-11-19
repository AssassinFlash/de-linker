import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ComponentProps } from "react";
import { ApiError } from "../data/protocol.ts";
import { formatDecimal } from "../domain/decimal.ts";
import {
	installerEntryHref,
	projectBriefInputs,
	readProjectBriefSource,
} from "../domain/projectBrief.ts";
import type { ProjectBriefSource } from "../domain/projectBrief.ts";
import { __ } from "../i18n.ts";
import { NewProject } from "./NewProject.tsx";
import { Notice } from "./Notice.tsx";

export function ProjectBriefStart({
	briefId,
	dismiss,
	...props
}: ComponentProps<typeof NewProject> & {
	briefId: string;
	dismiss: () => void;
}) {
	const locale = props.locale ?? "en";
	const source = useQuery({
		queryKey: [props.session.query_scope, "project-brief-source", briefId],
		enabled: !props.session.claim_pending,
		staleTime: Infinity,
		gcTime: 0,
		refetchOnWindowFocus: false,
		refetchOnReconnect: false,
		retry: false,
		queryFn: async ({ signal }) => {
			if (!/^[a-f0-9]{32}$/.test(briefId))
				throw new ApiError(404, "project_brief_unavailable");
			return readProjectBriefSource(
				await props.client.query(
					"sources/project-brief",
					{
						schema_version: 1,
						brief_id: briefId,
					},
					props.session.query_scope,
					signal,
				),
				briefId,
			);
		},
	});

	if (props.session.claim_pending)
		return (
			<Notice>
				<p role="status">
					{__(
						"Projects from the guest session are still being linked to your account.",
						"linker-tools",
					)}
				</p>
			</Notice>
		);

	if (!source.data)
		return (
			<Notice error={source.isError}>
				<p>
					{source.isError
						? __("The project note could not be opened.", "linker-tools")
						: __("Opening your workspace…", "linker-tools")}
				</p>
				<div className="lp-inline-actions">
					<a className="lp-button" href={installerEntryHref(null, locale)}>
						{__("Back to your entry", "linker-tools")}
					</a>
					{source.isError && briefId !== "" && (
						<button
							className="lp-text-button"
							type="button"
							onClick={() => {
								if (
									source.error instanceof ApiError &&
									[401, 403].includes(source.error.status)
								)
									props.recheck();
								else void source.refetch();
							}}
						>
							{__("Try again", "linker-tools")}
						</button>
					)}
					<button className="lp-text-button" type="button" onClick={dismiss}>
						{__("Continue without these inputs", "linker-tools")}
					</button>
				</div>
			</Notice>
		);

	return (
		<BriefForm
			key={briefId + props.session.query_scope}
			record={source.data}
			dismiss={dismiss}
			{...props}
		/>
	);
}

function BriefForm({
	record,
	dismiss,
	...props
}: ComponentProps<typeof NewProject> & {
	record: ProjectBriefSource;
	dismiss: () => void;
}) {
	const locale = props.locale ?? "en";
	const [currentNote, setNote] = useState(record.text);
	const [saved, setSaved] = useState(record);
	const [noteError, setNoteError] = useState(false);
	const [conflict, setConflict] = useState<ProjectBriefSource | null>(null);
	const [confirmed, setConfirmed] = useState(false);
	const [returning, setReturning] = useState(false);
	const pending = useRef<Promise<boolean> | null>(null);
	const revision = useRef(record);
	const text = useRef(record.text);
	const { client, session, recheck } = props;
	const scope = session.query_scope;
	const flush = useCallback(
		async function flush(): Promise<boolean> {
			if (pending.current) return (await pending.current) && flush();
			if (!client.isCurrentScope(scope) || conflict) return false;
			const previous = revision.current;
			const note = text.current;
			if (note === previous.text) return true;
			if (!note.trim()) {
				setNoteError(true);
				return false;
			}
			const write = async () => {
				try {
					const updated = readProjectBriefSource(
						await client.send(
							"sources/project-brief/stage",
							JSON.stringify({
								schema_version: 1,
								brief_id: previous.brief_id,
								expected_revision: previous.revision,
								text: note,
								source_path: previous.source_path,
							}),
							scope,
						),
						previous.brief_id,
					);
					if (!client.isCurrentScope(scope)) return false;
					if (
						updated.text !== note ||
						updated.source_path !== previous.source_path
					)
						throw new Error("invalid_project_brief_source");
					revision.current = updated;
					setSaved(updated);
					setNoteError(false);
					return true;
				} catch (error) {
					if (
						error instanceof ApiError &&
						([401, 403].includes(error.status) ||
							error.code === "session_changed")
					)
						recheck();
					setNoteError(true);
					if (
						error instanceof ApiError &&
						error.code === "linker_planner_project_brief_conflict"
					) {
						try {
							const other = readProjectBriefSource(
								await client.query(
									"sources/project-brief",
									{ schema_version: 1, brief_id: previous.brief_id },
									scope,
								),
								previous.brief_id,
							);
							if (client.isCurrentScope(scope)) setConflict(other);
						} catch {
							/* Keep the draft and retry the owner-scoped read on Next. */
						}
					}
					return false;
				} finally {
					pending.current = null;
				}
			};
			pending.current = write();
			return (await pending.current) && (text.current === note || flush());
		},
		[client, scope, recheck, conflict],
	);
	useEffect(() => {
		if (currentNote === saved.text || !currentNote.trim() || conflict) return;
		const timer = window.setTimeout(() => void flush(), 450);
		return () => window.clearTimeout(timer);
	}, [currentNote, saved, conflict, flush]);
	const hints = props.entryHints ?? null;
	const proposed = hints
		? [
				[__("Postal code", "linker-tools"), hints.postalCode],
				[
					__("Annual electricity consumption", "linker-tools"),
					hints.annualKwh === null
						? null
						: `${formatDecimal(hints.annualKwh, locale)} kWh`,
				],
				[
					__("PV array", "linker-tools"),
					hints.pvKw === null
						? null
						: `${formatDecimal(hints.pvKw, locale)} kWp`,
				],
				[
					__("Grid connection", "linker-tools"),
					hints.phase === null
						? null
						: hints.phase === 3
							? __("Three-phase", "linker-tools")
							: __("Single-phase", "linker-tools"),
				],
				[
					__("Backup supply", "linker-tools"),
					hints.backup === null
						? null
						: hints.backup === "none"
							? __("Not needed", "linker-tools")
							: __("Requested", "linker-tools"),
				],
			].filter(([, value]) => value !== null)
		: [];
	const statusBadge = confirmed
		? __("Confirmed", "linker-tools")
		: __("Carried over", "linker-tools");

	return (
		<NewProject
			{...props}
			initialProject={{
				title: __("New project", "linker-tools"),
				inputs: projectBriefInputs(record.text, null, ""),
			}}
			entryHints={null}
			cancelled={dismiss}
			briefEntry={{
				note: currentNote,
				flush: () => (returning ? Promise.resolve(false) : flush()),
				render: (disabled, showSizingHints, apply) => (
					<fieldset
						disabled={disabled || returning}
						className="sc-card lp-project-brief-start"
						aria-labelledby="lp-project-note-heading"
					>
						<h2 id="lp-project-note-heading">
							{__("Your project note", "linker-tools")}
						</h2>
						<p>
							{__("This note is not used in the calculation.", "linker-tools")}
						</p>
						<label className="lp-field">
							<span>{__("Your project note", "linker-tools")}</span>
							<textarea
								rows={4}
								maxLength={4096}
								required
								value={currentNote}
								onChange={(event) => {
									text.current = event.currentTarget.value;
									setNote(text.current);
									setNoteError(false);
								}}
							/>
						</label>
						<div className="lp-inline-actions">
							<a
								className="lp-text-button"
								href={
									installerEntryHref(record.source_path, locale) +
									"?brief=" +
									record.brief_id
								}
								onClick={(event) => {
									if (disabled || returning) {
										event.preventDefault();
										return;
									}
									if (
										!conflict &&
										text.current === revision.current.text &&
										!pending.current
									)
										return;
									event.preventDefault();
									const href = event.currentTarget.href;
									setReturning(true);
									void flush().then((ok) => {
										if (ok && client.isCurrentScope(scope))
											window.location.assign(href);
										else setReturning(false);
									});
								}}
							>
								{__("Back to your entry", "linker-tools")}
							</a>
						</div>
						{!noteError && saved !== record && currentNote === saved.text && (
							<p role="status">{__("Project note saved.", "linker-tools")}</p>
						)}
						{conflict && (
							<Notice error>
								<p>
									{__(
										"A newer saved revision is available. The open changes have been kept.",
										"linker-tools",
									)}
								</p>
								<p>{conflict.text}</p>
								<button
									type="button"
									onClick={() => {
										revision.current = conflict;
										setSaved(conflict);
										text.current = conflict.text;
										setNote(conflict.text);
										setConflict(null);
										setNoteError(false);
									}}
								>
									{__("Use saved revision", "linker-tools")}
								</button>
								<button
									type="button"
									onClick={() => {
										revision.current = conflict;
										setSaved(conflict);
										setConflict(null);
										setNoteError(false);
									}}
								>
									{__("Keep my changes", "linker-tools")}
								</button>
							</Notice>
						)}
						{noteError && !conflict && (
							<Notice error>
								{__(
									"The project note could not be carried over. Your text is still here.",
									"linker-tools",
								)}
							</Notice>
						)}
						{showSizingHints && proposed.length > 0 && (
							<>
								<p>
									{__(
										"Sizing uses the planning inputs shown below.",
										"linker-tools",
									)}
								</p>
								<h3>{__("Details to confirm", "linker-tools")}</h3>
								<dl className="lp-field-summary">
									{proposed.map(([label, value]) => (
										<div key={label}>
											<dt>{label}</dt>
											<dd>
												{value} ({statusBadge})
											</dd>
										</div>
									))}
								</dl>
								{!confirmed && (
									<button
										type="button"
										className="lp-button lp-button-secondary"
										onClick={() => {
											if (
												apply(
													projectBriefInputs(
														currentNote,
														hints,
														__(
															"Values carried from a tool link. Review them for this project.",
															"linker-tools",
														),
													),
												)
											)
												setConfirmed(true);
										}}
									>
										{__("Use these values", "linker-tools")}
									</button>
								)}
							</>
						)}
					</fieldset>
				),
			}}
		/>
	);
}
