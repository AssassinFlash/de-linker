import { useCallback, useEffect, useRef, useState } from "react";
import type { PlannerClient } from "./PlannerClient.ts";
import { ApiError } from "./protocol.ts";
import type { Session } from "./protocol.ts";
import { readObject, wire } from "./readProtocol.ts";
import { geometryImportStore } from "./GeometryImportStore.ts";
import type {
	GeometryImportStore,
	GeometryImportIntent,
} from "./GeometryImportStore.ts";
import {
	readGeometryImportCommand,
	readPreparedGeometryImport,
} from "../domain/geometryImports.ts";
import type {
	GeometryImportCommand,
	PreparedGeometryImport,
} from "../domain/geometryImports.ts";
import { sameJson } from "../domain/draft.ts";
import { isPreMutationInputRefusal } from "./inputRefusal.ts";

export type GeometryImportJournal = Pick<
	GeometryImportStore,
	"list" | "write" | "acknowledge" | "clear"
>;

/** One explicit mutation at a time. A native grant admits local recovery; an
 * intent is durable before dispatch and keeps its exact original namespace,
 * bytes and key until a confirmed server project protects its selection. */
export function useGeometryImport({
	projectId,
	session,
	client,
	recheck,
	recoveryScopes,
	recoveryChecking = false,
	confirmedAssetIds,
	store = geometryImportStore,
}: {
	projectId: string;
	session: Session;
	client: PlannerClient;
	recheck: () => void;
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
	confirmedAssetIds: readonly string[];
	store?: GeometryImportJournal;
}) {
	const [records, setRecords] = useState<readonly GeometryImportIntent[]>([]),
		[checking, setChecking] = useState(true),
		[storageFailed, setStorageFailed] = useState(false),
		[busy, setBusy] = useState(false),
		[durable, setDurable] = useState(false),
		[intent, setIntent] = useState<GeometryImportIntent | null>(null),
		[asset, setAsset] = useState<PreparedGeometryImport | null>(null),
		[error, setError] = useState<unknown>(null),
		[refresh, setRefresh] = useState(0);
	const lifetime = useRef(0),
		flight = useRef<AbortController | null>(null);
	const admitted = client.isCurrentScope(session.query_scope),
		scopeKey = JSON.stringify([
			...new Set([session.query_scope, ...(recoveryScopes ?? [])]),
		]),
		confirmedKey = JSON.stringify([...new Set(confirmedAssetIds)].sort());
	useEffect(() => {
		lifetime.current++;
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
			);
			if (!current()) return;
			const confirmed = new Set(JSON.parse(confirmedKey) as string[]),
				pending: GeometryImportIntent[] = [];
			for (const record of found) {
				if (!current()) return;
				if (record.assetId !== null && confirmed.has(record.assetId)) {
					await store.clear(record.scope, record.body);
				} else pending.push(record);
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

	const dismiss = useCallback(() => {
		flight.current?.abort();
		flight.current = null;
		lifetime.current++;
		setBusy(false);
		setDurable(false);
		setIntent(null);
		setAsset(null);
		setError(null);
		// Close may restore focus only after this recovery scan has completed;
		// a later checking=true must not disable an already-refocused trigger.
		setChecking(true);
		setRefresh((value) => value + 1);
	}, []);

	async function run(body: string, originScope: string) {
		if (flight.current || !client.isCurrentScope(session.query_scope)) return;
		const command = readGeometryImportCommand(JSON.parse(body));
		if (
			command.project_id !== projectId ||
			!JSON.parse(scopeKey).includes(originScope)
		)
			throw new Error("geometry_recovery_invalid");
		const controller = new AbortController(),
			instance = lifetime.current;
		flight.current = controller;
		const current = () =>
			flight.current === controller &&
			instance === lifetime.current &&
			client.isCurrentScope(session.query_scope);
		setBusy(true);
		setError(null);
		setAsset(null);
		setDurable(false);
		const pending: GeometryImportIntent = {
			scope: originScope,
			body,
			projectId,
			key: command.key.toLowerCase(),
			label: command.options.source.label,
			createdAt: Date.now(),
			assetId: null,
		};
		setIntent(pending);
		let dispatched = false;
		try {
			// An unsuccessful journal write cannot produce an unprotected mutation.
			await store.write(originScope, body);
			if (!current()) return;
			setDurable(true);
			dispatched = true;
			const prepared = readPreparedGeometryImport(
				await client.send(
					"geometry/import",
					body,
					session.query_scope,
					controller.signal,
				),
				projectId,
			);
			if (!current()) return;
			const original = Uint8Array.from(atob(command.content_base64), (char) =>
					char.charCodeAt(0),
				),
				hash = [
					...new Uint8Array(await crypto.subtle.digest("SHA-256", original)),
				]
					.map((byte) => byte.toString(16).padStart(2, "0"))
					.join("");
			if (!current()) return;
			if (
				prepared.contentHash !== hash ||
				!sameJson(prepared.options, command.options)
			)
				throw new Error("geometry_import_reply_mismatch");
			setAsset(prepared);
			setIntent({ ...pending, assetId: prepared.id });
			try {
				await store.acknowledge(originScope, body, prepared.id);
			} catch {
				if (current()) setStorageFailed(true);
			}
			if (current()) setRefresh((value) => value + 1);
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
			// Typed pre-publication refusals release the editable form. All unknown
			// outcomes keep the exact intent for an explicit retry.
			if (dispatched && isPreMutationInputRefusal(cause)) {
				setIntent(null);
				setDurable(false);
				setRecords((values) =>
					values.filter(
						(value) => value.scope !== originScope || value.body !== body,
					),
				);
				try {
					await store.clear(originScope, body);
				} catch {
					if (current()) setStorageFailed(true);
				}
			}
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
		busy,
		durable,
		intent,
		asset,
		error,
		refresh: () => setRefresh((value) => value + 1),
		dismiss,
		prepare: (command: GeometryImportCommand) =>
			run(
				wire(
					readObject(readGeometryImportCommand(command)),
					session.runtime.limits.max_json_depth,
					session.runtime.limits.max_body_bytes,
				),
				session.query_scope,
			),
		retry: (record: GeometryImportIntent) => run(record.body, record.scope),
	};
}
