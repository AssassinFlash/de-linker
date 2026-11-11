import { useEffect, useRef, useState } from "react";
import type { PlannerClient } from "./PlannerClient.ts";
import type { JsonObject, Session } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { wire } from "./readProtocol.ts";
import { readDraftReceipt } from "./draftTransfer.ts";
import type { DraftReceipt } from "./draftTransfer.ts";
import { isPreMutationInputRefusal } from "./inputRefusal.ts";
import { planningIntentStore } from "./PlanningIntentStore.ts";
import type {
	PlanningIntent,
	PlanningIntentStore,
} from "./PlanningIntentStore.ts";
import {
	readBatteryAsset,
	readPlanningOperation,
	readRun,
	RUN_OPERATIONS,
} from "./planningProtocol.ts";
import type {
	BatteryAsset,
	PlanningOperation,
	PlanningRun,
	RunOperation,
} from "./planningProtocol.ts";

export type PlanningJournal = Pick<
	PlanningIntentStore,
	"list" | "write" | "acknowledge" | "clear"
>;
export type PlanningReply =
	| {
			readonly path: "draft/apply";
			readonly receipt: DraftReceipt;
			readonly intent: PlanningIntent;
	  }
	| {
			readonly path: "battery/scenario";
			readonly asset: BatteryAsset;
			readonly intent: PlanningIntent;
	  }
	| {
			readonly path: RunOperation;
			readonly run: PlanningRun;
			readonly intent: PlanningIntent;
	  };

/** The same durable mutation path handles new and explicitly retried intents.
 * A grant permits recovery discovery, never automatic submission or authority. */

// A request the engine has been offered stays owned until its reply is read,
// including across the page that started it. Navigation unmounts that page but
// not the dispatch, so the journal entry is still being settled; another view
// of the same project must not offer it as a stored request the customer has to
// discard by hand. Keys are the journal's own identity: scope:path:key.
const inflight = new Set<string>();
const inflightKey = (scope: string, path: string, key: string) =>
	scope + ":" + path + ":" + key.toLowerCase();

