import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { ComponentProps } from "react";
import { ApiError } from "../data/protocol.ts";
import { formatDecimal } from "../domain/decimal.ts";
import {
	installerEntryHref,
	projectBriefInputs,
	readProjectBriefSource,
} from "../domain/projectBrief.ts";
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
	const [editedNote, setEditedNote] = useState<string | null>(null);
	const [savedRevision, setSavedRevision] = useState<string | null>(null);
	const [savingNote, setSavingNote] = useState(false);
	const [noteSaved, setNoteSaved] = useState(false);
	const [noteError, setNoteError] = useState(false);
	const [confirmed, setConfirmed] = useState(false);

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

	const record = source.data;
	const currentNote = editedNote ?? record.text;
	const currentRevision = savedRevision ?? record.revision;
	const hints = props.entryHints ?? null;
	const hasStructuredHints = Boolean(
		hints &&
		[
			hints.postalCode,
			hints.annualKwh,
			hints.pvKw,
			hints.phase,
			hints.backup,
		].some((value) => value !== null),
	);
	const activeHints = hasStructuredHints && confirmed ? hints : null;
	const inputs = projectBriefInputs(
		currentNote,
		activeHints,
		__(
			"Values carried from a tool link. Review them for this project.",
			"linker-tools",
		),
	);

	async function saveNote() {
		if (
			savingNote ||
			!currentNote.trim() ||
			Array.from(currentNote).length > 4096 ||
			!props.client.isCurrentScope(props.session.query_scope)
		)
			return;
		setSavingNote(true);
		setNoteSaved(false);
		setNoteError(false);
		try {
			const updated = readProjectBriefSource(
				await props.client.send(
					"sources/project-brief/stage",
					JSON.stringify({
						schema_version: 1,
						brief_id: briefId,
						expected_revision: currentRevision,
						text: currentNote,
						source_path: record.source_path,
					}),
					props.session.query_scope,
				),
				briefId,
			);
			setEditedNote(updated.text);
			setSavedRevision(updated.revision);
			setNoteSaved(true);
		} catch (error) {
			if (
				error instanceof ApiError &&
				([401, 403].includes(error.status) || error.code === "session_changed")
			)
				props.recheck();
			setNoteError(true);
		} finally {
			setSavingNote(false);
		}
	}

	const statusBadge = confirmed
		? __("Confirmed", "linker-tools")
		: __("Carried over", "linker-tools");

	return (
		<div className="lp-project-brief-start">
			<section className="lp-section" aria-labelledby="lp-project-note-heading">
				<h2 id="lp-project-note-heading">
					{__("Your project note", "linker-tools")}
				</h2>
				<p>{__("This note is not used in the calculation.", "linker-tools")}</p>
				<label className="lp-field">
					<span>{__("Your project note", "linker-tools")}</span>
					<textarea
						rows={4}
						maxLength={4096}
						value={currentNote}
						onChange={(event) => {
							setEditedNote(event.currentTarget.value);
							setNoteSaved(false);
							setNoteError(false);
						}}
					/>
				</label>
				<div className="lp-inline-actions">
					<button
						type="button"
						className="lp-button lp-button-secondary"
						disabled={savingNote || !currentNote.trim()}
						onClick={() => void saveNote()}
					>
						{__("Save", "linker-tools")}
					</button>
					<a
						className="lp-text-button"
						href={installerEntryHref(record.source_path, locale)}
					>
						{__("Back to your entry", "linker-tools")}
					</a>
				</div>
				{noteSaved && (
					<p role="status">{__("Project note saved.", "linker-tools")}</p>
				)}
				{noteError && (
					<Notice error>
						{__(
							"The project note could not be carried over. Your text is still here.",
							"linker-tools",
						)}
					</Notice>
				)}
				<p>
					{__("Sizing uses the planning inputs shown below.", "linker-tools")}
				</p>
				<h3>{__("Details to confirm", "linker-tools")}</h3>
				<dl className="lp-field-summary">
					<div>
						<dt>{__("Postal code", "linker-tools")}</dt>
						<dd>
							{hints?.postalCode !== null && hints?.postalCode !== undefined
								? `${hints.postalCode} (${statusBadge})`
								: __("Not entered", "linker-tools")}
						</dd>
					</div>
					<div>
						<dt>{__("Annual electricity consumption", "linker-tools")}</dt>
						<dd>
							{hints?.annualKwh !== null && hints?.annualKwh !== undefined
								? `${formatDecimal(hints.annualKwh, locale)} kWh (${statusBadge})`
								: __("Not entered", "linker-tools")}
						</dd>
					</div>
					<div>
						<dt>{__("PV array", "linker-tools")}</dt>
						<dd>
							{hints?.pvKw !== null && hints?.pvKw !== undefined
								? `${formatDecimal(hints.pvKw, locale)} kWp (${statusBadge})`
								: __("Not entered", "linker-tools")}
						</dd>
					</div>
					<div>
						<dt>{__("Grid connection", "linker-tools")}</dt>
						<dd>
							{hints?.phase !== null && hints?.phase !== undefined
								? `${
										hints.phase === 3
											? __("Three-phase", "linker-tools")
											: __("Single-phase", "linker-tools")
									} (${statusBadge})`
								: __("Not entered", "linker-tools")}
						</dd>
					</div>
					<div>
						<dt>{__("Backup supply", "linker-tools")}</dt>
						<dd>
							{hints?.backup !== null && hints?.backup !== undefined
								? `${
										hints.backup === "none"
											? __("Not needed", "linker-tools")
											: __("Requested", "linker-tools")
									} (${statusBadge})`
								: __("Not entered", "linker-tools")}
						</dd>
					</div>
				</dl>
				{hasStructuredHints && !confirmed && (
					<button
						type="button"
						className="lp-button lp-button-secondary"
						onClick={() => setConfirmed(true)}
					>
						{__("Use these values", "linker-tools")}
					</button>
				)}
			</section>
			<NewProject
				{...props}
				initialProject={{
					title: __("New project", "linker-tools"),
					inputs,
				}}
				// The note panel above is the single confirmation gesture, so the
				// project form never offers a second toggle that could drop the
				// customer's own note.
				entryHints={null}
				cancelled={dismiss}
			/>
		</div>
	);
}
