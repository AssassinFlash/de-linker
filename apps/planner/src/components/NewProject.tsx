import { useEffect, useRef, useState } from "react";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { Project, Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import type { DraftStore } from "../data/DraftStore.ts";
import { creationIntents, intentId } from "../data/recoveryIntents.ts";
import type { ScopedCreation } from "../data/recoveryIntents.ts";
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
	recoveryScopes,
	recoveryChecking = false,
	recoveryDiscoveryFailed = false,
}: {
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	created: (project: Project) => boolean;
	recheck: () => void;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	recoveryDiscoveryFailed?: boolean;
}) {
	const [open, setOpen] = useState(false);
	const [title, setTitle] = useState("");
	const [busy, setBusy] = useState(false);
	const [failed, setFailed] = useState(false);
	const [recoveryFailed, setRecoveryFailed] = useState(false);
	const [checking, setChecking] = useState(true);
	const [requests, setRequests] = useState<readonly ScopedCreation[]>([]);
	const intent = useRef<string | null>(null);
	const intentScope = useRef(session.query_scope);
	const lifetime = useRef(0);
	const openWork = useRef(false);
	openWork.current = Boolean(intent.current || title);
	const admitted = client.isCurrentScope(session.query_scope);
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
		};
	}, [session.query_scope]);
	useEffect(() => {
		if (recoveryChecking || !admitted) return;
		let active = true;
		setChecking(true);
		void creationIntents(store, recoveryScopes ?? [session.query_scope])
			.then((records) => {
				if (
					!active ||
					!client.isCurrentScope(session.query_scope) ||
					!records.length
				)
					return;
				setRequests(records);
				if (openWork.current) return;
				intent.current = records[0]!.body;
				intentScope.current = records[0]!.scope;
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
		};
	}, [
		admitted,
		client,
		session.query_scope,
		store,
		recoveryScopes,
		recoveryChecking,
	]);
	async function submit() {
		if (
			busy ||
			checking ||
			recoveryChecking ||
			recoveryDiscoveryFailed ||
			!title.trim()
		)
			return;
		const instance = lifetime.current;
		if (!intent.current) intentScope.current = session.query_scope;
		const originScope = intentScope.current;
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
			await store.writeCreation(originScope, intent.current).catch(() => {
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
			await store.clearCreation(originScope, intent.current).catch(() => {
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
	const selectedRequest = requests.find(
		(request) =>
			request.body === intent.current && request.scope === intentScope.current,
	);
	if (!open)
		return (
			<button
				className="lp-button"
				disabled={checking || recoveryChecking || recoveryDiscoveryFailed}
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
						value={selectedRequest ? intentId(selectedRequest) : ""}
						onChange={(event) => {
							const request = requests.find(
								(candidate) =>
									intentId(candidate) === event.currentTarget.value,
							);
							if (!request) return;
							intent.current = request.body;
							intentScope.current = request.scope;
							setTitle(request.title);
							setFailed(true);
						}}
					>
						{requests.map((request, index) => (
							<option key={intentId(request)} value={intentId(request)}>
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
				<button
					className="lp-button"
					disabled={
						busy ||
						checking ||
						recoveryChecking ||
						recoveryDiscoveryFailed ||
						!title.trim()
					}
				>
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
