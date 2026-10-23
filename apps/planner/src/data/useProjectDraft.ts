import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Draft } from "../domain/draft.ts";
import {
	acknowledgeSave,
	beginDraft,
	isDirty,
	markConflict,
	prepareSave,
	sameJson,
} from "../domain/draft.ts";
import type { Project, Session } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readProject } from "./readProtocol.ts";
import { isPreMutationInputRefusal } from "./inputRefusal.ts";
import type { PlannerClient } from "./PlannerClient.ts";
import type { DraftStore, RecoveryCandidate } from "./DraftStore.ts";

export function useProjectDraft(
	project: Project,
	session: Session,
	client: PlannerClient,
	store: DraftStore,
	recheck: () => void,
) {
	const [draft, setDraft] = useState<Draft | null>(null);
	const [busy, setBusy] = useState(false);
	const [failed, setFailed] = useState(false);
	const [recoveryFailed, setRecoveryFailed] = useState(false);
	const [recovered, setRecovered] = useState(false);
	const [recoveries, setRecoveries] = useState<readonly RecoveryCandidate[]>(
		[],
	);
	const latest = useRef<Draft | null>(null);
	const active = useRef(true);
	const writes = useRef<Promise<void>>(Promise.resolve());
	const cache = useQueryClient();
	const persist = useCallback(
		(next: Draft) => {
			const operation = writes.current
				.catch(() => undefined)
				.then(() => store.write(session.query_scope, next));
			writes.current = operation;
			void operation.then(
				() => {
					if (active.current) setRecoveryFailed(false);
				},
				() => {
					if (active.current) setRecoveryFailed(true);
				},
			);
			return operation;
		},
		[session.query_scope, store],
	);
	const update = useCallback(
		(operation: (previous: Draft) => Draft) => {
			if (!latest.current) return;
			const next = operation(latest.current);
			latest.current = next;
			setDraft(next);
			void persist(next);
		},
		[persist],
	);

	useEffect(() => {
		active.current = true;
		let mounted = true;
		void store
			.read(session.query_scope, project.id)
			.then(async (stored) => {
				if (!mounted) return;
				let next = beginDraft(project);
				if (
					stored &&
					(stored.pending ||
						(isDirty(stored) &&
							!sameJson(stored.history.current, project.inputs)))
				) {
					next = stored;
					if (!stored.pending && project.revision !== stored.baseline.revision)
						next = markConflict(stored, project);
					setRecovered(true);
				} else {
					// The parent has completed the current native owner's server
					// read. Local IDs and query cache do not grant project access.
					const candidates = (
						await store.candidates(session.query_scope, project)
					).filter(
						(candidate) =>
							candidate.draft.pending ||
							(isDirty(candidate.draft) &&
								!sameJson(candidate.draft.history.current, project.inputs)),
					);
					if (!mounted) return;
					if (candidates.length === 1) {
						next = markConflict(candidates[0]!.draft, project);
						setRecovered(true);
						void persist(next);
					} else setRecoveries(candidates);
				}
				latest.current = next;
				setDraft(next);
			})
			.catch(() => {
				if (!mounted) return;
				const next = beginDraft(project);
				latest.current = next;
				setDraft(next);
				setRecoveryFailed(true);
			});
		return () => {
			mounted = false;
			active.current = false;
		};
		// One editor instance is pinned to one opening snapshot and verified scope.
	}, [project, session.query_scope, store, persist]);

	function restore(candidate: RecoveryCandidate): void {
		if (!recoveries.includes(candidate)) return;
		update(() => markConflict(candidate.draft, project));
		setRecoveries([]);
		setRecovered(true);
	}

	useEffect(() => {
		const beforeUnload = (event: BeforeUnloadEvent) => {
			if (
				latest.current &&
				(isDirty(latest.current) || latest.current.pending)
			) {
				event.preventDefault();
				event.returnValue = "";
			}
		};
		window.addEventListener("beforeunload", beforeUnload);
		return () => window.removeEventListener("beforeunload", beforeUnload);
	}, []);

	async function save() {
		if (busy || recoveries.length || !latest.current || latest.current.conflict)
			return;
		const prepared = prepareSave(latest.current, crypto.randomUUID(), {
			maxDepth: session.runtime.limits.max_json_depth,
			maxBytes: session.runtime.limits.max_body_bytes,
		});
		const intent = prepared.pending;
		if (!intent) return;
		latest.current = prepared;
		setDraft(prepared);
		setBusy(true);
		setFailed(false);
		try {
			// Local recovery failure is reported, and does not make an available
			// server unavailable. The in-memory intent remains frozen for retry.
			await persist(prepared).catch(() => undefined);
			const result = readProject(
				await client.send("projects/revise", intent.body, session.query_scope),
			);
			if (
				!active.current ||
				!latest.current ||
				!client.isCurrentScope(session.query_scope)
			)
				return;
			const next = acknowledgeSave(latest.current, intent, result);
			latest.current = next;
			setDraft(next);
			void persist(next);
			void cache.invalidateQueries({
				queryKey: [session.query_scope, "projects"],
			});
		} catch (error) {
			if (!active.current) return;
			setFailed(true);
			if (
				error instanceof ApiError &&
				(error.status === 401 ||
					error.status === 403 ||
					error.code === "session_changed")
			) {
				recheck();
				return;
			}
			if (error instanceof ApiError && error.status === 409) {
				try {
					const remote = readProject(
						await client.query(
							"projects/read",
							{
								schema_version: 1,
								project_id: intent.projectId,
								revision: null,
							},
							session.query_scope,
						),
					);
					if (!active.current || !client.isCurrentScope(session.query_scope))
						return;
					update((previous) => markConflict(previous, remote));
				} catch {
					/* Local input and exact uncertain intent remain available. */
				}
			}
			if (isPreMutationInputRefusal(error)) {
				// These are explicit pre-mutation input refusals, not lost replies.
				update((previous) => ({ ...previous, pending: null }));
			}
		} finally {
			if (active.current) setBusy(false);
		}
	}
	async function flush(): Promise<boolean> {
		// Keep editing responsive while storage commits; closing waits for the
		// latest snapshot, including edits made during an earlier IDB write.
		while (latest.current) {
			const snapshot = latest.current;
			try {
				await persist(snapshot);
			} catch {
				return false;
			}
			if (latest.current === snapshot) return true;
		}
		return false;
	}
	return {
		draft,
		update,
		save,
		flush,
		busy,
		failed,
		recoveryFailed,
		recovered,
		recoveries,
		restore,
	};
}
