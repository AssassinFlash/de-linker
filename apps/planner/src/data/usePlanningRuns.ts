import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { PlannerClient } from "./PlannerClient.ts";
import type { Session } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { readRun, readRunPage, runPending } from "./planningProtocol.ts";
import type { PlanningRun, RunPage } from "./planningProtocol.ts";
import { replacePlannerLocation } from "./plannerLocation.ts";

// Visible-task polling policy, not numerical progress or a completion deadline.
const POLL_MS = 1000;
export function usePlanningRuns({
	projectId,
	session,
	client,
	recheck,
	active,
	readSelected = true,
}: {
	projectId: string;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	active: boolean;
	readSelected?: boolean;
}) {
	const [cursor, setCursor] = useState<RunPage["next"]>(null),
		[selected, setSelected] = useState<string | null>(() => {
			const id = new URL(window.location.href).searchParams.get("run");
			return id && /^[a-f0-9]{32}$/.test(id) ? id : null;
		}),
		[cancelTarget, setCancelTarget] = useState<string | null>(null),
		[cancelFailure, setCancelFailure] = useState<{
			id: string;
			error: unknown;
		} | null>(null);
	const cancelling = useRef(false),
		lifetime = useRef(0),
		cache = useQueryClient();
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
		};
	}, [projectId, session.query_scope]);
	const admitted = client.isCurrentScope(session.query_scope),
		listKey = [session.query_scope, "energy-runs", projectId] as const;
	async function request<T>(read: () => Promise<T>): Promise<T> {
		try {
			return await read();
		} catch (error) {
			if (
				error instanceof ApiError &&
				([401, 403].includes(error.status) || error.code === "session_changed")
			)
				recheck();
			throw error;
		}
	}
	const page = useQuery({
		queryKey: [...listKey, cursor],
		queryFn: ({ signal }) =>
			request(async () =>
				readRunPage(
					await client.query(
						"projects/runs",
						{
							schema_version: 1,
							project_id: projectId,
							page_size: Math.min(10, session.runtime.limits.max_page_size),
							before_created_at: cursor?.before_created_at ?? null,
							before_id: cursor?.before_id ?? null,
						},
						session.query_scope,
						signal,
					),
					projectId,
				),
			),
		enabled: active && admitted,
		retry: false,
		refetchInterval: (query) =>
			query.state.data?.items.some((run) => runPending(run.state))
				? POLL_MS
				: false,
	});
	const runId = selected ?? page.data?.items[0]?.id ?? null;
	const runKey = [session.query_scope, "energy-run", projectId, runId] as const;
	const run = useQuery({
		queryKey: runKey,
		queryFn: ({ signal }) =>
			request(async () => {
				if (!runId) throw new Error("run_selection_required");
				return readRun(
					await client.query(
						"runs/read",
						{ schema_version: 1, run_id: runId },
						session.query_scope,
						signal,
					),
					projectId,
					runId,
				);
			}),
		enabled: active && readSelected && admitted && runId !== null,
		retry: false,
		refetchInterval: (query) =>
			query.state.data && runPending(query.state.data.state) ? POLL_MS : false,
	});
	const verifiedRunId = run.data?.id;
	useEffect(() => {
		// The first history page can arrive after the user opens this view. Keep
		// its verified automatic selection in the URL too, for reload/language links.
		if (
			active &&
			readSelected &&
			admitted &&
			selected === null &&
			verifiedRunId &&
			verifiedRunId === runId
		)
			select(verifiedRunId);
	}, [
		active,
		readSelected,
		admitted,
		selected,
		verifiedRunId,
		runId,
		client,
		projectId,
		session.query_scope,
	]);
	function select(id: string) {
		if (
			!client.isCurrentScope(session.query_scope) ||
			!/^[a-f0-9]{32}$/.test(id)
		)
			return;
		const url = new URL(window.location.href);
		if (url.searchParams.get("project") !== projectId) return;
		setSelected(id);
		setCancelFailure(null);
		url.searchParams.set("run", id);
		url.searchParams.delete("compare");
		url.searchParams.delete("energy_view");
		url.hash = "lp-calculations";
		replacePlannerLocation(url);
	}
	function accepted(value: PlanningRun) {
		if (
			!client.isCurrentScope(session.query_scope) ||
			value.project_id !== projectId
		)
			return;
		cache.setQueryData(
			[session.query_scope, "energy-run", projectId, value.id],
			value,
		);
		setCursor(null);
		select(value.id);
		void cache.invalidateQueries({ queryKey: listKey });
	}
	async function cancel() {
		if (
			cancelling.current ||
			!runId ||
			!client.isCurrentScope(session.query_scope)
		)
			return;
		cancelling.current = true;
		const instance = lifetime.current;
		const current = () =>
			instance === lifetime.current &&
			client.isCurrentScope(session.query_scope);
		setCancelTarget(runId);
		setCancelFailure(null);
		try {
			const confirmed = readRun(
				await request(() =>
					client.query(
						"runs/cancel",
						{ schema_version: 1, run_id: runId },
						session.query_scope,
					),
				),
				projectId,
				runId,
			);
			if (!current()) return;
			cache.setQueryData(runKey, confirmed);
			void cache.invalidateQueries({ queryKey: listKey });
		} catch (error) {
			if (current()) setCancelFailure({ id: runId, error });
		} finally {
			cancelling.current = false;
			if (current()) setCancelTarget(null);
		}
	}
	return {
		page,
		run,
		runId,
		select,
		accepted,
		cancel,
		cancelBusy: cancelTarget === runId && cancelTarget !== null,
		cancelPending: cancelTarget !== null,
		cancelError: cancelFailure?.id === runId ? cancelFailure.error : null,
		first: () => setCursor(null),
		next: () => {
			if (page.data?.next) setCursor(page.data.next);
		},
		hasPrevious: cursor !== null,
	};
}
