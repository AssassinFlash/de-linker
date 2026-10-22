import { useEffect, useRef, useState } from "react";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { Project, Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import type { DraftStore } from "../data/DraftStore.ts";
import { readObject, readProject, wire } from "../data/readProtocol.ts";
import { emptyBrief } from "../domain/brief.ts";
import { __ } from "../i18n.ts";
import { Icon } from "./Icon.tsx";
import { Notice } from "./Notice.tsx";

export function NewProject({
	session,
	client,
	store,
	created,
	recheck,
}: {
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	created: (project: Project) => void;
	recheck: () => void;
}) {
	const [open, setOpen] = useState(false);
	const [title, setTitle] = useState("");
	const [busy, setBusy] = useState(false);
	const [failed, setFailed] = useState(false);
	const [recoveryFailed, setRecoveryFailed] = useState(false);
	const [checking, setChecking] = useState(true);
	const intent = useRef<string | null>(null);
	useEffect(() => {
		let active = true;
		void store
			.readCreation(session.query_scope)
			.then((body) => {
				if (!active || !body) return;
				const command = readObject(JSON.parse(body));
				intent.current = body;
				setTitle(String(command.title));
				setOpen(true);
				setFailed(true);
			})
			.catch(() => {
				if (active) setRecoveryFailed(true);
			})
			.finally(() => {
				if (active) setChecking(false);
			});
		return () => {
			active = false;
		};
	}, [session.query_scope, store]);
	async function submit() {
		if (busy || !title.trim()) return;
		intent.current ??= wire(
			{
				schema_version: 1,
				title: title.trim(),
				inputs: { brief: emptyBrief() },
				key: crypto.randomUUID(),
			},
			session.runtime.limits.max_json_depth,
			session.runtime.limits.max_body_bytes,
		);
		setBusy(true);
		setFailed(false);
		try {
			await store
				.writeCreation(session.query_scope, intent.current)
				.catch(() => setRecoveryFailed(true));
			const project = readProject(
				await client.send("projects/create", intent.current),
			);
			await store
				.clearCreation(session.query_scope)
				.catch(() => setRecoveryFailed(true));
			intent.current = null;
			setOpen(false);
			setTitle("");
			created(project);
		} catch (error) {
			setFailed(true);
			if (
				error instanceof ApiError &&
				(error.status === 401 ||
					error.status === 403 ||
					error.code === "session_changed")
			)
				recheck();
		} finally {
			setBusy(false);
		}
	}
	if (!open)
		return (
			<button
				className="lp-button"
				disabled={checking}
				onClick={() => setOpen(true)}
			>
				<Icon name="plus" />
				{__("New project", "linker-tools")}
			</button>
		);
	return (
		<form
			className="lp-new-project"
			onSubmit={(event) => {
				event.preventDefault();
				void submit();
			}}
		>
			<label className="lp-field">
				<span>{__("Project name", "linker-tools")}</span>
				<input
					autoFocus
					required
					maxLength={256}
					value={title}
					readOnly={Boolean(intent.current)}
					onChange={(event) => setTitle(event.currentTarget.value)}
				/>
			</label>
			<div className="lp-inline-actions">
				<button className="lp-button" disabled={busy || !title.trim()}>
					{busy
						? __("Creating…", "linker-tools")
						: failed
							? __("Retry project creation", "linker-tools")
							: __("Create project", "linker-tools")}
				</button>
				{!intent.current && (
					<button
						className="lp-text-button"
						type="button"
						onClick={() => setOpen(false)}
					>
						{__("Cancel", "linker-tools")}
					</button>
				)}
			</div>
			{failed && (
				<Notice error>
					{__(
						"Project creation was not confirmed. Retrying uses the same request.",
						"linker-tools",
					)}
				</Notice>
			)}
			{recoveryFailed && (
				<Notice error>
					{__(
						"Browser recovery is unavailable. The open request can still be retried here.",
						"linker-tools",
					)}
				</Notice>
			)}
		</form>
	);
}