export function usePlanningOperations({
	projectId,
	session,
	client,
	recheck,
	recoveryScopes,
	recoveryChecking = false,
	confirmedBatteryId = null,
	confirmedBatteryIds = [],
	store = planningIntentStore,
}: {
	projectId: string;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	confirmedBatteryId?: string | null;
	confirmedBatteryIds?: readonly string[];
	store?: PlanningJournal;
}) {
	const [records, setRecords] = useState<readonly PlanningIntent[]>([]),
		[checking, setChecking] = useState(true),
		[storageFailed, setStorageFailed] = useState(false),
		[error, setError] = useState<unknown>(null),
		[busy, setBusy] = useState(false),
		[refresh, setRefresh] = useState(0),
		[intent, setIntent] = useState<PlanningIntent | null>(null);
	const lifetime = useRef(0),
		flight = useRef<AbortController | null>(null);
	const admitted = client.isCurrentScope(session.query_scope);
	const confirmedKey = JSON.stringify(
		[
			...new Set([
				...confirmedBatteryIds,
				...(confirmedBatteryId ? [confirmedBatteryId] : []),
			]),
		].sort(),
	);
	const scopeKey = JSON.stringify([
		...new Set([session.query_scope, ...(recoveryScopes ?? [])]),
	]);
	useEffect(() => {
		lifetime.current++;
		setBusy(false);
		setError(null);
		setIntent(null);
		setRecords([]);
		setChecking(true);
		return () => {
			// Navigation must not abandon a request the server has already been
			// offered. The journal entry and the engine's own receipt own it from
			// the moment it is written: the reply below still acknowledges and
			// clears it without touching this page's unmounted state.
			lifetime.current++;
		};
	}, [projectId, session.query_scope]);
	useEffect(() => {
		if (!admitted || recoveryChecking) return;
		let active = true;
		const instance = lifetime.current;
		const current = () =>
			active &&
			instance === lifetime.current &&
			client.isCurrentScope(session.query_scope);
		setChecking(true);
		void (async () => {
			const found = await store.list(
					JSON.parse(scopeKey) as string[],
					projectId,
				),
				pending: PlanningIntent[] = [];
			const confirmed = new Set(JSON.parse(confirmedKey) as string[]);
			for (const record of found) {
				if (!current()) return;
				// A request this browser is still dispatching needs no recovery:
				// its own reply clears the entry, and offering it here would lock
				// every later action behind a request that is already running.
				if (inflight.has(inflightKey(record.scope, record.path, record.key)))
					continue;
				if (
					record.path === "battery/scenario" &&
					record.resultId !== null &&
					confirmed.has(record.resultId)
				)
					await store.clear(record.scope, record.path, record.body);
				else pending.push(record);
			}
			if (current()) {
				setRecords(pending);
				setStorageFailed(false);
			}
		})()
			.catch(() => {
				if (current()) setStorageFailed(true);
			})
			.finally(() => {
				if (current()) setChecking(false);
			});
		return () => {
			active = false;
		};
	}, [
		admitted,
		recoveryChecking,
		scopeKey,
		confirmedKey,
		projectId,
		session.query_scope,
		client,
		store,
		refresh,
	]);

	async function submit(
		path: PlanningOperation,
		body: string,
		originScope: string,
		expectedResultId: string | null = null,
	): Promise<PlanningReply | undefined> {
		if (
			flight.current ||
			checking ||
			recoveryChecking ||
			storageFailed ||
			!client.isCurrentScope(session.query_scope) ||
			!JSON.parse(scopeKey).includes(originScope)
		)
			return;
		const command = readPlanningOperation(path, body);
		if (command.project_id !== projectId)
			throw new Error("energy_recovery_invalid");
		const controller = new AbortController(),
			instance = lifetime.current;
		flight.current = controller;
		// React state belongs to this page; the journal and the engine receipt
		// belong to the request. A page that goes away keeps the reply path but
		// stops reporting, so a navigation can never strand an accepted run as an
		// unconfirmed stored request.
		const current = () =>
			flight.current === controller &&
			instance === lifetime.current &&
			client.isCurrentScope(session.query_scope);
		const owned = () =>
			flight.current === controller &&
			client.isCurrentScope(session.query_scope);
		const pending: PlanningIntent = {
			path,
			body,
			scope: originScope,
			projectId,
			key: String(command.key).toLowerCase(),
			createdAt: Date.now(),
			resultId: null,
		};
		setBusy(true);
		setError(null);
		setIntent(pending);
		const flightId = inflightKey(originScope, path, pending.key);
		inflight.add(flightId);
		let dispatched = false;
		try {
			// The request is marked in flight before the journal write, so a
			// second mounted view of this project cannot report the entry as a
			// stored request while this dispatch is still producing its reply.
			await store.write(
				originScope,
				path,
				body,
				JSON.parse(scopeKey) as string[],
			);
			// A page that goes away while the journal write is still pending must
			// not dispatch: the request would reach the server with nobody left
			// to read its reply. It stays a stored request, as before.
			if (!current()) return;
			setStorageFailed(false);
			setRecords((previous) => [
				...previous.filter(
					(row) =>
						row.scope !== originScope || row.path !== path || row.body !== body,
				),
				pending,
			]);
			dispatched = true;
			const raw = await client.send(
				path,
				body,
				session.query_scope,
				controller.signal,
			);
			if (!owned()) return;
			let reply: PlanningReply;
			if (path === "battery/scenario")
				reply = {
					path,
					asset: readBatteryAsset(
						raw,
						projectId,
						String(command.source_note),
						command,
					),
					intent: pending,
				};
			else if (path === "draft/apply")
				reply = {
					path,
					receipt: readDraftReceipt(raw, command, client.origin),
					intent: pending,
				};
			else {
				const run = readRun(raw, projectId, undefined, RUN_OPERATIONS[path]);
				if (run.revision !== command.expected_revision)
					throw new ApiError(502, "invalid_run_reply");
				reply = { path, run, intent: pending };
			}
			const resultId =
				reply.path === "battery/scenario"
					? reply.asset.id
					: reply.path === "draft/apply"
						? reply.receipt.handoffId
						: reply.run.id;
			if (expectedResultId !== null && resultId !== expectedResultId)
				throw new ApiError(502, "invalid_energy_receipt");
			try {
				await store.acknowledge(originScope, path, body, resultId);
				if (path !== "battery/scenario")
					await store.clear(originScope, path, body);
			} catch {
				if (current()) setStorageFailed(true);
			}
			if (!current()) return undefined;
			setIntent({ ...pending, resultId });
			setRefresh((value) => value + 1);
			return reply;
		} catch (cause) {
			if (flight.current !== controller) return;
			// The journal entry outlives this page. A refusal that proves the
			// request did no work must clear it here, or the next view would offer
			// a request the server already turned down as one to retry.
			const release = async () => {
				try {
					await store.clear(originScope, path, body);
				} catch {
					if (current()) setStorageFailed(true);
					return;
				}
				if (current()) {
					setRecords((rows) =>
						rows.filter(
							(row) =>
								row.scope !== originScope ||
								row.path !== path ||
								row.body !== body,
						),
					);
					setIntent(null);
				}
			};
			if (
				cause instanceof ApiError &&
				([401, 403].includes(cause.status) || cause.code === "session_changed")
			) {
				recheck();
				return;
			}
			if (!current()) {
				if (
					dispatched &&
					(isPreMutationInputRefusal(cause) ||
						(cause instanceof ApiError &&
							cause.status === 409 &&
							cause.code === "evaluation_revision_changed"))
				)
					await release();
				return;
			}
			if (
				cause instanceof ApiError &&
				cause.code === "planning_operation_pending" &&
				!dispatched
			) {
				setIntent(null);
				setRefresh((value) => value + 1);
				return;
			}
			setError(cause);
			if (!dispatched) setStorageFailed(true);
			if (
				dispatched &&
				(isPreMutationInputRefusal(cause) ||
					(["battery/scenario", "runs/energy"].includes(path) &&
						cause instanceof ApiError &&
						cause.status === 422 &&
						["evidence_missing", "method_domain_exceeded"].includes(
							cause.code,
						)) ||
					(path !== "battery/scenario" &&
						cause instanceof ApiError &&
						cause.status === 409 &&
						cause.code === "evaluation_revision_changed"))
			)
				await release();
			return;
		} finally {
			inflight.delete(flightId);
			if (flight.current === controller) {
				flight.current = null;
				if (instance === lifetime.current) setBusy(false);
			}
		}
	}
	return {
		records,
		checking,
		storageFailed,
		error,
		busy,
		intent,
		refresh: () => setRefresh((value) => value + 1),
		start: (path: PlanningOperation, fields: JsonObject) => {
			if (records.some((record) => record.resultId === null))
				return Promise.resolve(undefined);
			const body = wire(
				{
					...fields,
					schema_version: 1,
					project_id: projectId,
					key: crypto.randomUUID(),
				},
				session.runtime.limits.max_json_depth,
				session.runtime.limits.max_body_bytes,
			);
			return submit(path, body, session.query_scope);
		},
		retry: (record: PlanningIntent) =>
			submit(record.path, record.body, record.scope, record.resultId),
		acknowledgeReadback: async (record: PlanningIntent, resultId: string) => {
			if (
				!client.isCurrentScope(session.query_scope) ||
				record.projectId !== projectId ||
				!(JSON.parse(scopeKey) as string[]).includes(record.scope)
			)
				return;
			try {
				await store.acknowledge(
					record.scope,
					record.path,
					record.body,
					resultId,
				);
				if (record.path === "draft/apply")
					await store.clear(record.scope, record.path, record.body);
				setRefresh((value) => value + 1);
			} catch {
				setStorageFailed(true);
			}
		},
		discard: async (record: PlanningIntent) => {
			if (
				!client.isCurrentScope(session.query_scope) ||
				record.projectId !== projectId ||
				!(JSON.parse(scopeKey) as string[]).includes(record.scope)
			)
				return;
			const instance = lifetime.current;
			try {
				await store.clear(record.scope, record.path, record.body);
				if (
					instance === lifetime.current &&
					client.isCurrentScope(session.query_scope)
				)
					setRefresh((value) => value + 1);
			} catch {
				if (instance === lifetime.current) setStorageFailed(true);
			}
		},
		dismissAcknowledged: async (record: PlanningIntent) => {
			if (
				flight.current ||
				checking ||
				recoveryChecking ||
				record.resultId === null ||
				!client.isCurrentScope(session.query_scope) ||
				record.projectId !== projectId ||
				!(JSON.parse(scopeKey) as string[]).includes(record.scope)
			)
				return;
			const instance = lifetime.current;
			try {
				await store.clear(record.scope, record.path, record.body);
				if (
					instance === lifetime.current &&
					client.isCurrentScope(session.query_scope)
				)
					setRefresh((value) => value + 1);
			} catch {
				if (
					instance === lifetime.current &&
					client.isCurrentScope(session.query_scope)
				)
					setStorageFailed(true);
			}
		},
	};
}
