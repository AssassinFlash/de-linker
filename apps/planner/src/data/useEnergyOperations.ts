import { useEffect, useRef, useState } from "react";
import type { PlannerClient } from "./PlannerClient.ts";
import type { JsonObject, Session } from "./protocol.ts";
import { ApiError } from "./protocol.ts";
import { wire } from "./readProtocol.ts";
import { isPreMutationInputRefusal } from "./inputRefusal.ts";
import { energyIntentStore } from "./EnergyIntentStore.ts";
import type { EnergyIntent, EnergyIntentStore } from "./EnergyIntentStore.ts";
import {
	readBatteryAsset,
	readEnergyOperation,
	readRun,
} from "./energyProtocol.ts";
import type {
	BatteryAsset,
	EnergyOperation,
	EnergyRun,
} from "./energyProtocol.ts";

export type EnergyJournal = Pick<
	EnergyIntentStore,
	"list" | "write" | "acknowledge" | "clear"
>;
export type EnergyReply =
	| {
			readonly path: "battery/scenario";
			readonly asset: BatteryAsset;
			readonly intent: EnergyIntent;
	  }
	| {
			readonly path: "runs/energy";
			readonly run: EnergyRun;
			readonly intent: EnergyIntent;
	  };

/** The same durable mutation path handles new and explicitly retried intents.
 * A grant permits recovery discovery, never automatic submission or authority. */
export function useEnergyOperations({
	projectId,
	session,
	client,
	recheck,
	recoveryScopes,
	recoveryChecking = false,
	confirmedBatteryId = null,
	store = energyIntentStore,
}: {
	projectId: string;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	confirmedBatteryId?: string | null;
	store?: EnergyJournal;
}) {
	const [records, setRecords] = useState<readonly EnergyIntent[]>([]),
		[checking, setChecking] = useState(true),
		[storageFailed, setStorageFailed] = useState(false),
		[error, setError] = useState<unknown>(null),
		[busy, setBusy] = useState(false),
		[refresh, setRefresh] = useState(0),
		[intent, setIntent] = useState<EnergyIntent | null>(null);
	const lifetime = useRef(0),
		flight = useRef<AbortController | null>(null);
	const admitted = client.isCurrentScope(session.query_scope);
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
			lifetime.current++;
			flight.current?.abort();
			flight.current = null;
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
				pending: EnergyIntent[] = [];
			for (const record of found) {
				if (!current()) return;
				if (
					record.path === "battery/scenario" &&
					record.resultId !== null &&
					record.resultId === confirmedBatteryId
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
		confirmedBatteryId,
		projectId,
		session.query_scope,
		client,
		store,
		refresh,
	]);

	async function submit(
		path: EnergyOperation,
		body: string,
		originScope: string,
		expectedResultId: string | null = null,
	): Promise<EnergyReply | undefined> {
		if (
			flight.current ||
			checking ||
			recoveryChecking ||
			storageFailed ||
			!client.isCurrentScope(session.query_scope) ||
			!JSON.parse(scopeKey).includes(originScope)
		)
			return;
		const command = readEnergyOperation(path, body);
		if (command.project_id !== projectId)
			throw new Error("energy_recovery_invalid");
		const controller = new AbortController(),
			instance = lifetime.current;
		flight.current = controller;
		const current = () =>
			flight.current === controller &&
			instance === lifetime.current &&
			client.isCurrentScope(session.query_scope);
		const pending: EnergyIntent = {
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
		let dispatched = false;
		try {
			await store.write(originScope, path, body);
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
			if (!current()) return;
			let reply: EnergyReply;
			if (path === "battery/scenario")
				reply = {
					path,
					asset: readBatteryAsset(raw, projectId, String(command.source_note)),
					intent: pending,
				};
			else {
				const run = readRun(raw, projectId);
				if (run.revision !== command.expected_revision)
					throw new ApiError(502, "invalid_run_reply");
				reply = { path, run, intent: pending };
			}
			const resultId =
				reply.path === "battery/scenario" ? reply.asset.id : reply.run.id;
			if (expectedResultId !== null && resultId !== expectedResultId)
				throw new ApiError(502, "invalid_energy_receipt");
			setIntent({ ...pending, resultId });
			try {
				await store.acknowledge(originScope, path, body, resultId);
				if (path === "runs/energy") await store.clear(originScope, path, body);
			} catch {
				if (current()) setStorageFailed(true);
			}
			if (!current()) return;
			setRefresh((value) => value + 1);
			return reply;
		} catch (cause) {
			if (flight.current !== controller || instance !== lifetime.current)
				return;
			if (
				cause instanceof ApiError &&
				([401, 403].includes(cause.status) || cause.code === "session_changed")
			) {
				recheck();
				return;
			}
			if (!current()) return;
			setError(cause);
			if (!dispatched) setStorageFailed(true);
			if (
				dispatched &&
				(isPreMutationInputRefusal(cause) ||
					(path === "runs/energy" &&
						cause instanceof ApiError &&
						cause.status === 409 &&
						cause.code === "evaluation_revision_changed"))
			) {
				try {
					await store.clear(originScope, path, body);
				} catch {
					if (current()) setStorageFailed(true);
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
			}
			return;
		} finally {
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
		start: (path: EnergyOperation, fields: JsonObject) => {
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
		retry: (record: EnergyIntent) =>
			submit(record.path, record.body, record.scope, record.resultId),
		dismissAcknowledged: async (record: EnergyIntent) => {
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
