import { useEffect, useRef, useState } from "react";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { Project, Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import type { CreationIntent, DraftStore } from "../data/DraftStore.ts";
import { readProject, wire } from "../data/readProtocol.ts";
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
	created: (project: Project) => boolean;
	recheck: () => void;
}) {
	const [open, setOpen] = useState(false);
	const [title, setTitle] = useState("");
	const [busy, setBusy] = useState(false);
	const [failed, setFailed] = useState(false);
	const [recoveryFailed, setRecoveryFailed] = useState(false);
	const [checking, setChecking] = useState(true);
	const [requests, setRequests] = useState<readonly CreationIntent[]>([]);
	const intent = useRef<string | null>(null);
	const lifetime = useRef(0);
	useEffect(() => {
		lifetime.current++;
		let active = true;
		void store
			.readCreations(session.query_scope)
			.then((records) => {
				if (!active || !records.length) return;
				setRequests(records);
				intent.current = records[0]!.body;
				setTitle(records[0]!.title);
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
			lifetime.current++;
		};
	}, [session.query_scope, store]);
	async function submit() {
		if (busy || !title.trim()) return;
		const instance = lifetime.current;
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
				.catch(() => {
					if (lifetime.current === instance) setRecoveryFailed(true);
				});
			if (lifetime.current !== instance) return;
			if (!client.isCurrentScope(session.query_scope)) {
				setFailed(true);
				return;
			}
			const project = readProject(
				await client.send(
					"projects/create",
					intent.current,
					session.query_scope,
				),
			);
			await store
				.clearCreation(session.query_scope, intent.current)
				.catch(() => {
					if (lifetime.current === instance) setRecoveryFailed(true);
				});
			if (lifetime.current !== instance) return;
			if (!created(project)) {
				setFailed(true);
				return;
			}
			intent.current = null;
			setOpen(false);
			setTitle("");
		} catch (error) {
			if (lifetime.current !== instance) return;
			setFailed(true);
			if (
				error instanceof ApiError &&
				(error.status === 401 ||
					error.status === 403 ||
					error.code === "session_changed")
			)
				recheck();
		} finally {
			if (lifetime.current === instance) setBusy(false);
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
			{requests.length > 1 && (
				<label className="lp-field">
					<span>{__("Unconfirmed project creations", "linker-tools")}</span>
					<select
						disabled={busy}
						value={
							requests.find((request) => request.body === intent.current)
								?.key ?? ""
						}
						onChange={(event) => {
							const request = requests.find(
								(candidate) => candidate.key === event.currentTarget.value,
							);
							if (!request) return;
							intent.current = request.body;
							setTitle(request.title);
							setFailed(true);
						}}
					>
						{requests.map((request, index) => (
							<option key={request.key} value={request.key}>
								{index + 1}. {request.title}
							</option>
						))}
					</select>
				</label>
			)}
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
